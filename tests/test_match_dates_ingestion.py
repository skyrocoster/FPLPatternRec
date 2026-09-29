"""Premier League local dates must agree with accepted FPL fixtures."""

from datetime import datetime
import json
from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.canonical_fixtures import _fixtures
from tools.data_pipeline.ingestion.canonical_teams import TEAM_REFERENCE_PATH, _read_clubs
from tools.data_pipeline.ingestion.match_dates import MatchDatesError, MatchDatesSummary, load_match_dates
from tools.data_pipeline.ingestion.player_gameweek_teams import _source_teams


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/fpl_archive_vaastav"
PL = ROOT / "data/raw/premier_league_api/fixtures"
SCHEMA = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"


def _sample(tmp_path: Path, season: str = "2026-27") -> tuple[Path, Path, dict]:
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO competitions (competition_key, name) VALUES ('premier-league', 'Premier League')")
        connection.execute(
            "INSERT INTO seasons (competition_id, label, start_year, end_year) VALUES (1, ?, ?, ?)",
            (season, int(season[:4]), int(season[:4]) + 1),
        )
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", [
            ("arsenal", "Arsenal"), ("bournemouth", "Bournemouth"),
        ])
        connection.execute(
            "INSERT INTO fixtures (season_id, home_team_id, away_team_id, kickoff_at, "
            "status, home_goals, away_goals) VALUES (1, 1, 2, ?, 'finished', 2, 1)",
            (f"{season[:4]}-08-21T19:00:00Z",),
        )
    utc = datetime.fromisoformat(f"{season[:4]}-08-21T19:00:00+00:00")
    # Avoid platform-specific strftime day modifiers (Windows does not support %-d).
    label = f"{utc.strftime('%a')} {utc.day} {utc.strftime('%b %Y')}, 20:00 BST"
    match = {
        "id": 123, "status": "C", "kickoff": {
            "millis": int(utc.timestamp() * 1000), "label": label, "gmtOffset": 1,
        },
        "teams": [{"team": {"name": "Arsenal"}, "score": 2},
                  {"team": {"name": "Bournemouth"}, "score": 1}],
    }
    folder = tmp_path / "pl" / (
        "English-Premier-League-Season-2026-2027" if season == "2026-27" else season
    )
    folder.mkdir(parents=True)
    (folder / "page-000.json").write_text(json.dumps({
        "pageInfo": {"page": 0, "numPages": 1, "numEntries": 1}, "content": [match],
    }), encoding="utf-8")
    return database, tmp_path / "pl", match


def _dates(database: Path) -> list[tuple[int, str | None]]:
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT fixture_id, match_date FROM fixtures ORDER BY fixture_id").fetchall()


def test_accepts_checked_local_date_and_repeat_preserves_it(tmp_path: Path) -> None:
    database, pl, _ = _sample(tmp_path)
    result = load_match_dates("2026-27", pl, database)
    before = _dates(database)
    assert result == MatchDatesSummary("2026-27", 1)
    assert before == [(1, "2026-08-21")]
    assert load_match_dates("2026-27", pl, database) == result
    assert _dates(database) == before


def test_conflicting_existing_date_is_never_replaced(tmp_path: Path) -> None:
    database, pl, _ = _sample(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE fixtures SET match_date = '2026-08-20'")
    before = _dates(database)
    with pytest.raises(MatchDatesError, match="Partial or changed"):
        load_match_dates("2026-27", pl, database)
    assert _dates(database) == before


@pytest.mark.parametrize("change", ["score", "kickoff", "label", "weekday", "page_count"])
def test_unverified_saved_evidence_does_not_write(tmp_path: Path, change: str) -> None:
    database, pl, _ = _sample(tmp_path)
    page = next(pl.glob("*/page-000.json"))
    payload = json.loads(page.read_text(encoding="utf-8"))
    match = payload["content"][0]
    if change == "score":
        match["teams"][0]["score"] = 3
    elif change == "kickoff":
        match["kickoff"]["millis"] += 3_600_000
    elif change == "label":
        match["kickoff"]["label"] = match["kickoff"]["label"].replace("BST", "GMT")
    elif change == "weekday":
        match["kickoff"]["label"] = "Mon" + match["kickoff"]["label"][3:]
    else:
        payload["pageInfo"]["numPages"] = 2
    page.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(MatchDatesError):
        load_match_dates("2026-27", pl, database)
    assert _dates(database) == [(1, None)]


def test_incomplete_historical_canonical_season_cannot_be_dated(tmp_path: Path) -> None:
    database, pl, _ = _sample(tmp_path, "2025-26")
    with pytest.raises(MatchDatesError, match="Incomplete canonical fixture season"):
        load_match_dates("2025-26", pl, database)
    assert _dates(database) == [(1, None)]


def test_all_saved_pl_dates_match_saved_fpl_fixtures_in_isolated_database(tmp_path: Path) -> None:
    if not (ARCHIVE / "2016-17/gws/merged_gw.csv").is_file() or not (PL / "2025-26/page-000.json").is_file():
        pytest.skip("Saved FPL and Premier League fixture sources are unavailable")
    database = tmp_path / "saved.db"
    clubs, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO competitions (competition_key, name) VALUES ('premier-league', 'Premier League')")
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        ids = dict(connection.execute("SELECT team_key, team_id FROM teams"))
        for year in range(2016, 2027):
            season = f"{year}-{(year + 1) % 100:02d}"
            season_id = connection.execute(
                "INSERT INTO seasons (competition_id, label, start_year, end_year) "
                "VALUES (1, ?, ?, ?) RETURNING season_id", (season, year, year + 1),
            ).fetchone()[0]
            folder = ARCHIVE / season
            source = _fixtures(folder, _source_teams(folder, aliases))
            connection.executemany(
                "INSERT INTO fixtures (season_id, home_team_id, away_team_id, kickoff_at, "
                "status, home_goals, away_goals) VALUES (?, ?, ?, ?, 'finished', ?, ?)",
                [(season_id, ids[home], ids[away], kickoff, hg, ag)
                 for home, away, kickoff, _, hg, ag in source.values()],
            )
    counts = [load_match_dates(f"{year}-{(year + 1) % 100:02d}", PL, database).fixture_count
              for year in range(2016, 2027)]
    assert counts == [380] * 10 + [10]
    assert load_match_dates("2025-26", PL, database) == MatchDatesSummary("2025-26", 380)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM fixtures WHERE match_date IS NOT NULL").fetchone() == (3810,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_cli_forwards_season_and_runs_as_volume_owner(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_load(season, fixtures_root, database_path):
        calls.append((season, fixtures_root, database_path))
        return MatchDatesSummary(season, 380)

    monkeypatch.setattr(cli, "load_match_dates", fake_load)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["ingest", "match-dates"]).exit_code != 0
    result = runner.invoke(cli.app, [
        "ingest", "match-dates", "--season", "2025-26", "--raw-root", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert calls == [("2025-26", tmp_path / "premier_league_api/fixtures", cli.DATABASE_PATH)]
    assert "Accepted 380 local match dates" in result.output
    command = compose_runner.build_compose_command(["ingest", "match-dates", "--season", "2025-26"])
    assert command[command.index("--user") + 1] == "0:0"
