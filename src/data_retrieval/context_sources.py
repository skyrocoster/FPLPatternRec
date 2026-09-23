"""Historical/context source collectors that have no supported structured API."""

from __future__ import annotations

from datetime import UTC, datetime

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


def collect_football_data(collector: RawCollector) -> None:
    print("Collecting Football-Data.co.uk Premier League CSV seasons", flush=True)
    for year in range(1993, current_season_start() + 1):
        season_code = f"{year % 100:02d}{(year + 1) % 100:02d}"
        collector.get(
            "football_data",
            f"E0_{season_code}.csv",
            f"https://www.football-data.co.uk/mmz4281/{season_code}/E0.csv",
        )


def collect_clubelo(collector: RawCollector) -> None:
    print("Trying the ClubElo public CSV API", flush=True)
    date = datetime.now(UTC).date().isoformat()
    collector.get("clubelo", f"daily/{date}.csv", f"https://api.clubelo.com/{date}")


def collect_sofascore(collector: RawCollector) -> None:
    print("Trying the Sofascore public competition API", flush=True)
    collector.get_json(
        "sofascore",
        "premier_league_seasons.json",
        "https://www.sofascore.com/api/v1/unique-tournament/17/seasons",
        {"Referer": "https://www.sofascore.com/", "Accept": "application/json"},
    )
