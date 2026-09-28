"""Typer command line for safe refreshes of the core raw-data providers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable

import typer

from .ingestion.official_fpl_teams import (
    OfficialFplTeamsLoadSummary,
    OfficialFplTeamsValidationError,
    load_official_fpl_teams,
)
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
from .retrieval.sofascore import collect_sofascore
from .retrieval.understat import collect_understat

app = typer.Typer(no_args_is_help=True, help="Refresh football data and run data-pipeline tasks.")
retrieve_app = typer.Typer(no_args_is_help=True, help="Refresh supported raw-data sources.")
ingest_app = typer.Typer(no_args_is_help=True, help="Load supported data into SQLite staging tables.")
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
    "fotmob": _fotmob,
    "understat": _understat,
    "football-data": _football_data,
    "clubelo": _clubelo,
    "sofascore": _sofascore,
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
    """Refresh all eight core sources using the existing core raw root."""
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
