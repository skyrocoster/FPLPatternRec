# Retrieval rewrite and first FPL teams ingestion - refresh all supported sources and prove one SQLite staging table

> **Status:** done - all three stages accepted; the user separately authorized shared-volume proof and the ingestion-only root override.

- **Read trigger:** Before changing data retrieval, raw storage, the data CLI/PowerShell entry point, SQLite volume access, setup behavior, or ingestion.
- **Upstream:** [`docs/grilling-docs/retrieval-and-first-ingestion-slice.md`](../../../grilling-docs/retrieval-and-first-ingestion-slice.md) is the agreed direction. [`docs/throwaway/raw-data-staging-schemas.md`](../../../throwaway/raw-data-staging-schemas.md) is a proposal only, not existing DDL or authority to build all proposed tables. [`docs/grilling-docs/base-tables-schema.md`](../../../grilling-docs/base-tables-schema.md) is a separate future canonical proposal and is not part of this Plan.

## Outcome

The repository has one hobby-scale, Typer-based data-tooling package and a PowerShell entry point that can refresh every currently supported raw retrieval source and load only official FPL teams into the existing volume-only SQLite database. Successful responses replace their corresponding raw file; a failed request preserves the last good file. Re-running the teams load for the same season does not duplicate teams.

## Scope

- **Included:** A better-organized Python command package; commands for every currently supported core and alternative retrieval provider; safe in-place refresh; a one-shot Compose path that can reach both the repository's raw files and the named SQLite volume; setup behavior that safely accepts a populated valid database; and a season-scoped `stg_official_fpl_teams` loader and durable table checklist.
- **Expected areas:** `src/data_retrieval/**`, `src/tools/`, `tests/test_alternative_sources.py`, focused `tests/test_data_pipeline_*.py`, `pyproject.toml`, `uv.lock`, `requirements.txt`, `compose.yaml`, `dev.ps1`, new root `data.ps1`, `data/raw/README.md`, `src/tools/README.md`, new `src/tools/data_pipeline/README.md`, `docs/DATA_PIPELINE.md`, `docs/README.md`, and `docs/DEVELOPMENT_SERVICES.md`.
- **Excluded:** Any live retrieval as an automated proof step; moving or bulk-rewriting existing raw payloads (a successful explicit refresh may replace only its matching file); dated capture directories, new response manifests, or raw-response history; staging providers other than official FPL teams; the proposed canonical base tables; backend/API, frontend, or application integration; host `data/database/`; persistent service startup/restart; and commits or pushes.

### Code layout and command contract

Place new Python repository tooling under `src/tools/`, consistent with `src/README.md`:

```text
src/tools/
  __init__.py
  data_pipeline/
    __init__.py
    __main__.py
    cli.py
    retrieval/
      common.py
      official_fpl.py
      fpl_archive.py
      premier_league.py
      fotmob.py
      understat.py
      football_data.py
      clubelo.py
      sofascore.py
      alternative_competitions/
        fotmob.py
        openfootball.py
        wikipedia.py
        transfermarkt.py
    ingestion/
      sqlite.py
      official_fpl_teams.py
    README.md
data.ps1
```

The Typer entry point is `python -m tools.data_pipeline`. Expose `retrieve core`, `retrieve alternative-comps`, `retrieve all`, and individual provider commands for all of these existing collectors:

- Core: `official-fpl`, `fpl-archive`, `premier-league`, `fotmob`, `understat`, `football-data`, `clubelo`, and `sofascore`.
- Alternative group: `fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and `transfermarkt-injuries`.

`retrieve core` preserves the existing default group; `retrieve all` explicitly includes both groups. Keep current optional collection controls where useful, but default official FPL retrieval must request bootstrap, fixtures, current live snapshots, and player summaries. Do not add a bootstrap-only or teams-only retrieval route. The only ingestion command in this Plan is `ingest official-fpl-teams [--raw-root PATH] [--season YYYY-YY]`, with the core raw root as its default; this lets a deliberately overridden retrieval root be loaded without manually moving files.

`data.ps1` forwards Typer arguments to an ephemeral `data-tools` Compose service. That one-shot service uses the Python tooling environment, binds the checkout for source/raw access, and mounts the existing `fplpatternrec-sqlite` volume at `/data`. It is not a persistent service and must not be added to the four-service `dev.ps1` lifecycle targets. Do not start the persistent services for retrieval or ingestion.

### Raw storage contract

Keep the actual existing raw topology and defaults; root unification is not needed for this outcome and silently relocating captures would risk refreshes going to a different file than the one previously saved. No raw payload moves are part of the rewrite.

| Retrieval group | Default raw root | Provider files remain under |
|---|---|---|
| Core | `data/raw/` | `data/raw/<provider>/...` |
| Alternative competitions | `data/alternative_comps/raw/` | `data/alternative_comps/raw/<provider>/...` |

Single-group/provider commands accept `--raw-root` to override their default. `retrieve all` accepts distinct core and alternative-root overrides so neither existing default is silently changed. If a later requirement makes one unified raw root necessary, stop and ask the user before planning a file migration; do not quietly choose a new root.

Refresh the same provider-relative path. Fetch even when the target exists; write the complete response to a temporary sibling and atomically replace the target only after the request and write succeed. On request or write failure, retain the previous file byte-for-byte and clean up the temporary file. Preserve response bodies as received. Do not create new `collection-*.json` manifests or payload history; leave all existing payloads and old retrieval-record files in place. Update the raw README so it no longer promises that files are never overwritten.

### Database and checklist contract

The only database is `/data/fplpatternrec.db` in the `fplpatternrec-sqlite` named volume. By default the loader reads the complete existing `data/raw/official_fpl_api/bootstrap-static.json`; an explicit raw-root override selects the same provider-relative file beneath that root. It must not trigger retrieval or discard fixtures, live, or player raw data. Derive the season from the first gameweek deadline, allowing an explicit `--season` override for separately supplied files. Validate the full teams array before changing the database, then replace only that season's team rows in one transaction. Use the season/team composite primary key and the `softe_` prefix for every column. The only user-created staging table is `stg_official_fpl_teams`, with the proposed ID, code, Pulse ID, position, played/win/draw/loss/points, strength, name, short name, nullable link URL, and unavailable fields. Normalize empty `link_url` to SQL `NULL`; do not create other tables, migration/control tables, or canonical data.

Update `dev.ps1 setup` so an existing database with `PRAGMA quick_check` equal to `ok` is left unchanged regardless of table count. Keep create-if-absent behavior; do not reset, migrate, delete, or reject a valid populated database merely because it now contains tables. Any setup or ingestion operation that writes the shared volume remains gated on separate explicit user authorization.

`docs/DATA_PIPELINE.md` will contain an itemized checklist. Statuses must describe reality: the one selected table is “planned in this Plan; not yet created/proven” until its proof passes; other proposals remain “future; not created/proven”; only proven work may be marked “created and proven.” The schema proposal names these 53 staging tables:

- **Football-Data:** `stg_football_data_all`.
- **Vaastav:** `stg_vaastav_players`, `stg_vaastav_teams`, `stg_vaastav_fixtures`, `stg_vaastav_player_gameweeks`.
- **Understat:** `stg_understat_league_teams`, `stg_understat_team_match_history`, `stg_understat_league_players`, `stg_understat_league_matches`, `stg_understat_match_shots`, `stg_understat_match_rosters`.
- **Official FPL:** `stg_official_fpl_teams`, `stg_official_fpl_element_types`, `stg_official_fpl_phases`, `stg_official_fpl_chips`, `stg_official_fpl_element_stats`, `stg_official_fpl_elements`, `stg_official_fpl_events`, `stg_official_fpl_event_chip_plays`, `stg_official_fpl_fixtures`, `stg_official_fpl_fixture_stats`, `stg_official_fpl_element_history`, `stg_official_fpl_element_history_past`, `stg_official_fpl_element_upcoming_fixtures`, `stg_official_fpl_live_gameweek`, `stg_official_fpl_live_explain`, `stg_official_fpl_snapshot`.
- **Premier League API:** `stg_pl_seasons`, `stg_pl_clubs`, `stg_pl_teams`, `stg_pl_players`, `stg_pl_fixtures`, `stg_pl_fixture_teams`, `stg_pl_fixture_goals`, `stg_pl_stat_values`.
- **FotMob:** `stg_fotmob_leagues`, `stg_fotmob_league_group_membership`, `stg_fotmob_seasons`, `stg_fotmob_teams`, `stg_fotmob_season_standings`, `stg_fotmob_season_archive`, `stg_fotmob_fixtures`, `stg_fotmob_players`, `stg_fotmob_match_players`, `stg_fotmob_match_events`, `stg_fotmob_match_lineups`, `stg_fotmob_match_lineup_players`, `stg_fotmob_match_player_stats`, `stg_fotmob_match_team_stats`, `stg_fotmob_match_shots`, `stg_fotmob_match_momentum`, `stg_fotmob_stat_catalogue`, `stg_fotmob_stat_leaders`.

Mark only `stg_official_fpl_teams` as selected by this Plan; the other 52 staging proposals are future work. Separately list the eight future canonical proposals from `base-tables-schema.md`: `competitions`, `seasons`, `teams`, `players`, `fixtures`, `team_source_ids`, `player_source_ids`, and `fixture_source_ids`. Do not count them as staging tables or implement them here. ClubElo and SofaScore remain “no usable payload; no staging table proposed.” The alternative retrieval providers have no staging proposal in the referenced schema document; show them as “retrieval-only; staging shape not proposed,” not as invented tables or as completed ingestion.

## Stages

Stages are sequential. The coordinator must check this Plan after it is written and before implementation starts. That review is not implementation authorization. Separately obtain explicit user authorization before any operation that writes to the shared SQLite volume.

1. **done - Rewrite retrieval and provide commands.** Replaced `src/data_retrieval/**` with the organized package above; migrated all eight core and four alternative collectors without dropping existing provider coverage; added the Typer dependency to `pyproject.toml`, updated `uv.lock` and generated `requirements.txt`, and exposed the CLI through `data.ps1` and the one-shot Compose tooling service. Implemented refresh-in-place with last-good-file preservation. Updated focused retrieval tests and source/raw README instructions. **Proof:** mocked tests exercise provider dispatch (not just CLI help), PowerShell command forwarding, default full official FPL request coverage, optional existing collection controls, overwrite on a successful refresh, and exact preservation on request failure; no live network. **Escalate:** a provider contract or required source behavior changes beyond the already-supported collector behavior.
2. **done - Add the volume-only teams loader and setup accommodation.** Added one-shot volume access, changed `dev.ps1 setup` to leave valid populated databases unchanged, and implemented only the season-scoped `stg_official_fpl_teams` loader. Local temporary-database tests proved schema/key, season separation, empty-link normalization, rollback on invalid input, and idempotency; the separately authorized volume proof passed in Stage 3.
3. **done - Record the inventory and prove the authorized workflow.** Added the 53-table staging checklist and separate eight-table future canonical list to `docs/DATA_PIPELINE.md`, plus operator documentation. After separate authorization, verified the named-volume database's valid empty baseline, loaded the existing FPL bootstrap twice, and checked only the teams table, 20 stable season-scoped rows, no duplicate keys, and `quick_check=ok`. Post-load `dev.ps1 setup` left the database unchanged. No live retrieval ran.

## Progress and decisions

- **Stage 1:** done - focused retrieval, CLI, and alternative-provider tests: 19 passed; workdir `G:/FPLPatternRec`; `.venv/Scripts/python.exe -c 'import subprocess,sys; sys.exit(subprocess.run([".venv/Scripts/python.exe","-m","pytest","tests/test_data_pipeline_retrieval.py","tests/test_data_pipeline_cli.py","tests/test_alternative_sources.py","-q"], timeout=60).returncode)'` (Bash tool timeout 90,000 ms; command timeout 60 seconds). No live requests or Docker invocation. Old raw-root README edits appear ignored by Git; tracked documentation remains due in Stage 3.
- **Stage 2:** done - focused ingestion and CLI tests: 19 passed; workdir `G:/FPLPatternRec`; `.venv/Scripts/python.exe -c 'import subprocess,sys; sys.exit(subprocess.run([".venv/Scripts/python.exe","-m","pytest","tests/test_data_pipeline_ingestion.py","tests/test_data_pipeline_cli.py","-q"], timeout=60).returncode)' (Bash tool timeout 90,000 ms; command timeout 60 seconds). CLI tests re-proved the affected Stage 1 command wiring; unaffected retrieval/provider proof is retained. SQLite tests used only temporary fixture databases; shared-volume proof is still pending.
- **Stage 3:** done - the first load failed on root-owned SQLite permissions; an inspection confirmed the database was still valid and empty. The user approved running only ingestion with `--user 0:0` without changing volume ownership; retrieval stays non-root. Focused CLI forwarding tests passed (14 tests; `.venv/Scripts/python.exe -m pytest tests/test_data_pipeline_cli.py -q`, workdir `G:/FPLPatternRec`, 60-second command timeout and 90,000-ms Bash tool timeout). After `dev.ps1 status`, two separate `powershell -ExecutionPolicy Bypass -File ./data.ps1 ingest official-fpl-teams` runs exited 0 (120-second command and 135,000-ms Bash tool timeout each). Read-only checks after each and after `powershell -ExecutionPolicy Bypass -File ./dev.ps1 setup` (120-second command and 135,000-ms Bash tool timeout) found only `stg_official_fpl_teams`, 20 rows for `2026-27`, the season/team composite key, no duplicates, `quick_check=ok`, and the unchanged ordered-row SHA-256 `b466f03c16b25b4e9bb79ec0fb353b295e0730c26317cd08c5145202a3d024e9`. Read-only Docker probes had 45-second command and 75,000-ms Bash tool timeouts. No live retrieval ran.
- **Decision - raw roots:** preserve `data/raw/` and `data/alternative_comps/raw/` as separate defaults. No root consolidation or file move is required for this outcome.
- **Decision - first table:** official FPL teams only; the 52 other staging proposals, eight canonical proposals, and retrieval-only provider shapes are explicitly deferred.
- **Decision - dependency:** Typer is a runtime dependency because the CLI must run in the tooling container as well as in the local project environment.
- **Decision - named-volume ownership:** User approved a per-invocation root override only for teams ingestion to match the setup-created database. Volume ownership and permissions were not changed.

Passing focused behavioral proof remains valid until a later change affects its command, inputs, behavior, configuration, dependencies, or environment. Do not run lint, formatting, broad build/type checks, source-size checks, or the full test suite as part of this Plan.

## Proof

The following focused test commands are proposed for implementation, not for Plan writing. Each Bash invocation must use the stated finite tool timeout, and each command uses a finite Python subprocess timeout:

1. Retrieval behavior, tool timeout **90,000 ms**, command timeout **60 seconds**:
   ```bash
   .venv/Scripts/python.exe -c 'import subprocess,sys; sys.exit(subprocess.run([".venv/Scripts/python.exe","-m","pytest","tests/test_data_pipeline_retrieval.py","tests/test_alternative_sources.py","-q"], timeout=60).returncode)'
   ```
2. Teams loader and CLI behavior, tool timeout **90,000 ms**, command timeout **60 seconds**:
   ```bash
   .venv/Scripts/python.exe -c 'import subprocess,sys; sys.exit(subprocess.run([".venv/Scripts/python.exe","-m","pytest","tests/test_data_pipeline_ingestion.py","tests/test_data_pipeline_cli.py","-q"], timeout=60).returncode)'
   ```

For the final named-volume smoke proof, keep each PowerShell operation finite: run `dev.ps1 status` first with a command timeout of **30,000 ms** and Bash tool timeout of **45,000 ms**; only after its successful result, run the needed `dev.ps1 setup`, two `data.ps1 ingest official-fpl-teams` invocations, and post-load setup verification with command timeouts of **120,000 ms** and Bash tool timeouts of **135,000 ms** each. Execute these commands separately and in that order, wrapping each in `subprocess.run(..., timeout=<stated seconds>)`. Do not run this proof until the shared-volume write gate is explicitly authorized. The one-shot tooling path must not start persistent services or create a host database.

## Escalation boundaries

- Stop if satisfying the outcome requires a new provider endpoint, a different raw location, moving existing raw files, or a new capture/history/manifest policy. Ask the user before unifying the two raw roots.
- Stop if the official FPL teams payload no longer fits the proposed schema or the season cannot be determined safely; do not add another table or silently discard populated fields.
- Stop if the named volume is corrupt, contains unexpected user data, or would need reset/migration. Never delete or overwrite an existing valid database to make the proof pass.
- Stop before any shared-volume write without separate explicit user authorization. Coordinator review of this Plan does not grant that authorization or authorize implementation.
- Keep ClubElo and SofaScore as no-payload retrieval attempts without staging tables; keep alternative retrievals without invented staging schemas.

## Visible result

> The operator can refresh all supported raw sources safely and repeat the official FPL teams load without losing a prior raw file on request failure or duplicating teams.
