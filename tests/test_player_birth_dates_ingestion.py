from __future__ import annotations

import csv
from datetime import UTC, datetime
import gzip
import json
from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion import player_birth_dates
from tools.data_pipeline.ingestion.player_birth_dates import (
    BirthDateEvidenceError,
    BirthDateProposal,
    BirthDateProposalCategory,
    backfill_player_birth_dates,
)


@pytest.fixture(autouse=True)
def _isolate_reviewed_dates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture databases must not load reviewed IDs from the live player catalogue."""
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(player_birth_dates, "REVIEWED_PLAYER_BIRTH_DATES_PATH", reviewed)


def _csv(path: Path, columns: list[str], rows: list[list[str]], compressed: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if compressed else open
    with opener(path, "wt", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def _sources(root: Path) -> None:
    columns = ["code", "birth_date", "opta_code"]
    _csv(root / "fpl_archive_vaastav/2024-25/players_raw.csv", columns,
         [["101", "1994-02-03", "p101"], ["102", "None", "p102"],
          ["103", "None", "None"], ["105", "1989-01-02", "None"]])
    for season in ("2025-26", "2026-27"):
        _csv(root / f"fpl_archive_vaastav/{season}/players_raw.csv", columns, [])
    bootstrap = root / "official_fpl_api/bootstrap-static.json"
    bootstrap.parent.mkdir(parents=True)
    bootstrap.write_text('{"elements": []}', encoding="utf-8")
    birth = datetime(1995, 4, 5, tzinfo=UTC)
    payload = {"stats": {"content": [{"owner": {
        "altIds": {"opta": "p102"},
        "birth": {"date": {"millis": int(birth.timestamp() * 1000), "label": "5 April 1995"}},
    }}]}}
    page = root / "premier_league_api/stats/2024-25/players/appearances/page-000.json"
    page.parent.mkdir(parents=True)
    page.write_text(json.dumps(payload), encoding="utf-8")
    _csv(root / "transfermarkt_datasets/players.csv.gz",
         ["player_id", "name", "date_of_birth"],
         [["301", "Third Player", "1996-02-06 00:00:00"],
          ["302", "Unknown Player", "2000-01-01 00:00:00"]], compressed=True)
    _csv(root / "transfermarkt_datasets/games.csv.gz",
         ["game_id", "competition_id", "season", "home_club_id", "away_club_id",
          "home_club_name", "away_club_name"],
         [["401", "GB1", "2024", "501", "502", "Arsenal FC", "Chelsea FC"]], compressed=True)
    _csv(root / "transfermarkt_datasets/appearances.csv.gz",
         ["player_id", "game_id", "player_club_id", "minutes_played"],
         [["301", "401", "501", "90"], ["302", "401", "502", "90"]], compressed=True)
    bindings = [{"player": {"value": f"https://wikidata.org/entity/Q{idx}"},
                 "name": {"value": name}, "dob": {"value": dob + "T00:00:00Z"},
                 "precision": {"value": precision}}
                for idx, name, dob, precision in ((1, "Third Player", "1996-02-06", "11"),
                                                  (2, "Unknown Player", "2000-01-01", "9"))]
    wiki = root / "wikidata_players/premier_league_club_players_dob.json"
    wiki.parent.mkdir(parents=True)
    wiki.write_text(json.dumps({"results": {"bindings": bindings}}), encoding="utf-8")


def _database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE players (player_id INTEGER PRIMARY KEY, display_name TEXT, date_of_birth TEXT);
            CREATE TABLE player_source_ids (source_namespace TEXT, source_scope TEXT, source_id TEXT, player_id INTEGER);
            CREATE TABLE seasons (season_id INTEGER, label TEXT);
            CREATE TABLE gameweeks (gameweek_id INTEGER, season_id INTEGER);
            CREATE TABLE teams (team_id INTEGER, team_key TEXT);
            CREATE TABLE player_gameweek_teams (gameweek_id INTEGER, player_id INTEGER,
                team_id INTEGER, fixtures_with_minutes INTEGER);
            INSERT INTO seasons VALUES (1, '2024-25');
            INSERT INTO gameweeks VALUES (1, 1);
            INSERT INTO teams VALUES (1, 'arsenal');
            INSERT INTO players VALUES (1, 'Test Player', NULL), (2, 'Other Player', NULL),
                (3, 'Third Player', NULL), (4, 'Unknown Player', NULL),
                (5, 'Known Player', '1989-01-01');
            INSERT INTO player_gameweek_teams VALUES (1, 3, 1, 1);
        """)
        db.executemany("INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2024-25', ?, ?)",
                        [(str(100 + pid), pid) for pid in (1, 2, 3, 5)])


def _reviewed_entry(
    player_id: int = 4,
    display_name: str = "Unknown Player",
    fpl_code: str = "104",
    date_of_birth: str = "2000-01-01",
) -> dict[str, object]:
    return {
        "player_id": player_id,
        "display_name": display_name,
        "fpl_season": "2024-25",
        "fpl_code": fpl_code,
        "date_of_birth": date_of_birth,
        "source_urls": ["https://example.org/player-profile"],
        "review_note": "Identity and exact birth date checked against cited public records.",
    }


def _reviewed_file(monkeypatch, path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps(entries), encoding="utf-8")
    monkeypatch.setattr(player_birth_dates, "REVIEWED_PLAYER_BIRTH_DATES_PATH", path)


def _add_reviewed_fpl_mapping(path: Path, player_id: int = 4, code: str = "104") -> None:
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2024-25', ?, ?)",
            (code, player_id),
        )


def test_dry_run_then_atomic_backfill_and_repeat(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert (preview.direct_fpl, preview.scoped_opta, preview.external_pair) == (1, 1, 1)
    assert [(proposal.player_id, proposal.date_of_birth) for proposal in preview.proposed] == [
        (1, "1994-02-03"), (2, "1995-04-05"), (3, "1996-02-06")
    ]
    assert [proposal.category for proposal in preview.proposed] == [
        BirthDateProposalCategory.FPL,
        BirthDateProposalCategory.PREMIER_LEAGUE_OPTA,
        BirthDateProposalCategory.EXTERNAL_APPEARANCE,
    ]
    assert preview.conflicts == [(5, "Known Player", "1989-01-01", ("1989-01-02",))]
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NULL").fetchone()[0] == 4

    assert backfill_player_birth_dates(root, db).proposed == preview.proposed
    assert not backfill_player_birth_dates(root, db).proposed
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT player_id, date_of_birth FROM players ORDER BY player_id").fetchall() == [
            (1, "1994-02-03"), (2, "1995-04-05"), (3, "1996-02-06"),
            (4, None), (5, "1989-01-01"),
        ]


def test_reviewed_json_is_last_resort_read_only_and_repeat_safe(tmp_path: Path, monkeypatch) -> None:
    root, db, reviewed = tmp_path / "raw", tmp_path / "players.db", tmp_path / "reviewed.json"
    _sources(root)
    _database(db)
    _add_reviewed_fpl_mapping(db)
    _reviewed_file(monkeypatch, reviewed, [
        _reviewed_entry(),
        _reviewed_entry(1, "Test Player", "101", "1994-02-03"),
    ])

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert preview.reviewed_json == 1
    assert (4, "Unknown Player", "2000-01-01", BirthDateProposalCategory.REVIEWED_JSON) in preview.proposed
    assert (1, "Test Player", "1994-02-03", BirthDateProposalCategory.FPL) in preview.proposed
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id = 4").fetchone() == (None,)

    applied = backfill_player_birth_dates(root, db)
    assert applied.reviewed_json == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id = 4").fetchone() == (
            "2000-01-01",
        )

    repeated = backfill_player_birth_dates(root, db)
    assert repeated.proposed == []
    assert repeated.reviewed_json == 0
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id = 4").fetchone() == (
            "2000-01-01",
        )


@pytest.mark.parametrize(("field", "value", "message"), [
    ("player_id", 999, "no valid canonical player_id"),
    ("display_name", "Changed Name", "display_name does not exactly match"),
    ("fpl_code", "999", "FPL mapping does not match"),
    ("fpl_season", "2025-26", "FPL mapping does not match"),
    ("date_of_birth", "2000-02-30", "Invalid source date"),
    ("source_urls", ["javascript:alert(1)"], "unique public"),
    ("review_note", "   ", "non-empty review_note"),
])
def test_reviewed_json_rejects_tampered_entries_before_writing(
    tmp_path: Path, monkeypatch, field: str, value: object, message: str,
) -> None:
    root, db, reviewed = tmp_path / "raw", tmp_path / "players.db", tmp_path / "reviewed.json"
    _sources(root)
    _database(db)
    _add_reviewed_fpl_mapping(db)
    entry = _reviewed_entry()
    entry[field] = value
    _reviewed_file(monkeypatch, reviewed, [entry])

    with pytest.raises(BirthDateEvidenceError, match=message):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1


def test_reviewed_json_validates_all_entries_and_rejects_duplicate_players(
    tmp_path: Path, monkeypatch,
) -> None:
    root, db, reviewed = tmp_path / "raw", tmp_path / "players.db", tmp_path / "reviewed.json"
    _sources(root)
    _database(db)
    _add_reviewed_fpl_mapping(db)
    _reviewed_file(monkeypatch, reviewed, [_reviewed_entry(), _reviewed_entry(player_id=999)])

    with pytest.raises(BirthDateEvidenceError, match="no valid canonical player_id"):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id = 4").fetchone() == (None,)
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1

    _reviewed_file(monkeypatch, reviewed, [_reviewed_entry(), _reviewed_entry()])
    with pytest.raises(BirthDateEvidenceError, match="Duplicate reviewed DOB player_id"):
        backfill_player_birth_dates(root, db, dry_run=True)


def test_reviewed_json_conflicts_with_automatic_evidence_are_excluded(
    tmp_path: Path, monkeypatch,
) -> None:
    root, db, reviewed = tmp_path / "raw", tmp_path / "players.db", tmp_path / "reviewed.json"
    _sources(root)
    _database(db)
    _reviewed_file(monkeypatch, reviewed, [
        _reviewed_entry(1, "Test Player", "101", "1995-02-03"),
    ])

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert all(proposal.player_id != 1 for proposal in preview.proposed)
    assert (1, "Test Player", None, ("1994-02-03", "1995-02-03")) in preview.conflicts
    assert preview.reviewed_json == 0


def test_reviewed_json_rejects_disagreement_with_existing_dob_atomically(
    tmp_path: Path, monkeypatch,
) -> None:
    root, db, reviewed = tmp_path / "raw", tmp_path / "players.db", tmp_path / "reviewed.json"
    _sources(root)
    _database(db)
    _reviewed_file(monkeypatch, reviewed, [
        _reviewed_entry(5, "Known Player", "105", "1990-01-01"),
    ])

    with pytest.raises(BirthDateEvidenceError, match="disagrees with existing DOB"):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id = 5").fetchone() == (
            "1989-01-01",
        )


def test_cli_dry_run_forwards_core_root_and_write_uses_volume_user(tmp_path: Path, monkeypatch) -> None:
    calls = []
    from tools.data_pipeline.ingestion.player_birth_dates import BirthDateSummary
    summary = BirthDateSummary([], 0, 0, 0, 0, [])
    monkeypatch.setattr(cli, "backfill_player_birth_dates", lambda root, db, dry_run: (
        calls.append((root, db, dry_run)) or summary
    ))
    result = CliRunner().invoke(cli.app, ["ingest", "player-birth-dates", "--dry-run", "--raw-root", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert calls == [(tmp_path, cli.DATABASE_PATH, True)]
    command = compose_runner.build_compose_command(["ingest", "player-birth-dates"], project_root=tmp_path)
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


def test_cli_lists_candidates_only_in_read_only_mode(monkeypatch) -> None:
    from tools.data_pipeline.ingestion.player_birth_dates import BirthDateSummary
    calls = []
    monkeypatch.setattr(cli, "backfill_player_birth_dates", lambda root, db, dry_run: (
        calls.append(dry_run) or BirthDateSummary([
            BirthDateProposal(7, "FPL Player", "2001-02-03", BirthDateProposalCategory.FPL),
            BirthDateProposal(8, "Opta Player", "2001-02-03", BirthDateProposalCategory.PREMIER_LEAGUE_OPTA),
            BirthDateProposal(9, "Roster Player", "2001-02-03", BirthDateProposalCategory.PREMIER_LEAGUE_ROSTER),
            BirthDateProposal(
                10, "Sample Player", "2001-02-03", BirthDateProposalCategory.EXTERNAL_APPEARANCE
            ),
            BirthDateProposal(11, "ID Player", "2001-02-03", BirthDateProposalCategory.EXTERNAL_ID_NAME),
            BirthDateProposal(12, "Manual Player", "2001-02-03", BirthDateProposalCategory.REVIEWED_JSON),
        ], 1, 1, 1, 0, [], 1, 1, 1)
    ))
    preview = CliRunner().invoke(cli.app, ["ingest", "player-birth-dates", "--dry-run", "--show-candidates"])
    assert preview.exit_code == 0, preview.output
    assert "candidate [Transfermarkt/Wikidata with PL appearance evidence] player 10 Sample Player: 2001-02-03" in preview.output
    assert "candidate [reviewed JSON fallback] player 12 Manual Player: 2001-02-03" in preview.output
    assert "1 reviewed JSON fallback" in preview.output
    source_order = [
        preview.output.index("1 saved FPL"),
        preview.output.index("1 official PL API Opta"),
        preview.output.index("1 official PL API season rosters"),
        preview.output.index("1 matched Transfermarkt/Wikidata with PL club/season evidence"),
        preview.output.index("1 unique name plus Wikidata Transfermarkt ID without appearance"),
        preview.output.index("1 reviewed JSON fallback"),
    ]
    assert source_order == sorted(source_order)
    assert calls == [True]
    rejected = CliRunner().invoke(cli.app, ["ingest", "player-birth-dates", "--show-candidates"])
    assert rejected.exit_code == 1
    assert calls == [True]


def test_external_match_rejects_canonical_homonyms_and_missing_evidence(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO players VALUES (6, 'Third Player', NULL)")

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert preview.external_pair == 0
    assert all(proposal.player_id != 3 for proposal in preview.proposed)


def test_missing_required_source_cannot_partially_write(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    (root / "transfermarkt_datasets/games.csv.gz").unlink()
    with pytest.raises(FileNotFoundError):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1


def test_external_match_rejects_duplicate_transfermarkt_names(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _csv(root / "transfermarkt_datasets/players.csv.gz",
         ["player_id", "name", "date_of_birth"],
         [["301", "Third Player", "1996-02-06 00:00:00"],
          ["303", "Third Player", "2006-04-07 00:00:00"]], compressed=True)
    assert backfill_player_birth_dates(root, db, dry_run=True).external_pair == 0


def _linked_batch(root: Path, bindings: list[tuple[str, str, str, str]]) -> None:
    folder = root / "wikidata_transfermarkt"
    folder.mkdir(parents=True)
    rows = [{"tmId": {"value": tm_id}, "player": {"value": qid},
             "dob": {"value": dob + "T00:00:00Z"}, "precision": {"value": precision}}
            for tm_id, qid, dob, precision in bindings]
    (folder / "batch-000.json").write_text(json.dumps({"results": {"bindings": rows}}), encoding="utf-8")


def test_id_link_fills_when_wikidata_english_label_differs(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    wiki = root / "wikidata_players/premier_league_club_players_dob.json"
    payload = json.loads(wiki.read_text(encoding="utf-8"))
    payload["results"]["bindings"][0]["name"]["value"] = "An unrelated label"
    wiki.write_text(json.dumps(payload), encoding="utf-8")
    _linked_batch(root, [("301", "http://www.wikidata.org/entity/Q1", "1996-02-06", "11"),
                         ("302", "http://www.wikidata.org/entity/Q2", "2000-01-01", "11")])

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert preview.external_pair == 1
    assert (3, "Third Player", "1996-02-06", BirthDateProposalCategory.EXTERNAL_APPEARANCE) in preview.proposed
    assert all(proposal.player_id != 4 for proposal in preview.proposed)  # No matching FPL club appearance.
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id=3").fetchone() == (None,)

    assert backfill_player_birth_dates(root, db).external_pair == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id=3").fetchone() == ("1996-02-06",)
    assert backfill_player_birth_dates(root, db, dry_run=True).external_pair == 0


@pytest.mark.parametrize("bindings", [
    [("301", "Q1", "1996-02-06", "9")],  # A coarse date cannot prove a day.
    [("301", "Q1", "1996-02-06", "11"), ("301", "Q2", "1996-02-06", "11")],
    [("301", "Q1", "1996-02-07", "11")],  # ID-linked evidence contradicts name-matched source.
])
def test_id_link_rejects_imprecise_ambiguous_and_conflicting_dates(
    tmp_path: Path, bindings: list[tuple[str, str, str, str]],
) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _linked_batch(root, bindings)
    assert backfill_player_birth_dates(root, db, dry_run=True).external_pair == 0


def test_incomplete_id_link_batches_cannot_partially_write(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _linked_batch(root, [("301", "Q1", "1996-02-06", "11")])
    _csv(root / "transfermarkt_datasets/appearances.csv.gz",
         ["player_id", "game_id", "player_club_id", "minutes_played"],
         [[str(pid), "401", "501", "90"] for pid in range(301, 377)], compressed=True)
    with pytest.raises(ValueError, match="Incomplete Wikidata Transfermarkt birth-date batches"):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1


def test_id_link_does_not_bypass_ambiguous_canonical_or_transfermarkt_names(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _linked_batch(root, [("301", "Q1", "1996-02-06", "11")])
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO players VALUES (6, 'Third Player', NULL)")
    assert backfill_player_birth_dates(root, db, dry_run=True).external_pair == 0

    with sqlite3.connect(db) as connection:
        connection.execute("DELETE FROM players WHERE player_id = 6")
    _csv(root / "transfermarkt_datasets/players.csv.gz",
         ["player_id", "name", "date_of_birth"],
         [["301", "Third Player", "1996-02-06 00:00:00"],
          ["303", "Third Player", "1996-02-06 00:00:00"]], compressed=True)
    assert backfill_player_birth_dates(root, db, dry_run=True).external_pair == 0


def _fpl_names_for_name_only_test(root: Path) -> None:
    columns = ["id", "element_type", "first_name", "second_name", "web_name", "code", "birth_date", "opta_code"]
    for year in range(2016, 2027):
        season = f"{year}-{(year + 1) % 100:02d}"
        _csv(root / f"fpl_archive_vaastav/{season}/players_raw.csv", columns,
             [["3", "3", "Third", "Player", "Player", "103", "None", "None"]])
    bootstrap = root / "official_fpl_api/bootstrap-static.json"
    bootstrap.write_text(json.dumps({"elements": [
        {"id": 3, "element_type": 3, "first_name": "Third", "second_name": "Player",
         "code": 103, "birth_date": None}
    ]}), encoding="utf-8")


def test_exact_id_and_name_can_fill_without_appearance_after_separate_capture(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _fpl_names_for_name_only_test(root)
    wiki = root / "wikidata_players/premier_league_club_players_dob.json"
    wiki.write_text(json.dumps({"results": {"bindings": []}}), encoding="utf-8")
    _csv(root / "transfermarkt_datasets/appearances.csv.gz",
         ["player_id", "game_id", "player_club_id", "minutes_played"],
         [["301", "401", "501", "0"]], compressed=True)
    folder = root / "wikidata_transfermarkt_fpl"
    folder.mkdir()
    (folder / "batch-000.json").write_text(json.dumps({"results": {"bindings": [
        {"tmId": {"value": "301"}, "player": {"value": "Q3"},
         "dob": {"value": "1996-02-06T00:00:00Z"}, "precision": {"value": "11"}}
    ]}}), encoding="utf-8")

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert (preview.external_pair, preview.id_name_only) == (0, 1)
    assert (3, "Third Player", "1996-02-06", BirthDateProposalCategory.EXTERNAL_ID_NAME) in preview.proposed
    assert backfill_player_birth_dates(root, db).id_name_only == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id=3").fetchone() == ("1996-02-06",)


def test_incomplete_name_only_capture_prevents_any_write(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _fpl_names_for_name_only_test(root)
    (root / "wikidata_transfermarkt_fpl").mkdir()
    with pytest.raises(ValueError, match="Incomplete Wikidata FPL Transfermarkt birth-date batches"):
        backfill_player_birth_dates(root, db)
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM players WHERE date_of_birth IS NOT NULL").fetchone()[0] == 1


def test_official_roster_precedes_external_but_not_fpl_or_opta(tmp_path: Path) -> None:
    root, db = tmp_path / "raw", tmp_path / "players.db"
    _sources(root)
    _database(db)
    _fpl_names_for_name_only_test(root)
    wiki = root / "wikidata_players/premier_league_club_players_dob.json"
    wiki_payload = json.loads(wiki.read_text(encoding="utf-8"))
    wiki_payload["results"]["bindings"][1]["precision"]["value"] = "11"
    wiki.write_text(json.dumps(wiki_payload), encoding="utf-8")
    _csv(root / "fpl_archive_vaastav/2024-25/players_raw.csv",
         ["id", "element_type", "first_name", "second_name", "web_name", "code", "birth_date", "opta_code"],
         [["3", "3", "Third", "Player", "Player", "103", "None", "None"],
          ["1", "3", "Test", "Player", "Player", "101", "1994-02-03", "None"],
          ["2", "3", "Other", "Player", "Player", "102", "None", "p102"]])
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO player_source_ids VALUES "
                           "('fpl.element.code', 'premier-league:2024-25', '104', 4)")
        connection.execute("INSERT INTO teams VALUES (2, 'chelsea')")
        connection.execute("INSERT INTO player_gameweek_teams VALUES (1, 4, 2, 1)")
    external_only = backfill_player_birth_dates(root, db, dry_run=True)
    assert (4, "Unknown Player", "2000-01-01", BirthDateProposalCategory.EXTERNAL_APPEARANCE) in external_only.proposed
    seasons = root / "premier_league_api/competition_seasons.json"
    seasons.write_text(json.dumps({"content": [{"label": "2024/25", "id": 123}]}), encoding="utf-8")
    page = root / "premier_league_api/players/2024-25/page-000.json"
    page.parent.mkdir(parents=True)
    dob = datetime(2000, 1, 1, tzinfo=UTC)
    page.write_text(json.dumps({"pageInfo": {
        "page": 0, "numPages": 1, "pageSize": 100, "numEntries": 3,
    }, "content": [
        {"id": 501, "name": {"display": "Unknown Player"},
         "birth": {"date": {"millis": int(dob.timestamp() * 1000), "label": "1 January 2000"}}},
        {"id": 502, "name": {"display": "Test Player"},
         "birth": {"date": {"millis": int(datetime(1994, 2, 3, tzinfo=UTC).timestamp() * 1000),
                             "label": "3 February 1994"}}},
        {"id": 503, "name": {"display": "Other Player"},
         "birth": {"date": {"millis": int(datetime(1995, 4, 5, tzinfo=UTC).timestamp() * 1000),
                             "label": "5 April 1995"}}},
    ]}), encoding="utf-8")

    preview = backfill_player_birth_dates(root, db, dry_run=True)
    assert (preview.direct_fpl, preview.scoped_opta, preview.pl_roster, preview.external_pair) == (1, 1, 1, 1)
    assert (1, "Test Player", "1994-02-03", BirthDateProposalCategory.FPL) in preview.proposed
    assert (2, "Other Player", "1995-04-05", BirthDateProposalCategory.PREMIER_LEAGUE_OPTA) in preview.proposed
    assert (4, "Unknown Player", "2000-01-01", BirthDateProposalCategory.PREMIER_LEAGUE_ROSTER) in preview.proposed
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id=4").fetchone() == (None,)
    assert backfill_player_birth_dates(root, db).pl_roster == 1
    with sqlite3.connect(db) as connection:
        assert connection.execute("SELECT date_of_birth FROM players WHERE player_id=4").fetchone() == ("2000-01-01",)
