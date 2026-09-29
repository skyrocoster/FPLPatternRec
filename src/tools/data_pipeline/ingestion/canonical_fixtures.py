"""Accept saved FPL matches against existing player/team/week evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .canonical_teams import (
    COMPETITION_KEY, TEAM_REFERENCE_PATH, CanonicalTeamsValidationError, _read_clubs,
)
from .player_gameweek_teams import (
    GameweekTeamsError, _csv, _observations, _positive, _source_teams, _utc,
)
from .sqlite import DATABASE_PATH, connect_database

SEASONS = {f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027)}
EARLY_SEASONS = {"2016-17", "2017-18"}
NAMESPACE = "fpl.fixture.id"
FIXTURE_GAMEWEEKS_SQL = """CREATE TABLE fixture_gameweeks (
    fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
    gameweek_id INTEGER NOT NULL REFERENCES gameweeks(gameweek_id),
    PRIMARY KEY (fixture_id, gameweek_id)
) STRICT"""


class CanonicalFixturesError(ValueError):
    """A source match cannot safely be reconciled with the existing season."""


@dataclass(frozen=True)
class CanonicalFixturesSummary:
    season: str
    fixture_count: int


def _score(value: str, field: str) -> int:
    # Vaastav's unfinished 2026-27 snapshot serialized completed scores as 2.0.
    if value.endswith(".0") and value[:-2].isascii() and value[:-2].isdecimal():
        value = value[:-2]
    return _positive(value, field, allow_zero=True)


def _legacy_fixtures(folder: Path, source_teams: dict[str, str]) -> dict[str, tuple[str, str, str, int, int, int]]:
    """Recover both sides of each early fixture without season-end player teams."""
    reader = _csv(folder / "gws/merged_gw.csv")
    required = {"fixture", "was_home", "opponent_team", "kickoff_time", "GW", "team_h_score", "team_a_score"}
    if not required <= set(reader.fieldnames or ()):
        raise CanonicalFixturesError("Early archive lacks fixture side, kickoff or final-score evidence")
    sides: dict[str, dict[str, str]] = {}
    facts: dict[str, tuple[str, int, int, int]] = {}
    for row in reader:
        if any(not isinstance(row[field], str) for field in required):
            raise CanonicalFixturesError("Incomplete early fixture observation")
        source_id = row["fixture"]
        _positive(source_id, "fixture ID")
        side, opponent = row["was_home"], row["opponent_team"]
        if side not in {"True", "False"} or opponent not in source_teams:
            raise CanonicalFixturesError(f"Invalid early fixture side {source_id}")
        previous = sides.setdefault(source_id, {}).setdefault(side, opponent)
        if previous != opponent:
            raise CanonicalFixturesError(f"Conflicting early fixture sides for {source_id}")
        fact = (_utc(row["kickoff_time"]), _positive(row["GW"], "gameweek"),
                _score(row["team_h_score"], "home goals"), _score(row["team_a_score"], "away goals"))
        if source_id in facts and facts[source_id] != fact:
            raise CanonicalFixturesError(f"Conflicting early fixture result for {source_id}")
        facts[source_id] = fact
    fixtures = {}
    for source_id, values in sides.items():
        home, away = values.get("False"), values.get("True")
        if home is None or away is None or home == away:
            raise CanonicalFixturesError(f"Missing or invalid early fixture side for {source_id}")
        kickoff, week, home_goals, away_goals = facts[source_id]
        fixtures[source_id] = (source_teams[home], source_teams[away], kickoff, week, home_goals, away_goals)
    return fixtures


def _fixtures(folder: Path, source_teams: dict[str, str]) -> dict[str, tuple[str, str, str, int, int, int]]:
    if folder.name in EARLY_SEASONS:
        fixtures = _legacy_fixtures(folder, source_teams)
        if len(fixtures) != 380:
            raise CanonicalFixturesError(f"Incomplete early season: {len(fixtures)} fixtures")
        return fixtures
    reader = _csv(folder / "fixtures.csv")
    required = {
        "id", "team_h", "team_a", "event", "kickoff_time", "finished",
        "started", "finished_provisional", "minutes", "team_h_score", "team_a_score",
    }
    if not required <= set(reader.fieldnames or ()):
        raise CanonicalFixturesError("Archive fixtures lack required identity, status or result fields")
    fixtures = {}
    all_ids = set()
    for row in reader:
        if any(not isinstance(row[field], str) for field in required):
            raise CanonicalFixturesError("Incomplete archive fixture row")
        source_id = row["id"]
        _positive(source_id, "fixture ID")
        home, away = row["team_h"], row["team_a"]
        if source_id in all_ids or home == away or home not in source_teams or away not in source_teams:
            raise CanonicalFixturesError(f"Duplicate or unreviewed fixture {source_id}")
        all_ids.add(source_id)
        week = _positive(row["event"], "fixture event")
        kickoff = _utc(row["kickoff_time"])
        flags = (row["finished"], row["started"], row["finished_provisional"])
        if folder.name == "2026-27" and flags == ("False",) * 3:
            if row["minutes"] != "0" or row["team_h_score"] or row["team_a_score"]:
                raise CanonicalFixturesError(f"Unfinished fixture {source_id} has result evidence")
            continue  # No gameweek or player evidence for future scheduled matches yet.
        if flags != ("True",) * 3:
            raise CanonicalFixturesError(f"Fixture {source_id} is not a confirmed finished match")
        if row["minutes"] != "90":
            raise CanonicalFixturesError(f"Fixture {source_id} needs score interpretation review")
        home_goals = _score(row["team_h_score"], "home goals")
        away_goals = _score(row["team_a_score"], "away goals")
        fixtures[source_id] = (source_teams[home], source_teams[away], kickoff, week, home_goals, away_goals)
    if len(all_ids) != 380 or len(fixtures) != (10 if folder.name == "2026-27" else 380):
        raise CanonicalFixturesError(f"Incomplete reviewed fixture coverage for {folder.name}")
    if folder.name == "2026-27" and {values[3] for values in fixtures.values()} != {1}:
        raise CanonicalFixturesError("Current archive only establishes completed GW 1 fixtures")
    return fixtures


def _expected_assignments(
    folder: Path, source_teams: dict[str, str], aliases: dict[str, str],
    fixtures: dict[str, tuple[str, str, str, int, int, int]],
) -> tuple[set[tuple], set[int]]:
    if folder.name not in EARLY_SEASONS:
        reader = _csv(folder / "gws/merged_gw.csv")
        required = {"fixture", "GW", "team_h_score", "team_a_score"}
        if not required <= set(reader.fieldnames or ()):
            raise CanonicalFixturesError("Gameweek observations lack fixture scores")
        for row in reader:
            source_id = row["fixture"]
            fixture = fixtures.get(source_id)
            if fixture is None:
                raise CanonicalFixturesError(f"Unknown gameweek fixture {source_id}")
            if folder.name == "2019-20" and source_id == "275" and row["GW"] == "29":
                if row["team_h_score"] or row["team_a_score"]:
                    raise CanonicalFixturesError("Postponed fixture's original week has a result")
            elif (_score(row["team_h_score"], "home goals"),
                  _score(row["team_a_score"], "away goals")) != fixture[4:]:
                raise CanonicalFixturesError(f"Fixture/gameweek score differs for {source_id}")
    _, observations = _observations(folder, source_teams, aliases)
    return _group_assignments(observations, fixtures, folder.name)


def _group_assignments(
    observations: list[tuple[str, str, int, str, str, int, str]],
    fixtures: dict[str, tuple[str, str, str, int, int, int]],
    season: str,
) -> tuple[set[tuple], set[int]]:
    grouped: dict[tuple[int, str, str], list] = {}
    seen_fixtures = set()
    exceptions: dict[str, int] = {}
    for element, _, week, club, kickoff, minutes, source_id in observations:
        fixture = fixtures.get(source_id)
        exception = None
        if season == "2019-20" and source_id == "275" and week == 29 and kickoff == "2020-03-11T19:30:00Z":
            exception = "postponed"
        if season == "2021-22" and source_id == "263" and week == 27 and kickoff == "2022-02-26T15:00:00Z":
            exception = "kickoff correction"
        if (fixture is None or (week != fixture[3] and exception != "postponed")
            or (kickoff != fixture[2] and exception is None) or club not in fixture[:2]):
            raise CanonicalFixturesError(f"Fixture/gameweek evidence differs for FPL fixture {source_id}")
        if exception:
            exceptions[exception] = exceptions.get(exception, 0) + 1
        observation = (element, source_id, week)
        if observation in seen_fixtures:
            raise CanonicalFixturesError(f"Conflicting repeated fixture observation {observation}")
        seen_fixtures.add(observation)
        group = grouped.setdefault((week, element, club), [kickoff, kickoff, 0, 0])
        group[0], group[1] = min(group[0], kickoff), max(group[1], kickoff)
        group[2] += 1
        group[3] += minutes > 0
    if {source_id for _, source_id, _ in seen_fixtures} != set(fixtures):
        raise CanonicalFixturesError("Saved fixture coverage differs from gameweek observations")
    if season == "2019-20" and exceptions.get("postponed") != 59:
        raise CanonicalFixturesError("Reviewed postponed fixture evidence changed")
    if season == "2021-22" and exceptions.get("kickoff correction") != 78:
        raise CanonicalFixturesError("Reviewed kickoff correction evidence changed")
    return {(week, element, club, *values) for (week, element, club), values in grouped.items()}, {
        week for week, _, _ in grouped
    }


def load_canonical_fixtures(
    season: str,
    archive_root: Path,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
    *,
    official_raw_root: Path | None = None,
) -> CanonicalFixturesSummary:
    """Add reviewed fixtures; the official current season can grow by finished weeks."""
    if season not in SEASONS:
        raise CanonicalFixturesError("Only saved 2016-17 through 2026-27 fixtures have been reviewed")
    try:
        clubs, aliases = _read_clubs(Path(reference_path))
        if official_raw_root is not None:
            if season != "2026-27":
                raise CanonicalFixturesError("Official current-season ingestion is only reviewed for 2026-27")
            from .official_fpl_season import read_official_fpl_season

            evidence = read_official_fpl_season(Path(official_raw_root), season)
            fixtures = evidence.fixtures
            expected, weeks = _group_assignments(evidence.observations, fixtures, season)
        else:
            folder = Path(archive_root) / season
            source_teams = _source_teams(folder, aliases)
            fixtures = _fixtures(folder, source_teams)
            expected, weeks = _expected_assignments(folder, source_teams, aliases, fixtures)
    except (CanonicalTeamsValidationError, GameweekTeamsError) as error:
        raise CanonicalFixturesError(str(error)) from error

    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        season_row = connection.execute(
            "SELECT s.season_id FROM seasons s JOIN competitions c USING (competition_id) "
            "WHERE c.competition_key = ? AND s.label = ?", (COMPETITION_KEY, season),
        ).fetchone()
        if season_row is None:
            raise CanonicalFixturesError("Load this season's player-gameweek teams before fixtures")
        season_id = season_row[0]
        canonical = {key: (team_id, name) for team_id, key, name in connection.execute(
            "SELECT team_id, team_key, name FROM teams"
        )}
        if any(canonical.get(key, (None, None))[1] != name for key, name in clubs):
            raise CanonicalFixturesError("Canonical clubs differ from reviewed team reference")
        actual = connection.execute(
            "SELECT g.gameweek_number, p.source_element_id, t.team_key, p.first_kickoff_at, "
            "p.last_kickoff_at, p.fixture_observations, p.fixtures_with_minutes "
            "FROM player_gameweek_teams p JOIN gameweeks g USING (gameweek_id) "
            "JOIN teams t ON t.team_id = p.team_id WHERE g.season_id = ?", (season_id,),
        ).fetchall()
        week_ids = dict(connection.execute(
            "SELECT gameweek_number, gameweek_id FROM gameweeks WHERE season_id = ?", (season_id,),
        ))
        actual_weeks = set(week_ids)
        if len(actual) != len(expected) or set(actual) != expected or weeks != actual_weeks:
            raise CanonicalFixturesError("Existing player/team/week assignments differ from saved fixture evidence")

        desired = {
            source_id: (season_id, canonical[home][0], canonical[away][0], None, kickoff,
                        "finished", home_goals, away_goals)
            for source_id, (home, away, kickoff, _, home_goals, away_goals) in fixtures.items()
        }
        existing = {row[0]: row[1:] for row in connection.execute(
            "SELECT fixture_id, season_id, home_team_id, away_team_id, match_date, kickoff_at, "
            "status, home_goals, away_goals FROM fixtures WHERE season_id = ?", (season_id,),
        )}
        scope = f"{COMPETITION_KEY}:{season}"
        mapped = dict(connection.execute(
            "SELECT source_id, fixture_id FROM fixture_source_ids "
            "WHERE source_namespace = ? AND source_scope = ?", (NAMESPACE, scope),
        ))
        new_season = not existing and not mapped
        if (not set(mapped) <= set(desired) or len(existing) != len(mapped)
            or set(mapped.values()) != set(existing)
            or (official_raw_root is None and not new_season and set(mapped) != set(desired))
            or any(existing[mapped[source_id]][:3] + existing[mapped[source_id]][4:] !=
                   desired[source_id][:3] + desired[source_id][4:] for source_id in mapped)):
            raise CanonicalFixturesError("Existing season fixtures or source mappings differ; manual review required")

        previous_links = {(mapped[source_id], week_ids[fixtures[source_id][3]]) for source_id in mapped}
        schema = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'fixture_gameweeks'"
        ).fetchone()
        created = schema is None
        if created:
            connection.execute(FIXTURE_GAMEWEEKS_SQL)
            connection.execute("CREATE INDEX idx_fixture_gameweeks_gameweek ON fixture_gameweeks(gameweek_id)")
        elif schema[0].strip().rstrip(";") != FIXTURE_GAMEWEEKS_SQL:
            raise CanonicalFixturesError("Existing fixture_gameweeks schema differs; manual review required")
        existing_links = set(connection.execute(
            "SELECT fg.fixture_id, fg.gameweek_id FROM fixture_gameweeks fg "
            "JOIN fixtures f ON f.fixture_id = fg.fixture_id WHERE f.season_id = ?", (season_id,),
        ))
        if existing_links != previous_links and not (created and not existing_links):
            raise CanonicalFixturesError("Existing fixture/gameweek links differ; manual review required")
        if created and previous_links:
            connection.executemany(
                "INSERT INTO fixture_gameweeks (fixture_id, gameweek_id) VALUES (?, ?)", sorted(previous_links),
            )
        for source_id in sorted(set(desired) - set(mapped), key=int):
            values = desired[source_id]
            fixture_id = connection.execute(
                "INSERT INTO fixtures (season_id, home_team_id, away_team_id, match_date, "
                "kickoff_at, status, home_goals, away_goals) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "RETURNING fixture_id", values,
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO fixture_source_ids (source_namespace, source_scope, source_id, fixture_id) "
                "VALUES (?, ?, ?, ?)", (NAMESPACE, scope, source_id, fixture_id),
            )
            connection.execute(
                "INSERT INTO fixture_gameweeks (fixture_id, gameweek_id) VALUES (?, ?)",
                (fixture_id, week_ids[fixtures[source_id][3]]),
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return CanonicalFixturesSummary(season, len(desired))
