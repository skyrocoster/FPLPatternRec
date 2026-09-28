"""Transfermarkt Premier League current-injury-page retrieval."""

from __future__ import annotations

from datetime import UTC, datetime

from ..common import RawCollector


def collect_transfermarkt_injuries(collector: RawCollector) -> None:
    """Scrape a dated snapshot of Transfermarkt's current Premier League injury list."""
    print("Scraping Transfermarkt's current Premier League injury page", flush=True)
    date = datetime.now(UTC).date().isoformat()
    collector.get(
        "transfermarkt_injuries",
        f"snapshots/premier_league_injuries_{date}.html",
        "https://www.transfermarkt.com/premier-league/verletztespieler/wettbewerb/GB1",
        {
            "Accept": "text/html",
            "Referer": "https://www.transfermarkt.com/",
        },
    )
