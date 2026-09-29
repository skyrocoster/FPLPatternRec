"""Official Premier League fixtures and statistics API retrieval."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .common import (
    RawCollector,
    current_season_start,
    season_start,
    slug,
)
from .provider_config import PL_PLAYER_STATS, PL_TEAM_STATS, PULSELIVE_API


def _pl_headers() -> dict[str, str]:
    return {
        "Origin": "https://www.premierleague.com",
        "Referer": "https://www.premierleague.com/",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Accept": "application/json",
    }


def _pl_request_url(path: str, params: dict[str, object]) -> str:
    return f"{PULSELIVE_API}/{path}?{urlencode(params)}"


def _collect_pl_pages(
    collector: RawCollector,
    source: str,
    relative_base: str,
    url_base: str,
    payload: dict[str, object] | list[object] | None,
) -> None:
    if not isinstance(payload, dict):
        return
    stats = payload.get("stats")
    page_info = stats.get("pageInfo") if isinstance(stats, dict) else payload.get("pageInfo")
    if not isinstance(page_info, dict):
        return
    try:
        page_count = int(page_info.get("numPages", 1))
    except (TypeError, ValueError):
        page_count = 1
    for page in range(1, page_count):
        parts = urlsplit(url_base)
        params = dict(parse_qsl(parts.query))
        params["page"] = str(page)
        page_url = urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment)
        )
        collector.get(source, relative_base.format(page=page), page_url, _pl_headers())


def collect_premier_league_api(collector: RawCollector) -> None:
    source = "premier_league_api"
    print("Collecting official Premier League fixtures and stats", flush=True)
    seasons_url = _pl_request_url("competitions/1/compseasons", {"page": 0, "pageSize": 100})
    season_payload = collector.get_json(
        source, "competition_seasons.json", seasons_url, _pl_headers()
    )
    if not isinstance(season_payload, dict) or not isinstance(season_payload.get("content"), list):
        return
    seasons = [item for item in season_payload["content"] if isinstance(item, dict)]
    current_start = current_season_start()
    current = max(seasons, key=lambda item: season_start(str(item.get("label", ""))), default=None)
    if current is None:
        return
    current_season_id = int(current["id"])

    for season in seasons:
        season_id = int(season["id"])
        label = str(season.get("label", season_id))
        start_year = season_start(label)
        season_slug = slug(label)
        base_params: dict[str, object] = {
            "comp": 1,
            "compSeasons": season_id,
            "altIds": "true",
            "page": 0,
            "pageSize": 100,
        }
        url = _pl_request_url("fixtures", base_params)
        first = collector.get_json(
            source, f"fixtures/{season_slug}/page-000.json", url, _pl_headers()
        )
        _collect_pl_pages(
            collector,
            source,
            f"fixtures/{season_slug}/page-{{page:03d}}.json",
            url,
            first,
        )
        if start_year and start_year % 5 == 0:
            print(f"  fixture seasons through {label}", flush=True)

    valid_stats: dict[str, list[str]] = {"players": [], "teams": []}
    candidates = {"players": PL_PLAYER_STATS, "teams": PL_TEAM_STATS}
    current_slug = slug(str(current.get("label", current_season_id)))
    for entity, stats in candidates.items():
        for stat in stats:
            params: dict[str, object] = {
                "comp": 1,
                "compSeasons": current_season_id,
                "altIds": "true",
                "page": 0,
                "pageSize": 1000,
            }
            url = _pl_request_url(f"stats/ranked/{entity}/{stat}", params)
            path = f"stats/{current_slug}/{entity}/{stat}/page-000.json"
            payload = collector.get_json(source, path, url, _pl_headers())
            if isinstance(payload, dict) and isinstance(payload.get("stats"), dict):
                valid_stats[entity].append(stat)
                _collect_pl_pages(
                    collector,
                    source,
                    f"stats/{current_slug}/{entity}/{stat}/page-{{page:03d}}.json",
                    url,
                    payload,
                )

    historic_seasons = [
        item
        for item in seasons
        if 2016 <= season_start(str(item.get("label", ""))) < current_start
    ]
    for season in historic_seasons:
        season_id = int(season["id"])
        season_slug = slug(str(season.get("label", season_id)))
        for entity, stats in valid_stats.items():
            for stat in stats:
                params = {
                    "comp": 1,
                    "compSeasons": season_id,
                    "altIds": "true",
                    "page": 0,
                    "pageSize": 1000,
                }
                url = _pl_request_url(f"stats/ranked/{entity}/{stat}", params)
                path = f"stats/{season_slug}/{entity}/{stat}/page-000.json"
                payload = collector.get_json(source, path, url, _pl_headers())
                _collect_pl_pages(
                    collector,
                    source,
                    f"stats/{season_slug}/{entity}/{stat}/page-{{page:03d}}.json",
                    url,
                    payload,
                )
