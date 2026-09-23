# FPLPatternRec

Windows-focused starter with a FastAPI health endpoint, React status page,
reusable Base UI Storybook, and Datasette over an empty SQLite database.

## Repository map

- [Backend](backend/README.md)
- [Frontend](frontend/README.md)
- [Python source and repository tools](src/README.md)
- [Tests](tests/README.md)
- [Documentation](docs/README.md)
- [Experiments](experiments/README.md)

Install Python dependencies into the root `.venv` with `uv` and JavaScript
dependencies with `npm ci`. Use [`dev.ps1`](dev.ps1) through the commands in
[`docs/DEVELOPMENT_SERVICES.md`](docs/DEVELOPMENT_SERVICES.md); check service
status first and reuse healthy services. The SQLite file lives only in a
dedicated Docker volume. Repository rules for contributors and agents are in
[`AGENTS.md`](AGENTS.md).
