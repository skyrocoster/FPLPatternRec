"""SQLite locations and safe connection helpers for data-pipeline loaders."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DATABASE_PATH = Path("/data/fplpatternrec.db")


def connect_database(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open an existing database without creating a file or parent directory."""
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"SQLite database does not exist at {path}; run dev.ps1 setup first."
        )
    connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=rw", uri=True)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
