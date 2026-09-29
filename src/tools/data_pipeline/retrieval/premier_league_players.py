"""Saved official Premier League season roster retrieval."""

from __future__ import annotations

import json
from pathlib import Path

from .common import RawCollector, season_start
from .premier_league import _pl_headers, _pl_request_url

_SOURCE = "premier_league_api"
_PAGE_SIZE = 100
_FIRST_SEASON = 2016


def _read_seasons(raw_root: Path) -> list[tuple[int, int, str]]:
    path = raw_root / _SOURCE / "competition_seasons.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read saved Premier League seasons: {path}") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("content"), list):
        raise RuntimeError("Saved Premier League seasons do not contain a valid content list")

    seasons_by_start: dict[int, tuple[int, int, str]] = {}
    for item in payload["content"]:
        if not isinstance(item, dict) or not isinstance(item.get("label"), str):
            continue
        label = item["label"]
        start_year = season_start(label)
        if start_year < _FIRST_SEASON:
            continue

        season_id = _season_id(item.get("id"), label)
        season_slug = f"{start_year}-{(start_year + 1) % 100:02d}"
        previous = seasons_by_start.get(start_year)
        if previous is not None and previous[1] != season_id:
            raise RuntimeError(f"Saved Premier League seasons duplicate {label}")
        seasons_by_start[start_year] = (start_year, season_id, season_slug)

    if not seasons_by_start:
        raise RuntimeError("Saved Premier League seasons contain no seasons from 2016/17 onward")
    return [seasons_by_start[year] for year in sorted(seasons_by_start)]


def _season_id(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"Saved Premier League season {label} has an invalid ID")
    if isinstance(value, int):
        season_id = value
    elif isinstance(value, float) and value.is_integer():
        season_id = int(value)
    elif isinstance(value, str) and value.strip().isdecimal():
        season_id = int(value.strip())
    else:
        raise RuntimeError(f"Saved Premier League season {label} has an invalid ID")
    if season_id <= 0:
        raise RuntimeError(f"Saved Premier League season {label} has an invalid ID")
    return season_id


def _page_info(
    payload: object,
    expected_page: int,
    expected_metadata: tuple[int, int, int] | None,
) -> tuple[list[object], tuple[int, int, int]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Premier League players response is not a JSON object")
    content = payload.get("content")
    page_info = payload.get("pageInfo")
    if not isinstance(content, list) or not isinstance(page_info, dict):
        raise RuntimeError("Premier League players response has invalid pageInfo or content")

    page = _page_info_integer(page_info, "page")
    num_pages = _page_info_integer(page_info, "numPages")
    page_size = _page_info_integer(page_info, "pageSize")
    num_entries = _page_info_integer(page_info, "numEntries")
    if page != expected_page:
        raise RuntimeError(
            f"Premier League players page index mismatch: expected {expected_page}, received {page}"
        )
    if num_pages < 1 or page_size != _PAGE_SIZE or num_entries < 0:
        raise RuntimeError("Premier League players response has invalid pagination values")

    metadata = (num_pages, page_size, num_entries)
    if expected_metadata is not None and metadata != expected_metadata:
        raise RuntimeError("Premier League players pageInfo changed between pages")
    expected_pages = max(1, (num_entries + page_size - 1) // page_size)
    if num_pages != expected_pages:
        raise RuntimeError("Premier League players pageInfo has inconsistent numPages")

    # The live API sometimes overstates numEntries (2016/17 reports 966 but
    # returns 835, ending with a short page followed by an empty final page).
    # Do not infer missing identities from the advertised total.
    if len(content) > page_size:
        raise RuntimeError("Premier League players page exceeds its pageSize")
    return content, metadata


def _page_info_integer(page_info: dict[str, object], key: str) -> int:
    value = page_info.get(key)
    if isinstance(value, bool):
        raise RuntimeError(f"Premier League players pageInfo has an invalid {key}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise RuntimeError(f"Premier League players pageInfo has an invalid {key}")


def collect_premier_league_players(collector: RawCollector) -> None:
    """Save every page of the saved Premier League seasons' player rosters."""
    seasons = _read_seasons(Path(collector.raw_root))
    print(f"Collecting official Premier League player rosters for {len(seasons)} saved seasons", flush=True)
    for _, season_id, season_slug in seasons:
        params: dict[str, object] = {
            "comp": 1,
            "compSeasons": season_id,
            "altIds": "true",
            "page": 0,
            "pageSize": _PAGE_SIZE,
        }
        url = _pl_request_url("players", params)
        relative_path = f"players/{season_slug}/page-000.json"
        payload = collector.get_json(_SOURCE, relative_path, url, _pl_headers())
        if payload is None:
            raise RuntimeError(f"Premier League players page {relative_path} is unavailable")

        first, metadata = _page_info(payload, 0, None)
        returned = len(first)
        short_page = len(first) < _PAGE_SIZE
        for next_page in range(1, metadata[0]):
            next_params = dict(params)
            next_params["page"] = next_page
            next_url = _pl_request_url("players", next_params)
            next_path = f"players/{season_slug}/page-{next_page:03d}.json"
            next_payload = collector.get_json(_SOURCE, next_path, next_url, _pl_headers())
            if next_payload is None:
                raise RuntimeError(f"Premier League players page {next_path} is unavailable")
            content, _ = _page_info(next_payload, next_page, metadata)
            if short_page and content:
                raise RuntimeError(f"Premier League players returned data after a short page in {season_slug}")
            returned += len(content)
            short_page = short_page or len(content) < _PAGE_SIZE
        print(
            f"  saved {season_slug}: {returned} returned of {metadata[2]} advertised "
            f"in {metadata[0]} pages",
            flush=True,
        )
