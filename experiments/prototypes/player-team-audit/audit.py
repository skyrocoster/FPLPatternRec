"""Read-only check of reviewed FPL code pairs against dated team observations.

Run from the repository root while the existing Datasette service is healthy.
This is evidence for identity review, not a player-team or transfer importer.
"""

import csv
from collections import defaultdict
from datetime import date
import io
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "data/raw/fpl_archive_vaastav"
PAIRS = {
    "Aaron Ramsey": ("41792", "447715"),
    "Joshua King": ("78007", "577725"),
    "James Wilson": ("112139", "613232"),
    "Ben Davies": ("115556", "152898"),
    "Danny Ward": ("75826", "95463"),
    "Álvaro Fernández": ("240796", "515501"),
    "Kaine Hayden / Kesler-Hayden": ("490098", "465390"),
}
CODES = {code for pair in PAIRS.values() for code in pair}


def csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        yield from csv.DictReader(stream)


def gameweek_rows(path: Path):
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        # The older saved gameweek CSVs include Windows-1252 player names.
        text = path.read_text(encoding="cp1252")
    return csv.DictReader(io.StringIO(text))


def live_mappings() -> dict[str, tuple[int, str, str, str]]:
    codes = ",".join(f"'{code}'" for code in sorted(CODES))
    sql = (
        "SELECT s.source_id, p.player_id, p.display_name, "
        "min(s.source_scope), max(s.source_scope) "
        "FROM player_source_ids s JOIN players p ON p.player_id = s.player_id "
        "WHERE s.source_namespace = 'fpl.element.code' "
        f"AND s.source_id IN ({codes}) "
        "GROUP BY s.source_id, p.player_id, p.display_name"
    )
    url = "http://127.0.0.1:8677/fplpatternrec.json?" + urlencode({"sql": sql})
    with urlopen(url, timeout=15) as response:
        result = json.load(response)
    if not result["ok"] or result["truncated"] or len(result["rows"]) != len(CODES):
        raise RuntimeError(f"Live mapping query is incomplete: {result}")
    mappings = {code: (player_id, name, first, last)
                for code, player_id, name, first, last in result["rows"]}
    if set(mappings) != CODES:
        raise RuntimeError("Some reviewed FPL codes are missing from the live database")
    return mappings


def main() -> None:
    mappings = live_mappings()
    observations = defaultdict(list)
    seasons_by_code = defaultdict(list)
    covered_seasons = []
    uncovered_seasons = []
    multi_team_counts = {}
    transfer_examples = defaultdict(list)
    for year in range(2016, 2027):
        season = f"{year}-{(year + 1) % 100:02d}"
        folder = ARCHIVE / season
        elements = {}
        for row in csv_rows(folder / "players_raw.csv"):
            if row["element_type"] not in {"1", "2", "3", "4"}:
                continue
            elements[row["id"]] = row["code"]
            if row["code"] in CODES:
                seasons_by_code[row["code"]].append(season)
        reader = gameweek_rows(folder / "gws/merged_gw.csv")
        if "team" not in reader.fieldnames:
            uncovered_seasons.append(season)
            continue
        covered_seasons.append(season)
        teams_by_element = defaultdict(set)
        for row in reader:
            code = elements.get(row["element"])
            if code is None:
                continue  # Manager records are not canonical players.
            team, kickoff = row["team"].strip(), row["kickoff_time"].strip()
            if not team or not kickoff:
                raise ValueError(f"Missing dated team evidence in {season}: {row['element']}")
            date.fromisoformat(kickoff[:10])
            teams_by_element[row["element"]].add(team)
            if season == "2025-26" and row["element"] in {"135", "168"}:
                transfer_examples[(row["element"], team)].append(kickoff[:10])
            if code in CODES:
                observations[code].append((season, team, kickoff[:10], int(row["minutes"]) > 0))
        multi_team_counts[season] = sum(len(teams) > 1 for teams in teams_by_element.values())

    print("Reviewed code pairs: live player ID, archived seasons, dated FPL team observations")
    for label, (left, right) in PAIRS.items():
        ids = [mappings[code][0] for code in (left, right)]
        expected_same = label.startswith("Kaine")
        if (ids[0] == ids[1]) != expected_same:
            raise RuntimeError(f"Unexpected canonical player mapping for {label}: {ids}")
        print(f"\n{label}: codes {left}/{right}; player IDs {ids[0]}/{ids[1]}")
        for code in (left, right):
            print(f"  {code} ({mappings[code][1]}): archive seasons {','.join(seasons_by_code[code]) or 'none'}")
            grouped = defaultdict(list)
            for season, team, kickoff, played in observations[code]:
                grouped[(season, team)].append((kickoff, played))
            for (season, team), dates in sorted(grouped.items()):
                first, last = min(day for day, _ in dates), max(day for day, _ in dates)
                played = sum(yes for _, yes in dates)
                print(f"    {season} {team}: {first}..{last}, {len(dates)} records, {played} with minutes")
            if not grouped:
                print("    No dated team observations in the team-labelled seasons")
    print("\nDated team field present:", ", ".join(covered_seasons))
    print("Dated team field absent:", ", ".join(uncovered_seasons))
    print("Multi-team FPL elements per labelled season:", multi_team_counts)
    for (element, team), days in sorted(transfer_examples.items()):
        print(f"2025-26 element {element} {team}: {min(days)}..{max(days)} ({len(days)} records)")


if __name__ == "__main__":
    main()
