"""A gameweek links a canonical player to the team FPL listed that week."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3

import pytest
from typer.testing import CliRunner

from tools.data_pipeline import cli, compose_runner
from tools.data_pipeline.ingestion.canonical_teams import TEAM_REFERENCE_PATH, _normalize, _read_clubs
from tools.data_pipeline.ingestion.player_gameweek_teams import (
    GameweekTeamsError, GameweekTeamsSummary, _observations, _source_teams, load_player_gameweek_teams,
)

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "data/raw/fpl_archive_vaastav"
PL_FIXTURES = ROOT / "data/raw/premier_league_api/fixtures"


def _write(path: Path, fields: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(fields)
        writer.writerows(rows)


def _setup(tmp_path: Path, season: str = "2025-26") -> tuple[Path, Path, Path]:
    database = tmp_path / "isolated.db"
    schema = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    scope = f"premier-league:{season}"
    with sqlite3.connect(database) as connection:
        connection.executescript(schema.read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        connection.execute("INSERT INTO players (display_name) VALUES ('Test Player')")
        connection.executemany(
            "INSERT INTO player_source_ids VALUES (?, ?, ?, 1)",
            [("fpl.element.id", scope, "10"), ("fpl.element.code", scope, "123")],
        )
    archive_root = tmp_path / "fpl_archive_vaastav"
    folder = archive_root / season
    if season not in {"2016-17", "2017-18", "2018-19"}:
        _write(folder / "teams.csv", ["id", "name"],
               [("1", "Arsenal"), ("2", "Aston Villa"), ("3", "Chelsea")])
    if season not in {"2016-17", "2017-18"}:
        _write(folder / "fixtures.csv", ["id", "team_h", "team_a"],
               [("1", "1", "2"), ("2", "2", "3")])
    _write(folder / "players_raw.csv", ["id", "code", "element_type"],
           [("10", "123", "3"), ("11", "987", "5")])
    return database, archive_root, folder


def _gameweeks(folder: Path, labelled: bool = True) -> None:
    year = folder.name[:4]
    fields = ["element", "fixture", "opponent_team", "was_home", "kickoff_time", "GW", "minutes"]
    rows = [
        ["10", "1", "2", "True", f"{year}-08-16T14:00:00Z", "1", "90"],
        ["10", "2", "2", "False", f"{year}-08-23T14:00:00Z", "2", "0"],
        ["11", "2", "2", "False", f"{year}-08-23T14:00:00Z", "2", "0"],
    ]
    if labelled:
        fields.append("team")
        for row, name in zip(rows, ("Arsenal", "Chelsea", "Chelsea")):
            row.append(name)
    _write(folder / "gws/merged_gw.csv", fields, [tuple(row) for row in rows])


def _state(database: Path):
    with sqlite3.connect(database) as connection:
        return (
            connection.execute("SELECT label FROM seasons ORDER BY label").fetchall(),
            connection.execute("SELECT gameweek_id, season_id, gameweek_number FROM gameweeks ORDER BY gameweek_number").fetchall(),
            connection.execute(
                "SELECT g.gameweek_number, t.team_key, p.source_element_id, "
                "p.fixture_observations, p.fixtures_with_minutes "
                "FROM player_gameweek_teams p JOIN gameweeks g USING (gameweek_id) "
                "JOIN teams t USING (team_id) ORDER BY g.gameweek_number, p.player_id"
            ).fetchall(),
            connection.execute("PRAGMA foreign_key_check").fetchall(),
        )


def test_gameweeks_and_transferred_player_are_linked_without_inventing_appearances(tmp_path: Path) -> None:
    database, archive_root, folder = _setup(tmp_path)
    _gameweeks(folder)
    first = load_player_gameweek_teams("2025-26", archive_root, database)
    before = _state(database)
    second = load_player_gameweek_teams("2025-26", archive_root, database)
    assert first == second
    assert (first.gameweeks, first.player_team_rows, first.multi_team_players) == (2, 2, 1)
    assert before == _state(database)
    assert before[0] == [("2025-26",)]
    assert before[2] == [
        (1, "arsenal", "10", 1, 1), (2, "chelsea", "10", 1, 0),
    ]
    assert before[3] == []


def test_legacy_2019_20_fixture_identifies_team_without_gameweek_label(tmp_path: Path) -> None:
    database, archive_root, folder = _setup(tmp_path, "2019-20")
    _gameweeks(folder, labelled=False)
    result = load_player_gameweek_teams("2019-20", archive_root, database)
    assert result.player_team_rows == 2
    assert _state(database)[2][0][1] == "arsenal"


@pytest.mark.parametrize("season", ["2016-17", "2017-18"])
def test_early_archive_infers_club_from_both_fixture_sides(tmp_path: Path, season: str) -> None:
    database, archive_root, folder = _setup(tmp_path, season)
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO players (display_name) VALUES ('Opponent')")
        connection.executemany("INSERT INTO player_source_ids VALUES (?, ?, ?, 2)", [
            ("fpl.element.id", f"premier-league:{season}", "12"),
            ("fpl.element.code", f"premier-league:{season}", "321"),
        ])
    _write(folder / "players_raw.csv", ["id", "code", "element_type", "team"],
           [("10", "123", "3", "1"), ("12", "321", "3", "2")])
    fields = ["element", "fixture", "opponent_team", "was_home", "kickoff_time", "GW", "minutes"]
    rows = [
        ("10", "1", "2", "True", f"{season[:4]}-08-16T14:00:00Z", "1", "90"),
        ("12", "1", "1", "False", f"{season[:4]}-08-16T14:00:00Z", "1", "0"),
        ("10", "2", "1", "False", f"{season[:4]}-08-23T14:00:00Z", "2", "0"),
        ("12", "2", "6", "True", f"{season[:4]}-08-23T14:00:00Z", "2", "90"),
    ]
    # In the second week FPL lists element 10 at club ID 6, despite
    # players_raw.csv retaining the season-end team ID 1.
    _write(folder / "gws/merged_gw.csv", fields, rows)
    first = load_player_gameweek_teams(season, archive_root, database)
    assert first == load_player_gameweek_teams(season, archive_root, database)
    assert first.player_team_rows == 4
    assert _state(database)[2] == [
        (1, "arsenal", "10", 1, 1), (1, "bournemouth", "12", 1, 0),
        (2, "everton" if season == "2016-17" else "crystal-palace", "10", 1, 0),
        (2, "arsenal", "12", 1, 1),
    ]
    assert _state(database)[3] == []

    _write(folder / "gws/merged_gw.csv", fields, rows[:1])
    with pytest.raises(GameweekTeamsError, match="Incomplete archive fixture sides"):
        load_player_gameweek_teams(season, archive_root, database)
    assert len(_state(database)[2]) == 4


def test_early_fixture_rejects_conflicting_opponents_before_writing(tmp_path: Path) -> None:
    database, archive_root, folder = _setup(tmp_path, "2016-17")
    _write(folder / "gws/merged_gw.csv",
           ["element", "fixture", "opponent_team", "was_home", "kickoff_time", "GW", "minutes"], [
               ("10", "1", "2", "True", "2016-08-16T14:00:00Z", "1", "90"),
               ("10", "1", "3", "True", "2016-08-16T14:00:00Z", "1", "90"),
           ])
    with pytest.raises(GameweekTeamsError, match="Conflicting opponent IDs"):
        load_player_gameweek_teams("2016-17", archive_root, database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM seasons").fetchone()[0] == 0


def test_team_conflict_rejects_load_and_does_not_create_schema(tmp_path: Path) -> None:
    database, archive_root, folder = _setup(tmp_path)
    _gameweeks(folder)
    path = folder / "gws/merged_gw.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    rows[1][-1] = "Chelsea"  # The fixture says Arsenal.
    _write(path, rows[0], [tuple(row) for row in rows[1:]])
    with pytest.raises(GameweekTeamsError, match="Fixture/gameweek team conflict"):
        load_player_gameweek_teams("2025-26", archive_root, database)
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM seasons").fetchone()[0] == 0
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name IN ('gameweeks', 'player_gameweek_teams')"
        ).fetchall() == []


def test_repeated_raw_line_is_deduplicated_but_postponed_fixture_keeps_its_week(tmp_path: Path) -> None:
    database, archive_root, folder = _setup(tmp_path)
    _gameweeks(folder)
    path = folder / "gws/merged_gw.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        fields, *rows = list(reader)
    delayed = rows[0].copy()
    delayed[4], delayed[5] = "2025-09-01T14:00:00Z", "3"
    _write(path, fields, [*map(tuple, rows), tuple(rows[0]), tuple(delayed)])
    result = load_player_gameweek_teams("2025-26", archive_root, database)
    assert (result.gameweeks, result.player_team_rows) == (3, 3)
    assert _state(database)[2] == [
        (1, "arsenal", "10", 1, 1),
        (2, "chelsea", "10", 1, 0),
        (3, "arsenal", "10", 1, 1),
    ]


def test_cli_forwards_season_and_uses_volume_owner(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_load(season, archive_root, database_path):
        calls.append((season, archive_root, database_path))
        return GameweekTeamsSummary(season, 38, 100, 1)

    monkeypatch.setattr(cli, "load_player_gameweek_teams", fake_load)
    runner = CliRunner()
    assert runner.invoke(cli.app, ["ingest", "player-gameweek-teams"]).exit_code != 0
    result = runner.invoke(cli.app, [
        "ingest", "player-gameweek-teams", "--season", "2025-26", "--raw-root", str(tmp_path),
    ])
    assert result.exit_code == 0, result.output
    assert calls == [("2025-26", tmp_path / "fpl_archive_vaastav", cli.DATABASE_PATH)]
    command = compose_runner.build_compose_command(
        ["ingest", "player-gameweek-teams", "--season", "2025-26"], project_root=tmp_path
    )
    assert command[command.index("--user"):command.index("data-tools")] == ["--user", "0:0"]


@pytest.mark.parametrize("year", range(2016, 2027))
def test_saved_archive_fixture_team_links_are_consistent(year: int) -> None:
    season = f"{year}-{(year + 1) % 100:02d}"
    folder = ARCHIVE / season
    if not folder.is_dir():
        pytest.skip("Saved archive not present")
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    teams = _source_teams(folder, aliases)
    elements, observations = _observations(folder, teams, aliases)
    assert observations
    assert all(elements[element] == code for element, code, *_ in observations)


@pytest.mark.parametrize("year", range(2016, 2019))
def test_early_fixture_clubs_match_saved_premier_league_schedule(year: int) -> None:
    season = f"{year}-{(year + 1) % 100:02d}"
    folder, pages = ARCHIVE / season, sorted((PL_FIXTURES / season).glob("page-*.json"))
    if not (folder / "gws/merged_gw.csv").is_file() or not pages:
        pytest.skip("Saved FPL/PL sources not present")
    _, aliases = _read_clubs(TEAM_REFERENCE_PATH)
    teams = _source_teams(folder, aliases)
    schedule = set()
    for page in pages:
        for match in json.loads(page.read_text(encoding="utf-8"))["content"]:
            home, away = match["teams"]
            schedule.add((
                aliases[_normalize(home["team"]["name"])],
                aliases[_normalize(away["team"]["name"])],
                datetime.fromtimestamp(match["kickoff"]["millis"] / 1000, timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%SZ"),
            ))
    sides = {}
    with (folder / "gws/merged_gw.csv").open(encoding="cp1252", newline="") as stream:
        for row in csv.DictReader(stream):
            pair = sides.setdefault(row["fixture"], {})
            team = teams[row["opponent_team"]]
            slot = "away" if row["was_home"] == "True" else "home"
            assert slot not in pair or pair[slot] == team
            pair[slot] = team
            assert "kickoff" not in pair or pair["kickoff"] == row["kickoff_time"]
            pair["kickoff"] = row["kickoff_time"]
    assert len(sides) == len(schedule) == 380
    assert {(row["home"], row["away"], row["kickoff"]) for row in sides.values()} == schedule


def test_all_saved_seasons_load_into_isolated_database(tmp_path: Path) -> None:
    if not (ARCHIVE / "2016-17/players_raw.csv").is_file():
        pytest.skip("Saved archive not present")
    database = tmp_path / "full-saved-fixture.db"
    clubs, _ = _read_clubs(TEAM_REFERENCE_PATH)
    schema = ROOT / "src/tools/data_pipeline/ingestion/base_tables.sql"
    with sqlite3.connect(database) as connection:
        connection.executescript(schema.read_text(encoding="utf-8"))
        connection.executemany("INSERT INTO teams (team_key, name) VALUES (?, ?)", clubs)
        by_code = {}
        for year in range(2016, 2027):
            season = f"{year}-{(year + 1) % 100:02d}"
            path = ARCHIVE / season / "players_raw.csv"
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    if row["element_type"] == "5":
                        continue
                    code = row["code"]
                    if code not in by_code:
                        by_code[code] = connection.execute(
                            "INSERT INTO players (display_name) VALUES (?) RETURNING player_id", (f"code {code}",)
                        ).fetchone()[0]
                    connection.executemany(
                        "INSERT INTO player_source_ids VALUES (?, ?, ?, ?)",
                        [("fpl.element.id", f"premier-league:{season}", row["id"], by_code[code]),
                         ("fpl.element.code", f"premier-league:{season}", code, by_code[code])],
                    )
    summaries = [
        load_player_gameweek_teams(f"{year}-{(year + 1) % 100:02d}", ARCHIVE, database)
        for year in range(2016, 2027)
    ]
    assert [summary.gameweeks for summary in summaries[:3]] == [38, 38, 38]
    assert summaries[3].gameweeks == 38  # Archived 2019-20 skips some numbers after the pause.
    assert summaries[-1].gameweeks == 1  # Saved 2026-27 gameweek file is still partial.
    assert summaries[-2].multi_team_players == 27
    assert all(summary.player_team_rows > 0 for summary in summaries)
    assert load_player_gameweek_teams("2025-26", ARCHIVE, database) == summaries[-2]
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT max(gameweek_number) FROM gameweeks").fetchone()[0] > 38
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT count(*) FROM player_gameweek_teams").fetchone()[0] == sum(
            summary.player_team_rows for summary in summaries
        )
