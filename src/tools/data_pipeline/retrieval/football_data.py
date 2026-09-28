"""Football-Data.co.uk Premier League CSV retrieval."""

from __future__ import annotations

from .common import RawCollector, current_season_start


def collect_football_data(collector: RawCollector) -> None:
    print("Collecting Football-Data.co.uk Premier League CSV seasons", flush=True)
    for year in range(1993, current_season_start() + 1):
        season_code = f"{year % 100:02d}{(year + 1) % 100:02d}"
        collector.get(
            "football_data",
            f"E0_{season_code}.csv",
            f"https://www.football-data.co.uk/mmz4281/{season_code}/E0.csv",
        )
