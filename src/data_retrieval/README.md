# Premier League raw-data retrieval

This package fetches public English Premier League and Fantasy Premier League sources and saves each response body unchanged under `data/raw/<source>/`. It uses only Python's standard library; no extra package installation is needed.

Run from the repository root:

```powershell
$env:PYTHONPATH = "src"
.venv/Scripts/python.exe -m data_retrieval
```

By default, collection includes the current FPL API and per-player summaries, the Vaastav historical FPL archive, Premier League official fixtures and ranked stats, FotMob season and match data, Understat league data plus recent shot-level match payloads, Football-Data.co.uk historical CSVs, ClubElo, and a Sofascore API access check. The optional arguments `--no-fpl-player-summaries` and `--no-fotmob-match-details` omit the largest request groups; `--sources` selects a comma-separated subset.

The collector reads JSON in memory only to discover IDs, seasons, and pages for subsequent raw requests. It does not normalize, filter, or rewrite provider payloads. Existing payload files are left in place. Each run writes timestamped retrieval records with source URLs, byte counts, hashes, and request failures.
