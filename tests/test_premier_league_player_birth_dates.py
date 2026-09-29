from __future__ import annotations

import csv
from datetime import UTC, datetime
import gzip
import json
from pathlib import Path

import pytest

from tools.data_pipeline.ingestion.premier_league_player_birth_dates import (
    PremierLeagueBirthDatesError,
    roster_birth_dates,
)

_ARCHIVE_SEASONS = tuple(f"{year}-{(year + 1) % 100:02d}" for year in range(2016, 2027))
_ARCHIVE_FIELDS = ["code", "first_name", "second_name", "web_name", "element_type"]


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _player(pl_id: int, name: str, dob: str) -> dict[str, object]:
    date_value = datetime.strptime(dob, "%Y-%m-%d").replace(tzinfo=UTC)
    return {
        "id": pl_id,
        "name": {"display": name},
        "birth": {
            "date": {
                "millis": int(date_value.timestamp() * 1000),
                "label": date_value.strftime("%d %B %Y"),
            }
        },
    }


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


def _write_seasons(raw_root: Path, season_slugs: list[str]) -> None:
    path = raw_root / "premier_league_api" / "competition_seasons.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    seasons = []
    for index, slug in enumerate(season_slugs):
        start = int(slug[:4])
        seasons.append({"id": index + 1, "label": f"{start}/{start + 1}"})
    path.write_text(json.dumps({"content": seasons}), encoding="utf-8")
    for season in _ARCHIVE_SEASONS:
        _write_archive_rows(raw_root, season, [])


def _write_archive_rows(
    raw_root: Path,
    season: str,
    rows: list[tuple[str, str, str, str, str]],
) -> None:
    path = raw_root / "fpl_archive_vaastav" / season / "players_raw.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_ARCHIVE_FIELDS)
        writer.writerows(rows)


def _write_rosters(raw_root: Path, seasons: dict[str, list[object]]) -> None:
    _write_seasons(raw_root, list(seasons))
    for season, players in seasons.items():
        path = raw_root / "premier_league_api" / "players" / season / "page-000.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_page(0, 1, len(players), players)), encoding="utf-8")


def _candidate(
    raw_root: Path,
    *,
    people: dict[int, tuple[str, str | None]] | None = None,
    mappings: dict[tuple[str, str], int] | None = None,
) -> dict[int, str]:
    return roster_birth_dates(
        raw_root,
        people or {1: ("Alice Example", None)},
        mappings or {("premier-league:2016-17", "101"): 1},
        _normalize,
    )


def test_returns_candidate_for_unique_same_season_fpl_roster_name(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "  ALICE   EXAMPLE ", "2000-01-02")]})

    assert _candidate(tmp_path) == {1: "2000-01-02"}


def test_alternate_fpl_label_matches_romelu_lukaku(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Romelu Lukaku", "1993-05-13")]})
    _write_archive_rows(
        tmp_path,
        "2016-17",
        [("183", "Romelu", "Lukaku Bolingoli", "Lukaku", "4")],
    )

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None)},
        mappings={("premier-league:2016-17", "183"): 1},
    ) == {1: "1993-05-13"}


def test_alias_collision_with_another_canonical_name_is_ambiguous(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Romelu Lukaku", "1993-05-13")]})
    _write_archive_rows(
        tmp_path,
        "2016-17",
        [
            ("183", "Romelu", "Lukaku Bolingoli", "Lukaku", "4"),
            ("184", "Romelu", "Lukaku", "Lukaku", "4"),
        ],
    )

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None), 2: ("Romelu Lukaku", None)},
        mappings={
            ("premier-league:2016-17", "183"): 1,
            ("premier-league:2016-17", "184"): 2,
        },
    ) == {}


@pytest.mark.parametrize(
    ("alias_pl_id", "alias_dob"),
    [(72, "1993-05-13"), (71, "1993-05-14")],
)
def test_matching_full_and_alternate_labels_must_agree_on_id_and_dob(
    tmp_path: Path, alias_pl_id: int, alias_dob: str
) -> None:
    _write_rosters(
        tmp_path,
        {
            "2016-17": [
                _player(71, "Romelu Lukaku Bolingoli", "1993-05-13"),
                _player(alias_pl_id, "Romelu Lukaku", alias_dob),
            ]
        },
    )
    _write_archive_rows(
        tmp_path,
        "2016-17",
        [("183", "Romelu", "Lukaku Bolingoli", "Lukaku", "4")],
    )

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None)},
        mappings={("premier-league:2016-17", "183"): 1},
    ) == {}


def test_blank_web_name_keeps_the_canonical_route_and_is_ignored(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice Example", "2000-01-02")]})
    _write_archive_rows(tmp_path, "2016-17", [("101", "Alice", "Example", "", "3")])

    assert _candidate(tmp_path) == {1: "2000-01-02"}


def test_web_name_alone_does_not_create_an_alias(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice", "2000-01-02")]})
    _write_archive_rows(tmp_path, "2016-17", [("101", "Unrelated", "Player", "Alice", "3")])

    assert _candidate(tmp_path) == {}


def test_raw_full_name_must_match_before_an_alias_is_used(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Romelu Lukaku", "1993-05-13")]})
    _write_archive_rows(tmp_path, "2016-17", [("183", "Romelu", "Other Player", "Lukaku", "4")])

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None)},
        mappings={("premier-league:2016-17", "183"): 1},
    ) == {}


def test_alias_from_another_season_is_not_used(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2017-18": [_player(71, "Romelu Lukaku", "1993-05-13")]})
    _write_archive_rows(
        tmp_path,
        "2016-17",
        [("183", "Romelu", "Lukaku Bolingoli", "Lukaku", "4")],
    )

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None)},
        mappings={("premier-league:2017-18", "183"): 1},
    ) == {}


def test_single_conflicting_transfermarkt_dob_for_matched_alias_excludes_candidate(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Romelu Lukaku", "1993-05-13")]})
    _write_archive_rows(
        tmp_path,
        "2016-17",
        [("183", "Romelu", "Lukaku Bolingoli", "Lukaku", "4")],
    )
    _write_transfermarkt(tmp_path, [("301", "Romelu Lukaku", "1993-05-14 00:00:00")])

    assert _candidate(
        tmp_path,
        people={1: ("Romelu Lukaku Bolingoli", None)},
        mappings={("premier-league:2016-17", "183"): 1},
    ) == {}


def test_duplicate_canonical_names_are_not_candidates(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice Example", "2000-01-02")]})

    assert _candidate(
        tmp_path,
        people={1: ("Alice Example", None), 2: ("ALICE EXAMPLE", None)},
    ) == {}


def test_multiple_matching_premier_league_ids_in_one_season_are_ambiguous(tmp_path: Path) -> None:
    _write_rosters(
        tmp_path,
        {
            "2016-17": [
                _player(71, "Alice Example", "2000-01-02"),
                _player(72, "ALICE EXAMPLE", "2000-01-02"),
            ]
        },
    )

    assert _candidate(tmp_path) == {}


@pytest.mark.parametrize(
    ("second_pl_id", "second_dob"),
    [(72, "2000-01-02"), (71, "2001-02-03")],
)
def test_discordant_ids_or_dates_across_mapped_seasons_are_excluded(
    tmp_path: Path, second_pl_id: int, second_dob: str
) -> None:
    _write_rosters(
        tmp_path,
        {
            "2016-17": [_player(71, "Alice Example", "2000-01-02")],
            "2017-18": [_player(second_pl_id, "Alice Example", second_dob)],
        },
    )
    mappings = {
        ("premier-league:2016-17", "101"): 1,
        ("premier-league:2017-18", "202"): 1,
    }

    assert _candidate(tmp_path, mappings=mappings) == {}


def test_single_conflicting_transfermarkt_dob_excludes_candidate(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice Example", "2000-01-02")]})
    _write_transfermarkt(tmp_path, [("301", "Alice Example", "2000-01-03 00:00:00")])

    assert _candidate(tmp_path) == {}


def test_multiple_transfermarkt_name_matches_do_not_establish_conflict(tmp_path: Path) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice Example", "2000-01-02")]})
    _write_transfermarkt(
        tmp_path,
        [
            ("301", "Alice Example", "2000-01-03 00:00:00"),
            ("302", "ALICE EXAMPLE", "2000-01-02 00:00:00"),
        ],
    )

    assert _candidate(tmp_path) == {1: "2000-01-02"}


def test_missing_page_fails_closed(tmp_path: Path) -> None:
    _write_seasons(tmp_path, ["2016-17"])
    page_path = tmp_path / "premier_league_api" / "players" / "2016-17" / "page-000.json"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        json.dumps(_page(0, 2, 101, [_player(71, "Alice Example", "2000-01-02")])),
        encoding="utf-8",
    )

    with pytest.raises(PremierLeagueBirthDatesError, match="pages do not match pageInfo"):
        _candidate(tmp_path)


def test_absent_roster_folder_returns_no_candidates(tmp_path: Path) -> None:
    assert _candidate(tmp_path) == {}


@pytest.mark.parametrize("failure", ["missing", "incomplete"])
def test_missing_or_incomplete_fpl_archive_fails_closed_with_roster_folder(
    tmp_path: Path, failure: str
) -> None:
    _write_rosters(tmp_path, {"2016-17": [_player(71, "Alice Example", "2000-01-02")]})
    path = tmp_path / "fpl_archive_vaastav" / "2016-17" / "players_raw.csv"
    if failure == "missing":
        path.unlink()
    else:
        path.write_text("code,first_name\n101,Alice\n", encoding="utf-8")

    with pytest.raises(PremierLeagueBirthDatesError, match="saved FPL archive"):
        _candidate(tmp_path)


def test_short_data_page_followed_by_empty_page_is_accepted(tmp_path: Path) -> None:
    _write_seasons(tmp_path, ["2016-17"])
    season_root = tmp_path / "premier_league_api" / "players" / "2016-17"
    season_root.mkdir(parents=True)
    (season_root / "page-000.json").write_text(
        json.dumps(_page(0, 2, 101, [_player(71, "Alice Example", "2000-01-02")])),
        encoding="utf-8",
    )
    (season_root / "page-001.json").write_text(
        json.dumps(_page(1, 2, 101, [])),
        encoding="utf-8",
    )

    assert _candidate(tmp_path) == {1: "2000-01-02"}


def _write_transfermarkt(raw_root: Path, rows: list[tuple[str, str, str]]) -> None:
    path = raw_root / "transfermarkt_datasets" / "players.csv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["player_id", "name", "date_of_birth"])
        writer.writerows(rows)
