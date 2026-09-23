"""Raw HTTP transport and shared source helpers for the data-retrieval package."""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import time
from collections import Counter
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
    """Save each successful HTTP response body as-is, and never replace a file."""

    def __init__(self, raw_root: Path) -> None:
        self.raw_root = raw_root
        self.run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
        self.records: dict[str, list[dict[str, object]]] = {}
        self.host_next_request: dict[str, float] = {}
        self.host_intervals = {
            "api.github.com": 0.1,
            "raw.githubusercontent.com": 0.1,
            "fantasy.premierleague.com": 0.15,
            "footballapi.pulselive.com": 0.15,
            "www.fotmob.com": 0.2,
            "understat.com": 0.5,
            "www.football-data.co.uk": 0.15,
            "api.clubelo.com": 0.5,
            "www.sofascore.com": 0.5,
        }
        self.blocked_hosts: set[str] = set()

    def _record(self, source: str, record: dict[str, object]) -> None:
        self.records.setdefault(source, []).append(record)

    def record_issue(self, source: str, error: Exception) -> None:
        self._record(
            source,
            {
                "result": "collector_failed",
                "retrieved_at_utc": datetime.now(UTC).isoformat(),
                "error": f"{type(error).__name__}: {error}",
            },
        )

    def get(
        self,
        source: str,
        relative_path: str,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> bytes | None:
        source_dir = self.raw_root / source
        source_dir.mkdir(parents=True, exist_ok=True)
        target = source_dir / relative_path
        host = urlparse(url).netloc
        if target.exists():
            body = target.read_bytes()
            self._record(
                source,
                {
                    "path": relative_path,
                    "url": url,
                    "result": "already_present_not_modified",
                    "file_mtime_utc": datetime.fromtimestamp(
                        target.stat().st_mtime, UTC
                    ).isoformat(),
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                },
            )
            return body
        if host in self.blocked_hosts:
            self._record(
                source,
                {"path": relative_path, "url": url, "result": "skipped_host_blocked"},
            )
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
                    content_type = response.headers.get("Content-Type", "")
                    content_encoding = response.headers.get("Content-Encoding", "")
                    status = response.status
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(f"{target.name}.{self.run_id}.part")
                temporary.write_bytes(body)
                temporary.replace(target)
                self._record(
                    source,
                    {
                        "path": relative_path,
                        "url": url,
                        "result": "downloaded",
                        "http_status": status,
                        "content_type": content_type,
                        "content_encoding": content_encoding,
                        "retrieved_at_utc": datetime.now(UTC).isoformat(),
                        "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(),
                    },
                )
                return body
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
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))

        self._record(
            source,
            {
                "path": relative_path,
                "url": url,
                "result": "request_failed",
                "retrieved_at_utc": datetime.now(UTC).isoformat(),
                "error": error_text,
            },
        )
        print(f"  unavailable: {url} ({error_text})", flush=True)
        return None

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
        try:
            payload = gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body
            return json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            self._record(
                source,
                {
                    "path": relative_path,
                    "url": url,
                    "result": "saved_body_not_json",
                    "error": str(error),
                },
            )
            return None

    def _write_run_metadata(self, source: str) -> dict[str, object]:
        records = self.records.get(source, [])
        counts = Counter(str(item.get("result", "unknown")) for item in records)
        result: dict[str, object] = {
            "source": source,
            "run_id": self.run_id,
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "record_counts": dict(counts),
            "records": records,
        }
        directory = self.raw_root / source
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"collection-{self.run_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"source": source, "record_counts": dict(counts)}

    def finish(self) -> None:
        self.raw_root.mkdir(parents=True, exist_ok=True)
        summaries = [self._write_run_metadata(source) for source in sorted(self.records)]
        summary = {
            "run_id": self.run_id,
            "retrieved_at_utc": datetime.now(UTC).isoformat(),
            "raw_payloads_are_unmodified_http_bodies": True,
            "sources": summaries,
        }
        (self.raw_root / f"collection-{self.run_id}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        readme = self.raw_root / "README.md"
        if not readme.exists():
            readme.write_text(
                "# Raw Premier League data\n\n"
                "Source responses are stored under separate provider folders. "
                "The downloaded payload files "
                "are saved as received; no fields are normalized or rewritten.\n\n"
                "Each source folder has a `collection-*.json` retrieval record containing URLs, "
                "timestamps, HTTP status, byte counts, SHA-256 checksums, and any access failures. "
                "Existing payload files "
                "are never overwritten by this collector.\n\n"
                "The collector is in `src/data_retrieval/`. From PowerShell "
                "at the repository root, "
                "run `$env:PYTHONPATH = \"src\"` followed by "
                "`.venv/Scripts/python.exe -m data_retrieval`.\n",
                encoding="utf-8",
            )
        print(f"Raw archive: {self.raw_root}", flush=True)
        for item in summaries:
            print(f"  {item['source']}: {item['record_counts']}", flush=True)
