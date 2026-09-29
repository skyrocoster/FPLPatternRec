# Reviewed reference data

Small, version-controlled inputs used by the ingestion loaders. These are not
raw downloads, generated research reports, or a copy of the runtime database.

| File | Purpose |
| --- | --- |
| `premier_league_team_names.json` | Reviewed club identities and whole-name aliases; includes source and matching-policy notes. |
| `legacy_fpl_teams.csv` | Season-specific FPL team IDs for 2016-17 through 2018-19, from Vaastav's master team list. |
| `reviewed_player_birth_dates.json` | Individually reviewed player identities and exact birth dates, with source URLs and review notes. |

Loaders import resource paths from this package. Setuptools includes the CSV and
JSON resources in distributions. Keep schema SQL beside its ingestion owner.

Adding or changing evidence requires review; moving a file does not authorize a
database update. Provider captures remain in their existing ignored raw roots,
and SQLite remains exclusively in the named Docker volume. Research prototypes
and intermediate notes belong under `experiments/`, not here.

The club reference previously lived at
`docs/throwaway/premier-league-team-names.json`; the other two files previously
lived beside the ingestion modules. Historical records may cite those old paths.
