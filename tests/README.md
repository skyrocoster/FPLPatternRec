# Tests

- `cleanliness/` — maintenance-runner and source-size checks
- `services/` — development-service checks
- `e2e/` — Playwright browser tests
- `graphify/` — catalogue generation
- `test_*ingestion.py`, `test_*schema*.py`, and `test_data_pipeline_cli.py` — data loaders, schemas, and command routing
- `test_*retrieval.py` and provider-specific tests — saved-response retrieval behavior

Backend health/API tests are colocated in [`backend/tests/`](../backend/tests/).
The full test process is documented in
[`docs/FULL_TEST_PROCESS.md`](../docs/FULL_TEST_PROCESS.md). Browser tests reuse
healthy Compose services; check `dev.ps1 status` first.
