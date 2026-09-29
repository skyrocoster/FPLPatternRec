"""Official Fantasy Premier League API retrieval."""

from __future__ import annotations

from .common import RawCollector
from .provider_config import FPL_API


def _fpl_headers() -> dict[str, str]:
    return {"Referer": "https://fantasy.premierleague.com/"}


def collect_fpl(collector: RawCollector, include_player_summaries: bool = True) -> None:
    source = "official_fpl_api"
    print("Collecting the public Fantasy Premier League API", flush=True)
    bootstrap = collector.get_json(
        source,
        "bootstrap-static.json",
        f"{FPL_API}/bootstrap-static/",
        _fpl_headers(),
    )
    collector.get(source, "fixtures.json", f"{FPL_API}/fixtures/", _fpl_headers())
    if not isinstance(bootstrap, dict):
        return

    events = bootstrap.get("events", [])
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict) or not (
                event.get("is_previous") or event.get("is_current")
            ):
                continue
            event_id = event.get("id")
            if event_id is not None:
                collector.get(
                    source,
                    f"live_gameweeks/gw_{int(event_id):02d}.json",
                    f"{FPL_API}/event/{int(event_id)}/live/",
                    _fpl_headers(),
                )

    players = bootstrap.get("elements", [])
    if include_player_summaries and isinstance(players, list):
        for index, player in enumerate(players, start=1):
            if not isinstance(player, dict) or player.get("id") is None:
                continue
            player_id = int(player["id"])
            collector.get(
                source,
                f"element_summaries/element_{player_id:04d}.json",
                f"{FPL_API}/element-summary/{player_id}/",
                _fpl_headers(),
            )
            if index % 100 == 0:
                print(f"  player summaries: {index}/{len(players)}", flush=True)
