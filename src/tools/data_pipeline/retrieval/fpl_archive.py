"""Historical FPL archive retrieval."""

from __future__ import annotations

import re

from .common import RawCollector, season_start
from .provider_config import FPL_ARCHIVE_CONTENTS_API


def collect_fpl_archive(collector: RawCollector) -> None:
    source = "fpl_archive_vaastav"
    print("Collecting historical FPL gameweek archives", flush=True)
    api_headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    listing = collector.get_json(
        source, "catalogues/data.json", f"{FPL_ARCHIVE_CONTENTS_API}/data", api_headers
    )
    if not isinstance(listing, list):
        return
    seasons = sorted(
        (
            item.get("name", "")
            for item in listing
            if isinstance(item, dict) and re.fullmatch(r"20\d{2}-\d{2}", str(item.get("name", "")))
        ),
        key=season_start,
    )
    for season in seasons:
        root = collector.get_json(
            source,
            f"catalogues/{season}.json",
            f"{FPL_ARCHIVE_CONTENTS_API}/data/{season}",
            api_headers,
        )
        if not isinstance(root, list):
            continue
        wanted = {"fixtures.csv", "players_raw.csv", "teams.csv", "events.csv", "player_idlist.csv"}
        for item in root:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            name = str(item.get("name", ""))
            url = item.get("download_url")
            if name in wanted and isinstance(url, str):
                collector.get(source, f"{season}/{name}", url)
        gameweeks = collector.get_json(
            source,
            f"catalogues/{season}_gws.json",
            f"{FPL_ARCHIVE_CONTENTS_API}/data/{season}/gws",
            api_headers,
        )
        if isinstance(gameweeks, list):
            merged = next(
                (
                    item
                    for item in gameweeks
                    if isinstance(item, dict) and item.get("name") == "merged_gw.csv"
                ),
                None,
            )
            if isinstance(merged, dict) and isinstance(merged.get("download_url"), str):
                collector.get(source, f"{season}/gws/merged_gw.csv", str(merged["download_url"]))
