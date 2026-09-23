---
description: Stage all changes and commit with an AI-generated summary message.
---

1. In a Bash tool call with a `10810000` ms timeout, run `timeout 10800s .venv/Scripts/python.exe src/tools/graphify_catalogue.py` from the repository root. This is the first operation: it refreshes all six bundles from the complete local working tree using local deterministic AST-only extraction and clustering, with no API or LLM.
   If generation exits nonzero, times out, or reports any failure, stop immediately and report the failed layer and exact command. Do not continue to repository review, staging, or committing after a failed refresh.
2. Run `git status` to understand what has changed.
3. Run `git diff --staged` and `git diff` to review the actual changes. Note that `docs/graphify/` bundles are gitignored, machine-local output; they never appear in the diff.
4. Write a concise commit message that accurately summarizes all changes. Follow conventional commit style (e.g. `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`). Keep the subject line under 72 characters. Add a body if the changes are complex.
5. Run `git add -A` to stage everything.
6. Run `git commit` with the message you wrote.
7. Report the commit hash and summary to the user.
