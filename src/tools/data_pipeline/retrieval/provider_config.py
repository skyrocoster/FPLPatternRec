"""Provider endpoints and ordered statistic selections, separate from transport.

Keep these selections explicit: their order determines the retrieval request
order. This module contains no network calls or filesystem operations.
"""

FPL_API = "https://fantasy.premierleague.com/api"
PULSELIVE_API = "https://footballapi.pulselive.com/football"
FOTMOB_API = "https://www.fotmob.com/api/data"
FPL_ARCHIVE_CONTENTS_API = (
    "https://api.github.com/repos/vaastav/Fantasy-Premier-League/contents"
)

PL_PLAYER_STATS = (
    "appearances",
    "minutes_played",
    "starts",
    "goals",
    "goal_assist",
    "clean_sheet",
    "saves",
    "penalty_save",
    "yellow_card",
    "red_card",
    "own_goals",
    "tackles",
    "interception",
    "clearance",
    "recoveries",
    "pass",
    "touches",
    "total_scoring_att",
    "expected_goals",
    "expected_assists",
    "big_chance_created",
    "duel_won",
    "aerial_won",
    "penalty_miss",
)
PL_TEAM_STATS = (
    "wins",
    "draws",
    "losses",
    "goals",
    "goals_conceded",
    "clean_sheet",
    "shots",
    "shots_on_target",
    "pass",
    "possession",
    "yellow_card",
    "red_card",
    "cross",
    "big_chance_created",
)
FOTMOB_HISTORICAL_PLAYER_STATS = (
    "goals",
    "goal_assist",
    "mins_played",
    "expected_goals",
    "expected_assists",
    "ontarget_scoring_att",
    "accurate_pass",
    "clean_sheet",
    "saves",
    "total_tackle",
    "interception",
    "effective_clearance",
    "ball_recovery",
    "total_yel_card",
    "total_red_card",
)
FOTMOB_HISTORICAL_TEAM_STATS = (
    "goals_team_match",
    "goals_conceded_team_match",
    "expected_goals_team",
    "possession_percentage_team",
    "clean_sheet_team",
    "accurate_pass_team",
    "saves_team",
    "ontarget_scoring_att_team",
    "corner_taken_team",
    "total_yel_card_team",
    "total_red_card_team",
)
