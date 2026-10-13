"""Prior-season FPL players retain person IDs across transfers and season boundaries."""

import csv
import json
from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.archive_players import ArchivePlayersValidationError, load_archive_players
from tools.data_pipeline.ingestion.canonical_players import load_canonical_players

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"
ARCHIVE_FIELDS = [
    "id", "code", "first_name", "second_name", "birth_date", "element_type",
    "has_temporary_code", "team",
]
EARLY_ARCHIVE_FIELDS = ["id", "code", "first_name", "second_name", "element_type", "team_code", "team"]


def _database(tmp_path: Path) -> Path:
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    return database


def _current(tmp_path: Path, database: Path, elements: list[dict]) -> None:
    bootstrap = tmp_path / "bootstrap.json"
    bootstrap.write_text(json.dumps({
        "events": [{"deadline_time": "2026-08-21T17:30:00Z"}], "elements": elements,
    }), encoding="utf-8")
    load_canonical_players("2026-27", bootstrap, database)


def _element(source_id: int = 10, code: int = 216646, **updates) -> dict:
    row = {
        "id": source_id, "code": code, "element_type": 3,
        "first_name": "Yoane", "second_name": "Wissa", "birth_date": "1996-09-03",
    }
    row.update(updates)
    return row


def _archive_row(source_id: str = "135", code: str = "216646", **updates) -> dict:
    row = {
        "id": source_id, "code": code, "element_type": "3", "has_temporary_code": "False",
        "first_name": "Yoane", "second_name": "Wissa", "birth_date": "1996-09-03", "team": "15",
    }
    row.update(updates)
    return row


def _archive(tmp_path: Path, rows: list[dict], fields: list[str] = ARCHIVE_FIELDS) -> tuple[Path, Path]:
    players = tmp_path / "players_raw.csv"
    idlist = tmp_path / "player_idlist.csv"
    for path, columns in ((players, fields), (idlist, ["id", "first_name", "second_name"])):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return players, idlist


def _state(database: Path) -> tuple[list, list]:
    with sqlite3.connect(database) as connection:
        return (
            connection.execute("SELECT player_id, display_name, date_of_birth FROM players ORDER BY player_id").fetchall(),
            connection.execute(
                "SELECT source_scope, source_namespace, source_id, player_id "
                "FROM player_source_ids ORDER BY source_scope, source_namespace, source_id"
            ).fetchall(),
        )


def test_transfer_uses_existing_player_not_latest_club_or_new_person(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element()])
    players, idlist = _archive(tmp_path, [
        _archive_row(team="15"),
        _archive_row("10", "444", first_name="New", second_name="Player", birth_date="None", team="2"),
    ])

    first = load_archive_players("2025-26", players, idlist, database)
    state = _state(database)
    second = load_archive_players("2025-26", players, idlist, database)

    assert first == second
    assert (first.player_count, first.linked_player_count, first.archive_only_player_count) == (2, 1, 1)
    assert _state(database) == state
    assert state[0] == [(1, "Yoane Wissa", "1996-09-03"), (2, "New Player", None)]
    assert ("premier-league:2025-26", "fpl.element.id", "135", 1) in state[1]
    assert ("premier-league:2026-27", "fpl.element.id", "10", 1) in state[1]
    assert ("premier-league:2025-26", "fpl.element.id", "10", 2) in state[1]
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%stint%'"
        ).fetchall() == []


def test_known_dob_and_shared_surname_accept_shortened_name_without_overwriting(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element(first_name="Kostas", second_name="Tsimikas")])
    players, idlist = _archive(tmp_path, [
        _archive_row(first_name="Konstantinos", second_name="Tsimikas", team="12"),
    ])

    result = load_archive_players("2025-26", players, idlist, database)

    assert result.linked_player_count == 1
    assert _state(database)[0] == [(1, "Kostas Tsimikas", "1996-09-03")]


def test_missing_dob_requires_same_normalized_name_and_preserves_canonical_null(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element(first_name="Armin", second_name="Pecsi", birth_date=None)])
    players, idlist = _archive(tmp_path, [
        _archive_row(first_name="Ármin", second_name="Pécsi", birth_date="2005-02-24"),
    ])

    load_archive_players("2025-26", players, idlist, database)

    assert _state(database)[0] == [(1, "Armin Pecsi", None)]


def test_manager_entries_are_excluded_even_if_code_resolves_to_a_player(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element()])
    before = _state(database)
    players, idlist = _archive(tmp_path, [
        _archive_row("135", "216646", element_type="5", first_name="Assistant", second_name="Manager"),
        _archive_row("136", "555", first_name="Football", second_name="Player"),
    ])

    result = load_archive_players("2025-26", players, idlist, database)

    assert (result.player_count, result.excluded_manager_count) == (1, 1)
    assert len(_state(database)[0]) == len(before[0]) + 1
    assert ("premier-league:2025-26", "fpl.element.code", "216646", 1) not in _state(database)[1]


def test_cannot_load_prior_season_without_current_identity_anchor(tmp_path: Path) -> None:
    database = _database(tmp_path)
    players, idlist = _archive(tmp_path, [_archive_row()])

    with pytest.raises(ArchivePlayersValidationError, match="Load canonical 2026-27"):
        load_archive_players("2025-26", players, idlist, database)
    assert _state(database) == ([], [])


def test_older_archive_requires_next_season_and_rejects_unreviewed_name_collision(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element()])
    players, idlist = _archive(tmp_path, [_archive_row("51", "999", team="2")], EARLY_ARCHIVE_FIELDS)
    with pytest.raises(ArchivePlayersValidationError, match="2025-26 before premier-league:2024-25"):
        load_archive_players("2024-25", players, idlist, database)
    newer, newer_idlist = _archive(tmp_path, [_archive_row()])
    load_archive_players("2025-26", newer, newer_idlist, database)
    players, idlist = _archive(tmp_path, [_archive_row("51", "999", team="2")], EARLY_ARCHIVE_FIELDS)
    before = _state(database)
    with pytest.raises(ArchivePlayersValidationError, match="resembles an unmapped player"):
        load_archive_players("2024-25", players, idlist, database)
    assert _state(database) == before


def test_reviewed_hayden_code_change_requires_specific_source_evidence(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [
        _element(code=465390, first_name="Kaine", second_name="Kesler-Hayden", birth_date="2002-10-23"),
    ])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2020-21', '465390', 1)"
        )
    wrong, idlist = _archive(tmp_path, [
        _archive_row("659", "490098", first_name="Kaine", second_name="Hayden", team_code="999"),
    ], EARLY_ARCHIVE_FIELDS)
    before = _state(database)
    with pytest.raises(ArchivePlayersValidationError, match="Reviewed code change"):
        load_archive_players("2019-20", wrong, idlist, database)
    assert _state(database) == before
    correct, idlist = _archive(tmp_path, [
        _archive_row("659", "490098", first_name="Kaine", second_name="Hayden", team_code="7"),
    ], EARLY_ARCHIVE_FIELDS)
    result = load_archive_players("2019-20", correct, idlist, database)
    assert (result.linked_player_count, result.archive_only_player_count) == (1, 0)
    assert len(_state(database)[0]) == 1


def test_reviewed_2022_23_kesler_hayden_code_change_links_hyphen_variant(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [
        _element(code=465390, first_name="Kaine", second_name="Kesler-Hayden", birth_date="2002-10-23"),
    ])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2023-24', '465390', 1)"
        )
    wrong, idlist = _archive(tmp_path, [
        _archive_row("537", "537043", first_name="Kaine", second_name="Kesler Hayden", team_code="999"),
    ], EARLY_ARCHIVE_FIELDS)
    before = _state(database)
    with pytest.raises(ArchivePlayersValidationError, match="Reviewed code change"):
        load_archive_players("2022-23", wrong, idlist, database)
    assert _state(database) == before
    correct, idlist = _archive(tmp_path, [
        _archive_row("537", "537043", first_name="Kaine", second_name="Kesler Hayden", team_code="7"),
    ], EARLY_ARCHIVE_FIELDS)
    result = load_archive_players("2022-23", correct, idlist, database)
    assert (result.linked_player_count, result.archive_only_player_count) == (1, 0)
    assert len(_state(database)[0]) == 1


def test_hyphen_variant_without_review_forces_manual_review(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [
        _element(code=465390, first_name="Kaine", second_name="Kesler-Hayden", birth_date="2002-10-23"),
    ])
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2023-24', '465390', 1)"
        )
    players, idlist = _archive(tmp_path, [
        _archive_row("537", "999999", first_name="Kaine", second_name="Kesler Hayden", team_code="7"),
    ], EARLY_ARCHIVE_FIELDS)
    before = _state(database)
    with pytest.raises(ArchivePlayersValidationError, match="resembles an unmapped player"):
        load_archive_players("2022-23", players, idlist, database)
    assert _state(database) == before


@pytest.mark.parametrize("changes", [
    {"birth_date": "1995-09-03"},
    {"birth_date": "None", "first_name": "Unrelated"},
    {"has_temporary_code": "True"},
    {"element_type": "6"},
])
def test_conflicting_identifiers_or_details_cannot_partially_write(tmp_path: Path, changes: dict) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element()])
    before = _state(database)
    players, idlist = _archive(tmp_path, [
        _archive_row("9", "1000", first_name="Fresh", second_name="Player"),
        _archive_row(**changes),
    ])

    with pytest.raises(ArchivePlayersValidationError):
        load_archive_players("2025-26", players, idlist, database)
    assert _state(database) == before


def test_duplicate_code_idlist_mismatch_and_wrong_season_are_rejected(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _current(tmp_path, database, [_element()])
    players, idlist = _archive(tmp_path, [_archive_row(), _archive_row("136", "216646")])
    with pytest.raises(ArchivePlayersValidationError, match="Duplicate"):
        load_archive_players("2025-26", players, idlist, database)
    players, idlist = _archive(tmp_path, [_archive_row()])
    idlist.write_text("id,first_name,second_name\n135,Other,Wissa\n", encoding="utf-8")
    with pytest.raises(ArchivePlayersValidationError, match="idlist"):
        load_archive_players("2025-26", players, idlist, database)
    with pytest.raises(ArchivePlayersValidationError, match="2016-17 through 2025-26 only"):
        load_archive_players("2015-16", players, idlist, database)
    assert len(_state(database)[0]) == 1


def test_saved_archive_links_only_corroborated_2026_players(tmp_path: Path) -> None:
    bootstrap = ROOT / "data/raw/official_fpl_api/bootstrap-static.json"
    archive = ROOT / "data/raw/fpl_archive_vaastav/2025-26"
    if not bootstrap.is_file() or not archive.is_dir():
        pytest.skip("Saved FPL snapshots unavailable")
    database = _database(tmp_path)
    load_canonical_players("2026-27", bootstrap, database)
    before = _state(database)

    summary = load_archive_players(
        "2025-26", archive / "players_raw.csv", archive / "player_idlist.csv", database
    )

    assert (summary.player_count, summary.linked_player_count, summary.archive_only_player_count,
            summary.excluded_manager_count) == (841, 480, 361, 0)
    assert _state(database)[0][:667] == before[0]
    assert len(_state(database)[0]) == 1028
    assert len(_state(database)[1]) == 3016
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    state = _state(database)
    assert load_archive_players("2025-26", archive / "players_raw.csv", archive / "player_idlist.csv", database) == summary
    assert _state(database) == state


def test_all_saved_archive_seasons_load_backwards_without_merging_managers(tmp_path: Path) -> None:
    bootstrap = ROOT / "data/raw/official_fpl_api/bootstrap-static.json"
    archives = ROOT / "data/raw/fpl_archive_vaastav"
    if not bootstrap.is_file() or not archives.is_dir():
        pytest.skip("Saved FPL snapshots unavailable")
    database = _database(tmp_path)
    load_canonical_players("2026-27", bootstrap, database)
    current_players = _state(database)[0]
    summaries = []
    for year in range(2025, 2015, -1):
        season = f"{year}-{(year + 1) % 100:02d}"
        folder = archives / season
        summaries.append(load_archive_players(
            season, folder / "players_raw.csv", folder / "player_idlist.csv", database
        ))

    assert [summary.season for summary in summaries] == [
        f"{year}-{(year + 1) % 100:02d}" for year in range(2025, 2015, -1)
    ]
    assert sum(summary.excluded_manager_count for summary in summaries) == 20
    assert _state(database)[0][:667] == current_players
    # 2,758 distinct codes in the imported sources, minus two reviewed Kaine code changes.
    assert len(_state(database)[0]) == 2756
    assert len(_state(database)[1]) == 16010
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT count(*) FROM player_source_ids WHERE source_scope = 'premier-league:2024-25' "
            "AND source_namespace = 'fpl.element.code'"
        ).fetchone() == (784,)
        assert connection.execute(
            "SELECT count(DISTINCT player_id) FROM player_source_ids "
            "WHERE source_id IN ('490098', '465390', '537043') "
            "AND source_namespace = 'fpl.element.code'"
        ).fetchone() == (1,)

    before = _state(database)
    for year, summary in zip(range(2025, 2015, -1), summaries):
        season = summary.season
        folder = archives / season
        assert load_archive_players(
            season, folder / "players_raw.csv", folder / "player_idlist.csv", database
        ) == summary
    assert _state(database) == before
