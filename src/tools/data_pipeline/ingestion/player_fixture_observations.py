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
    _csv,
    _observations,
    _positive,
    _source_teams,
)
from .official_fpl_season import OfficialFplSeasonError, read_official_fpl_season
from .sqlite import DATABASE_PATH, connect_database

ARCHIVE_SEASONS = {f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2026)}
OFFICIAL_SEASON = "2026-27"
SUPPORTED_SEASONS = ARCHIVE_SEASONS | {OFFICIAL_SEASON}
# Kept as the 2025-26 scope constant for callers that inspect that archived slice.
FIXTURE_SCOPE = f"{COMPETITION_KEY}:2025-26"
_LEGACY_OBSERVATIONS_SQL = """CREATE TABLE player_fixture_observations (
    fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    gameweek_id INTEGER NOT NULL REFERENCES gameweeks(gameweek_id),
    source_element_id TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes >= 0),
    PRIMARY KEY (fixture_id, player_id)
) STRICT"""
_STAT_COLUMN_DEFS = (
    ("goals_scored", "INTEGER CHECK (goals_scored IS NULL OR goals_scored >= 0)"),
    ("assists", "INTEGER CHECK (assists IS NULL OR assists >= 0)"),
    ("clean_sheets", "INTEGER CHECK (clean_sheets IS NULL OR clean_sheets >= 0)"),
    ("goals_conceded", "INTEGER CHECK (goals_conceded IS NULL OR goals_conceded >= 0)"),
    ("own_goals", "INTEGER CHECK (own_goals IS NULL OR own_goals >= 0)"),
    ("penalties_saved", "INTEGER CHECK (penalties_saved IS NULL OR penalties_saved >= 0)"),
    ("penalties_missed", "INTEGER CHECK (penalties_missed IS NULL OR penalties_missed >= 0)"),
    ("yellow_cards", "INTEGER CHECK (yellow_cards IS NULL OR yellow_cards >= 0)"),
    ("red_cards", "INTEGER CHECK (red_cards IS NULL OR red_cards >= 0)"),
    ("saves", "INTEGER CHECK (saves IS NULL OR saves >= 0)"),
    ("bonus", "INTEGER CHECK (bonus IS NULL OR bonus >= 0)"),
    ("bps", "INTEGER"),
    ("total_points", "INTEGER"),
    ("starts", "INTEGER CHECK (starts IS NULL OR starts IN (0, 1))"),
    ("tackles", "INTEGER CHECK (tackles IS NULL OR tackles >= 0)"),
    ("recoveries", "INTEGER CHECK (recoveries IS NULL OR recoveries >= 0)"),
    ("clearances_blocks_interceptions", "INTEGER CHECK (clearances_blocks_interceptions IS NULL OR clearances_blocks_interceptions >= 0)"),
    ("defensive_contribution", "INTEGER CHECK (defensive_contribution IS NULL OR defensive_contribution >= 0)"),
    ("influence", "REAL CHECK (influence IS NULL OR influence >= 0)"),
    ("creativity", "REAL CHECK (creativity IS NULL OR creativity >= 0)"),
    ("threat", "REAL CHECK (threat IS NULL OR threat >= 0)"),
    ("ict_index", "REAL CHECK (ict_index IS NULL OR ict_index >= 0)"),
    ("expected_goals", "REAL CHECK (expected_goals IS NULL OR expected_goals >= 0)"),
    ("expected_assists", "REAL CHECK (expected_assists IS NULL OR expected_assists >= 0)"),
    ("expected_goal_involvements", "REAL CHECK (expected_goal_involvements IS NULL OR expected_goal_involvements >= 0)"),
    ("expected_goals_conceded", "REAL CHECK (expected_goals_conceded IS NULL OR expected_goals_conceded >= 0)"),
    ("expected_points", "REAL"),
    ("value", "INTEGER CHECK (value IS NULL OR value >= 0)"),
    ("selected", "INTEGER CHECK (selected IS NULL OR selected >= 0)"),
    ("transfers_in", "INTEGER CHECK (transfers_in IS NULL OR transfers_in >= 0)"),
    ("transfers_out", "INTEGER CHECK (transfers_out IS NULL OR transfers_out >= 0)"),
    ("transfers_balance", "INTEGER"),
)
_STAT_COLUMNS = tuple(name for name, _ in _STAT_COLUMN_DEFS)
_BASE_COLUMNS = ("fixture_id", "player_id", "team_id", "gameweek_id", "source_element_id", "minutes")
_ALL_COLUMNS = (*_BASE_COLUMNS, *_STAT_COLUMNS)
PLAYER_FIXTURE_OBSERVATIONS_SQL = (
    "CREATE TABLE player_fixture_observations (\n"
    "    fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),\n"
    "    player_id INTEGER NOT NULL REFERENCES players(player_id),\n"
    "    team_id INTEGER NOT NULL REFERENCES teams(team_id),\n"
    "    gameweek_id INTEGER NOT NULL REFERENCES gameweeks(gameweek_id),\n"
    "    source_element_id TEXT NOT NULL,\n"
    "    minutes INTEGER NOT NULL CHECK (minutes >= 0),\n"
    + "".join(f"    {name} {definition},\n" for name, definition in _STAT_COLUMN_DEFS)
    + "    PRIMARY KEY (fixture_id, player_id)\n"
    ") STRICT"
)
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


def _normalize_sql(sql: str) -> str:
    return " ".join(sql.strip().rstrip(";").split())


def _schema(connection: sqlite3.Connection) -> None:
    existing = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'player_fixture_observations'"
    ).fetchone()
    if existing is None:
        connection.execute(PLAYER_FIXTURE_OBSERVATIONS_SQL)
    elif _normalize_sql(existing[0]) == _normalize_sql(PLAYER_FIXTURE_OBSERVATIONS_SQL):
        pass
    elif _normalize_sql(existing[0]) == _normalize_sql(_LEGACY_OBSERVATIONS_SQL):
        # One-time widening of the pre-stats table. New stat columns stay
        # nullable so the populated volume can be backfilled in the same
        # transaction; the loader validates completeness.
        for name, definition in _STAT_COLUMN_DEFS:
            connection.execute(f"ALTER TABLE player_fixture_observations ADD COLUMN {name} {definition}")
        migrated = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'player_fixture_observations'"
        ).fetchone()
        if migrated is None or _normalize_sql(migrated[0]) != _normalize_sql(PLAYER_FIXTURE_OBSERVATIONS_SQL):
            raise PlayerFixtureObservationsError(
                "Player/fixture observations widening failed; manual review required"
            )
    else:
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


_CORE_STAT_FIELDS = (
    "goals_scored",
    "assists",
    "clean_sheets",
    "goals_conceded",
    "own_goals",
    "penalties_saved",
    "penalties_missed",
    "yellow_cards",
    "red_cards",
    "saves",
    "bonus",
    "bps",
)
_OPTIONAL_INT_STAT_FIELDS = (
    "starts",
    "tackles",
    "recoveries",
    "clearances_blocks_interceptions",
    "defensive_contribution",
)
_OPTIONAL_REAL_STAT_FIELDS = (
    "influence",
    "creativity",
    "threat",
    "ict_index",
    "expected_goals",
    "expected_assists",
    "expected_goal_involvements",
    "expected_goals_conceded",
    "expected_points",
)
_OWNERSHIP_STAT_FIELDS = (
    "value",
    "selected",
    "transfers_in",
    "transfers_out",
)


def _parse_stat_int(value: object, field: str, *, allow_null: bool, allow_negative: bool = False) -> int | None:
    if value is None:
        if allow_null:
            return None
        raise PlayerFixtureObservationsError(f"Missing FPL stat {field}")
    text = str(value).strip()
    if text == "":
        if allow_null:
            return None
        raise PlayerFixtureObservationsError(f"Missing FPL stat {field}")
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    if not digits.isascii() or not digits.isdecimal() or str(int(digits)) != digits:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    result = int(text)
    if result < 0 and not allow_negative:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    return result


def _parse_stat_float(value: object, field: str, *, allow_null: bool, allow_negative: bool = False) -> float | None:
    if value is None:
        if allow_null:
            return None
        raise PlayerFixtureObservationsError(f"Missing FPL stat {field}")
    text = str(value).strip()
    if text == "":
        if allow_null:
            return None
        raise PlayerFixtureObservationsError(f"Missing FPL stat {field}")
    try:
        result = float(text)
    except ValueError as error:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}") from error
    if result < 0 and not allow_negative:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    return result


def _parse_stat_json_int(value: object, field: str, *, allow_negative: bool = False) -> int:
    if type(value) is not int:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    if value < 0 and not allow_negative:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    return value


def _parse_stat_json_float(value: object, field: str) -> float:
    if type(value) in (int, float):
        result = float(value)
    elif isinstance(value, str) and value.strip() != "":
        try:
            result = float(value.strip())
        except ValueError as error:
            raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}") from error
    else:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    if result < 0:
        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {value!r}")
    return result


def _archive_stat_rows(folder: Path, elements: dict[str, str | None]) -> dict[tuple[str, str, int], tuple]:
    """Parse saved Vaastav gameweek rows into (element, fixture, week) stat tuples."""
    reader = _csv(folder / "gws/merged_gw.csv")
    fields = set(reader.fieldnames or ())
    required = {
        "element", "fixture", "GW", *_CORE_STAT_FIELDS,
        "total_points", "influence", "creativity", "threat", "ict_index",
        *_OWNERSHIP_STAT_FIELDS, "transfers_balance",
    }
    if not required <= fields:
        missing = sorted(required - fields)
        raise PlayerFixtureObservationsError(f"Archive gameweeks lack required stat fields: {', '.join(missing)}")
    rows = list(reader)
    if folder.name == "2019-20":
        rows = [row for row in rows if not (row.get("GW") == "29" and row.get("fixture") == "275")]
    stats: dict[tuple[str, str, int], tuple] = {}
    for row in rows:
        element = row["element"]
        if element not in elements:
            raise PlayerFixtureObservationsError(f"Unknown FPL gameweek element {element}")
        if elements[element] is None:
            continue
        fixture = row["fixture"]
        _positive(fixture, "fixture ID")
        week = _positive(row["GW"], "gameweek")
        key = (element, fixture, week)
        values: list[object] = []
        for field in _CORE_STAT_FIELDS:
            values.append(_parse_stat_int(row.get(field), field, allow_null=False, allow_negative=(field == "bps")))
        values.append(_parse_stat_int(row.get("total_points"), "total_points", allow_null=False, allow_negative=True))
        for field in _OPTIONAL_INT_STAT_FIELDS:
            if field == "starts":
                if field not in fields:
                    values.append(None)
                else:
                    parsed = _parse_stat_int(row.get(field), field, allow_null=True)
                    if parsed is not None and parsed not in (0, 1):
                        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {row.get(field)!r}")
                    values.append(parsed)
            elif field not in fields:
                values.append(None)
            else:
                values.append(_parse_stat_int(row.get(field), field, allow_null=True))
        for field in _OPTIONAL_REAL_STAT_FIELDS:
            source = "xP" if field == "expected_points" else field
            if source not in fields:
                values.append(None)
            else:
                values.append(_parse_stat_float(row.get(source), field, allow_null=True, allow_negative=(field == "expected_points")))
        for field in _OWNERSHIP_STAT_FIELDS:
            values.append(_parse_stat_int(row.get(field), field, allow_null=False))
        values.append(_parse_stat_int(row.get("transfers_balance"), "transfers_balance", allow_null=False, allow_negative=True))
        stat_tuple = tuple(values)
        previous = stats.get(key)
        if previous is not None and previous != stat_tuple:
            raise PlayerFixtureObservationsError(f"Conflicting repeated player/fixture stat {key[1]}:{key[0]}")
        stats[key] = stat_tuple
    if not stats:
        raise PlayerFixtureObservationsError(f"No player/fixture stats in {folder.name}")
    return stats


def _official_stat_rows(official_raw_root: Path, elements: dict[str, str]) -> dict[tuple[str, str, int], tuple]:
    """Parse saved official element-summary history into (element, fixture, week) stats."""
    from .official_fpl_season import _SUMMARY_FILENAME, _integer, _read_json, _object, _list

    folder = Path(official_raw_root) / "element_summaries"
    if not folder.is_dir():
        raise PlayerFixtureObservationsError(f"Missing official FPL element summaries directory {folder}")
    stats: dict[tuple[str, str, int], tuple] = {}
    for path in folder.glob("element_*.json"):
        match = _SUMMARY_FILENAME.fullmatch(path.name)
        if match is None:
            raise PlayerFixtureObservationsError(f"Invalid official FPL summary filename {path.name!r}")
        element = str(int(match.group("element")))
        if element not in elements:
            continue
        payload = _object(_read_json(path), f"element summary {element}")
        history = _list(payload.get("history"), f"element {element} history")
        for row in history:
            record = _object(row, f"element {element} history row")
            if _integer(record.get("element"), "history element") != int(element):
                raise PlayerFixtureObservationsError(f"History row is filed under the wrong element summary {element}")
            fixture = str(_integer(record.get("fixture"), "history fixture"))
            week = _integer(record.get("round"), "history round")
            key = (element, fixture, week)
            values: list[object] = []
            for field in _CORE_STAT_FIELDS:
                values.append(_parse_stat_json_int(record.get(field), field, allow_negative=(field == "bps")))
            values.append(_parse_stat_json_int(record.get("total_points"), "total_points", allow_negative=True))
            for field in _OPTIONAL_INT_STAT_FIELDS:
                raw = record.get(field)
                if raw is None:
                    values.append(None)
                    continue
                if field == "starts":
                    parsed = _parse_stat_json_int(raw, field)
                    if parsed not in (0, 1):
                        raise PlayerFixtureObservationsError(f"Invalid FPL stat {field}: {raw!r}")
                    values.append(parsed)
                else:
                    values.append(_parse_stat_json_int(raw, field))
            for field in _OPTIONAL_REAL_STAT_FIELDS:
                if field == "expected_points":
                    values.append(None)
                    continue
                raw = record.get(field)
                if raw is None:
                    values.append(None)
                else:
                    values.append(_parse_stat_json_float(raw, field))
            for field in _OWNERSHIP_STAT_FIELDS:
                values.append(_parse_stat_json_int(record.get(field), field))
            values.append(_parse_stat_json_int(record.get("transfers_balance"), "transfers_balance", allow_negative=True))
            stat_tuple = tuple(values)
            previous = stats.get(key)
            if previous is not None and previous != stat_tuple:
                raise PlayerFixtureObservationsError(f"Conflicting repeated player/fixture stat {fixture}:{element}")
            stats[key] = stat_tuple
    if not stats:
        raise PlayerFixtureObservationsError("No official player/fixture stats were found")
    return stats


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
            elements: dict[str, str | None] = dict(evidence.elements)
            observations = evidence.observations
            expected_assignments, expected_weeks = _group_assignments(
                observations, fixtures, season
            )
            stat_rows = _official_stat_rows(Path(official_raw_root), evidence.elements)
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
            stat_rows = _archive_stat_rows(folder, elements)
        observation_keys = {(element, source_fixture, week) for element, _, week, _, _, _, source_fixture in observations}
        if set(stat_rows) != observation_keys:
            missing = sorted(observation_keys - set(stat_rows), key=lambda item: (int(item[1]), item[0]))[:5]
            extra = sorted(set(stat_rows) - observation_keys, key=lambda item: (int(item[1]), item[0]))[:5]
            raise PlayerFixtureObservationsError(
                f"Player/fixture stats do not match saved listings; missing={missing}, extra={extra}"
            )
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

        desired_rows: dict[tuple[int, int], tuple] = {}
        for element, _, week, club, _, minutes, source_fixture_id in observations:
            fixture_id = fixture_mappings.get(source_fixture_id)
            player_id = players_by_element.get(element)
            if fixture_id is None or player_id is None:
                raise PlayerFixtureObservationsError(
                    f"Missing fixture or player mapping for observation {source_fixture_id}:{element}"
                )
            stats_tuple = stat_rows.get((element, source_fixture_id, week))
            if stats_tuple is None:
                raise PlayerFixtureObservationsError(f"Missing stat for {source_fixture_id}:{element}")
            values = (
                fixture_id,
                player_id,
                canonical_teams[club][0],
                week_ids[week],
                element,
                minutes,
                *stats_tuple,
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
        select_columns = ", ".join(f"o.{name}" for name in _ALL_COLUMNS)
        existing_observations = connection.execute(
            f"SELECT {select_columns} FROM player_fixture_observations o "
            "JOIN fixtures f USING (fixture_id) WHERE f.season_id = ?",
            (season_id,),
        ).fetchall()
        existing_by_key = {
            (row[0], row[1]): row for row in existing_observations
        }

        def _is_narrow_backfill(existing_row: tuple, desired_row: tuple) -> bool:
            return (
                existing_row[:6] == desired_row[:6]
                and all(value is None for value in existing_row[6:])
                and any(value is not None for value in desired_row[6:])
            )

        def _backfill_updates(
            old_by_key: dict[tuple[int, int], tuple], new_by_key: dict[tuple[int, int], tuple]
        ) -> list[tuple]:
            updates: list[tuple] = []
            for key, desired in new_by_key.items():
                existing = old_by_key.get(key)
                if existing is None:
                    continue
                if existing == desired:
                    continue
                if _is_narrow_backfill(existing, desired):
                    updates.append(desired)
                    continue
                raise PlayerFixtureObservationsError(
                    "Existing player/fixture observations are missing, partial or changed; manual review required"
                )
            return updates

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
        additions: list[tuple] = []
        backfills: list[tuple] = []
        if season != OFFICIAL_SEASON:
            if recorded_fixtures and recorded_fixtures != desired_fixture_ids:
                raise PlayerFixtureObservationsError(
                    "Existing archived player/fixture completion records are partial or changed"
                )
            if existing_observations:
                if set(existing_observations) == set(desired_rows.values()):
                    pass
                else:
                    backfills = _backfill_updates(existing_by_key, desired_rows)
                    if set(existing_by_key) != set(desired_rows):
                        raise PlayerFixtureObservationsError(
                            "Existing player/fixture observations are partial or differ; manual review required"
                        )
            else:
                additions = list(desired_rows.values())
            fixture_markers_to_add = desired_fixture_ids - recorded_fixtures
        else:
            if not existing_fixture_log and existing_observations:
                if set(existing_observations) != set(desired_rows.values()):
                    try:
                        backfills = _backfill_updates(existing_by_key, desired_rows)
                    except PlayerFixtureObservationsError:
                        raise PlayerFixtureObservationsError(
                            "Official fixture completion records are missing; existing rows cannot be safely extended"
                        ) from None
                    if set(existing_by_key) != set(desired_rows):
                        raise PlayerFixtureObservationsError(
                            "Official fixture completion records are missing; existing rows cannot be safely extended"
                        )
                fixture_markers_to_add = desired_fixture_ids
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
                        try:
                            backfills_for_fixture = _backfill_updates(old_slice, expected_slice)
                        except PlayerFixtureObservationsError:
                            raise PlayerFixtureObservationsError(
                                "Existing official player/fixture observations are missing, partial or changed"
                            ) from None
                        if set(old_slice) != set(expected_slice):
                            raise PlayerFixtureObservationsError(
                                "Existing official player/fixture observations are missing, partial or changed"
                            )
                        backfills.extend(backfills_for_fixture)
                fixture_markers_to_add = desired_fixture_ids - recorded_fixtures
                additions = [
                    row for key, row in desired_rows.items() if key[0] in fixture_markers_to_add
                ]

        if additions:
            placeholders = ", ".join(["?"] * len(_ALL_COLUMNS))
            columns = ", ".join(_ALL_COLUMNS)
            connection.executemany(
                f"INSERT INTO player_fixture_observations ({columns}) VALUES ({placeholders})",
                sorted(additions),
            )
        if backfills:
            set_clause = ", ".join(f"{name} = ?" for name in _STAT_COLUMNS)
            connection.executemany(
                f"UPDATE player_fixture_observations SET {set_clause} WHERE fixture_id = ? AND player_id = ?",
                [(*row[6:], row[0], row[1]) for row in sorted(backfills)],
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
        sum(values[5] > 0 for values in desired_rows.values()),
    )
