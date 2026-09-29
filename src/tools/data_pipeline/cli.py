"""Typer commands for provider retrieval and validated SQLite ingestion."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import typer

from .ingestion.archive_players import (
    ArchivePlayersValidationError,
    load_archive_players,
)
from .ingestion.archive_teams import ArchiveTeamsError, load_archive_teams
from .ingestion.canonical_fixtures import CanonicalFixturesError, load_canonical_fixtures
from .ingestion.canonical_players import (
    CanonicalPlayersValidationError,
    load_canonical_players,
)
from .ingestion.canonical_schema import CanonicalSchemaError, install_canonical_schema
from .ingestion.canonical_teams import (
    TEAM_REFERENCE_PATH,
    CanonicalTeamsValidationError,
    load_canonical_teams,
)
from .ingestion.match_dates import MatchDatesError, load_match_dates
from .ingestion.official_fpl_season import OfficialFplSeasonError
from .ingestion.official_fpl_teams import (
    OfficialFplTeamsLoadSummary,
    OfficialFplTeamsValidationError,
    load_official_fpl_teams,
)
from .ingestion.player_birth_dates import BirthDateEvidenceError, backfill_player_birth_dates
from .ingestion.player_fixture_observations import (
    PlayerFixtureObservationsError,
    load_player_fixture_observations,
)
from .ingestion.player_gameweek_teams import GameweekTeamsError, load_player_gameweek_teams
from .ingestion.sqlite import DATABASE_PATH
from .retrieval.alternative_competitions.fotmob import collect_fotmob_competitions
from .retrieval.alternative_competitions.openfootball import collect_openfootball
from .retrieval.alternative_competitions.transfermarkt import collect_transfermarkt_injuries
from .retrieval.alternative_competitions.wikipedia import collect_wikipedia_competitions
from .retrieval.clubelo import collect_clubelo
from .retrieval.common import RawCollector
from .retrieval.football_data import collect_football_data
from .retrieval.fotmob import collect_fotmob
from .retrieval.fpl_archive import collect_fpl_archive
from .retrieval.official_fpl import collect_fpl
from .retrieval.premier_league import collect_premier_league_api
from .retrieval.premier_league_players import collect_premier_league_players
from .retrieval.sofascore import collect_sofascore
from .retrieval.transfermarkt_datasets import collect_transfermarkt_datasets
from .retrieval.understat import collect_understat
from .retrieval.wikidata_players import collect_wikidata_players
from .retrieval.wikidata_transfermarkt import (
    collect_wikidata_transfermarkt,
    collect_wikidata_transfermarkt_fpl,
)

app = typer.Typer(no_args_is_help=True, help="Refresh football data and run data-pipeline tasks.")
retrieve_app = typer.Typer(no_args_is_help=True, help="Refresh supported raw-data sources.")
ingest_app = typer.Typer(no_args_is_help=True, help="Load supported staging and canonical data into SQLite.")
app.add_typer(retrieve_app, name="retrieve")
app.add_typer(ingest_app, name="ingest")


def _report_ingestion_result(summary: OfficialFplTeamsLoadSummary) -> None:
    typer.echo(f"Loaded {summary.team_count} official FPL teams for {summary.season}.")


@dataclass(frozen=True)
class RetrievalOptions:
    include_fpl_player_summaries: bool = True
    include_fotmob_match_details: bool = True


ProviderRunner = Callable[[RawCollector, RetrievalOptions], None]


def _official_fpl(collector: RawCollector, options: RetrievalOptions) -> None:
    collect_fpl(collector, options.include_fpl_player_summaries)


def _fotmob(collector: RawCollector, options: RetrievalOptions) -> None:
    collect_fotmob(collector, options.include_fotmob_match_details)


def _fpl_archive(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_fpl_archive(collector)


def _premier_league(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_premier_league_api(collector)


def _premier_league_players(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_premier_league_players(collector)


def _understat(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_understat(collector)


def _football_data(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_football_data(collector)


def _clubelo(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_clubelo(collector)


def _sofascore(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_sofascore(collector)


def _transfermarkt_datasets(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_transfermarkt_datasets(collector)


def _wikidata_players(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_wikidata_players(collector)


def _wikidata_transfermarkt(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_wikidata_transfermarkt(collector)


def _wikidata_transfermarkt_fpl(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_wikidata_transfermarkt_fpl(collector)


def _fotmob_competitions(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_fotmob_competitions(collector)


def _openfootball(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_openfootball(collector)


def _wikipedia_competitions(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_wikipedia_competitions(collector)


def _transfermarkt_injuries(collector: RawCollector, options: RetrievalOptions) -> None:
    del options
    collect_transfermarkt_injuries(collector)


CORE_PROVIDERS: dict[str, ProviderRunner] = {
    "official-fpl": _official_fpl,
    "fpl-archive": _fpl_archive,
    "premier-league": _premier_league,
    "premier-league-players": _premier_league_players,
    "fotmob": _fotmob,
    "understat": _understat,
    "football-data": _football_data,
    "clubelo": _clubelo,
    "sofascore": _sofascore,
    "transfermarkt-datasets": _transfermarkt_datasets,
    "wikidata-players": _wikidata_players,
    "wikidata-transfermarkt": _wikidata_transfermarkt,
    "wikidata-transfermarkt-fpl": _wikidata_transfermarkt_fpl,
}
ALTERNATIVE_PROVIDERS: dict[str, ProviderRunner] = {
    "fotmob-competitions": _fotmob_competitions,
    "openfootball": _openfootball,
    "wikipedia-competitions": _wikipedia_competitions,
    "transfermarkt-injuries": _transfermarkt_injuries,
}


def default_core_raw_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "raw"


def default_alternative_raw_root() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "alternative_comps" / "raw"


@ingest_app.command("official-fpl-teams")
def ingest_official_fpl_teams(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Core raw root (default: data/raw).",
    ),
    season: str | None = typer.Option(
        None,
        "--season",
        help="Season in YYYY-YY form; otherwise derive it from the first gameweek deadline.",
    ),
) -> None:
    """Load the official FPL teams from the saved bootstrap into SQLite."""
    bootstrap_path = (raw_root or default_core_raw_root()) / "official_fpl_api" / "bootstrap-static.json"
    try:
        summary = load_official_fpl_teams(bootstrap_path, DATABASE_PATH, season)
    except (OfficialFplTeamsValidationError, OSError, sqlite3.Error) as error:
        typer.echo(f"official FPL teams ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    _report_ingestion_result(summary)


@ingest_app.command("canonical-teams")
def ingest_canonical_teams(
    season: str | None = typer.Option(
        None, "--season", help="Also map staged official FPL teams for this YYYY-YY season."
    ),
    team_reference: Path = typer.Option(
        TEAM_REFERENCE_PATH, "--team-reference", help="Reviewed Premier League club reference JSON."
    ),
) -> None:
    """Load reviewed clubs from JSON; optionally add a season's FPL team mappings."""
    try:
        summary = load_canonical_teams(season, DATABASE_PATH, team_reference)
    except (CanonicalTeamsValidationError, OfficialFplTeamsValidationError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical teams ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    if summary.season is None:
        typer.echo(f"Loaded {summary.club_count} reviewed clubs from the team reference.")
    else:
        typer.echo(
            f"Loaded {summary.club_count} reviewed clubs and mapped "
            f"{summary.mapped_team_count} FPL teams for {summary.season}."
        )


@ingest_app.command("canonical-archive-teams")
def ingest_canonical_archive_teams(
    season: str = typer.Option(..., "--season", help="Completed saved FPL season (2016-17 to 2025-26)."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Map saved historical FPL team IDs to existing reviewed clubs."""
    try:
        summary = load_archive_teams(
            season, (raw_root or default_core_raw_root()) / "fpl_archive_vaastav", DATABASE_PATH
        )
    except (ArchiveTeamsError, CanonicalTeamsValidationError, GameweekTeamsError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical archive teams ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Mapped {summary.mapped_team_count} historical FPL teams for {summary.season}.")


@ingest_app.command("canonical-schema")
def ingest_canonical_schema() -> None:
    """Install the eight base tables on an existing, staging-only SQLite database."""
    try:
        install_canonical_schema(DATABASE_PATH)
    except (CanonicalSchemaError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical schema installation failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo("Installed the eight canonical base tables; existing staging data was retained.")


@ingest_app.command("canonical-players")
def ingest_canonical_players(
    season: str = typer.Option(..., "--season", help="FPL season in YYYY-YY form; must match the saved bootstrap."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Load a saved season's official FPL football players into canonical identity tables."""
    bootstrap = (raw_root or default_core_raw_root()) / "official_fpl_api" / "bootstrap-static.json"
    try:
        summary = load_canonical_players(season, bootstrap, DATABASE_PATH)
    except (CanonicalPlayersValidationError, OfficialFplTeamsValidationError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical players ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Resolved {summary.player_count} FPL players for {summary.season}; "
        f"excluded {summary.excluded_manager_count} manager entries."
    )


@ingest_app.command("canonical-archive-players")
def ingest_canonical_archive_players(
    season: str = typer.Option(..., "--season", help="Reviewed FPL archive season (2016-17 to 2025-26); load newest first."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Resolve one historical season against later saved FPL identities."""
    archive = (raw_root or default_core_raw_root()) / "fpl_archive_vaastav" / season
    try:
        summary = load_archive_players(
            season, archive / "players_raw.csv", archive / "player_idlist.csv", DATABASE_PATH
        )
    except (ArchivePlayersValidationError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical archive players ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Resolved {summary.player_count} FPL players for {summary.season}: "
        f"{summary.linked_player_count} linked to later seasons, "
        f"{summary.archive_only_player_count} archive-only; "
        f"excluded {summary.excluded_manager_count} managers."
    )


@ingest_app.command("player-birth-dates")
def ingest_player_birth_dates(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Review candidates without writing SQLite."),
    show_candidates: bool = typer.Option(False, "--show-candidates", help="List proposed players and DOBs in a dry run."),
) -> None:
    """Fill NULL player DOBs only from checked saved source evidence."""
    if show_candidates and not dry_run:
        typer.echo("--show-candidates requires --dry-run; no DOBs were changed.", err=True)
        raise typer.Exit(code=1)
    try:
        summary = backfill_player_birth_dates(raw_root or default_core_raw_root(), DATABASE_PATH, dry_run=dry_run)
    except (BirthDateEvidenceError, OSError, KeyError, TypeError, ValueError, sqlite3.Error) as error:
        typer.echo(f"player birth-date backfill failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"{'Would fill' if dry_run else 'Filled'} {len(summary.proposed)} missing player DOBs "
        f"({summary.direct_fpl} saved FPL, {summary.scoped_opta} official PL API Opta, "
        f"{summary.pl_roster} official PL API season rosters, "
        f"{summary.external_pair} matched Transfermarkt/Wikidata with PL club/season evidence, "
        f"{summary.id_name_only} unique name plus Wikidata Transfermarkt ID without appearance, "
        f"{summary.reviewed_json} reviewed JSON fallback). "
        f"Cross-checked {summary.corroborated_controls} already-dated players; "
        f"skipped {len(summary.conflicts)} conflicting players."
    )
    for pid, name, existing, candidates in summary.conflicts:
        typer.echo(f"  review player {pid} {name}: existing={existing!r}, evidence={candidates}")
    if show_candidates:
        for proposal in summary.proposed:
            typer.echo(
                f"  candidate [{proposal.category.value}] player {proposal.player_id} "
                f"{proposal.name}: {proposal.date_of_birth}"
            )


@ingest_app.command("player-gameweek-teams")
def ingest_player_gameweek_teams(
    season: str = typer.Option(..., "--season", help="Saved FPL season from 2016-17 through 2026-27."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Load validated gameweeks and each canonical player's FPL-listed team in that week."""
    try:
        root = raw_root or default_core_raw_root()
        summary = load_player_gameweek_teams(
            season, root / "fpl_archive_vaastav", DATABASE_PATH,
            **({"official_raw_root": root / "official_fpl_api"} if season == "2026-27" else {}),
        )
    except (GameweekTeamsError, OfficialFplSeasonError, OSError, sqlite3.Error) as error:
        typer.echo(f"player-gameweek teams ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Loaded {summary.season}: {summary.gameweeks} gameweeks, "
        f"{summary.player_team_rows} player/team/week rows, "
        f"{summary.multi_team_players} players with multiple FPL-listed clubs."
    )


@ingest_app.command("canonical-fixtures")
def ingest_canonical_fixtures(
    season: str = typer.Option(..., "--season", help="Saved FPL fixture season (2016-17 to 2026-27)."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Load checked FPL fixtures against existing gameweek/team assignments."""
    try:
        root = raw_root or default_core_raw_root()
        summary = load_canonical_fixtures(
            season, root / "fpl_archive_vaastav", DATABASE_PATH,
            **({"official_raw_root": root / "official_fpl_api"} if season == "2026-27" else {}),
        )
    except (CanonicalFixturesError, OfficialFplSeasonError, OSError, sqlite3.Error) as error:
        typer.echo(f"canonical fixtures ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Loaded {summary.fixture_count} canonical fixtures for {summary.season}.")


@ingest_app.command("player-fixture-observations")
def ingest_player_fixture_observations(
    season: str = typer.Option(
        ..., "--season", help="Saved archive season 2016-17 through 2025-26, or official 2026-27."
    ),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Load saved player listings against existing canonical fixtures and identities."""
    try:
        root = raw_root or default_core_raw_root()
        summary = load_player_fixture_observations(
            season,
            root / "fpl_archive_vaastav",
            DATABASE_PATH,
            **({"official_raw_root": root / "official_fpl_api"} if season == "2026-27" else {}),
        )
    except (PlayerFixtureObservationsError, OfficialFplSeasonError, OSError, sqlite3.Error) as error:
        typer.echo(f"player-fixture observations ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(
        f"Loaded {summary.observation_count} player/fixture observations for {summary.season} "
        f"across {summary.fixture_count} fixtures ({summary.appearance_count} with minutes)."
    )


@ingest_app.command("match-dates")
def ingest_match_dates(
    season: str = typer.Option(..., "--season", help="Saved Premier League season (2016-17 to 2026-27)."),
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Backfill accepted local dates from saved official Premier League fixtures."""
    try:
        summary = load_match_dates(
            season, (raw_root or default_core_raw_root()) / "premier_league_api" / "fixtures", DATABASE_PATH
        )
    except (MatchDatesError, CanonicalTeamsValidationError, OSError, ValueError, sqlite3.Error) as error:
        typer.echo(f"match dates ingestion failed: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"Accepted {summary.fixture_count} local match dates for {summary.season}.")


def _dispatch_providers(
    provider_names: tuple[str, ...],
    raw_root: Path,
    options: RetrievalOptions,
    providers: dict[str, ProviderRunner],
) -> list[str]:
    collector = RawCollector(raw_root)
    failures: list[str] = []
    for provider_name in provider_names:
        try:
            providers[provider_name](collector, options)
        except Exception as error:
            failures.append(provider_name)
            typer.echo(
                f"collector failed for {provider_name}: {type(error).__name__}: {error}",
                err=True,
            )
    return failures


def _dispatch(
    provider_names: tuple[str, ...],
    raw_root: Path | None,
    options: RetrievalOptions,
    providers: dict[str, ProviderRunner],
    default_raw_root: Callable[[], Path],
) -> list[str]:
    return _dispatch_providers(
        provider_names,
        raw_root or default_raw_root(),
        options,
        providers,
    )


def _raise_for_failures(failures: list[str]) -> None:
    if failures:
        raise typer.Exit(code=1)


@retrieve_app.command("core")
def retrieve_core(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
    no_fpl_player_summaries: bool = typer.Option(
        False,
        "--no-fpl-player-summaries",
        help="Skip the official FPL player-summary requests.",
    ),
    no_fotmob_match_details: bool = typer.Option(
        False,
        "--no-fotmob-match-details",
        help="Skip FotMob completed-match detail requests.",
    ),
) -> None:
    """Refresh all core sources using the existing core raw root."""
    failures = _dispatch(
        tuple(CORE_PROVIDERS),
        raw_root,
        RetrievalOptions(
            include_fpl_player_summaries=not no_fpl_player_summaries,
            include_fotmob_match_details=not no_fotmob_match_details,
        ),
        CORE_PROVIDERS,
        default_core_raw_root,
    )
    _raise_for_failures(failures)


@retrieve_app.command("official-fpl")
def retrieve_official_fpl(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
    no_fpl_player_summaries: bool = typer.Option(
        False,
        "--no-fpl-player-summaries",
        help="Skip the player-summary requests; bootstrap, fixtures, and live snapshots remain enabled.",
    ),
) -> None:
    """Refresh bootstrap, fixtures, current live snapshots, and player summaries."""
    failures = _dispatch(
        ("official-fpl",),
        raw_root,
        RetrievalOptions(include_fpl_player_summaries=not no_fpl_player_summaries),
        CORE_PROVIDERS,
        default_core_raw_root,
    )
    _raise_for_failures(failures)


@retrieve_app.command("fpl-archive")
def retrieve_fpl_archive(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh the Vaastav historical FPL archive."""
    failures = _dispatch(
        ("fpl-archive",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("premier-league")
def retrieve_premier_league(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh Premier League fixtures and statistics."""
    failures = _dispatch(
        ("premier-league",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("premier-league-players")
def retrieve_premier_league_players(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh official Premier League season player roster pages from saved season IDs."""
    _raise_for_failures(
        _dispatch(("premier-league-players",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root)
    )


@retrieve_app.command("fotmob")
def retrieve_fotmob(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
    no_fotmob_match_details: bool = typer.Option(
        False,
        "--no-fotmob-match-details",
        help="Skip completed-match detail requests.",
    ),
) -> None:
    """Refresh FotMob league, season, statistics, and match data."""
    failures = _dispatch(
        ("fotmob",),
        raw_root,
        RetrievalOptions(include_fotmob_match_details=not no_fotmob_match_details),
        CORE_PROVIDERS,
        default_core_raw_root,
    )
    _raise_for_failures(failures)


@retrieve_app.command("understat")
def retrieve_understat(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh Understat league and recent match data."""
    failures = _dispatch(
        ("understat",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("football-data")
def retrieve_football_data(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh Football-Data.co.uk season CSVs."""
    failures = _dispatch(
        ("football-data",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("clubelo")
def retrieve_clubelo(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Try to refresh the ClubElo public CSV."""
    failures = _dispatch(
        ("clubelo",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("sofascore")
def retrieve_sofascore(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Try to refresh SofaScore Premier League seasons."""
    failures = _dispatch(
        ("sofascore",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
    )
    _raise_for_failures(failures)


@retrieve_app.command("transfermarkt-datasets")
def retrieve_transfermarkt_datasets(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh the published player, games and appearances CSVs."""
    _raise_for_failures(
        _dispatch(
            ("transfermarkt-datasets",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
        )
    )


@retrieve_app.command("wikidata-players")
def retrieve_wikidata_players(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Refresh Wikidata birth-date statements for Premier League club footballers."""
    _raise_for_failures(
        _dispatch(("wikidata-players",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root)
    )


@retrieve_app.command("wikidata-transfermarkt")
def retrieve_wikidata_transfermarkt(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Retrieve Wikidata birth-date statements for saved Transfermarkt players."""
    _raise_for_failures(
        _dispatch(
            ("wikidata-transfermarkt",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
        )
    )


@retrieve_app.command("wikidata-transfermarkt-fpl")
def retrieve_wikidata_transfermarkt_fpl(
    raw_root: Path | None = typer.Option(None, "--raw-root", help="Core raw root (default: data/raw)."),
) -> None:
    """Retrieve Wikidata birth dates by ID for Transfermarkt players named in saved FPL files."""
    _raise_for_failures(
        _dispatch(
            ("wikidata-transfermarkt-fpl",), raw_root, RetrievalOptions(), CORE_PROVIDERS, default_core_raw_root
        )
    )


@retrieve_app.command("alternative-comps")
def retrieve_alternative_comps(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
) -> None:
    """Refresh all four alternative-competition sources."""
    failures = _dispatch(
        tuple(ALTERNATIVE_PROVIDERS),
        raw_root,
        RetrievalOptions(),
        ALTERNATIVE_PROVIDERS,
        default_alternative_raw_root,
    )
    _raise_for_failures(failures)


@retrieve_app.command("all")
def retrieve_all(
    core_raw_root: Path | None = typer.Option(
        None,
        "--core-raw-root",
        help="Core raw root (default: data/raw).",
    ),
    alternative_raw_root: Path | None = typer.Option(
        None,
        "--alternative-raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
    no_fpl_player_summaries: bool = typer.Option(
        False,
        "--no-fpl-player-summaries",
        help="Skip the official FPL player-summary requests.",
    ),
    no_fotmob_match_details: bool = typer.Option(
        False,
        "--no-fotmob-match-details",
        help="Skip FotMob completed-match detail requests.",
    ),
) -> None:
    """Refresh both source groups using their separate raw roots."""
    options = RetrievalOptions(
        include_fpl_player_summaries=not no_fpl_player_summaries,
        include_fotmob_match_details=not no_fotmob_match_details,
    )
    failures = _dispatch(
        tuple(CORE_PROVIDERS),
        core_raw_root,
        options,
        CORE_PROVIDERS,
        default_core_raw_root,
    )
    failures.extend(
        _dispatch(
            tuple(ALTERNATIVE_PROVIDERS),
            alternative_raw_root,
            options,
            ALTERNATIVE_PROVIDERS,
            default_alternative_raw_root,
        )
    )
    _raise_for_failures(failures)


@retrieve_app.command("fotmob-competitions")
def retrieve_fotmob_competitions(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
) -> None:
    """Refresh FotMob alternative competition seasons and leaderboards."""
    _raise_for_failures(
        _dispatch(
            ("fotmob-competitions",),
            raw_root,
            RetrievalOptions(),
            ALTERNATIVE_PROVIDERS,
            default_alternative_raw_root,
        )
    )


@retrieve_app.command("openfootball")
def retrieve_openfootball(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
) -> None:
    """Refresh OpenFootball CC0 cup and international data."""
    _raise_for_failures(
        _dispatch(
            ("openfootball",),
            raw_root,
            RetrievalOptions(),
            ALTERNATIVE_PROVIDERS,
            default_alternative_raw_root,
        )
    )


@retrieve_app.command("wikipedia-competitions")
def retrieve_wikipedia_competitions(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
) -> None:
    """Refresh Wikipedia competition article revision responses."""
    _raise_for_failures(
        _dispatch(
            ("wikipedia-competitions",),
            raw_root,
            RetrievalOptions(),
            ALTERNATIVE_PROVIDERS,
            default_alternative_raw_root,
        )
    )


@retrieve_app.command("transfermarkt-injuries")
def retrieve_transfermarkt_injuries(
    raw_root: Path | None = typer.Option(
        None,
        "--raw-root",
        help="Alternative-competition raw root (default: data/alternative_comps/raw).",
    ),
) -> None:
    """Refresh the current Transfermarkt Premier League injury-page snapshot."""
    _raise_for_failures(
        _dispatch(
            ("transfermarkt-injuries",),
            raw_root,
            RetrievalOptions(),
            ALTERNATIVE_PROVIDERS,
            default_alternative_raw_root,
        )
    )
