"""Download the published Transfermarkt player and historical match CSVs."""

from __future__ import annotations

from .common import RawCollector

DATASET_BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
PLAYER_FILES = ("players.csv.gz", "games.csv.gz", "appearances.csv.gz")


def collect_transfermarkt_datasets(collector: RawCollector) -> None:
    """Keep the publisher's compressed source files, without transforming DOBs."""
    print("Collecting Transfermarkt published player and match datasets", flush=True)
    for filename in PLAYER_FILES:
        if collector.get("transfermarkt_datasets", filename, f"{DATASET_BASE}/{filename}") is None:
            raise RuntimeError(f"Transfermarkt dataset unavailable: {filename}")
