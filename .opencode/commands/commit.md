---
description: Stage all changes and commit with an AI-generated summary message.
---

2. Run `git status` to understand what has changed.
3. Run `git diff --staged` and `git diff` to review the actual changes. Note that `docs/graphify/` bundles are gitignored, machine-local output; they never appear in the diff.
4. Write a concise commit message that accurately summarizes all changes. Follow conventional commit style (e.g. `feat:`, `fix:`, `chore:`, `refactor:`, `test:`, `docs:`). Keep the subject line under 72 characters. Add a body if the changes are complex.
5. Run `git add -A` to stage everything.
6. Run `git commit` with the message you wrote.
7. Report the commit hash and summary to the user.
