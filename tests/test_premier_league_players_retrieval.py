from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tools.data_pipeline.retrieval.premier_league import _pl_headers
from tools.data_pipeline.retrieval.premier_league_players import (
    collect_premier_league_players,
)


class RecordingCollector:
    def __init__(self, raw_root: Path, responses: dict[str, object]) -> None:
        self.raw_root = raw_root
        self.responses = responses
        self.calls: list[tuple[str, str, str, dict[str, str] | None]] = []

    def get_json(
        self,
        source: str,
        relative_path: str,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> object:
        self.calls.append((source, relative_path, url, headers))
        response = self.responses.get(relative_path)
        if response is not None:
            target = self.raw_root / source / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(response), encoding="utf-8")
        return response


def _write_seasons(raw_root: Path, seasons: list[dict[str, object]]) -> None:
    path = raw_root / "premier_league_api" / "competition_seasons.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"content": seasons}), encoding="utf-8")


def _page(page: int, num_pages: int, num_entries: int, content: list[object]) -> dict[str, object]:
    return {
        "pageInfo": {
            "page": page,
            "numPages": num_pages,
            "pageSize": 100,
            "numEntries": num_entries,
        },
        "content": content,
    }


def test_collects_saved_rosters_with_expected_season_slugs_and_pagination(
    tmp_path: Path,
) -> None:
    _write_seasons(
        tmp_path,
        [
            {"label": "2015/16", "id": 42},
            {"label": "2016/17", "id": 54},
            {"label": "English Premier League Season 2026/2027", "id": 841.0},
        ],
    )
    owner_record = {
        "id": 12345,
        "name": {"display": "Owner Record"},
        "birth": {"date": {"millis": 946684800000, "label": "01 Jan 2000"}},
        "altIds": {"opta": "p12345"},
    }
    first_page = [owner_record] + [{"id": player_id} for player_id in range(2, 101)]
    responses = {
        "players/2016-17/page-000.json": _page(0, 2, 101, first_page),
        "players/2016-17/page-001.json": _page(1, 2, 101, [{"id": 101}]),
        "players/2026-27/page-000.json": _page(0, 1, 1, [owner_record]),
    }
    collector = RecordingCollector(tmp_path, responses)

    collect_premier_league_players(collector)  # type: ignore[arg-type]

    assert [path for _, path, _, _ in collector.calls] == list(responses)
    for source, path, url, headers in collector.calls:
        assert source == "premier_league_api"
        assert headers == _pl_headers()
        parsed = urlsplit(url)
        assert parsed.netloc == "footballapi.pulselive.com"
        assert parsed.path == "/football/players"
        query = parse_qs(parsed.query)
        expected_season_id = "54" if path.startswith("players/2016-17/") else "841"
        assert query == {
            "comp": ["1"],
            "compSeasons": [expected_season_id],
            "altIds": ["true"],
            "page": [str(int(path[-8:-5]))],
            "pageSize": ["100"],
        }

    saved = json.loads(
        (tmp_path / "premier_league_api" / "players/2016-17/page-000.json").read_text(
            encoding="utf-8"
        )
    )
    assert saved["content"][0] == owner_record
    assert [path for _, path, _, _ in collector.calls] == [
        "players/2016-17/page-000.json",
        "players/2016-17/page-001.json",
        "players/2026-27/page-000.json",
    ]


def test_unavailable_roster_page_fails_without_replacing_its_saved_file(tmp_path: Path) -> None:
    _write_seasons(tmp_path, [{"label": "2016/17", "id": 54}])
    existing_path = tmp_path / "premier_league_api" / "players/2016-17/page-001.json"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    original = b"previous complete page"
    existing_path.write_bytes(original)
    collector = RecordingCollector(
        tmp_path,
        {"players/2016-17/page-000.json": _page(0, 2, 101, [{"id": 1}] * 100)},
    )

    with pytest.raises(RuntimeError, match="page-001.json is unavailable"):
        collect_premier_league_players(collector)  # type: ignore[arg-type]

    assert existing_path.read_bytes() == original
    assert [path for _, path, _, _ in collector.calls] == [
        "players/2016-17/page-000.json",
        "players/2016-17/page-001.json",
    ]


@pytest.mark.parametrize(
    ("second_page", "message"),
    [
        (_page(0, 2, 101, [{"id": 101}]), "page index mismatch"),
        (_page(1, 3, 201, [{"id": 101}]), "pageInfo changed between pages"),
    ],
)
def test_inconsistent_roster_pagination_fails_closed(
    tmp_path: Path, second_page: dict[str, object], message: str
) -> None:
    _write_seasons(tmp_path, [{"label": "2016/17", "id": 54}])
    collector = RecordingCollector(
        tmp_path,
        {
            "players/2016-17/page-000.json": _page(0, 2, 101, [{"id": 1}] * 100),
            "players/2016-17/page-001.json": second_page,
        },
    )

    with pytest.raises(RuntimeError, match=message):
        collect_premier_league_players(collector)  # type: ignore[arg-type]


def test_api_overstated_total_accepts_short_final_data_then_empty_page(tmp_path: Path) -> None:
    _write_seasons(tmp_path, [{"label": "2016/17", "id": 54}])
    collector = RecordingCollector(tmp_path, {
        "players/2016-17/page-000.json": _page(0, 3, 225, [{"id": i} for i in range(100)]),
        "players/2016-17/page-001.json": _page(1, 3, 225, [{"id": 100}]),
        "players/2016-17/page-002.json": _page(2, 3, 225, []),
    })
    collect_premier_league_players(collector)  # type: ignore[arg-type]
    assert len(collector.calls) == 3


def test_short_page_cannot_hide_later_data(tmp_path: Path) -> None:
    _write_seasons(tmp_path, [{"label": "2016/17", "id": 54}])
    collector = RecordingCollector(tmp_path, {
        "players/2016-17/page-000.json": _page(0, 2, 101, [{"id": 1}]),
        "players/2016-17/page-001.json": _page(1, 2, 101, [{"id": 101}]),
    })
    with pytest.raises(RuntimeError, match="data after a short page"):
        collect_premier_league_players(collector)  # type: ignore[arg-type]
