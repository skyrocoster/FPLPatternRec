from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest

from src.tools import graphify_catalogue as catalogue
from src.tools.graphify_catalogue_validation import PATH_KEYS, REQUIRED_ARTIFACTS

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_generator_is_owned_by_src_tools_and_resolves_repository_root() -> None:
    assert Path(catalogue.__file__).resolve() == PROJECT_ROOT / "src/tools/graphify_catalogue.py"
    assert catalogue.REPOSITORY_ROOT == PROJECT_ROOT
    assert not (PROJECT_ROOT / "tools/graphify_catalogue.py").exists()
    assert Path(catalogue.__file__).resolve().parent == PROJECT_ROOT / "src/tools"


def test_six_layer_map_includes_retained_source_tools() -> None:
    assert [(layer.name, layer.source_root, layer.output_dir) for layer in catalogue.LAYERS] == [
        ("repository", ".", "docs/graphify/repository"),
        ("backend", "backend", "docs/graphify/backend"),
        ("frontend", "frontend", "docs/graphify/frontend"),
        ("source-tools", "src/tools", "docs/graphify/source-tools"),
        ("tests", "tests", "docs/graphify/tests"),
        ("agent-workflow", ".opencode", "docs/graphify/agent-workflow"),
    ]


def test_commands_use_code_only_no_label_and_application_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(catalogue.subprocess, "run", fake_run)
    output = tmp_path / "bundle"
    layer = catalogue.LAYERS[3]
    catalogue.run_graphify(layer, "extract", output, tmp_path)
    catalogue.run_graphify(layer, "cluster-only", output, tmp_path)

    assert calls[0]["command"] == [
        sys.executable,
        "-m",
        "graphify",
        "extract",
        "src/tools",
        "--code-only",
    ]
    assert calls[1]["command"] == [
        sys.executable,
        "-m",
        "graphify",
        "cluster-only",
        "src/tools",
        "--no-label",
    ]
    assert calls[0]["env"]["GRAPHIFY_OUT"] == str(output.resolve())  # type: ignore[index]
    assert calls[0]["env"]["PYTHONHASHSEED"] == "0"  # type: ignore[index]
    assert calls[0]["timeout"] == 900
    assert "--semantic" not in calls[0]["command"]
    assert "--api" not in calls[0]["command"]


def test_graphify_failure_is_finite_reported_and_stops_before_next_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command[3])
        return subprocess.CompletedProcess(command, 17, "child stdout", "child stderr")

    monkeypatch.setattr(catalogue.subprocess, "run", fail_run)
    with pytest.raises(catalogue.GraphifyError) as raised:
        catalogue.run_graphify(catalogue.LAYERS[0], "extract", Path("bundle"), PROJECT_ROOT)

    message = str(raised.value)
    assert calls == ["extract"]
    assert "repository" in message
    assert "child stdout" in message
    assert "child stderr" in message
    assert "--code-only" in message


def test_catalogue_stops_at_failing_layer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run(layer: catalogue.LayerSpec, action: str, output: Path, root: Path) -> None:
        calls.append((layer.name, action))
        if layer.name == "backend":
            raise catalogue.GraphifyError("controlled backend failure")

    monkeypatch.setattr(catalogue, "run_graphify", fake_run)
    monkeypatch.setattr(catalogue, "validate_bundle", lambda output: None)
    with pytest.raises(catalogue.GraphifyError, match="controlled backend failure"):
        catalogue.generate_catalogue(tmp_path)
    assert calls == [
        ("repository", "extract"),
        ("repository", "cluster-only"),
        ("backend", "extract"),
    ]


def test_fresh_output_dir_replaces_prior_bundle_and_refuses_non_directory(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "stale.json").write_text("{}", encoding="utf-8")
    catalogue._fresh_output_dir(bundle)
    assert list(bundle.iterdir()) == []

    plain_file = tmp_path / "plain.txt"
    plain_file.write_text("not a directory", encoding="utf-8")
    with pytest.raises(catalogue.GraphifyError, match="Refusing to replace"):
        catalogue._fresh_output_dir(plain_file)
    assert plain_file.read_text(encoding="utf-8") == "not a directory"


def test_artifact_contract_rejects_missing_and_unexpected_entries(tmp_path: Path) -> None:
    def fixture(output: Path) -> None:
        output.mkdir(parents=True, exist_ok=True)
        (output / "graph.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
        (output / ".graphify_analysis.json").write_text("{}", encoding="utf-8")
        (output / "manifest.json").write_text("{}", encoding="utf-8")
        (output / "GRAPH_REPORT.md").write_text("# Graph\n", encoding="utf-8")
        (output / "graph.html").write_text("<html></html>", encoding="utf-8")

    output = tmp_path / "bundle"
    fixture(output)
    catalogue.validate_bundle(output)
    (output / "manifest.json").unlink()
    with pytest.raises(catalogue.GraphifyError, match="missing required artifacts"):
        catalogue.validate_bundle(output)

    fixture(output)
    (output / "unexpected.txt").write_text("no", encoding="utf-8")
    with pytest.raises(catalogue.GraphifyError, match="unexpected final artifacts"):
        catalogue.validate_bundle(output)


def test_host_database_paths_are_rejected_without_database_access(
    tmp_path: Path,
) -> None:
    output = tmp_path / "runtime-data-bundle"
    output.mkdir()
    (output / "graph.json").write_text(
        json.dumps({"nodes": [{"file_path": "data/database/example.db"}]}), encoding="utf-8"
    )
    (output / ".graphify_analysis.json").write_text("{}", encoding="utf-8")
    (output / "manifest.json").write_text("{}", encoding="utf-8")
    (output / "GRAPH_REPORT.md").write_text("# Graph\n", encoding="utf-8")
    (output / "graph.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(catalogue.GraphifyError, match="Runtime-data path"):
        catalogue.validate_bundle(output)


def test_ignore_rules_exclude_generated_graphify_bundles() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    graphifyignore = (PROJECT_ROOT / ".graphifyignore").read_text(encoding="utf-8")
    assert "docs/graphify/*" in gitignore
    assert "!docs/graphify/README.md" in gitignore
    assert "/graphify-out/" in gitignore
    assert "!.opencode/commands/" in gitignore
    assert "!.opencode/commands/commit.md" in gitignore
    assert "/docs/graphify/" in graphifyignore
    assert "/graphify-out/" in graphifyignore


def test_generated_bundles_are_ignored_and_index_is_not_ignored() -> None:
    generated = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "docs/graphify/source-tools/manifest.json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    index = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", "docs/graphify/README.md"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert generated.returncode == 0
    assert index.returncode == 1


def _assert_relative_catalogue_path(value: str) -> None:
    normalized = value.replace("\\", "/")
    assert not normalized.startswith(("/", "//"))
    assert not (len(normalized) > 1 and normalized[1] == ":")
    assert not PurePosixPath(normalized).is_absolute()
    assert ".." not in PurePosixPath(normalized).parts


def _graph_path_values(value: object) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if (
                isinstance(key, str)
                    and key.lower() in PATH_KEYS
                and isinstance(child, str)
            ):
                paths.append(child)
            paths.extend(_graph_path_values(child))
    elif isinstance(value, list):
        for child in value:
            paths.extend(_graph_path_values(child))
    return paths


def test_generated_catalogues_have_six_exact_five_artifact_bundles_when_present() -> None:
    if not any((PROJECT_ROOT / layer.output_dir).exists() for layer in catalogue.LAYERS):
        pytest.skip("Graphify generation is a separate operation")
    for layer in catalogue.LAYERS:
        output = PROJECT_ROOT / layer.output_dir
        assert output.is_dir()
        assert {entry.name for entry in output.iterdir()} == set(REQUIRED_ARTIFACTS)

        graph = json.loads((output / "graph.json").read_text(encoding="utf-8"))
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        assert isinstance(manifest, dict) and manifest

        for source_path in _graph_path_values(graph):
            _assert_relative_catalogue_path(source_path)
        for source_path, record in manifest.items():
            _assert_relative_catalogue_path(source_path)
            assert {"mtime", "seen", "ast_hash", "semantic_hash"} <= set(record)
            assert record["ast_hash"] and record["semantic_hash"]

        generated_text = (
            json.dumps(graph).lower() + json.dumps(manifest).lower()
        )
        assert "docs/graphify/" not in generated_text
        assert "data/database/" not in generated_text
        assert str(PROJECT_ROOT.resolve()).replace("\\", "/").lower() not in generated_text

    tools_manifest = json.loads(
        (PROJECT_ROOT / "docs/graphify/source-tools/manifest.json").read_text(encoding="utf-8")
    )
    assert set(tools_manifest) == {
        "full_test_process.py",
        "graphify_catalogue.py",
        "graphify_catalogue_validation.py",
    }
    assert all(not path.startswith("src/") for path in tools_manifest)
    assert not any(path.startswith("data_retrieval/") for path in tools_manifest)


def test_stage_two_signpost_is_a_thin_bundle_index() -> None:
    readme = (PROJECT_ROOT / "docs/graphify/README.md").read_text(encoding="utf-8")
    bundles = (
        "repository",
        "backend",
        "frontend",
        "source-tools",
        "tests",
        "agent-workflow",
    )
    for bundle in bundles:
        assert f"]({bundle}/GRAPH_REPORT.md)" in readme
    assert "AGENTS.md" in readme
    assert "src/tools/graphify_catalogue.py" in readme
    assert len(readme.splitlines()) <= 20


def test_stage_two_authority_and_commit_fail_closed_ordering() -> None:
    agents = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    commit = (PROJECT_ROOT / ".opencode/commands/commit.md").read_text(encoding="utf-8")
    assert "docs/graphify/README.md" in agents
    assert "orientation, dependency tracing, ownership discovery" in agents
    assert "source code, this `AGENTS.md`, and active Plans remain authoritative" in agents
    assert "`source-tools` layer covers retained" in agents
    assert "never runtime databases" in agents
    assert "gitignored" in commit
    assert commit.index("src/tools/graphify_catalogue.py") < commit.index("git status")
    assert commit.index("git status") < commit.index("git diff")
    assert commit.index("git diff") < commit.index("git add -A")
    assert commit.index("git add -A") < commit.index("git commit")
    assert "timeout 10800s" in commit
    assert "10810000" in commit
    assert "failed layer and exact command" in commit
    assert "Do not continue to repository review, staging, or committing" in commit
