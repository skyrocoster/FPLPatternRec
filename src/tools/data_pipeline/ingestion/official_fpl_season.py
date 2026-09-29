"""Review saved official FPL season payloads as canonical football evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from .canonical_teams import TEAM_REFERENCE_PATH, CanonicalTeamsValidationError, _normalize, _read_clubs
from .official_fpl_teams import (
    OfficialFplTeamsValidationError,
    _derive_season,
    validate_season,
)
from .player_gameweek_teams import GameweekTeamsError, _positive, _utc
from .canonical_players import MANAGER_TYPE, PLAYER_TYPES

TEAM_COUNT = 20
FIXTURE_COUNT = 380
_SUMMARY_FILENAME = re.compile(r"element_(?P<element>\d+)\.json\Z")
_FIXTURE_FLAGS = ("finished", "started", "finished_provisional")

Fixture = tuple[str, str, str, int, int, int]
Observation = tuple[str, str, int, str, str, int, str]


class OfficialFplSeasonError(ValueError):
    """Saved official FPL evidence is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class OfficialFplSeasonEvidence:
    """Normalized identities, finished fixtures, and player match observations."""

    season: str
    teams: dict[str, str]
    elements: dict[str, str]
    fixtures: dict[str, Fixture]
    observations: list[Observation]


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OfficialFplSeasonError(f"Cannot read official FPL JSON {path}: {error}") from error


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OfficialFplSeasonError(f"{field} must be a JSON object")
    return value


def _list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise OfficialFplSeasonError(f"{field} must be a JSON array")
    return value


def _integer(value: Any, field: str, *, allow_zero: bool = False) -> int:
    if type(value) is not int:
        raise OfficialFplSeasonError(f"{field} must be an integer")
    try:
        return _positive(str(value), field, allow_zero=allow_zero)
    except GameweekTeamsError as error:
        raise OfficialFplSeasonError(str(error)) from error


def _kickoff(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise OfficialFplSeasonError(f"{field} must be a UTC timestamp")
    try:
        return _utc(value)
    except GameweekTeamsError as error:
        raise OfficialFplSeasonError(str(error)) from error


def _bootstrap_teams(payload: dict[str, Any], aliases: dict[str, str]) -> dict[str, str]:
    rows = _list(payload.get("teams"), "bootstrap teams")
    teams: dict[str, str] = {}
    seen_keys: set[str] = set()
    for index, raw_row in enumerate(rows):
        row = _object(raw_row, f"bootstrap team {index}")
        source_id = str(_integer(row.get("id"), f"bootstrap team {index} ID"))
        name = row.get("name")
        if not isinstance(name, str) or not name.strip():
            raise OfficialFplSeasonError(f"Bootstrap team {source_id} has no valid name")
        key = aliases.get(_normalize(name))
        if key is None:
            raise OfficialFplSeasonError(f"Unreviewed official FPL team name {name!r}")
        if source_id in teams or key in seen_keys:
            raise OfficialFplSeasonError(f"Duplicate official FPL team ID or club {source_id}: {name!r}")
        teams[source_id] = key
        seen_keys.add(key)
    if len(teams) != TEAM_COUNT:
        raise OfficialFplSeasonError(f"Expected {TEAM_COUNT} reviewed official FPL teams, found {len(teams)}")
    return teams


def _bootstrap_elements(payload: dict[str, Any]) -> tuple[dict[str, str], set[str]]:
    rows = _list(payload.get("elements"), "bootstrap elements")
    elements: dict[str, str] = {}
    managers: set[str] = set()
    seen_codes: set[str] = set()
    seen_ids: set[str] = set()
    for index, raw_row in enumerate(rows):
        row = _object(raw_row, f"bootstrap element {index}")
        source_id = str(_integer(row.get("id"), f"bootstrap element {index} ID"))
        element_type = _integer(row.get("element_type"), f"bootstrap element {source_id} type")
        if element_type not in PLAYER_TYPES | {MANAGER_TYPE}:
            raise OfficialFplSeasonError(f"Unknown official FPL element type {element_type}")
        code = str(_integer(row.get("code"), f"bootstrap element {source_id} code"))
        if source_id in seen_ids:
            raise OfficialFplSeasonError(f"Duplicate official FPL element ID {source_id}")
        seen_ids.add(source_id)
        if element_type == MANAGER_TYPE:
            managers.add(source_id)
            continue
        if code in seen_codes:
            raise OfficialFplSeasonError(f"Duplicate official FPL footballer code {code}")
        seen_codes.add(code)
        elements[source_id] = code
    if not elements:
        raise OfficialFplSeasonError("Bootstrap contains no footballer elements")
    return elements, managers


def _bootstrap_events(payload: dict[str, Any]) -> dict[int, bool]:
    rows = _list(payload.get("events"), "bootstrap events")
    events: dict[int, bool] = {}
    for index, raw_row in enumerate(rows):
        row = _object(raw_row, f"bootstrap event {index}")
        event_id = _integer(row.get("id"), f"bootstrap event {index} ID")
        finished = row.get("finished")
        if type(finished) is not bool:
            raise OfficialFplSeasonError(f"Bootstrap event {event_id} has no boolean finished flag")
        if event_id in events:
            raise OfficialFplSeasonError(f"Duplicate bootstrap event ID {event_id}")
        events[event_id] = finished
    if set(events) != set(range(1, 39)):
        raise OfficialFplSeasonError("Bootstrap must contain all 38 Premier League gameweek events")
    return events


def _fixture_rows(
    payload: Any,
    teams: dict[str, str],
    events: dict[int, bool],
) -> tuple[dict[str, Fixture], dict[str, tuple[int, int]], set[int]]:
    rows = _list(payload, "fixtures.json")
    if len(rows) != FIXTURE_COUNT:
        raise OfficialFplSeasonError(f"Expected {FIXTURE_COUNT} official fixtures, found {len(rows)}")

    fixtures: dict[str, Fixture] = {}
    source_sides: dict[str, tuple[int, int]] = {}
    directed_pairs: set[tuple[int, int]] = set()
    appearances = {team_id: 0 for team_id in teams}
    completed_weeks: set[int] = set()

    for index, raw_row in enumerate(rows):
        row = _object(raw_row, f"fixture {index}")
        required = {
            "id", "team_h", "team_a", "event", "kickoff_time", "finished", "started",
            "finished_provisional", "minutes", "team_h_score", "team_a_score",
        }
        missing = required - set(row)
        if missing:
            raise OfficialFplSeasonError(
                f"Fixture {index} is missing required fields: {', '.join(sorted(missing))}"
            )
        source_id = str(_integer(row.get("id"), f"fixture {index} ID"))
        home_id = _integer(row.get("team_h"), f"fixture {source_id} home team")
        away_id = _integer(row.get("team_a"), f"fixture {source_id} away team")
        home, away = str(home_id), str(away_id)
        if source_id in source_sides or home not in teams or away not in teams or home == away:
            raise OfficialFplSeasonError(f"Duplicate fixture ID or unreviewed fixture teams for {source_id}")
        if (home_id, away_id) in directed_pairs:
            raise OfficialFplSeasonError(f"Duplicate home/away pairing for fixture {source_id}")
        directed_pairs.add((home_id, away_id))
        source_sides[source_id] = (home_id, away_id)
        appearances[home] += 1
        appearances[away] += 1

        flags = tuple(row.get(field) for field in _FIXTURE_FLAGS)
        if any(type(flag) is not bool for flag in flags):
            raise OfficialFplSeasonError(f"Fixture {source_id} has incomplete completion flags")
        minutes = _integer(row.get("minutes"), f"fixture {source_id} minutes", allow_zero=True)
        raw_event = row.get("event")
        event_id = None if raw_event is None else _integer(raw_event, f"fixture {source_id} event")
        raw_kickoff = row.get("kickoff_time")

        if flags == (True, True, True):
            if event_id is None or event_id not in events:
                raise OfficialFplSeasonError(f"Finished fixture {source_id} has no reviewed gameweek")
            if minutes != 90:
                raise OfficialFplSeasonError(f"Finished fixture {source_id} must have 90 minutes")
            home_goals = _integer(row.get("team_h_score"), f"fixture {source_id} home score", allow_zero=True)
            away_goals = _integer(row.get("team_a_score"), f"fixture {source_id} away score", allow_zero=True)
            kickoff = _kickoff(raw_kickoff, f"fixture {source_id} kickoff_time")
            fixtures[source_id] = (
                teams[home], teams[away], kickoff, event_id, home_goals, away_goals,
            )
            completed_weeks.add(event_id)
        elif flags == (False, False, False):
            if minutes != 0 or row.get("team_h_score") is not None or row.get("team_a_score") is not None:
                raise OfficialFplSeasonError(f"Scheduled fixture {source_id} contains result evidence")
            if event_id is not None and event_id not in events:
                raise OfficialFplSeasonError(f"Scheduled fixture {source_id} has an unknown gameweek")
            if raw_kickoff is not None:
                _kickoff(raw_kickoff, f"fixture {source_id} kickoff_time")
        else:
            raise OfficialFplSeasonError(f"Fixture {source_id} has inconsistent completion flags")

    if len(source_sides) != FIXTURE_COUNT or len(directed_pairs) != FIXTURE_COUNT:
        raise OfficialFplSeasonError("Fixture IDs or reviewed home/away pairs are not unique")
    if set(appearances) != set(teams) or any(count != 38 for count in appearances.values()):
        raise OfficialFplSeasonError("The 380 fixtures do not cover every reviewed team 38 times")
    if len(directed_pairs) != TEAM_COUNT * (TEAM_COUNT - 1):
        raise OfficialFplSeasonError("The fixture set does not contain one home match per team pairing")
    if not fixtures:
        raise OfficialFplSeasonError("No finished fixtures were found")
    return fixtures, source_sides, completed_weeks


def _summary_paths(folder: Path, elements: dict[str, str], managers: set[str]) -> dict[str, Path]:
    if not folder.is_dir():
        raise OfficialFplSeasonError(f"Missing official FPL element summaries directory {folder}")
    paths: dict[str, Path] = {}
    for path in folder.glob("element_*.json"):
        match = _SUMMARY_FILENAME.fullmatch(path.name)
        if match is None:
            raise OfficialFplSeasonError(f"Invalid official FPL summary filename {path.name!r}")
        source_id = str(_integer(int(match.group("element")), f"summary filename {path.name} element ID"))
        if source_id in paths:
            raise OfficialFplSeasonError(f"Multiple official FPL summaries for element {source_id}")
        paths[source_id] = path
    # Retrieval also saves manager element summaries when the bootstrap lists them;
    # they are not footballers and must not be loaded as player observations.
    for source_id in managers:
        paths.pop(source_id, None)
    expected, actual = set(elements), set(paths)
    if actual != expected:
        missing, unexpected = sorted(expected - actual), sorted(actual - expected)
        raise OfficialFplSeasonError(
            f"Official FPL summaries do not match bootstrap footballers; missing={missing[:5]}, "
            f"unexpected={unexpected[:5]}"
        )
    return paths


def _history_observations(
    summary_paths: dict[str, Path],
    elements: dict[str, str],
    teams: dict[str, str],
    fixtures: dict[str, Fixture],
    source_sides: dict[str, tuple[int, int]],
    events: dict[int, bool],
) -> list[Observation]:
    observations: list[Observation] = []
    seen: set[tuple[str, str, int]] = set()
    observed_fixtures: set[str] = set()
    observed_weeks: set[int] = set()

    for element_id, path in summary_paths.items():
        payload = _object(_read_json(path), f"element summary {element_id}")
        summary_fixtures = _list(payload.get("fixtures"), f"element {element_id} fixtures")
        history = _list(payload.get("history"), f"element {element_id} history")
        history_past = _list(payload.get("history_past"), f"element {element_id} history_past")
        # These lists are part of the saved official summary envelope; upcoming fixtures are
        # intentionally not normalized into historical match observations.
        del summary_fixtures, history_past
        for index, raw_row in enumerate(history):
            row = _object(raw_row, f"element {element_id} history row {index}")
            if _integer(row.get("element"), f"element {element_id} history row {index} element") != int(element_id):
                raise OfficialFplSeasonError(f"History row is filed under the wrong element summary {element_id}")
            source_fixture = str(_integer(row.get("fixture"), f"element {element_id} history fixture"))
            fixture = fixtures.get(source_fixture)
            sides = source_sides.get(source_fixture)
            if fixture is None or sides is None:
                raise OfficialFplSeasonError(
                    f"Element {element_id} history references unknown or unfinished fixture {source_fixture}"
                )
            raw_is_home = row.get("was_home")
            if type(raw_is_home) is not bool:
                raise OfficialFplSeasonError(f"Element {element_id} fixture {source_fixture} has invalid was_home")
            home_id, away_id = sides
            expected_opponent = away_id if raw_is_home else home_id
            opponent_id = _integer(row.get("opponent_team"), f"element {element_id} opponent_team")
            if opponent_id != expected_opponent:
                raise OfficialFplSeasonError(f"Element {element_id} fixture {source_fixture} opponent differs")
            week = _integer(row.get("round"), f"element {element_id} fixture {source_fixture} round")
            if week != fixture[3] or week not in events:
                raise OfficialFplSeasonError(f"Element {element_id} fixture {source_fixture} gameweek differs")
            kickoff = _kickoff(row.get("kickoff_time"), f"element {element_id} fixture {source_fixture} kickoff_time")
            if kickoff != fixture[2]:
                raise OfficialFplSeasonError(f"Element {element_id} fixture {source_fixture} kickoff differs")
            home_score = _integer(
                row.get("team_h_score"), f"element {element_id} fixture {source_fixture} home score", allow_zero=True,
            )
            away_score = _integer(
                row.get("team_a_score"), f"element {element_id} fixture {source_fixture} away score", allow_zero=True,
            )
            if (home_score, away_score) != fixture[4:]:
                raise OfficialFplSeasonError(f"Element {element_id} fixture {source_fixture} score differs")
            minutes = _integer(
                row.get("minutes"), f"element {element_id} fixture {source_fixture} minutes", allow_zero=True,
            )
            canonical_club = teams[str(home_id if raw_is_home else away_id)]
            observation_key = (element_id, source_fixture, week)
            if observation_key in seen:
                raise OfficialFplSeasonError(f"Duplicate player/fixture/gameweek observation {observation_key}")
            seen.add(observation_key)
            observed_fixtures.add(source_fixture)
            observed_weeks.add(week)
            observations.append((
                element_id, elements[element_id], week, canonical_club, kickoff, minutes, source_fixture,
            ))

    missing_fixtures = set(fixtures) - observed_fixtures
    if missing_fixtures:
        raise OfficialFplSeasonError(
            f"Completed fixtures lack history observations: {sorted(missing_fixtures, key=int)[:5]}"
        )
    completed_events = {event_id for event_id, finished in events.items() if finished}
    if not completed_events <= observed_weeks:
        missing_weeks = sorted(completed_events - observed_weeks)
        raise OfficialFplSeasonError(f"Completed bootstrap gameweeks lack history observations: {missing_weeks}")
    return observations


def read_official_fpl_season(raw_root: Path, season: str) -> OfficialFplSeasonEvidence:
    """Parse saved official FPL payloads without accessing or modifying a database."""
    if not isinstance(season, str):
        raise OfficialFplSeasonError("Season must be a YYYY-YY string")
    try:
        validate_season(season)
        root = Path(raw_root)
        bootstrap = _object(_read_json(root / "bootstrap-static.json"), "bootstrap-static.json")
        derived_season = _derive_season(bootstrap)
        if derived_season != season:
            raise OfficialFplSeasonError(
                f"Bootstrap season {derived_season} does not match requested season {season}"
            )
        _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
        teams = _bootstrap_teams(bootstrap, aliases)
        elements, managers = _bootstrap_elements(bootstrap)
        events = _bootstrap_events(bootstrap)
        fixtures_payload = _read_json(root / "fixtures.json")
        fixtures, source_sides, _ = _fixture_rows(fixtures_payload, teams, events)
        summary_paths = _summary_paths(root / "element_summaries", elements, managers)
        observations = _history_observations(
            summary_paths, elements, teams, fixtures, source_sides, events,
        )
    except (CanonicalTeamsValidationError, GameweekTeamsError, OfficialFplTeamsValidationError) as error:
        raise OfficialFplSeasonError(str(error)) from error
    return OfficialFplSeasonEvidence(season, teams, elements, fixtures, observations)
