# Proposed base-table schema

## Recommendation

Start with **eight tables: five core tables and three source-ID maps**. This is enough to identify competitions, seasons, teams, players, and fixtures consistently across providers without also building a transfer database, a calendar model, or a statistics warehouse. Managers are outside this initial canonical model and must not be loaded as players.

The base should answer **“which competition, season, team, player, and match is this?”** It should not attempt to standardize every provider's football or fantasy data. Keep those observations in staging until a feature needs a canonical fact table.

This document replaces the earlier proposal. It is a logical design, not DDL or approval to create a database. The names and constraints below are recommendations for implementation.

## Design rules

- Give each core entity a project-generated integer primary key. Provider IDs, names, dates, and team assignments must not determine that key.
- Keep identifiers stable through corrections, name changes, transfers, and rescheduling. Do not regenerate canonical IDs on each import.
- Use `NOT NULL` for required fields below; only fields explicitly marked nullable may be unknown. `FK` means foreign key and `UNIQUE` means an alternate key.
- Keep source identifiers as text, including numeric-looking IDs. Their meaning depends on their namespace and scope, not their SQL numeric type.
- Store known instants in UTC using one consistent representation. Preserve a date without inventing midnight or assuming an undocumented source timezone.
- Populate canonical records and mappings only when identity is sufficiently established. Unknown or conflicting source rows can remain in staging; they do not justify guessing or creating duplicate players.
- Keep constraints local to what is actually known. Do not assume every season has 20 teams, 38 rounds, or 380 matches.

## 1. Core tables

### `competitions`

**One row per real-world competition**, not per provider's version of it.

| Column | Rule / meaning |
|---|---|
| `competition_id` | Primary key. |
| `competition_key` | Unique, project-controlled text key, such as `premier-league`. Not regenerated when the display name changes. |
| `name` | Canonical display name. |

Start with the Premier League. Use `competitions` rather than `leagues` so adding a cup later does not require renaming the foundation; cup-specific stages and ties are not part of this proposal. Country, governing body, and competition-type lookup tables are unnecessary now.

### `seasons`

**One row per competition campaign.** The Premier League's 2025-26 season and another competition's 2025-26 season are different rows.

| Column | Rule / meaning |
|---|---|
| `season_id` | Primary key. |
| `competition_id` | FK to `competitions`. |
| `label` | Canonical campaign label, initially `YYYY-YY`. |
| `start_year` | Integer; sorts campaigns and disambiguates provider year conventions. |
| `end_year` | Integer; may equal `start_year` for a calendar-year competition. |

Enforce `UNIQUE (competition_id, label)` and `end_year >= start_year`. Labels and years must agree under the chosen competition's convention. Do not create both a generic calendar-season table and a competition-season join table: there is no current need for that extra layer. Actual opening and closing dates can be added when needed.

### `teams`

**One row per club identity across seasons**, including seasons outside the Premier League.

| Column | Rule / meaning |
|---|---|
| `team_id` | Primary key. |
| `team_key` | Unique, project-controlled text key. Use the curated club `id` values in `premier-league-team-names.json` as initial keys, subject to its identity decisions. |
| `name` | Canonical display name; not unique. |

Do not put a current competition or season on the club. Promotion and relegation change participation, not club identity. The curated JSON file remains the initial seed and reviewed alias source; a second database copy of its aliases is not required yet. Consult its normalization rules and reject ambiguous matches rather than automatically fuzzy-matching names.

### `players`

**One row per football player**, independent of club, season, or provider. Manager records are excluded.

| Column | Rule / meaning |
|---|---|
| `player_id` | Primary key. |
| `display_name` | Preferred readable name; not unique. |
| `date_of_birth` | Nullable date, where supported by reliable evidence. |

The 2024-25 FPL archive includes assistant-manager game entries. Retain those records in staging, but exclude them from canonical player records, player source-ID mappings, and player facts. Do not treat every row in a provider's player/element file as a football player.

If manager analysis is needed, add separate `managers` and `manager_source_ids` tables with their own keys and relationships. A former player who becomes a manager retains their player record and receives a separate manager record when required. A cross-role link can be added later for a concrete feature; do not introduce a shared `people` table or role flags now. Current team and position also do not belong to player identity; keep those in source observations or later purpose-specific relationships.

Preserve provider name parts, spellings, and external codes in staging. A matching name, even combined with a team, is evidence rather than a unique player key. Date of birth is also not a unique key.

### `fixtures`

**One row per scheduled or played match**, surviving postponement and kickoff corrections.

| Column | Rule / meaning |
|---|---|
| `fixture_id` | Primary key. |
| `season_id` | FK to `seasons`; competition is obtained through the season. |
| `home_team_id` | FK to `teams`. |
| `away_team_id` | FK to `teams`. |
| `match_date` | Nullable date in the competition's agreed local timezone; supports historical date-only records. |
| `kickoff_at` | Nullable UTC instant; only populate when time and timezone are known. |
| `status` | Small controlled text vocabulary: `unknown`, `scheduled`, `in_progress`, `finished`, `postponed`, `cancelled`, `abandoned`. Default `unknown`. |
| `home_goals`, `away_goals` | Nullable integers: accepted final regulation-time score, including stoppage time. Not a live score or an extra-time/shootout total. |

Enforce different home and away teams, nonnegative scores, and scores being either both present or both absent. A `finished` fixture may still have an unknown score. Under this initial model, final scores are populated only for `finished` fixtures; exceptional awarded results need an explicit policy before loading. If both date and kickoff are known, they must agree after converting the instant to the competition's local timezone.

Keeping a basic result here avoids requiring another table just to answer who played and what the result was. Shots, xG, lineups, odds, and player performance remain separate source facts. A dedicated canonical result table becomes useful only when result history, multiple result interpretations, or extra-time/shootout detail is required.

Do **not** make `(season_id, home_team_id, away_team_id, match_date)` a unique key: the date can change. Do not enforce the team pairing alone as universal uniqueness either; future competition formats may repeat it. Use season and participants to find match candidates, then confirm using source mappings and other evidence. Rescheduling updates the existing fixture; a distinct replay is a separate fixture.

No canonical gameweek or round is required on this record. FPL events and competition rounds are different concepts, and sorting fixtures by date does not establish either one.

## 2. Source-ID maps

These three tables are necessary identity infrastructure, not duplicate entity tables. They let multiple providers and historical IDs point to one canonical record while keeping real foreign-key enforcement.

| Table | Composite primary key | Required target |
|---|---|---|
| `team_source_ids` | (`source_namespace`, `source_scope`, `source_id`) | `team_id` FK to `teams` |
| `player_source_ids` | (`source_namespace`, `source_scope`, `source_id`) | `player_id` FK to `players` |
| `fixture_source_ids` | (`source_namespace`, `source_scope`, `source_id`) | `fixture_id` FK to `fixtures` |

All key columns and the target FK are non-null. Index each target FK for reverse lookups. Do not make the target unique: one canonical entity can have many source identifiers, including multiple identifiers from one provider.

### Namespace and scope rules

- **Namespace identifies the issuing system and identifier field**, not just the download folder. For example, `fpl.element.id` and `fpl.element.code` are different namespaces. A third-party archive may reproduce official FPL identifiers without creating a new identity namespace; its collection provenance still stays in staging.
- **Scope identifies the full context in which that ID is unique.** For season-local FPL IDs, use an unambiguous value such as `premier-league:2024-25`, not a bare year. Include further context if an identifier requires it. Use the reserved value `global` only after cross-season stability and uniqueness are established; never use NULL to mean global.
- A numeric ID, a stable-looking code, and an Opta-style code are not interchangeable. Keep them in distinct namespaces. Sample agreement is not proof that a code is globally reliable.
- A mapping row represents an accepted resolution. Leave unresolved rows unmapped in staging, rather than allowing null targets or inventing a placeholder player. Manager identifiers must not point to player records, even when the manager is a former player.
- Do not replace these maps with one polymorphic `(entity_type, entity_id)` table. Saving two tables would lose straightforward foreign keys and permit invalid entity references.

For source records with no actual ID, do not invent a supposedly stable provider ID from a date or name. Resolve football-data team labels through the curated aliases; resolve its matches against canonical fixture candidates. A later loader can retain the resolved canonical FK alongside its staging row. Corrected source dates then need reconciliation, not a new canonical match by default.

Competition and season identifiers can initially be resolved through explicit loader configuration, since the imported scope is known. Add their own mapping tables only when that becomes real, variable data to maintain. Do not add a provider registry table merely to hold a few namespace strings; document and validate those strings in loader configuration.

## 3. Relationships deliberately deferred

| Not included initially | Why it can wait / when to introduce it |
|---|---|
| `season_teams` | Participating teams can be derived from the union of home and away teams in fixtures, **only for seasons with complete fixture coverage**. Add this relationship when authoritative membership is needed before fixtures exist or independently of incomplete match data. Never treat the derived list as proof that an absent club did not participate. |
| `player_team_stints` | A current-team snapshot or an appearance does not establish contract dates, loans, or a complete employment history. Keep source associations in staging. Add dated stints only for a feature needing those distinctions and with evidence to populate them. |
| `season_rounds` / `gameweeks` | Round numbers alone do not justify a table. Retain source fields in staging. Add a specifically named FPL-event or competition-round model when deadlines, blank/double gameweeks, scheduling, or round-level analysis require it; define assignments separately where those concepts differ. |
| `team_aliases` | The curated JSON already supplies reviewed team aliases. Move them into a relational table when runtime editing or provider/competition-scoped matching requires it, with collision handling rather than an assumption of globally unique names. |
| `managers` / `manager_source_ids` | Manager identities and mappings must be separate from players. Add these tables when manager data has a canonical consumer; preserve manager observations in staging in the meantime. |
| Player-season, squad, and position tables | These describe participation or provider classifications, not player identity. Add only the relationship or fact needed by the first consuming feature. |
| Stadiums, countries, referees, transfers, and generic metadata tables | No current identity requirement needs them. Do not build lookup tables or a generic attribute-value system speculatively. |

Deferring a relationship does not mean discarding its source data. Staging preserves the evidence so later extensions can use the existing canonical IDs. The base is deliberately **not yet** an authoritative squad list, transfer history, or FPL calendar.

## 4. Evidence and limits

This recommendation uses [the staging proposal](raw-data-staging-schemas.md), the existing team-name reference, and a bounded raw-data check rather than a full audit:

- `data/raw/fpl_archive_vaastav/2024-25/players_raw.csv` includes FPL `id`, `code`, and `opta_code`, plus manager entries with `element_type = 5`. That supports distinct identifier namespaces and explicit filtering of manager entries out of canonical player data.
- The archive's `teams.csv` and `fixtures.csv`, compared with the current official FPL payloads, expose season-context IDs and separate fixture `event` assignments. Treat those IDs as scoped; do not assume a code has proved permanent.
- `data/raw/football_data/E0_2425.csv` has date and time fields but no round. The staging review records date-only older coverage. A nullable precise kickoff and a separate known date are therefore useful, not speculative.
- Sampled Understat 2025 roster player IDs matched that season's league player IDs. This supports investigating a shared namespace; it does **not** establish cross-season identity, complete shot coverage, or a corpus-wide FK guarantee.

No global uniqueness, complete coverage, timezone interpretation, or cross-provider player match is claimed from these samples. This proposal does not change the staging schemas or raw files.

## 5. What needs resolving

These are decisions and checks before the affected loaders or features are implemented, not reasons to add more tables now.

1. **Canonical field authority and corrections.** Choose which source wins for fixture status, dates, scores, team names, and personal details, including fallbacks when the preferred source is missing. Define how accepted values retain enough provenance to explain a correction. Do not silently use “last file loaded wins”; the exact provenance storage can follow the loader design.
2. **Identifier contracts.** Verify season reuse and cross-season stability for each ID/code actually used. Document namespaces, scope formats, and when Vaastav and official FPL identifiers can share a namespace. Confirm Understat roster, league, and shot identities over the intended coverage before enforcing joins. Opta-style codes are candidate evidence, not automatically trusted universal keys.
3. **Player matching, manager exclusion, and error repair.** Agree the evidence needed to link players across providers and seasons, how ambiguous matches are reviewed, and how mistaken merges are reversed without orphaning facts. Validate each source's player/manager classification before loading player mappings or facts. Players and managers remain separate; the open question is when manager analysis warrants its own canonical tables, not whether to combine them.
4. **Club identity and alias coverage.** Confirm the curated reference's successor/history decisions and coverage of actual source labels. Agree how to handle unknown clubs and alias collisions. Adding another league must not assume that the Premier League reference is a complete team directory.
5. **Fixture resolution and exceptional results.** Set rules for matching date-only records, postponements, abandoned matches, replays, and source duplicates. Decide how awarded results are represented. Define source timezone conversion and the local timezone used for `match_date`; do not infer UTC from an unzoned timestamp.
6. **Coverage and participation requirements.** Decide whether the first feature needs complete season membership or squads before fixture/appearance coverage exists. If yes, the relevant explicit relationship is required at that point; a derived view is not an adequate substitute for absent evidence.
7. **Meaning of gameweek.** Before FPL analysis, decide whether the needed fact is the original schedule, actual competition round, or the FPL scoring event after rescheduling. Preserve those distinctions and decide whether assignment history is needed rather than forcing one `round_id` onto every match.
8. **Season interpretation and import validation.** Explicitly translate each provider's start-year, end-year, label, and season-ID conventions. Validate questionable or future-labelled captures against payload contents before loading; a directory name is useful context, not sufficient proof of the campaign.
