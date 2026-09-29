"""Version-controlled, reviewed inputs shared by the ingestion loaders.

These files are reference evidence, not downloaded provider responses or a
runtime database. Keep their paths relative to this package so loaders do not
depend on the checkout's documentation tree or the current working directory.
"""

from pathlib import Path

REFERENCE_ROOT = Path(__file__).resolve().parent
TEAM_REFERENCE_PATH = REFERENCE_ROOT / "premier_league_team_names.json"
LEGACY_TEAMS_PATH = REFERENCE_ROOT / "legacy_fpl_teams.csv"
REVIEWED_PLAYER_BIRTH_DATES_PATH = REFERENCE_ROOT / "reviewed_player_birth_dates.json"
