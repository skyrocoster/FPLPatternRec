"""Schema installation proof uses temporary databases, never the Docker volume."""

from pathlib import Path
import sqlite3

import pytest

from tools.data_pipeline.ingestion.canonical_schema import (
    CANONICAL_TABLES,
    CanonicalSchemaError,
    install_canonical_schema,
)


def test_installs_eight_tables_without_changing_staged_rows(tmp_path: Path) -> None:
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE stg_official_fpl_teams (softe_name TEXT)")
        connection.execute("INSERT INTO stg_official_fpl_teams VALUES ('Arsenal')")

    install_canonical_schema(database)

    with sqlite3.connect(database) as connection:
        actual = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        assert actual == CANONICAL_TABLES | {"stg_official_fpl_teams"}
        assert connection.execute("SELECT softe_name FROM stg_official_fpl_teams").fetchall() == [
            ("Arsenal",),
        ]
        assert connection.execute("PRAGMA quick_check").fetchone() == ("ok",)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []

    with pytest.raises(CanonicalSchemaError, match="need review"):
        install_canonical_schema(database)


def test_refuses_unexpected_preexisting_tables_without_creating_schema(tmp_path: Path) -> None:
    database = tmp_path / "isolated.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE user_notes (note TEXT)")

    with pytest.raises(CanonicalSchemaError, match="user_notes"):
        install_canonical_schema(database)

    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall() == [("user_notes",)]
