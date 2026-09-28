"""ClubElo public CSV retrieval."""

from __future__ import annotations

from datetime import UTC, datetime

from .common import RawCollector


def collect_clubelo(collector: RawCollector) -> None:
    print("Trying the ClubElo public CSV API", flush=True)
    date = datetime.now(UTC).date().isoformat()
    collector.get("clubelo", f"daily/{date}.csv", f"https://api.clubelo.com/{date}")
