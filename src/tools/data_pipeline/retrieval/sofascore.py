"""Sofascore public competition API retrieval."""

from __future__ import annotations

from .common import RawCollector


def collect_sofascore(collector: RawCollector) -> None:
    print("Trying the Sofascore public competition API", flush=True)
    collector.get_json(
        "sofascore",
        "premier_league_seasons.json",
        "https://www.sofascore.com/api/v1/unique-tournament/17/seasons",
        {"Referer": "https://www.sofascore.com/", "Accept": "application/json"},
    )
