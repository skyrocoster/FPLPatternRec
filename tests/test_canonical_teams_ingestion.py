"""The first canonical loader only touches isolated SQLite fixture databases."""

import json
from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.canonical_teams import (
    TEAM_REFERENCE_PATH,
    CanonicalTeamsValidationError,
    load_canonical_teams,
)
from tools.data_pipeline.ingestion.official_fpl_teams import load_official_fpl_teams


SCHEMA = Path(__file__).resolve().parents[1] / "src/tools/data_pipeline/ingestion/base_tables.sql"


def _database(tmp_path: Path, *, canonical_schema: bool = True, staging: bool = True) -> Path:
    path = tmp_path / "isolated.db"
    with sqlite3.connect(path) as connection:
        if canonical_schema:
            connection.executescript(SCHEMA.read_text(encoding="utf-8"))
        if staging:
            connection.execute(
                "CREATE TABLE stg_official_fpl_teams ("
                "softe_season TEXT NOT NULL, softe_team_id INTEGER NOT NULL, "
                "softe_name TEXT NOT NULL, PRIMARY KEY (softe_season, softe_team_id))"
            )
    return path


def _stage(path: Path, rows: list[tuple[str, int, str]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.executemany("INSERT INTO stg_official_fpl_teams VALUES (?, ?, ?)", rows)


def _reference(tmp_path: Path, clubs=None) -> Path:
    if clubs is None:
        clubs = [
            {"id": "arsenal", "canonical_name": "Arsenal", "aliases": ["Arsenal FC"]},
            {"id": "manchester-city", "canonical_name": "Manchester City", "aliases": ["Man City"]},
        ]
    path = tmp_path / "clubs.json"
    path.write_text(json.dumps({
        "dataset": "premier_league_team_names",
        "schema_version": 1,
        "scope": {"club_count": len(clubs)},
        "clubs": clubs,
    }), encoding="utf-8")
    return path


def _counts(path: Path) -> tuple[int, ...]:
    with sqlite3.connect(path) as connection:
        return tuple(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in (
            "competitions", "seasons", "teams", "team_source_ids",
            "players", "fixtures", "player_source_ids", "fixture_source_ids",
        ))


def test_clubs_load_directly_from_json_without_staging_or_season(tmp_path: Path) -> None:
    database = _database(tmp_path, staging=False)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO teams (team_key, name) VALUES ('unrelated', 'Unrelated')")

    first = load_canonical_teams(database_path=database)
    with sqlite3.connect(database) as connection:
        ids = connection.execute("SELECT team_key, team_id FROM teams ORDER BY team_key").fetchall()
    second = load_canonical_teams(database_path=database)

    assert first == second
    assert (first.season, first.club_count, first.mapped_team_count) == (None, 51, 0)
    assert len(ids) == 52
    assert ("unrelated", 1) in ids
    assert _counts(database) == (0, 0, 52, 0, 0, 0, 0, 0)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT team_key, team_id FROM teams ORDER BY team_key"
        ).fetchall() == ids


def test_loads_reviewed_clubs_and_scoped_ids_without_replacing_rows(tmp_path: Path) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path)
    _stage(database, [("2026-27", 1, " Arsenal F.C. "), ("2026-27", 2, "Man. City")])

    first = load_canonical_teams("2026-27", database, reference)
    with sqlite3.connect(database) as connection:
        identities = connection.execute(
            "SELECT team_key, team_id FROM teams ORDER BY team_key"
        ).fetchall()
        mappings = connection.execute(
            "SELECT source_namespace, source_scope, source_id, team_id "
            "FROM team_source_ids ORDER BY source_id"
        ).fetchall()
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    second = load_canonical_teams("2026-27", database, reference)

    assert second == first
    assert (first.season, first.club_count, first.mapped_team_count) == ("2026-27", 2, 2)
    assert identities == [("arsenal", 1), ("manchester-city", 2)]
    assert mappings == [
        ("fpl.team.id", "premier-league:2026-27", "1", 1),
        ("fpl.team.id", "premier-league:2026-27", "2", 2),
    ]
    assert _counts(database) == (1, 1, 2, 2, 0, 0, 0, 0)


def test_mapping_after_seed_keeps_all_club_ids(tmp_path: Path) -> None:
    database = _database(tmp_path, staging=False)
    reference = _reference(tmp_path)
    load_canonical_teams(database_path=database, reference_path=reference)
    with sqlite3.connect(database) as connection:
        original = connection.execute("SELECT team_key, team_id FROM teams ORDER BY team_key").fetchall()
        connection.execute(
            "CREATE TABLE stg_official_fpl_teams (softe_season TEXT, softe_team_id INTEGER, softe_name TEXT)"
        )
    _stage(database, [("2026-27", 2, "Man City")])

    result = load_canonical_teams("2026-27", database, reference)

    assert (result.club_count, result.mapped_team_count) == (2, 1)
    assert _counts(database) == (1, 1, 2, 1, 0, 0, 0, 0)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT team_key, team_id FROM teams ORDER BY team_key"
        ).fetchall() == original


def test_overlapping_fpl_ids_in_different_seasons_remain_distinct(tmp_path: Path) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path)
    _stage(database, [("2025-26", 1, "Arsenal"), ("2026-27", 1, "Man City")])

    load_canonical_teams("2025-26", database, reference)
    load_canonical_teams("2026-27", database, reference)

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT source_scope, team_id FROM team_source_ids ORDER BY source_scope"
        ).fetchall() == [("premier-league:2025-26", 1), ("premier-league:2026-27", 2)]
        assert _counts(database) == (1, 2, 2, 2, 0, 0, 0, 0)


@pytest.mark.parametrize("names", [
    ["Unreviewed FC"], ["Arsenal", "Arsenal FC"],
])
def test_unresolved_or_duplicate_staged_names_do_not_write(tmp_path: Path, names: list[str]) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path)
    _stage(database, [("2026-27", index, name) for index, name in enumerate(names, 1)])

    with pytest.raises(CanonicalTeamsValidationError):
        load_canonical_teams("2026-27", database, reference)

    assert _counts(database) == (0,) * 8


def test_missing_schema_or_staged_season_does_not_create_tables(tmp_path: Path) -> None:
    database = _database(tmp_path, canonical_schema=False)
    reference = _reference(tmp_path)
    _stage(database, [("2026-27", 1, "Arsenal")])
    with pytest.raises(CanonicalTeamsValidationError, match="apply base_tables.sql"):
        load_canonical_teams("2026-27", database, reference)
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall() == [("stg_official_fpl_teams",)]

    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(CanonicalTeamsValidationError, match="No staged"):
        load_canonical_teams("2025-26", database, reference)
    assert _counts(database) == (0,) * 8


def test_conflicting_mapping_rolls_back_new_season_and_clubs(tmp_path: Path) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path)
    _stage(database, [("2026-27", 1, "Arsenal")])
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO teams (team_key, name) VALUES ('manchester-city', 'Manchester City')")
        connection.execute(
            "INSERT INTO team_source_ids VALUES ('fpl.team.id', 'premier-league:2026-27', '1', 1)"
        )

    with pytest.raises(CanonicalTeamsValidationError, match="different club"):
        load_canonical_teams("2026-27", database, reference)

    assert _counts(database) == (0, 0, 1, 1, 0, 0, 0, 0)


def test_existing_canonical_name_is_not_silently_replaced(tmp_path: Path) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path)
    _stage(database, [("2026-27", 1, "Arsenal")])
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO teams (team_key, name) VALUES ('arsenal', 'Reviewed separately')")
    with pytest.raises(CanonicalTeamsValidationError, match="differs"):
        load_canonical_teams("2026-27", database, reference)
    assert _counts(database) == (0, 0, 1, 0, 0, 0, 0, 0)


def test_ambiguous_reference_alias_is_rejected_before_writing(tmp_path: Path) -> None:
    database = _database(tmp_path)
    reference = _reference(tmp_path, [
        {"id": "club-a", "canonical_name": "Club A", "aliases": ["Shared"]},
        {"id": "club-b", "canonical_name": "Club B", "aliases": ["Shared"]},
    ])
    _stage(database, [("2026-27", 1, "Club A")])
    with pytest.raises(CanonicalTeamsValidationError, match="Ambiguous"):
        load_canonical_teams("2026-27", database, reference)
    assert _counts(database) == (0,) * 8


def test_full_reviewed_reference_matches_known_fpl_name_forms(tmp_path: Path) -> None:
    database = _database(tmp_path)
    _stage(database, [("2026-27", 3, "Man City"), ("2026-27", 4, "Wolves")])

    result = load_canonical_teams("2026-27", database, TEAM_REFERENCE_PATH)

    assert (result.club_count, result.mapped_team_count) == (51, 2)
    assert _counts(database) == (1, 1, 51, 2, 0, 0, 0, 0)


def test_saved_bootstrap_resolves_through_the_real_staging_loader(tmp_path: Path) -> None:
    bootstrap = Path(__file__).resolve().parents[1] / "data/raw/official_fpl_api/bootstrap-static.json"
    if not bootstrap.is_file():
        pytest.skip("Local saved bootstrap is not available")
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(SCHEMA.read_text(encoding="utf-8"))

    staged = load_official_fpl_teams(bootstrap, database)
    loaded = load_canonical_teams(staged.season, database)

    assert loaded.season == staged.season
    assert loaded.mapped_team_count == staged.team_count
    assert loaded.club_count == 51
    assert _counts(database) == (1, 1, 51, staged.team_count, 0, 0, 0, 0)
