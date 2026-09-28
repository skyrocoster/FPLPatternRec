"""Understat league and match-payload retrieval."""

from __future__ import annotations

from .common import RawCollector, current_season_start


def collect_understat(collector: RawCollector) -> None:
    print("Collecting Understat league data and recent shot-level match payloads", flush=True)
    current_year = current_season_start()
    league_headers = {
        "Referer": f"https://understat.com/league/EPL/{current_year}",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }
    league_data: dict[int, dict[str, object]] = {}
    for year in range(2014, current_year + 1):
        payload = collector.get_json(
            "understat",
            f"league_data/EPL_{year}.json.gz",
            f"https://understat.com/getLeagueData/EPL/{year}",
            league_headers,
        )
        if isinstance(payload, dict):
            league_data[year] = payload

    match_headers = {
        "Referer": "https://understat.com/",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
    }
    for year in (current_year - 1, current_year):
        payload = league_data.get(year)
        dates = payload.get("dates", []) if payload else []
        if not isinstance(dates, list):
            continue
        match_ids = sorted(
            {
                int(match["id"])
                for match in dates
                if isinstance(match, dict) and match.get("isResult") and match.get("id") is not None
            }
        )
        for index, match_id in enumerate(match_ids, start=1):
            collector.get(
                "understat",
                f"match_data/{year}/{match_id}.json.gz",
                f"https://understat.com/getMatchData/{match_id}",
                match_headers,
            )
            if index % 100 == 0:
                print(f"  Understat {year}: {index}/{len(match_ids)} match payloads", flush=True)
