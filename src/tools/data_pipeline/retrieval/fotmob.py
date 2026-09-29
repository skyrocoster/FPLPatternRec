"""FotMob league-season, statistics, and match retrieval."""

from __future__ import annotations

from urllib.parse import urlencode

from .common import (
    RawCollector,
    current_season_start,
    season_label,
    season_start,
    slug,
)
from .provider_config import (
    FOTMOB_API,
    FOTMOB_HISTORICAL_PLAYER_STATS,
    FOTMOB_HISTORICAL_TEAM_STATS,
)


def _fotmob_url(route: str, params: dict[str, object]) -> str:
    return f"{FOTMOB_API}/{route}?{urlencode(params)}"


def _fotmob_season_payload(
    collector: RawCollector, season: str
) -> dict[str, object] | list[object] | None:
    season_slug = slug(season.replace("/", "-"))
    return collector.get_json(
        "fotmob",
        f"seasons/{season_slug}.json",
        _fotmob_url("leagues", {"id": 47, "ccode3": "USA", "season": season}),
        {"Referer": "https://www.fotmob.com/"},
    )


def _fotmob_stat(
    collector: RawCollector,
    season_name: str,
    season_id: int,
    category: str,
    stat: str,
) -> None:
    collector.get(
        "fotmob",
        f"statistics/{season_name}/{slug(category)}/{slug(stat)}.json",
        _fotmob_url(
            "leagueseasondeepstats",
            {"id": 47, "ccode3": "USA", "season": season_id, "stat": stat, "type": category},
        ),
        {"Referer": "https://www.fotmob.com/"},
    )


def collect_fotmob(collector: RawCollector, include_match_details: bool = True) -> None:
    source = "fotmob"
    print("Collecting FotMob league seasons and match data", flush=True)
    collector.get(
        source,
        "all_leagues.json",
        f"{FOTMOB_API}/allLeagues",
        {"Referer": "https://www.fotmob.com/"},
    )
    current_start = current_season_start()
    current_label = season_label(current_start)
    current_slug = slug(current_label.replace("/", "-"))
    current_data = _fotmob_season_payload(collector, current_label)
    if not isinstance(current_data, dict):
        return

    season_names = current_data.get("allAvailableSeasons", [])
    seasons = (
        [str(value) for value in season_names if isinstance(value, str)]
        if isinstance(season_names, list)
        else []
    )
    if current_label not in seasons:
        seasons.append(current_label)
    season_data: dict[str, dict[str, object]] = {current_label: current_data}
    for season in seasons:
        if season == current_label:
            continue
        payload = _fotmob_season_payload(collector, season)
        if isinstance(payload, dict):
            season_data[season] = payload

    catalogue_url = _fotmob_url(
        "leagueseasondeepstats",
        {"id": 47, "ccode3": "USA", "season": current_label, "stat": "goals", "type": "players"},
    )
    player_catalogue = collector.get_json(
        source,
        "statistics/catalogue_players.json",
        catalogue_url,
        {"Referer": "https://www.fotmob.com/"},
    )
    if not isinstance(player_catalogue, dict):
        return
    season_records = player_catalogue.get("seasons", [])
    season_ids = {
        str(item.get("name")): int(item["id"])
        for item in season_records
        if isinstance(item, dict) and item.get("name") and item.get("id") is not None
    } if isinstance(season_records, list) else {}
    current_id_value = player_catalogue.get("currentSeasonId")
    try:
        current_id = int(current_id_value)
    except (TypeError, ValueError):
        current_id = int(season_ids.get(current_label, 0))
    player_stats = player_catalogue.get("statsList", [])
    if current_id:
        current_player_catalogue = collector.get_json(
            source,
            "statistics/catalogue_players_current.json",
            _fotmob_url(
                "leagueseasondeepstats",
                {
                    "id": 47,
                    "ccode3": "USA",
                    "season": current_id,
                    "stat": "goals",
                    "type": "players",
                },
            ),
            {"Referer": "https://www.fotmob.com/"},
        )
        if isinstance(current_player_catalogue, dict):
            player_stats = current_player_catalogue.get("statsList", player_stats)

    team_catalogue = collector.get_json(
        source,
        "statistics/catalogue_teams.json",
        _fotmob_url(
            "leagueseasondeepstats",
            {
                "id": 47,
                "ccode3": "USA",
                "season": current_id,
                "stat": "goals_team_match",
                "type": "teams",
            },
        ),
        {"Referer": "https://www.fotmob.com/"},
    )
    team_stats = team_catalogue.get("statsList", []) if isinstance(team_catalogue, dict) else []

    if current_id:
        for category, items in (("players", player_stats), ("teams", team_stats)):
            if not isinstance(items, list):
                continue
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    _fotmob_stat(collector, current_slug, current_id, category, item["name"])

    historic_names = [name for name in season_ids if 2016 <= season_start(name) < current_start]
    player_available = {
        item.get("name")
        for item in player_stats
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    } if isinstance(player_stats, list) else set()
    team_available = {
        item.get("name")
        for item in team_stats
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    } if isinstance(team_stats, list) else set()
    for season in historic_names:
        season_id = season_ids[season]
        season_slug = slug(season.replace("/", "-"))
        for stat in FOTMOB_HISTORICAL_PLAYER_STATS:
            if stat in player_available:
                _fotmob_stat(collector, season_slug, season_id, "players", stat)
        for stat in FOTMOB_HISTORICAL_TEAM_STATS:
            if stat in team_available:
                _fotmob_stat(collector, season_slug, season_id, "teams", stat)

    if not include_match_details:
        return
    detail_seasons = {current_label, season_label(current_start - 1)}
    match_ids: dict[str, set[int]] = {season: set() for season in detail_seasons}
    for season in detail_seasons:
        payload = season_data.get(season)
        fixtures = payload.get("fixtures") if isinstance(payload, dict) else None
        matches = fixtures.get("allMatches") if isinstance(fixtures, dict) else None
        if not isinstance(matches, list):
            continue
        for match in matches:
            if not isinstance(match, dict):
                continue
            status = match.get("status")
            is_finished = isinstance(status, dict) and (
                status.get("finished") is True
                or (
                    isinstance(status.get("reason"), dict)
                    and status["reason"].get("shortKey") == "finished"
                )
            )
            match_id = match.get("id")
            if is_finished and match_id is not None:
                match_ids[season].add(int(match_id))
    for season, ids in match_ids.items():
        season_slug = slug(season.replace("/", "-"))
        for index, match_id in enumerate(sorted(ids), start=1):
            collector.get(
                source,
                f"matches/{season_slug}/match_{match_id}.json",
                _fotmob_url("matchDetails", {"matchId": match_id}),
                {"Referer": "https://www.fotmob.com/"},
            )
            if index % 100 == 0:
                print(f"  FotMob {season}: {index}/{len(ids)} match details", flush=True)
