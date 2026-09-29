"""Canonical DDL proof against isolated, in-memory SQLite only."""

from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.sqlite import connect_database


SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "src/tools/data_pipeline/ingestion/base_tables.sql"
).read_text(encoding="utf-8")


@pytest.fixture
def database():
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    try:
        yield connection
    finally:
        connection.close()


def _identities(connection: sqlite3.Connection) -> tuple[int, int, int, int]:
    competition = connection.execute(
        "INSERT INTO competitions (competition_key, name) VALUES (?, ?) RETURNING competition_id",
        ("premier-league", "Premier League"),
    ).fetchone()[0]
    season = connection.execute(
        "INSERT INTO seasons (competition_id, label, start_year, end_year) "
        "VALUES (?, ?, ?, ?) RETURNING season_id",
        (competition, "2025-26", 2025, 2026),
    ).fetchone()[0]
    home = connection.execute(
        "INSERT INTO teams (team_key, name) VALUES (?, ?) RETURNING team_id",
        ("arsenal", "Arsenal"),
    ).fetchone()[0]
    away = connection.execute(
        "INSERT INTO teams (team_key, name) VALUES (?, ?) RETURNING team_id",
        ("aston-villa", "Aston Villa"),
    ).fetchone()[0]
    return competition, season, home, away


def test_eight_tables_are_independent_of_existing_staging(database):
    database.execute("CREATE TABLE stg_official_fpl_teams (sample TEXT NOT NULL)")
    database.execute("INSERT INTO stg_official_fpl_teams VALUES ('retained')")
    database.executescript(SCHEMA)

    names = {
        row[0]
        for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert names == {
        "competitions", "seasons", "teams", "players", "fixtures",
        "team_source_ids", "player_source_ids", "fixture_source_ids",
        "stg_official_fpl_teams",
    }
    assert database.execute("SELECT sample FROM stg_official_fpl_teams").fetchone() == ("retained",)
    assert database.execute("PRAGMA foreign_keys").fetchone() == (1,)
    for table, target in (
        ("team_source_ids", "team_id"),
        ("player_source_ids", "player_id"),
        ("fixture_source_ids", "fixture_id"),
    ):
        indexes = database.execute(f"PRAGMA index_list({table})").fetchall()
        assert any(
            [row[2] for row in database.execute(f"PRAGMA index_info({index[1]})")] == [target]
            for index in indexes
        )


def test_competition_season_team_and_player_identity(database):
    competition, season, home, _ = _identities(database)
    assert (competition, season, home) == (1, 1, 1)
    for name in ("Alex Smith", "Alex Smith"):
        database.execute("INSERT INTO players (display_name) VALUES (?)", (name,))
    assert database.execute("SELECT count(*) FROM players").fetchone() == (2,)

    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO teams (team_key, name) VALUES ('arsenal', 'Renamed')")
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO seasons (competition_id, label, start_year, end_year) "
            "VALUES (?, '2025-26', 2025, 2026)", (competition,)
        )
    for label, start, end in (("2025-27", 2025, 2026), ("2026-25", 2026, 2025)):
        with pytest.raises(sqlite3.IntegrityError):
            database.execute(
                "INSERT INTO seasons (competition_id, label, start_year, end_year) "
                "VALUES (?, ?, ?, ?)", (competition, label, start, end)
            )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            "INSERT INTO seasons (competition_id, label, start_year, end_year) "
            "VALUES (999, '2024-25', 2024, 2025)"
        )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute("INSERT INTO players (display_name) VALUES (NULL)")
    database.execute("DELETE FROM teams WHERE team_id = ?", (home,))
    replacement = database.execute(
        "INSERT INTO teams (team_key, name) VALUES ('replacement', 'Replacement') "
        "RETURNING team_id"
    ).fetchone()[0]
    assert replacement > 2  # Removed canonical IDs are never reused.


def test_fixture_corrections_and_distinct_replay_preserve_identity(database):
    _, season, home, away = _identities(database)
    fixture = database.execute(
        "INSERT INTO fixtures (season_id, home_team_id, away_team_id, match_date) "
        "VALUES (?, ?, ?, ?) RETURNING fixture_id",
        (season, home, away, "2025-08-16"),
    ).fetchone()[0]
    assert database.execute(
        "SELECT kickoff_at, status, home_goals, away_goals FROM fixtures"
    ).fetchone() == (None, "unknown", None, None)
    database.execute(
        "INSERT INTO fixture_source_ids VALUES ('fpl.fixture.id', 'premier-league:2025-26', '42', ?)",
        (fixture,),
    )
    database.execute(
        "UPDATE fixtures SET match_date = '2025-09-20', kickoff_at = '2025-09-20T14:00:00Z', "
        "status = 'finished', home_goals = 2, away_goals = 1 WHERE fixture_id = ?",
        (fixture,),
    )
    replay = database.execute(
        "INSERT INTO fixtures (season_id, home_team_id, away_team_id, match_date, status) "
        "VALUES (?, ?, ?, '2025-09-20', 'finished') RETURNING fixture_id",
        (season, home, away),
    ).fetchone()[0]
    assert replay != fixture  # Same pairing and date do not define a fixture key.
    assert database.execute("SELECT fixture_id FROM fixture_source_ids").fetchone() == (fixture,)
    assert database.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize(
    "columns,values",
    [
        ("season_id, home_team_id, away_team_id", (999, 1, 2)),
        ("season_id, home_team_id, away_team_id", (1, 1, 1)),
        ("season_id, home_team_id, away_team_id, status", (1, 1, 2, "unverified")),
        ("season_id, home_team_id, away_team_id, home_goals", (1, 1, 2, 1)),
        ("season_id, home_team_id, away_team_id, home_goals, away_goals", (1, 1, 2, -1, 0)),
        ("season_id, home_team_id, away_team_id, home_goals, away_goals", (1, 1, 2, 1, 0)),
        ("season_id, home_team_id, away_team_id, match_date", (1, 1, 2, "unknown")),
        ("season_id, home_team_id, away_team_id, kickoff_at", (1, 1, 2, "2025-08-16T15:00:00")),
    ],
)
def test_invalid_fixtures_are_rejected(database, columns, values):
    _identities(database)
    placeholders = ", ".join("?" for _ in values)
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(f"INSERT INTO fixtures ({columns}) VALUES ({placeholders})", values)


@pytest.mark.parametrize(
    "table,target",
    [
        ("team_source_ids", "team_id"),
        ("player_source_ids", "player_id"),
        ("fixture_source_ids", "fixture_id"),
    ],
)
def test_source_mappings_are_scoped_text_ids_with_real_fks(database, table, target):
    _, season, home, away = _identities(database)
    database.execute("INSERT INTO players (display_name) VALUES ('A Player')")
    database.execute(
        "INSERT INTO fixtures (season_id, home_team_id, away_team_id) VALUES (?, ?, ?)",
        (season, home, away),
    )
    columns = f"source_namespace, source_scope, source_id, {target}"
    for scope, identifier in (("premier-league:2024-25", "42"),
                              ("premier-league:2025-26", "42"),
                              ("premier-league:2025-26", "0042")):
        database.execute(
            f"INSERT INTO {table} ({columns}) VALUES (?, ?, ?, ?)",
            ("fpl.source.id", scope, identifier, 1),
        )
    assert database.execute(f"SELECT count(*) FROM {table}").fetchone() == (3,)
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            f"INSERT INTO {table} ({columns}) VALUES (?, ?, ?, ?)",
            ("fpl.source.id", "premier-league:2024-25", "42", 1),
        )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            f"INSERT INTO {table} ({columns}) VALUES (?, ?, ?, ?)",
            ("fpl.source.code", "global", "42", 999),
        )
    with pytest.raises(sqlite3.IntegrityError):
        database.execute(
            f"INSERT INTO {table} ({columns}) VALUES (?, ?, ?, ?)",
            ("fpl.source.code", None, "42", 1),
        )


def test_existing_database_connector_enables_foreign_keys(tmp_path):
    path = tmp_path / "test.db"
    with sqlite3.connect(path):
        pass
    with connect_database(path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
