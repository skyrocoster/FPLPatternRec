-- Canonical identity foundation from docs/grilling-docs/base-tables-schema.md.
-- Apply only to an explicitly authorized SQLite database; this file does not seed
-- entities, resolve source identities, or migrate existing canonical tables.
-- Foreign keys must also be enabled on every connection that writes these tables.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS competitions (
    competition_id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS seasons (
    season_id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL REFERENCES competitions(competition_id),
    label TEXT NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    UNIQUE (competition_id, label),
    CHECK (start_year BETWEEN 1 AND 9999),
    CHECK (end_year BETWEEN start_year AND 9999),
    CHECK (label = printf('%04d-%02d', start_year, end_year % 100))
) STRICT;

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL
) STRICT;

CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name TEXT NOT NULL,
    date_of_birth TEXT,
    CHECK (date_of_birth IS NULL OR
           (date_of_birth GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(date_of_birth) IS NOT NULL))
) STRICT;

CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL REFERENCES seasons(season_id),
    home_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    away_team_id INTEGER NOT NULL REFERENCES teams(team_id),
    match_date TEXT,
    kickoff_at TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    home_goals INTEGER,
    away_goals INTEGER,
    CHECK (home_team_id <> away_team_id),
    CHECK (match_date IS NULL OR
           (match_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
            AND date(match_date) IS NOT NULL)),
    CHECK (kickoff_at IS NULL OR
           (kickoff_at GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z'
            AND datetime(kickoff_at) IS NOT NULL)),
    CHECK (status IN ('unknown', 'scheduled', 'in_progress', 'finished',
                      'postponed', 'cancelled', 'abandoned')),
    CHECK ((home_goals IS NULL) = (away_goals IS NULL)),
    CHECK (home_goals IS NULL OR (home_goals >= 0 AND away_goals >= 0)),
    CHECK (home_goals IS NULL OR status = 'finished')
) STRICT;

CREATE TABLE IF NOT EXISTS team_source_ids (
    source_namespace TEXT NOT NULL,
    source_scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    team_id INTEGER NOT NULL REFERENCES teams(team_id),
    PRIMARY KEY (source_namespace, source_scope, source_id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_team_source_ids_team_id ON team_source_ids(team_id);

CREATE TABLE IF NOT EXISTS player_source_ids (
    source_namespace TEXT NOT NULL,
    source_scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    PRIMARY KEY (source_namespace, source_scope, source_id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_player_source_ids_player_id ON player_source_ids(player_id);

CREATE TABLE IF NOT EXISTS fixture_source_ids (
    source_namespace TEXT NOT NULL,
    source_scope TEXT NOT NULL,
    source_id TEXT NOT NULL,
    fixture_id INTEGER NOT NULL REFERENCES fixtures(fixture_id),
    PRIMARY KEY (source_namespace, source_scope, source_id)
) STRICT;
CREATE INDEX IF NOT EXISTS idx_fixture_source_ids_fixture_id ON fixture_source_ids(fixture_id);
COMMIT;
