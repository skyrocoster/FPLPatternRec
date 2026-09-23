"""Artifact validation helpers for the Graphify catalogue generator."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_ARTIFACTS = (
    "GRAPH_REPORT.md",
    "graph.html",
    "graph.json",
    ".graphify_analysis.json",
    "manifest.json",
)
FORBIDDEN_PATH_RE = re.compile(
    r"(?i)(?:^[\"'`\s(/\\])data(?:[/\\])database(?:[/\\])"
)
ABSOLUTE_WINDOWS_RE = re.compile(r"(?i)^[a-z]:[/\\]")
PATH_KEYS = frozenset(
    {
        "file",
        "file_name",
        "filename",
        "file_path",
        "filepath",
        "path",
        "relative_path",
        "source_file",
        "source_path",
    }
)


class GraphifyError(RuntimeError):
    """A fail-fast error that identifies the layer and operation involved."""


def _assert_safe_path(value: str, label: str) -> None:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ABSOLUTE_WINDOWS_RE.match(value) or normalized.startswith("//"):
        raise GraphifyError(f"Absolute path in generated {label}: {value}")
    if any(part == ".." for part in path.parts):
        raise GraphifyError(f"Parent traversal in generated {label}: {value}")
    lowered = normalized.lower().lstrip("./")
    if lowered.startswith("data/database/"):
        raise GraphifyError(f"Runtime-data path in generated {label}: {value}")
    if lowered.startswith("docs/graphify/"):
        raise GraphifyError(f"Forbidden generated {label}: {value}")


def _walk_json_paths(value: Any, label: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.replace("\\", "/").lower().startswith("data/"):
                yield f"{label}.<key>", key
            if isinstance(key, str) and ("/" in key or "\\" in key):
                yield f"{label}.<key>", key
            if isinstance(key, str) and key.lower() in PATH_KEYS and isinstance(child, str):
                yield f"{label}.{key}", child
            yield from _walk_json_paths(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_json_paths(child, f"{label}[{index}]")


def _validate_generated_text(text: str, label: str) -> None:
    normalized = text.replace("\\", "/")
    lowered = normalized.lower()
    if FORBIDDEN_PATH_RE.search(normalized):
        raise GraphifyError(f"Runtime-data path in generated {label}")
    if "docs/graphify/" in lowered:
        raise GraphifyError(f"Self-indexed output path in generated {label}")
    root_text = str(REPOSITORY_ROOT).replace("\\", "/").lower()
    if root_text and root_text in lowered:
        raise GraphifyError(f"Absolute repository path in generated {label}")


def _load_json(path: Path, label: str) -> Any:
    try:
        with path.open(encoding="utf-8") as stream:
            value = json.load(stream)
    except (OSError, json.JSONDecodeError) as error:
        raise GraphifyError(f"Malformed generated {label}: {path}") from error
    for path_label, path_value in _walk_json_paths(value, label):
        _assert_safe_path(path_value, path_label)
    _validate_generated_text(json.dumps(value), label)
    return value


def _validate_artifact_files(output_dir: Path) -> None:
    if not output_dir.is_dir() or output_dir.is_symlink():
        raise GraphifyError(f"Graphify output directory is invalid: {output_dir}")
    names = {entry.name for entry in output_dir.iterdir()}
    required = set(REQUIRED_ARTIFACTS)
    missing = required - names
    extra = names - required
    if missing:
        raise GraphifyError(
            f"Graphify output is missing required artifacts in {output_dir}: {sorted(missing)}"
        )
    if extra:
        raise GraphifyError(
            f"Graphify output has unexpected final artifacts in {output_dir}: {sorted(extra)}"
        )
    for name in REQUIRED_ARTIFACTS:
        artifact = output_dir / name
        if artifact.is_symlink() or not artifact.is_file():
            raise GraphifyError(f"Graphify artifact is not a regular file: {artifact}")
