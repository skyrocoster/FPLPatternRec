"""Command-line entry point for the raw public-data collectors."""

from __future__ import annotations

import argparse
from pathlib import Path

from .common import RawCollector
from .context_sources import (
    collect_clubelo,
    collect_football_data,
    collect_sofascore,
    collect_understat,
)
from .fpl_sources import collect_fpl, collect_fpl_archive
from .league_sources import collect_fotmob, collect_premier_league_api


def main() -> int:
    collectors = {
        "fpl": lambda collector, args: collect_fpl(collector, not args.no_fpl_player_summaries),
        "fpl_archive": lambda collector, args: collect_fpl_archive(collector),
        "premier_league": lambda collector, args: collect_premier_league_api(collector),
        "fotmob": lambda collector, args: collect_fotmob(
            collector, not args.no_fotmob_match_details
        ),
        "understat": lambda collector, args: collect_understat(collector),
        "football_data": lambda collector, args: collect_football_data(collector),
        "clubelo": lambda collector, args: collect_clubelo(collector),
        "sofascore": lambda collector, args: collect_sofascore(collector),
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=",".join(collectors),
        help=f"Comma-separated sources (default: {','.join(collectors)}).",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "data" / "raw",
        help="Raw archive root (default: repository data/raw).",
    )
    parser.add_argument(
        "--no-fpl-player-summaries",
        action="store_true",
        help="Skip one request per FPL player.",
    )
    parser.add_argument(
        "--no-fotmob-match-details",
        action="store_true",
        help="Skip completed match details.",
    )
    args = parser.parse_args()

    selected = [name.strip() for name in args.sources.split(",") if name.strip()]
    unknown = sorted(set(selected) - set(collectors))
    if unknown:
        parser.error(f"unknown source(s): {', '.join(unknown)}")
    collector = RawCollector(args.raw_root)
    source_folders = {
        "fpl": "official_fpl_api",
        "fpl_archive": "fpl_archive_vaastav",
        "premier_league": "premier_league_api",
    }
    collection_failed = False
    for name in selected:
        try:
            collectors[name](collector, args)
        except Exception as error:
            collection_failed = True
            source = source_folders.get(name, name)
            print(f"  collector failed for {source}: {type(error).__name__}: {error}", flush=True)
            collector.record_issue(source, error)
    collector.finish()
    return int(collection_failed)


if __name__ == "__main__":
    raise SystemExit(main())
