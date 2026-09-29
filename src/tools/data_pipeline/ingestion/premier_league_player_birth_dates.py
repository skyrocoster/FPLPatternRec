"""Read conservative player birth-date candidates from saved PL season rosters."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import UTC, date, datetime
import gzip
import json
from pathlib import Path
from typing import Callable

from ..retrieval.premier_league_players import _page_info, _read_seasons

_SOURCE = "premier_league_api"
_PAGE_SIZE = 100
_TRANSFERMARKT_PATH = Path("transfermarkt_datasets") / "players.csv.gz"
_FPL_ARCHIVE_ROOT = Path("fpl_archive_vaastav")
_FPL_ARCHIVE_SEASONS = tuple(f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027))
_FPL_ARCHIVE_FIELDS = {"code", "first_name", "second_name", "web_name", "element_type"}


class PremierLeagueBirthDatesError(ValueError):
    """Saved Premier League, FPL archive, or Transfermarkt evidence is incomplete or malformed."""


def roster_birth_dates(
    raw_root: Path,
    people: dict[int, tuple[str, str | None]],
    mappings: dict[tuple[str, str], int],
    normalize: Callable[[str], str],
) -> dict[int, str]:
    """Return safe DOB candidates for uniquely named canonical players without a DOB.

    A candidate requires a uniquely named FPL mapping in at least one saved
    season, a stable Premier League player ID and DOB across every matching
    canonical or confirmed alternate label, and no single contradictory
    Transfermarkt DOB for a matched label.
    """
    roster_root = Path(raw_root) / _SOURCE / "players"
    if not roster_root.exists():
        return {}
    if not roster_root.is_dir():
        raise PremierLeagueBirthDatesError(f"Premier League roster path is not a directory: {roster_root}")

    try:
        seasons = _read_seasons(Path(raw_root))
    except RuntimeError as error:
        raise PremierLeagueBirthDatesError(str(error)) from error

    rosters = _read_rosters(roster_root, seasons, normalize)
    transfermarkt = _transfermarkt_birth_dates(Path(raw_root), normalize)

    normalized_people: dict[int, str] = {}
    people_by_name: dict[str, set[int]] = defaultdict(set)
    for player_id, (name, _) in people.items():
        if not isinstance(name, str) or not name.strip():
            normalized_people[player_id] = ""
            continue
        normalized = _normalize_name(name, normalize)
        normalized_people[player_id] = normalized
        if normalized:
            people_by_name[normalized].add(player_id)

    season_by_scope = {f"premier-league:{season}": season for _, _, season in seasons}
    mapped_seasons: dict[int, set[str]] = defaultdict(set)
    codes_by_season: dict[str, dict[str, int]] = defaultdict(dict)
    for (scope, code), player_id in mappings.items():
        season = season_by_scope.get(scope)
        if season is not None and isinstance(code, str) and code.strip() and player_id in people:
            mapped_seasons[player_id].add(season)
            codes_by_season[season][code] = player_id

    aliases = _read_fpl_aliases(Path(raw_root), codes_by_season, normalized_people, normalize)
    labels_by_player_season: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    players_by_season_label: dict[str, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    for player_id, player_seasons in mapped_seasons.items():
        for season in player_seasons:
            labels = labels_by_player_season[player_id][season]
            if normalized_people[player_id]:
                labels.add(normalized_people[player_id])
            labels.update(aliases.get(season, {}).get(player_id, ()))
            for label in labels:
                players_by_season_label[season][label].add(player_id)

    candidates: dict[int, str] = {}
    for player_id, (name, current_dob) in people.items():
        normalized = normalized_people[player_id]
        if (
            current_dob is not None
            or not normalized
            or len(people_by_name[normalized]) != 1
        ):
            continue

        observations: list[tuple[int, str, str]] = []
        matched_labels: set[str] = set()
        ambiguous = False
        for season in mapped_seasons.get(player_id, ()):
            labels = labels_by_player_season[player_id].get(season, set())
            if any(len(players_by_season_label[season][label]) != 1 for label in labels):
                ambiguous = True
                break
            for label in labels:
                named_players = rosters[season].get(label, {})
                if not named_players:
                    continue
                if len(named_players) != 1:
                    ambiguous = True
                    break
                pl_id, dates = next(iter(named_players.items()))
                if len(dates) != 1:
                    ambiguous = True
                    break
                observations.append((pl_id, next(iter(dates)), label))
                matched_labels.add(label)
            if ambiguous:
                break

        if ambiguous or not observations:
            continue
        if len({pl_id for pl_id, _, _ in observations}) != 1:
            continue
        dates = {dob for _, dob, _ in observations}
        if len(dates) != 1:
            continue

        dob = next(iter(dates))
        if any(
            len(rows := transfermarkt.get(label, ())) == 1
            and rows[0] is not None
            and rows[0] != dob
            for label in matched_labels
        ):
            continue
        candidates[player_id] = dob

    return candidates


def _read_fpl_aliases(
    raw_root: Path,
    codes_by_season: dict[str, dict[str, int]],
    normalized_people: dict[int, str],
    normalize: Callable[[str], str],
) -> dict[str, dict[int, set[str]]]:
    aliases: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    for season in _FPL_ARCHIVE_SEASONS:
        path = raw_root / _FPL_ARCHIVE_ROOT / season / "players_raw.csv"
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if (
                    not reader.fieldnames
                    or not _FPL_ARCHIVE_FIELDS <= set(reader.fieldnames)
                    or len(reader.fieldnames) != len(set(reader.fieldnames))
                ):
                    raise PremierLeagueBirthDatesError(f"Missing or duplicate fields in saved FPL archive {path}")
                seen_codes: set[str] = set()
                for index, row in enumerate(reader, start=2):
                    if None in row or any(row.get(field) is None for field in _FPL_ARCHIVE_FIELDS):
                        raise PremierLeagueBirthDatesError(f"Malformed row {index} in saved FPL archive {path}")
                    code = row["code"].strip()
                    if not code or code in seen_codes:
                        raise PremierLeagueBirthDatesError(f"Invalid or duplicate player code in saved FPL archive {path}")
                    seen_codes.add(code)
                    first_name = row["first_name"].strip()
                    second_name = row["second_name"].strip()
                    web_name = row["web_name"].strip()
                    player_id = codes_by_season.get(season, {}).get(code)
                    if (
                        player_id is None
                        or not first_name
                        or not second_name
                        or not web_name
                        or _normalize_name(f"{first_name} {second_name}", normalize)
                        != normalized_people.get(player_id)
                    ):
                        continue
                    alias = _normalize_name(f"{first_name} {web_name}", normalize)
                    if alias:
                        aliases[season][player_id].add(alias)
        except PremierLeagueBirthDatesError:
            raise
        except (OSError, UnicodeDecodeError, csv.Error) as error:
            raise PremierLeagueBirthDatesError(f"Cannot read saved FPL archive: {path}") from error
    return {season: dict(players) for season, players in aliases.items()}


def _read_rosters(
    roster_root: Path,
    seasons: list[tuple[int, int, str]],
    normalize: Callable[[str], str],
) -> dict[str, dict[str, dict[int, set[str]]]]:
    expected_seasons = {season for _, _, season in seasons}
    season_paths = list(roster_root.iterdir())
    actual_seasons = {path.name for path in season_paths}
    if actual_seasons != expected_seasons or any(not path.is_dir() for path in season_paths):
        raise PremierLeagueBirthDatesError(
            "Saved Premier League roster seasons do not match competition_seasons.json"
        )

    rosters: dict[str, dict[str, dict[int, set[str]]]] = {}
    for season in sorted(expected_seasons):
        season_root = roster_root / season
        first_path = season_root / "page-000.json"
        first_page = _read_page(first_path)
        try:
            first_content, metadata = _page_info(first_page, 0, None)
        except RuntimeError as error:
            raise PremierLeagueBirthDatesError(f"Invalid Premier League roster page {first_path}: {error}") from error

        expected_pages = {f"page-{page:03d}.json" for page in range(metadata[0])}
        page_paths = list(season_root.iterdir())
        actual_pages = {path.name for path in page_paths}
        if actual_pages != expected_pages or any(not path.is_file() for path in page_paths):
            raise PremierLeagueBirthDatesError(
                f"Saved Premier League roster pages do not match pageInfo for {season}"
            )

        entries: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
        short_page = len(first_content) < _PAGE_SIZE
        _add_players(entries, first_content, first_path, normalize)
        for page_number in range(1, metadata[0]):
            page_path = season_root / f"page-{page_number:03d}.json"
            payload = _read_page(page_path)
            try:
                content, _ = _page_info(payload, page_number, metadata)
            except RuntimeError as error:
                raise PremierLeagueBirthDatesError(
                    f"Invalid Premier League roster page {page_path}: {error}"
                ) from error
            if short_page and content:
                raise PremierLeagueBirthDatesError(
                    f"Premier League roster returned data after a short page in {season}"
                )
            _add_players(entries, content, page_path, normalize)
            short_page = short_page or len(content) < _PAGE_SIZE
        rosters[season] = dict(entries)

    return rosters


def _read_page(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PremierLeagueBirthDatesError(f"Cannot read saved Premier League roster page: {path}") from error


def _add_players(
    entries: dict[str, dict[int, set[str]]],
    content: list[object],
    path: Path,
    normalize: Callable[[str], str],
) -> None:
    for index, value in enumerate(content):
        if not isinstance(value, dict):
            raise PremierLeagueBirthDatesError(f"Malformed player entry {index} in {path}")
        pl_id = _positive_id(value.get("id"), path, index)
        name_payload = value.get("name")
        display_name = name_payload.get("display") if isinstance(name_payload, dict) else None
        if not isinstance(display_name, str) or not display_name.strip():
            raise PremierLeagueBirthDatesError(f"Missing Premier League player name in {path} entry {index}")
        birth = value.get("birth")
        date_payload = birth.get("date") if isinstance(birth, dict) else None
        if date_payload is None:
            continue  # Some roster entries have no DOB; they cannot be candidates.
        normalized = _normalize_name(display_name, normalize)
        dob = _birth_date(birth, path, index)
        entries[normalized][pl_id].add(dob)


def _positive_id(value: object, path: Path, index: int) -> int:
    if isinstance(value, bool):
        player_id = 0
    elif isinstance(value, int):
        player_id = value
    elif isinstance(value, float) and value.is_integer():
        player_id = int(value)
    elif isinstance(value, str) and value.strip().isdecimal():
        player_id = int(value.strip())
    else:
        player_id = 0
    if player_id <= 0:
        raise PremierLeagueBirthDatesError(f"Invalid Premier League player ID in {path} entry {index}")
    return player_id


def _birth_date(value: object, path: Path, index: int) -> str:
    date_payload = value.get("date") if isinstance(value, dict) else None
    millis = date_payload.get("millis") if isinstance(date_payload, dict) else None
    label = date_payload.get("label") if isinstance(date_payload, dict) else None
    if isinstance(millis, bool):
        raise PremierLeagueBirthDatesError(f"Invalid Premier League birth date in {path} entry {index}")
    if isinstance(millis, int):
        timestamp = millis
    elif isinstance(millis, float) and millis.is_integer():
        timestamp = int(millis)
    else:
        raise PremierLeagueBirthDatesError(f"Invalid Premier League birth date in {path} entry {index}")
    if not isinstance(label, str):
        raise PremierLeagueBirthDatesError(f"Invalid Premier League birth-date label in {path} entry {index}")
    try:
        label_date = datetime.strptime(label, "%d %B %Y").date()
        utc_date = datetime.fromtimestamp(timestamp / 1000, UTC).date()
    except (OverflowError, OSError, ValueError) as error:
        raise PremierLeagueBirthDatesError(
            f"Invalid Premier League birth date or label in {path} entry {index}"
        ) from error
    if label_date != utc_date:
        raise PremierLeagueBirthDatesError(
            f"Premier League birth-date millis and label disagree in {path} entry {index}"
        )
    return utc_date.isoformat()


def _transfermarkt_birth_dates(
    raw_root: Path,
    normalize: Callable[[str], str],
) -> dict[str, list[str | None]]:
    path = raw_root / _TRANSFERMARKT_PATH
    if not path.exists():
        return {}

    by_name: dict[str, list[str | None]] = defaultdict(list)
    try:
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {"player_id", "name", "date_of_birth"}
            if not reader.fieldnames or not required <= set(reader.fieldnames):
                raise PremierLeagueBirthDatesError(f"Missing fields in saved Transfermarkt dataset {path}")
            for row in reader:
                if None in row or any(row.get(field) is None for field in required):
                    raise PremierLeagueBirthDatesError(f"Malformed row in saved Transfermarkt dataset {path}")
                name = row["name"].strip()
                if not row["player_id"].strip() or not name:
                    raise PremierLeagueBirthDatesError(f"Incomplete row in saved Transfermarkt dataset {path}")
                by_name[_normalize_name(name, normalize)].append(_transfermarkt_date(row["date_of_birth"], path))
    except PremierLeagueBirthDatesError:
        raise
    except (OSError, EOFError, UnicodeDecodeError, csv.Error) as error:
        raise PremierLeagueBirthDatesError(f"Cannot read saved Transfermarkt dataset {path}") from error
    return dict(by_name)


def _transfermarkt_date(value: str, path: Path) -> str | None:
    value = value.strip()
    if not value or value.casefold() in {"none", "null", "nan"}:
        return None
    if value.endswith(" 00:00:00") and len(value) == 19:
        value = value[:10]
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise PremierLeagueBirthDatesError(
            f"Invalid Transfermarkt birth date {value!r} in {path}"
        ) from error
    if parsed.isoformat() != value:
        raise PremierLeagueBirthDatesError(f"Invalid Transfermarkt birth date {value!r} in {path}")
    return parsed.isoformat()


def _normalize_name(value: str, normalize: Callable[[str], str]) -> str:
    normalized = normalize(value)
    if not isinstance(normalized, str):
        raise PremierLeagueBirthDatesError("Name normalizer did not return a string")
    return normalized
