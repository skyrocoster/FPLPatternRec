"""Shared HTTP transport and safe in-place raw-file refresh helpers."""

from __future__ import annotations

import gzip
import json
import os
import re
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

FPL_API = "https://fantasy.premierleague.com/api"
PULSELIVE_API = "https://footballapi.pulselive.com/football"
FOTMOB_API = "https://www.fotmob.com/api/data"
GITHUB_API = "https://api.github.com/repos/vaastav/Fantasy-Premier-League/contents"
USER_AGENT = "Mozilla/5.0 (compatible; FPLPatternRecDataCollector/1.0)"

PL_PLAYER_STATS = (
    "appearances",
    "minutes_played",
    "starts",
    "goals",
    "goal_assist",
    "clean_sheet",
    "saves",
    "penalty_save",
    "yellow_card",
    "red_card",
    "own_goals",
    "tackles",
    "interception",
    "clearance",
    "recoveries",
    "pass",
    "touches",
    "total_scoring_att",
    "expected_goals",
    "expected_assists",
    "big_chance_created",
    "duel_won",
    "aerial_won",
    "penalty_miss",
)
PL_TEAM_STATS = (
    "wins",
    "draws",
    "losses",
    "goals",
    "goals_conceded",
    "clean_sheet",
    "shots",
    "shots_on_target",
    "pass",
    "possession",
    "yellow_card",
    "red_card",
    "cross",
    "big_chance_created",
)
FOTMOB_HISTORICAL_PLAYER_STATS = (
    "goals",
    "goal_assist",
    "mins_played",
    "expected_goals",
    "expected_assists",
    "ontarget_scoring_att",
    "accurate_pass",
    "clean_sheet",
    "saves",
    "total_tackle",
    "interception",
    "effective_clearance",
    "ball_recovery",
    "total_yel_card",
    "total_red_card",
)
FOTMOB_HISTORICAL_TEAM_STATS = (
    "goals_team_match",
    "goals_conceded_team_match",
    "expected_goals_team",
    "possession_percentage_team",
    "clean_sheet_team",
    "accurate_pass_team",
    "saves_team",
    "ontarget_scoring_att_team",
    "corner_taken_team",
    "total_yel_card_team",
    "total_red_card_team",
)


def season_start(label: str) -> int:
    match = re.search(r"(?:19|20)\d{2}", label)
    return int(match.group()) if match else 0


def season_label(start_year: int) -> str:
    return f"{start_year}/{start_year + 1}"


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-.")


def current_season_start() -> int:
    now = datetime.now(UTC)
    return now.year if now.month >= 7 else now.year - 1


class RawCollector:
    """Fetch responses on every call and replace a target only after a full write."""

    def __init__(self, raw_root: Path) -> None:
        self.raw_root = Path(raw_root)
        self.host_next_request: dict[str, float] = {}
        self.host_intervals = {
            "api.github.com": 0.1,
            "raw.githubusercontent.com": 0.1,
            "fantasy.premierleague.com": 0.15,
            "footballapi.pulselive.com": 0.15,
            "www.fotmob.com": 0.2,
            "data.fotmob.com": 0.25,
            "understat.com": 0.5,
            "www.football-data.co.uk": 0.15,
            "api.clubelo.com": 0.5,
            "www.sofascore.com": 0.5,
            "en.wikipedia.org": 8.0,
            "www.transfermarkt.com": 2.0,
        }
        self.blocked_hosts: set[str] = set()

    @staticmethod
    def _relative_path(source: str, relative_path: str) -> Path:
        relative = Path(source) / relative_path
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("raw response paths must stay beneath the selected raw root")
        return relative

    def get(
        self,
        source: str,
        relative_path: str,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> bytes | None:
        target = self.raw_root / self._relative_path(source, relative_path)
        host = urlparse(url).netloc
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"  unavailable: {url} (cannot prepare destination: {error})", flush=True)
            return None

        if host in self.blocked_hosts:
            return None

        request_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
        if headers:
            request_headers.update(headers)
        request = Request(url, headers=request_headers)
        error_text = ""
        for attempt in range(3):
            wait = self.host_next_request.get(host, 0.0) - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self.host_next_request[host] = time.monotonic() + self.host_intervals.get(host, 0.2)
            try:
                with urlopen(request, timeout=15) as response:
                    body = response.read()
            except HTTPError as error:
                error_text = f"HTTP {error.code}: {error.reason}"
                if error.code == 403:
                    self.blocked_hosts.add(host)
                    break
                if error.code == 429 and attempt == 2:
                    self.blocked_hosts.add(host)
                    break
                if error.code < 500 and error.code != 429:
                    break
            except (TimeoutError, URLError, OSError) as error:
                error_text = f"{type(error).__name__}: {error}"
            else:
                try:
                    self._replace(target, body)
                except OSError as error:
                    print(
                        f"  unavailable: {url} (cannot replace destination: {error})",
                        flush=True,
                    )
                    return None
                return body
            if attempt < 2:
                time.sleep(float(attempt + 1))

        print(f"  unavailable: {url} ({error_text})", flush=True)
        return None

    @staticmethod
    def _replace(target: Path, body: bytes) -> None:
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".part",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(body)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
        except OSError:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def get_json(
        self,
        source: str,
        relative_path: str,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> dict[str, object] | list[object] | None:
        body = self.get(source, relative_path, url, headers)
        if body is None:
            return None
        payload = gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def record_issue(self, source: str, error: Exception) -> None:
        print(f"  collector failed for {source}: {type(error).__name__}: {error}", flush=True)

    def finish(self) -> None:
        """Compatibility with the legacy collector; refreshes create no run records."""
