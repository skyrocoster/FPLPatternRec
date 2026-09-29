"""Canonical matches must agree with saved FPL gameweeks before accepting IDs."""

import csv
from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.canonical_fixtures import (
    FIXTURE_GAMEWEEKS_SQL, CanonicalFixturesError, CanonicalFixturesSummary, _expected_assignments, _fixtures,
    load_canonical_fixtures,
)
from tools.data_pipeline.ingestion.canonical_players import CODE_NAMESPACE, ID_NAMESPACE
from tools.data_pipeline.ingestion.canonical_teams import TEAM_REFERENCE_PATH, _read_clubs
from tools.data_pipeline.ingestion.player_fixture_observations import (
    FIXTURE_NAMESPACE,
    FIXTURE_SCOPE,
    PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL,
    PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL,
    PLAYER_FIXTURE_OBSERVATIONS_SQL,
    PlayerFixtureObservationsError,
    PlayerFixtureObservationsSummary,
    load_player_fixture_observations,
)
from tools.data_pipeline.ingestion.player_gameweek_teams import (
    _observations,
    _source_teams,
    load_player_gameweek_teams,
)

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/fpl_archive_vaastav"
SEASON = "2025-26"


def _database(tmp_path: Path, season: str = SEASON) -> Path:
    if not (ARCHIVE / season / "players_raw.csv").is_file():
        pytest.skip(f"Saved {season} FPL archive unavailable")
    database = tmp_path / "fixtures.db"
    schema = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    with sqlite3.connect(database) as connection:
        connection.executescript(schema.read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        with (ARCHIVE / season / "players_raw.csv").open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if row["element_type"] == "5":
                    continue
                player_id = connection.execute(
                    "INSERT INTO players (display_name) VALUES (?) RETURNING player_id", (row["code"],)
                ).fetchone()[0]
                connection.executemany(
                    "INSERT INTO player_source_ids VALUES (?, ?, ?, ?)",
                    [("fpl.element.id", f"premier-league:{season}", row["id"], player_id),
                     ("fpl.element.code", f"premier-league:{season}", row["code"], player_id)],
                )
    assert load_player_gameweek_teams(season, ARCHIVE, database).player_team_rows > 0
    return database


def _state(database: Path):
    with sqlite3.connect(database) as connection:
        links_exist = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name = 'fixture_gameweeks' AND type = 'table'"
        ).fetchone()
        return (
            connection.execute("SELECT * FROM fixtures ORDER BY fixture_id").fetchall(),
            connection.execute("SELECT * FROM fixture_source_ids ORDER BY source_id").fetchall(),
            connection.execute("SELECT * FROM fixture_gameweeks ORDER BY fixture_id").fetchall()
            if links_exist else [],
        )


def test_full_saved_season_loads_and_repeats_without_changing_matches(tmp_path: Path) -> None:
    database = _database(tmp_path)
    result = load_canonical_fixtures(SEASON, ARCHIVE, database)
    assert result == CanonicalFixturesSummary(SEASON, 380)
    before = _state(database)
    assert load_canonical_fixtures(SEASON, ARCHIVE, database) == result
    assert _state(database) == before
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT count(DISTINCT home_team_id) FROM fixtures").fetchone() == (20,)
        assert connection.execute("SELECT count(DISTINCT away_team_id) FROM fixtures").fetchone() == (20,)
        assert connection.execute("SELECT count(*) FROM fixtures WHERE status='finished' "
                                  "AND home_goals IS NOT NULL AND away_goals IS NOT NULL "
                                  "AND kickoff_at IS NOT NULL AND match_date IS NULL").fetchone() == (380,)
        assert connection.execute("SELECT count(*) FROM fixture_source_ids WHERE source_namespace=? "
                                  "AND source_scope=?", ("fpl.fixture.id", "premier-league:2025-26")).fetchone() == (380,)
        assert connection.execute(
            "SELECT count(*), count(DISTINCT fg.fixture_id), count(DISTINCT g.gameweek_number) "
            "FROM fixture_gameweeks fg JOIN gameweeks g USING (gameweek_id)"
        ).fetchone() == (380, 380, 38)
        assert connection.execute(
            "SELECT count(*) FROM fixture_gameweeks fg JOIN fixtures f USING (fixture_id) "
            "JOIN gameweeks g USING (gameweek_id) WHERE f.season_id != g.season_id"
        ).fetchone() == (0,)


@pytest.mark.parametrize("season", [
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21", "2021-22",
    "2022-23", "2023-24", "2024-25", "2026-27",
])
def test_other_saved_seasons_match_source_gameweeks(tmp_path: Path, season: str) -> None:
    database = _database(tmp_path, season)
    if season == "2016-17":
        with sqlite3.connect(database) as connection:
            connection.execute(FIXTURE_GAMEWEEKS_SQL)  # An older season must load alongside this table.
    count = 10 if season == "2026-27" else 380
    weeks = 1 if season == "2026-27" else 37 if season == "2022-23" else 38
    assert load_canonical_fixtures(season, ARCHIVE, database) == CanonicalFixturesSummary(season, count)
    before = _state(database)
    assert load_canonical_fixtures(season, ARCHIVE, database) == CanonicalFixturesSummary(season, count)
    assert _state(database) == before
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM fixtures").fetchone() == (count,)
        assert connection.execute("SELECT count(*) FROM fixture_source_ids").fetchone() == (count,)
        assert connection.execute("SELECT count(*), count(DISTINCT g.gameweek_number) "
                                  "FROM fixture_gameweeks fg JOIN gameweeks g USING(gameweek_id)").fetchone() == (count, weeks)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_existing_fixtures_get_their_week_links_without_new_fixture_ids(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_canonical_fixtures(SEASON, ARCHIVE, database)
    before = _state(database)
    with sqlite3.connect(database) as connection:
        connection.execute("DROP TABLE fixture_gameweeks")  # Simulate a volume loaded by the earlier command.
    assert load_canonical_fixtures(SEASON, ARCHIVE, database) == CanonicalFixturesSummary(SEASON, 380)
    assert _state(database) == before


def test_repeat_fixture_load_preserves_backfilled_match_dates(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_canonical_fixtures(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE fixtures SET match_date = substr(kickoff_at, 1, 10)")
    before = _state(database)
    assert load_canonical_fixtures(SEASON, ARCHIVE, database) == CanonicalFixturesSummary(SEASON, 380)
    assert _state(database) == before


def test_partial_gameweek_links_are_rejected_without_changes(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_canonical_fixtures(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM fixture_gameweeks WHERE fixture_id = 1")
    before = _state(database)
    with pytest.raises(CanonicalFixturesError, match="fixture/gameweek links differ"):
        load_canonical_fixtures(SEASON, ARCHIVE, database)
    assert _state(database) == before


def test_partial_or_changed_existing_fixture_is_rejected_without_new_writes(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_canonical_fixtures(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM fixture_source_ids WHERE source_id='1'")
    before = _state(database)
    with pytest.raises(CanonicalFixturesError, match="Existing season fixtures"):
        load_canonical_fixtures(SEASON, ARCHIVE, database)
    assert _state(database) == before
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO fixture_source_ids VALUES ('fpl.fixture.id', 'premier-league:2025-26', '1', 1)")
        connection.execute("UPDATE fixtures SET home_goals = home_goals + 1 WHERE fixture_id = 1")
    before = _state(database)
    with pytest.raises(CanonicalFixturesError, match="Existing season fixtures"):
        load_canonical_fixtures(SEASON, ARCHIVE, database)
    assert _state(database) == before


def test_refuses_unreviewed_season_or_uncertain_results(tmp_path: Path) -> None:
    with pytest.raises(CanonicalFixturesError, match="Only saved 2016-17 through 2026-27"):
        load_canonical_fixtures("2015-16", ARCHIVE, tmp_path / "missing.db")
    folder = tmp_path / "2025-26"
    folder.mkdir()
    (folder / "fixtures.csv").write_text(
        "id,team_h,team_a,event,kickoff_time,finished,started,finished_provisional,minutes,team_h_score,team_a_score\n"
        "1,1,2,1,2025-08-15T19:00:00Z,True,True,True,90,,2\n", encoding="utf-8",
    )
    with pytest.raises(ValueError, match="home goals"):
        _fixtures(folder, {"1": "arsenal", "2": "aston-villa"})


def test_fixture_kickoff_and_database_gameweeks_must_agree(tmp_path: Path) -> None:
    folder = ARCHIVE / SEASON
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    source_teams = _source_teams(folder, aliases)
    fixtures = _fixtures(folder, source_teams)
    first = next(iter(fixtures))
    changed = dict(fixtures)
    original = fixtures[first]
    changed[first] = (original[0], original[1], "2025-08-15T00:00:00Z", *original[3:])
    with pytest.raises(CanonicalFixturesError, match="Fixture/gameweek evidence differs"):
        _expected_assignments(folder, source_teams, aliases, changed)
    changed[first] = (*original[:-2], original[-2] + 1, original[-1])
    with pytest.raises(CanonicalFixturesError, match="Fixture/gameweek score differs"):
        _expected_assignments(folder, source_teams, aliases, changed)

    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE player_gameweek_teams SET source_element_id = '99999' "
                           "WHERE rowid = (SELECT rowid FROM player_gameweek_teams LIMIT 1)")
    with pytest.raises(CanonicalFixturesError, match="Existing player/team/week assignments differ"):
        load_canonical_fixtures(SEASON, ARCHIVE, database)
    assert _state(database) == ([], [], [])


def test_cli_forwards_season_and_uses_write_enabled_data_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load(season, archive_root, database_path):
        assert season == SEASON
        assert archive_root.name == "fpl_archive_vaastav"
        return CanonicalFixturesSummary(season, 380)

    monkeypatch.setattr(cli, "load_canonical_fixtures", fake_load)
    result = CliRunner().invoke(cli.app, ["ingest", "canonical-fixtures", "--season", SEASON])
    assert result.exit_code == 0, result.output
    assert "Loaded 380 canonical fixtures" in result.output
    command = compose_runner.build_compose_command(["ingest", "canonical-fixtures", "--season", SEASON])
    assert command[command.index("--user") + 1] == "0:0"


def _player_fixture_observation_database(tmp_path: Path) -> Path:
    database = _database(tmp_path)
    assert load_canonical_fixtures(SEASON, ARCHIVE, database) == CanonicalFixturesSummary(SEASON, 380)
    return database


@pytest.mark.parametrize("season", [
    "2016-17", "2017-18", "2018-19", "2019-20", "2020-21",
    "2021-22", "2022-23", "2023-24", "2024-25", "2025-26",
])
def test_each_saved_archive_season_loads_complete_player_fixture_rows_and_repeats(
    tmp_path: Path, season: str
) -> None:
    database = _database(tmp_path, season)
    assert load_canonical_fixtures(season, ARCHIVE, database).fixture_count == 380
    folder = ARCHIVE / season
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    source_teams = _source_teams(folder, aliases)
    _, source_observations = _observations(folder, source_teams, aliases)
    excluded = 59 if season == "2019-20" else 0
    expected_rows = [
        observation for observation in source_observations
        if not (
            season == "2019-20"
            and observation[2] == 29
            and observation[4] == "2020-03-11T19:30:00Z"
            and observation[6] == "275"
        )
    ]
    assert len(source_observations) - len(expected_rows) == excluded

    result = load_player_fixture_observations(season, ARCHIVE, database)
    assert result == PlayerFixtureObservationsSummary(
        season,
        380,
        len(expected_rows),
        sum(observation[5] > 0 for observation in expected_rows),
    )
    scope = f"premier-league:{season}"
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT observation.* FROM player_fixture_observations observation "
            "JOIN fixtures f USING (fixture_id) WHERE f.season_id = "
            "(SELECT season_id FROM seasons WHERE label = ?) ORDER BY observation.fixture_id, observation.player_id",
            (season,),
        ).fetchall()
        assert len(rows) == result.observation_count
        assert connection.execute(
            "SELECT count(*) FROM player_fixture_observation_fixtures log "
            "JOIN fixtures f USING (fixture_id) WHERE f.season_id = "
            "(SELECT season_id FROM seasons WHERE label = ?)",
            (season,),
        ).fetchone() == (380,)
        if season == "2019-20":
            postponed_rows = connection.execute(
                "SELECT count(*) FROM player_fixture_observations observation "
                "JOIN fixture_source_ids fs ON fs.fixture_id = observation.fixture_id "
                "JOIN gameweeks g ON g.gameweek_id = observation.gameweek_id "
                "WHERE fs.source_namespace=? AND fs.source_scope=? AND fs.source_id='275' "
                "AND g.gameweek_number=29",
                (FIXTURE_NAMESPACE, scope),
            ).fetchone()[0]
            resumed_rows = connection.execute(
                "SELECT count(*) FROM player_fixture_observations observation "
                "JOIN fixture_source_ids fs ON fs.fixture_id = observation.fixture_id "
                "JOIN gameweeks g ON g.gameweek_id = observation.gameweek_id "
                "WHERE fs.source_namespace=? AND fs.source_scope=? AND fs.source_id='275' "
                "AND g.gameweek_number=39",
                (FIXTURE_NAMESPACE, scope),
            ).fetchone()[0]
            expected_resumed_rows = sum(
                observation[6] == "275" and observation[2] == 39
                for observation in source_observations
            )
            assert postponed_rows == 0
            assert resumed_rows == expected_resumed_rows > 0
        before = rows

    assert load_player_fixture_observations(season, ARCHIVE, database) == result
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT observation.* FROM player_fixture_observations observation "
            "JOIN fixtures f USING (fixture_id) WHERE f.season_id = "
            "(SELECT season_id FROM seasons WHERE label = ?) ORDER BY observation.fixture_id, observation.player_id",
            (season,),
        ).fetchall() == before


def test_full_season_player_fixture_observations_include_listings_and_repeat(tmp_path: Path) -> None:
    database = _player_fixture_observation_database(tmp_path)
    folder = ARCHIVE / SEASON
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    source_teams = _source_teams(folder, aliases)
    _, observations = _observations(folder, source_teams, aliases)

    result = load_player_fixture_observations(SEASON, ARCHIVE, database)
    assert result == PlayerFixtureObservationsSummary(
        SEASON,
        380,
        len(observations),
        sum(minutes > 0 for _, _, _, _, _, minutes, _ in observations),
    )
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='player_fixture_observations'"
        ).fetchone() == (PLAYER_FIXTURE_OBSERVATIONS_SQL,)
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' "
            "AND name='idx_player_fixture_observations_player'"
        ).fetchone() == (PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL,)
        assert connection.execute(
            "SELECT count(*), sum(minutes > 0) FROM player_fixture_observations"
        ).fetchone() == (result.observation_count, result.appearance_count)
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            "AND name='player_fixture_observation_fixtures'"
        ).fetchone() == (PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL,)
        assert connection.execute(
            "SELECT count(*) FROM player_fixture_observation_fixtures"
        ).fetchone() == (result.fixture_count,)
        saliba = connection.execute(
            "SELECT fs.source_id, g.gameweek_number, observation.minutes, t.team_key "
            "FROM player_fixture_observations observation "
            "JOIN fixture_source_ids fs ON fs.fixture_id = observation.fixture_id "
            "JOIN gameweeks g ON g.gameweek_id = observation.gameweek_id "
            "JOIN teams t ON t.team_id = observation.team_id "
            "WHERE fs.source_namespace = ? AND fs.source_scope = ? "
            "AND fs.source_id IN ('252', '310') AND observation.source_element_id = '6' "
            "ORDER BY fs.source_id",
            (FIXTURE_NAMESPACE, FIXTURE_SCOPE),
        ).fetchall()
        assert saliba == [
            ("252", 26, 0, "arsenal"),
            ("310", 26, 90, "arsenal"),
        ]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    # A different season's row must survive a repeat rather than being replaced.
    with sqlite3.connect(database) as connection:
        competition_id = connection.execute(
            "SELECT competition_id FROM competitions WHERE competition_key='premier-league'"
        ).fetchone()[0]
        other_season_id = connection.execute(
            "INSERT INTO seasons (competition_id, label, start_year, end_year) "
            "VALUES (?, '2024-25', 2024, 2025) RETURNING season_id",
            (competition_id,),
        ).fetchone()[0]
        other_week_id = connection.execute(
            "INSERT INTO gameweeks (season_id, gameweek_number) VALUES (?, 1) RETURNING gameweek_id",
            (other_season_id,),
        ).fetchone()[0]
        team_ids = dict(
            connection.execute(
                "SELECT team_key, team_id FROM teams WHERE team_key IN ('arsenal', 'aston-villa')"
            ).fetchall()
        )
        arsenal_id, villa_id = team_ids["arsenal"], team_ids["aston-villa"]
        saliba_id = connection.execute(
            "SELECT player_id FROM player_source_ids "
            "WHERE source_namespace=? AND source_scope=? AND source_id='6'",
            (ID_NAMESPACE, FIXTURE_SCOPE),
        ).fetchone()[0]
        other_fixture_id = connection.execute(
            "INSERT INTO fixtures (season_id, home_team_id, away_team_id, kickoff_at, status, home_goals, away_goals) "
            "VALUES (?, ?, ?, '2024-08-16T19:00:00Z', 'finished', 1, 0) RETURNING fixture_id",
            (other_season_id, arsenal_id, villa_id),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO player_fixture_observations "
            "(fixture_id, player_id, team_id, gameweek_id, source_element_id, minutes) "
            "VALUES (?, ?, ?, ?, '6', 1)",
            (other_fixture_id, saliba_id, arsenal_id, other_week_id),
        )
        before = connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall()
    assert load_player_fixture_observations(SEASON, ARCHIVE, database) == result
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall() == before


@pytest.mark.parametrize("change", ["partial", "conflicting"])
def test_partial_or_conflicting_observations_are_rejected_without_changes(
    tmp_path: Path, change: str
) -> None:
    database = _player_fixture_observation_database(tmp_path)
    load_player_fixture_observations(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        fixture_id = connection.execute(
            "SELECT fixture_id FROM fixture_source_ids WHERE source_namespace=? "
            "AND source_scope=? AND source_id='252'",
            (FIXTURE_NAMESPACE, FIXTURE_SCOPE),
        ).fetchone()[0]
        player_id = connection.execute(
            "SELECT player_id FROM player_source_ids WHERE source_namespace=? "
            "AND source_scope=? AND source_id='6'",
            (ID_NAMESPACE, FIXTURE_SCOPE),
        ).fetchone()[0]
        if change == "partial":
            connection.execute(
                "DELETE FROM player_fixture_observations WHERE fixture_id=? AND player_id=?",
                (fixture_id, player_id),
            )
        else:
            connection.execute(
                "UPDATE player_fixture_observations SET minutes=1 WHERE fixture_id=? AND player_id=?",
                (fixture_id, player_id),
            )
        before = connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall()

    with pytest.raises(PlayerFixtureObservationsError, match="Existing player/fixture observations"):
        load_player_fixture_observations(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT * FROM player_fixture_observations ORDER BY fixture_id, player_id"
        ).fetchall() == before


@pytest.mark.parametrize("missing", ["player-id", "player-code", "fixture-id", "fixture-week-link"])
def test_missing_source_mapping_or_fixture_week_link_is_rejected_before_schema_creation(
    tmp_path: Path, missing: str
) -> None:
    database = _player_fixture_observation_database(tmp_path)
    with sqlite3.connect(database) as connection:
        if missing in {"player-id", "player-code"}:
            namespace = ID_NAMESPACE if missing == "player-id" else CODE_NAMESPACE
            if missing == "player-id":
                source_id = "6"
            else:
                source_id = connection.execute(
                    "SELECT source_id FROM player_source_ids WHERE source_namespace=? "
                    "AND source_scope=? AND player_id=(SELECT player_id FROM player_source_ids "
                    "WHERE source_namespace=? AND source_scope=? AND source_id='6')",
                    (CODE_NAMESPACE, FIXTURE_SCOPE, ID_NAMESPACE, FIXTURE_SCOPE),
                ).fetchone()[0]
            connection.execute(
                "DELETE FROM player_source_ids WHERE source_namespace=? AND source_scope=? AND source_id=?",
                (namespace, FIXTURE_SCOPE, source_id),
            )
        elif missing == "fixture-id":
            connection.execute(
                "DELETE FROM fixture_source_ids WHERE source_namespace=? AND source_scope=? AND source_id='1'",
                (FIXTURE_NAMESPACE, FIXTURE_SCOPE),
            )
        else:
            fixture_id = connection.execute(
                "SELECT fixture_id FROM fixture_source_ids WHERE source_namespace=? "
                "AND source_scope=? AND source_id='1'",
                (FIXTURE_NAMESPACE, FIXTURE_SCOPE),
            ).fetchone()[0]
            connection.execute("DELETE FROM fixture_gameweeks WHERE fixture_id=?", (fixture_id,))
    before = _state(database)

    with pytest.raises(PlayerFixtureObservationsError):
        load_player_fixture_observations(SEASON, ARCHIVE, database)
    assert _state(database) == before
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_fixture_observations'"
        ).fetchone() is None
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' "
            "AND name='player_fixture_observation_fixtures'"
        ).fetchone() is None


def test_player_fixture_observations_cli_routes_saved_archive_to_write_enabled_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw_root = tmp_path / "raw"
    summary = PlayerFixtureObservationsSummary(SEASON, 380, 123, 100)
    calls = []

    def fake_load(season, archive_root, database_path):
        calls.append((season, archive_root, database_path))
        return summary

    monkeypatch.setattr(cli, "load_player_fixture_observations", fake_load)
    result = CliRunner().invoke(
        cli.app,
        ["ingest", "player-fixture-observations", "--season", SEASON, "--raw-root", str(raw_root)],
    )
    assert result.exit_code == 0, result.output
    assert "Loaded 123 player/fixture observations" in result.output
    assert calls == [(SEASON, raw_root / "fpl_archive_vaastav", cli.DATABASE_PATH)]
    command = compose_runner.build_compose_command(
        ["ingest", "player-fixture-observations", "--season", SEASON]
    )
    assert command[command.index("--user") + 1] == "0:0"


def test_player_fixture_observations_rejects_unreviewed_seasons_before_opening_database(
    tmp_path: Path,
) -> None:
    database = tmp_path / "not-created.db"
    with pytest.raises(PlayerFixtureObservationsError, match="2016-17 through 2026-27"):
        load_player_fixture_observations("2027-28", ARCHIVE, database)
    assert not database.exists()


def test_existing_player_fixture_observation_schema_must_match_exact_ddl(tmp_path: Path) -> None:
    database = _player_fixture_observation_database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "CREATE TABLE player_fixture_observations (fixture_id INTEGER PRIMARY KEY)"
        )
    with pytest.raises(PlayerFixtureObservationsError, match="schema differs"):
        load_player_fixture_observations(SEASON, ARCHIVE, database)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='player_fixture_observations'"
        ).fetchone() == ("CREATE TABLE player_fixture_observations (fixture_id INTEGER PRIMARY KEY)",)
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_player_fixture_observations_player'"
        ).fetchone() is None
