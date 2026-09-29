"""Historical FPL IDs are immutable mappings, not refreshed club identities."""

import csv
from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.archive_teams import ArchiveTeamsError, ArchiveTeamsSummary, load_archive_teams
from tools.data_pipeline.ingestion.canonical_teams import TEAM_REFERENCE_PATH, _read_clubs
from tools.data_pipeline.ingestion.player_gameweek_teams import _source_teams


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/fpl_archive_vaastav"
SCHEMA = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"


def _setup(tmp_path: Path, season: str, teams: dict[str, str]) -> Path:
    database = tmp_path / "isolated.db"
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        connection.execute("INSERT INTO competitions (competition_key, name) VALUES ('premier-league', 'Premier League')")
        connection.execute(
            "INSERT INTO seasons (competition_id, label, start_year, end_year) VALUES (1, ?, ?, ?)",
            (season, int(season[:4]), int(season[:4]) + 1),
        )
        ids = dict(connection.execute("SELECT team_key, team_id FROM teams"))
        ordered = [ids[teams[str(i)]] for i in range(1, 21)]
        connection.executemany(
            "INSERT INTO fixtures (season_id, home_team_id, away_team_id, status) VALUES (1, ?, ?, 'finished')",
            [(ordered[n % 20], ordered[(n + 1) % 20]) for n in range(380)],
        )
    return database


def _snapshot(database: Path) -> list[tuple[str, str, str, str]]:
    with sqlite3.connect(database) as connection:
        return connection.execute(
            "SELECT source_namespace, source_scope, source_id, team_key "
            "FROM team_source_ids JOIN teams USING (team_id) ORDER BY source_namespace, source_scope, source_id"
        ).fetchall()


def _sample(tmp_path: Path) -> tuple[Path, Path, dict[str, str]]:
    season = "2025-26"
    archive = tmp_path / "archive"
    folder = archive / season
    folder.mkdir(parents=True)
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    names = dict(clubs[:20])
    teams = {str(i): key for i, key in enumerate(names, 1)}
    with (folder / "teams.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["id", "name"])
        writer.writerows((source_id, names[key]) for source_id, key in teams.items())
    return archive, _setup(tmp_path, season, teams), teams


def test_backfill_preserves_mapping_and_unrelated_ids_on_repeat(tmp_path: Path) -> None:
    archive, database, teams = _sample(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO team_source_ids VALUES ('other.provider', 'global', 'abc', 1)"
        )
    first = load_archive_teams("2025-26", archive, database)
    before = _snapshot(database)
    assert first == load_archive_teams("2025-26", archive, database)
    assert first == ArchiveTeamsSummary("2025-26", 20)
    assert _snapshot(database) == before
    assert len(before) == 21
    assert ("fpl.team.id", "premier-league:2025-26", "1", teams["1"]) in before
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_partial_and_changed_mappings_abort_without_filling_or_replacing(tmp_path: Path) -> None:
    archive, database, _ = _sample(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO team_source_ids VALUES ('fpl.team.id', 'premier-league:2025-26', '1', 2)"
        )
    before = _snapshot(database)
    with pytest.raises(ArchiveTeamsError, match="Partial or changed"):
        load_archive_teams("2025-26", archive, database)
    assert _snapshot(database) == before

    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM team_source_ids")
    load_archive_teams("2025-26", archive, database)
    before = _snapshot(database)
    path = archive / "2025-26/teams.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    rows[1][1], rows[2][1] = rows[2][1], rows[1][1]
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(rows)
    with pytest.raises(ArchiveTeamsError, match="Partial or changed"):
        load_archive_teams("2025-26", archive, database)
    assert _snapshot(database) == before


def test_incomplete_season_or_team_source_does_not_write(tmp_path: Path) -> None:
    archive, database, _ = _sample(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE fixtures SET status = 'scheduled' WHERE fixture_id = 1")
    with pytest.raises(ArchiveTeamsError, match="fixtures do not cover"):
        load_archive_teams("2025-26", archive, database)
    assert _snapshot(database) == []
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE fixtures SET status = 'finished' WHERE fixture_id = 1")
    path = archive / "2025-26/teams.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    with path.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(rows[:-1])
    with pytest.raises(ArchiveTeamsError, match="exactly FPL team IDs 1-20"):
        load_archive_teams("2025-26", archive, database)
    assert _snapshot(database) == []
    with pytest.raises(ArchiveTeamsError, match="2016-17 through 2025-26"):
        load_archive_teams("2026-27", archive, database)


@pytest.mark.parametrize("year", range(2016, 2026))
def test_saved_archives_resolve_twenty_distinct_historical_ids(tmp_path: Path, year: int) -> None:
    season = f"{year}-{(year + 1) % 100:02d}"
    if not (ARCHIVE / season).is_dir():
        pytest.skip("Saved archive not present")
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    teams = _source_teams(ARCHIVE / season, aliases)
    database = _setup(tmp_path, season, teams)
    result = load_archive_teams(season, ARCHIVE, database)
    assert result.mapped_team_count == 20
    assert load_archive_teams(season, ARCHIVE, database) == result
    assert {(scope, source_id, key) for _, scope, source_id, key in _snapshot(database)} == {
        (f"premier-league:{season}", source_id, key) for source_id, key in teams.items()
    }


def test_cli_forwards_archive_and_uses_volume_owner(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_load(season, archive_root, database_path):
        calls.append((season, archive_root, database_path))
        return ArchiveTeamsSummary(season, 20)

    monkeypatch.setattr(cli, "load_archive_teams", fake_load)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["ingest", "canonical-archive-teams"]).exit_code != 0
    result = runner.invoke(cli.app, [
        "ingest", "canonical-archive-teams", "--season", "2025-26", "--raw-root", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert calls == [("2025-26", tmp_path / "fpl_archive_vaastav", cli.DATABASE_PATH)]
    assert "Mapped 20 historical FPL teams" in result.output
    command = compose_runner.build_compose_command(
        ["ingest", "canonical-archive-teams", "--season", "2025-26"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]
