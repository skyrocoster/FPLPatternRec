"""Resolve saved FPL seasons backwards without assigning players to clubs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import unicodedata

from .canonical_players import CODE_NAMESPACE, COMPETITION_KEY, ID_NAMESPACE, MANAGER_TYPE, PLAYER_TYPES
from .sqlite import DATABASE_PATH, connect_database

CURRENT_SEASON = "2026-27"
EARLIEST_SEASON = "2016-17"
ARCHIVE_SEASONS = {f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2026)}
REQUIRED_FIELDS = {
    "id", "code", "element_type", "first_name", "second_name",
}

# A specifically reviewed code change, not a general name/team matching rule.
# 2019-20 element 659 (Aston Villa, Kaine Hayden, code 490098) is the same
# Kaine Kesler-Hayden as later code 465390. See docs/DATA_PIPELINE.md.
REVIEWED_CODE_CHANGE = {("2019-20", "659", "490098"): ("465390", "Kaine Hayden", "7")}

# These equal names identify DIFFERENT footballers (three pairs co-occur within
# a season; the other three have distinct generations and later dated evidence).
REVIEWED_HOMONYMS = {
    frozenset(pair) for pair in (
        ("41792", "447715"), ("78007", "577725"), ("112139", "613232"),
        ("115556", "152898"), ("75826", "95463"), ("240796", "515501"),
    )
}


class ArchivePlayersValidationError(ValueError):
    """Raised before accepting an uncertain archived FPL player identity."""


@dataclass(frozen=True)
class ArchivePlayersLoadSummary:
    season: str
    player_count: int
    linked_player_count: int
    archive_only_player_count: int
    excluded_manager_count: int


def _read_csv(path: Path, fields: set[str]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None or len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ArchivePlayersValidationError(f"Missing or repeated CSV header in {path}.")
            if not fields <= set(reader.fieldnames):
                raise ArchivePlayersValidationError(f"Missing required CSV fields in {path}.")
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as error:
        raise ArchivePlayersValidationError(f"Cannot read FPL archive {path}: {error}") from error
    if not rows or any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ArchivePlayersValidationError(f"Empty or malformed FPL archive {path}.")
    return rows


def _identifier(value: str, field: str) -> str:
    if not value.isascii() or not value.isdecimal() or int(value) <= 0 or str(int(value)) != value:
        raise ArchivePlayersValidationError(f"Invalid archive {field} {value!r}.")
    return value


def _name(row: dict[str, str]) -> str:
    first, second = row["first_name"].strip(), row["second_name"].strip()
    if not first or not second or first == "None" or second == "None":
        raise ArchivePlayersValidationError("Archive player has an incomplete full name.")
    return f"{first} {second}"


def _birth_date(value: str | None) -> str | None:
    if value in ("", "None", None):
        return None
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError("noncanonical date")
    except ValueError as error:
        raise ArchivePlayersValidationError(f"Invalid archive birth date {value!r}.") from error
    return value


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(character for character in text if not unicodedata.combining(character)).split())


def _shared_name_tokens(previous_name: str, current_name: str) -> bool:
    previous_parts = {part for part in re.findall(r"\w+", _normalize(previous_name)) if len(part) > 2}
    current_parts = {part for part in re.findall(r"\w+", _normalize(current_name)) if len(part) > 2}
    return bool(previous_parts & current_parts)


def _compatible(previous_name: str, previous_dob: str | None,
                current_name: str, current_dob: str | None) -> bool:
    if previous_dob is None or current_dob is None:
        # A code on its own is not enough when either date is unknown.
        return _normalize(previous_name) == _normalize(current_name)
    if previous_dob != current_dob:
        return False
    # A verified DOB and FPL code permit nicknames/shortened multi-part names,
    # but not an entirely unrelated name under the same code.
    return _shared_name_tokens(previous_name, current_name)


def _compatible_undated_history(previous_name: str, previous_dob: str | None,
                                current_name: str, current_dob: str | None) -> bool:
    """Require corroborating name tokens where early FPL files have no DOB."""
    if previous_dob is not None and current_dob is not None and previous_dob != current_dob:
        return False
    return _shared_name_tokens(previous_name, current_name)


def _read_players(players_path: Path, idlist_path: Path) -> tuple[list[tuple[str, str, str, str | None, str | None]], int]:
    rows = _read_csv(players_path, REQUIRED_FIELDS)
    names = _read_csv(idlist_path, {"id", "first_name", "second_name"})
    idlist: dict[str, str] = {}
    for row in names:
        source_id = _identifier(row["id"], "idlist ID")
        if source_id in idlist:
            raise ArchivePlayersValidationError(f"Duplicate idlist ID {source_id}.")
        idlist[source_id] = _name(row)

    players: list[tuple[str, str, str, str | None, str | None]] = []
    seen_ids: set[str] = set()
    seen_codes: set[str] = set()
    managers = 0
    for row in rows:
        source_id, code = _identifier(row["id"], "element ID"), _identifier(row["code"], "code")
        if source_id in seen_ids or code in seen_codes:
            raise ArchivePlayersValidationError(f"Duplicate archive element ID or code {source_id}.")
        seen_ids.add(source_id)
        seen_codes.add(code)
        if row.get("has_temporary_code", "False") != "False":
            raise ArchivePlayersValidationError(f"Element {source_id} has an unverified temporary code.")
        kind = _identifier(row["element_type"], "element type")
        if int(kind) == MANAGER_TYPE:
            managers += 1
            continue
        if int(kind) not in PLAYER_TYPES:
            raise ArchivePlayersValidationError(f"Element {source_id} has an unknown type.")
        name = _name(row)
        if idlist.get(source_id) != name:
            raise ArchivePlayersValidationError(f"Element {source_id} differs from the archive idlist.")
        players.append((source_id, code, name, _birth_date(row.get("birth_date")), row.get("team_code")))
    if set(idlist) != seen_ids or not players:
        raise ArchivePlayersValidationError("Archive player list and idlist disagree or contain no football players.")
    return players, managers


def load_archive_players(
    season: str,
    players_path: Path,
    idlist_path: Path,
    database_path: Path = DATABASE_PATH,
) -> ArchivePlayersLoadSummary:
    """Load one reviewed season, after later seasons, using scoped FPL IDs."""
    if season not in ARCHIVE_SEASONS:
        raise ArchivePlayersValidationError(
            f"This archive loader supports {EARLIEST_SEASON} through 2025-26 only."
        )
    players, managers = _read_players(players_path, idlist_path)
    scope = f"{COMPETITION_KEY}:{season}"
    current_scope = f"{COMPETITION_KEY}:{CURRENT_SEASON}"
    connection = connect_database(database_path)
    linked = 0
    archive_only = 0
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {"players", "player_source_ids"} <= existing:
            raise ArchivePlayersValidationError("Canonical player tables missing; apply base_tables.sql first.")
        future_mappings = connection.execute(
            "SELECT source_scope, source_id, player_id FROM player_source_ids "
            "WHERE source_namespace = ? AND source_scope > ? AND source_scope <= ?",
            (CODE_NAMESPACE, scope, current_scope),
        ).fetchall()
        next_year = int(season[:4]) + 1
        next_scope = f"{COMPETITION_KEY}:{next_year}-{(next_year + 1) % 100:02d}"
        if connection.execute(
            "SELECT player_id FROM player_source_ids WHERE source_namespace = ? AND source_scope = ? LIMIT 1",
            (CODE_NAMESPACE, next_scope),
        ).fetchone() is None:
            if season == "2025-26":
                raise ArchivePlayersValidationError(f"Load canonical {CURRENT_SEASON} FPL players first.")
            raise ArchivePlayersValidationError(f"Load {next_scope} before {scope}.")
        if not future_mappings:
            raise ArchivePlayersValidationError(f"Load canonical {CURRENT_SEASON} FPL players first.")
        targets: dict[str, set[int]] = {}
        codes_by_player: dict[int, set[str]] = {}
        accepted_scopes = {f"{COMPETITION_KEY}:{label}" for label in ARCHIVE_SEASONS | {CURRENT_SEASON}}
        for mapped_scope, mapped_code, mapped_id in future_mappings:
            if mapped_scope not in accepted_scopes:
                raise ArchivePlayersValidationError(f"Unknown FPL player mapping scope {mapped_scope!r}.")
            targets.setdefault(mapped_code, set()).add(mapped_id)
            codes_by_player.setdefault(mapped_id, set()).add(mapped_code)
        preexisting_names: dict[str, set[int]] = {}
        for player_id, player_name in connection.execute("SELECT player_id, display_name FROM players"):
            preexisting_names.setdefault(_normalize(player_name), set()).add(player_id)
        resolved_players: set[int] = set()
        for source_id, code, name, dob, team_code in players:
            mapped = []
            for namespace, value in ((ID_NAMESPACE, source_id), (CODE_NAMESPACE, code)):
                row = connection.execute(
                    "SELECT player_id FROM player_source_ids "
                    "WHERE source_namespace = ? AND source_scope = ? AND source_id = ?",
                    (namespace, scope, value),
                ).fetchone()
                mapped.append(row[0] if row else None)
            if mapped[0] != mapped[1]:
                raise ArchivePlayersValidationError(f"Element {source_id} has conflicting or partial mappings.")
            anchor_code = code
            reviewed = REVIEWED_CODE_CHANGE.get((season, source_id, code))
            if reviewed is not None:
                anchor_code, expected_name, expected_team_code = reviewed
                if name != expected_name or team_code != expected_team_code:
                    raise ArchivePlayersValidationError(f"Reviewed code change for {source_id} no longer agrees.")
                if targets.get(code) and targets[code] != targets.get(anchor_code):
                    raise ArchivePlayersValidationError(f"Reviewed code change for {source_id} conflicts with later IDs.")
            anchors = targets.get(anchor_code, set())
            if len(anchors) > 1:
                raise ArchivePlayersValidationError(f"Code {anchor_code} has conflicting later identities.")
            current_id = next(iter(anchors), None)
            if mapped[0] is not None and current_id is not None and mapped[0] != current_id:
                raise ArchivePlayersValidationError(f"Element {source_id} conflicts with its later identity.")

            player_id = mapped[0] if mapped[0] is not None else current_id
            if player_id is not None:
                current = connection.execute(
                    "SELECT display_name, date_of_birth FROM players WHERE player_id = ?", (player_id,)
                ).fetchone()
                compatible = _compatible if season == "2025-26" else _compatible_undated_history
                if current is None or not compatible(name, dob, *current):
                    raise ArchivePlayersValidationError(
                        f"Element {source_id} code {code} has conflicting name or birth date; review it."
                    )
            else:
                for candidate_id in preexisting_names.get(_normalize(name), set()):
                    candidate_codes = codes_by_player.get(candidate_id, set())
                    if not candidate_codes or any(
                        frozenset((code, candidate_code)) not in REVIEWED_HOMONYMS
                        for candidate_code in candidate_codes
                    ):
                        raise ArchivePlayersValidationError(
                            f"Element {source_id} resembles an unmapped player; review it."
                        )
                player_id = connection.execute(
                    "INSERT INTO players (display_name, date_of_birth) VALUES (?, ?) RETURNING player_id",
                    (name, dob),
                ).fetchone()[0]

            if player_id in resolved_players:
                raise ArchivePlayersValidationError(f"Multiple archive elements resolve to player {player_id}.")
            resolved_players.add(player_id)
            if current_id is None:
                archive_only += 1
            else:
                linked += 1
            if mapped[0] is None:
                connection.executemany(
                    "INSERT INTO player_source_ids "
                    "(source_namespace, source_scope, source_id, player_id) VALUES (?, ?, ?, ?)",
                    ((namespace, scope, value, player_id) for namespace, value in
                     ((ID_NAMESPACE, source_id), (CODE_NAMESPACE, code))),
                )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return ArchivePlayersLoadSummary(season, len(players), linked, archive_only, managers)
