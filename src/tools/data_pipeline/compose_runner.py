"""Run a one-shot data-tools Compose command from the repository checkout."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

CommandRunner = Callable[..., subprocess.CompletedProcess[object]]


def build_compose_command(arguments: Sequence[str], project_root: Path | None = None) -> list[str]:
    root = project_root or Path(__file__).resolve().parents[3]
    run_options = ["--build", "--rm", "--no-deps"]
    if tuple(arguments[:2]) in {
        ("ingest", "official-fpl-teams"),
        ("ingest", "canonical-schema"),
        ("ingest", "canonical-teams"),
        ("ingest", "canonical-archive-teams"),
        ("ingest", "canonical-players"),
        ("ingest", "canonical-archive-players"),
        ("ingest", "player-birth-dates"),
        ("ingest", "player-gameweek-teams"),
        ("ingest", "canonical-fixtures"),
        ("ingest", "player-fixture-observations"),
        ("ingest", "match-dates"),
    }:
        run_options.extend(["--user", "0:0"])

    return [
        "docker",
        "compose",
        "--file",
        str(root / "compose.yaml"),
        "--project-directory",
        str(root),
        "--profile",
        "one-shot",
        "run",
        *run_options,
        "data-tools",
        *arguments,
    ]


def run_data_tools(
    arguments: Sequence[str],
    project_root: Path | None = None,
    runner: CommandRunner | None = None,
) -> int:
    invoke = runner or subprocess.run
    result = invoke(build_compose_command(arguments, project_root), check=False)
    return result.returncode


def main(arguments: Sequence[str] | None = None) -> int:
    return run_data_tools(sys.argv[1:] if arguments is None else arguments)


if __name__ == "__main__":
    raise SystemExit(main())
