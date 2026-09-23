"""Fantasy Premier League API and open historical archive collectors."""

from __future__ import annotations

import re

from .common import FPL_API, GITHUB_API, RawCollector, season_start


def _fpl_headers() -> dict[str, str]:
    return {"Referer": "https://fantasy.premierleague.com/"}


def collect_fpl(collector: RawCollector, include_player_summaries: bool) -> None:
    source = "official_fpl_api"
    print("Collecting the public Fantasy Premier League API", flush=True)
    bootstrap = collector.get_json(
        source,
        "bootstrap-static.json",
        f"{FPL_API}/bootstrap-static/",
        _fpl_headers(),
    )
    collector.get(source, "fixtures.json", f"{FPL_API}/fixtures/", _fpl_headers())
    if not isinstance(bootstrap, dict):
        return

    events = bootstrap.get("events", [])
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict) or not (
                event.get("is_previous") or event.get("is_current")
            ):
                continue
            event_id = event.get("id")
            if event_id is not None:
                collector.get(
                    source,
                    f"live_gameweeks/gw_{int(event_id):02d}.json",
                    f"{FPL_API}/event/{int(event_id)}/live/",
                    _fpl_headers(),
                )

    players = bootstrap.get("elements", [])
    if include_player_summaries and isinstance(players, list):
        for index, player in enumerate(players, start=1):
            if not isinstance(player, dict) or player.get("id") is None:
                continue
            player_id = int(player["id"])
            collector.get(
                source,
                f"element_summaries/element_{player_id:04d}.json",
                f"{FPL_API}/element-summary/{player_id}/",
                _fpl_headers(),
            )
            if index % 100 == 0:
                print(f"  player summaries: {index}/{len(players)}", flush=True)


def collect_fpl_archive(collector: RawCollector) -> None:
    source = "fpl_archive_vaastav"
    print("Collecting historical FPL gameweek archives", flush=True)
    api_headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    listing = collector.get_json(source, "catalogues/data.json", f"{GITHUB_API}/data", api_headers)
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
            f"{GITHUB_API}/data/{season}",
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
            f"{GITHUB_API}/data/{season}/gws",
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
