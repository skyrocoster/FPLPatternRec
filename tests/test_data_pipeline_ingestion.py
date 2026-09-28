from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.official_fpl_teams import (
    OfficialFplTeamsValidationError,
    load_official_fpl_teams,
)


def _team(team_id: int, *, link_url: str | None = "") -> dict[str, object]:
    return {
        "id": team_id,
        "code": team_id + 10,
        "pulse_id": team_id + 20,
        "position": team_id,
        "played": 0,
        "win": 0,
        "draw": 0,
        "loss": 0,
        "points": 0,
        "strength_overall_home": 4,
        "strength_overall_away": 5,
        "strength_attack_home": 6,
        "strength_attack_away": 7,
        "strength_defence_home": 8,
        "strength_defence_away": 9,
        "name": f"Team {team_id}",
        "short_name": f"T{team_id}",
        "link_url": link_url,
        "unavailable": False,
    }


def _payload(*, deadline: str = "2026-08-21T17:30:00Z") -> dict[str, object]:
    return {
        "events": [{"id": 1, "deadline_time": deadline}],
        "teams": [_team(1), _team(2, link_url="https://example.test/team/2")],
    }


def _write_bootstrap(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _create_database(path: Path) -> Path:
    with sqlite3.connect(path):
        pass
    return path


def _query_rows(database_path: Path) -> list[tuple[object, ...]]:
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            "SELECT softe_season, softe_team_id, softe_name, softe_link_url, softe_unavailable "
            "FROM stg_official_fpl_teams ORDER BY softe_season, softe_team_id"
        ).fetchall()


def test_load_derives_season_and_creates_prefixed_composite_key(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "raw" / "official_fpl_api" / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    _write_bootstrap(bootstrap_path, _payload())

    summary = load_official_fpl_teams(bootstrap_path, database_path)

    assert (summary.season, summary.team_count) == ("2026-27", 2)
    with sqlite3.connect(database_path) as connection:
        schema = connection.execute("PRAGMA table_info(stg_official_fpl_teams)").fetchall()
        assert all(row[1].startswith("softe_") for row in schema)
        assert schema[0][1:3] == ("softe_season", "TEXT")
        assert schema[1][1:3] == ("softe_team_id", "INTEGER")
        assert schema[18][1:4] == ("softe_link_url", "TEXT", 0)
        assert schema[19][1:3] == ("softe_unavailable", "BOOLEAN")
        assert [(row[1], row[5]) for row in schema if row[5]] == [
            ("softe_season", 1),
            ("softe_team_id", 2),
        ]
        assert all(row[3] == 1 for row in schema if row[1] != "softe_link_url")
        assert connection.execute(
            "SELECT softe_link_url FROM stg_official_fpl_teams WHERE softe_team_id = 1"
        ).fetchone() == (None,)


def test_load_keeps_team_ids_separate_between_seasons(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    _write_bootstrap(bootstrap_path, _payload())

    load_official_fpl_teams(bootstrap_path, database_path)
    override_summary = load_official_fpl_teams(
        bootstrap_path, database_path, season="2027-28"
    )

    assert override_summary.season == "2027-28"
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT softe_season, softe_team_id FROM stg_official_fpl_teams "
            "WHERE softe_team_id = 1 ORDER BY softe_season"
        ).fetchall() == [("2026-27", 1), ("2027-28", 1)]


def test_invalid_teams_leave_existing_season_unchanged(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    valid_payload = _payload()
    _write_bootstrap(bootstrap_path, valid_payload)
    load_official_fpl_teams(bootstrap_path, database_path)
    previous_rows = _query_rows(database_path)

    invalid_payload = _payload()
    invalid_payload["teams"] = [_team(1), {**_team(2), "points": "not-an-integer"}]
    _write_bootstrap(bootstrap_path, invalid_payload)

    with pytest.raises(OfficialFplTeamsValidationError, match="must be an integer"):
        load_official_fpl_teams(bootstrap_path, database_path)

    assert _query_rows(database_path) == previous_rows


def test_invalid_initial_input_does_not_create_staging_table(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    invalid_payload = _payload()
    invalid_payload["teams"] = []
    _write_bootstrap(bootstrap_path, invalid_payload)

    with pytest.raises(OfficialFplTeamsValidationError, match="non-empty list"):
        load_official_fpl_teams(bootstrap_path, database_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == []


def test_reloading_same_season_is_idempotent(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    _write_bootstrap(bootstrap_path, _payload())

    first_summary = load_official_fpl_teams(bootstrap_path, database_path)
    first_rows = _query_rows(database_path)
    second_summary = load_official_fpl_teams(bootstrap_path, database_path)

    assert second_summary == first_summary
    assert _query_rows(database_path) == first_rows
    assert len(first_rows) == 2


def test_invalid_season_format_is_rejected(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap-static.json"
    database_path = _create_database(tmp_path / "fplpatternrec.db")
    _write_bootstrap(bootstrap_path, _payload())

    with pytest.raises(OfficialFplTeamsValidationError, match="expected YYYY-YY"):
        load_official_fpl_teams(bootstrap_path, database_path, season="2026-2027")
