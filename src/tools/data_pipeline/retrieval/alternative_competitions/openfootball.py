"""OpenFootball CC0 match and squad retrieval."""

from __future__ import annotations

import re
from urllib.parse import quote

from ..common import RawCollector
from .common import GITHUB_API, OPENFOOTBALL_REPOSITORIES


def _repository_start_year(path: str) -> int:
    match = re.search(r"(?:19|20)\d{2}", path)
    return int(match.group()) if match else 0


def _openfootball_path_is_in_scope(repository: str, path: str) -> bool:
    if not path.lower().endswith((".txt", ".csv", ".json")):
        return False
    if _repository_start_year(path) < 1992:
        return False
    if repository == "england":
        return path.rsplit("/", 1)[-1].lower() in {"facup.txt", "eflcup.txt"}
    return True


def collect_openfootball(collector: RawCollector) -> None:
    """Fetch CC0 match and squad files from OpenFootball, limited to 1992 onward."""
    source = "openfootball"
    print("Collecting OpenFootball international and cup files", flush=True)
    for repository in OPENFOOTBALL_REPOSITORIES:
        repository_url = f"{GITHUB_API}/openfootball/{repository}"
        metadata = collector.get_json(
            source,
            f"catalogues/{repository}_repository.json",
            repository_url,
            {"Accept": "application/vnd.github+json"},
        )
        if not isinstance(metadata, dict):
            continue
        branch = metadata.get("default_branch")
        if not isinstance(branch, str):
            continue
        tree_url = f"{repository_url}/git/trees/{quote(branch, safe='')}?recursive=1"
        tree = collector.get_json(
            source,
            f"catalogues/{repository}_tree.json",
            tree_url,
            {"Accept": "application/vnd.github+json"},
        )
        items = tree.get("tree") if isinstance(tree, dict) else None
        if not isinstance(items, list):
            continue
        selected = [
            item
            for item in items
            if isinstance(item, dict)
            and item.get("type") == "blob"
            and isinstance(item.get("path"), str)
            and _openfootball_path_is_in_scope(repository, item["path"])
        ]
        for item in selected:
            path = str(item["path"])
            raw_url = (
                f"https://raw.githubusercontent.com/openfootball/{repository}/"
                f"{quote(branch, safe='')}/{quote(path, safe='/')}"
            )
            collector.get(source, f"datasets/{repository}/{path}", raw_url)
        print(f"  OpenFootball {repository}: {len(selected)} files", flush=True)
