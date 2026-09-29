# Player/fixture observations: handoff

**Status (29 September 2026):** Implementation is in the worktree, but the all-season
ingestion has **not** been proved end to end or run against the shared database.
The user wants **all saved seasons, 2016-17 through 2026-27**, not a 2025-26-only
solution. This is a checkpoint, not a claim that the work is finished.

## Where to pick up

- `src/tools/data_pipeline/ingestion/player_fixture_observations.py` is the new
  loader. It proposes one row per canonical fixture/player listing with club,
  gameweek, FPL element ID, and minutes. Positive minutes mean an appearance;
  zero means listed without playing. It also creates
  `player_fixture_observation_fixtures` to mark processed fixtures, including
  those that might have zero player rows. Existing rows must agree on repeat;
  current-season finished fixtures are intended to append without changing old
  rows.
- `src/tools/data_pipeline/cli.py` exposes
  `ingest player-fixture-observations --season YYYY-YY [--raw-root PATH]`;
  `src/tools/data_pipeline/compose_runner.py` allows the command to write the
  root-owned database. Archives use saved Vaastav files; 2026-27 uses saved
  official FPL fixtures and element-summary histories, **not** the stale
  current-season Vaastav archive.
- Focused tests are in `tests/test_canonical_fixtures_ingestion.py` (all ten
  archived seasons, 2025-26 Saliba example, repeat/conflict cases) and
  `tests/test_official_current_season_ingestion.py` (current-season append and
  changed-old-row rejection). Review these and the loader together.
- In 2019-20, the 59 scoreless original GW 29 observations for postponed FPL
  fixture 275 must remain only in the existing gameweek aggregates; do **not**
  misattribute them to the completed GW 39 match. The loader guards and excludes
  those 59 match-level rows. The reviewed 2021-22 fixture 263 kickoff discrepancy
  is handled by the existing fixture validation routines.

## Verified versus outstanding

- A focused **2025-26-only** test selection passed (10 tests) before the loader
  was extended to all seasons. After the extension, two isolated tests passed:
  the full 2025-26 observation/repeat test and the official 2026-27 append/repeat
  test (`2 passed, 46 deselected`). **The complete all-season test selection was
  interrupted by the user, so do not describe it as passing.** No further tests
  were requested at this checkpoint.
- A direct read-only SQLite check found **neither new table in the named Docker
  volume**. No match observations have been ingested into that database by this
  work. Existing fixtures and grouped player/gameweek/team data are unchanged.
- The worktree has extensive pre-existing unrelated changes, including a move
  of reviewed references into `src/tools/data_pipeline/reference/`. Preserve
  those changes; do not reset files or assume Git HEAD describes the running
  pipeline. There is no active implementation Plan under `docs/plans/active/`.

## Remaining steps (when ready)

1. Review the all-season loader and tests, especially cross-season isolation,
   the 2019-20 exclusion, fixture completion markers, and append-only 2026-27
   behavior. Run only focused tests with explicit finite command **and** tool
   timeouts; the user asked not to run more tests during this handoff.
2. Before any shared-volume write, run
   `powershell -ExecutionPolicy Bypass -File ./dev.ps1 status`. After review and
   authorization, ingest each saved season with
   `./data.ps1 ingest player-fixture-observations --season YYYY-YY` (2016-17
   through 2026-27). Do not run retrieval or create a host database directory.
3. Verify the named volume with **read-only SQLite** via the `data-inspector`
   service: rows and processed fixtures per season, zero-minute versus positive-
   minute counts, Saliba's 2025-26 GW 26 fixture 252 = 0 and fixture 310 = 90,
   no match-level GW 29 listing for 2019-20 fixture 275, repeat stability,
   `PRAGMA quick_check`, and `PRAGMA foreign_key_check`. Document actual counts
   and the precise source exception in `docs/DATA_PIPELINE.md` only after proof.

See `AGENTS.md` for service, database-access, and timeout rules. Existing
`docs/DATA_PIPELINE.md` lines 396-554 explain the earlier week/fixture evidence.
