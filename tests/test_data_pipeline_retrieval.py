from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest

from tools.data_pipeline.retrieval import common
from tools.data_pipeline.retrieval.common import RawCollector
from tools.data_pipeline.retrieval.official_fpl import collect_fpl


class RecordingCollector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def get_json(self, source: str, relative_path: str, url: str, headers=None):
        self.calls.append(("json", relative_path, url))
        if relative_path == "bootstrap-static.json":
            return {
                "events": [
                    {"id": 1, "is_previous": True},
                    {"id": 2, "is_current": True},
                    {"id": 3, "is_next": True},
                ],
                "elements": [{"id": 17}, {"id": 29}, {"name": "missing id"}],
            }
        return None

    def get(self, source: str, relative_path: str, url: str, headers=None):
        self.calls.append(("raw", relative_path, url))
        return b"response"


class Response:
    status = 200
    headers = {}

    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_official_fpl_default_requests_bootstrap_fixtures_live_and_player_summaries() -> None:
    collector = RecordingCollector()

    collect_fpl(collector)

    paths = [path for _, path, _ in collector.calls]
    assert paths == [
        "bootstrap-static.json",
        "fixtures.json",
        "live_gameweeks/gw_01.json",
        "live_gameweeks/gw_02.json",
        "element_summaries/element_0017.json",
        "element_summaries/element_0029.json",
    ]


def test_official_fpl_optional_player_summary_control_keeps_bootstrap_fixtures_and_live() -> None:
    collector = RecordingCollector()

    collect_fpl(collector, include_player_summaries=False)

    assert [path for _, path, _ in collector.calls] == [
        "bootstrap-static.json",
        "fixtures.json",
        "live_gameweeks/gw_01.json",
        "live_gameweeks/gw_02.json",
    ]


def test_successful_refresh_atomically_replaces_only_the_matching_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "provider" / "payload.bin"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"previous response")
    monkeypatch.setattr(common, "urlopen", lambda request, timeout: Response(b"new\x00response"))
    collector = RawCollector(tmp_path)
    collector.host_intervals = {}

    result = collector.get("provider", "payload.bin", "https://example.test/payload")

    assert result == b"new\x00response"
    assert target.read_bytes() == b"new\x00response"
    assert list(target.parent.iterdir()) == [target]


def test_request_failure_keeps_existing_file_bytes_and_creates_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "provider" / "payload.bin"
    target.parent.mkdir(parents=True)
    original = b"exact previous bytes\x00"
    target.write_bytes(original)
    calls = 0

    def fail_request(request, timeout):
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, 404, "missing", None, BytesIO())

    monkeypatch.setattr(common, "urlopen", fail_request)
    collector = RawCollector(tmp_path)
    collector.host_intervals = {}

    assert collector.get("provider", "payload.bin", "https://example.test/payload") is None

    assert calls == 1
    assert target.read_bytes() == original
    assert list(target.parent.iterdir()) == [target]


def test_replace_failure_keeps_existing_file_bytes_and_cleans_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "provider" / "payload.bin"
    target.parent.mkdir(parents=True)
    original = b"exact previous bytes\x00"
    target.write_bytes(original)
    requests = 0

    def response(request, timeout):
        nonlocal requests
        requests += 1
        return Response(b"new complete response")

    def fail_replace(source, destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(common, "urlopen", response)
    monkeypatch.setattr(common.os, "replace", fail_replace)
    collector = RawCollector(tmp_path)
    collector.host_intervals = {}

    assert collector.get("provider", "payload.bin", "https://example.test/payload") is None

    assert requests == 1
    assert target.read_bytes() == original
    assert list(target.parent.iterdir()) == [target]
