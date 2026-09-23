"""Generate the repository's deterministic Graphify catalogue.

The generator runs local, deterministic AST-only extraction and clustering for
each layer, then validates the resulting bundle. It never opens the repository
database; Graphify's normal ignore handling excludes it. Generated bundles are
machine-local (gitignored) output under ``docs/graphify/<layer>/``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from .graphify_catalogue_validation import (
        REQUIRED_ARTIFACTS,
        GraphifyError,
        _load_json,
        _validate_artifact_files,
    )
except ImportError:  # direct script execution: python src/tools/graphify_catalogue.py
    from graphify_catalogue_validation import (  # type: ignore[import-not-found]
        REQUIRED_ARTIFACTS,
        GraphifyError,
        _load_json,
        _validate_artifact_files,
    )


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GRAPHIFY_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class LayerSpec:
    name: str
    source_root: str
    output_dir: str


LAYERS = (
    LayerSpec("repository", ".", "docs/graphify/repository"),
    LayerSpec("backend", "backend", "docs/graphify/backend"),
    LayerSpec("frontend", "frontend", "docs/graphify/frontend"),
    LayerSpec("source-tools", "src/tools", "docs/graphify/source-tools"),
    LayerSpec("tests", "tests", "docs/graphify/tests"),
    LayerSpec("agent-workflow", ".opencode", "docs/graphify/agent-workflow"),
)


def _command_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def build_graphify_command(action: str, source_root: str) -> list[str]:
    """Build one of the two permitted Graphify commands."""

    if action == "extract":
        return [sys.executable, "-m", "graphify", "extract", source_root, "--code-only"]
    if action == "cluster-only":
        return [
            sys.executable,
            "-m",
            "graphify",
            "cluster-only",
            source_root,
            "--no-label",
        ]
    raise ValueError(f"unsupported Graphify action: {action}")


def _process_output(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


def run_graphify(
    layer: LayerSpec,
    action: str,
    output_dir: Path,
    repository_root: Path = REPOSITORY_ROOT,
) -> None:
    """Run one Graphify operation with the approved environment and timeout."""

    command = build_graphify_command(action, layer.source_root)
    environment = os.environ.copy()
    environment["GRAPHIFY_OUT"] = str(output_dir.resolve())
    environment["PYTHONHASHSEED"] = "0"
    try:
        completed = subprocess.run(
            command,
            cwd=repository_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=GRAPHIFY_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = _process_output(error.stdout)
        stderr = _process_output(error.stderr)
        raise GraphifyError(
            f"Graphify layer {layer.name!r} timed out after "
            f"{GRAPHIFY_TIMEOUT_SECONDS}s.\n"
            f"Command: {_command_text(command)}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        ) from error

    if completed.returncode:
        raise GraphifyError(
            f"Graphify layer {layer.name!r} failed with exit code "
            f"{completed.returncode}.\n"
            f"Command: {_command_text(command)}\n"
            f"stdout:\n{_process_output(completed.stdout)}\n"
            f"stderr:\n{_process_output(completed.stderr)}"
        )


def _fresh_output_dir(output_dir: Path) -> None:
    """Replace the layer's generated output directory with an empty directory."""

    if not output_dir.exists():
        output_dir.mkdir(parents=True)
        return
    if output_dir.is_symlink() or not output_dir.is_dir():
        raise GraphifyError(f"Refusing to replace non-directory Graphify output: {output_dir}")
    shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)


def _strip_graphify_sidecars(output_dir: Path) -> None:
    """Remove Graphify CLI sidecars, leaving exactly the required artifacts."""

    required = set(REQUIRED_ARTIFACTS)
    for entry in output_dir.iterdir():
        if entry.name in required:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def validate_bundle(output_dir: Path) -> None:
    """Validate a complete five-artifact Graphify bundle."""

    _validate_artifact_files(output_dir)
    _load_json(output_dir / "graph.json", "graph.json")
    _load_json(output_dir / ".graphify_analysis.json", ".graphify_analysis.json")
    _load_json(output_dir / "manifest.json", "manifest.json")
    for name in ("GRAPH_REPORT.md", "graph.html"):
        try:
            (output_dir / name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise GraphifyError(f"Unable to read Graphify {name} in {output_dir}") from error


def generate_catalogue(repository_root: Path = REPOSITORY_ROOT) -> None:
    """Generate all layers in order, stopping at the first failure."""

    legacy_output = repository_root / "graphify-out"
    if legacy_output.is_dir() and not legacy_output.is_symlink():
        shutil.rmtree(legacy_output)
    for layer in LAYERS:
        output_dir = repository_root / layer.output_dir
        _fresh_output_dir(output_dir)
        run_graphify(layer, "extract", output_dir, repository_root)
        run_graphify(layer, "cluster-only", output_dir, repository_root)
        _strip_graphify_sidecars(output_dir)
        validate_bundle(output_dir)


def main() -> int:
    try:
        generate_catalogue()
    except (GraphifyError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
