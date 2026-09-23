"""Fail-fast, resumable runner for every repository-defined local check."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
STATE_DIRECTORY = REPOSITORY_ROOT / ".stage-check" / "full-test"
STATE_PATH = STATE_DIRECTORY / "state.json"
FAILURE_LOG_PATH = STATE_DIRECTORY / "latest-failure.log"
STORYBOOK_WINDOWS_TEARDOWN_CODES = {0xC0000409, -1073740791}
STORYBOOK_WINDOWS_TEARDOWN_ASSERTION = (
    "Assertion failed: !(handle->flags & UV_HANDLE_CLOSING), "
    r"file c:\ws\deps\uv\src\win\async.c, line 76"
)
WARNING_PATTERN = re.compile(
    r"(?:\bwarnings?\b|\bwarn\b|\bdeprecationwarnings?\b|\bexperimentalwarnings?\b|^\s*\(!\))",
    re.IGNORECASE,
)
ZERO_WARNING_PATTERN = re.compile(r"\b(?:0|no) warnings?\b", re.IGNORECASE)
ALLOWED_WARNING_PATTERNS = (re.compile(r"^\s*npm warn EBADENGINE\b", re.IGNORECASE),)


def _configure_output_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


@dataclass(frozen=True)
class Step:
    name: str
    command: tuple[str, ...]
    timeout_seconds: int
    environment: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StepResult:
    passed: bool
    reason: str
    stdout: str = ""
    stderr: str = ""


def _tool(name: str) -> str:
    return str(REPOSITORY_ROOT / "node_modules" / ".bin" / f"{name}.cmd")


def _npm(*arguments: str) -> tuple[str, ...]:
    return ("corepack.cmd", "npm", *arguments)


def build_steps() -> list[Step]:
    return [
        Step("Compose configuration", ("docker", "compose", "config", "--quiet"), 60),
        Step("Python dependency integrity", (sys.executable, "-m", "pip", "check"), 60),
        Step("Node dependency integrity", _npm("ls", "--all"), 180),
        Step(
            "Source size limits",
            (sys.executable, "tests/cleanliness/check_file_lengths.py"),
            60,
        ),
        Step("Ruff lint", (sys.executable, "-m", "ruff", "check", "."), 180),
        Step(
            "Ruff formatting",
            (sys.executable, "-m", "ruff", "format", "--check", "."),
            180,
        ),
        Step("Prettier formatting", (_tool("prettier"), "--check", "frontend"), 300),
        Step(
            "ESLint",
            _npm(
                "--loglevel",
                "warn",
                "run",
                "lint",
                "--prefix",
                "frontend",
                "--",
                "--max-warnings",
                "0",
            ),
            300,
        ),
        Step("TypeScript", (_tool("tsc"), "-b", "frontend"), 300),
        Step(
            "Python backend and repository tests",
            (
                sys.executable,
                "-m",
                "pytest",
                "backend/tests",
                "tests",
                "-W",
                "error",
                "--maxfail=1",
                "-q",
            ),
            1800,
            {"PYTHONWARNINGS": "error"},
        ),
        Step(
            "Frontend unit tests",
            (
                "corepack.cmd",
                "npm",
                "run",
                "test",
                "--prefix",
                "frontend",
                "--",
                "--run",
                "--project=unit",
                "--bail=1",
            ),
            900,
        ),
        Step(
            "Development service preflight",
            (
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "./dev.ps1",
                "status",
            ),
            60,
        ),
        Step(
            "Frontend real-backend API tests",
            (
                _tool("vitest"),
                "run",
                "--config",
                "frontend/vitest.api.config.ts",
                "--bail=1",
            ),
            300,
        ),
        Step("Frontend production build", _npm("run", "build", "--prefix", "frontend"), 900),
        Step(
            "Storybook browser tests",
            (
                "corepack.cmd",
                "npm",
                "run",
                "test-storybook",
                "--prefix",
                "frontend",
                "--",
                "--run",
                "--bail=1",
            ),
            1200,
        ),
        Step(
            "Storybook production build",
            _npm("run", "build-storybook", "--prefix", "frontend"),
            1200,
        ),
        Step(
            "Playwright end-to-end tests",
            (
                _tool("playwright"),
                "test",
                "--config",
                "tests/e2e/playwright.config.ts",
                "--max-failures=1",
            ),
            1800,
        ),
    ]


def _command_text(step: Step) -> str:
    return subprocess.list2cmdline(step.command)


def _suite_fingerprint(steps: Sequence[Step]) -> str:
    payload = [
        {
            "name": step.name,
            "command": step.command,
            "timeout_seconds": step.timeout_seconds,
            "environment": step.environment,
        }
        for step in steps
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def warning_lines(stdout: str, stderr: str) -> list[str]:
    warnings: list[str] = []
    for line in (*stdout.splitlines(), *stderr.splitlines()):
        if not WARNING_PATTERN.search(line) or ZERO_WARNING_PATTERN.search(line):
            continue
        if any(pattern.search(line) for pattern in ALLOWED_WARNING_PATTERNS):
            continue
        warnings.append(line)
    return warnings


def _documented_storybook_teardown(step: Step, return_code: int, stdout: str, stderr: str) -> bool:
    return (
        os.name == "nt"
        and step.name == "Storybook production build"
        and return_code in STORYBOOK_WINDOWS_TEARDOWN_CODES
        and "Storybook build completed successfully" in stdout
        and stderr.strip() == STORYBOOK_WINDOWS_TEARDOWN_ASSERTION
    )


def classify_result(step: Step, return_code: int, stdout: str, stderr: str) -> StepResult:
    if _documented_storybook_teardown(step, return_code, stdout, stderr):
        return StepResult(True, "documented Windows Storybook teardown exception", stdout, stderr)
    if return_code != 0:
        return StepResult(False, f"exit code {return_code}", stdout, stderr)
    warnings = warning_lines(stdout, stderr)
    if warnings:
        return StepResult(False, f"warning output: {warnings[0]}", stdout, stderr)
    return StepResult(True, "clean exit", stdout, stderr)


def _stop_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def execute_step(step: Step) -> StepResult:
    environment = os.environ.copy()
    environment.update(step.environment)
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            step.command,
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        return StepResult(False, f"could not start: {error}", stderr=str(error))
    try:
        stdout, stderr = process.communicate(timeout=step.timeout_seconds)
    except subprocess.TimeoutExpired as error:
        _stop_process_tree(process)
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = error.stderr if isinstance(error.stderr, str) else ""
        return StepResult(
            False,
            f"timeout after {step.timeout_seconds} seconds",
            stdout,
            stderr,
        )
    result = classify_result(step, process.returncode, stdout, stderr)
    duration = time.monotonic() - started
    return StepResult(result.passed, f"{result.reason}; {duration:.1f}s", stdout, stderr)


def _write_state(index: int, steps: Sequence[Step]) -> None:
    STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "suite_fingerprint": _suite_fingerprint(steps),
        "next_index": index,
        "next_step": steps[index].name if index < len(steps) else None,
        "completed": [step.name for step in steps[:index]],
    }
    STATE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _load_resume_index(steps: Sequence[Step]) -> int:
    if not STATE_PATH.is_file():
        return 0
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Checkpoint is unreadable; starting from the first check.")
        return 0
    if state.get("suite_fingerprint") != _suite_fingerprint(steps):
        print("Check inventory changed; starting from the first check.")
        return 0
    index = state.get("next_index")
    return index if isinstance(index, int) and 0 <= index <= len(steps) else 0


def _matching_index(steps: Sequence[Step], query: str) -> int:
    normalized = query.casefold()
    exact = [index for index, step in enumerate(steps) if step.name.casefold() == normalized]
    if exact:
        return exact[0]
    matches = [index for index, step in enumerate(steps) if normalized in step.name.casefold()]
    if len(matches) != 1:
        names = ", ".join(steps[index].name for index in matches) or "none"
        raise ValueError(f"step name must match exactly one check; matches: {names}")
    return matches[0]


def _write_failure(step: Step, result: StepResult) -> None:
    STATE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    payload = [
        f"CHECK: {step.name}",
        f"COMMAND: {_command_text(step)}",
        f"RESULT: {result.reason}",
        "--- stdout ---",
        result.stdout,
        "--- stderr ---",
        result.stderr,
    ]
    FAILURE_LOG_PATH.write_text("\n".join(payload), encoding="utf-8")


def run_suite(steps: Sequence[Step], start_index: int) -> int:
    for index in range(start_index, len(steps)):
        step = steps[index]
        _write_state(index, steps)
        print(f"START [{index + 1}/{len(steps)}] {step.name}", flush=True)
        print(f"  {_command_text(step)}", flush=True)
        result = execute_step(step)
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="" if result.stderr.endswith("\n") else "\n")
        if not result.passed:
            _write_failure(step, result)
            print(f"FAIL {step.name}: {result.reason}", file=sys.stderr, flush=True)
            print(f"Failure log: {FAILURE_LOG_PATH}", file=sys.stderr, flush=True)
            print("Fix this issue, then run the same command to resume here.", file=sys.stderr)
            return 1
        print(f"PASS {step.name}: {result.reason}", flush=True)
        _write_state(index + 1, steps)
    STATE_PATH.unlink(missing_ok=True)
    FAILURE_LOG_PATH.unlink(missing_ok=True)
    print(f"PASS complete full-test process ({len(steps)} checks).", flush=True)
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run all repository checks in order and remember the first failure."
    )
    parser.add_argument("--list", action="store_true", help="list the complete ordered inventory")
    parser.add_argument(
        "--fresh", action="store_true", help="discard the checkpoint and start first"
    )
    parser.add_argument("--from", dest="from_step", metavar="NAME", help="start at one named check")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_output_streams()
    args = _parser().parse_args(argv)
    steps = build_steps()
    if args.list:
        for index, step in enumerate(steps, start=1):
            print(f"{index:>2}. {step.name} ({step.timeout_seconds}s)\n    {_command_text(step)}")
        return 0
    if args.fresh and args.from_step:
        _parser().error("--fresh and --from cannot be used together")
    if args.fresh:
        start_index = 0
    elif args.from_step:
        try:
            start_index = _matching_index(steps, args.from_step)
        except ValueError as error:
            _parser().error(str(error))
    else:
        start_index = _load_resume_index(steps)
    return run_suite(steps, start_index)


if __name__ == "__main__":
    raise SystemExit(main())
