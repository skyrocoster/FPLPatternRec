from __future__ import annotations

import json

from src.tools import full_test_process
from src.tools.full_test_process import Step, StepResult


def _step(name: str) -> Step:
    return Step(name, ("fake", name), 10)


def test_inventory_covers_retained_tests_build_and_quality_layers() -> None:
    steps = full_test_process.build_steps()
    names = [step.name for step in steps]

    assert names == [
        "Compose configuration",
        "Python dependency integrity",
        "Node dependency integrity",
        "Source size limits",
        "Ruff lint",
        "Ruff formatting",
        "Prettier formatting",
        "ESLint",
        "TypeScript",
        "Python backend and repository tests",
        "Frontend unit tests",
        "Development service preflight",
        "Frontend real-backend API tests",
        "Frontend production build",
        "Storybook browser tests",
        "Storybook production build",
        "Playwright end-to-end tests",
    ]
    python_tests = steps[names.index("Python backend and repository tests")]
    assert "--maxfail=1" in python_tests.command
    assert python_tests.environment == {"PYTHONWARNINGS": "error"}
    assert python_tests.timeout_seconds > 0
    assert "--max-warnings" in steps[names.index("ESLint")].command
    assert "--max-failures=1" in steps[names.index("Playwright end-to-end tests")].command


def test_warning_output_fails_a_successful_process() -> None:
    step = _step("Example")

    result = full_test_process.classify_result(step, 0, "build warnings: chunk is large", "")

    assert result.passed is False
    assert result.reason.startswith("warning output:")


def test_documented_zero_and_engine_warning_lines_are_ignored() -> None:
    output = "0 warnings\nnpm warn EBADENGINE Unsupported engine\n"

    assert full_test_process.warning_lines(output, "") == []


def test_suite_stops_at_failure_and_resumes_at_that_check(tmp_path, monkeypatch) -> None:
    steps = [_step("first"), _step("second"), _step("third")]
    state_directory = tmp_path / "state"
    monkeypatch.setattr(full_test_process, "STATE_DIRECTORY", state_directory)
    monkeypatch.setattr(full_test_process, "STATE_PATH", state_directory / "state.json")
    monkeypatch.setattr(
        full_test_process,
        "FAILURE_LOG_PATH",
        state_directory / "latest-failure.log",
    )
    first_calls: list[str] = []

    def fail_second(step: Step) -> StepResult:
        first_calls.append(step.name)
        return StepResult(step.name != "second", "test result")

    monkeypatch.setattr(full_test_process, "execute_step", fail_second)

    assert full_test_process.run_suite(steps, 0) == 1
    assert first_calls == ["first", "second"]
    state = json.loads(full_test_process.STATE_PATH.read_text(encoding="utf-8"))
    assert state["next_step"] == "second"
    assert full_test_process._load_resume_index(steps) == 1

    resumed_calls: list[str] = []
    monkeypatch.setattr(
        full_test_process,
        "execute_step",
        lambda step: resumed_calls.append(step.name) or StepResult(True, "test result"),
    )

    assert full_test_process.run_suite(steps, full_test_process._load_resume_index(steps)) == 0
    assert resumed_calls == ["second", "third"]
    assert not full_test_process.STATE_PATH.exists()


def test_from_step_requires_one_unambiguous_match() -> None:
    steps = [_step("Ruff lint"), _step("Ruff formatting"), _step("ESLint")]

    assert full_test_process._matching_index(steps, "Ruff lint") == 0
    assert full_test_process._matching_index(steps, "format") == 1

    try:
        full_test_process._matching_index(steps, "Ruff")
    except ValueError as error:
        assert "exactly one" in str(error)
    else:
        raise AssertionError("ambiguous names must fail")
