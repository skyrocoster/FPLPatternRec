"""Accept Premier League local match dates for already identified FPL fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

from .canonical_fixtures import SEASONS
from .canonical_teams import COMPETITION_KEY, TEAM_REFERENCE_PATH, _normalize, _read_clubs
from .sqlite import DATABASE_PATH, connect_database


class MatchDatesError(ValueError):
    """Saved Premier League evidence cannot safely date the canonical fixtures."""


@dataclass(frozen=True)
class MatchDatesSummary:
    season: str
    fixture_count: int


def _local_kickoff(value: dict, season: str) -> tuple[str, str]:
    """Confirm the PL local label and timestamp describe the same UTC instant."""
    if not isinstance(value, dict):
        raise MatchDatesError(f"Missing Premier League kickoff for {season}")
    millis, label = value.get("millis"), value.get("label")
    if (type(millis) not in (int, float) or millis != int(millis)
            or not isinstance(label, str)):
        raise MatchDatesError(f"Invalid Premier League kickoff for {season}")
    match = re.fullmatch(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun) (\d{1,2}) "
                         r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
                         r"(\d{4}), (\d{2}):(\d{2}) (BST|GMT)", label)
    if match is None:
        raise MatchDatesError(f"Unreviewed Premier League local kickoff {label!r}")
    try:
        local = datetime.strptime(label[:-4], "%a %d %b %Y, %H:%M")
        utc = datetime.fromtimestamp(millis / 1000, timezone.utc)
    except (ValueError, OverflowError, OSError) as error:
        raise MatchDatesError(f"Invalid Premier League kickoff {label!r}") from error
    if local.strftime("%a") != match[1]:
        raise MatchDatesError(f"Premier League kickoff weekday differs: {label!r}")
    offset = 1 if match[7] == "BST" else 0
    if value.get("gmtOffset") not in (None, offset):
        raise MatchDatesError(f"Premier League kickoff offset differs: {label!r}")
    if local.replace(tzinfo=timezone(timedelta(hours=offset))).astimezone(timezone.utc) != utc:
        raise MatchDatesError(f"Premier League local and UTC kickoffs differ: {label!r}")
    return local.date().isoformat(), utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def _saved_matches(folder: Path, season: str, aliases: dict[str, str]) -> dict[tuple[str, str], tuple]:
    first = folder / "page-000.json"
    try:
        info = json.loads(first.read_text(encoding="utf-8"))["pageInfo"]
    except (KeyError, TypeError) as error:
        raise MatchDatesError(f"Missing Premier League fixture page metadata for {season}") from error
    if not isinstance(info, dict):
        raise MatchDatesError(f"Invalid Premier League fixture page metadata for {season}")
    pages = info.get("numPages")
    if type(pages) is not int or pages < 1:
        raise MatchDatesError(f"Missing Premier League fixture pages for {season}")
    if {path.name for path in folder.glob("page-*.json")} != {
        f"page-{index:03d}.json" for index in range(pages)
    }:
        raise MatchDatesError(f"Incomplete Premier League fixture pages for {season}")
    matches: dict[tuple[str, str], tuple] = {}
    ids: set[int] = set()
    count = 0
    for index in range(pages):
        payload = json.loads((folder / f"page-{index:03d}.json").read_text(encoding="utf-8"))
        if (not isinstance(payload, dict) or not isinstance(payload.get("pageInfo"), dict)
                or payload["pageInfo"].get("page") != index
                or not isinstance(payload.get("content"), list)):
            raise MatchDatesError(f"Invalid Premier League fixture page {index} for {season}")
        for match in payload["content"]:
            count += 1
            if not isinstance(match, dict):
                raise MatchDatesError(f"Invalid Premier League match in {season}")
            source_id = match.get("id")
            if (type(source_id) not in (int, float) or source_id != int(source_id)
                    or source_id in ids):
                raise MatchDatesError(f"Invalid or duplicate Premier League match ID in {season}")
            ids.add(source_id)
            sides = match.get("teams")
            if not isinstance(sides, list) or len(sides) != 2:
                raise MatchDatesError(f"Missing Premier League match clubs in {season}")
            try:
                home, away = (aliases[_normalize(side["team"]["name"])] for side in sides)
            except (KeyError, TypeError, AttributeError) as error:
                raise MatchDatesError(f"Unreviewed Premier League match clubs in {season}") from error
            if home == away or (home, away) in matches:
                raise MatchDatesError(f"Duplicate Premier League club pairing in {season}")
            if match.get("status") == "C":
                date, kickoff = _local_kickoff(match.get("kickoff"), season)
                scores = [side.get("score") for side in sides]
                if any(type(score) not in (int, float) or score != int(score) or score < 0 for score in scores):
                    raise MatchDatesError(f"Invalid Premier League final score in {season}")
                matches[home, away] = (date, kickoff, int(scores[0]), int(scores[1]))
            else:
                matches[home, away] = None
    if count != info.get("numEntries"):
        raise MatchDatesError(f"Premier League fixture page count differs in {season}")
    return matches


def load_match_dates(
    season: str,
    fixtures_root: Path,
    database_path: Path = DATABASE_PATH,
    reference_path: Path = TEAM_REFERENCE_PATH,
) -> MatchDatesSummary:
    """Backfill one season atomically, without replacing accepted dates or identities."""
    if season not in SEASONS:
        raise MatchDatesError("Only saved 2016-17 through 2026-27 seasons have been reviewed")
    _, aliases = _read_clubs(Path(reference_path))
    folder = Path(fixtures_root) / (
        "English-Premier-League-Season-2026-2027" if season == "2026-27" else season
    )
    source = _saved_matches(folder, season, aliases)
    connection = connect_database(database_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute(
            "SELECT f.fixture_id, h.team_key, a.team_key, f.match_date, f.kickoff_at, "
            "f.home_goals, f.away_goals, f.status FROM fixtures f "
            "JOIN seasons s ON s.season_id = f.season_id "
            "JOIN competitions c ON c.competition_id = s.competition_id "
            "JOIN teams h ON h.team_id = f.home_team_id "
            "JOIN teams a ON a.team_id = f.away_team_id "
            "WHERE c.competition_key = ? AND s.label = ?", (COMPETITION_KEY, season),
        ).fetchall()
        if not existing:
            raise MatchDatesError(f"No canonical fixtures for {season}")
        if season != "2026-27" and len(existing) != 380:
            raise MatchDatesError(f"Incomplete canonical fixture season {season}")
        desired: dict[int, str] = {}
        accepted: dict[int, str | None] = {}
        for fixture_id, home, away, date, kickoff, hg, ag, status in existing:
            matched = source.get((home, away))
            if matched is None or status != "finished" or matched[1:] != (kickoff, hg, ag):
                raise MatchDatesError(f"Premier League fixture differs from canonical {season}:{fixture_id}")
            desired[fixture_id] = matched[0]
            accepted[fixture_id] = date
        if any(date is not None and date != desired[fixture_id]
               for fixture_id, date in accepted.items()) or (
                   season != "2026-27" and any(date is not None for date in accepted.values())
                   and accepted != desired
               ):
            raise MatchDatesError(f"Partial or changed canonical match dates for {season}; review required")
        if any(date is None for date in accepted.values()):
            connection.executemany(
                "UPDATE fixtures SET match_date = ? WHERE fixture_id = ? AND match_date IS NULL",
                [(desired[fixture_id], fixture_id) for fixture_id, date in accepted.items() if date is None],
            )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return MatchDatesSummary(season, len(desired))
