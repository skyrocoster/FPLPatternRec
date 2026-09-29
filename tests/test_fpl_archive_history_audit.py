"""Saved-file evidence required for matching FPL codes across all available seasons."""

import csv
from collections import defaultdict
import json
from pathlib import Path

import pytest

from tools.data_pipeline.ingestion.archive_players import _normalize

ROOT = Path(__file__).resolve().parents[1] / "data/raw"
SEASONS = [f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027)]
COUNTS = {
    "2016-17": (683, 683, 0, 683), "2017-18": (647, 647, 0, 647),
    "2018-19": (624, 624, 0, 624), "2019-20": (666, 666, 0, 666),
    "2020-21": (713, 713, 0, 713), "2021-22": (737, 737, 0, 737),
    "2022-23": (778, 778, 0, 778), "2023-24": (865, 865, 0, 865),
    "2024-25": (804, 784, 20, 162), "2025-26": (841, 841, 0, 19),
    "2026-27": (616, 616, 0, 16),
}
REVIEWED_SAME_NAME_PAIRS = {
    frozenset(pair) for pair in (
        ("41792", "447715"), ("78007", "577725"), ("112139", "613232"),
        ("115556", "152898"), ("75826", "95463"), ("240796", "515501"),
        ("490098", "465390"),
    )
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def test_saved_fpl_identity_evidence_through_2026_27() -> None:
    if not (ROOT / "fpl_archive_vaastav/2016-17/players_raw.csv").is_file():
        pytest.skip("Saved FPL archive unavailable")
    by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    name_codes: dict[str, set[str]] = defaultdict(set)
    for season in SEASONS:
        folder = ROOT / "fpl_archive_vaastav" / season
        rows = _read_csv(folder / "players_raw.csv")
        idlist = _read_csv(folder / "player_idlist.csv")
        names_by_id = {row["id"]: (row["first_name"], row["second_name"]) for row in idlist}
        players = [row for row in rows if row["element_type"] in {"1", "2", "3", "4"}]
        managers = len(rows) - len(players)
        assert (len(rows), len(players), managers,
                sum(row.get("birth_date") in (None, "", "None") for row in players)) == COUNTS[season]
        assert len({row["code"] for row in rows}) == len({row["id"] for row in rows}) == len(rows)
        assert len(names_by_id) == len(rows)
        assert all(names_by_id[row["id"]] == (row["first_name"], row["second_name"]) for row in rows)
        assert all(row.get("has_temporary_code", "False") == "False" for row in rows)
        assert all(row["first_name"].strip() and row["second_name"].strip() for row in players)
        if season == "2024-25":
            assert {row["element_type"] for row in rows if row["element_type"] not in {"1", "2", "3", "4"}} == {"5"}
        for row in players:
            by_code[row["code"]].append(row)
            name_codes[_normalize(row["first_name"] + " " + row["second_name"])].add(row["code"])

    assert len(by_code) == 2723
    assert {frozenset(codes) for codes in name_codes.values() if len(codes) > 1} == REVIEWED_SAME_NAME_PAIRS
    for code, records in by_code.items():
        dates = {row["birth_date"] for row in records if row.get("birth_date") not in (None, "", "None")}
        assert len(dates) <= 1, code
        if len(records) > 1:
            names = [
                {part for part in _normalize(row["first_name"] + " " + row["second_name"]).split()
                 if len(part) > 2 and part not in {"and", "dos", "das", "the"}}
                for row in records
            ]
            assert set.intersection(*names), code

    bootstrap = ROOT / "official_fpl_api/bootstrap-static.json"
    if bootstrap.is_file():
        current = json.loads(bootstrap.read_text(encoding="utf-8"))["elements"]
        assert len({str(row["code"]) for row in current} | set(by_code)) == 2758
        current_codes = {str(row["code"]): row for row in current}
        saved_current = _read_csv(ROOT / "fpl_archive_vaastav/2026-27/players_raw.csv")
        assert {row["code"] for row in saved_current} <= set(current_codes)
        assert all(row["id"] == str(current_codes[row["code"]]["id"]) for row in saved_current)
