from __future__ import annotations

from tools.data_pipeline.retrieval.alternative_competitions.common import season_start_year
from tools.data_pipeline.retrieval.alternative_competitions.openfootball import (
    _openfootball_path_is_in_scope,
)
from tools.data_pipeline.retrieval.alternative_competitions.wikipedia import _wikipedia_titles


def test_season_start_year_handles_full_short_and_calendar_labels() -> None:
    assert season_start_year("1992/1993") == 1992
    assert season_start_year("92/93") == 1992
    assert season_start_year("91/92") == 1991
    assert season_start_year("2024") == 2024
    assert season_start_year("unknown") == 0


def test_openfootball_selection_keeps_competitions_since_1992_only() -> None:
    assert _openfootball_path_is_in_scope("internationals", "euro/1992_euro.txt")
    assert not _openfootball_path_is_in_scope("internationals", "euro/1991_euro.txt")
    assert _openfootball_path_is_in_scope("england", "2024-25/facup.txt")
    assert _openfootball_path_is_in_scope("england", "2024-25/eflcup.txt")
    assert not _openfootball_path_is_in_scope("england", "2024-25/1-premierleague.txt")


def test_wikipedia_scope_includes_cup_and_europe_history_from_1992() -> None:
    titles = _wikipedia_titles()
    assert titles
    assert all(year >= 1992 for year, _ in titles)
    assert (1992, "1992–93 FA Cup") in titles
    assert (1992, "1992–93 UEFA Champions League") in titles
    assert (1992, "1992–93 UEFA Cup") in titles
    assert (2021, "2021–22 UEFA Europa Conference League") in titles
    assert not any("Conference League" in title for year, title in titles if year < 2021)
