"""Load saved FPL player listings for each validated canonical fixture."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .canonical_fixtures import (
    FIXTURE_GAMEWEEKS_SQL,
    NAMESPACE as FIXTURE_NAMESPACE,
    CanonicalFixturesError,
    _expected_assignments,
    _fixtures,
    _group_assignments,
)
from .canonical_players import CODE_NAMESPACE, ID_NAMESPACE
from .canonical_teams import (
    COMPETITION_KEY,
    COMPETITION_NAME,
    TEAM_REFERENCE_PATH,
    CanonicalTeamsValidationError,
    _read_clubs,
)
from .player_gameweek_teams import (
    GameweekTeamsError,
    _observations,
    _source_teams,
)
from .official_fpl_season import OfficialFplSeasonError, read_official_fpl_season
from .sqlite import DATABASE_PATH, connect_database

ARCHIVE_SEASONS = {f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2026)}
OFFICIAL_SEASON = "2026-27"
SUPPORTED_SEASONS = ARCHIVE_SEASONS | {OFFICIAL_SEASON}
# Kept as the 2025-26 scope constant for callers that inspect that archived slice.
FIXTURE_SCOPE = f"{COMPETITION_KEY}:2025-26"
PLAYER_FIXTURE_OBSERVATIONS_SQL = """CREATE TABLE player_fixture_observations (
    fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    gameweek_id INTEGER NOT NULL REFERENCES gameweeks(gameweek_id),
    source_element_id TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    PRIMARY KEY (fixture_id, player_id)
) STRICT"""
PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL = (
    "CREATE INDEX idx_player_fixture_observations_player "
    "ON player_fixture_observations(player_id)"
)
PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL = """CREATE TABLE player_fixture_observation_fixtures (
    fixture_id INTEGER PRIMARY KEY REFERENCES fixtures(fixture_id)
) STRICT"""


class PlayerFixtureObservationsError(ValueError):
    """Saved player/fixture evidence differs from existing canonical records."""


@dataclass(frozen=True)
class PlayerFixtureObservationsSummary:
    season: str
    fixture_count: int
    observation_count: int
    appearance_count: int


def _schema(connection: sqlite3.Connection) -> None:
    existing = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'player_fixture_observations'"
    ).fetchone()
    if existing is None:
        connection.execute(PLAYER_FIXTURE_OBSERVATIONS_SQL)
    elif existing[0].strip().rstrip(";") != PLAYER_FIXTURE_OBSERVATIONS_SQL:
        raise PlayerFixtureObservationsError(
            "Existing player_fixture_observations schema differs; manual review required"
        )

    existing_index = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' "
        "AND name = 'idx_player_fixture_observations_player'"
    ).fetchone()
    if existing_index is None:
        connection.execute(PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL)
    elif existing_index[0].strip().rstrip(";") != PLAYER_FIXTURE_OBSERVATIONS_INDEX_SQL:
        raise PlayerFixtureObservationsError(
            "Existing player_fixture_observations player index differs; manual review required"
        )

    fixture_log = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' "
        "AND name = 'player_fixture_observation_fixtures'"
    ).fetchone()
    if fixture_log is None:
        connection.execute(PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL)
    elif fixture_log[0].strip().rstrip(";") != PLAYER_FIXTURE_OBSERVATION_FIXTURES_SQL:
        raise PlayerFixtureObservationsError(
            "Existing player_fixture_observation_fixtures schema differs; manual review required"
        )


def load_player_fixture_observations(
    season: str,
    archive_root: Path,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
    *,
    official_raw_root: Path | None = None,
) -> PlayerFixtureObservationsSummary:
    """Load reviewed archived seasons or append finished official-current observations."""
    if season not in SUPPORTED_SEASONS:
        raise PlayerFixtureObservationsError(
            "Player/fixture observation ingestion is only reviewed for saved 2016-17 through 2026-27"
        )
    if season == OFFICIAL_SEASON and official_raw_root is None:
        raise PlayerFixtureObservationsError(
            "2026-27 player/fixture observations require saved official FPL evidence"
        )
    if season != OFFICIAL_SEASON and official_raw_root is not None:
        raise PlayerFixtureObservationsError(
            "Saved official FPL evidence is only reviewed for 2026-27"
        )

    try:
        clubs, aliases = _read_clubs(Path(reference_path))
        if season == OFFICIAL_SEASON:
            evidence = read_official_fpl_season(Path(official_raw_root), season)
            source_teams = evidence.teams
            fixtures = evidence.fixtures
            elements = evidence.elements
            observations = evidence.observations
            expected_assignments, expected_weeks = _group_assignments(
                observations, fixtures, season
            )
        else:
            folder = Path(archive_root) / season
            source_teams = _source_teams(folder, aliases)
            fixtures = _fixtures(folder, source_teams)
            expected_assignments, expected_weeks = _expected_assignments(
                folder, source_teams, aliases, fixtures
            )
            elements, observations = _observations(folder, source_teams, aliases)
            if season == "2019-20":
                # The archive repeats the postponed GW29 listing for fixture 275.
                # Keep its validated grouped-week evidence, but never attach it to
                # the completed GW39 canonical match.
                postponed = [
                    row for row in observations
                    if row[2] == 29 and row[4] == "2020-03-11T19:30:00Z" and row[6] == "275"
                ]
                if len(postponed) != 59:
                    raise PlayerFixtureObservationsError(
                        "Reviewed 2019-20 postponed fixture 275 must have exactly 59 original GW29 listings"
                    )
                observations = [row for row in observations if row not in postponed]
    except (
        CanonicalFixturesError,
        CanonicalTeamsValidationError,
        GameweekTeamsError,
        OfficialFplSeasonError,
    ) as error:
        raise PlayerFixtureObservationsError(str(error)) from error

    scope = f"{COMPETITION_KEY}:{season}"
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing_tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        required_tables = {
            "competitions",
            "seasons",
            "teams",
            "players",
            "fixtures",
            "player_source_ids",
            "fixture_source_ids",
            "team_source_ids",
            "gameweeks",
            "player_gameweek_teams",
            "fixture_gameweeks",
        }
        missing_tables = required_tables - existing_tables
        if missing_tables:
            raise PlayerFixtureObservationsError(
                f"Required canonical tables missing ({', '.join(sorted(missing_tables))})"
            )

        competition = connection.execute(
            "SELECT competition_id, name FROM competitions WHERE competition_key = ?",
            (COMPETITION_KEY,),
        ).fetchone()
        if competition is None or competition[1] != COMPETITION_NAME:
            raise PlayerFixtureObservationsError("Existing Premier League competition differs or is missing")
        competition_id = competition[0]
        season_row = connection.execute(
            "SELECT season_id, start_year, end_year FROM seasons "
            "WHERE competition_id = ? AND label = ?",
            (competition_id, season),
        ).fetchone()
        start_year = int(season[:4])
        if season_row is None or season_row[1:] != (start_year, start_year + 1):
            raise PlayerFixtureObservationsError(
                f"Load canonical teams, players, gameweeks and fixtures for {season} first"
            )
        season_id = season_row[0]

        canonical_teams = {
            key: (team_id, name)
            for team_id, key, name in connection.execute(
                "SELECT team_id, team_key, name FROM teams"
            )
        }
        if any(canonical_teams.get(key, (None, None))[1] != name for key, name in clubs):
            raise PlayerFixtureObservationsError(
                "Canonical clubs differ from reviewed team reference"
            )

        if season == OFFICIAL_SEASON:
            existing_team_mappings = dict(
                connection.execute(
                    "SELECT source_id, team_id FROM team_source_ids "
                    "WHERE source_namespace = 'fpl.team.id' AND source_scope = ?",
                    (scope,),
                )
            )
            expected_team_mappings = {
                source_id: canonical_teams[key][0]
                for source_id, key in source_teams.items()
            }
            if existing_team_mappings != expected_team_mappings:
                raise PlayerFixtureObservationsError(
                    "Existing official FPL team mappings differ from reviewed canonical teams"
                )

        fixture_schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'fixture_gameweeks'"
        ).fetchone()
        if fixture_schema is None or fixture_schema[0].strip().rstrip(";") != FIXTURE_GAMEWEEKS_SQL:
            raise PlayerFixtureObservationsError(
                "Existing fixture_gameweeks schema differs; manual review required"
            )

        # Every archive fixture must already resolve to exactly one canonical fixture,
        # with the same saved teams, kickoff, event and final score.
        fixture_mappings = dict(
            connection.execute(
                "SELECT source_id, fixture_id FROM fixture_source_ids "
                "WHERE source_namespace = ? AND source_scope = ?",
                (FIXTURE_NAMESPACE, scope),
            )
        )
        season_fixtures = {
            row[0]
            for row in connection.execute(
                "SELECT fixture_id FROM fixtures WHERE season_id = ?", (season_id,)
            )
        }
        if (
            set(fixture_mappings) != set(fixtures)
            or set(fixture_mappings.values()) != season_fixtures
            or len(fixture_mappings) != len(season_fixtures)
        ):
            raise PlayerFixtureObservationsError(
                "Existing season fixture mappings are missing, partial or changed"
            )

        actual_fixtures = {
            source_id: (
                fixture_id,
                found_season_id,
                home_team_id,
                away_team_id,
                kickoff,
                status,
                home_goals,
                away_goals,
            )
            for (
                source_id,
                fixture_id,
                found_season_id,
                home_team_id,
                away_team_id,
                kickoff,
                status,
                home_goals,
                away_goals,
            ) in connection.execute(
                "SELECT fs.source_id, f.fixture_id, f.season_id, f.home_team_id, f.away_team_id, "
                "f.kickoff_at, f.status, f.home_goals, f.away_goals "
                "FROM fixture_source_ids fs JOIN fixtures f USING (fixture_id) "
                "WHERE fs.source_namespace = ? AND fs.source_scope = ?",
                (FIXTURE_NAMESPACE, scope),
            )
        }
        expected_fixtures = {
            source_id: (
                fixture_mappings[source_id],
                season_id,
                canonical_teams[home][0],
                canonical_teams[away][0],
                kickoff,
                "finished",
                home_goals,
                away_goals,
            )
            for source_id, (home, away, kickoff, _, home_goals, away_goals) in fixtures.items()
        }
        if actual_fixtures != expected_fixtures:
            raise PlayerFixtureObservationsError(
                "Existing season fixture facts differ from saved archive evidence"
            )

        week_ids = dict(
            connection.execute(
                "SELECT gameweek_number, gameweek_id FROM gameweeks WHERE season_id = ?",
                (season_id,),
            )
        )
        if set(week_ids) != expected_weeks:
            raise PlayerFixtureObservationsError(
                "Existing season gameweeks are missing, partial or changed"
            )
        expected_fixture_weeks = {
            (fixture_mappings[source_id], week_ids[fixture_facts[3]])
            for source_id, fixture_facts in fixtures.items()
        }
        actual_fixture_weeks = set(
            connection.execute(
                "SELECT fg.fixture_id, fg.gameweek_id FROM fixture_gameweeks fg "
                "JOIN fixtures f USING (fixture_id) WHERE f.season_id = ?",
                (season_id,),
            )
        )
        if actual_fixture_weeks != expected_fixture_weeks:
            raise PlayerFixtureObservationsError(
                "Existing fixture/gameweek links differ from saved archive evidence"
            )

        # Both season-scoped source identities must resolve to the same canonical
        # player for every saved football player; managers have no player mapping.
        player_mappings = {
            (namespace, source_id): player_id
            for namespace, source_id, player_id in connection.execute(
                "SELECT source_namespace, source_id, player_id FROM player_source_ids "
                "WHERE source_scope = ? AND source_namespace IN (?, ?)",
                (scope, ID_NAMESPACE, CODE_NAMESPACE),
            )
        }
        football_elements = {element: code for element, code in elements.items() if code is not None}
        expected_mapping_keys = {
            (namespace, source_id)
            for element, code in football_elements.items()
            for namespace, source_id in ((ID_NAMESPACE, element), (CODE_NAMESPACE, code))
        }
        if len(expected_mapping_keys) != 2 * len(football_elements) or set(player_mappings) != expected_mapping_keys:
            raise PlayerFixtureObservationsError(
                "Existing season FPL player ID/code mappings are missing, partial or changed"
            )
        players_by_element: dict[str, int] = {}
        for element, code in football_elements.items():
            player_id = player_mappings[(ID_NAMESPACE, element)]
            if player_id != player_mappings[(CODE_NAMESPACE, code)]:
                raise PlayerFixtureObservationsError(
                    f"Conflicting FPL player ID/code mapping for element {element}"
                )
            players_by_element[element] = player_id
        if len(set(players_by_element.values())) != len(players_by_element):
            raise PlayerFixtureObservationsError(
                "Multiple FPL elements map to one canonical player"
            )

        actual_assignments = connection.execute(
            "SELECT g.gameweek_number, p.source_element_id, t.team_key, p.first_kickoff_at, "
            "p.last_kickoff_at, p.fixture_observations, p.fixtures_with_minutes "
            "FROM player_gameweek_teams p JOIN gameweeks g USING (gameweek_id) "
            "JOIN teams t USING (team_id) WHERE g.season_id = ?",
            (season_id,),
        ).fetchall()
        if len(actual_assignments) != len(expected_assignments) or set(actual_assignments) != expected_assignments:
            raise PlayerFixtureObservationsError(
                "Existing player/team/week assignments differ from saved fixture evidence"
            )

        desired_rows: dict[tuple[int, int], tuple[int, int, int, int, str, int]] = {}
        for element, _, week, club, _, minutes, source_fixture_id in observations:
            fixture_id = fixture_mappings.get(source_fixture_id)
            player_id = players_by_element.get(element)
            if fixture_id is None or player_id is None:
                raise PlayerFixtureObservationsError(
                    f"Missing fixture or player mapping for observation {source_fixture_id}:{element}"
                )
            values = (
                fixture_id,
                player_id,
                canonical_teams[club][0],
                week_ids[week],
                element,
                minutes,
            )
            key = (fixture_id, player_id)
            previous = desired_rows.get(key)
            if previous is not None and previous != values:
                raise PlayerFixtureObservationsError(
                    f"Conflicting repeated player/fixture observation {source_fixture_id}:{element}"
                )
            desired_rows[key] = values

        existing_fixture_log = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'player_fixture_observation_fixtures'"
        ).fetchone() is not None
        _schema(connection)
        existing_observations = connection.execute(
            "SELECT o.fixture_id, o.player_id, o.team_id, o.gameweek_id, "
            "o.source_element_id, o.minutes FROM player_fixture_observations o "
            "JOIN fixtures f USING (fixture_id) WHERE f.season_id = ?",
            (season_id,),
        ).fetchall()
        existing_by_key = {
            (row[0], row[1]): row for row in existing_observations
        }
        recorded_fixtures = {
            row[0]
            for row in connection.execute(
                "SELECT log.fixture_id FROM player_fixture_observation_fixtures log "
                "JOIN fixtures f USING (fixture_id) WHERE f.season_id = ?",
                (season_id,),
            )
        }
        desired_fixture_ids = {values[0] for values in desired_rows.values()}
        existing_observation_fixture_ids = {row[0] for row in existing_observations}
        if season != OFFICIAL_SEASON:
            if recorded_fixtures and recorded_fixtures != desired_fixture_ids:
                raise PlayerFixtureObservationsError(
                    "Existing archived player/fixture completion records are partial or changed"
                )
            if existing_observations and set(existing_observations) != set(desired_rows.values()):
                raise PlayerFixtureObservationsError(
                    "Existing player/fixture observations are partial or differ; manual review required"
                )
            additions = [] if existing_observations else list(desired_rows.values())
            fixture_markers_to_add = desired_fixture_ids - recorded_fixtures
        else:
            # The fixture log distinguishes a newly finished match from a complete
            # old match whose player rows were all removed. Existing logged fixtures
            # must be unchanged; only unlogged, newly finished fixtures can append.
            if not existing_fixture_log and existing_observations:
                if set(existing_observations) != set(desired_rows.values()):
                    raise PlayerFixtureObservationsError(
                        "Official fixture completion records are missing; existing rows cannot be safely extended"
                    )
                fixture_markers_to_add = desired_fixture_ids
                additions = []
            else:
                if not existing_observation_fixture_ids <= recorded_fixtures:
                    raise PlayerFixtureObservationsError(
                        "Official player/fixture observations lack completion records"
                    )
                if not recorded_fixtures <= desired_fixture_ids:
                    raise PlayerFixtureObservationsError(
                        "A previously loaded official fixture is missing from saved evidence"
                    )
                for fixture_id in recorded_fixtures:
                    old_slice = {
                        key: row for key, row in existing_by_key.items() if key[0] == fixture_id
                    }
                    expected_slice = {
                        key: row for key, row in desired_rows.items() if key[0] == fixture_id
                    }
                    if old_slice != expected_slice:
                        raise PlayerFixtureObservationsError(
                            "Existing official player/fixture observations are missing, partial or changed"
                        )
                fixture_markers_to_add = desired_fixture_ids - recorded_fixtures
                additions = [
                    row for key, row in desired_rows.items() if key[0] in fixture_markers_to_add
                ]

        if additions:
            connection.executemany(
                "INSERT INTO player_fixture_observations "
                "(fixture_id, player_id, team_id, gameweek_id, source_element_id, minutes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                sorted(additions),
            )
        if fixture_markers_to_add:
            connection.executemany(
                "INSERT INTO player_fixture_observation_fixtures (fixture_id) VALUES (?)",
                ((fixture_id,) for fixture_id in sorted(fixture_markers_to_add)),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return PlayerFixtureObservationsSummary(
        season,
        len(fixtures),
        len(desired_rows),
        sum(values[-1] > 0 for values in desired_rows.values()),
    )
