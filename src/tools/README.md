# Repository tools

- `full_test_process.py` — see [`docs/FULL_TEST_PROCESS.md`](../../docs/FULL_TEST_PROCESS.md)
- `graphify_catalogue.py` — see [`docs/graphify/README.md`](../../docs/graphify/README.md)
- `data_pipeline/` — safe-refresh commands for all twelve core and alternative raw-data providers.

Run these tools from the repository root with `.venv/Scripts/python.exe`.

Run a retrieval group with `.venv/Scripts/python.exe -m tools.data_pipeline retrieve core`,
`retrieve alternative-comps`, or `retrieve all`. Individual provider commands are also available.
The core and alternative groups keep their separate `data/raw/` and
`data/alternative_comps/raw/` defaults. Successful refreshes replace only the matching
provider-relative response file; failed requests or writes keep the previous file unchanged. See
[`data_pipeline/README.md`](data_pipeline/README.md) for PowerShell and one-shot Compose usage.

The only current ingestion command is `./data.ps1 ingest official-fpl-teams`. Its local tests use
temporary SQLite databases; shared-volume status and proof remain pending. See
[`docs/DATA_PIPELINE.md`](../../docs/DATA_PIPELINE.md) for the full provider inventory, operator
guidance, and evidence status.
