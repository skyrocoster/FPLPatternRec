# Graphify catalogue

Generated code maps for repository orientation and dependency tracing. The
catalogue is advisory; source code, `AGENTS.md`, and active Plans are
authoritative. Graphify uses local deterministic AST extraction only and does
not process Markdown or YAML.

- [Repository](repository/GRAPH_REPORT.md)
- [Backend](backend/GRAPH_REPORT.md)
- [Frontend](frontend/GRAPH_REPORT.md)
- [Source tools](source-tools/GRAPH_REPORT.md)
- [Tests](tests/GRAPH_REPORT.md)
- [Agent workflow](agent-workflow/GRAPH_REPORT.md)

Regenerate all six bundles from the repository root with
`.venv/Scripts/python.exe src/tools/graphify_catalogue.py`. Each bundle
contains five generated artifacts and is ignored by Git; only this index is
tracked. The source-tools layer covers `src/tools/` only. No runtime database
or host data directory is used.
