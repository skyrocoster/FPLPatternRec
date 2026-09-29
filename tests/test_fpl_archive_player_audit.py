"""Evidence from saved FPL files for safe 2025-26 player identity resolution."""

import csv
import json
from collections import defaultdict
from pathlib import Path
import unicodedata

import pytest


ROOT = Path(__file__).resolve().parents[1] / "data/raw"


def _normalized(name: str) -> str:
    return "".join(
        character for character in unicodedata.normalize("NFKD", name.casefold())
        if not unicodedata.combining(character)
    )


def test_saved_2025_26_archive_identity_and_transfer_evidence() -> None:
    archive = ROOT / "fpl_archive_vaastav/2025-26"
    bootstrap = ROOT / "official_fpl_api/bootstrap-static.json"
    if not archive.is_dir() or not bootstrap.is_file():
        pytest.skip("Saved FPL snapshots unavailable")
    with (archive / "players_raw.csv").open(encoding="utf-8-sig", newline="") as stream:
        previous = list(csv.DictReader(stream))
    current = json.loads(bootstrap.read_text(encoding="utf-8"))["elements"]
    old = {str(row["code"]): row for row in previous}
    new = {str(row["code"]): row for row in current}
    shared = old.keys() & new.keys()
    differences = [
        (code, old[code]["first_name"], old[code]["second_name"], old[code]["birth_date"],
         new[code]["first_name"], new[code]["second_name"], new[code]["birth_date"])
        for code in sorted(shared)
        if (old[code]["first_name"], old[code]["second_name"], old[code]["birth_date"])
        != (new[code]["first_name"], new[code]["second_name"], new[code]["birth_date"])
    ]
    teams_by_element: dict[str, set[str]] = defaultdict(set)
    with (archive / "gws/merged_gw.csv").open(encoding="utf-8-sig", newline="") as stream:
        for gameweek in csv.DictReader(stream):
            teams_by_element[gameweek["element"]].add(gameweek["team"])
    moves = {element: teams for element, teams in teams_by_element.items() if len(teams) > 1}
    assert len(previous) == 841
    assert len(current) == 667
    assert len(shared) == 480
    assert len(old.keys() - new.keys()) == 361
    assert len(new.keys() - old.keys()) == 187
    assert len({row["id"] for row in previous}) == len(old) == len(previous)
    assert {row["element_type"] for row in previous} == {"1", "2", "3", "4"}
    assert sum(row["birth_date"] == "None" for row in previous) == 19
    assert all(row["opta_code"] == "p" + row["code"] for row in previous)
    assert len(differences) == 22
    assert all(
        old[code]["birth_date"] == new[code]["birth_date"]
        for code in shared
        if old[code]["birth_date"] not in ("", "None") and new[code]["birth_date"] is not None
    )
    missing_dob = [code for code in shared if old[code]["birth_date"] in ("", "None")
                   or new[code]["birth_date"] is None]
    assert len(missing_dob) == 14
    assert all(
        _normalized(old[code]["first_name"] + " " + old[code]["second_name"])
        == _normalized(new[code]["first_name"] + " " + new[code]["second_name"])
        for code in missing_dob
    ), [(code, old[code]["first_name"], old[code]["second_name"],
         new[code]["first_name"], new[code]["second_name"]) for code in missing_dob]
    assert len(moves) == 27
    assert moves["135"] == {"Brentford", "Newcastle"}
    assert moves["168"] == {"Brighton", "Chelsea", "Leeds"}
    with (archive / "teams.csv").open(encoding="utf-8-sig", newline="") as stream:
        team_names = {row["id"]: row["name"] for row in csv.DictReader(stream)}
    by_id = {row["id"]: row for row in previous}
    assert team_names[by_id["135"]["team"]] == "Newcastle"
    assert len(moves["135"]) > 1
    with (archive / "player_idlist.csv").open(encoding="utf-8-sig", newline="") as stream:
        idlist = {row["id"]: (row["first_name"], row["second_name"]) for row in csv.DictReader(stream)}
    assert len(idlist) == len(previous)
    assert all(idlist[row["id"]] == (row["first_name"], row["second_name"]) for row in previous)

    new_names = defaultdict(set)
    for code, row in new.items():
        new_names[_normalized(row["first_name"] + " " + row["second_name"])].add(code)
    unlinked_same_names = [
        (row["code"], new_names[_normalized(row["first_name"] + " " + row["second_name"])])
        for row in previous if row["code"] not in shared
        and _normalized(row["first_name"] + " " + row["second_name"]) in new_names
    ]
    assert not unlinked_same_names, unlinked_same_names
