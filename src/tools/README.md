# Repository tools

- `full_test_process.py` — see [`docs/FULL_TEST_PROCESS.md`](../../docs/FULL_TEST_PROCESS.md)
- `graphify_catalogue.py` — see [`docs/graphify/README.md`](../../docs/graphify/README.md)
- [`data_pipeline/`](data_pipeline/README.md) — provider retrieval and validated SQLite ingestion.

Run these tools from the repository root with `.venv/Scripts/python.exe`.

Run a retrieval group with `.venv/Scripts/python.exe -m tools.data_pipeline retrieve core`,
`retrieve alternative-comps`, or `retrieve all`. Individual provider commands are also available.
The core and alternative groups keep their separate `data/raw/` and
`data/alternative_comps/raw/` defaults. Successful refreshes replace only the matching
provider-relative response file; failed requests or writes keep the previous file unchanged. See
[`data_pipeline/README.md`](data_pipeline/README.md) for PowerShell and one-shot Compose usage.

Ingestion runs through `./data.ps1 ingest <command>` and requires separate authorization
before writing the shared SQLite volume. See
[`docs/DATA_PIPELINE.md`](../../docs/DATA_PIPELINE.md) for the provider inventory,
command guidance, and recorded load evidence, rather than duplicating changing counts here.
Reviewed reference inputs live in [`data_pipeline/reference/`](data_pipeline/reference/README.md);
[`docs/DATA_STORAGE.md`](../../docs/DATA_STORAGE.md) explains the storage boundaries.
