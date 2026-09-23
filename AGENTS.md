# AI Instructions: FPLPatternRec

Windows-only FastAPI + Vite React TypeScript starter. The repository also
contains a small, role-based coordinator workflow. Use plain English and do not
assume the user is an expert. Ground explanations in this repository's actual
files, commands, and behavior.

## Application architecture

- `backend/` contains the FastAPI service. `GET /api/health` returns
  `{"status":"ok"}` on port `5677`.
- `frontend/` contains the Vite React TypeScript status page on port `8455`.
- Storybook runs on port `6017`; Datasette runs on port `8677` and reads the
  empty SQLite file from the `fplpatternrec-sqlite` Docker volume.
- `tests/e2e/` contains Playwright browser tests. Backend tests live under
  `backend/tests/`; component tests live beside frontend features.
- The only database is a zero-table SQLite file in its named Docker volume.
  Never create or mount a host `data/` or `data/database/` directory.

## Graphify catalogue

For orientation, dependency tracing, ownership discovery, or work across
repository boundaries, consult `docs/graphify/README.md`. A small edit in a
known file does not require opening Graphify. The catalogue is advisory only:
source code, this `AGENTS.md`, and active Plans remain authoritative. Graphify
uses local, deterministic code-only AST extraction without an API or LLM; it
does not index Markdown or YAML. Its `source-tools` layer covers retained
`src/tools/` code, never runtime databases or other runtime data.

## Windows shell

The agent's preferred shell is Git Bash. Use PowerShell for commands documented
for Windows users. Both shells use forward slashes (e.g.
`.venv/Scripts/python.exe`), not backslashes. PowerShell commands must use
`$(...)` for subexpressions, ASCII punctuation, and no `&&` or `||` operators.
If a shell command fails, report the exact command and failure.

## Application commands

- Manage the four detached Docker services only through `dev.ps1`. Before any
  lifecycle action or browser/E2E check, run `powershell -ExecutionPolicy
  Bypass -File ./dev.ps1 status` and reuse healthy services as-is. Available
  actions are `setup`, `start`, `stop`, `restart`, `rebuild`, `status`, and
  `logs`; target `backend`, `frontend`, `storybook`, or `datasette` if needed.
  `setup` creates a valid empty database only if absent; `start` never seeds,
  imports, or refreshes it. See `docs/DEVELOPMENT_SERVICES.md`.
- `.venv/Scripts/python.exe -m pytest backend/tests tests` runs Python tests.
- Use the root `.venv` managed by `uv`; Python dependencies are configured in
  `pyproject.toml` and locked in `uv.lock`/`requirements.txt`. The root
  `package-lock.json` is authoritative for npm workspaces.
- Use the repository's root npm workspace installation; `.opencode` has its
  own package lock and install.

Local Node may fall outside the `>=24 <25` engines pin. Ignore that warning and
the non-fatal Storybook `build-storybook` teardown libuv assertion.

All checks are local; do not add application CI.

## Persistent development services

Backend, frontend, Storybook, and Datasette run as shared, long-lived Docker
Compose services. Manage them only through `dev.ps1`; check status first and
reuse healthy services. Never start competing host servers or stop services as
task cleanup.

## Testing and module-size rules

Behavioral testing uses pytest/API tests, Vitest plus React Testing Library
component tests, and Playwright end-to-end tests. Maintenance uses Ruff,
ESLint, Prettier, and source-size limits, but Plan implementation does not run
those checks unless the Plan outcome specifically changes them. The complete
test/fix run is documented in `docs/FULL_TEST_PROCESS.md`.

**Mandatory safety:** every `bash` invocation and test must have explicit finite
tool-level and command-level timeouts. Never run an unbounded process.

## Start here

1. Read the relevant active Plan under `docs/plans/active/`; completed Plans
   are archived under `docs/plans/done/`.
2. Before exploring source, read only files named by approved work or its Plan.
3. Run only finite tests or browser scenarios that directly prove approved
   behavior. Do not run lint, formatting, broad type/build, source-size,
   aggregate, or other hygiene checks during Plan implementation unless
   specifically approved.

## Workspaces

Early HTML mock-ups, catalogues, optional design notes, and prototypes belong
under `experiments/`, which has its own manifests and ignored environments and
artifacts. The design loop from mock-up to approved Storybook candidate is
defined in the Coordinator workflow skills.

## Working modes

This repository has two working modes: **God** and **Coordinator**.

- **God (default):** every session where the coordinator agent was not invoked.
  Work directly on the request using the application, command, and safety
  rules above. For substantial work, suggest moving it to the coordinator.
- **Coordinator:** runs only when the user explicitly invokes the coordinator
  agent, or when a coordinator session dispatches one of its subagents. Routing,
  scope, Plan, direct, and design-exploration behavior lives in
  `.opencode/agents/coordinator.md` and its skills.

Both modes use `.opencode/skills/grilling/SKILL.md` for interviews or material
decisions that must be settled before work continues.

## Safety

- Preserve unrelated worktree changes, historical Plans, grilling records,
  and master-plan records.
- Do not commit, push, or use destructive Git operations unless explicitly
  requested. Do not edit product source for workflow cleanup.
- Keep credentials, databases, logs, PID files, dependency directories, and
  generated build output out of commits.

## Workflow assets

`.opencode/` contains reusable repository agents, workflows, plugins, and
tools. Keep agent roles and their stated boundaries intact.

## Development rules

- Prefer modifying, reusing, and composing existing frontend components over
  replacing them or creating new implementations.
- Preserve existing component APIs, behavior, styling, and structure unless
  the requested change requires altering them.
- Create a new component only when no existing component can reasonably be
  reused, composed, adapted, or extracted. Do not rewrite a component merely
  to make it cleaner or more idiomatic.
