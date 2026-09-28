"""FotMob alternative competition seasons and leaderboard retrieval."""

from __future__ import annotations

from urllib.parse import urlencode, urlparse

from ..common import RawCollector, current_season_start, slug
from .common import (
    FOTMOB_API,
    FOTMOB_COMPETITIONS,
    FOTMOB_HEADERS,
    PLAYER_LEADERBOARDS,
    TEAM_LEADERBOARDS,
    season_start_year,
)


def _fotmob_url(route: str, params: dict[str, object]) -> str:
    return f"{FOTMOB_API}/{route}?{urlencode(params)}"


def _season_slug(label: str) -> str:
    return slug(label.replace("/", "-")) or "unknown-season"


def _collect_fotmob_leaderboards(
    collector: RawCollector,
    competition_slug: str,
    season_slug: str,
    payload: dict[str, object],
) -> None:
    stats = payload.get("stats")
    if not isinstance(stats, dict):
        return

    for entity, selected_stats in (
        ("players", PLAYER_LEADERBOARDS),
        ("teams", TEAM_LEADERBOARDS),
    ):
        records = stats.get(entity)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, dict):
                continue
            url = record.get("fetchAllUrl")
            if not isinstance(url, str):
                continue
            parsed = urlparse(url)
            stat_name = parsed.path.rsplit("/", 1)[-1].removesuffix(".json")
            if parsed.scheme != "https" or parsed.netloc != "data.fotmob.com":
                continue
            if stat_name not in selected_stats:
                continue
            collector.get(
                "fotmob_competitions",
                f"seasons/{competition_slug}/{season_slug}/stats/{entity}_{stat_name}.json",
                url,
                FOTMOB_HEADERS,
            )


def collect_fotmob_competitions(collector: RawCollector) -> None:
    """Save available FotMob season payloads and selected full-season leaderboards."""
    print("Collecting FotMob alternative competition seasons and stats", flush=True)
    for competition_id, name in FOTMOB_COMPETITIONS:
        competition_slug = slug(name)
        catalogue_url = _fotmob_url("leagues", {"id": competition_id, "ccode3": "USA"})
        catalogue = collector.get_json(
            "fotmob_competitions",
            f"seasons/{competition_slug}/latest.json",
            catalogue_url,
            FOTMOB_HEADERS,
        )
        if not isinstance(catalogue, dict):
            continue
        available = catalogue.get("allAvailableSeasons", [])
        labels = [
            value
            for value in available
            if isinstance(value, str) and season_start_year(value) >= 1992
        ] if isinstance(available, list) else []
        if not labels:
            continue

        latest_label = labels[0]
        for label in labels:
            season_slug = _season_slug(label)
            if label == latest_label:
                payload = catalogue
            else:
                season_url = _fotmob_url(
                    "leagues",
                    {"id": competition_id, "ccode3": "USA", "season": label},
                )
                result = collector.get_json(
                    "fotmob_competitions",
                    f"seasons/{competition_slug}/{season_slug}.json",
                    season_url,
                    FOTMOB_HEADERS,
                )
                payload = result if isinstance(result, dict) else None
            if payload is not None:
                _collect_fotmob_leaderboards(collector, competition_slug, season_slug, payload)
        print(f"  FotMob {name}: {len(labels)} season payloads", flush=True)
