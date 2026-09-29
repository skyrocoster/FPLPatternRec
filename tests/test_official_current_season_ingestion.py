"""The current season uses official FPL evidence, including its existing GW 1."""

from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.canonical_fixtures import (
    CanonicalFixturesError, CanonicalFixturesSummary, load_canonical_fixtures,
)
from tools.data_pipeline.ingestion.canonical_teams import TEAM_REFERENCE_PATH, _read_clubs
from tools.data_pipeline.ingestion.match_dates import load_match_dates
from tools.data_pipeline.ingestion.player_fixture_observations import (
    FIXTURE_NAMESPACE,
    PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL,
    PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL,
    PLAYER_FIXTURE_OBSERVATIONS_SQL,
    PlayerFixtureObservationsError,
    PlayerFixtureObservationsSummary,
    load_player_fixture_observations,
)
from tools.data_pipeline.ingestion.player_gameweek_teams import (
    GameweekTeamsError, GameweekTeamsSummary, load_player_gameweek_teams,
)
from tools.data_pipeline.ingestion.official_fpl_season import read_official_fpl_season

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
ARCHIVE = RAW / "fpl_archive_vaastav"
OFFICIAL = RAW / "official_fpl_api"
PL = RAW / "premier_league_api/fixtures"
SEASON = "2026-27"
SCHEMA = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"


def _database(tmp_path: Path) -> Path:
    if not (OFFICIAL / "fixtures.json").is_file():
        pytest.skip("Saved official FPL evidence unavailable")
    tmp_path.mkdir(parents=True, exist_ok=True)
    evidence = read_official_fpl_season(OFFICIAL, SEASON)
    database = tmp_path / "current-season.db"
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        team_ids = dict(connection.execute("SELECT team_key, team_id FROM teams"))
        connection.executemany(
            "INSERT INTO team_source_ids (source_namespace, source_scope, source_id, team_id) "
            "VALUES ('fpl.team.id', ?, ?, ?)",
            [(f"premier-league:{SEASON}", source_id, team_ids[key])
             for source_id, key in evidence.teams.items()],
        )
        for element, code in evidence.elements.items():
            player_id = connection.execute(
                "INSERT INTO players (display_name) VALUES (?) RETURNING player_id", (f"FPL {element}",)
            ).fetchone()[0]
            connection.executemany(
                "INSERT INTO player_source_ids VALUES (?, ?, ?, ?)",
                [("fpl.element.id", f"premier-league:{SEASON}", element, player_id),
                 ("fpl.element.code", f"premier-league:{SEASON}", code, player_id)],
            )
    return database


def _first_week(database: Path) -> tuple[list[tuple], list[tuple]]:
    with sqlite3.connect(database) as connection:
        assignments = connection.execute(
            "SELECT p.gameweek_id, p.player_id, p.team_id, p.source_element_id, "
            "p.first_kickoff_at, p.last_kickoff_at, p.fixture_observations, p.fixtures_with_minutes "
            "FROM player_gameweek_teams p JOIN gameweeks g USING (gameweek_id) "
            "WHERE g.gameweek_number = 1 ORDER BY p.player_id, p.team_id"
        ).fetchall()
        fixtures = connection.execute(
            "SELECT f.fixture_id, m.source_id, f.home_team_id, f.away_team_id, "
            "f.match_date, f.kickoff_at, f.home_goals, f.away_goals, fg.gameweek_id "
            "FROM fixtures f JOIN fixture_source_ids m USING (fixture_id) "
            "JOIN fixture_gameweeks fg USING (fixture_id) "
            "JOIN gameweeks g USING (gameweek_id) WHERE g.gameweek_number = 1 "
            "ORDER BY m.source_id"
        ).fetchall()
        return assignments, fixtures


def _full_state(database: Path) -> tuple[list[tuple], list[tuple], list[tuple]]:
    with sqlite3.connect(database) as connection:
        return tuple(connection.execute(f"SELECT * FROM {table} ORDER BY 1, 2").fetchall()
                      for table in ("gameweeks", "player_gameweek_teams", "fixtures"))


def _canonical_current_season_database(tmp_path: Path) -> Path:
    database = _database(tmp_path)
    no_archive = tmp_path / "missing-archive"
    load_player_gameweek_teams(SEASON, no_archive, database, official_raw_root=OFFICIAL)
    load_canonical_fixtures(SEASON, no_archive, database, official_raw_root=OFFICIAL)
    return database


def _seed_current_observation_fixture_slice(database: Path, source_fixtures: set[str]) -> None:
    evidence = read_official_fpl_season(OFFICIAL, SEASON)
    scope = f"premier-league:{SEASON}"
    with sqlite3.connect(database) as connection:
        connection.execute(PLAYER_FIXTURE_OBSERVATIONS_SQL)
        connection.execute(PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL)
        connection.execute(PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL)
        fixture_ids = dict(connection.execute(
            "SELECT source_id, fixture_id FROM fixture_source_ids "
            "WHERE source_namespace=? AND source_scope=?",
            (FIXTURE_NAMESPACE, scope),
        ))
        player_ids = dict(connection.execute(
            "SELECT source_id, player_id FROM player_source_ids "
            "WHERE source_namespace='fpl.element.id' AND source_scope=?",
            (scope,),
        ))
        team_ids = dict(connection.execute("SELECT team_key, team_id FROM teams"))
        week_ids = dict(connection.execute(
            "SELECT gameweek_number, gameweek_id FROM gameweeks "
            "WHERE season_id=(SELECT season_id FROM seasons WHERE label=?)",
            (SEASON,),
        ))
        rows = [
            (
                fixture_ids[source_fixture], player_ids[element], team_ids[club],
                week_ids[week], element, minutes,
            )
            for element, _, week, club, _, minutes, source_fixture in evidence.observations
            if source_fixture in source_fixtures
        ]
        connection.executemany(
            "INSERT INTO player_fixture_observations "
            "(fixture_id, player_id, team_id, gameweek_id, source_element_id, minutes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        connection.executemany(
            "INSERT INTO player_fixture_observation_fixtures (fixture_id) VALUES (?)",
            ((fixture_ids[source_id],) for source_id in sorted(source_fixtures, key=int)),
        )


def test_official_gw1_agrees_with_existing_archive_and_new_weeks_append(tmp_path: Path) -> None:
    database = _database(tmp_path)
    assert load_player_gameweek_teams(SEASON, ARCHIVE, database).player_team_rows == 610
    assert load_canonical_fixtures(SEASON, ARCHIVE, database).fixture_count == 10
    assert load_match_dates(SEASON, PL, database).fixture_count == 10
    original = _first_week(database)

    teams = load_player_gameweek_teams(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    assert teams.gameweeks == 5
    assert teams.player_team_rows == 610 + 626 + 654 + 659 + 667
    assert _first_week(database) == original
    fixtures = load_canonical_fixtures(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    assert fixtures == CanonicalFixturesSummary(SEASON, 50)
    assert load_match_dates(SEASON, PL, database).fixture_count == 50
    assert _first_week(database) == original
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM fixtures WHERE match_date IS NULL").fetchone() == (0,)
        assert connection.execute("SELECT count(*) FROM fixture_gameweeks").fetchone() == (50,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    state = _full_state(database)
    assert load_player_gameweek_teams(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL) == teams
    assert load_canonical_fixtures(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL) == fixtures
    assert load_match_dates(SEASON, PL, database).fixture_count == 50
    assert _full_state(database) == state


def test_official_fpl_loads_gw1_without_any_archive_files(tmp_path: Path) -> None:
    database = _database(tmp_path)
    no_archive = tmp_path / "missing-archive"
    teams = load_player_gameweek_teams(SEASON, no_archive, database, official_raw_root=OFFICIAL)
    assert (teams.gameweeks, teams.player_team_rows) == (5, 3216)
    fixtures = load_canonical_fixtures(SEASON, no_archive, database, official_raw_root=OFFICIAL)
    assert fixtures.fixture_count == 50
    assert len(_first_week(database)[0]) == 610
    assert len(_first_week(database)[1]) == 10
    assert load_match_dates(SEASON, PL, database).fixture_count == 50


def test_changed_first_week_or_partial_existing_links_rolls_back(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_player_gameweek_teams(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE player_gameweek_teams SET fixtures_with_minutes = 0 "
                           "WHERE rowid = (SELECT rowid FROM player_gameweek_teams "
                           "WHERE fixtures_with_minutes = 1 LIMIT 1)")
    before = _full_state(database)
    with pytest.raises(GameweekTeamsError, match="Existing player/team rows"):
        load_player_gameweek_teams(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    assert _full_state(database) == before

    # Recreate a clean isolated season for the fixture-link rollback case.
    database = _database(tmp_path / "links")
    load_player_gameweek_teams(SEASON, ARCHIVE, database)
    load_canonical_fixtures(SEASON, ARCHIVE, database)
    load_player_gameweek_teams(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM fixture_gameweeks WHERE fixture_id = "
                           "(SELECT fixture_id FROM fixture_source_ids WHERE source_id = '1' "
                           "AND source_scope = 'premier-league:2026-27')")
    before = _full_state(database)
    with pytest.raises(CanonicalFixturesError, match="fixture/gameweek links"):
        load_canonical_fixtures(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    assert _full_state(database) == before


def test_changed_official_team_mapping_is_rejected_before_writing(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE team_source_ids SET team_id = (SELECT team_id FROM teams "
                           "WHERE team_key = 'chelsea') WHERE source_scope = 'premier-league:2026-27' "
                           "AND source_namespace = 'fpl.team.id' AND source_id = '1'")
    with pytest.raises(GameweekTeamsError, match="season-scoped canonical mappings"):
        load_player_gameweek_teams(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM seasons").fetchone() == (0,)


def test_cli_routes_current_season_to_official_fpl_not_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = []

    def fake_teams(season, archive_root, database_path, **kwargs):
        calls.append(("teams", season, archive_root, kwargs))
        return GameweekTeamsSummary(season, 5, 3216, 1)

    def fake_fixtures(season, archive_root, database_path, **kwargs):
        calls.append(("fixtures", season, archive_root, kwargs))
        return CanonicalFixturesSummary(season, 50)

    monkeypatch.setattr(cli, "load_player_gameweek_teams", fake_teams)
    monkeypatch.setattr(cli, "load_canonical_fixtures", fake_fixtures)
    for command in ("player-gameweek-teams", "canonical-fixtures"):
        result = CliRunner().invoke(cli.app, ["ingest", command, "--season", SEASON,
                                              "--raw-root", str(tmp_path)])
        assert result.exit_code == 0, result.output
    assert calls == [(kind, SEASON, tmp_path / "fpl_archive_vaastav",
                      {"official_raw_root": tmp_path / "official_fpl_api"})
                     for kind in ("teams", "fixtures")]


def test_official_player_fixture_observations_append_finished_fixtures_and_repeat(
    tmp_path: Path,
) -> None:
    database = _canonical_current_season_database(tmp_path)
    evidence = read_official_fpl_season(OFFICIAL, SEASON)
    old_source_fixtures = {
        source_id for source_id, fixture in evidence.fixtures.items() if fixture[3] == 1
    }
    assert len(old_source_fixtures) == 10
    _seed_current_observation_fixture_slice(database, old_source_fixtures)

    result = load_player_fixture_observations(
        SEASON, ARCHIVE, database, official_raw_root=OFFICIAL
    )
    expected = PlayerFixtureObservationsSummary(
        SEASON,
        len(evidence.fixtures),
        len(evidence.observations),
        sum(observation[5] > 0 for observation in evidence.observations),
    )
    assert result == expected
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT count(*), sum(minutes > 0) FROM player_fixture_observations"
        ).fetchone() == (result.observation_count, result.appearance_count)
        assert connection.execute(
            "SELECT count(*) FROM player_fixture_observation_fixtures"
        ).fetchone() == (result.fixture_count,)
        before = connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall()

    assert load_player_fixture_observations(
        SEASON, ARCHIVE, database, official_raw_root=OFFICIAL
    ) == result
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall() == before


@pytest.mark.parametrize("change", ["missing", "missing-fixture", "changed"])
def test_official_player_fixture_observations_reject_missing_or_changed_old_rows(
    tmp_path: Path, change: str
) -> None:
    database = _canonical_current_season_database(tmp_path)
    load_player_fixture_observations(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    with sqlite3.connect(database) as connection:
        fixture_id, player_id = connection.execute(
            "SELECT fixture_id, player_id FROM player_fixture_observations "
            "ORDER BY fixture_id, player_id LIMIT 1"
        ).fetchone()
        if change == "missing":
            connection.execute(
                "DELETE FROM player_fixture_observations WHERE fixture_id=? AND player_id=?",
                (fixture_id, player_id),
            )
        elif change == "missing-fixture":
            connection.execute(
                "DELETE FROM player_fixture_observations WHERE fixture_id=?",
                (fixture_id,),
            )
        else:
            connection.execute(
                "UPDATE player_fixture_observations SET minutes=minutes+1 "
                "WHERE fixture_id=? AND player_id=?",
                (fixture_id, player_id),
            )
        before = connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall()

    with pytest.raises(PlayerFixtureObservationsError, match="Existing official player/fixture observations"):
        load_player_fixture_observations(SEASON, ARCHIVE, database, official_raw_root=OFFICIAL)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall() == before


def test_cli_routes_current_player_fixture_observations_to_official_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = []
    summary = PlayerFixtureObservationsSummary(SEASON, 50, 1_000, 800)

    def fake_load(season, archive_root, database_path, **kwargs):
        calls.append((season, archive_root, kwargs))
        return summary

    monkeypatch.setattr(cli, "load_player_fixture_observations", fake_load)
    result = CliRunner().invoke(
        cli.app,
        ["ingest", "player-fixture-observations", "--season", SEASON, "--raw-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    assert calls == [(
        SEASON,
        tmp_path / "fpl_archive_vaastav",
        {"official_raw_root": tmp_path / "official_fpl_api"},
    )]
    command = compose_runner.build_compose_command(
        ["ingest", "player-fixture-observations", "--season", SEASON]
    )
    assert command[command.index("--user") + 1] == "0:0"
