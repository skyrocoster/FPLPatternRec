from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.archive_players import ArchivePlayersLoadSummary
from tools.data_pipeline.ingestion.canonical_players import CanonicalPlayersLoadSummary
from tools.data_pipeline.ingestion.canonical_teams import CanonicalTeamsLoadSummary

runner = CliRunner()


def test_core_group_dispatches_all_registered_providers(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, cli.RetrievalOptions]] = []
    provider_names = tuple(cli.CORE_PROVIDERS)
    for provider_name in provider_names:
        monkeypatch.setitem(
            cli.CORE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append((name, options)),
        )

    result = runner.invoke(cli.app, ["retrieve", "core", "--raw-root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert [name for name, _ in calls] == list(provider_names)
    assert all(options.include_fpl_player_summaries for _, options in calls)
    assert all(options.include_fotmob_match_details for _, options in calls)


def test_core_group_defaults_to_the_existing_core_raw_root(monkeypatch) -> None:
    roots: list[Path] = []

    class RecordingCollector:
        def __init__(self, raw_root: Path) -> None:
            roots.append(raw_root)

    monkeypatch.setattr(cli, "RawCollector", RecordingCollector)
    for provider_name in tuple(cli.CORE_PROVIDERS):
        monkeypatch.setitem(
            cli.CORE_PROVIDERS,
            provider_name,
            lambda collector, options: None,
        )

    result = runner.invoke(cli.app, ["retrieve", "core"])

    assert result.exit_code == 0, result.output
    assert roots == [cli.default_core_raw_root()]


def test_individual_provider_commands_dispatch_all_registered_core_providers(
    tmp_path: Path, monkeypatch
) -> None:
    provider_names = tuple(cli.CORE_PROVIDERS)
    for provider_name in provider_names:
        calls: list[str] = []
        monkeypatch.setitem(
            cli.CORE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(name),
        )

        result = runner.invoke(
            cli.app, ["retrieve", provider_name, "--raw-root", str(tmp_path)]
        )

        assert result.exit_code == 0, f"{provider_name}: {result.output}"
        assert calls == [provider_name]


def test_core_group_preserves_optional_collection_controls(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, cli.RetrievalOptions]] = []
    for provider_name in tuple(cli.CORE_PROVIDERS):
        monkeypatch.setitem(
            cli.CORE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append((name, options)),
        )

    result = runner.invoke(
        cli.app,
        [
            "retrieve",
            "core",
            "--raw-root",
            str(tmp_path),
            "--no-fpl-player-summaries",
            "--no-fotmob-match-details",
        ],
    )

    assert result.exit_code == 0, result.output
    assert all(not options.include_fpl_player_summaries for _, options in calls)
    assert all(not options.include_fotmob_match_details for _, options in calls)


def test_official_fpl_command_defaults_to_full_request_coverage(
    tmp_path: Path, monkeypatch
) -> None:
    class RecordingCollector:
        def __init__(self) -> None:
            self.paths: list[str] = []

        def get_json(self, source: str, relative_path: str, url: str, headers=None):
            self.paths.append(relative_path)
            return {
                "events": [
                    {"id": 1, "is_previous": True},
                    {"id": 2, "is_current": True},
                    {"id": 3, "is_next": True},
                ],
                "elements": [{"id": 17}],
            }

        def get(self, source: str, relative_path: str, url: str, headers=None):
            self.paths.append(relative_path)
            return b"response"

    collector = RecordingCollector()
    monkeypatch.setattr(cli, "RawCollector", lambda raw_root: collector)

    result = runner.invoke(
        cli.app, ["retrieve", "official-fpl", "--raw-root", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert collector.paths == [
        "bootstrap-static.json",
        "fixtures.json",
        "live_gameweeks/gw_01.json",
        "live_gameweeks/gw_02.json",
        "element_summaries/element_0017.json",
    ]


def test_alternative_group_dispatches_all_four_providers_and_uses_its_default_root(
    monkeypatch,
) -> None:
    calls: list[str] = []
    roots: list[Path] = []

    class RecordingCollector:
        def __init__(self, raw_root: Path) -> None:
            roots.append(raw_root)

    monkeypatch.setattr(cli, "RawCollector", RecordingCollector)
    provider_names = tuple(cli.ALTERNATIVE_PROVIDERS)
    for provider_name in provider_names:
        monkeypatch.setitem(
            cli.ALTERNATIVE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(name),
        )

    result = runner.invoke(cli.app, ["retrieve", "alternative-comps"])

    assert result.exit_code == 0, result.output
    assert calls == list(provider_names)
    assert roots == [cli.default_alternative_raw_root()]


def test_individual_alternative_commands_dispatch_all_four_providers(
    tmp_path: Path, monkeypatch
) -> None:
    for provider_name in tuple(cli.ALTERNATIVE_PROVIDERS):
        calls: list[str] = []
        monkeypatch.setitem(
            cli.ALTERNATIVE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(name),
        )

        result = runner.invoke(
            cli.app,
            ["retrieve", provider_name, "--raw-root", str(tmp_path)],
        )

        assert result.exit_code == 0, f"{provider_name}: {result.output}"
        assert calls == [provider_name]


def test_retrieve_all_keeps_core_and_alternative_raw_roots_distinct(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[str, str, Path]] = []

    class RecordingCollector:
        def __init__(self, raw_root: Path) -> None:
            self.raw_root = raw_root

    monkeypatch.setattr(cli, "RawCollector", RecordingCollector)
    for provider_name in tuple(cli.CORE_PROVIDERS):
        monkeypatch.setitem(
            cli.CORE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(
                ("core", name, collector.raw_root)
            ),
        )
    for provider_name in tuple(cli.ALTERNATIVE_PROVIDERS):
        monkeypatch.setitem(
            cli.ALTERNATIVE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(
                ("alternative", name, collector.raw_root)
            ),
        )
    core_root = tmp_path / "core"
    alternative_root = tmp_path / "alternative"

    result = runner.invoke(
        cli.app,
        [
            "retrieve",
            "all",
            "--core-raw-root",
            str(core_root),
            "--alternative-raw-root",
            str(alternative_root),
        ],
    )

    assert result.exit_code == 0, result.output
    assert len(calls) == len(cli.CORE_PROVIDERS) + len(cli.ALTERNATIVE_PROVIDERS)
    assert {root for group, _, root in calls if group == "core"} == {core_root}
    assert {root for group, _, root in calls if group == "alternative"} == {alternative_root}


def test_alternative_provider_failure_does_not_stop_later_providers(monkeypatch) -> None:
    calls: list[str] = []
    provider_names = tuple(cli.ALTERNATIVE_PROVIDERS)

    def fail(collector, options):
        calls.append(provider_names[0])
        raise RuntimeError("mock failure")

    monkeypatch.setitem(cli.ALTERNATIVE_PROVIDERS, provider_names[0], fail)
    for provider_name in provider_names[1:]:
        monkeypatch.setitem(
            cli.ALTERNATIVE_PROVIDERS,
            provider_name,
            lambda collector, options, name=provider_name: calls.append(name),
        )

    result = runner.invoke(cli.app, ["retrieve", "alternative-comps", "--raw-root", "."])

    assert result.exit_code == 1
    assert calls == list(provider_names)
    assert "collector failed for" in result.output


def test_data_tools_runner_forwards_typer_arguments_without_running_docker(
    tmp_path: Path, monkeypatch
) -> None:
    calls: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[object]:
        calls.append((command, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(compose_runner.subprocess, "run", fake_run)
    typer_arguments = ["retrieve", "openfootball", "--raw-root", "custom/raw root"]

    exit_code = compose_runner.run_data_tools(typer_arguments, project_root=tmp_path)

    assert exit_code == 0
    assert calls == [
        (
            [
                "docker",
                "compose",
                "--file",
                str(tmp_path / "compose.yaml"),
                "--project-directory",
                str(tmp_path),
                "--profile",
                "one-shot",
                "run",
                "--build",
                "--rm",
                "--no-deps",
                "data-tools",
                *typer_arguments,
            ],
            False,
        )
    ]


def test_data_tools_ingestion_runs_as_root(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[list[str], bool]] = []

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[object]:
        calls.append((command, check))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(compose_runner.subprocess, "run", fake_run)
    typer_arguments = ["ingest", "official-fpl-teams"]

    exit_code = compose_runner.run_data_tools(typer_arguments, project_root=tmp_path)

    assert exit_code == 0
    assert calls == [
        (
            [
                "docker",
                "compose",
                "--file",
                str(tmp_path / "compose.yaml"),
                "--project-directory",
                str(tmp_path),
                "--profile",
                "one-shot",
                "run",
                "--build",
                "--rm",
                "--no-deps",
                "--user",
                "0:0",
                "data-tools",
                *typer_arguments,
            ],
            False,
        )
    ]


def test_canonical_ingestion_uses_root_for_existing_volume_ownership(tmp_path: Path):
    command = compose_runner.build_compose_command(
        ["ingest", "canonical-teams", "--season", "2026-27"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


def test_schema_installation_uses_root_for_existing_volume_ownership(tmp_path: Path):
    command = compose_runner.build_compose_command(
        ["ingest", "canonical-schema"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


def test_canonical_players_ingestion_uses_root_for_existing_volume_ownership(tmp_path: Path):
    command = compose_runner.build_compose_command(
        ["ingest", "canonical-players", "--season", "2026-27"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


def test_canonical_archive_players_uses_root_for_existing_volume_ownership(tmp_path: Path):
    command = compose_runner.build_compose_command(
        ["ingest", "canonical-archive-players", "--season", "2025-26"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


def test_data_tools_compose_service_is_one_shot_and_mounts_checkout_and_named_volume() -> None:
    compose_file = Path(__file__).resolve().parents[1] / "compose.yaml"
    services = yaml.safe_load(compose_file.read_text(encoding="utf-8"))["services"]
    data_tools = services["data-tools"]

    assert data_tools["build"]["dockerfile"] == "backend/Dockerfile"
    assert data_tools["entrypoint"] == ["python", "-m", "tools.data_pipeline"]
    assert data_tools["profiles"] == ["one-shot"]
    assert data_tools["restart"] == "no"
    assert any(
        mount.get("type") == "bind"
        and mount.get("source") == "."
        and mount.get("target") == "/workspace"
        for mount in data_tools["volumes"]
        if isinstance(mount, dict)
    )
    assert "fplpatternrec-sqlite:/data" in data_tools["volumes"]
    assert "depends_on" not in data_tools


def test_official_fpl_teams_command_forwards_raw_root_and_season(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, Path, str | None]] = []

    def fake_load(bootstrap_path: Path, database_path: Path, season: str | None):
        calls.append((bootstrap_path, database_path, season))
        return cli.OfficialFplTeamsLoadSummary(season="2027-28", team_count=20)

    monkeypatch.setattr(cli, "load_official_fpl_teams", fake_load)
    raw_root = tmp_path / "custom raw root"

    result = runner.invoke(
        cli.app,
        [
            "ingest",
            "official-fpl-teams",
            "--raw-root",
            str(raw_root),
            "--season",
            "2027-28",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        (raw_root / "official_fpl_api" / "bootstrap-static.json", cli.DATABASE_PATH, "2027-28")
    ]
    assert "Loaded 20 official FPL teams for 2027-28." in result.output


def test_official_fpl_teams_command_uses_core_raw_root_by_default(monkeypatch) -> None:
    calls: list[tuple[Path, Path, str | None]] = []

    def fake_load(bootstrap_path: Path, database_path: Path, season: str | None):
        calls.append((bootstrap_path, database_path, season))
        return cli.OfficialFplTeamsLoadSummary(season="2026-27", team_count=20)

    monkeypatch.setattr(cli, "load_official_fpl_teams", fake_load)

    result = runner.invoke(cli.app, ["ingest", "official-fpl-teams"])

    assert result.exit_code == 0, result.output
    assert calls == [
        (
            cli.default_core_raw_root() / "official_fpl_api" / "bootstrap-static.json",
            cli.DATABASE_PATH,
            None,
        )
    ]


def test_canonical_teams_command_forwards_explicit_season_and_reference(monkeypatch, tmp_path):
    calls: list[tuple[str, Path, Path]] = []

    def fake_load(season: str, database_path: Path, reference_path: Path):
        calls.append((season, database_path, reference_path))
        return CanonicalTeamsLoadSummary(season, 51, 20)

    monkeypatch.setattr(cli, "load_canonical_teams", fake_load)
    reference = tmp_path / "reference.json"
    result = runner.invoke(cli.app, [
        "ingest", "canonical-teams", "--season", "2026-27", "--team-reference", str(reference),
    ])

    assert result.exit_code == 0, result.output
    assert calls == [("2026-27", cli.DATABASE_PATH, reference)]
    assert "mapped 20 FPL teams for 2026-27" in result.output


def test_canonical_teams_command_seeds_without_season_and_defaults_reference(monkeypatch):
    calls: list[tuple[str | None, Path, Path]] = []

    def fake_load(season: str | None, database_path: Path, reference_path: Path):
        calls.append((season, database_path, reference_path))
        return CanonicalTeamsLoadSummary(season, 51, 0)

    monkeypatch.setattr(cli, "load_canonical_teams", fake_load)
    result = runner.invoke(cli.app, ["ingest", "canonical-teams"])

    assert result.exit_code == 0, result.output
    assert calls == [(None, cli.DATABASE_PATH, cli.TEAM_REFERENCE_PATH)]
    assert "Loaded 51 reviewed clubs from the team reference." in result.output


def test_canonical_schema_command_forwards_database_path(monkeypatch):
    calls: list[Path] = []
    monkeypatch.setattr(cli, "install_canonical_schema", lambda path: calls.append(path))

    result = runner.invoke(cli.app, ["ingest", "canonical-schema"])

    assert result.exit_code == 0, result.output
    assert calls == [cli.DATABASE_PATH]


def test_canonical_players_command_requires_season_and_forwards_saved_bootstrap(monkeypatch, tmp_path):
    calls: list[tuple[str, Path, Path]] = []

    def fake_load(season: str, bootstrap_path: Path, database_path: Path):
        calls.append((season, bootstrap_path, database_path))
        return CanonicalPlayersLoadSummary(season, 667, 0)

    monkeypatch.setattr(cli, "load_canonical_players", fake_load)
    assert runner.invoke(cli.app, ["ingest", "canonical-players"]).exit_code != 0
    assert calls == []
    result = runner.invoke(cli.app, [
        "ingest", "canonical-players", "--season", "2026-27", "--raw-root", str(tmp_path),
    ])

    assert result.exit_code == 0, result.output
    assert calls == [("2026-27", tmp_path / "official_fpl_api/bootstrap-static.json", cli.DATABASE_PATH)]
    assert "Resolved 667 FPL players for 2026-27" in result.output


def test_canonical_archive_players_command_forwards_explicit_season(monkeypatch, tmp_path):
    calls: list[tuple[str, Path, Path, Path]] = []

    def fake_load(season: str, players: Path, idlist: Path, database: Path):
        calls.append((season, players, idlist, database))
        return ArchivePlayersLoadSummary(season, 841, 480, 361, 0)

    monkeypatch.setattr(cli, "load_archive_players", fake_load)
    assert runner.invoke(cli.app, ["ingest", "canonical-archive-players"]).exit_code != 0
    assert calls == []
    result = runner.invoke(cli.app, [
        "ingest", "canonical-archive-players", "--season", "2025-26", "--raw-root", str(tmp_path),
    ])

    assert result.exit_code == 0, result.output
    archive = tmp_path / "fpl_archive_vaastav/2025-26"
    assert calls == [("2025-26", archive / "players_raw.csv", archive / "player_idlist.csv", cli.DATABASE_PATH)]
    assert "480 linked to later seasons, 361 archive-only" in result.output
