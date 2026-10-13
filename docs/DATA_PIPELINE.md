# Data pipeline: retrieval, staging, and proof status

The data pipeline refreshes supported provider files in the repository and has eight SQLite loaders:
official FPL teams into staging, reviewed Premier League clubs (with optional season-scoped FPL
team mappings), saved official FPL football players, and reviewed historical archive FPL players
into canonical tables, plus archived player/gameweek/team assignments, reviewed FPL fixtures,
historical FPL team-ID mappings, and Premier League local match dates.
The 2026-27 staging teams, 51 reviewed clubs, and 2,756 canonical players identified
across saved FPL seasons 2016-17 through 2026-27 are present in the named volume (2,757 before
the reviewed 2022-23 Kaine Kesler-Hayden merge described below). It also has
220 season-scoped FPL team mappings across 11 seasons, 384 gameweeks, 247,641 player/team/week
assignments, and 3,850 canonical fixtures (50 in 2026-27 through GW 5).
The proposed
staging-table inventory is not a claim that all staging schemas exist. The proposals are
sourced from [`throwaway/raw-data-staging-schemas.md`](throwaway/raw-data-staging-schemas.md).

## Retrieval commands

Run from the repository root. The Typer entry point is
`.venv/Scripts/python.exe -m tools.data_pipeline`:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve core
.venv/Scripts/python.exe -m tools.data_pipeline retrieve alternative-comps
.venv/Scripts/python.exe -m tools.data_pipeline retrieve all
```

The supported individual core commands are `official-fpl`, `fpl-archive`, `premier-league`,
`fotmob`, `understat`, `football-data`, `clubelo`, `sofascore`, `transfermarkt-datasets`,
`wikidata-players`, `wikidata-transfermarkt`, and `wikidata-transfermarkt-fpl`. The alternative-competition
commands are `fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and
`transfermarkt-injuries`. Use the `retrieve` group before an individual command, for example:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve official-fpl
.venv/Scripts/python.exe -m tools.data_pipeline retrieve openfootball --raw-root data/alternative_comps/raw
```

Core and alternative-competition files deliberately keep separate roots and provider-relative
paths:

| Retrieval group | Default raw root | Provider files |
|---|---|---|
| Core | `data/raw/` | `data/raw/<provider>/...` |
| Alternative competitions | `data/alternative_comps/raw/` | `data/alternative_comps/raw/<provider>/...` |

For player birth-date research, the initial two **core, retrieval-only** sources can be refreshed
independently (or as part of `retrieve core` / `retrieve all`); the two later ID-targeted sources
are described below:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve transfermarkt-datasets
.venv/Scripts/python.exe -m tools.data_pipeline retrieve wikidata-players
```

The first saves the publisher's gzip-compressed `players.csv.gz`, `games.csv.gz`, and
`appearances.csv.gz` under `data/raw/transfermarkt_datasets/`. These are the player profiles
and historical match links from [Transfermarkt Datasets](https://github.com/dcaribou/transfermarkt-datasets),
not pages from the existing `transfermarkt-injuries` provider. The published snapshot currently
stops on 6 July 2026 and does not cover 2026-27 squads. Preserve the original CSV bytes: the
publisher's derived `date_of_birth` field can turn a year-only date into January 1, which is
**not** an exact DOB. Games and appearances are saved for historical identity checks, not as
proof that two players with the same name are identical.

The second saves a raw Wikidata SPARQL JSON response at
`data/raw/wikidata_players/premier_league_club_players_dob.json`. Its reproducible query
selects footballers with an English label, a recorded club marked as a Premier League club,
and a birth-date statement since 1970. The response includes Wikidata player and team IDs,
the date value, and **time precision** (only day-level precision is a candidate for an exact DOB). This is
a bounded candidate set, not an exhaustive FPL player export: Wikidata's club links and
birth-date statements may be absent or disputed. The official Wikidata query service is tried
first; if it is rate-limiting or unavailable, the query uses the public QLever Wikidata mirror
instead (whose indexed copy may lag the live service). Neither retrieval writes to SQLite, matches
canonical players, or authorizes a birth-date backfill. Both use the same atomic raw-file
refresh behavior as the other providers; no host database directory or generated manifest is
created.

The first saved capture has 50,149 Transfermarkt player rows, 88,958 games, and 1,894,350
appearances. The Wikidata query service returned HTTP 429 during capture, so the QLever mirror
supplied 7,986 club/date statement rows for 5,842 distinct Wikidata people, including the
date-precision values. These are **candidate source records**, not matched canonical players
or proof that their DOBs are correct.

To review or (with **separate authorization to write the named volume**) backfill canonical
player dates from these saved files plus saved FPL and Premier League player data:

```powershell
./data.ps1 ingest player-birth-dates --dry-run
./data.ps1 ingest player-birth-dates
```

The dry run opens SQLite read-only. The write command updates only NULL `players.date_of_birth`
values in one transaction; repeat runs preserve existing dates. Direct FPL DOBs use scoped
element-code mappings; Premier League DOBs require the Opta code explicitly recorded in that
same FPL season and a matching Premier League season. External-source candidates require one
unambiguous normalized full name in each of canonical players, Transfermarkt and Wikidata;
Transfermarkt and day-precise Wikidata DOBs must agree, and a positive-minute Transfermarkt
Premier League appearance must match the canonical player's FPL-listed club in that season.
Year-only Wikidata dates, unresolved names, uncertain cross-season Opta reuse, mismatches and
unmatched players remain unfilled. Saved gameweek/team rows alone are not used as proof of an
individual appearance; they corroborate the independently recorded Transfermarkt appearance.
The saved official FPL loader preserves a subsequently reviewed DOB when its source birth
date is NULL on a repeat; a conflicting non-NULL FPL DOB still requires review.

When several sources agree on one proposed DOB, its displayed proposal category follows this
priority: saved FPL, official Premier League API Opta, official Premier League API season roster,
Transfermarkt/Wikidata corroborated by same-season club/appearance evidence, then the
Wikidata-Transfermarkt-ID name-only fallback, then the reviewed JSON fallback. This priority labels
the proposal; it does not hide disagreeing dates, which remain conflicts for review, and existing
DOBs are never overwritten.

The last-resort, manually researched records live in the tracked
[`reviewed_player_birth_dates.json`](../src/tools/data_pipeline/reference/reviewed_player_birth_dates.json)
file. It now contains 159 reviewed records; adding records is a separate research/review activity. Each entry must
contain exactly `player_id`, `display_name`, `fpl_season`, `fpl_code`, `date_of_birth`, `source_urls`,
and `review_note`: the canonical integer ID and exact stored display name, one real
`premier-league:<season>` FPL element-code mapping to that player, a real `YYYY-MM-DD` DOB, one or
more unique public HTTP(S) source URLs, and a non-empty note explaining the identity/date review.
The loader validates every entry, including exact database identity and mapping, URL shape, duplicate
entries, and disagreement with any existing DOB, before applying any updates. Manual dates join the
other evidence rather than overriding it: a disagreement with another candidate remains a conflict
and is excluded. A valid record only fills a NULL DOB; matching existing dates are left untouched.
Dry runs read both this file and SQLite without writing.

A read-only dry run against the existing volume proposed **470 of the 1,627 missing dates**:
21 directly recorded in mapped FPL observations, 26 from same-season recorded FPL/PL Opta
IDs, and 423 from unique Transfermarkt/Wikidata full-name and DOB agreement corroborated by
same-season Premier League appearance and FPL-listed club. It compared 306 already-dated
external-source controls and reported two already-dated disagreements for review (El Hadji
Malick Diouf and Jake Evans); neither existing DOB was changed. After separate authorization
and a `dev.ps1 status` check, the backfill applied those 470 dates from saved files without
retrieval. Direct read-only SQLite checks found **2,757 players, 1,600 dated, 1,157 still
missing**, unchanged 16,010 player source mappings, `PRAGMA quick_check = ok`, no foreign-key
violations, and the two disputed existing dates unchanged. Further volume writes require
separate authorization.

### ID-linked Wikidata DOB corroboration

The original name-matched Wikidata query covers only people recorded against clubs marked as
Premier League clubs, and an English label can differ from the saved FPL/Transfermarkt name.
For a second, bounded route, refresh **only** the new Wikidata Transfermarkt-ID source from
the already-saved Transfermarkt games and appearances (no database access or other retrieval):

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve wikidata-transfermarkt
./data.ps1 ingest player-birth-dates --dry-run
./data.ps1 ingest player-birth-dates --dry-run --show-candidates
```

The retrieval selects the 2,466 Transfermarkt IDs with positive-minute appearances in saved
Premier League games, asks Wikidata for its explicit Transfermarkt player ID (`P2446`) and
birth-date statement (`P569`) including day precision, and saves the original SPARQL JSON
responses in 33 deterministic batches under `data/raw/wikidata_transfermarkt/`. It queries
the QLever Wikidata mirror first, then the official endpoint if needed; mirror snapshots may lag.
A failed batch fails the retrieval, and missing or mismatched batches fail the DOB loader rather
than authorizing a partial backfill. Retrieval does not write SQLite.

For a missing canonical DOB, the loader still requires a unique normalized FPL/Transfermarkt
name, one Transfermarkt identity, a day-precise Wikidata statement whose **explicit P2446 ID**
points to that identity and whose DOB agrees with the saved Transfermarkt date, and a
positive-minute Transfermarkt Premier League appearance at the same club and season as a
canonical FPL gameweek listing. Different English Wikidata labels are allowed through this
ID-linked route; multiple Wikidata people, imprecise or conflicting dates, and missing club
evidence are not. A Wikidata statement may ultimately cite Transfermarkt, so matching dates
are corroboration with a separately recorded identity link, **not** proof of independent
primary-source birth records. Do not equate an unmatched ID or query result with no DOB existing.

After the read-only `dev.ps1 status` check, the saved-file capture and read-only volume dry run
proposed **430 additional DOBs** from this route (0 direct FPL or same-season Opta). It
cross-checked 1,060 already-dated players; the same two pre-existing disputed dates were
still flagged. Three proposed birthdays are January 1. With subsequent explicit authorization,
the backfill applied exactly these 430 NULL-only dates. Direct read-only SQLite checks found
**2,757 players, 2,030 dated, 727 still missing**, unchanged 16,010 player source mappings,
`PRAGMA quick_check = ok`, no foreign-key violations, and both disputed existing DOBs unchanged.
Future volume writes require a preceding `dev.ps1 status` check and authorization.

### FPL-name-targeted Wikidata ID follow-up

With explicit approval to accept a **unique exact FPL/Transfermarkt normalized full name**
and a Wikidata `P2446` identity link **without an independently confirmed appearance**, the
additional retrieval command reads all 11 saved FPL player lists and the saved Transfermarkt
profiles, excluding FPL assistant managers:

```powershell
.venv/Scripts/python.exe -m tools.data_pipeline retrieve wikidata-transfermarkt-fpl
./data.ps1 ingest player-birth-dates --dry-run --show-candidates
```

It selects 2,449 Transfermarkt IDs whose names occur among saved FPL footballers and stores
the original `P2446`/`P569` SPARQL JSON in 33 complete batches under the separate ignored
`data/raw/wikidata_transfermarkt_fpl/` path. This retrieval neither reads nor writes SQLite.
The loader still requires one canonical player and one Transfermarkt record for the full
normalized name, one Wikidata person linked by **that Transfermarkt ID**, day precision,
exact date agreement, and no contradictory linked Wikidata dates or IDs. Its dry-run summary
separates this weaker name-and-ID route from dates supported by same-season club/appearance
evidence; missing/incomplete source batches fail before any database changes. Exact names
can still refer to *different people*: the already-dated Cameron Humphreys is a concrete
counterexample (current canonical DOB 2003-10-30; other same-name Transfermarkt identity
1998-08-22). This method is explicitly **not proof of appearance or infallible identity**.

After a `dev.ps1 status` check, the authorized volume backfill filled **399** previously NULL
dates on this route, with 0 additional strict-route dates. A read-only audit found 2,757
players, **2,429 dated, 328 still NULL**, unchanged 16,010 source mappings,
`PRAGMA quick_check = ok`, and zero foreign-key violations. The existing dates for El Hadji
Malick Diouf, Jake Evans, and Cameron Humphreys were not overwritten; all three remain
flagged for review. A repeat dry run now proposes **zero** dates under either supported
automatic route. Reaching only a handful of NULLs is not currently justified by either
saved-data route: at least 216 of the 328 lack an exact-name Transfermarkt record, 18 have
multiple same-name Transfermarkt records, and five collide in canonical names. Official
Premier League pages offer some further name/season DOB observations, but no general
cross-provider identity key for these historical players; further automatic fills require
new verified links or a separately reviewed change in matching policy.

### Final reviewed player birth dates

Later backfills reduced the remaining NULL count to 159. After individual identity and
exact-date review, the 159 source-linked records in `reviewed_player_birth_dates.json`
were applied through `ingest player-birth-dates`. This is a manually reviewed fallback,
not a relaxation of the automatic matching rules. The reviews distinguish same-club
namesakes (including Fernando Reges from Fernandinho and Mika from Vito Mannone), and
record how conflicting date claims were resolved. For Tom Taylor, two player profiles
agree on 21 February but disagree on the year; Cheltenham Town's dated announcement
that he turned 20 in February 2025 supports the reviewed 2005 birth year. The research
and follow-up notes are under `experiments/prototypes/dob-research/reviews/dob-159-*.json`.

A subsequent direct read-only SQLite check found **2,757 players, 2,757 dated, zero
missing DOBs**, unchanged 16,010 player-source mappings, `PRAGMA quick_check = ok`,
and zero foreign-key violations. The three previously flagged *already-dated*
disagreements (El Hadji Malick Diouf, Cameron Humphreys, and Jake Evans) were not
overwritten and still merit separate review; they are not missing dates. Future volume
writes still require separate authorization and a preceding `dev.ps1 status` check.

Single-group and individual-provider commands accept `--raw-root`. `retrieve all` accepts separate
`--core-raw-root` and `--alternative-raw-root` options; it does not merge the roots. Official FPL
retrieval continues to request the bootstrap, fixtures, current live snapshots, and player
summaries by default. The teams loader does not trigger retrieval or discard other saved FPL files.

Every refresh fetches a new response even if its destination exists. On success, the complete
response replaces only that provider-relative file using a temporary sibling and atomic replace.
If the request or file write fails, the previous file stays byte-for-byte intact and the temporary
file is cleaned up. Payload bytes are preserved; this workflow adds no new capture history or
retrieval manifests.

## Ingestion command and shared-volume boundary

The existing staging loader is:

```powershell
./data.ps1 ingest official-fpl-teams
./data.ps1 ingest official-fpl-teams --raw-root data/raw --season 2026-27
```

These examples document command syntax; they are not authorization to write the shared volume.
Ingestion changes the named SQLite volume. Wait for separate authorization before running it. When
the authorized volume workflow is performed, begin with the read-only `dev.ps1 status` check.

Without `--raw-root`, it reads `data/raw/official_fpl_api/bootstrap-static.json`. An override reads
`official_fpl_api/bootstrap-static.json` below that root. Unless `--season YYYY-YY` is supplied,
the loader derives the season from the first gameweek deadline. It validates the complete teams
array before changing the database and replaces only the chosen season's team rows. Empty
`link_url` values become SQL `NULL`; reloading the same season replaces its rows rather than
duplicating them.

`data.ps1` forwards its arguments to the `data-tools` one-shot Compose service. The service binds
the checkout at `/workspace` for code and raw-file access and mounts the existing
`fplpatternrec-sqlite` named volume at `/data`; the database path inside the container is
`/data/fplpatternrec.db`. It runs with `--no-deps` and is not one of the four persistent services
managed by `dev.ps1`. Retrieval uses the checkout's raw files and does not read or write SQLite;
the `ingest` commands write their specified staging or canonical tables in the named volume.

The authorized shared-volume proof ran `ingest official-fpl-teams` as root using a per-command
`--user 0:0` override because the existing database is root-owned and the image's default `app`
user cannot write it. Canonical teams ingestion also uses a per-command root override for this
root-owned database; retrieval keeps the image's default non-root user. No database ownership or
permissions were changed.

Do not create or mount a host `data/` or `data/database/` directory for SQLite. `dev.ps1 setup`
creates the database only when absent. For an existing file it requires `PRAGMA quick_check` to
return `ok`, then leaves it unchanged regardless of table count; setup does not reset, migrate, or
delete tables. A missing or corrupt database needs operator attention rather than a host-side
workaround.

The staging loader is implemented and tested with temporary fixture databases. Its authorized
named-volume proof used the existing raw bootstrap, loaded the teams twice, and verified the same 20 rows for
2026-27 after both runs. A subsequent `dev.ps1 setup` reported that the valid table-bearing database
was left unchanged; a final read-only check confirmed its schema, rows, and integrity. No live
retrieval or raw-file changes were part of the proof. Any future operation that creates or writes
the shared database still requires separate authorization and must begin with the read-only
`dev.ps1 status` check.

After a read-only `dev.ps1 status` check, the canonical schema was installed with
`./data.ps1 ingest canonical-schema` on the existing staging-only database. The command checks
`PRAGMA quick_check`, refuses unrecognized or pre-existing canonical tables, and is **not** a
migration to rerun. The seed-only canonical loader populated the volume first; the season-scoped
mapping form was run later:

```powershell
./data.ps1 ingest canonical-teams
./data.ps1 ingest canonical-teams --season 2026-27
```

Both loader forms require `base_tables.sql` to have been applied first. Without `--season`, the
loader reads `src/tools/data_pipeline/reference/premier_league_team_names.json` (override with
`--team-reference PATH`) and seeds all 51 reviewed club identities directly. It needs no staging table, adds no
season or competition, and does not imply every club played in any particular season.

With `--season`, it additionally requires populated `stg_official_fpl_teams` for that season,
adds the Premier League competition and season, and resolves FPL team names using only reviewed
whole-name aliases. Accepted FPL team IDs are stored as text in `team_source_ids` under namespace
`fpl.team.id` and scope `premier-league:<YYYY-YY>`. The mapping includes only staged teams for
the requested season. Neither form loads players, managers, fixtures, source codes, or Pulse IDs.
Both refuse conflicting canonical rows and preserve existing IDs and unrelated rows; repeat loads
are idempotent. Both forms have been run in the volume: the `--season 2026-27` load mapped all
20 staged FPL team IDs to 20 distinct reviewed clubs. A read-only check after the load found
20 scoped mappings, the original 51 clubs and 20 staged teams, unchanged player/gameweek counts,
`PRAGMA quick_check = ok`, and no foreign-key violations.
Further volume writes require authorization and a read-only `dev.ps1 status` check first.

The first canonical player loader reads the saved official FPL bootstrap directly, not the
unimplemented `stg_official_fpl_elements` proposal:

```powershell
./data.ps1 ingest canonical-players --season 2026-27
```

The requested season must agree with the first gameweek deadline in the payload. `--raw-root`
can select another core raw root. The loader uses full FPL first/second names for `display_name`,
valid non-null `birth_date` values for `date_of_birth`, and creates a new project-generated ID
for each previously unmapped football player. It excludes `element_type = 5` managers, rejects
unknown types, and never derives identity from a name or across seasons from a provider code.
`fpl.element.id` and `fpl.element.code` have separate `player_source_ids` mappings, each scoped
to `premier-league:<YYYY-YY>`; even numeric-looking source IDs are stored as text. Repeat loads
retain player IDs and unrelated rows, but conflicting mappings, existing unmapped names, or
changed canonical details require review and roll back the whole load. This is not an archive
loader, a historical deduplication policy, or an element staging table.
The authorized 2026-27 player load resolved 667 football players, excluded zero manager entries,
and created 667 mappings in each of the two scoped FPL namespaces. The database's 51 clubs and
20 staged teams were unchanged. No retrieval or raw-file refresh was run.

The historical loader reads each saved Vaastav copy of FPL's `players_raw.csv` and checks
its IDs and names against that season's `player_idlist.csv`. It supports 2016-17 through
2025-26, **newest first**, after the official 2026-27 bootstrap load:

```powershell
./data.ps1 ingest canonical-archive-players --season 2025-26
./data.ps1 ingest canonical-archive-players --season 2024-25
# Continue one season at a time down to --season 2016-17.
```

An optional `--raw-root` changes the core raw root. The archived FPL `code` and corroborating
name/birth date can link an earlier season's source IDs to a later canonical player;
`id` is strictly season-scoped and is never matched across seasons. A birth-date conflict,
uncorroborated name, temporary code, partial mapping, or unreviewed same-name code collision
aborts that season's transaction. Early archive seasons do not contain birth dates, so they
require a common significant name token alongside the same FPL code. Differences in FPL
spellings or missing birth dates do not overwrite already accepted canonical fields.
Archive-only football players get new project-generated IDs. Both `fpl.element.id` and
`fpl.element.code` are mapped to `premier-league:<YYYY-YY>`, not `global`. The 2024-25
archive contains 20 `element_type = 5` assistant-manager observations; they remain in
the raw archive, never canonical players or player ID mappings. This is not a manager import.

The saved-file audit of all 11 seasons found no different dates of birth for any repeated
footballer code; repeated codes retain a common significant name token. Seven pairs of
different FPL codes have the same full name. Six are reviewed **different players**: Aaron
Ramsey (codes 41792/447715), Joshua King (78007/577725), James Wilson (112139/613232),
Ben Davies (115556/152898), Danny Ward (75826/95463), and Álvaro Fernández
(240796/515501). The last three pairs occur in the same season; the first three include
later players born in 2003 or 2007, not the earlier adult players. The seventh pair is one
reviewed **same player across an FPL code change**: 2019-20 Aston Villa element 659,
Kaine Hayden, code 490098, and later code 465390 for Kaine Kesler-Hayden. The older row
has no birth date; its same club, name and later [youth-career evidence](https://en.wikipedia.org/wiki/Kaine_Kesler-Hayden)
justify this one explicit exception. It is guarded by season, element ID, name, and source
team code. An eighth reviewed **same player across a second FPL code change** covers the
2022-23 Aston Villa element 537, Kaine Kesler Hayden without hyphen, code 537043, on
season-long Huddersfield loan: same birth date 2002-10-23, same team_code 7, and FPL
reverted to 465390 afterwards. Its hyphen/space name difference previously bypassed the
exact normalized-name review guard and silently split the identity; the loader now also
checks a punctuation-folded name form to force review of such near-identical unmapped
names instead of inserting. Both exceptions are guarded by season, element ID, name, and
source team code. No general name-plus-team auto-merge is permitted.

**Transfers:** `players_raw.csv.team` is a season-end snapshot, not an employment history.
For example, the saved `gws/merged_gw.csv` shows Wissa at Brentford and Newcastle under
one element ID, and Buonanotte at Brighton, Chelsea, and Leeds. The loader never stores a
team, position, squad stint, or transfer on `players`. Those gameweek observations remain
in the saved archive for a later staging/appearance loader; the canonical identity does not
change on transfer. The historical loads are not transfer-history imports and do not
establish who played for whom on a given date.
The authorized 2025-26 archive load resolved 841 football players: 480 linked to existing
2026-27 player IDs, 361 added as archive-only identities, and zero managers. It created 841
season-scoped mappings in each FPL element namespace. The 51 clubs and 20 staged 2026-27
teams were unchanged. No raw-file refresh or historical team/transfer import was run.

The remaining nine archive seasons (2024-25 back through 2016-17) were subsequently loaded
newest-first from the saved files. They supplied 6,497 football-player observations; 20
additional 2024-25 manager observations were excluded. All 11 seasons' players have both
season-scoped FPL ID and code mappings. The 2026-27 official bootstrap contains all 616
players in the saved 2026-27 archive plus 51 others; importing its archive snapshot would
not add distinct identities. The resulting 2,756 canonical identities are two fewer than
the 2,758 distinct imported FPL codes because of the two reviewed Kaine code changes
(490098 to 465390, and one-season 537043 back to 465390).
This is not an authoritative season squad, transfer, or complete footballer directory;
the player-identity loader alone does not populate `seasons`, player-team stints, or gameweeks.

### Gameweeks and player-team assignments

After canonical players and reviewed clubs exist, load the saved historical seasons with
identifiable FPL clubs:

```powershell
./data.ps1 ingest player-gameweek-teams --season 2016-17
# Repeat for each completed historical season through 2025-26.
```

For **2026-27, including GW 1**, the same command reads saved **official FPL**
`bootstrap-static.json`, `fixtures.json`, and every footballer's `element_summaries/element_*.json`
instead of the Vaastav archive. Completed fixtures and each player's per-fixture history establish
their club in that week; the current bootstrap club is not used to guess earlier clubs after a
transfer. GW 1's previously loaded archive-derived rows must agree *exactly* with this official
history before later weeks can be appended. Existing player/week identities and assignments are
preserved; missing or changed old rows abort the transaction. A zero-minute history entry still
means an FPL-listed club, not an appearance. The saved official snapshot currently has GW 1–5
history; archived GW 1 alone is not the current-season ingestion source going forward.

`--raw-root` selects a different core raw root. This command creates the Premier League competition
and its season in the existing canonical tables, then adds `gameweeks` (one per saved FPL week
number in that season) and `player_gameweek_teams` (one canonical player/club/week assignment).
The latter stores the season-scoped FPL element ID, first and last fixture kickoff, number of
fixture observations, and number with positive minutes. Zero minutes means FPL listed the player
for that team/week, **not** that the player appeared. The kickoff range is not a contract or
transfer interval. Multiple fixture records in one week are grouped by player and club; identical
duplicate raw rows are counted once. A postponed fixture can legitimately occur in different
source-labelled weeks. The command validates fixture teams and opponents against saved FPL
fixture evidence, reviewed club aliases, and both canonical player-source mappings before changing SQLite. Repeat
loads preserve IDs and rows; changes to previously loaded rows require manual review, not replacement.
Historical seasons still reject partial prior loads; the current official season can only grow.

The 2016-17 through 2018-19 archives lack `teams.csv`; their season-specific FPL ID/name
lookup is retained in [`legacy_fpl_teams.csv`](../src/tools/data_pipeline/reference/legacy_fpl_teams.csv),
from Vaastav's [master team list](https://github.com/vaastav/Fantasy-Premier-League/blob/master/data/master_team_list.csv).
The 2018-19 archive has `fixtures.csv` with both team IDs. The 2016-17 and 2017-18 archives
lack that file, so the loader requires *both* sides of every saved FPL fixture to agree:
each side names the other's season-specific team ID in `opponent_team`, and `was_home`
identifies which side is home. Missing or contradictory fixture sides abort the whole season;
the season-end team in `players_raw.csv` is never used to infer a weekly club. All 380
fixture identities and UTC kickoffs per season in 2016-17 through 2018-19 were independently
matched against the saved Premier League fixture schedule (380/380 each).

The 2019-20 `merged_gw.csv` has no `team` column, but the archived `fixtures.csv`, `teams.csv`,
`was_home`, and `opponent_team` establish the club for each fixture. Its saved `GW` values run to
47 after the pandemic pause (38 populated week labels); they are retained as source labels, not
renumbered. From 2020-21 onward the direct gameweek team label is also checked against the
fixture. The saved 2022-23 gameweek file has 37 populated weeks (GW 7 is
absent); the saved 2026-27 **archive** file covers only GW 1. The current official bootstrap has
51 more players than that archive snapshot, so those 51 are not assigned a guessed GW 1 team.

The initial separately authorized named-volume load began with `dev.ps1 status`, ran eight seasons
from saved files without retrieval, and left 2,757 players, 51 clubs, 16,010 player source
mappings, and 20 staged teams unchanged. Read-only Datasette checks found **8 seasons, 266
gameweeks and 178,998 player/team/week rows**, zero mismatched scoped player IDs, and zero
dangling player, club, gameweek, or season links. For example, the 2025-26 rows show Wissa at
Brentford for GW 1–3 and Newcastle for GW 4–38; Buonanotte appears at Brighton for GW 1–3,
Chelsea for GW 4–21, and Leeds United for GW 22–38. These are FPL team associations, not
confirmed employment or appearance histories. The Datasette query endpoint does not provide
`PRAGMA quick_check` or `PRAGMA foreign_key_check` on the live volume; isolated full-season tests
did pass `foreign_key_check`.

A subsequent authorized load added the three earlier seasons from the saved gameweek files and
the retained historical FPL team lookup, without replacing any existing season. They added
38 gameweeks each and respectively 23,106 (2016-17), 21,797 (2017-18), and 21,134 (2018-19)
player/team/week associations. At that earlier point, the named volume had **11 seasons, 380
gameweeks and 245,035 player/team/week rows**. A direct read-only SQLite check returned `PRAGMA quick_check = ok`,
no `PRAGMA foreign_key_check` violations, and zero player/team/week rows with a mismatched
season-scoped FPL player ID. Its 2,757 players and 51 clubs remain unchanged.

### Canonical matches from saved FPL seasons

After a season's player-gameweek teams exist, the fixture loader accepts saved archive seasons
2016-17 through 2025-26 and official FPL for 2026-27 (no retrieval or raw-file update):

```powershell
./data.ps1 ingest canonical-fixtures --season 2016-17
# Repeat for completed historical seasons through 2025-26; then 2026-27.
```

For **2026-27, including GW 1**, this command now checks finished matches against the saved
official FPL fixtures and player history, not the archive. It preserves the ten existing GW 1
fixture IDs and links only when all their facts agree with the official records, then adds newly
finished matches and links; scheduled matches stay out. Run the official 2026-27
`player-gameweek-teams` command first, and `match-dates --season 2026-27` afterward to date
only newly added fixtures using the saved Premier League pages. These commands were tested
on isolated SQLite databases before the separately authorized shared-volume load.

After explicit authorization and a fresh `dev.ps1 status` check, the three 2026-27 ingestion
commands ran in that order without refreshing the saved files. Direct read-only SQLite checks
found **5 gameweeks with 3,216 player/team/week rows** (610, 626, 654, 659, 667 respectively),
**50 finished fixtures and 50 fixture/gameweek links** (10 per week), and 50 populated local
`match_date` values. The existing GW 1 gameweek ID 266, all 610 GW 1 assignments, and FPL
fixture IDs 1–10 mapped to canonical fixture IDs 3801–3810 with their original dates were
preserved. Across all seasons the volume now has 384 gameweeks, 247,641 player/team/week rows,
and 3,850 fixtures/source mappings/week links. `PRAGMA quick_check = ok`, no foreign-key
violations, no unlinked or cross-season fixtures, and no NULL match dates in 2026-27.
Further volume writes still need authorization and a preceding `dev.ps1 status` check.

For 2016-17 through 2025-26 it reads `fixtures.csv`, `teams.csv` where available,
`players_raw.csv`, and `gws/merged_gw.csv` under `data/raw/fpl_archive_vaastav/`
(or `--raw-root`). For 2016-17 and 2017-18, which lack
`fixtures.csv`, both archived gameweek sides must agree on every fixture's clubs, score, kickoff
and week; 2018-19 uses the reviewed legacy FPL club lookup with its saved fixture file. A
completed match needs confirmed finished flags (or corroborated historical two-sided results),
a final score, reviewed clubs, and a UTC kickoff. Fixture identity, FPL event, score and kickoff
are checked against the saved player/team observations and the **existing** grouped
`player_gameweek_teams` rows. Missing or changed evidence, partial prior historical fixtures, and
conflicting mappings abort rather than filling gaps. Accepted IDs use namespace `fpl.fixture.id`
and scope `premier-league:<YYYY-YY>`; repeat loads
retain the original canonical IDs. Fixture ingestion left `match_date` NULL because that field
requires an agreed competition-local timezone date; `kickoff_at` stores the known
UTC instant. A later, separately authorized backfill populated the dates from saved official
Premier League local kickoff labels, as described below. The saved FPL
`event` is stored as a validated link between each fixture and its existing FPL `gameweeks` row in
the separate `fixture_gameweeks` table. The canonical fixture itself has no competition round or
gameweek column. Linking a player's listed club and week to those matches identifies candidate
fixtures, **not** which match the player appeared in; no employment stint is inferred.

The authorized named-volume load inserted **380 finished fixtures and 380 FPL fixture-ID mappings**
for 2025-26, with all 20 clubs on each side across the season. A direct read-only check found
no unmapped fixtures or missing scores/kickoffs, `PRAGMA quick_check = ok`, zero foreign-key
violations, and unchanged club, player, gameweek, player/team/week and FPL team-mapping counts.
A later authorized repeat of the same command retained all 380 fixture identities and added
**380 fixture/gameweek links** spanning all 38 saved FPL weeks. Read-only checks found zero
unlinked fixtures, zero cross-season links, `PRAGMA quick_check = ok`, and no foreign-key
violations. All 29,338 2025-26 player/team/week rows have at least one match candidate for their
club and week; some weeks have two matches for one club (for example Arsenal in GW 26), so this
join is not proof of an individual appearance.

A further authorized run loaded each remaining saved season without refreshing raw files. At that
earlier point, the volume held **3,810 finished canonical fixtures, 3,810 season-scoped FPL fixture-ID mappings,
and 3,810 fixture/gameweek links**: 380 matches in each season 2016-17 through 2025-26, plus the
10 completed GW 1 matches in 2026-27. All 245,035 player/team/week rows have at least one
club/week match candidate; this is not proof of a particular appearance. Read-only SQL found no
unmapped or unlinked fixtures, no links crossing seasons, no missing scores or UTC kickoffs,
`PRAGMA quick_check = ok`, and zero foreign-key violations. Players, clubs, gameweeks,
player/team/week assignments, and FPL team mappings are unchanged.

**Source gaps and reviewed exceptions (at the earlier archive-backed volume proof):** the saved
2026-27 archive contains 370 more *scheduled* fixtures without a finished result or
player-gameweek evidence. They were not written as finished matches or linked to invented future
gameweeks; canonical coverage in the named volume stopped at GW 1 until the separately
authorized official-FPL load described above. The newer saved official FPL capture includes 40
further finished matches across GW 2–5; it is not interchangeable with the stale archive snapshot. Saved
2022-23 has no GW 7 in either fixture events or player observations (37 populated weeks), but
its 380 completed matches are accounted for. In 2019-20, FPL fixture ID 275 appears in 59 saved
player-fixture rows under its original, scoreless GW 29 slot (`2020-03-11T19:30:00Z`) and again
under its completed GW 39 slot (`2020-06-17T19:15:00Z`, 3–0). Its canonical match links only
to the completed fixture event GW 39; the original GW 29 player observations remain in their
gameweek records, not a fabricated second match. In 2021-22, fixture 263 has 78 saved player
rows at 15:00 UTC, whereas the finished fixture record gives 15:30 UTC; the canonical kickoff
uses the finished fixture time, while the historical gameweek observation range is unchanged.
These two exceptions are guarded by their exact season, fixture ID, week and kickoff in the
loader; changed evidence requires review. Individual player-to-match participation remains
unresolved, especially where a club has multiple fixtures in one FPL week. In particular, a
club/week join can return another match for one of the original 2019-20 GW 29 postponement
observations; it must not be presented as that player's match appearance.

At the time of that fixture load, 1,627 players lacked a birth date (all have since been
backfilled), and 57 of the 667 2026-27 mapped players have no saved GW 1 team assignment.
No missing assignments or dates were
inferred during fixture ingestion.

### Player/fixture observations from saved FPL seasons

After a season's canonical fixtures exist, one row per canonical fixture/player
listing is loaded from the same saved evidence (no retrieval or raw-file update):

```powershell
./data.ps1 ingest player-fixture-observations --season 2016-17
# Repeat one saved season at a time through 2026-27.
```

For 2016-17 through 2025-26 it reads the saved Vaastav gameweek files;
for 2026-27 it reads the saved official FPL fixtures and element-summary
histories, not the stale archive snapshot. Each wide row stores the canonical
fixture, player, club, gameweek, season-scoped FPL element ID, minutes, plus
per-match FPL stats: goals, assists, clean sheets, goals conceded, own goals,
penalties saved/missed, cards, saves, bonus, bps (which can be negative),
total points, starts, tackles, recoveries, clearances-blocks-interceptions,
defensive contribution, ICT (influence/creativity/threat/index), expected
goals/assists/involvements/conceded, archive-only expected points (`xP`, NULL
for official 2026-27), and the saved value/selected/transfers snapshot.
Positive minutes mean an appearance; zero means FPL listed the player without
playing. Early-only detail (attempted passes, big chances, dribbles,
`ea_index`, errors, fouls, key passes and similar) and manager-only `mng_*`
columns are not canonical stats. A second table,
`player_fixture_observation_fixtures`, marks each processed fixture so a repeat
can tell a complete season from a partial write. Archive seasons must agree
exactly on repeat; the current official season only appends newly finished
fixtures and rejects changed old rows. A pre-stats narrow table is widened
in place with nullable stat columns and backfilled in the same transaction.
All 11 seasons were loaded newest-evidence-first after authorization and a
`dev.ps1 status` check, then 2025-26 was repeated to prove stability
(identical summary, total unchanged).

Direct read-only SQLite checks found **256,725 player/fixture observations
(110,219 with minutes, 146,506 zero-minute listings)** and **3,850 processed
fixtures** (380 per archived season, 50 for 2026-27):

| Season | Observations | With minutes | Zero-minute |
|---|---|---|---|
| 2016-17 | 23,679 | 10,474 | 13,205 |
| 2017-18 | 22,467 | 10,448 | 12,019 |
| 2018-19 | 21,790 | 10,480 | 11,310 |
| 2019-20 | 22,501 | 10,614 | 11,887 |
| 2020-21 | 24,365 | 10,393 | 13,972 |
| 2021-22 | 25,447 | 10,485 | 14,962 |
| 2022-23 | 26,505 | 11,345 | 15,160 |
| 2023-24 | 29,725 | 11,384 | 18,341 |
| 2024-25 | 27,283 | 11,566 | 15,717 |
| 2025-26 | 29,747 | 11,492 | 18,255 |
| 2026-27 | 3,216 | 1,538 | 1,678 |

Spot checks passed: Saliba (element 6) in 2025-26 GW 26 has fixture 252 = 0
minutes and fixture 310 = 90 minutes for Arsenal; 2019-20 fixture 275 has zero
match-level rows under GW 29 and 60 rows under the completed GW 39 fixture.
`PRAGMA quick_check = ok` with zero foreign-key violations. The precise source
exception: the 59 scoreless original GW 29 listings for postponed 2019-20
fixture 275 (`2020-03-11T19:30:00Z`) stay only in the gameweek aggregates and
are excluded from the observations by exact season, fixture ID, week, and
kickoff; the loader aborts if that postponed set is not exactly 59 rows.
Listings identify candidate fixtures, not confirmed appearances, especially
where a club has two matches in one FPL week. Isolated-database checks prove
2025-26 (29,747 wide rows, 1,005 goals, 34,382 points), 2019-20 narrow NULLs
(starts/expected NULL), 2016-17 tackles, and official 2026-27 (3,216 wide rows,
`expected_points` NULL). After authorization and a `dev.ps1 status` check, all
11 seasons were widened and backfilled in the named volume from saved files
without retrieval. Direct read-only SQLite checks found **256,725 wide rows,
10,533 goals, 9,561 assists, 24,613 bonus, 320,765 points, zero NULL
`goals_scored`**, 140,249 NULL starts/expected (pre-2022 seasons) and 163,072
non-NULL archive `xP`, `PRAGMA quick_check = ok`, and zero foreign-key
violations. Further volume writes still need authorization and a preceding
`dev.ps1 status` check.

### Local match-date backfill

The saved official Premier League fixture pages provide a local `kickoff.label` with `BST` or
`GMT` and a UTC `kickoff.millis`. A direct, read-only audit matched every one of the 3,810
canonical completed fixtures by season, reviewed home/away club, exact UTC kickoff and final
score; all local labels agreed with their timestamps. Saved Football-Data dates independently
agreed for all 3,810, but this loader uses **only** the Premier League source for dates:

```powershell
./data.ps1 ingest match-dates --season 2016-17
# Repeat one saved season at a time through 2026-27, with volume-write authorization.
```

The loader parses the explicitly zoned local label, checks its weekday and UTC timestamp,
requires all saved pages, and compares every canonical fixture in that season with a uniquely
identified completed Premier League match. It updates only NULL `fixtures.match_date` values.
Historical seasons still reject partial prior dates; the current official season accepts new NULL
dates alongside previously checked dates. Changed existing dates, incomplete historical fixture
seasons, changed source evidence and uncertain matches abort without replacement. The FPL fixture
loader preserves
accepted dates when rechecking the rest of a season's fixture facts. No dependency on Windows
timezone data, retrieval refresh or new table is needed. The current 2026-27 season remains
partial: only completed matches already loaded into `fixtures` are eligible; scheduled fixtures
are not imported by this date loader.

At the earlier date-backfill proof, after separate authorization and a `dev.ps1 status` check,
all 11 saved seasons were loaded from existing files without retrieval. Direct read-only SQLite
SQL confirmed **3,810 populated
`match_date` values, zero NULLs**, exact agreement with saved Premier League dates/kickoffs/scores
for every canonical fixture, `PRAGMA quick_check = ok`, and zero foreign-key violations. The 51
clubs, 2,757 players, 3,810 fixture identities, 245,035 player/team/week assignments, and 220
FPL team mappings were unchanged. Future volume writes require separate authorization.

### Historical FPL team-ID backfill

The saved Vaastav `teams.csv` files for 2019-20 through 2025-26 and the reviewed
`legacy_fpl_teams.csv` lookup for 2016-17 through 2018-19 contain all 20 season-specific team
IDs for each of those ten seasons. These IDs are **not** global club identities; the same FPL
team ID can identify a different club in another season. Before the load, read-only SQL confirmed
all ten historical scopes had zero mappings, while each had 380 canonical fixtures whose clubs
matched the 20 saved IDs. Isolated-database tests cover all ten saved seasons. The loader is:

```powershell
./data.ps1 ingest canonical-archive-teams --season 2025-26
# Repeat one season at a time down to 2016-17, with volume-write authorization.
```

It resolves only reviewed whole-name club aliases and requires the existing canonical season,
reviewed clubs, and 380 finished fixtures covering its 20 clubs. It inserts only the 20 missing
`fpl.team.id` mappings in `team_source_ids` under `premier-league:<season>`; it never reassigns
IDs, creates clubs or seasons, or changes fixture/player data. An identical repeat preserves the
canonical mappings, while partial mappings or source changes that alter reviewed club identity
fail rather than replacing history. No retrieval is needed. After separate authorization and a
`dev.ps1 status` check, all ten seasons were loaded newest-first into the named volume. Direct
read-only SQLite SQL found 20 correct mappings per historical season, plus the unchanged 20 for
2026-27 (**220 total**), `PRAGMA quick_check = ok`, no foreign-key violations, and unchanged
counts of 51 clubs, 2,757 players, 3,810 fixtures, and 245,035 player/team/week assignments.
Further volume writes still require separate authorization and a preceding status check.

## Staging-table inventory

The schema proposal names 53 staging tables. Only `stg_official_fpl_teams` has a staging loader in
this slice. It is implemented, locally tested, and **created and proven in the named volume** for season
2026-27. The other 52 tables are future proposals, not implemented or proven by this pipeline.

| Provider | Proposed staging table | Current status |
|---|---|---|
| Football-Data | `stg_football_data_all` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_players` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_teams` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_fixtures` | Future; not implemented or proven. |
| Vaastav archive | `stg_vaastav_player_gameweeks` | Future; not implemented or proven. |
| Understat | `stg_understat_league_teams` | Future; not implemented or proven. |
| Understat | `stg_understat_team_match_history` | Future; not implemented or proven. |
| Understat | `stg_understat_league_players` | Future; not implemented or proven. |
| Understat | `stg_understat_league_matches` | Future; not implemented or proven. |
| Understat | `stg_understat_match_shots` | Future; not implemented or proven. |
| Understat | `stg_understat_match_rosters` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_teams` | Created and proven in the named volume for 2026-27 (20 teams; repeat load stable; setup preserved the table). |
| Official FPL | `stg_official_fpl_element_types` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_phases` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_chips` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_stats` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_elements` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_events` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_event_chip_plays` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_fixtures` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_fixture_stats` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_history` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_history_past` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_element_upcoming_fixtures` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_live_gameweek` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_live_explain` | Future; not implemented or proven. |
| Official FPL | `stg_official_fpl_snapshot` | Future; not implemented or proven. |
| Premier League API | `stg_pl_seasons` | Future; not implemented or proven. |
| Premier League API | `stg_pl_clubs` | Future; not implemented or proven. |
| Premier League API | `stg_pl_teams` | Future; not implemented or proven. |
| Premier League API | `stg_pl_players` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixtures` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixture_teams` | Future; not implemented or proven. |
| Premier League API | `stg_pl_fixture_goals` | Future; not implemented or proven. |
| Premier League API | `stg_pl_stat_values` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_leagues` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_league_group_membership` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_seasons` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_teams` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_season_standings` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_season_archive` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_fixtures` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_events` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_lineups` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_lineup_players` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_player_stats` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_team_stats` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_shots` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_match_momentum` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_stat_catalogue` | Future; not implemented or proven. |
| FotMob | `stg_fotmob_stat_leaders` | Future; not implemented or proven. |

The 53 rows comprise one locally implemented and temporary-database-verified table plus 52 future
proposals. The proposal's empty-field, provider-local key, and type details are not additional DDL
or implementation approval.

### Separate canonical base-table schema

The independent [canonical base-table proposal](grilling-docs/base-tables-schema.md) lists eight
tables. Their SQLite DDL is in
[`src/tools/data_pipeline/ingestion/base_tables.sql`](../src/tools/data_pipeline/ingestion/base_tables.sql)
and is verified against temporary SQLite databases. It has been applied to the shared named volume
without modifying the existing staging rows. The volume has 51 canonical `teams` and 2,757 canonical
`players` rows. Saved historical archives and official current-season FPL have canonical fixture
loaders; 2026-27 in the volume is currently partial. These are not staging tables:

`competitions`, `seasons`, `teams`, `players`, `fixtures`, `team_source_ids`, `player_source_ids`,
and `fixture_source_ids`. The subsequently installed `gameweeks`, `player_gameweek_teams`,
and `fixture_gameweeks` are separate tables, not part of that one-time eight-table base DDL.

Do not rerun this SQL as a migration; future schema changes need explicit review. It uses SQLite
STRICT tables (SQLite 3.37+), generated integer IDs, and foreign keys. Enable
`PRAGMA foreign_keys = ON` on **every** writing connection (the existing
data-pipeline SQLite connector does so). Store dates as `YYYY-MM-DD` and known UTC kickoff instants
as `YYYY-MM-DDTHH:MM:SSZ`; the schema permits unknown dates and times. The SQL enforces local
identity, status, score, and key constraints, not provider identity resolution or manager exclusion:
loaders must keep unresolved/manager observations in staging and validate real calendar dates,
source timezone, local `match_date` versus UTC kickoff agreement, fixture matching, and canonical
field authority before writing. Reapplying the DDL is not a migration for changed existing tables.

### Retrieval providers without staging tables

| Retrieval providers | Current status |
|---|---|
| ClubElo and SofaScore | No usable payload in the proposal review; no staging table proposed. |
| `fotmob-competitions`, `openfootball`, `wikipedia-competitions`, and `transfermarkt-injuries` | Retrieval-only; staging shape not proposed. Do not infer or invent staging tables for these commands. |

The `stg_fotmob_*` proposals above refer to the core FotMob provider schema; they do not define a
staging shape for the separate alternative-competition FotMob command.

## Proof status

The focused retrieval and provider tests (19 passed), local teams-loader/CLI tests (19 passed), and
updated CLI command-forwarding tests (14 passed) are retained proof. Local loader tests use
temporary SQLite fixtures. The earlier authorized named-volume proof loaded the existing bootstrap
twice; at that time read-only checks confirmed only `stg_official_fpl_teams`, the
`(softe_season, softe_team_id)` primary key, 20 rows for `2026-27`, no duplicate keys, and
`quick_check=ok`. The ordered-row SHA-256 was
identical after both loads and after `dev.ps1 setup`, which left the existing valid database
unchanged. No live retrieval was run.

The canonical schema-installation and teams-loader tests also pass on isolated SQLite databases,
including an end-to-end load from the saved FPL bootstrap through staging and reviewed club
resolution. Following the schema install and seed-only load, a read-only Datasette query against
the named volume found 51 canonical teams and the original 20 staged FPL teams, with zero rows in
`competitions`, `seasons`, `team_source_ids`, `players`, and `fixtures`. The installer required
`quick_check=ok` before and after creating the tables. No persistent service was started or
restarted for this proof.

The player loader passed 12 isolated-database tests using the saved 2026-27 bootstrap and
synthetic conflict/manager cases. Focused player/CLI tests passed (33 total). A read-only
Datasette check after the authorized load found 667 players, 1,334 player-source mappings
(667 in each `fpl.element.id` and `fpl.element.code`, all scoped to
`premier-league:2026-27`), 16 unknown birth dates, zero orphan mappings, and zero unmapped
players. The existing 51 clubs and 20 staged teams remained in place. Datasette does not
accept the `pragma_foreign_key_check` / `pragma_quick_check` SQL queries through its query API;
the read-only orphan check is not a replacement for an SQLite integrity check.

The previous-season archive audit found 27 player IDs with multiple team labels in saved
gameweek data; this evidence is retained outside the canonical player table. Focused audit,
archive-loader, and CLI tests passed (35 total), including an isolated full load of the
saved archive twice, name/DOB conflicts, manager exclusion, and transfer-safe reuse of a
canonical ID. A read-only Datasette check after the shared-volume load found 1,028 players,
3,016 scoped player mappings (841 in each 2025-26 namespace, 667 in each 2026-27 namespace),
33 missing birth dates, no orphan mappings or unmapped players, and no changes to the 51 clubs
or 20 staged teams. All 480 FPL codes shared across the seasons map to the same canonical
player; zero shared codes map to different players. This is identity proof, not proof of
transfer-history coverage or an SQLite PRAGMA integrity check.

The expanded history audit and archive loader pass focused tests (51 total, including a
full isolated 2016-17-to-2026-27 load followed by repeat loads). A final read-only Datasette
check after the authorized nine-season load found 2,757 players, 16,010 mappings across
11 season scopes (8,005 season-specific FPL players, each with two namespaces), 1,627
unknown birth dates, zero orphan mappings, zero unmapped players, and zero FPL codes
mapping to different canonical players across seasons. Both reviewed Hayden codes map
to one canonical ID. The 51 clubs and 20 staged 2026-27 teams are unchanged. The Datasette
query endpoint does not allow the SQLite PRAGMA integrity commands; this check is not a
full `PRAGMA quick_check` or `PRAGMA foreign_key_check` on the volume.
