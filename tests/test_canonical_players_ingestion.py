"""Canonical player identity tests use isolated, disposable SQLite files only."""

import json
from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.canonical_players import (
    CanonicalPlayersValidationError,
    load_canonical_players,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"


def _database(tmp_path: Path, schema: bool = True) -> Path:
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        if schema:
            connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    return database


def _bootstrap(tmp_path: Path, elements: list[dict], deadline: str = "2026-08-21T17:30:00Z") -> Path:
    path = tmp_path / "bootstrap.json"
    path.write_text(json.dumps({
        "events": [{"deadline_time": deadline}], "elements": elements,
    }), encoding="utf-8")
    return path


def _player(source_id: int = 1, code: int = 100, **updates) -> dict:
    player = {
        "id": source_id, "code": code, "element_type": 1,
        "first_name": "David", "second_name": "Raya Martín", "web_name": "Raya",
        "birth_date": "1995-09-15",
    }
    player.update(updates)
    return player


def _rows(database: Path) -> tuple[list, list]:
    with sqlite3.connect(database) as connection:
        return (
            connection.execute(
                "SELECT player_id, display_name, date_of_birth FROM players ORDER BY player_id"
            ).fetchall(),
            connection.execute(
                "SELECT source_namespace, source_scope, source_id, player_id "
                "FROM player_source_ids ORDER BY source_namespace, source_scope"
            ).fetchall(),
        )


def test_fpl_names_dates_and_scoped_identifiers_are_stable_on_repeat_load(tmp_path: Path) -> None:
    database = _database(tmp_path)
    bootstrap = _bootstrap(tmp_path, [
        _player(), _player(2, 101, first_name="Alex", second_name="Smith", birth_date=None),
        {"id": 3, "code": 102, "element_type": 5},
    ])

    first = load_canonical_players("2026-27", bootstrap, database)
    rows = _rows(database)
    second = load_canonical_players("2026-27", bootstrap, database)

    assert first == second
    assert (first.player_count, first.excluded_manager_count) == (2, 1)
    assert _rows(database) == rows
    assert rows[0] == [(1, "David Raya Martín", "1995-09-15"), (2, "Alex Smith", None)]
    assert rows[1] == [
        ("fpl.element.code", "premier-league:2026-27", "100", 1),
        ("fpl.element.code", "premier-league:2026-27", "101", 2),
        ("fpl.element.id", "premier-league:2026-27", "1", 1),
        ("fpl.element.id", "premier-league:2026-27", "2", 2),
    ]
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_same_element_id_in_another_season_does_not_reuse_canonical_identity(tmp_path: Path) -> None:
    database = _database(tmp_path)
    load_canonical_players("2026-27", _bootstrap(tmp_path, [_player()]), database)
    earlier = _bootstrap(tmp_path, [
        _player(1, 200, first_name="Other", second_name="Footballer", birth_date=None),
    ], "2025-08-21T17:30:00Z")

    load_canonical_players("2025-26", earlier, database)

    assert len(_rows(database)[0]) == 2
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT source_scope, player_id FROM player_source_ids "
            "WHERE source_namespace = 'fpl.element.id' ORDER BY source_scope"
        ).fetchall() == [("premier-league:2025-26", 2), ("premier-league:2026-27", 1)]


def test_repeat_preserves_reviewed_dob_when_saved_fpl_date_is_unknown(tmp_path: Path) -> None:
    database = _database(tmp_path)
    bootstrap = _bootstrap(tmp_path, [_player(birth_date=None)])
    load_canonical_players("2026-27", bootstrap, database)
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE players SET date_of_birth = '1995-09-15' WHERE player_id = 1")

    load_canonical_players("2026-27", bootstrap, database)

    assert _rows(database)[0] == [(1, "David Raya Martín", "1995-09-15")]


@pytest.mark.parametrize("elements", [
    [_player(1, 100), _player(2, 100)],
    [_player(1, 100), _player(1, 101)],
    [_player(1, 100, birth_date="2026-02-30")],
    [_player(1, 100, element_type=6)],
    [_player(1, 100, first_name=" ")],
])
def test_invalid_payload_never_writes(tmp_path: Path, elements: list[dict]) -> None:
    database = _database(tmp_path)
    with pytest.raises(CanonicalPlayersValidationError):
        load_canonical_players("2026-27", _bootstrap(tmp_path, elements), database)
    assert _rows(database) == ([], [])


def test_wrong_season_and_missing_schema_do_not_write(tmp_path: Path) -> None:
    bootstrap = _bootstrap(tmp_path, [_player()])
    database = _database(tmp_path, schema=False)
    with pytest.raises(CanonicalPlayersValidationError, match="tables missing"):
        load_canonical_players("2026-27", bootstrap, database)
    with pytest.raises(CanonicalPlayersValidationError, match="belongs to 2026-27"):
        load_canonical_players("2025-26", bootstrap, database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall() == []


def test_existing_name_without_mapping_requires_review_instead_of_duplication(tmp_path: Path) -> None:
    database = _database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO players (display_name, date_of_birth) VALUES ('David Raya Martín', NULL)"
        )
    with pytest.raises(CanonicalPlayersValidationError, match="unmapped existing"):
        load_canonical_players("2026-27", _bootstrap(tmp_path, [_player()]), database)
    assert _rows(database)[0] == [(1, "David Raya Martín", None)]
    assert _rows(database)[1] == []


def test_conflicting_code_mapping_rolls_back_all_new_players(tmp_path: Path) -> None:
    database = _database(tmp_path)
    bootstrap = _bootstrap(tmp_path, [_player(1, 100), _player(2, 101, first_name="Alex")])
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO players (display_name) VALUES ('Existing')")
        connection.execute(
            "INSERT INTO player_source_ids VALUES ('fpl.element.code', 'premier-league:2026-27', '101', 1)"
        )

    with pytest.raises(CanonicalPlayersValidationError, match="incomplete or conflicting"):
        load_canonical_players("2026-27", bootstrap, database)
    assert _rows(database) == (
        [(1, "Existing", None)], [("fpl.element.code", "premier-league:2026-27", "101", 1)],
    )


def test_changed_canonical_details_require_review_not_silent_overwrite(tmp_path: Path) -> None:
    database = _database(tmp_path)
    bootstrap = _bootstrap(tmp_path, [_player()])
    load_canonical_players("2026-27", bootstrap, database)
    original = _rows(database)

    changed = _bootstrap(tmp_path, [_player(second_name="Changed")])
    with pytest.raises(CanonicalPlayersValidationError, match="differs"):
        load_canonical_players("2026-27", changed, database)
    assert _rows(database) == original


def test_saved_bootstrap_loads_all_current_players_when_available(tmp_path: Path) -> None:
    bootstrap = ROOT / "data/raw/official_fpl_api/bootstrap-static.json"
    if not bootstrap.is_file():
        pytest.skip("Saved official FPL bootstrap is unavailable")
    database = _database(tmp_path)

    summary = load_canonical_players("2026-27", bootstrap, database)

    assert summary.player_count == 667
    assert len(_rows(database)[0]) == 667
    assert len(_rows(database)[1]) == 1334
