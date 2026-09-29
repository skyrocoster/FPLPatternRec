"""Seed reviewed clubs; optionally resolve staged official FPL team IDs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
import unicodedata

from ..reference import TEAM_REFERENCE_PATH
from .official_fpl_teams import validate_season
from .sqlite import DATABASE_PATH, connect_database

COMPETITION_KEY = "premier-league"
COMPETITION_NAME = "Premier League"
SOURCE_NAMESPACE = "fpl.team.id"
MAPPING_TABLES = {"competitions", "seasons", "team_source_ids"}


class CanonicalTeamsValidationError(ValueError):
    """Raised before accepting an uncertain or conflicting canonical identity."""


@dataclass(frozen=True)
class CanonicalTeamsLoadSummary:
    season: str | None
    club_count: int
    mapped_team_count: int


def _normalize(name: str) -> str:
    """Apply the reviewed reference's whole-name matching rules, never fuzzy matching."""
    name = unicodedata.normalize("NFKC", name).casefold().replace("\u2019", "'")
    name = name.replace("&", " and ").replace(".", "")
    return " ".join(name.split())


def _read_clubs(reference_path: Path) -> tuple[list[tuple[str, str]], dict[str, str]]:
    try:
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CanonicalTeamsValidationError(f"Cannot read club reference {reference_path}: {error}") from error
    if not isinstance(reference, dict) or reference.get("dataset") != "premier_league_team_names":
        raise CanonicalTeamsValidationError("Expected the reviewed Premier League club reference.")
    if reference.get("schema_version") != 1 or not isinstance(reference.get("clubs"), list):
        raise CanonicalTeamsValidationError("Unsupported Premier League club reference schema.")

    clubs: list[tuple[str, str]] = []
    aliases: dict[str, str] = {}
    seen_keys: set[str] = set()
    for club in reference["clubs"]:
        if not isinstance(club, dict):
            raise CanonicalTeamsValidationError("Club reference contains a non-object club.")
        key, name, names = club.get("id"), club.get("canonical_name"), club.get("aliases")
        if (not isinstance(key, str) or not key.strip() or
                not isinstance(name, str) or not name.strip() or
                not isinstance(names, list) or any(not isinstance(a, str) or not a.strip() for a in names)):
            raise CanonicalTeamsValidationError("Club reference contains an invalid key, name or aliases.")
        if key in seen_keys:
            raise CanonicalTeamsValidationError(f"Duplicate club key {key!r}.")
        seen_keys.add(key)
        clubs.append((key, name))
        for alias in (name, *names):
            normalized = _normalize(alias)
            previous = aliases.get(normalized)
            if previous is not None and previous != key:
                raise CanonicalTeamsValidationError(
                    f"Ambiguous reviewed club alias {alias!r}: {previous!r} and {key!r}."
                )
            aliases[normalized] = key

    scope = reference.get("scope")
    if not clubs or not isinstance(scope, dict) or scope.get("club_count") != len(clubs):
        raise CanonicalTeamsValidationError("Club reference count is missing or inconsistent.")
    return clubs, aliases


def _ensure_entity(
    connection: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    values: tuple[object, ...],
    other_columns: tuple[str, ...],
) -> int:
    id_column = {"competitions": "competition_id", "teams": "team_id"}[table]
    columns = ", ".join((id_column, *other_columns))
    row = connection.execute(f"SELECT {columns} FROM {table} WHERE {key_column} = ?", (key,)).fetchone()
    if row is not None:
        if row[1:] != values:
            raise CanonicalTeamsValidationError(
                f"Existing {table} row for {key!r} differs from the reviewed reference; review it."
            )
        return row[0]
    insert_columns = ", ".join((key_column, *other_columns))
    placeholders = ", ".join("?" for _ in range(len(values) + 1))
    return connection.execute(
        f"INSERT INTO {table} ({insert_columns}) VALUES ({placeholders}) RETURNING {id_column}",
        (key, *values),
    ).fetchone()[0]


def _ensure_season(connection: sqlite3.Connection, competition_id: int, label: str) -> int:
    start_year = int(label[:4])
    end_year = start_year + 1
    row = connection.execute(
        "SELECT season_id, start_year, end_year FROM seasons "
        "WHERE competition_id = ? AND label = ?", (competition_id, label),
    ).fetchone()
    if row is not None:
        if row[1:] != (start_year, end_year):
            raise CanonicalTeamsValidationError(f"Existing season {label!r} has conflicting years.")
        return row[0]
    return connection.execute(
        "INSERT INTO seasons (competition_id, label, start_year, end_year) "
        "VALUES (?, ?, ?, ?) RETURNING season_id",
        (competition_id, label, start_year, end_year),
    ).fetchone()[0]


def load_canonical_teams(
    season: str | None = None,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
) -> CanonicalTeamsLoadSummary:
    """Seed clubs from JSON; with a season, also add scoped, accepted FPL IDs."""
    if season is not None:
        validate_season(season)
    clubs, aliases = _read_clubs(Path(reference_path))
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        required = {"teams"} | (MAPPING_TABLES if season is not None else set())
        missing = required - existing
        if missing:
            raise CanonicalTeamsValidationError(
                f"Canonical tables missing ({', '.join(sorted(missing))}); apply base_tables.sql first."
            )
        resolved: list[tuple[str, str]] = []
        if season is not None:
            staged = connection.execute(
                "SELECT softe_team_id, softe_name FROM stg_official_fpl_teams "
                "WHERE softe_season = ? ORDER BY softe_team_id", (season,),
            ).fetchall()
            if not staged:
                raise CanonicalTeamsValidationError(f"No staged official FPL teams for {season}.")

            seen_clubs: set[str] = set()
            for source_id, name in staged:
                if type(source_id) is not int or source_id <= 0 or not isinstance(name, str):
                    raise CanonicalTeamsValidationError("Staged FPL team has an invalid ID or name.")
                club_key = aliases.get(_normalize(name))
                if club_key is None:
                    raise CanonicalTeamsValidationError(f"Unknown FPL team name {name!r}; review aliases.")
                if club_key in seen_clubs:
                    raise CanonicalTeamsValidationError(f"Multiple FPL team IDs resolve to {club_key!r}.")
                seen_clubs.add(club_key)
                resolved.append((str(source_id), club_key))

        ids = {
            key: _ensure_entity(connection, "teams", "team_key", key, (name,), ("name",))
            for key, name in clubs
        }
        if season is not None:
            scope = f"{COMPETITION_KEY}:{season}"
            competition_id = _ensure_entity(
                connection, "competitions", "competition_key", COMPETITION_KEY,
                (COMPETITION_NAME,), ("name",),
            )
            _ensure_season(connection, competition_id, season)
            for source_id, club_key in resolved:
                row = connection.execute(
                    "SELECT team_id FROM team_source_ids "
                    "WHERE source_namespace = ? AND source_scope = ? AND source_id = ?",
                    (SOURCE_NAMESPACE, scope, source_id),
                ).fetchone()
                if row is not None and row[0] != ids[club_key]:
                    raise CanonicalTeamsValidationError(
                        f"FPL team {source_id} in {scope} is mapped to a different club; review it."
                    )
                if row is None:
                    connection.execute(
                        "INSERT INTO team_source_ids "
                        "(source_namespace, source_scope, source_id, team_id) VALUES (?, ?, ?, ?)",
                        (SOURCE_NAMESPACE, scope, source_id, ids[club_key]),
                    )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return CanonicalTeamsLoadSummary(season, len(clubs), len(resolved))
