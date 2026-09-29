"""Map saved FPL gameweek team assignments onto canonical players and clubs.

These are FPL-listed teams for a gameweek, not employment stints. A zero-minute
observation does not establish that a player appeared in a match.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import io
from pathlib import Path
import sqlite3

from ..reference import LEGACY_TEAMS_PATH
from .canonical_players import CODE_NAMESPACE, ID_NAMESPACE, MANAGER_TYPE, PLAYER_TYPES
from .canonical_teams import (
    COMPETITION_KEY, COMPETITION_NAME, TEAM_REFERENCE_PATH, _normalize, _read_clubs,
)
from .sqlite import DATABASE_PATH, connect_database

LEGACY_SEASONS = {"2016-17", "2017-18", "2018-19"}
SEASONS = {f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027)}
# Season-scoped FPL IDs from vaastav/Fantasy-Premier-League/data/master_team_list.csv.
LEGACY_TEAMS = LEGACY_TEAMS_PATH
GAMEWEEKS_SQL = """CREATE TABLE gameweeks (
    gameweek_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(season_id),
    gameweek_number INTEGER NOT NULL CHECK (gameweek_number > 0),
    UNIQUE (season_id, gameweek_number)
) STRICT"""
MEMBERSHIPS_SQL = """CREATE TABLE player_gameweek_teams (
    gameweek_id INTEGER NOT NULL REFERENCES gameweeks(gameweek_id),
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    source_element_id TEXT NOT NULL,
    first_kickoff_at TEXT NOT NULL,
    last_kickoff_at TEXT NOT NULL,
    fixture_observations INTEGER NOT NULL CHECK (fixture_observations > 0),
    fixtures_with_minutes INTEGER NOT NULL CHECK (fixtures_with_minutes >= 0
        AND fixtures_with_minutes <= fixture_observations),
    PRIMARY KEY (gameweek_id, player_id, team_id),
    CHECK (first_kickoff_at <= last_kickoff_at)
) STRICT"""


class GameweekTeamsError(ValueError):
    """The saved team/week evidence disagrees with reviewed canonical identities."""


@dataclass(frozen=True)
class GameweekTeamsSummary:
    season: str
    gameweeks: int
    player_team_rows: int
    multi_team_players: int


def _csv(path: Path) -> csv.DictReader:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # Some early saved Vaastav gameweek CSVs contain Windows-1252 names.
        text = path.read_text(encoding="cp1252")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise GameweekTeamsError(f"Missing or repeated CSV header: {path}")
    return reader


def _positive(value: str, field: str, *, allow_zero: bool = False) -> int:
    if not value.isascii() or not value.isdecimal() or str(int(value)) != value or (
        int(value) < 0 if allow_zero else int(value) <= 0
    ):
        raise GameweekTeamsError(f"Invalid {field}: {value!r}")
    return int(value)


def _utc(value: str) -> str:
    try:
        if not value.endswith("Z") or datetime.fromisoformat(value).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z") != value:
            raise ValueError("not a canonical UTC instant")
    except ValueError as error:
        raise GameweekTeamsError(f"Invalid FPL kickoff time {value!r}") from error
    return value


def _source_teams(folder: Path, aliases: dict[str, str]) -> dict[str, str]:
    legacy = folder.name in LEGACY_SEASONS
    reader = _csv(LEGACY_TEAMS if legacy else folder / "teams.csv")
    id_field, name_field = ("team", "team_name") if legacy else ("id", "name")
    if not {id_field, name_field} <= set(reader.fieldnames or ()) or (legacy and "season" not in reader.fieldnames):
        raise GameweekTeamsError("Archived FPL team lookup lacks season/ID/name")
    teams = {}
    for row in reader:
        if legacy and row["season"] != folder.name:
            continue
        source_id = row[id_field]
        _positive(source_id, "FPL team ID")
        key = aliases.get(_normalize(row[name_field]))
        if key is None or source_id in teams or key in teams.values():
            raise GameweekTeamsError(f"Unreviewed or duplicate FPL team {row[name_field]!r}")
        teams[source_id] = key
    if (legacy and set(teams) != {str(i) for i in range(1, 21)}) or (not legacy and not teams):
        raise GameweekTeamsError("Missing archived FPL team IDs")
    return teams


def _observations(folder: Path, teams: dict[str, str], aliases: dict[str, str]):
    fixtures = {}
    if folder.name not in {"2016-17", "2017-18"}:
        fixture_reader = _csv(folder / "fixtures.csv")
        if not {"id", "team_h", "team_a"} <= set(fixture_reader.fieldnames or ()):
            raise GameweekTeamsError("Archive fixtures.csv lacks fixture/team IDs")
        for row in fixture_reader:
            fixture = row["id"]
            _positive(fixture, "fixture ID")
            home, away = row["team_h"], row["team_a"]
            if fixture in fixtures or home == away or home not in teams or away not in teams:
                raise GameweekTeamsError(f"Invalid archive fixture teams for {fixture}")
            fixtures[fixture] = (home, away)

    reader = _csv(folder / "players_raw.csv")
    if not {"id", "code", "element_type"} <= set(reader.fieldnames or ()):
        raise GameweekTeamsError("Archive players_raw.csv lacks player identity fields")
    elements = {}
    for row in reader:
        source_id, code = row["id"], row["code"]
        _positive(source_id, "element ID")
        _positive(code, "FPL code")
        kind = _positive(row["element_type"], "element type")
        if source_id in elements:
            raise GameweekTeamsError(f"Repeated FPL element {source_id}")
        if kind not in PLAYER_TYPES | {MANAGER_TYPE}:
            raise GameweekTeamsError(f"Unknown FPL element type {kind}")
        elements[source_id] = code if kind != MANAGER_TYPE else None

    reader = _csv(folder / "gws/merged_gw.csv")
    required = {"element", "fixture", "opponent_team", "was_home", "kickoff_time", "GW", "minutes"}
    if not required <= set(reader.fieldnames or ()):
        raise GameweekTeamsError("Archive gameweeks lack required fixture/team fields")
    labelled = "team" in reader.fieldnames
    if not labelled and folder.name not in LEGACY_SEASONS | {"2019-20"}:
        raise GameweekTeamsError(f"Unlabelled gameweek teams require review: {folder.name}")
    rows = list(reader)
    if folder.name in {"2016-17", "2017-18"}:
        # Both sides of an FPL fixture name their opponent. Cross-check them
        # instead of using the season-end players_raw.csv team after transfers.
        sides: dict[str, dict[str, str]] = {}
        for row in rows:
            fixture = row["fixture"]
            _positive(fixture, "fixture ID")
            side, opponent = row["was_home"], row["opponent_team"]
            if side not in ("True", "False") or opponent not in teams:
                raise GameweekTeamsError(f"Invalid archive fixture side for {fixture}")
            values = sides.setdefault(fixture, {})
            if side in values and values[side] != opponent:
                raise GameweekTeamsError(f"Conflicting opponent IDs for fixture {fixture}")
            values[side] = opponent
        for fixture, values in sides.items():
            home, away = values.get("False"), values.get("True")
            if home is None or away is None or home == away:
                raise GameweekTeamsError(f"Incomplete archive fixture sides for {fixture}")
            fixtures[fixture] = (home, away)
    observations = []
    seen_rows = set()
    for row in rows:
        element = row["element"]
        if element not in elements:
            raise GameweekTeamsError(f"Unknown FPL gameweek element {element}")
        if elements[element] is None:
            continue  # Managers are not football players.
        fixture = row["fixture"]
        _positive(fixture, "fixture ID")
        if fixture not in fixtures:
            raise GameweekTeamsError(f"Gameweek references unknown fixture {fixture}")
        home, away = fixtures[fixture]
        if row["was_home"] not in ("True", "False"):
            raise GameweekTeamsError(f"Invalid home/away flag {row['was_home']!r}")
        source_team, opponent = (home, away) if row["was_home"] == "True" else (away, home)
        if row["opponent_team"] != opponent:
            raise GameweekTeamsError(f"Fixture/opponent conflict for element {element}, fixture {fixture}")
        key = teams[source_team]
        if labelled and aliases.get(_normalize(row["team"])) != key:
            raise GameweekTeamsError(f"Fixture/gameweek team conflict for element {element}, fixture {fixture}")
        week = _positive(row["GW"], "gameweek")
        minutes = _positive(row["minutes"], "minutes", allow_zero=True)
        observation = (element, elements[element], week, key,
                       _utc(row["kickoff_time"]), minutes, fixture)
        if observation not in seen_rows:  # The saved archive contains a few identical repeated rows.
            observations.append(observation)
            seen_rows.add(observation)
    if not observations:
        raise GameweekTeamsError(f"No player/team gameweek observations in {folder.name}")
    return elements, observations


def _schema(connection: sqlite3.Connection) -> None:
    for table, sql in (("gameweeks", GAMEWEEKS_SQL), ("player_gameweek_teams", MEMBERSHIPS_SQL)):
        existing = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        if existing is None:
            connection.execute(sql)
            if table == "player_gameweek_teams":
                connection.execute("CREATE INDEX idx_player_gameweek_teams_player ON player_gameweek_teams(player_id)")
        elif existing[0].strip().rstrip(";") != sql:
            raise GameweekTeamsError(f"Existing {table} schema differs; manual review required")


def load_player_gameweek_teams(
    season: str,
    archive_root: Path,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
    *,
    official_raw_root: Path | None = None,
) -> GameweekTeamsSummary:
    """Insert a saved season; official current-season evidence may extend it."""
    if season not in SEASONS:
        raise GameweekTeamsError("Dated club identity is only established for 2016-17 through 2026-27")
    clubs, aliases = _read_clubs(Path(reference_path))
    if official_raw_root is not None:
        if season != "2026-27":
            raise GameweekTeamsError("Official current-season ingestion is only reviewed for 2026-27")
        from .official_fpl_season import read_official_fpl_season

        evidence = read_official_fpl_season(Path(official_raw_root), season)
        elements, observations = evidence.elements, evidence.observations
    else:
        folder = Path(archive_root) / season
        teams = _source_teams(folder, aliases)
        elements, observations = _observations(folder, teams, aliases)
    scope = f"{COMPETITION_KEY}:{season}"
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        canonical = {key: (team_id, name) for team_id, key, name in
                     connection.execute("SELECT team_id, team_key, name FROM teams")}
        if any(canonical.get(key, (None, None))[1] != name for key, name in clubs):
            raise GameweekTeamsError("Canonical clubs differ from reviewed team reference")
        if official_raw_root is not None:
            saved_team_ids = dict(connection.execute(
                "SELECT source_id, team_id FROM team_source_ids WHERE source_namespace = 'fpl.team.id' "
                "AND source_scope = ?", (scope,),
            ))
            if saved_team_ids != {source_id: canonical[key][0]
                                  for source_id, key in evidence.teams.items()}:
                raise GameweekTeamsError("Official FPL teams differ from season-scoped canonical mappings")
        mapped = {(namespace, source_id): player_id for namespace, source_id, player_id in
                  connection.execute(
                      "SELECT source_namespace, source_id, player_id FROM player_source_ids "
                      "WHERE source_scope = ? AND source_namespace IN (?, ?)",
                      (scope, ID_NAMESPACE, CODE_NAMESPACE),
                  )}
        resolved = {}
        for element, code in elements.items():
            if code is None:
                continue
            player_id = mapped.get((ID_NAMESPACE, element))
            if player_id is None or player_id != mapped.get((CODE_NAMESPACE, code)):
                raise GameweekTeamsError(f"Missing or conflicting FPL player mapping for {scope}:{element}")
            resolved[element] = player_id

        competition = connection.execute(
            "SELECT competition_id, name FROM competitions WHERE competition_key = ?", (COMPETITION_KEY,)
        ).fetchone()
        if competition is None:
            competition_id = connection.execute(
                "INSERT INTO competitions (competition_key, name) VALUES (?, ?) RETURNING competition_id",
                (COMPETITION_KEY, COMPETITION_NAME),
            ).fetchone()[0]
        elif competition[1] == COMPETITION_NAME:
            competition_id = competition[0]
        else:
            raise GameweekTeamsError("Existing Premier League competition differs")
        start_year = int(season[:4])
        existing_season = connection.execute(
            "SELECT season_id, start_year, end_year FROM seasons WHERE competition_id = ? AND label = ?",
            (competition_id, season),
        ).fetchone()
        if existing_season is None:
            season_id = connection.execute(
                "INSERT INTO seasons (competition_id, label, start_year, end_year) "
                "VALUES (?, ?, ?, ?) RETURNING season_id",
                (competition_id, season, start_year, start_year + 1),
            ).fetchone()[0]
        elif existing_season[1:] == (start_year, start_year + 1):
            season_id = existing_season[0]
        else:
            raise GameweekTeamsError(f"Existing season metadata differs for {season}")
        _schema(connection)
        weeks = sorted({week for _, _, week, _, _, _, _ in observations})
        current_weeks = dict(connection.execute(
            "SELECT gameweek_number, gameweek_id FROM gameweeks WHERE season_id = ?", (season_id,)
        ))
        previous_week_ids = set(current_weeks.values())
        changed_weeks = (not set(current_weeks) <= set(weeks) if official_raw_root is not None
                         else set(current_weeks) != set(weeks))
        if current_weeks and changed_weeks:
            raise GameweekTeamsError(f"Existing gameweeks for {season} are partial or changed")
        if set(current_weeks) != set(weeks):
            connection.executemany(
                "INSERT INTO gameweeks (season_id, gameweek_number) VALUES (?, ?)",
                ((season_id, number) for number in weeks if number not in current_weeks),
            )
            current_weeks = dict(connection.execute(
                "SELECT gameweek_number, gameweek_id FROM gameweeks WHERE season_id = ?", (season_id,)
            ))
        grouped = {}
        unique_fixtures = set()
        for element, _, week, key, kickoff, minutes, fixture in observations:
            # A postponed fixture may appear in both its original and replayed FPL week.
            fixture_key = (element, fixture, week)
            if fixture_key in unique_fixtures:
                raise GameweekTeamsError(f"Repeated FPL fixture observation {fixture_key}")
            unique_fixtures.add(fixture_key)
            group = (current_weeks[week], resolved[element], canonical[key][0])
            if group not in grouped:
                grouped[group] = [element, kickoff, kickoff, 0, 0]
            row = grouped[group]
            if row[0] != element:
                raise GameweekTeamsError(f"Two FPL elements map to one player in week {week}")
            row[1], row[2] = min(row[1], kickoff), max(row[2], kickoff)
            row[3] += 1
            row[4] += minutes > 0
        desired = {(gw, player, team, *values) for (gw, player, team), values in grouped.items()}
        existing = set(connection.execute(
            "SELECT p.gameweek_id, p.player_id, p.team_id, p.source_element_id, "
            "p.first_kickoff_at, p.last_kickoff_at, p.fixture_observations, p.fixtures_with_minutes "
            "FROM player_gameweek_teams p JOIN gameweeks g ON g.gameweek_id = p.gameweek_id "
            "WHERE g.season_id = ?", (season_id,)
        ))
        if existing or previous_week_ids:
            previous = desired if official_raw_root is None else {
                row for row in desired if row[0] in previous_week_ids
            }
            if existing != previous:
                raise GameweekTeamsError(f"Existing player/team rows for {season} differ; manual review required")
        if desired - existing:
            connection.executemany(
                "INSERT INTO player_gameweek_teams "
                "(gameweek_id, player_id, team_id, source_element_id, first_kickoff_at, "
                "last_kickoff_at, fixture_observations, fixtures_with_minutes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sorted(desired - existing),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    player_teams = {}
    for (_, player, team) in grouped:
        player_teams.setdefault(player, set()).add(team)
    return GameweekTeamsSummary(season, len(weeks), len(desired),
                                sum(len(clubs) > 1 for clubs in player_teams.values()))
