from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tools.data_pipeline.retrieval.transfermarkt_datasets import (
    DATASET_BASE,
    PLAYER_FILES,
    collect_transfermarkt_datasets,
)
from tools.data_pipeline.retrieval.wikidata_players import ENDPOINTS, collect_wikidata_players
from tools.data_pipeline.retrieval.wikidata_transfermarkt import (
    BATCH_SIZE,
    ENDPOINTS as TRANSFERMARKT_WIKIDATA_ENDPOINTS,
    collect_wikidata_transfermarkt,
    collect_wikidata_transfermarkt_fpl,
    fpl_tm_ids,
)


class RecordingCollector:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.fail = fail

    def get(self, source: str, path: str, url: str) -> bytes | None:
        self.calls.append((source, path, url))
        return None if self.fail else b"published source bytes"

    def get_json(self, source: str, path: str, url: str, headers: dict[str, str]):
        self.calls.append((source, path, url))
        assert headers == {"Accept": "application/sparql-results+json"}
        return None if self.fail else {"results": {"bindings": [{"player": {}}]}}


def test_transfermarkt_downloads_only_relevant_published_csvs() -> None:
    collector = RecordingCollector()

    collect_transfermarkt_datasets(collector)

    assert collector.calls == [
        ("transfermarkt_datasets", filename, f"{DATASET_BASE}/{filename}")
        for filename in PLAYER_FILES
    ]


def test_wikidata_query_retains_identity_and_birth_date_precision() -> None:
    collector = RecordingCollector()

    collect_wikidata_players(collector)

    source, path, url = collector.calls[0]
    query = parse_qs(urlsplit(url).query)["query"][0]
    assert (source, path) == ("wikidata_players", "premier_league_club_players_dob.json")
    assert urlsplit(url).netloc == "query.wikidata.org"
    assert "?player ?name ?dob ?precision ?team" in query
    assert "wikibase:timePrecision ?precision" in query
    assert "?team wdt:P118 wd:Q9448" in query
    assert "1970-01-01" in query


def test_wikidata_retries_on_mirror_when_primary_is_unavailable() -> None:
    class FallbackCollector(RecordingCollector):
        def get_json(self, source: str, path: str, url: str, headers: dict[str, str]):
            self.calls.append((source, path, url))
            return None if len(self.calls) == 1 else {"results": {"bindings": [{"player": {}}]}}

    collector = FallbackCollector()
    collect_wikidata_players(collector)

    assert len(collector.calls) == 2
    assert [urlsplit(url).netloc for _, _, url in collector.calls] == [
        urlsplit(endpoint).netloc for endpoint in ENDPOINTS
    ]
    assert collector.calls[0][1] == collector.calls[1][1]


@pytest.mark.parametrize("collect", [collect_transfermarkt_datasets, collect_wikidata_players])
def test_missing_source_reports_failure(collect) -> None:
    with pytest.raises(RuntimeError, match="unavailable|did not return results"):
        collect(RecordingCollector(fail=True))


def _write_gzip_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_transfermarkt_fixtures(raw_root: Path, player_ids: list[str]) -> None:
    games_path = raw_root / "transfermarkt_datasets" / "games.csv.gz"
    appearances_path = raw_root / "transfermarkt_datasets" / "appearances.csv.gz"
    _write_gzip_csv(
        games_path,
        ["game_id", "competition_id"],
        [
            {"game_id": "pl-1", "competition_id": "GB1"},
            {"game_id": "cup-1", "competition_id": "DFB"},
        ],
    )
    appearances = [
        {"player_id": "90", "game_id": "pl-1", "minutes_played": "0"},
        {"player_id": "91", "game_id": "cup-1", "minutes_played": "90"},
    ]
    appearances.extend(
        {"player_id": player_id, "game_id": "pl-1", "minutes_played": "1"}
        for player_id in player_ids
    )
    _write_gzip_csv(
        appearances_path,
        ["player_id", "game_id", "minutes_played"],
        appearances,
    )


class FixtureWikidataCollector:
    def __init__(self, raw_root: Path, responses: list[object]) -> None:
        self.raw_root = raw_root
        self.responses = iter(responses)
        self.calls: list[tuple[str, str, str, dict[str, str]]] = []

    def get_json(self, source: str, path: str, url: str, headers: dict[str, str]):
        self.calls.append((source, path, url, headers))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


def test_wikidata_transfermarkt_queries_sorted_positive_minute_gb1_ids_and_precision(
    tmp_path: Path,
) -> None:
    _write_transfermarkt_fixtures(tmp_path, ["22", "3", "22"])
    collector = FixtureWikidataCollector(
        tmp_path,
        [
            {
                "results": {
                    "bindings": [
                        {
                            "player": {"value": "http://www.wikidata.org/entity/Q1"},
                            "tmId": {"value": "3"},
                            "dob": {"value": "2000-01-02T00:00:00Z"},
                            "precision": {"value": "11"},
                        }
                    ]
                }
            }
        ],
    )

    collect_wikidata_transfermarkt(collector)

    assert len(collector.calls) == 1
    source, path, url, headers = collector.calls[0]
    query = parse_qs(urlsplit(url).query)["query"][0]
    assert (source, path) == ("wikidata_transfermarkt", "batch-000.json")
    assert urlsplit(url).netloc == "qlever.cs.uni-freiburg.de"
    assert headers == {"Accept": "application/sparql-results+json"}
    assert 'VALUES ?tmId { "3" "22" }' in query
    assert "SELECT DISTINCT ?player ?tmId ?dob ?precision" in query
    assert "wdt:P2446 ?tmId" in query
    assert "p:P569/psv:P569 ?birthDate" in query
    assert "wikibase:timePrecision ?precision" in query


def test_wikidata_transfermarkt_uses_deterministic_75_id_batches_and_accepts_empty_results(
    tmp_path: Path,
) -> None:
    player_ids = [str(player_id) for player_id in range(1, BATCH_SIZE + 2)]
    _write_transfermarkt_fixtures(tmp_path, player_ids)
    collector = FixtureWikidataCollector(
        tmp_path,
        [
            {"results": {"bindings": []}},
            {"results": {"bindings": []}},
        ],
    )

    collect_wikidata_transfermarkt(collector)

    assert [path for _, path, _, _ in collector.calls] == ["batch-000.json", "batch-001.json"]
    first_query = parse_qs(urlsplit(collector.calls[0][2]).query)["query"][0]
    second_query = parse_qs(urlsplit(collector.calls[1][2]).query)["query"][0]
    assert first_query.count('"') // 2 == BATCH_SIZE
    assert 'VALUES ?tmId { "1" "2"' in first_query
    assert 'VALUES ?tmId { "76" }' in second_query


def test_wikidata_transfermarkt_falls_back_to_official_endpoint_for_invalid_bindings(
    tmp_path: Path,
) -> None:
    _write_transfermarkt_fixtures(tmp_path, ["5"])
    collector = FixtureWikidataCollector(
        tmp_path,
        [None, {"results": {"bindings": []}}],
    )

    collect_wikidata_transfermarkt(collector)

    assert len(collector.calls) == 2
    assert [urlsplit(url).netloc for _, _, url, _ in collector.calls] == [
        urlsplit(endpoint).netloc for endpoint in TRANSFERMARKT_WIKIDATA_ENDPOINTS
    ]
    assert collector.calls[0][1] == collector.calls[1][1] == "batch-000.json"


def test_wikidata_transfermarkt_requires_every_batch_to_return_bindings(tmp_path: Path) -> None:
    _write_transfermarkt_fixtures(tmp_path, ["5"])
    collector = FixtureWikidataCollector(tmp_path, [None, {"results": {"bindings": None}}])

    with pytest.raises(RuntimeError, match="batch 000 did not return valid bindings"):
        collect_wikidata_transfermarkt(collector)


@pytest.mark.parametrize("missing_file", ["games.csv.gz", "appearances.csv.gz"])
def test_wikidata_transfermarkt_fails_closed_when_saved_dataset_is_missing(
    tmp_path: Path, missing_file: str
) -> None:
    games_path = tmp_path / "transfermarkt_datasets" / "games.csv.gz"
    appearances_path = tmp_path / "transfermarkt_datasets" / "appearances.csv.gz"
    _write_gzip_csv(games_path, ["game_id", "competition_id"], [])
    _write_gzip_csv(appearances_path, ["player_id", "game_id", "minutes_played"], [])
    (tmp_path / "transfermarkt_datasets" / missing_file).unlink()
    collector = FixtureWikidataCollector(tmp_path, [])

    with pytest.raises(ValueError, match="Cannot read saved Transfermarkt dataset"):
        collect_wikidata_transfermarkt(collector)


def test_wikidata_transfermarkt_fails_closed_when_saved_schema_is_incomplete(tmp_path: Path) -> None:
    _write_gzip_csv(
        tmp_path / "transfermarkt_datasets" / "games.csv.gz",
        ["game_id"],
        [],
    )
    _write_gzip_csv(
        tmp_path / "transfermarkt_datasets" / "appearances.csv.gz",
        ["player_id", "game_id", "minutes_played"],
        [],
    )
    collector = FixtureWikidataCollector(tmp_path, [])

    with pytest.raises(ValueError, match="Missing required fields"):
        collect_wikidata_transfermarkt(collector)


FPL_ARCHIVE_SEASONS = [f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027)]


def _write_fpl_sources(
    raw_root: Path,
    archive_rows: dict[str, list[dict[str, str]]],
    bootstrap_players: list[dict[str, object]],
) -> None:
    fields = ["id", "element_type", "first_name", "second_name"]
    for season in FPL_ARCHIVE_SEASONS:
        path = raw_root / "fpl_archive_vaastav" / season / "players_raw.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(archive_rows.get(season, []))
    bootstrap_path = raw_root / "official_fpl_api" / "bootstrap-static.json"
    bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
    bootstrap_path.write_text(json.dumps({"elements": bootstrap_players}), encoding="utf-8")


def test_fpl_tm_ids_matches_archived_and_current_names_excluding_managers_and_duplicate_ids(
    tmp_path: Path,
) -> None:
    archive_rows = {
        season: [{"id": "100", "element_type": "3", "first_name": "José", "second_name": "O'Neil"}]
        for season in FPL_ARCHIVE_SEASONS
    }
    archive_rows[FPL_ARCHIVE_SEASONS[0]].extend(
        [
            {"id": "101", "element_type": "4", "first_name": "Kai", "second_name": "Old"},
            {"id": "102", "element_type": "5", "first_name": "Coach", "second_name": "Boss"},
        ]
    )
    _write_fpl_sources(
        tmp_path,
        archive_rows,
        [
            {"id": 103, "element_type": 3, "first_name": "Kái", "second_name": "New"},
            {"id": 104, "element_type": 5, "first_name": "Coach", "second_name": "Boss"},
        ],
    )
    _write_gzip_csv(
        tmp_path / "transfermarkt_datasets" / "players.csv.gz",
        ["player_id", "name"],
        [
            {"player_id": "20", "name": "JOSE O NEIL"},
            {"player_id": "20", "name": "José O'Neil"},
            {"player_id": "8", "name": "Kai Old"},
            {"player_id": "3", "name": "Kai New"},
            {"player_id": "5", "name": "Coach Boss"},
            {"player_id": "1", "name": "Unmatched Player"},
        ],
    )

    assert fpl_tm_ids(tmp_path) == ["3", "8", "20"]


def test_wikidata_transfermarkt_fpl_batches_sorted_matching_ids_and_saves_in_own_namespace(
    tmp_path: Path,
) -> None:
    archive_rows = {
        season: [{"id": "100", "element_type": "3", "first_name": "Archive", "second_name": "Player"}]
        for season in FPL_ARCHIVE_SEASONS
    }
    _write_fpl_sources(
        tmp_path,
        archive_rows,
        [{"id": 101, "element_type": 4, "first_name": "Current", "second_name": "Player"}],
    )
    _write_gzip_csv(
        tmp_path / "transfermarkt_datasets" / "players.csv.gz",
        ["player_id", "name"],
        [{"player_id": str(player_id), "name": "ARCHIVE PLAYER"} for player_id in range(1, BATCH_SIZE + 2)],
    )
    collector = FixtureWikidataCollector(
        tmp_path,
        [{"results": {"bindings": []}}, {"results": {"bindings": []}}],
    )

    collect_wikidata_transfermarkt_fpl(collector)

    assert [source for source, _, _, _ in collector.calls] == [
        "wikidata_transfermarkt_fpl",
        "wikidata_transfermarkt_fpl",
    ]
    assert [path for _, path, _, _ in collector.calls] == ["batch-000.json", "batch-001.json"]
    first_query = parse_qs(urlsplit(collector.calls[0][2]).query)["query"][0]
    second_query = parse_qs(urlsplit(collector.calls[1][2]).query)["query"][0]
    assert urlsplit(collector.calls[0][2]).netloc == "qlever.cs.uni-freiburg.de"
    assert first_query.count('"') // 2 == BATCH_SIZE
    assert 'VALUES ?tmId { "1" "2"' in first_query
    assert 'VALUES ?tmId { "76" }' in second_query
    assert "wikibase:timePrecision ?precision" in first_query


def test_wikidata_transfermarkt_fpl_falls_back_and_fails_if_batch_has_no_bindings(
    tmp_path: Path,
) -> None:
    archive_rows = {
        season: [{"id": "100", "element_type": "3", "first_name": "Archive", "second_name": "Player"}]
        for season in FPL_ARCHIVE_SEASONS
    }
    _write_fpl_sources(
        tmp_path,
        archive_rows,
        [{"id": 101, "element_type": 4, "first_name": "Current", "second_name": "Player"}],
    )
    _write_gzip_csv(
        tmp_path / "transfermarkt_datasets" / "players.csv.gz",
        ["player_id", "name"],
        [{"player_id": "7", "name": "Archive Player"}],
    )
    collector = FixtureWikidataCollector(
        tmp_path,
        [None, {"results": {"bindings": None}}],
    )

    with pytest.raises(RuntimeError, match="FPL Transfermarkt batch 000 did not return valid bindings"):
        collect_wikidata_transfermarkt_fpl(collector)

    assert [urlsplit(url).netloc for _, _, url, _ in collector.calls] == [
        urlsplit(endpoint).netloc for endpoint in TRANSFERMARKT_WIKIDATA_ENDPOINTS
    ]
    assert [path for _, path, _, _ in collector.calls] == ["batch-000.json", "batch-000.json"]


def test_fpl_tm_ids_fails_closed_when_a_required_archive_season_is_missing(tmp_path: Path) -> None:
    archive_rows = {
        season: [{"id": "100", "element_type": "3", "first_name": "Archive", "second_name": "Player"}]
        for season in FPL_ARCHIVE_SEASONS
    }
    _write_fpl_sources(
        tmp_path,
        archive_rows,
        [{"id": 101, "element_type": 4, "first_name": "Current", "second_name": "Player"}],
    )
    (tmp_path / "fpl_archive_vaastav" / FPL_ARCHIVE_SEASONS[-1] / "players_raw.csv").unlink()

    with pytest.raises(ValueError, match="Cannot read saved FPL source"):
        fpl_tm_ids(tmp_path)


def test_fpl_tm_ids_fails_closed_when_an_archive_schema_is_incomplete(tmp_path: Path) -> None:
    archive_rows = {
        season: [{"id": "100", "element_type": "3", "first_name": "Archive", "second_name": "Player"}]
        for season in FPL_ARCHIVE_SEASONS
    }
    _write_fpl_sources(
        tmp_path,
        archive_rows,
        [{"id": 101, "element_type": 4, "first_name": "Current", "second_name": "Player"}],
    )
    incomplete_source = (
        tmp_path / "fpl_archive_vaastav" / FPL_ARCHIVE_SEASONS[0] / "players_raw.csv"
    )
    incomplete_source.write_text("id,element_type,first_name\n100,3,Archive\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required fields in saved FPL source"):
        fpl_tm_ids(tmp_path)
