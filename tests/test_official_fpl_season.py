"""Read-only checks for saved official FPL season evidence."""

from __future__ import annotations

from datetime import datetime, timedelta
import json
from pathlib import Path

import pytest

from tools.data_pipeline.ingestion.official_fpl_season import (
    OfficialFplSeasonError,
    read_official_fpl_season,
)

ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data/raw/official_fpl_api"
SEASON = "2026-27"
TEAM_NAMES = (
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton and Hove Albion",
    "Burnley", "Chelsea", "Crystal Palace", "Everton", "Fulham", "Leeds United",
    "Liverpool", "Manchester City", "Manchester United", "Newcastle United",
    "Nottingham Forest", "Sunderland", "Tottenham Hotspur", "West Ham United",
    "Wolverhampton Wanderers",
)


def test_saved_current_season_includes_gw1_and_matches_official_history() -> None:
    evidence = read_official_fpl_season(RAW_ROOT, SEASON)

    assert evidence.season == SEASON
    assert len(evidence.teams) == 20
    assert len(evidence.elements) == 667
    assert "1" in evidence.teams and "1" in evidence.elements
    assert len(evidence.fixtures) < 380  # Scheduled fixtures are reviewed, then omitted.
    assert evidence.fixtures["1"][3] == 1
    assert any(observation[2] == 1 for observation in evidence.observations)
    assert {row[6] for row in evidence.observations} == set(evidence.fixtures)
    assert all(row[2] == fixture[3] and row[4] == fixture[2]
               for row in evidence.observations
               for fixture in (evidence.fixtures[row[6]],))
    assert all(len(fixture) == 6 and fixture[2].endswith("Z") for fixture in evidence.fixtures.values())


def _synthetic_root(root: Path) -> Path:
    summaries = root / "element_summaries"
    summaries.mkdir(parents=True)
    teams = [{"id": index, "name": name} for index, name in enumerate(TEAM_NAMES, 1)]
    elements = [
        {"id": 1, "code": 154561, "element_type": 1, "team": 20},
        {"id": 900, "code": 999999, "element_type": 5, "team": 1},
    ]
    bootstrap = {
        "events": [
            {"id": week, "deadline_time": "2026-08-21T17:30:00Z", "finished": week < 38}
            for week in range(1, 39)
        ],
        "teams": teams,
        "elements": elements,
    }

    rotating = list(range(1, 21))
    pairings: list[tuple[int, int, int]] = []
    for round_index in range(19):
        for match_index in range(10):
            pairings.append((round_index + 1, rotating[match_index], rotating[-match_index - 1]))
        rotating = [rotating[0], rotating[-1], *rotating[1:-1]]
    pairings.extend((week + 19, away, home) for week, home, away in pairings[:190])

    fixtures = []
    history = []
    for fixture_id, (week, home, away) in enumerate(pairings, 1):
        match_index = (fixture_id - 1) % 10
        kickoff = (
            datetime(2026, 8, 21) + timedelta(days=7 * (week - 1), minutes=match_index)
        ).isoformat(timespec="seconds") + "Z"
        finished = week < 38
        fixture = {
            "id": fixture_id,
            "team_h": home,
            "team_a": away,
            "event": week,
            "kickoff_time": kickoff,
            "finished": finished,
            "started": finished,
            "finished_provisional": finished,
            "minutes": 90 if finished else 0,
            "team_h_score": 2 if finished else None,
            "team_a_score": 1 if finished else None,
        }
        fixtures.append(fixture)
        if finished:
            history.append({
                "element": 1,
                "fixture": fixture_id,
                "opponent_team": away,
                "was_home": True,
                "kickoff_time": kickoff,
                "team_h_score": 2,
                "team_a_score": 1,
                "round": week,
                "minutes": 0,
            })

    for name, payload in (
        ("bootstrap-static.json", bootstrap),
        ("fixtures.json", fixtures),
        ("element_summaries/element_0001.json", {"fixtures": [], "history": history, "history_past": []}),
    ):
        (root / name).write_text(json.dumps(payload), encoding="utf-8")
    return root


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_synthetic_round_robin_skips_schedule_and_excludes_managers(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    (root / "element_summaries/element_0900.json").write_text("{}", encoding="utf-8")
    evidence = read_official_fpl_season(root, SEASON)

    assert len(evidence.fixtures) == 370
    assert len(evidence.observations) == 370
    assert evidence.elements == {"1": "154561"}
    assert evidence.fixtures["1"][:2] == ("arsenal", "wolves")
    assert {observation[2] for observation in evidence.observations} == set(range(1, 38))
    assert len({observation[3] for observation in evidence.observations}) > 1


def test_synthetic_season_mismatch_is_rejected(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    path = root / "bootstrap-static.json"
    payload = _load(path)
    payload["events"][0]["deadline_time"] = "2025-08-21T17:30:00Z"
    _save(path, payload)

    with pytest.raises(OfficialFplSeasonError, match="does not match requested season"):
        read_official_fpl_season(root, SEASON)


def test_synthetic_duplicate_history_observation_is_rejected(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    path = root / "element_summaries/element_0001.json"
    payload = _load(path)
    payload["history"].append(payload["history"][0])
    _save(path, payload)

    with pytest.raises(OfficialFplSeasonError, match="Duplicate player/fixture/gameweek"):
        read_official_fpl_season(root, SEASON)


def test_synthetic_scheduled_fixture_cannot_have_a_result(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    path = root / "fixtures.json"
    payload = _load(path)
    payload[-1]["team_h_score"] = 0
    _save(path, payload)

    with pytest.raises(OfficialFplSeasonError, match="contains result evidence"):
        read_official_fpl_season(root, SEASON)


def test_synthetic_incomplete_scheduled_fixture_is_rejected(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    path = root / "fixtures.json"
    payload = _load(path)
    payload[-1].pop("team_h_score")
    _save(path, payload)

    with pytest.raises(OfficialFplSeasonError, match="missing required fields.*team_h_score"):
        read_official_fpl_season(root, SEASON)


def test_synthetic_missing_summary_is_rejected(tmp_path: Path) -> None:
    root = _synthetic_root(tmp_path / "official")
    (root / "element_summaries/element_0001.json").unlink()

    with pytest.raises(OfficialFplSeasonError, match="summaries do not match bootstrap"):
        read_official_fpl_season(root, SEASON)
