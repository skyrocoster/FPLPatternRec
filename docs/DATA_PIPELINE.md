# Data pipeline: retrieval, staging, and proof status

The data pipeline refreshes supported provider files in the repository and has one SQLite loader:
official FPL teams, tested locally and proven against the named volume as documented below. The
proposed table inventory is not a claim that all staging schemas exist. The proposals are sourced from
[`throwaway/raw-data-staging-schemas.md`](throwaway/raw-data-staging-schemas.md); canonical tables
are a separate future proposal.

## Retrieval commands

Run from the repository root. The Typer entry point is
`.venv/Scripts/python.exe -m tools.data_pipeline`:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve core
.venv/Scripts/python.exe -m tools.data_pipeline retrieve alternative-comps
.venv/Scripts/python.exe -m tools.data_pipeline retrieve all
```

The supported individual core commands are `official-fpl`, `fpl-archive`, `premier-league`,
`fotmob`, `understat`, `football-data`, `clubelo`, and `sofascore`. The alternative-competition
commands are `fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and
`transfermarkt-injuries`. Use the `retrieve` group before an individual command, for example:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve official-fpl
.venv/Scripts/python.exe -m tools.data_pipeline retrieve openfootball --raw-root data/alternative_comps/raw
```

Core and alternative-competition files deliberately keep separate roots and provider-relative
paths:

| Retrieval group | Default raw root | Provider files |
|---|---|---|
| Core | `data/raw/` | `data/raw/<provider>/...` |
| Alternative competitions | `data/alternative_comps/raw/` | `data/alternative_comps/raw/<provider>/...` |

Single-group and individual-provider commands accept `--raw-root`. `retrieve all` accepts separate
`--core-raw-root` and `--alternative-raw-root` options; it does not merge the roots. Official FPL
retrieval continues to request the bootstrap, fixtures, current live snapshots, and player
summaries by default. The teams loader does not trigger retrieval or discard other saved FPL files.

Every refresh fetches a new response even if its destination exists. On success, the complete
response replaces only that provider-relative file using a temporary sibling and atomic replace.
If the request or file write fails, the previous file stays byte-for-byte intact and the temporary
file is cleaned up. Payload bytes are preserved; this workflow adds no new capture history or
retrieval manifests.

## Ingestion command and shared-volume boundary

The only loader in this slice is:

```powershell
./data.ps1 ingest official-fpl-teams
./data.ps1 ingest official-fpl-teams --raw-root data/raw --season 2026-27
```

These examples document command syntax; they are not authorization to write the shared volume.
Ingestion changes the named SQLite volume. Wait for separate authorization before running it. When
the authorized volume workflow is performed, begin with the read-only `dev.ps1 status` check.

Without `--raw-root`, it reads `data/raw/official_fpl_api/bootstrap-static.json`. An override reads
`official_fpl_api/bootstrap-static.json` below that root. Unless `--season YYYY-YY` is supplied,
the loader derives the season from the first gameweek deadline. It validates the complete teams
array before changing the database and replaces only the chosen season's team rows. Empty
`link_url` values become SQL `NULL`; reloading the same season replaces its rows rather than
duplicating them.

`data.ps1` forwards its arguments to the `data-tools` one-shot Compose service. The service binds
the checkout at `/workspace` for code and raw-file access and mounts the existing
`fplpatternrec-sqlite` named volume at `/data`; the database path inside the container is
`/data/fplpatternrec.db`. It runs with `--no-deps` and is not one of the four persistent services
managed by `dev.ps1`. Retrieval uses the checkout's raw files and does not read or write SQLite;
the `ingest` command writes the teams table in the named volume.

The authorized shared-volume proof ran `ingest official-fpl-teams` as root using a per-command
`--user 0:0` override because the existing database is root-owned and the image's default `app`
user cannot write it. This override applies only to that ingestion command; retrieval keeps the
image's default non-root user. No database ownership or permissions were changed.

Do not create or mount a host `data/` or `data/database/` directory for SQLite. `dev.ps1 setup`
creates the database only when absent. For an existing file it requires `PRAGMA quick_check` to
return `ok`, then leaves it unchanged regardless of table count; setup does not reset, migrate, or
delete tables. A missing or corrupt database needs operator attention rather than a host-side
workaround.

The loader is implemented and tested with temporary fixture databases. Its authorized named-volume
proof used the existing raw bootstrap, loaded the teams twice, and verified the same 20 rows for
2026-27 after both runs. A subsequent `dev.ps1 setup` reported that the valid table-bearing database
was left unchanged; a final read-only check confirmed its schema, rows, and integrity. No live
retrieval or raw-file changes were part of the proof. Any future operation that creates or writes
the shared database still requires separate authorization and must begin with the read-only
`dev.ps1 status` check.

## Staging-table inventory

The schema proposal names 53 staging tables. Only `stg_official_fpl_teams` has a loader in this
slice. It is implemented, locally tested, and **created and proven in the named volume** for season
2026-27. The other 52 tables are future proposals, not implemented or proven by this pipeline.

| Provider | Proposed staging table | Current status |
|---|---|---|
| Football-Data | `stg_football_data_all` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_players` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_teams` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_fixtures` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_player_gameweeks` | Future; not implemented or proven. |
| Understat | `stg_understat_league_teams` | Future; not implemented or proven. |
| Understat | `stg_understat_team_match_history` | Future; not implemented or proven. |
| Understat | `stg_understat_league_players` | Future; not implemented or proven. |
| Understat | `stg_understat_league_matches` | Future; not implemented or proven. |
| Understat | `stg_understat_match_shots` | Future; not implemented or proven. |
| Understat | `stg_understat_match_rosters` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_teams` | Created and proven in the named volume for 2026-27 (20 teams; repeat load stable; setup preserved the table). |
| Official FPL | `stg_official_fpl_element_types` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_phases` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_chips` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_stats` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_elements` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_events` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_event_chip_plays` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_fixtures` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_fixture_stats` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_history` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_history_past` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_upcoming_fixtures` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_live_gameweek` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_live_explain` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_snapshot` | Future; not implemented or proven. |
| Premier League API | `stg_pl_seasons` | Future; not implemented or proven. |
| Premier League API | `stg_pl_clubs` | Future; not implemented or proven. |
| Premier League API | `stg_pl_teams` | Future; not implemented or proven. |
| Premier League API | `stg_pl_players` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixtures` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixture_teams` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixture_goals` | Future; not implemented or proven. |
| Premier League API | `stg_pl_stat_values` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_leagues` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_league_group_membership` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_seasons` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_teams` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_season_standings` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_season_archive` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_fixtures` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_events` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_lineups` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_lineup_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_player_stats` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_team_stats` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_shots` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_momentum` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_stat_catalogue` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_stat_leaders` | Future; not implemented or proven. |

The 53 rows comprise one locally implemented and temporary-database-verified table plus 52 future
proposals. The proposal's empty-field, provider-local key, and type details are not additional DDL
or implementation approval.

### Separate future canonical tables

The independent [canonical base-table proposal](grilling-docs/base-tables-schema.md) lists eight
future tables. They are not staging tables and are not implemented or proven by this pipeline:

`competitions`, `seasons`, `teams`, `players`, `fixtures`, `team_source_ids`, `player_source_ids`,
and `fixture_source_ids`.

### Retrieval providers without staging tables

| Retrieval providers | Current status |
|---|---|
| ClubElo and SofaScore | No usable payload in the proposal review; no staging table proposed. |
| `fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and `transfermarkt-injuries` | Retrieval-only; staging shape not proposed. Do not infer or invent staging tables for these commands. |

The `stg_fotmob_*` proposals above refer to the core FotMob provider schema; they do not define a
staging shape for the separate alternative-competition FotMob command.

## Proof status

The focused retrieval and provider tests (19 passed), local teams-loader/CLI tests (19 passed), and
updated CLI command-forwarding tests (14 passed) are retained proof. Local loader tests use
temporary SQLite fixtures. The authorized named-volume proof loaded the existing bootstrap twice;
read-only checks confirmed only `stg_official_fpl_teams`, the `(softe_season, softe_team_id)` primary
key, 20 rows for `2026-27`, no duplicate keys, and `quick_check=ok`. The ordered-row SHA-256 was
identical after both loads and after `dev.ps1 setup`, which left the existing valid database
unchanged. No live retrieval was run.
