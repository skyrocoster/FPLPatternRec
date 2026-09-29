"""Backfill immutable, season-scoped FPL team IDs from saved archives."""

from dataclasses import dataclass
from pathlib import Path

from .canonical_teams import (
    COMPETITION_KEY, COMPETITION_NAME, SOURCE_NAMESPACE, TEAM_REFERENCE_PATH, _read_clubs,
)
from .player_gameweek_teams import SEASONS, _source_teams
from .sqlite import DATABASE_PATH, connect_database


class ArchiveTeamsError(ValueError):
    """The saved season is incomplete or disagrees with accepted canonical data."""


@dataclass(frozen=True)
class ArchiveTeamsSummary:
    season: str
    mapped_team_count: int


def load_archive_teams(
    season: str,
    archive_root: Path,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
) -> ArchiveTeamsSummary:
    """Map a completed historical season once; identical repeats preserve all IDs."""
    if season not in SEASONS or season == "2026-27":
        raise ArchiveTeamsError("Historical team mappings require 2016-17 through 2025-26")
    clubs, aliases = _read_clubs(Path(reference_path))
    teams = _source_teams(Path(archive_root) / season, aliases)
    if set(teams) != {str(number) for number in range(1, 21)}:
        raise ArchiveTeamsError(f"Expected exactly FPL team IDs 1-20 for {season}")

    scope = f"{COMPETITION_KEY}:{season}"
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        canonical = {key: (team_id, name) for team_id, key, name in connection.execute(
            "SELECT team_id, team_key, name FROM teams"
        )}
        if any(canonical.get(key, (None, None))[1] != name for key, name in clubs):
            raise ArchiveTeamsError("Canonical clubs differ from reviewed team reference")
        season_row = connection.execute(
            "SELECT s.season_id, s.start_year, s.end_year, c.name FROM seasons s "
            "JOIN competitions c ON c.competition_id = s.competition_id "
            "WHERE c.competition_key = ? AND s.label = ?", (COMPETITION_KEY, season),
        ).fetchone()
        start = int(season[:4])
        if season_row is None or season_row[1:] != (start, start + 1, COMPETITION_NAME):
            raise ArchiveTeamsError(f"Missing or conflicting canonical season {season}")
        fixtures = connection.execute(
            "SELECT home_team_id, away_team_id FROM fixtures "
            "WHERE season_id = ? AND status = 'finished'", (season_row[0],)
        ).fetchall()
        fixture_clubs = {team_id for fixture in fixtures for team_id in fixture}
        expected_clubs = {canonical[key][0] for key in teams.values()}
        if len(fixtures) != 380 or fixture_clubs != expected_clubs:
            raise ArchiveTeamsError(f"Canonical fixtures do not cover the completed 20-club season {season}")

        desired = {source_id: canonical[key][0] for source_id, key in teams.items()}
        existing = dict(connection.execute(
            "SELECT source_id, team_id FROM team_source_ids "
            "WHERE source_namespace = ? AND source_scope = ?", (SOURCE_NAMESPACE, scope),
        ))
        if existing and existing != desired:
            raise ArchiveTeamsError(f"Partial or changed FPL team mappings for {scope}; review required")
        if not existing:
            connection.executemany(
                "INSERT INTO team_source_ids (source_namespace, source_scope, source_id, team_id) "
                "VALUES (?, ?, ?, ?)",
                [(SOURCE_NAMESPACE, scope, source_id, desired[source_id]) for source_id in sorted(desired, key=int)],
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return ArchiveTeamsSummary(season, len(desired))
