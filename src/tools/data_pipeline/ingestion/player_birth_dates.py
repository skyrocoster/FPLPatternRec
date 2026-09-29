"""Conservative, source-corroborated backfill of missing canonical player DOBs."""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
import gzip
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
from typing import NamedTuple
import unicodedata
from urllib.parse import urlsplit

from ..reference import REVIEWED_PLAYER_BIRTH_DATES_PATH
from .canonical_teams import TEAM_REFERENCE_PATH, _normalize as club_name, _read_clubs
from .premier_league_player_birth_dates import roster_birth_dates
from .sqlite import DATABASE_PATH, connect_database
from ..retrieval.wikidata_transfermarkt import BATCH_SIZE, _tm_ids, fpl_tm_ids


class BirthDateEvidenceError(ValueError):
    """The saved evidence is missing or cannot be used safely."""


class BirthDateProposalCategory(str, Enum):
    FPL = "FPL"
    PREMIER_LEAGUE_OPTA = "official PL API Opta"
    PREMIER_LEAGUE_ROSTER = "official PL API roster"
    EXTERNAL_APPEARANCE = "Transfermarkt/Wikidata with PL appearance evidence"
    EXTERNAL_ID_NAME = "Wikidata Transfermarkt ID without appearance"
    REVIEWED_JSON = "reviewed JSON fallback"


class BirthDateProposal(NamedTuple):
    player_id: int
    name: str
    date_of_birth: str
    category: BirthDateProposalCategory


_PROPOSAL_CATEGORY_ORDER = (
    BirthDateProposalCategory.FPL,
    BirthDateProposalCategory.PREMIER_LEAGUE_OPTA,
    BirthDateProposalCategory.PREMIER_LEAGUE_ROSTER,
    BirthDateProposalCategory.EXTERNAL_APPEARANCE,
    BirthDateProposalCategory.EXTERNAL_ID_NAME,
    BirthDateProposalCategory.REVIEWED_JSON,
)


@dataclass(frozen=True)
class BirthDateSummary:
    proposed: list[BirthDateProposal]
    direct_fpl: int
    scoped_opta: int
    external_pair: int
    corroborated_controls: int
    conflicts: list[tuple[int, str, str | None, tuple[str, ...]]]
    id_name_only: int = 0
    pl_roster: int = 0
    reviewed_json: int = 0


def _name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))


def _date(value: str | None) -> str | None:
    if not value or value in ("None", "null", "nan"):
        return None
    if value.endswith(" 00:00:00") and len(value) == 19:
        value = value[:10]  # Published Transfermarkt CSV encodes dates as midnight datetimes.
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError(value)
    except ValueError as error:
        raise BirthDateEvidenceError(f"Invalid source date {value!r}") from error
    return value


def _json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise BirthDateEvidenceError(f"Duplicate JSON key {key!r} in reviewed DOB evidence")
        result[key] = value
    return result


def _public_source_url(value: object) -> bool:
    if (not isinstance(value, str) or not value
            or any(char.isspace() or ord(char) < 0x20 or ord(char) == 0x7F for char in value)):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme not in ("http", "https") or not host
                or parsed.username is not None or parsed.password is not None):
            return False
        if parsed.port is not None:
            if not 1 <= parsed.port <= 65535:
                return False
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            try:
                ascii_host = host.rstrip(".").encode("idna").decode("ascii").lower()
            except UnicodeError:
                return False
            labels = ascii_host.split(".")
            label_pattern = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
            if (len(ascii_host) > 253 or len(labels) < 2
                    or any(not label_pattern.fullmatch(label) for label in labels)
                    or not re.fullmatch(r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", labels[-1])):
                return False
    except ValueError:
        return False
    return True


def _reviewed_birth_dates(
    path: Path,
    people: dict[int, tuple[str, str | None]],
    mapping_rows: list[tuple[str, str, int]],
) -> dict[int, str]:
    """Validate every manually reviewed DOB before it can join automatic evidence."""
    try:
        entries = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_json_object)
    except json.JSONDecodeError as error:
        raise BirthDateEvidenceError(f"Invalid reviewed DOB JSON in {path}") from error
    if not isinstance(entries, list):
        raise BirthDateEvidenceError("Reviewed DOB JSON must be a list")

    expected_fields = {
        "player_id", "display_name", "fpl_season", "fpl_code", "date_of_birth", "source_urls", "review_note",
    }
    accepted: dict[int, str] = {}
    seen_player_ids: set[int] = set()
    seen_fpl_mappings: set[tuple[str, str]] = set()
    for index, entry in enumerate(entries):
        label = f"Reviewed DOB entry {index}"
        if not isinstance(entry, dict) or set(entry) != expected_fields:
            raise BirthDateEvidenceError(f"{label} must contain exactly {sorted(expected_fields)}")

        player_id = entry["player_id"]
        if type(player_id) is not int or player_id not in people:
            raise BirthDateEvidenceError(f"{label} has no valid canonical player_id")
        if player_id in seen_player_ids:
            raise BirthDateEvidenceError(f"Duplicate reviewed DOB player_id {player_id}")
        seen_player_ids.add(player_id)

        display_name = entry["display_name"]
        if not isinstance(display_name, str) or display_name != people[player_id][0]:
            raise BirthDateEvidenceError(f"{label} display_name does not exactly match player {player_id}")

        season = entry["fpl_season"]
        season_match = re.fullmatch(r"([0-9]{4})-([0-9]{2})", season) if isinstance(season, str) else None
        if (season_match is None or not 1 <= int(season_match[1]) <= 9998
                or int(season_match[2]) != (int(season_match[1]) + 1) % 100):
            raise BirthDateEvidenceError(f"{label} has an invalid FPL season")
        code = entry["fpl_code"]
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]+", code):
            raise BirthDateEvidenceError(f"{label} has an invalid FPL code")
        scope = f"premier-league:{season}"
        mapping_key = (scope, code)
        if mapping_key in seen_fpl_mappings:
            raise BirthDateEvidenceError(f"Duplicate reviewed FPL mapping {scope} code {code}")
        seen_fpl_mappings.add(mapping_key)
        matching_players = [
            mapped_player for mapped_scope, mapped_code, mapped_player in mapping_rows
            if (mapped_scope, mapped_code) == mapping_key
        ]
        if matching_players != [player_id]:
            raise BirthDateEvidenceError(f"{label} FPL mapping does not match player {player_id}")

        raw_dob = entry["date_of_birth"]
        if not isinstance(raw_dob, str):
            raise BirthDateEvidenceError(f"{label} must have an exact ISO date")
        dob = _date(raw_dob)
        if dob is None:
            raise BirthDateEvidenceError(f"{label} must have an exact ISO date")
        current_dob = people[player_id][1]
        if current_dob is not None and current_dob != dob:
            raise BirthDateEvidenceError(f"{label} disagrees with existing DOB for player {player_id}")

        urls = entry["source_urls"]
        if (not isinstance(urls, list) or not urls
                or any(not _public_source_url(url) for url in urls)
                or len(set(urls)) != len(urls)):
            raise BirthDateEvidenceError(f"{label} must cite unique public HTTP(S) source URLs")
        note = entry["review_note"]
        if not isinstance(note, str) or not note.strip():
            raise BirthDateEvidenceError(f"{label} must have a non-empty review_note")

        accepted[player_id] = dob
    return accepted


def _csv(path: Path, fields: set[str], *, compressed: bool = False):
    opener = gzip.open if compressed else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not fields <= set(reader.fieldnames):
            raise BirthDateEvidenceError(f"Missing fields in {path}")
        yield from reader


def _fpl(raw_root: Path, mappings: dict[tuple[str, str], int]):
    direct: dict[int, set[str]] = defaultdict(set)
    opta: dict[int, set[tuple[str, str]]] = defaultdict(set)
    for year in (2024, 2025, 2026):
        season = f"{year}-{(year + 1) % 100:02d}"
        scope = f"premier-league:{season}"
        path = raw_root / "fpl_archive_vaastav" / season / "players_raw.csv"
        for row in _csv(path, {"code", "birth_date", "opta_code"}):
            pid = mappings.get((scope, row["code"]))
            if pid is None:
                continue  # Excludes assistant managers and unimported observations.
            dob = _date(row["birth_date"])
            if dob:
                direct[pid].add(dob)
            if row["opta_code"].startswith("p"):
                opta[pid].add((season, row["opta_code"]))
    bootstrap = json.loads((raw_root / "official_fpl_api" / "bootstrap-static.json").read_text(encoding="utf-8"))
    for element in bootstrap["elements"]:
        pid = mappings.get(("premier-league:2026-27", str(element["code"])))
        if pid is None:
            continue
        dob = _date(element.get("birth_date"))
        if dob:
            direct[pid].add(dob)
        if isinstance(element.get("opta_code"), str) and element["opta_code"].startswith("p"):
            opta[pid].add(("2026-27", element["opta_code"]))
    return direct, opta


def _premier_league(raw_root: Path):
    dates: dict[tuple[str, str], set[str]] = defaultdict(set)
    folder = raw_root / "premier_league_api" / "stats"
    paths = list(folder.glob("*/players/*/page-*.json"))
    if not paths:
        raise BirthDateEvidenceError("No saved Premier League player-stat pages")
    for path in paths:
        season = "2026-27" if path.parts[-4].startswith("English-Premier-League-") else path.parts[-4]
        payload = json.loads(path.read_text(encoding="utf-8"))
        for entry in payload["stats"]["content"]:
            owner = entry["owner"]
            opta = owner.get("altIds", {}).get("opta")
            birth = owner.get("birth", {}).get("date", {})
            if not opta or birth.get("millis") is None:
                continue
            dob = datetime.fromtimestamp(birth["millis"] / 1000, UTC).date().isoformat()
            if datetime.strptime(birth["label"], "%d %B %Y").date().isoformat() != dob:
                raise BirthDateEvidenceError(f"Premier League date/label disagree for {opta}")
            dates[(season, opta)].add(dob)
    return dates


def _linked_dates(raw_root: Path, source: str, ids: list[str]):
    folder = raw_root / source
    if not folder.exists():
        return None
    batches = list(range(0, len(ids), BATCH_SIZE))
    expected = {f"batch-{index:03d}.json" for index in range(len(batches))}
    actual = {path.name for path in folder.glob("batch-*.json")}
    if not batches or actual != expected:
        label = ("Wikidata Transfermarkt" if source == "wikidata_transfermarkt"
                 else "Wikidata FPL Transfermarkt")
        raise BirthDateEvidenceError(f"Incomplete {label} birth-date batches")
    linked: dict[str, dict[str, set[str | None]]] = defaultdict(lambda: defaultdict(set))
    for index, start in enumerate(batches):
        payload = json.loads((folder / f"batch-{index:03d}.json").read_text(encoding="utf-8"))
        bindings = payload.get("results", {}).get("bindings")
        if not isinstance(bindings, list):
            raise BirthDateEvidenceError(f"Invalid {source} birth-date batch")
        batch_ids = set(ids[start : start + BATCH_SIZE])
        for binding in bindings:
            tm_id = binding["tmId"]["value"]
            if tm_id not in batch_ids:
                raise BirthDateEvidenceError(f"Unexpected Transfermarkt ID in {source} batch")
            qid = binding["player"]["value"]
            precision = binding["precision"]["value"]
            dob = _date(binding["dob"]["value"][:10]) if precision == "11" else None
            linked[tm_id][qid].add(dob)
    return linked


def _external(raw_root: Path):
    transfermarkt: dict[str, dict[str, str | None]] = defaultdict(dict)
    for row in _csv(raw_root / "transfermarkt_datasets" / "players.csv.gz",
                    {"player_id", "name", "date_of_birth"}, compressed=True):
        transfermarkt[_name(row["name"])][row["player_id"]] = _date(row["date_of_birth"])
    wikidata: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    payload = json.loads((raw_root / "wikidata_players" / "premier_league_club_players_dob.json").read_text(encoding="utf-8"))
    for binding in payload["results"]["bindings"]:
        name = _name(binding["name"]["value"])
        qid = binding["player"]["value"]
        if binding["precision"]["value"] == "11":
            dob = _date(binding["dob"]["value"][:10])
            if dob:
                wikidata[name][qid].add(dob)
        else:
            wikidata[name][qid]  # Keep coarse-precision homonyms ambiguous.
    paired: dict[str, tuple[str, str]] = {}
    for name, players in transfermarkt.items():
        wiki = wikidata.get(name, {})
        if len(players) != 1 or len(wiki) != 1:
            continue
        tm_id, tm_date = next(iter(players.items()))
        wiki_dates = next(iter(wiki.values()))
        if tm_date and wiki_dates == {tm_date}:
            paired[name] = (tm_id, tm_date)

    # Merge the two ID-linked captures; contradictory QIDs or dates disqualify
    # this player even if one capture or a same-name Wikidata row looks correct.
    linked = (_linked_dates(raw_root, "wikidata_transfermarkt", _tm_ids(raw_root))
              if (raw_root / "wikidata_transfermarkt").exists() else None)
    named_linked = (_linked_dates(raw_root, "wikidata_transfermarkt_fpl", fpl_tm_ids(raw_root))
                    if (raw_root / "wikidata_transfermarkt_fpl").exists() else None)
    combined: dict[str, dict[str, set[str | None]]] = defaultdict(lambda: defaultdict(set))
    for captured in (linked, named_linked):
        if captured is None:
            continue
        for tm_id, people in captured.items():
            for qid, dates in people.items():
                combined[tm_id][qid].update(dates)
    id_name_only: dict[str, tuple[str, str]] = {}
    for name, players in transfermarkt.items():
        if len(players) != 1:
            continue
        tm_id, tm_date = next(iter(players.items()))
        people = combined.get(tm_id, {})
        if not people:
            continue
        if tm_date and len(people) == 1 and next(iter(people.values())) == {tm_date}:
            if named_linked is not None and tm_id in named_linked:
                id_name_only[name] = (tm_id, tm_date)
            paired[name] = (tm_id, tm_date)
        else:
            paired.pop(name, None)
    return paired, id_name_only


def _appearance_matches(connection: sqlite3.Connection, raw_root: Path,
                        candidates: dict[int, tuple[str, str]]) -> set[int]:
    """Require same-season, same-reviewed-club *positive-minute* PL evidence."""
    if not candidates:
        return set()
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    listed = defaultdict(set)
    for pid, season, club in connection.execute(
        "SELECT DISTINCT p.player_id, s.label, t.team_key FROM player_gameweek_teams p "
        "JOIN gameweeks g ON g.gameweek_id = p.gameweek_id "
        "JOIN seasons s ON s.season_id = g.season_id "
        "JOIN teams t ON t.team_id = p.team_id WHERE p.fixtures_with_minutes > 0"
    ):
        if pid in candidates:
            listed[pid].add((season, club))
    games = {}
    for row in _csv(raw_root / "transfermarkt_datasets" / "games.csv.gz",
                    {"game_id", "competition_id", "season", "home_club_id", "away_club_id",
                     "home_club_name", "away_club_name"}, compressed=True):
        if row["competition_id"] != "GB1":
            continue
        year = int(row["season"])
        season = f"{year}-{(year + 1) % 100:02d}"
        clubs = {
            row[f"{side}_club_id"]: aliases.get(club_name(row[f"{side}_club_name"]))
            for side in ("home", "away")
        }
        games[row["game_id"]] = season, clubs
    by_tm = {tm_id: (pid, dob) for pid, (tm_id, dob) in candidates.items()}
    matched = set()
    for row in _csv(raw_root / "transfermarkt_datasets" / "appearances.csv.gz",
                    {"player_id", "game_id", "player_club_id", "minutes_played"}, compressed=True):
        candidate = by_tm.get(row["player_id"])
        game = games.get(row["game_id"])
        if candidate and game and row["minutes_played"] and int(row["minutes_played"]) > 0:
            pid, _ = candidate
            season, clubs = game
            if (season, clubs.get(row["player_club_id"])) in listed[pid]:
                matched.add(pid)
    return matched


def backfill_player_birth_dates(raw_root: Path, database_path: Path = DATABASE_PATH,
                                *, dry_run: bool = False) -> BirthDateSummary:
    """Fill only NULLs from source evidence, then the validated reviewed JSON fallback."""
    if dry_run:
        connection = sqlite3.connect(f"{Path(database_path).resolve().as_uri()}?mode=ro", uri=True)
        connection.execute("PRAGMA query_only = ON")
    else:
        connection = connect_database(database_path)
    try:
        if not dry_run:
            connection.execute("BEGIN IMMEDIATE")
        people = {
            pid: (name, dob) for pid, name, dob in connection.execute("SELECT player_id, display_name, date_of_birth FROM players")
        }
        mapping_rows = connection.execute(
            "SELECT source_scope, source_id, player_id FROM player_source_ids "
            "WHERE source_namespace = 'fpl.element.code'"
        ).fetchall()
        mappings = {(scope, code): pid for scope, code, pid in mapping_rows}
        reviewed = _reviewed_birth_dates(REVIEWED_PLAYER_BIRTH_DATES_PATH, people, mapping_rows)
        names: dict[str, set[int]] = defaultdict(set)
        for pid, (name, _) in people.items():
            names[_name(name)].add(pid)
        direct, opta = _fpl(raw_root, mappings)
        pl_dates = _premier_league(raw_root)
        roster = roster_birth_dates(raw_root, people, mappings, _name)
        paired, id_name_only = _external(raw_root)
        potential = {
            pid: paired[_name(name)] for pid, (name, _) in people.items()
            if len(names[_name(name)]) == 1 and _name(name) in paired
        }
        named_potential = {
            pid: id_name_only[_name(name)] for pid, (name, _) in people.items()
            if len(names[_name(name)]) == 1 and _name(name) in id_name_only
        }
        witnessed = _appearance_matches(connection, raw_root, potential)
        proposed: list[BirthDateProposal] = []
        conflicts = []
        controls = 0
        direct_count = opta_count = external_count = name_only_count = roster_count = reviewed_count = 0
        for pid, (name, current) in people.items():
            dates = set(direct.get(pid, ()))
            pl = set().union(*(pl_dates.get(pair, set()) for pair in opta.get(pid, ())))
            external = {potential[pid][1]} if pid in witnessed else set()
            if pid in named_potential:
                external.add(named_potential[pid][1])
            manual = {reviewed[pid]} if pid in reviewed else set()
            evidence = dates | pl | external | ({roster[pid]} if pid in roster else set()) | manual
            if current is not None:
                if external:
                    controls += 1
                if evidence and evidence != {current}:
                    conflicts.append((pid, name, current, tuple(sorted(evidence))))
                continue
            if len(evidence) > 1:
                conflicts.append((pid, name, None, tuple(sorted(evidence))))
            elif evidence:
                available_categories = {
                    BirthDateProposalCategory.FPL: bool(dates),
                    BirthDateProposalCategory.PREMIER_LEAGUE_OPTA: bool(pl),
                    BirthDateProposalCategory.PREMIER_LEAGUE_ROSTER: pid in roster,
                    BirthDateProposalCategory.EXTERNAL_APPEARANCE: pid in witnessed,
                    BirthDateProposalCategory.EXTERNAL_ID_NAME: pid in named_potential,
                    BirthDateProposalCategory.REVIEWED_JSON: pid in reviewed,
                }
                category = next(
                    category for category in _PROPOSAL_CATEGORY_ORDER if available_categories[category]
                )
                proposed.append(BirthDateProposal(pid, name, next(iter(evidence)), category))
                if category is BirthDateProposalCategory.FPL:
                    direct_count += 1
                elif category is BirthDateProposalCategory.PREMIER_LEAGUE_OPTA:
                    opta_count += 1
                elif category is BirthDateProposalCategory.PREMIER_LEAGUE_ROSTER:
                    roster_count += 1
                elif category is BirthDateProposalCategory.EXTERNAL_APPEARANCE:
                    external_count += 1
                elif category is BirthDateProposalCategory.EXTERNAL_ID_NAME:
                    name_only_count += 1
                else:
                    reviewed_count += 1
        if not dry_run:
            for proposal in proposed:
                result = connection.execute(
                    "UPDATE players SET date_of_birth = ? WHERE player_id = ? AND date_of_birth IS NULL",
                    (proposal.date_of_birth, proposal.player_id),
                )
                if result.rowcount != 1:
                    raise BirthDateEvidenceError(f"Player {proposal.player_id} changed during DOB review")
            connection.commit()
        return BirthDateSummary(
            proposed, direct_count, opta_count, external_count, controls, conflicts,
            name_only_count, roster_count, reviewed_count,
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
