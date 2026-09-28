# Data pipeline commands

Run the Typer CLI from the repository root:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve core
.venv/Scripts/python.exe -m tools.data_pipeline retrieve alternative-comps
.venv/Scripts/python.exe -m tools.data_pipeline retrieve all --core-raw-root data/raw --alternative-raw-root data/alternative_comps/raw
```

Use `retrieve official-fpl`, `retrieve fotmob-competitions`, and the other individual provider
commands to refresh one source. `retrieve core` supports `--raw-root`; `retrieve alternative-comps`
supports its own `--raw-root`. `retrieve all` accepts the separate `--core-raw-root` and
`--alternative-raw-root` overrides. The default roots remain `data/raw/` for core providers and
`data/alternative_comps/raw/` for alternative competitions. Provider-relative folder and file names
are unchanged.

Each successful refresh fetches even when its target already exists, then writes the complete
response to a temporary sibling and atomically replaces only that provider-relative target. A
request or write failure leaves the previous file unchanged and removes the temporary file. Raw
response bytes are kept as received. The retrieval path creates no run manifests or raw history;
existing payloads and historical `collection-*.json` records are left in place.

From PowerShell, `./data.ps1` forwards Typer arguments through the one-shot Compose service:

```powershell
./data.ps1 retrieve core
./data.ps1 retrieve openfootball --raw-root data/alternative_comps/raw
```

The `data-tools` service uses the Python tooling image, binds this checkout at `/workspace` for
source and raw-file access, and mounts the existing `fplpatternrec-sqlite` volume at `/data`. It is
profiled as one-shot, run with `--no-deps`, and is not part of `dev.ps1` lifecycle actions. The
retrieval commands in this stage read/write only the checkout's raw files; they do not access or
write the database volume. No live requests are needed for the mocked retrieval tests.

The individual core provider names are `official-fpl`, `fpl-archive`, `premier-league`, `fotmob`,
`understat`, `football-data`, `clubelo`, and `sofascore`. The alternative names are
`fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and `transfermarkt-injuries`.
Successful refreshes replace the matching response file; a failed request or write preserves its
last good contents.

The only ingestion command currently available is:

```powershell
./data.ps1 ingest official-fpl-teams [--raw-root PATH] [--season YYYY-YY]
```

This syntax is not permission to write the shared volume. Wait for its separate authorization before running the
loader; when authorized, begin the volume workflow with the read-only `dev.ps1 status` check.

It reads `official_fpl_api/bootstrap-static.json` from the core raw root, which defaults to
`data/raw/`, then creates/uses only `stg_official_fpl_teams` and writes the selected season's rows to
`/data/fplpatternrec.db`. It does not retrieve data. `--season` is optional; by default the loader
derives the season from the first gameweek deadline. This loader has passed temporary SQLite fixture
tests, but the shared-volume state and workflow have not been proven. Ingestion changes the named
volume, so do not treat the local tests as shared-volume authorization or proof. The full inventory
and current evidence are in [`docs/DATA_PIPELINE.md`](../../../docs/DATA_PIPELINE.md).
