# Full test and repair process

This is the repository's complete local maintenance run. It is deliberately different from focused feature
proof: it runs all currently defined tests, builds, and quality checks, stops at the first problem, and remembers
where to continue after that problem is fixed.

The OpenCode primary agent for this job is **`test-fixer`**. It uses Luna at `xhigh` reasoning and cannot invoke
subagents or create Plans.

## Start or resume

Run from the repository root with the project virtual environment:

```bash
# Show the authoritative ordered inventory without running it.
.venv/Scripts/python.exe src/tools/full_test_process.py --list

# Start at check 1, or automatically resume at the remembered failure.
.venv/Scripts/python.exe src/tools/full_test_process.py
```

The runner writes ignored, machine-local state under `.stage-check/full-test/`:

- `state.json` identifies the next check. It points to the running check before that process starts, so an
  interruption safely reruns that check.
- `latest-failure.log` contains the complete stdout and stderr for the first failed check.

The Python suite uses only the retained backend and repository tests. No live
or host-side application database is needed by the test run.

On a failure, fix that one issue and run the same command again. The failed check runs again; after it passes, the
remaining checks continue. A completed run deletes the checkpoint and failure log.

Use these controls only when needed:

```bash
# Deliberately discard progress and start at check 1.
.venv/Scripts/python.exe src/tools/full_test_process.py --fresh

# Restart at one exact or uniquely matching check after a fix invalidates earlier proof.
.venv/Scripts/python.exe src/tools/full_test_process.py --from "Ruff lint"
```

If the check inventory changes while a checkpoint exists, the runner rejects the old checkpoint and starts from
check 1.

## Ordered inventory

The `--list` output is authoritative. The process currently covers:

1. Docker Compose configuration parsing.
2. Installed Python dependency integrity (`pip check`).
3. The complete installed npm dependency tree (`npm ls --all`).
4. The 500-line source and 700-line test limits.
5. Ruff lint.
6. Ruff formatting.
7. Prettier formatting.
8. ESLint with zero warnings allowed.
9. TypeScript project checking.
10. All Python tests under `backend/tests` and `tests`, with Python warnings converted to errors and pytest
    stopping at its first failure.
11. Frontend Vitest/React Testing Library unit tests, stopping at the first failure.
12. Shared development-service health through `dev.ps1 status`.
13. The Vitest API tests against the real backend service.
14. The production frontend build.
15. Storybook browser tests in Chromium, including story interactions and accessibility assertions.
16. The production Storybook build.
17. Every Playwright end-to-end spec, including application, Storybook, responsive, and accessibility coverage,
    stopping at the first failure.

Every child process has a finite timeout. The full process does not install
optional external scanners, refresh Graphify's generated catalogue, commit
changes, or add CI. Those are separate operations rather than
repository-defined test commands.

## Failure and warning policy

The runner stops immediately for:

- a nonzero exit;
- a timeout;
- warning output, even when the command exits successfully.

Pytest uses `-W error`, ESLint uses `--max-warnings 0`, and Playwright, Vitest, and pytest use their fail-fast
options. The runner also scans stdout and stderr so successful builds cannot silently leave warnings behind.

Two narrow exceptions come from `AGENTS.md` and no others:

1. the local npm `EBADENGINE` warning when the installed Node version is outside the repository's Node 24 pin;
2. the exact known Windows Storybook libuv teardown assertion, only after Storybook says the production build
   completed successfully.

Do not suppress a new warning. Repair its cause. Do not skip, weaken, or delete a valid test to move the
checkpoint.

## Repair loop and proof

1. Run the process until it stops.
2. Read the terminal output and, if needed, `latest-failure.log`.
3. Repair only the first failure or warning.
4. Run the same command to resume at that check.
5. If the repair could affect a previously passed check, use `--from` with the earliest affected check. For
   example, changing Python source after Ruff passed invalidates the Ruff checks; changing only a Storybook test
   does not invalidate Python tests.
6. Finish only when the runner prints `PASS complete full-test process` against the final worktree.

Before the service preflight or any browser/E2E work, follow `docs/DEVELOPMENT_SERVICES.md`: reuse healthy shared
services, inspect logs before restarting an unhealthy service, and never start Uvicorn, Vite, or Storybook
directly.
