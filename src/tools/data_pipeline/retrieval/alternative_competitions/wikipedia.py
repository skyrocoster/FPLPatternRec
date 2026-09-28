"""Wikipedia competition article revision retrieval."""

from __future__ import annotations

from urllib.parse import urlencode

from ..common import RawCollector, current_season_start
from .common import WIKIPEDIA_API, WIKIPEDIA_HEADERS


def _wikipedia_titles() -> list[tuple[int, str]]:
    titles: list[tuple[int, str]] = []
    for year in range(1992, current_season_start() + 1):
        season = f"{year}–{(year + 1) % 100:02d}"
        titles.extend(
            (
                (year, f"{season} FA Cup"),
                (
                    year,
                    f"{season} {'Football League Cup' if year < 2016 else 'EFL Cup'}",
                ),
                (year, f"{season} UEFA Champions League"),
                (
                    year,
                    f"{season} {'UEFA Cup' if year < 2009 else 'UEFA Europa League'}",
                ),
                (
                    year,
                    f"{year} {'FA Charity Shield' if year < 2002 else 'FA Community Shield'}",
                ),
                (
                    year,
                    f"{year} {'European Super Cup' if year < 1995 else 'UEFA Super Cup'}",
                ),
            )
        )
        if year >= 2021:
            titles.append(
                (
                    year,
                    f"{season} {'UEFA Europa Conference League' if year < 2024 else 'UEFA Conference League'}",
                )
            )
    return titles


def collect_wikipedia_competitions(collector: RawCollector) -> None:
    """Retrieve MediaWiki source for historical cup and European competition pages."""
    print("Collecting Wikipedia competition article revisions", flush=True)
    titles = _wikipedia_titles()
    batch_size = 20
    for batch_index, start in enumerate(range(0, len(titles), batch_size), start=1):
        batch = titles[start : start + batch_size]
        years = [year for year, _ in batch]
        params = {
            "action": "query",
            "prop": "revisions",
            "titles": "|".join(title for _, title in batch),
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "format": "json",
            "formatversion": "2",
        }
        url = f"{WIKIPEDIA_API}?{urlencode(params)}"
        collector.get(
            "wikipedia_competitions",
            (
                f"mediawiki_api/verified_competition_articles/{min(years)}-"
                f"{max(years)}_batch-{batch_index:02d}.json"
            ),
            url,
            WIKIPEDIA_HEADERS,
        )
    print(f"  Wikipedia: {len(titles)} article titles queried", flush=True)
