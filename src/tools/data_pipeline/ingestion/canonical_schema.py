"""Install the initial canonical schema without migrating or replacing existing tables."""

from pathlib import Path

from .sqlite import DATABASE_PATH, connect_database

SCHEMA_PATH = Path(__file__).with_name("base_tables.sql")
CANONICAL_TABLES = {
    "competitions", "seasons", "teams", "players", "fixtures",
    "team_source_ids", "player_source_ids", "fixture_source_ids",
}


class CanonicalSchemaError(ValueError):
    """Raised when the shared database is not safe for initial schema installation."""


def install_canonical_schema(database_path: Path = DATABASE_PATH) -> None:
    """Create the eight canonical tables only on a valid, staging-only database."""
    ddl = SCHEMA_PATH.read_text(encoding="utf-8")
    connection = connect_database(database_path)
    try:
        if connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise CanonicalSchemaError("Database quick_check failed; no schema was installed.")
        existing = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        unexpected = existing - {"stg_official_fpl_teams"}
        if unexpected:
            raise CanonicalSchemaError(
                f"Existing non-staging tables need review before installation: {sorted(unexpected)}"
            )
        connection.executescript(ddl)
        created = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if not CANONICAL_TABLES <= created or connection.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise CanonicalSchemaError("Installed schema failed the post-installation check.")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
