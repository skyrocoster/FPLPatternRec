# Provider retrieval

- `common.py` — shared HTTP transport, throttling, atomic response replacement,
  and season/path-label helpers.
- `provider_config.py` — API endpoints and ordered statistic selections for the
  core providers; the FotMob endpoint is shared with alternative competitions.
- Provider-named modules — request sequences and provider-relative output paths.
- `alternative_competitions/` — separate competition catalogues and collectors.

Collectors receive a `RawCollector` rather than choosing a raw root themselves.
The CLI selects the core or alternative root and preserves provider subfolders.
Keep provider payloads unchanged; identity resolution belongs to ingestion.

See the [pipeline command guide](../README.md) and
[storage conventions](../../../../docs/DATA_STORAGE.md). Retrieval never writes
SQLite; ingestion never implicitly refreshes these sources.
