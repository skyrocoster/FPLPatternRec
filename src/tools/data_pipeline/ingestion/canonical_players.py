"""Resolve one saved official FPL season into canonical player identities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import sqlite3

from .official_fpl_teams import OfficialFplTeamsValidationError, _derive_season, validate_season
from .sqlite import DATABASE_PATH, connect_database

COMPETITION_KEY = "premier-league"
ID_NAMESPACE = "fpl.element.id"
CODE_NAMESPACE = "fpl.element.code"
PLAYER_TYPES = {1, 2, 3, 4}
MANAGER_TYPE = 5


class CanonicalPlayersValidationError(ValueError):
    """Raised when an FPL observation cannot safely be made canonical."""


@dataclass(frozen=True)
class CanonicalPlayersLoadSummary:
    season: str
    player_count: int
    excluded_manager_count: int


def _read_players(bootstrap_path: Path, season: str) -> tuple[list[tuple[str, str, str, str | None]], int]:
    validate_season(season)
    try:
        payload = json.loads(Path(bootstrap_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CanonicalPlayersValidationError(
            f"Cannot read official FPL bootstrap {bootstrap_path}: {error}"
        ) from error
    if not isinstance(payload, dict):
        raise CanonicalPlayersValidationError("The official FPL bootstrap must be an object.")
    try:
        actual_season = _derive_season(payload)
    except OfficialFplTeamsValidationError as error:
        raise CanonicalPlayersValidationError(str(error)) from error
    if actual_season != season:
        raise CanonicalPlayersValidationError(
            f"Bootstrap belongs to {actual_season}, not requested season {season}."
        )
    elements = payload.get("elements")
    if not isinstance(elements, list) or not elements:
        raise CanonicalPlayersValidationError("Bootstrap elements must be a non-empty list.")

    players: list[tuple[str, str, str, str | None]] = []
    seen_ids: set[int] = set()
    seen_codes: set[int] = set()
    managers = 0
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            raise CanonicalPlayersValidationError(f"Element {index} is not an object.")
        source_id, code, kind = (element.get(field) for field in ("id", "code", "element_type"))
        if (type(source_id) is not int or source_id <= 0 or
                type(code) is not int or code <= 0 or type(kind) is not int or
                kind not in PLAYER_TYPES | {MANAGER_TYPE}):
            raise CanonicalPlayersValidationError(f"Element {index} has an invalid ID, code or type.")
        if source_id in seen_ids or code in seen_codes:
            raise CanonicalPlayersValidationError(f"Duplicate FPL element ID or code at index {index}.")
        seen_ids.add(source_id)
        seen_codes.add(code)
        if kind == MANAGER_TYPE:
            managers += 1
            continue

        first, second = element.get("first_name"), element.get("second_name")
        if not isinstance(first, str) or not first.strip() or not isinstance(second, str) or not second.strip():
            raise CanonicalPlayersValidationError(f"Element {index} has an incomplete full name.")
        name = f"{first.strip()} {second.strip()}"
        dob = element.get("birth_date")
        if dob is not None:
            if not isinstance(dob, str) or len(dob) != 10:
                raise CanonicalPlayersValidationError(f"Element {index} has an invalid birth date.")
            try:
                if date.fromisoformat(dob).isoformat() != dob:
                    raise ValueError("noncanonical birth date")
            except ValueError as error:
                raise CanonicalPlayersValidationError(f"Element {index} has an invalid birth date.") from error
        players.append((str(source_id), str(code), name, dob))
    if not players:
        raise CanonicalPlayersValidationError("Bootstrap contains no football players.")
    return players, managers


def load_canonical_players(
    season: str,
    bootstrap_path: Path,
    database_path: Path = DATABASE_PATH,
) -> CanonicalPlayersLoadSummary:
    """Add only unambiguous players; never infer cross-season identity from a code or name."""
    players, managers = _read_players(bootstrap_path, season)
    scope = f"{COMPETITION_KEY}:{season}"
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        if not {"players", "player_source_ids"} <= existing:
            raise CanonicalPlayersValidationError("Canonical player tables missing; apply base_tables.sql first.")

        # Take this snapshot before inserting: two distinct source IDs may legitimately share a name.
        preexisting_names = {row[0] for row in connection.execute("SELECT display_name FROM players")}
        resolved_players: set[int] = set()
        for source_id, code, name, dob in players:
            matched = []
            for namespace, value in ((ID_NAMESPACE, source_id), (CODE_NAMESPACE, code)):
                row = connection.execute(
                    "SELECT player_id FROM player_source_ids "
                    "WHERE source_namespace = ? AND source_scope = ? AND source_id = ?",
                    (namespace, scope, value),
                ).fetchone()
                matched.append(row[0] if row else None)
            if matched[0] != matched[1]:
                raise CanonicalPlayersValidationError(
                    f"FPL element {source_id} has incomplete or conflicting mappings; review it."
                )
            if matched[0] is None:
                if name in preexisting_names:
                    raise CanonicalPlayersValidationError(
                        f"FPL element {source_id} resembles an unmapped existing player; review it."
                    )
                player_id = connection.execute(
                    "INSERT INTO players (display_name, date_of_birth) VALUES (?, ?) RETURNING player_id",
                    (name, dob),
                ).fetchone()[0]
                connection.executemany(
                    "INSERT INTO player_source_ids "
                    "(source_namespace, source_scope, source_id, player_id) VALUES (?, ?, ?, ?)",
                    ((namespace, scope, value, player_id) for namespace, value in
                     ((ID_NAMESPACE, source_id), (CODE_NAMESPACE, code))),
                )
            else:
                player_id = matched[0]
                row = connection.execute(
                    "SELECT display_name, date_of_birth FROM players WHERE player_id = ?", (player_id,)
                ).fetchone()
                if row is None or row[0] != name or (dob is not None and row[1] != dob):
                    raise CanonicalPlayersValidationError(
                        f"FPL element {source_id} differs from the existing canonical player; review it."
                    )
            if player_id in resolved_players:
                raise CanonicalPlayersValidationError(
                    f"Multiple FPL elements resolve to player {player_id}; review them."
                )
            resolved_players.add(player_id)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return CanonicalPlayersLoadSummary(season, len(players), managers)
