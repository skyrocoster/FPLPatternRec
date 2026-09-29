"""Retrieve Wikidata birth-date statements for saved Transfermarkt player IDs."""

from __future__ import annotations

import csv
import gzip
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

from .common import RawCollector

BATCH_SIZE = 75
ENDPOINTS = (
    "https://qlever.cs.uni-freiburg.de/api/wikidata",
    "https://query.wikidata.org/sparql",
)
REQUIRED_GAME_FIELDS = {"game_id", "competition_id"}
REQUIRED_APPEARANCE_FIELDS = {"player_id", "game_id", "minutes_played"}
REQUIRED_PLAYER_FIELDS = {"player_id", "name"}
FPL_ARCHIVE_SEASONS = tuple(
    f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027)
)
REQUIRED_FPL_ARCHIVE_FIELDS = {"id", "element_type", "first_name", "second_name"}

WIKIDATA_QUERY = """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX p: <http://www.wikidata.org/prop/>
PREFIX psv: <http://www.wikidata.org/prop/statement/value/>
PREFIX wikibase: <http://wikiba.se/ontology#>
SELECT DISTINCT ?player ?tmId ?dob ?precision WHERE {
  VALUES ?tmId { {tm_ids} }
  ?player wdt:P2446 ?tmId;
          p:P569/psv:P569 ?birthDate.
  ?birthDate wikibase:timeValue ?dob;
             wikibase:timePrecision ?precision.
}"""


def _read_rows(path: Path, required_fields: set[str]):
    try:
        stream = gzip.open(path, "rt", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise ValueError(f"Cannot read saved Transfermarkt dataset {path}: {error}") from error
    try:
        with stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or not required_fields <= set(reader.fieldnames):
                raise ValueError(f"Missing required fields in saved Transfermarkt dataset {path}")
            for row in reader:
                if None in row:
                    raise ValueError(f"Malformed row in saved Transfermarkt dataset {path}")
                if any(not row[field] for field in required_fields):
                    raise ValueError(f"Incomplete row in saved Transfermarkt dataset {path}")
                yield row
    except (OSError, EOFError, UnicodeError, csv.Error) as error:
        raise ValueError(f"Cannot parse saved Transfermarkt dataset {path}: {error}") from error


def _tm_ids(raw_root: Path) -> list[str]:
    dataset_root = raw_root / "transfermarkt_datasets"
    games_path = dataset_root / "games.csv.gz"
    appearances_path = dataset_root / "appearances.csv.gz"

    gb1_games = {
        row["game_id"]
        for row in _read_rows(games_path, REQUIRED_GAME_FIELDS)
        if row["competition_id"] == "GB1" and row["game_id"]
    }
    player_ids: set[str] = set()
    for row in _read_rows(appearances_path, REQUIRED_APPEARANCE_FIELDS):
        if row["game_id"] not in gb1_games:
            continue
        player_id = row["player_id"].strip()
        try:
            minutes = int(row["minutes_played"])
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid minutes_played in saved Transfermarkt appearances") from error
        if minutes <= 0:
            continue
        if not player_id.isdigit() or int(player_id) <= 0:
            raise ValueError("Invalid player_id in saved Transfermarkt appearances")
        player_ids.add(str(int(player_id)))
    return sorted(player_ids, key=int)


def _normalized_name(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name.casefold())
    normalized = "".join(character for character in decomposed if not unicodedata.combining(character))
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _fpl_name(first_name: object, second_name: object, source: str) -> str:
    if not isinstance(first_name, str) or not isinstance(second_name, str):
        raise ValueError(f"Incomplete full name in saved FPL source {source}")
    first, second = first_name.strip(), second_name.strip()
    if not first or not second or first == "None" or second == "None":
        raise ValueError(f"Incomplete full name in saved FPL source {source}")
    return f"{first} {second}"


def _fpl_player_names(raw_root: Path) -> set[str]:
    names: set[str] = set()
    archive_root = raw_root / "fpl_archive_vaastav"
    for season in FPL_ARCHIVE_SEASONS:
        path = archive_root / season / "players_raw.csv"
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if (
                    not reader.fieldnames
                    or len(reader.fieldnames) != len(set(reader.fieldnames))
                    or not REQUIRED_FPL_ARCHIVE_FIELDS <= set(reader.fieldnames)
                ):
                    raise ValueError(f"Missing required fields in saved FPL source {path}")
                for row in reader:
                    if None in row or any(not row.get(field) for field in REQUIRED_FPL_ARCHIVE_FIELDS):
                        raise ValueError(f"Malformed row in saved FPL source {path}")
                    player_id = row["id"].strip()
                    if not player_id.isdigit() or int(player_id) <= 0:
                        raise ValueError(f"Invalid player id in saved FPL source {path}")
                    element_type = row["element_type"].strip()
                    if element_type not in {"1", "2", "3", "4", "5"}:
                        raise ValueError(f"Invalid element_type in saved FPL source {path}")
                    full_name = _fpl_name(row["first_name"], row["second_name"], str(path))
                    if element_type != "5":
                        names.add(_normalized_name(full_name))
        except ValueError:
            raise
        except (OSError, UnicodeError, csv.Error) as error:
            raise ValueError(f"Cannot read saved FPL source {path}: {error}") from error

    bootstrap_path = raw_root / "official_fpl_api" / "bootstrap-static.json"
    try:
        payload = json.loads(bootstrap_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read saved FPL source {bootstrap_path}: {error}") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list) or not payload["elements"]:
        raise ValueError(f"Missing required elements in saved FPL source {bootstrap_path}")
    for player in payload["elements"]:
        if not isinstance(player, dict):
            raise ValueError(f"Malformed player in saved FPL source {bootstrap_path}")
        player_id = player.get("id")
        if isinstance(player_id, bool) or not isinstance(player_id, int) or player_id <= 0:
            raise ValueError(f"Invalid player id in saved FPL source {bootstrap_path}")
        element_type = player.get("element_type")
        if isinstance(element_type, bool) or not isinstance(element_type, int) or element_type not in {1, 2, 3, 4, 5}:
            raise ValueError(f"Invalid element_type in saved FPL source {bootstrap_path}")
        full_name = _fpl_name(
            player.get("first_name"), player.get("second_name"), str(bootstrap_path)
        )
        if element_type != 5:
            names.add(_normalized_name(full_name))
    return names


def fpl_tm_ids(raw_root: Path) -> list[str]:
    """Return saved Transfermarkt IDs whose names match saved FPL players."""
    fpl_names = _fpl_player_names(Path(raw_root))
    players_path = Path(raw_root) / "transfermarkt_datasets" / "players.csv.gz"
    player_ids: set[str] = set()
    for row in _read_rows(players_path, REQUIRED_PLAYER_FIELDS):
        player_id = row["player_id"].strip()
        if not player_id.isdigit() or int(player_id) <= 0:
            raise ValueError("Invalid player_id in saved Transfermarkt players")
        if _normalized_name(row["name"]) in fpl_names:
            player_ids.add(str(int(player_id)))
    return sorted(player_ids, key=int)


def _bindings(response: object) -> list[object] | None:
    if not isinstance(response, dict):
        return None
    results = response.get("results")
    if not isinstance(results, dict):
        return None
    bindings = results.get("bindings")
    return bindings if isinstance(bindings, list) else None


def _query(tm_ids: list[str]) -> str:
    values = " ".join(f'"{tm_id}"' for tm_id in tm_ids)
    return WIKIDATA_QUERY.replace("{tm_ids}", values)


def collect_wikidata_transfermarkt(collector: RawCollector) -> None:
    """Save batched Wikidata birth-date results for positive-minute GB1 players."""
    print("Collecting Wikidata birth dates for saved Transfermarkt Premier League players", flush=True)
    tm_ids = _tm_ids(Path(collector.raw_root))
    for batch_index, start in enumerate(range(0, len(tm_ids), BATCH_SIZE)):
        batch = tm_ids[start : start + BATCH_SIZE]
        relative_path = f"batch-{batch_index:03d}.json"
        query = _query(batch)
        succeeded = False
        last_error: Exception | None = None
        for endpoint in ENDPOINTS:
            url = endpoint + "?" + urlencode({"query": query, "format": "json"})
            try:
                response = collector.get_json(
                    "wikidata_transfermarkt",
                    relative_path,
                    url,
                    {"Accept": "application/sparql-results+json"},
                )
            except Exception as error:
                last_error = error
                print(f"  Wikidata query failed at {endpoint}; trying next endpoint", flush=True)
                continue
            if _bindings(response) is not None:
                succeeded = True
                break
            print(f"  Wikidata query unavailable at {endpoint}; trying next endpoint", flush=True)
        if not succeeded:
            message = f"Wikidata Transfermarkt batch {batch_index:03d} did not return valid bindings"
            if last_error is not None:
                raise RuntimeError(message) from last_error
            raise RuntimeError(message)


def collect_wikidata_transfermarkt_fpl(collector: RawCollector) -> None:
    """Save birth-date results for Transfermarkt players matching saved FPL names."""
    print("Collecting Wikidata birth dates for name-matched saved FPL players", flush=True)
    tm_ids = fpl_tm_ids(Path(collector.raw_root))
    for batch_index, start in enumerate(range(0, len(tm_ids), BATCH_SIZE)):
        batch = tm_ids[start : start + BATCH_SIZE]
        relative_path = f"batch-{batch_index:03d}.json"
        query = _query(batch)
        succeeded = False
        last_error: Exception | None = None
        for endpoint in ENDPOINTS:
            url = endpoint + "?" + urlencode({"query": query, "format": "json"})
            try:
                response = collector.get_json(
                    "wikidata_transfermarkt_fpl",
                    relative_path,
                    url,
                    {"Accept": "application/sparql-results+json"},
                )
            except Exception as error:
                last_error = error
                print(f"  Wikidata query failed at {endpoint}; trying next endpoint", flush=True)
                continue
            if _bindings(response) is not None:
                succeeded = True
                break
            print(f"  Wikidata query unavailable at {endpoint}; trying next endpoint", flush=True)
        if not succeeded:
            message = f"Wikidata FPL Transfermarkt batch {batch_index:03d} did not return valid bindings"
            if last_error is not None:
                raise RuntimeError(message) from last_error
            raise RuntimeError(message)
