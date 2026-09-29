"""Shared catalogue helpers for alternative-competition providers."""

from __future__ import annotations

import re

from ..common import USER_AGENT

GITHUB_API = "https://api.github.com/repos"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_HEADERS = {
    "Accept": "application/json",
    "User-Agent": f"{USER_AGENT} (historical competition data)",
}
FOTMOB_HEADERS = {"Accept": "application/json", "Referer": "https://www.fotmob.com/"}

OPENFOOTBALL_REPOSITORIES = (
    "internationals",
    "worldcup",
    "euro",
    "champions-league",
    "club-worldcup",
    "england",
)

FOTMOB_COMPETITIONS = (
    (132, "FA Cup"),
    (133, "EFL Cup"),
    (247, "Community Shield"),
    (42, "Champions League"),
    (10611, "Champions League Qualification"),
    (73, "Europa League"),
    (10613, "Europa League Qualification"),
    (10216, "Conference League"),
    (10615, "Conference League Qualification"),
    (74, "UEFA Super Cup"),
    (78, "FIFA Club World Cup"),
    (77, "FIFA World Cup"),
    (10195, "World Cup Qualification UEFA"),
    (10196, "World Cup Qualification CAF"),
    (10197, "World Cup Qualification AFC"),
    (10198, "World Cup Qualification CONCACAF"),
    (10199, "World Cup Qualification CONMEBOL"),
    (10200, "World Cup Qualification OFC"),
    (10201, "World Cup Qualification Inter-confederation"),
    (50, "EURO"),
    (10607, "EURO Qualification"),
    (9806, "UEFA Nations League A"),
    (9807, "UEFA Nations League B"),
    (9808, "UEFA Nations League C"),
    (9809, "UEFA Nations League D"),
    (44, "Copa America"),
    (289, "Africa Cup of Nations"),
    (10608, "Africa Cup of Nations Qualification"),
    (290, "Asian Cup"),
    (10609, "Asian Cup Qualification Playoff"),
    (298, "CONCACAF Gold Cup"),
    (9821, "CONCACAF Nations League"),
    (66, "Summer Olympics"),
    (288, "EURO U21"),
    (10437, "EURO U21 Qualification"),
    (296, "World Cup U20"),
    (306, "World Cup U17"),
)

PLAYER_LEADERBOARDS = frozenset(
    {"goals", "goal_assist", "mins_played", "rating", "clean_sheet", "yellow_card", "red_card"}
)
TEAM_LEADERBOARDS = frozenset({"goals_team_match", "expected_goals_team", "clean_sheet_team"})


def season_start_year(label: str) -> int:
    """Return the start year for a competition season or calendar-year event."""
    match = re.search(r"(?:19|20)\d{2}", label)
    if match:
        return int(match.group())
    short_year = re.match(r"(\d{2})[/\-]", label)
    if not short_year:
        return 0
    year = int(short_year.group(1))
    return 1900 + year if year >= 90 else 2000 + year
