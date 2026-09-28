"""Validate and load official FPL bootstrap teams into the staging database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .sqlite import DATABASE_PATH, connect_database

TABLE_NAME = "stg_official_fpl_teams"
SEASON_PATTERN = re.compile(r"(?P<start>\d{4})-(?P<end>\d{2})\Z")

INTEGER_FIELDS = (
    ("softe_team_id", "id"),
    ("softe_code", "code"),
    ("softe_pulse_id", "pulse_id"),
    ("softe_position", "position"),
    ("softe_played", "played"),
    ("softe_win", "win"),
    ("softe_draw", "draw"),
    ("softe_loss", "loss"),
    ("softe_points", "points"),
    ("softe_strength_overall_home", "strength_overall_home"),
    ("softe_strength_overall_away", "strength_overall_away"),
    ("softe_strength_attack_home", "strength_attack_home"),
    ("softe_strength_attack_away", "strength_attack_away"),
    ("softe_strength_defence_home", "strength_defence_home"),
    ("softe_strength_defence_away", "strength_defence_away"),
)
TEXT_FIELDS = (
    ("softe_name", "name"),
    ("softe_short_name", "short_name"),
)
INSERT_COLUMNS = (
    "softe_season",
    *(column for column, _ in INTEGER_FIELDS),
    *(column for column, _ in TEXT_FIELDS),
    "softe_link_url",
    "softe_unavailable",
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS stg_official_fpl_teams (
    softe_season TEXT NOT NULL,
    softe_team_id INTEGER NOT NULL,
    softe_code INTEGER NOT NULL,
    softe_pulse_id INTEGER NOT NULL,
    softe_position INTEGER NOT NULL,
    softe_played INTEGER NOT NULL,
    softe_win INTEGER NOT NULL,
    softe_draw INTEGER NOT NULL,
    softe_loss INTEGER NOT NULL,
    softe_points INTEGER NOT NULL,
    softe_strength_overall_home INTEGER NOT NULL,
    softe_strength_overall_away INTEGER NOT NULL,
    softe_strength_attack_home INTEGER NOT NULL,
    softe_strength_attack_away INTEGER NOT NULL,
    softe_strength_defence_home INTEGER NOT NULL,
    softe_strength_defence_away INTEGER NOT NULL,
    softe_name TEXT NOT NULL,
    softe_short_name TEXT NOT NULL,
    softe_link_url TEXT,
    softe_unavailable BOOLEAN NOT NULL,
    PRIMARY KEY (softe_season, softe_team_id)
)
"""


class OfficialFplTeamsValidationError(ValueError):
    """Raised when a bootstrap payload cannot safely populate the teams table."""


@dataclass(frozen=True)
class OfficialFplTeamsLoadSummary:
    season: str
    team_count: int


def validate_season(season: str) -> str:
    """Require the compact FPL YYYY-YY season form, including consecutive years."""
    match = SEASON_PATTERN.fullmatch(season)
    if match is None:
        raise OfficialFplTeamsValidationError(
            f"Invalid season {season!r}; expected YYYY-YY, such as 2026-27."
        )
    start_year = int(match.group("start"))
    if start_year == 0 or start_year == 9999 or int(match.group("end")) != (start_year + 1) % 100:
        raise OfficialFplTeamsValidationError(
            f"Invalid season {season!r}; the end year must immediately follow the start year."
        )
    return season


def _derive_season(payload: dict[str, Any]) -> str:
    events = payload.get("events")
    if not isinstance(events, list) or not events or not isinstance(events[0], dict):
        raise OfficialFplTeamsValidationError(
            "The bootstrap must contain a first gameweek event to derive its season."
        )
    deadline = events[0].get("deadline_time")
    if not isinstance(deadline, str) or not deadline:
        raise OfficialFplTeamsValidationError(
            "The first gameweek event must have a valid deadline_time to derive its season."
        )
    try:
        deadline_date = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
    except ValueError as error:
        raise OfficialFplTeamsValidationError(
            "The first gameweek deadline_time is not a valid ISO date/time."
        ) from error

    start_year = deadline_date.year if deadline_date.month >= 7 else deadline_date.year - 1
    season = f"{start_year:04d}-{(start_year + 1) % 100:02d}"
    return validate_season(season)


def _required_value(row: dict[str, Any], field: str, index: int) -> Any:
    if field not in row:
        raise OfficialFplTeamsValidationError(
            f"Team at index {index} is missing required field {field!r}."
        )
    return row[field]


def _validate_teams(payload: dict[str, Any], season: str) -> list[tuple[Any, ...]]:
    teams = payload.get("teams")
    if not isinstance(teams, list) or not teams:
        raise OfficialFplTeamsValidationError("The bootstrap teams array must be a non-empty list.")

    validated: list[tuple[Any, ...]] = []
    seen_ids: set[int] = set()
    for index, row in enumerate(teams):
        if not isinstance(row, dict):
            raise OfficialFplTeamsValidationError(f"Team at index {index} must be a JSON object.")

        values: list[Any] = [season]
        for _, field in INTEGER_FIELDS:
            value = _required_value(row, field, index)
            if type(value) is not int:
                raise OfficialFplTeamsValidationError(
                    f"Team at index {index} field {field!r} must be an integer."
                )
            values.append(value)

        team_id = values[1]
        if team_id in seen_ids:
            raise OfficialFplTeamsValidationError(
                f"The bootstrap contains duplicate team id {team_id}."
            )
        seen_ids.add(team_id)

        for _, field in TEXT_FIELDS:
            value = _required_value(row, field, index)
            if not isinstance(value, str):
                raise OfficialFplTeamsValidationError(
                    f"Team at index {index} field {field!r} must be text."
                )
            values.append(value)

        link_url = row.get("link_url")
        if link_url is not None and not isinstance(link_url, str):
            raise OfficialFplTeamsValidationError(
                f"Team at index {index} field 'link_url' must be text or null."
            )
        values.append(None if link_url == "" else link_url)

        unavailable = _required_value(row, "unavailable", index)
        if not isinstance(unavailable, bool):
            raise OfficialFplTeamsValidationError(
                f"Team at index {index} field 'unavailable' must be a boolean."
            )
        values.append(int(unavailable))
        validated.append(tuple(values))
    return validated


def _read_and_validate(bootstrap_path: Path, season_override: str | None) -> tuple[str, list[tuple[Any, ...]]]:
    if season_override is not None:
        validate_season(season_override)
    try:
        payload = json.loads(Path(bootstrap_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise OfficialFplTeamsValidationError(
            f"Could not read official FPL bootstrap JSON at {bootstrap_path}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise OfficialFplTeamsValidationError("The official FPL bootstrap must be a JSON object.")

    season = season_override if season_override is not None else _derive_season(payload)
    return season, _validate_teams(payload, season)


def load_official_fpl_teams(
    bootstrap_path: Path,
    database_path: Path = DATABASE_PATH,
    season: str | None = None,
) -> OfficialFplTeamsLoadSummary:
    """Replace one complete season of team rows in a single SQLite transaction."""
    resolved_season, teams = _read_and_validate(bootstrap_path, season)
    quoted_columns = ", ".join(INSERT_COLUMNS)
    placeholders = ", ".join("?" for _ in INSERT_COLUMNS)

    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(CREATE_TABLE_SQL)
        connection.execute(
            "DELETE FROM stg_official_fpl_teams WHERE softe_season = ?",
            (resolved_season,),
        )
        connection.executemany(
            f"INSERT INTO stg_official_fpl_teams ({quoted_columns}) VALUES ({placeholders})",
            teams,
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    return OfficialFplTeamsLoadSummary(season=resolved_season, team_count=len(teams))
