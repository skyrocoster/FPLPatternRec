"""Retrieval adapters for non-Premier-League competitions."""

from .fotmob import collect_fotmob_competitions
from .openfootball import collect_openfootball
from .transfermarkt import collect_transfermarkt_injuries
from .wikipedia import collect_wikipedia_competitions

__all__ = [
    "collect_fotmob_competitions",
    "collect_openfootball",
    "collect_transfermarkt_injuries",
    "collect_wikipedia_competitions",
]
