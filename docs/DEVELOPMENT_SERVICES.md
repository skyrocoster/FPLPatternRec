# Persistent development services

The backend, frontend, Storybook, Datasette, and read-only database inspector run as detached Docker Compose
services. Manage all service lifecycle actions through `dev.ps1`; do not launch competing host servers or use raw
Compose lifecycle commands.

## Commands

Run these from the repository root in PowerShell. Before any lifecycle action, first run `status`; the initial
missing-service report is expected. Reuse healthy services rather than restarting them.
The `setup` command can create the SQLite file in the shared volume; run it only when needed and with the required
authorization. If a database already exists and passes `quick_check`, setup leaves it unchanged.

```powershell
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
powershell -ExecutionPolicy Bypass -File ./dev.ps1 setup
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
powershell -ExecutionPolicy Bypass -File ./dev.ps1 start
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
```

`setup` creates `/data/fplpatternrec.db` only when the file is absent. For an existing database it requires
`PRAGMA quick_check` to return `ok`, then leaves the file unchanged regardless of its table count. Setup does not
reset, migrate, or delete database contents. A newly created database is empty; `start` does not seed, import,
update, or otherwise populate it. The SQLite file exists only in the `fplpatternrec-sqlite` Docker volume; do not
create or mount a host `data/` or `data/database/` folder for SQLite.

Supported actions are `setup`, `start`, `stop`, `restart`, `rebuild`, `status`, and `logs`. Each action may target
`all`, `backend`, `frontend`, `storybook`, `datasette`, or `data-inspector`, for example:

```powershell
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status frontend
powershell -ExecutionPolicy Bypass -File ./dev.ps1 logs datasette
```

`status` is read-only and reports missing services as not created yet. The script
selects this checkout's `compose.yaml`, whose project is explicitly named
`fplpatternrec`. Services and volumes are isolated to this project.

## Addresses and storage

| Service | Local address | Container port |
| --- | --- | ---: |
| Backend | <http://localhost:5677> | 5677 |
| Frontend | <http://localhost:8455> | 8455 |
| Storybook | <http://localhost:6017> | 6017 |
| Datasette | <http://localhost:8677> | 8677 |
| Data inspector | None (use `docker compose exec -T`) | None |

All ports bind only to `127.0.0.1`. They were checked for availability before
startup; if selecting a different port set is necessary, update Compose,
application configuration, and this document together. Keep these services
isolated from other local projects.

Compose creates three distinct target volumes: `fplpatternrec-sqlite` for the SQLite database,
`fplpatternrec-frontend-node-modules` for the frontend install, and
`fplpatternrec-storybook-node-modules` for Storybook. Datasette mounts the SQLite volume at `/data`; the inspector
mounts the same volume read-only, without a host database directory or an exposed port.

## Inspecting SQLite

Check status before starting the inspector (a healthy one is left running). From the repository root in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
powershell -ExecutionPolicy Bypass -File ./dev.ps1 start data-inspector
@'
import sqlite3

db = sqlite3.connect("file:/data/fplpatternrec.db?mode=ro", uri=True)
db.execute("PRAGMA query_only = ON")
print(db.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall())
db.close()
'@ | docker compose -f compose.yaml exec -T data-inspector python -
```

Replace the `SELECT` with the read-only question you need answered. The inspector uses a read-only volume mount,
and `mode=ro` fails if the database file is missing. Do not use Datasette (UI or HTTP API) or Playwright for database
exploration. Keep command and tool timeouts finite. `data-tools` remains the separate, one-shot writable pipeline
service; inspection does not run ingestion or refresh data.

## Day-to-day behavior

- Backend changes reload through Uvicorn; frontend and Storybook changes use their normal hot reload.
- `start` leaves a healthy stack alone; it never performs a data refresh.
- `rebuild` is for Dockerfile, Compose, or dependency/lockfile changes. Ordinary source edits need no rebuild.
- Docker Desktop must be running. If a service is unhealthy, inspect `dev.ps1 logs <service>` before deciding
  whether a targeted restart is necessary.
- Do not stop services as task cleanup. Never use `docker compose down` or delete target volumes without explicit
  authorization.

## Agent rules

- Before every lifecycle action or browser/E2E check, run `dev.ps1 status` and reuse healthy services.
- Use only `dev.ps1` for service lifecycle actions. Never start Uvicorn, Vite, or Storybook directly on the host.
- `data-tools` is a separate one-shot Compose service, not a persistent lifecycle target. Use `data.ps1` for its
  supported data-pipeline commands; it runs with `--no-deps` and does not start the five development services.
- `data.ps1 retrieve ...` refreshes raw files in the checkout and does not import them into SQLite.
  `data.ps1 ingest official-fpl-teams` creates/uses only `stg_official_fpl_teams` and writes the selected season to
  `/data/fplpatternrec.db` in the named volume.
  The eight canonical base tables and 51 reviewed clubs are also in that volume. The separate
  `data.ps1 ingest canonical-teams` loader reads the reviewed club JSON and can optionally map one
  staged FPL season with `--season`. See [`DATA_PIPELINE.md`](DATA_PIPELINE.md) for commands,
  inventory, authorization boundaries, and verified state.
  `data.ps1 ingest canonical-players --season 2026-27` reads the saved official FPL bootstrap and
  has populated 667 canonical players and their season-scoped FPL ID/code mappings in this volume.
  `data.ps1 ingest canonical-archive-players --season 2025-26` reads the saved Vaastav FPL archive:
  480 players share existing canonical IDs, 361 are new identities. Neither command treats a
  player's latest team as a transfer history. The archive command also supports the saved
  seasons 2024-25 back through 2016-17 in reverse order, and those seasons have been loaded.
  The volume now has 2,757 canonical football players; 20 assistant-manager entries were excluded.
  The separately authorized `data.ps1 ingest player-gameweek-teams --season YYYY-YY` command
  has added 11 seasons (2016-17 through 2026-27), 380 FPL gameweeks, and 245,035 canonical
  player/team/week associations. It does not infer employment stints or fill gaps in the saved
  gameweek data; see `DATA_PIPELINE.md` for the season coverage and limitations.
  `data.ps1 ingest canonical-fixtures --season YYYY-YY` has loaded 3,810 finished matches,
  their scoped FPL IDs, and validated fixture-to-FPL-gameweek links: 380 in each saved season
  from 2016-17 through 2025-26 and 10 from 2026-27 GW 1. The other 370 scheduled 2026-27
  fixtures and individual player-to-match appearances are not loaded. See `DATA_PIPELINE.md`
  for postponed-fixture and kickoff-time caveats.
- Use only the named SQLite volume for database storage; do not create a host database directory. Run volume-writing
  setup or ingestion only with the required authorization, and never reset or delete a populated volume to make a
  proof pass.
- Use only the ports listed above for these services.
