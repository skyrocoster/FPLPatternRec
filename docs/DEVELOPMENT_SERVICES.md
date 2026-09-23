# Persistent development services

The backend, frontend, Storybook, and Datasette run as detached Docker Compose services. Manage all service
lifecycle actions through `dev.ps1`; do not launch competing host servers or use raw Compose lifecycle commands.

## Commands

Run these from the repository root in PowerShell. Before any lifecycle action, first run `status`; the initial
missing-service report is expected. Reuse healthy services rather than restarting them.

```powershell
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
powershell -ExecutionPolicy Bypass -File ./dev.ps1 setup
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
powershell -ExecutionPolicy Bypass -File ./dev.ps1 start
powershell -ExecutionPolicy Bypass -File ./dev.ps1 status
```

`setup` creates `/data/fplpatternrec.db` only when the file is absent and refuses to overwrite it. It is an empty,
valid SQLite database with no tables. `start` does not seed, import, update, or otherwise populate the database.
The SQLite file exists only in the `fplpatternrec-sqlite` Docker volume; do not create or mount a host `data/` folder.

Supported actions are `setup`, `start`, `stop`, `restart`, `rebuild`, `status`, and `logs`. Each action may target
`all`, `backend`, `frontend`, `storybook`, or `datasette`, for example:

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

All ports bind only to `127.0.0.1`. They were checked for availability before
startup; if selecting a different port set is necessary, update Compose,
application configuration, and this document together. Keep these services
isolated from other local projects.

Compose creates three distinct target volumes: `fplpatternrec-sqlite` for the empty database,
`fplpatternrec-frontend-node-modules` for the frontend install, and
`fplpatternrec-storybook-node-modules` for Storybook. Datasette alone mounts the SQLite volume, at `/data`.

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
- Never write data into the SQLite volume; this starter intentionally keeps the database empty.
- Use only the ports listed above for these services.
