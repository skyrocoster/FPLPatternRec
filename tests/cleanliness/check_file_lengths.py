from __future__ import annotations

import argparse
import fnmatch
import pathlib
import sys

# Production code gets 500 lines; test files get 700 lines.
SOURCE_LIMIT = 500
TEST_LIMIT = 700

# Only these file types are measured. Everything else (JSON, Markdown,
# YAML, images, databases, ...) is skipped on purpose.
SCRIPT_EXTENSIONS = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".mts",
        ".cts",
        ".ps1",
        ".sh",
    }
)

# Folder names that are never scanned. Compared case-insensitively so both
# "Scratch/" and "scratch/" are skipped. These hold installed dependencies,
# build output, disposable mock-ups, or personal notes -- not code to fix.
EXCLUDE_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "dist",
        "build",
        "storybook-static",
        "coverage",
        "test-results",
        "artifacts",
        "logs",
        ".playwright-mcp",
        ".claude",
        ".cursor",
        ".agents",
        ".opencode",
        ".vscode",
        ".idea",
        "data",
        "scratch",
        "experiments",
    }
)

# File/folder patterns that are never scanned. This covers generated code
# (which we should not hand-split) and compiled files.
EXCLUDE_PATTERNS = (
    "*/generated/*",
    "*.gen.*",
    "*.generated.*",
    "*.min.js",
    "*.bundle.js",
    "*.pyc",
    "*.pyo",
)

# Folder names that mark a file as a test file (700-line limit).
TEST_DIRS = frozenset({"tests", "test", "__tests__", "e2e", "integration", "services"})


def is_excluded(path: pathlib.Path, root: pathlib.Path) -> bool:
    """Return True when a file lives in a skipped folder or matches a skip pattern."""
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        return True
    for part in path.relative_to(root).parts:
        if part.lower() in EXCLUDE_DIRS:
            return True
    return any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDE_PATTERNS)


def is_test_file(path: pathlib.Path) -> bool:
    """Return True when a file counts as a test (700-line limit).

    Real-world examples that count as tests:

    * ``backend/tests/features/health/test_health.py``
    * ``tests/e2e/status-page.spec.ts``
    * ``frontend/src/App.test.tsx``
    """
    name = path.name.lower()
    if name == "conftest.py":
        return True
    for marker in ("test_", "_test.", ".test.", ".spec."):
        if marker in name:
            return True
    return any(part in TEST_DIRS for part in path.parts)


def count_lines(path: pathlib.Path) -> int:
    """Count lines in a file, tolerating unusual characters."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def scan(root: pathlib.Path) -> list[dict]:
    """Walk the repo and measure every script file. Returns one row per file."""
    rows: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SCRIPT_EXTENSIONS:
            continue
        if is_excluded(path, root):
            continue
        test = is_test_file(path)
        limit = TEST_LIMIT if test else SOURCE_LIMIT
        lines = count_lines(path)
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "lines": lines,
                "limit": limit,
                "kind": "test" if test else "source",
                "over": lines - limit,
            }
        )
    return rows


def print_report(rows: list[dict]) -> list[dict]:
    """Print a plain-English inventory. Returns only the over-limit rows."""
    over = sorted(
        (row for row in rows if row["lines"] > row["limit"]),
        key=lambda row: row["over"],
        reverse=True,
    )
    checked = len(rows)
    print(f"Checked {checked} script files (limits: source {SOURCE_LIMIT}, test {TEST_LIMIT}).")
    print("Non-script files (like JSON) and generated code were skipped.")
    if not over:
        print("All files are within their limits. Nothing to split up.")
        return over
    print(f"Found {len(over)} file(s) over the limit:")
    print(f"{'Lines':>7}  {'Limit':>6}  {'Over':>6}  File")
    for row in over:
        print(f"{row['lines']:>7}  {row['limit']:>6}  {row['over']:>+6}  {row['path']}")
    return over


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory files over the length limits "
            f"(source {SOURCE_LIMIT} lines, test {TEST_LIMIT} lines). "
            "Prints the list; exits 1 on violations unless --inventory is given."
        )
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan (default: current directory).",
    )
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="Only print the list; always exit 0 (for AI inventory runs).",
    )
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root).resolve()
    if not root.is_dir():
        print(f"Root folder not found: {root}", file=sys.stderr)
        return 2

    rows = scan(root)
    over = print_report(rows)
    if args.inventory:
        return 0
    return 1 if over else 0


if __name__ == "__main__":
    raise SystemExit(main())
