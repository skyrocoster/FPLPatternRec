# Proposed staging schemas for the actual raw data

This is a **schema proposal only**. No tables, loaders, transformations, or raw files were changed.

## Scope and conventions

I inspected payload files under `data/raw/`, not the retrieval records. The proposal uses ordinary typed columns, natural/composite keys where the data supports them, and a few JSON columns for genuinely nested or irregular values. It does not add hashes, manifests, or ingestion-control tables.

SQL types below are portable (`INTEGER`, `BIGINT`, `DECIMAL`, `BOOLEAN`, `DATE`, `TIMESTAMP`, `TEXT`, `JSON`); adjust spelling to the chosen database. Column suffixes are shown without the table-specific prefix: for example, `stg_football_data_all` uses `sfda_`, so `match_date` means `sfda_match_date`. Every stored column should have that prefix. `PK` means proposed primary key; `FK` names a clear relationship. `Candidate PK` means check uniqueness on all rows before enforcing it.

For CSV imports, discard blank rows and unnamed empty-header columns; convert empty strings and source null sentinels to SQL `NULL`, but retain meaningful zeros. Fields absent from older versions of a stacked file family must be nullable. Cast numeric-looking strings to numeric columns where supported; retain text/JSON where parsing would be ambiguous or lossy.

**Append/refresh policy:** these tables hold the latest available value for each provider-local key, not a history of every retrieval. Append newly collected seasons and facts; when a complete source file is refreshed within an existing season, apply the newer capture to existing keys and replace that file's child rows within its known scope so removed entries do not linger. Do not interpret an absent row in an incomplete page/partial response as a deletion. Staging does not preserve previous values when a capture is refreshed; retaining multiple staged versions of the same fact would require a separate capture identifier and revised keys (and preservation of those raw captures). Check the proposed candidate keys before enforcing them. If a later payload introduces a populated field not mapped below, extend the nullable typed schema (or explicitly retain its raw value pending typing) before loading it; do not silently discard it. Fields omitted because they are currently always empty may need to be added if later populated.

## What is actually present

| Provider/folder | Actual payload families found | Schema scope |
|---|---|---|
| `football_data/` | 34 `E0_*.csv` files, 1993-94 through 2026-27 (last season partial) | One stacked match table |
| `fpl_archive_vaastav/` | Season CSVs for 2016-17 through 2026-27; player list, player snapshot, gameweek rows, fixtures, and teams become available in different years | Four tables; redundant player ID list folded into players |
| `understat/` | 13 compressed league JSONs (2014-2026), 430 compressed match JSONs (2025 and 2026), and 13 HTML captures | Six relational tables; HTML captures contain no usable league data |
| `official_fpl_api/` | Bootstrap snapshot, fixtures, 667 element summaries, two live-gameweek snapshots | Entity, fixture, history, and live tables |
| `premier_league_api/` | Competition seasons, 143 fixture pages (13,546 fixtures), 418 stat pages (50,940 rows) | Season, fixture, team/player, goal, and stat tables |
| `fotmob/` | League list, 17 season files, 430 match files, season/stat-leader files for 11 seasons, and three statistics catalogues | League/season, fixture/match, nested match facts, and stat-leader tables |
| `clubelo/` | No payload file; only a failed retrieval record | No schema proposed |
| `sofascore/` | No payload file; only a failed retrieval record | No schema proposed |

`collection-*.json` files are retrieval records, not football data, and are not staged. Vaastav `catalogues/*.json` files are repository directory listings rather than player/match records. Understat's 13 saved league HTML pages are JS-shell pages with no embedded league tables/data arrays. FotMob's `statistics/catalogue_*.json` files are different: they contain usable statistic catalogues and, in two cases, actual leader rows, so those are covered below.

---

## 1. football_data

### `stg_football_data_all` (`sfda_`)

Stack all 34 season CSVs into **one wide match table**, as requested. Derive `season_end_year` from the filename (`E0_9900.csv` → `2000`, `E0_2526.csv` → `2026`). `Div` is retained even though the supplied files currently contain only `E0`.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_end_year`, `division_code`, `match_date`, `home_team`, `away_team` | `SMALLINT`, `TEXT`, `DATE`, `TEXT`, `TEXT` | All NOT NULL; **Candidate PK** is the five-column tuple |
| `kickoff_time` | `TIME` or `TEXT` | NULL; absent in older seasons |
| `full_time_home_goals`, `full_time_away_goals` | `INTEGER` | NOT NULL |
| `full_time_result` | `TEXT` | NOT NULL; observed `H/D/A` |
| `half_time_home_goals`, `half_time_away_goals` | `INTEGER` | NULL; absent in early seasons |
| `half_time_result` | `TEXT` | NULL; absent in early seasons |
| `referee` | `TEXT` | NULL; not present in all seasons |
| `attendance` | `INTEGER` | NULL; only present in some older seasons |
| `home_shots`, `away_shots`, `home_shots_on_target`, `away_shots_on_target`, `home_hit_woodwork`, `away_hit_woodwork`, `home_corners`, `away_corners`, `home_fouls`, `away_fouls`, `home_offsides`, `away_offsides`, `home_yellow_cards`, `away_yellow_cards`, `home_red_cards`, `away_red_cards`, `home_hbp`, `away_abp` | `INTEGER` | NULL where absent in a source season; no FK |
| `home_expected_goals`, `away_expected_goals` | `DECIMAL(8,4)` | NULL; only in the 2026-27 file |
| `odds_*` columns described below | `DECIMAL(12,6)` | All NULLABLE; bookmaker/market coverage differs by season and match |

Odds are wide columns, not a separate odds table. Expand only combinations occurring in at least one supplied CSV. Normalize source columns with these rules:

| Source field pattern | Normalized suffix pattern |
|---|---|
| `<book>H`, `<book>D`, `<book>A` | `odds_<book>_match_home`, `_draw`, `_away` |
| `<book>CH`, `<book>CD`, `<book>CA` | `odds_<book>_match_home_close`, `_draw_close`, `_away_close` |
| `<book>>2.5`, `<book><2.5` and closing `C` variants | `odds_<book>_over_2_5`, `_under_2_5`, and matching `_close` suffixes |
| `AHh`, `AHCh` | `asian_handicap_line`, `asian_handicap_line_close` |
| `<book>AH` (bare per-book line, observed as `GBAH`, `LBAH`, `B365AH` in 2003-04/2004-05) | `odds_<book>_asian_line` |
| `<book>AHH`, `<book>AHA`, `<book>CAHH`, `<book>CAHA` | `odds_<book>_asian_home`, `_asian_away`, and matching `_close` suffixes |
| `Bb...` BetBrain fields | `betbrain_<lowercase source suffix>`; retain the suffix so actual BetBrain fields stay distinct |

Book/source codes represented across the files include `B365`, `BF`, `BFD`, `BFE`, `BMGM`, `BS`, `BV`, `BW`, `CL`, `GB`, `IW`, `LB`, `P`, `PP`, `PS`, `SB`, `SJ`, `SKB`, `SO`, `VC`, `WH`, `SY`, `1XB`, `Max`, and `Avg`; older BetBrain `Bb...` fields are also present. The 2026-27 header, for example, includes `PPH` and `SKBH`. Apply the pattern rules to every observed source code, not only this illustrative list. `Max`/`Avg` are bookmaker aggregates. Their market fields are nullable `DECIMAL`s like bookmaker prices.

**Key/FK notes:** the five-column natural match key is a candidate, not yet an enforced constraint. There is no provider-local team dimension, so team names have no FK. The source has two-digit and four-digit dates; parse using the filename season rather than a fixed two-digit-year pivot. `HBP`/`ABP` are preserved as `home_hbp`/`away_abp` because their meaning was not established from payloads.

---

## 2. fpl_archive_vaastav

Season is derived from the directory name and stored as `TEXT` in `YYYY-YY` form. Player and team IDs restart/change across seasons, so include season in keys and relationships. `player_idlist.csv` repeats `id`, `first_name`, and `second_name` already in `players_raw.csv`; do not duplicate those rows in a fifth table. Use it as an import cross-check. The 2016-17/2017-18 CSVs use a legacy encoding in some names; decode before typing text.

### `stg_vaastav_players` (`svpl_`)

One player-season row from `players_raw.csv`; union the observed season-specific columns.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season`, `player_id` (source `id`) | `TEXT`, `INTEGER` | NOT NULL; **PK** (`season`, `player_id`) |
| `team_id` (source `team`) | `INTEGER` | NULL if blank; FK (`season`, `team_id`) → `stg_vaastav_teams` where that season has a teams file (2019-20 onward) |
| `code`, `team_code`, `element_type`, `now_cost`, `cost_change_start`, `cost_change_start_fall`, `cost_change_event`, `cost_change_event_fall`, `price_change_hourly_rate`, `chance_of_playing_next_round`, `chance_of_playing_this_round`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `dreamteam_count`, `event_points`, `total_points`, `transfers_in`, `transfers_out`, `transfers_in_event`, `transfers_out_event`, `starts`, `tackles`, `recoveries`, `clearances_blocks_interceptions`, `defensive_contribution`, `ea_index`, `loans_in`, `loans_out`, `loaned_in`, `loaned_out`, `corners_and_indirect_freekicks_order`, `direct_freekicks_order`, `penalties_order`, `region`, `squad_number`, `creativity_rank`, `creativity_rank_type`, `form_rank`, `form_rank_type`, `ict_index_rank`, `ict_index_rank_type`, `influence_rank`, `influence_rank_type`, `now_cost_rank`, `now_cost_rank_type`, `points_per_game_rank`, `points_per_game_rank_type`, `selected_rank`, `selected_rank_type`, `threat_rank`, `threat_rank_type` | `INTEGER` | Nullable when source is blank, unavailable, or that season's schema lacks the field; order/region/squad fields nullable |
| `creativity`, `ep_next`, `ep_this`, `form`, `ict_index`, `influence`, `points_per_game`, `selected_by_percent`, `threat`, `value_form`, `value_season`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded`, `expected_goals_per_90`, `expected_assists_per_90`, `expected_goal_involvements_per_90`, `expected_goals_conceded_per_90`, `clean_sheets_per_90`, `goals_conceded_per_90`, `saves_per_90`, `starts_per_90`, `defensive_contribution_per_90`, `price_change_percent` | `DECIMAL(12,4)` | NULL when blank/`None`, or absent in that season |
| `can_select`, `can_transact`, `has_temporary_code`, `in_dreamteam`, `price_change_calibrating`, `removed`, `special` | `BOOLEAN` | Nullable only if absent/blank; columns vary by season |
| `first_name`, `second_name`, `known_name`, `web_name`, `birth_date`, `photo`, `opta_code`, `status`, `news`, `news_added`, `scout_news_link`, `corners_and_indirect_freekicks_text`, `direct_freekicks_text`, `penalties_text`, `team_join_date`, `price_change_locked_until` | `TEXT` (dates/times may be typed as `DATE`/`TIMESTAMP`) | Nullable where source is blank; `news`, `news_added`, `known_name`, `birth_date`, and price lock are observed nullable |
| `price_change_projections`, `scout_risks` | `JSON` | Nullable or empty list; source CSV cells are serialized nested values, not scalar text |
| `mng_clean_sheets`, `mng_draw`, `mng_goals_scored`, `mng_loss`, `mng_underdog_draw`, `mng_underdog_win`, `mng_win` | `INTEGER` | NULL in seasons without manager fields (observed in 2024-25) |

All season-union columns are nullable when the source schema does not supply them. Never turn `0` into NULL. `price_change_projections` and `scout_risks` are Python-literal-style CSV cells and need conversion to JSON if stored as JSON.

### `stg_vaastav_teams` (`svt_`)

From `teams.csv` (2019-20 through 2026-27 only).

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season`, `team_id` (source `id`) | `TEXT`, `INTEGER` | NOT NULL; **PK** (`season`, `team_id`) |
| `code`, `pulse_id`, `played`, `win`, `draw`, `loss`, `points`, `position`, `strength`, `strength_overall_home`, `strength_overall_away`, `strength_attack_home`, `strength_attack_away`, `strength_defence_home`, `strength_defence_away` | `INTEGER` | Nullable where source is blank; `strength` is NULL in 2026-27 |
| `name`, `short_name` | `TEXT` | NOT NULL |
| `unavailable` | `BOOLEAN` | NOT NULL in observed rows |

`form`, `team_division`, and `link_url` are empty in all available rows and should be dropped rather than carried as permanently empty columns. Team IDs are season-local.

### `stg_vaastav_fixtures` (`svf_`)

From `fixtures.csv` (2018-19 through 2026-27; team reference rows exist from 2019-20).

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season`, `fixture_id` (source `id`) | `TEXT`, `INTEGER` | NOT NULL; **PK** (`season`, `fixture_id`) |
| `code`, `event`, `event_day`, `minutes`, `pulse_id`, `team_h_difficulty`, `team_a_difficulty`, `team_h`, `team_a` | `INTEGER` | Nullable only if source is blank or the season lacks the field; `team_h`/`team_a` are team IDs |
| `team_h_score`, `team_a_score` | `INTEGER` | NULL for unplayed/postponed fixtures |
| `kickoff_time`, `deadline_time` | `TIMESTAMP` | NULL where source is blank/absent |
| `kickoff_time_formatted`, `deadline_time_formatted` | `TEXT` | Nullable; human-readable duplicates may be omitted if canonical timestamps are stored |
| `started`, `finished`, `finished_provisional`, `provisional_start_time` | `BOOLEAN` | Nullable only if source is blank |
| `stats` | `JSON` | Nullable if blank; source CSV stores nested stat identifiers and per-side player/value entries as text |

`team_h`/`team_a` are FKs (`season`, team ID) → `stg_vaastav_teams` only when a matching season team file exists. The 2018-19 fixture `stats` cell uses a stringified list of identifier/side/player-value objects; normalize to JSON if retained.

### `stg_vaastav_player_gameweeks` (`svgw_`)

From each season's `gws/merged_gw.csv`, one player-fixture-gameweek observation. Earliest seasons have detailed player stats; 2019-20 is much narrower; newer seasons add xP/expected-goal and manager stats. Union the fields below and leave version-specific fields NULL.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season`, `player_id` (source `element`), `fixture_id` (source `fixture`), `gameweek` (source `GW`, falling back to `round`) | `TEXT`, `INTEGER`, `INTEGER`, `INTEGER` | NOT NULL; **Candidate PK** (`season`, `player_id`, `fixture_id`, `gameweek`) |
| `player_name` (source `name`), `position`, `team_name` (source `team`), `kickoff_time`, `kickoff_time_formatted` | `TEXT` | Nullable across variants; `team_name` is a label, not a team ID |
| `assists`, `bonus`, `bps`, `clean_sheets`, `clearances_blocks_interceptions`, `defensive_contribution`, `attempted_passes`, `big_chances_created`, `big_chances_missed`, `completed_passes`, `dribbles`, `ea_index`, `errors_leading_to_goal`, `errors_leading_to_goal_attempt`, `fouls`, `goals_conceded`, `goals_scored`, `key_passes`, `loaned_in`, `loaned_out`, `minutes`, `offside`, `open_play_crosses`, `opponent_team`, `own_goals`, `penalties_conceded`, `penalties_missed`, `penalties_saved`, `recoveries`, `red_cards`, `saves`, `selected`, `tackled`, `tackles`, `target_missed`, `team_a_score`, `team_h_score`, `transfers_balance`, `transfers_in`, `transfers_out`, `value`, `winning_goals`, `yellow_cards`, `starts` | `INTEGER` | Nullable where absent in a season or where scores are unknown |
| `creativity`, `ict_index`, `influence`, `threat`, `expected_points` (source `xP`), `expected_assists`, `expected_goal_involvements`, `expected_goals`, `expected_goals_conceded` | `DECIMAL(12,4)` | NULL when absent from a season |
| `mng_clean_sheets`, `mng_draw`, `mng_goals_scored`, `mng_loss`, `mng_underdog_draw`, `mng_underdog_win`, `mng_win` | `INTEGER` | NULL except where the season's gameweek file carries manager rows (observed in 2024-25) |
| `was_home`, `modified` | `BOOLEAN` | Nullable only where absent in source variant |

`player_id` is an FK (`season`, ID) → `stg_vaastav_players`. `fixture_id` is an FK (`season`, ID) → `stg_vaastav_fixtures` from 2018-19 onward only. `opponent_team` is an FK (`season`, ID) → `stg_vaastav_teams` where available. Do not use `team_name` as an FK. Early merged files include `id` equal to `element`; use one `player_id` field rather than both. Treat `round`/`GW` as one normalized gameweek field.

---

## 3. Understat

For compressed JSON, source IDs and numeric values are JSON strings; cast numeric IDs/counts to integer and measurements to decimal. Derive `season_year` from the season/file path. The 2026 league file is in-season and has unplayed matches, so score/xG fields are legitimately nullable.

### `stg_understat_league_teams` (`sult_`)

Source: `league_data/EPL_<year>.json.gz`, `teams` object.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_year`, `team_id` | `SMALLINT`, `BIGINT` | NOT NULL; **PK** (`season_year`, `team_id`) |
| `team_title` | `TEXT` | NOT NULL |

### `stg_understat_team_match_history` (`suth_`)

Source: each `teams{teamId}.history[]` row; flatten the two `ppda` objects into four scalar columns.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_year`, `team_id`, `match_date` | `SMALLINT`, `BIGINT`, `TIMESTAMP` | NOT NULL; **Candidate PK** (`season_year`, `team_id`, `match_date`); FK (`season_year`, `team_id`) → `stg_understat_league_teams` |
| `home_away` | `CHAR(1)` | NOT NULL; source `h_a` (`h`/`a`) |
| `xg`, `xga`, `npxg`, `npxga`, `npxgd`, `xpoints` | `DECIMAL(12,6)` | NOT NULL in inspected rows |
| `deep`, `deep_allowed`, `scored`, `missed`, `wins`, `draws`, `losses`, `points` | `INTEGER` | NOT NULL in inspected rows |
| `result` | `TEXT` | NOT NULL (`w/d/l`) |
| `ppda_att`, `ppda_def`, `ppda_allowed_att`, `ppda_allowed_def` | `INTEGER` | NOT NULL |

### `stg_understat_league_players` (`sulp_`)

One row per player in `players[]` for each season.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_year`, `player_id` | `SMALLINT`, `BIGINT` | NOT NULL; **PK** (`season_year`, `player_id`) |
| `player_name`, `position`, `team_title` | `TEXT` | NOT NULL; `position` is a space-separated role string |
| `games`, `time`, `goals`, `assists`, `shots`, `key_passes`, `yellow_cards`, `red_cards`, `npg` | `INTEGER` | NOT NULL in inspected rows |
| `xg`, `xa`, `npxg`, `xg_chain`, `xg_buildup` | `DECIMAL(12,6)` | NOT NULL in inspected rows |

`team_title` is a name, not a team ID; do not make it an FK. The source `xG buildup` key is renamed to `xg_buildup`.

### `stg_understat_league_matches` (`sulm_`)

Source: `dates[]` in each league JSON file.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `match_id` | `BIGINT` | NOT NULL; **PK** (unique across inspected seasons and match-data file IDs) |
| `season_year` | `SMALLINT` | NOT NULL; derived from filename |
| `is_result` | `BOOLEAN` | NOT NULL |
| `home_team_id`, `away_team_id` | `BIGINT` | NOT NULL; FK (`season_year`, team ID) → `stg_understat_league_teams` |
| `home_team_title`, `home_team_short_title`, `away_team_title`, `away_team_short_title` | `TEXT` | NOT NULL |
| `home_goals`, `away_goals` | `INTEGER` | NULL for unplayed matches |
| `home_xg`, `away_xg` | `DECIMAL(12,6)` | NULL for unplayed matches |
| `kickoff_at` | `TIMESTAMP` | NOT NULL |
| `forecast_json` | `JSON` | NULL/absent for upcoming matches; retain nested forecast only if needed |

Team IDs have a clear same-season relationship to the `teams` object. The 2026 file includes 330 not-yet-resulted matches with null goals/xG and no forecast object.

### `stg_understat_match_shots` (`sums_`)

One row per shot from `match_data/<year>/<match_id>.json.gz` `shots{h,a}[]`. Do not repeat match-level context (season, team names, scores, date) on each shot; those facts are available through the match FK.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `shot_id` | `BIGINT` | NOT NULL; **PK** (unique across inspected corpus) |
| `match_id` | `BIGINT` | NOT NULL; FK → `stg_understat_league_matches.match_id` |
| `home_away` | `CHAR(1)` | NOT NULL (`h`/`a`) |
| `minute` | `INTEGER` | NOT NULL |
| `result`, `situation`, `shot_type`, `last_action`, `player_name` | `TEXT` | `last_action` may be NULL if absent; other fields present in inspected rows |
| `x`, `y`, `xg` | `DECIMAL(16,10)` | NOT NULL |
| `player_id` | `BIGINT` | NOT NULL; no FK asserted because identity against other Understat player records is unsettled |
| `player_assisted` | `TEXT` | NULL (JSON null observed in 3,030 shots) |

### `stg_understat_match_rosters` (`sumr_`)

One row per roster player from each match file's `rosters` object. `roster_id` (the object key/row `id`) is distinct from the row's `player_id`.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `roster_id` | `BIGINT` | NOT NULL; **PK** (unique across inspected files) |
| `season_year`, `match_id` | `SMALLINT`, `BIGINT` | NOT NULL; season derived from folder; FK `match_id` → `stg_understat_league_matches.match_id` |
| `player_id`, `team_id` | `BIGINT` | NOT NULL; `team_id` FK (`season_year`, `team_id`) → `stg_understat_league_teams`; player ID has no confirmed FK |
| `player_name`, `position`, `home_away`, `position_order` | `TEXT` | NOT NULL |
| `goals`, `own_goals`, `shots`, `key_passes`, `assists`, `yellow_card`, `red_card`, `minutes` | `INTEGER` | NOT NULL in inspected rows |
| `xg`, `xa`, `xg_chain`, `xg_buildup` | `DECIMAL(12,6)` | NOT NULL in inspected rows |
| `roster_in`, `roster_out` | `TEXT` | NOT NULL in source; `"0"` is a sentinel and nonzero references have no identified target |

The HTML captures have no table/embedded data and therefore have no staging table.

---

## 4. Official FPL API

Bootstrap arrays become entity tables. IDs in nested lists (element summaries/live snapshots) come from the element ID or gameweek in the file name when not repeated in each child row. No hash or retrieval manifest is needed.

**Season scope for every table in this section:** add `season TEXT NOT NULL` in `YYYY-YY` form, determined from the associated bootstrap's first gameweek deadline (or the explicitly recorded collection season if loading files separately). The PK, candidate PK, and provider-local FKs listed below are shorthand: prepend `season` on both sides of each key/relationship. This prevents a new season's reused element, fixture, event, or chip IDs from overwriting the previous season. Within one season, refreshed bootstrap/fixture/live files follow the latest-by-key policy above; they do not create additional rows for the same gameweek and player. Load related files with the same season value.

### `stg_official_fpl_teams` (`softe_`), `stg_official_fpl_element_types` (`sofet_`), `stg_official_fpl_phases` (`sofph_`), `stg_official_fpl_chips` (`sofch_`), `stg_official_fpl_element_stats` (`sofes_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Teams: `team_id` (source `id`), `code`, `pulse_id`, `position`, `played`, `win`, `draw`, `loss`, `points`, `strength_overall_home`, `strength_overall_away`, `strength_attack_home`, `strength_attack_away`, `strength_defence_home`, `strength_defence_away` | `INTEGER` | `team_id` PK; other listed fields NOT NULL in this snapshot |
| Teams: `name`, `short_name` | `TEXT` | NOT NULL |
| Teams: `link_url` | `TEXT` | NULL; empty string in all 20 rows of this snapshot, so normalize to `NULL` (drop if it stays empty) |
| Teams: `unavailable` | `BOOLEAN` | NOT NULL |
| Element types: `element_type_id` (source `id`), `element_count`, `squad_select`, `squad_min_play`, `squad_max_play` | `INTEGER` | `element_type_id` PK; other fields NOT NULL |
| Element types: `plural_name`, `plural_name_short`, `singular_name`, `singular_name_short` | `TEXT` | NOT NULL |
| Element types: `sub_positions_locked` | `JSON` | NOT NULL (integer list) |
| Element types: `ui_shirt_specific` | `BOOLEAN` | NOT NULL |
| Phases: `phase_id` (source `id`), `start_event`, `stop_event`, `highest_score` | `INTEGER` | `phase_id` PK; `highest_score` NULL in 8/11 rows; start/stop FK → `stg_official_fpl_events.event_id` |
| Phases: `name` | `TEXT` | NOT NULL |
| Chips: `chip_id` (source `id`), `number`, `start_event`, `stop_event` | `INTEGER` | `chip_id` PK; other fields NOT NULL; start/stop FK → events |
| Chips: `name`, `chip_type` | `TEXT` | NOT NULL |
| Element stats: `name` | `TEXT` | **PK**; NOT NULL |
| Element stats: `label` | `TEXT` | NOT NULL |

Element-type `squad_min_select`/`squad_max_select`, player `squad_number`, and team `form`/`strength`/`team_division` are NULL for every row and should be dropped under the empty-field rule. Team `link_url` is an empty string for every row in this snapshot; normalize it to `NULL` and drop it if later captures stay empty. Chip/phase `overrides` objects are empty/null configuration and are not carried.

### `stg_official_fpl_elements` (`sofel_`)

667 current player/element records from `bootstrap-static.json.elements`.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `player_id` (source `id`) | `INTEGER` | NOT NULL; **PK** |
| `team_id` (source `team`), `position_type_id` (source `element_type`) | `INTEGER` | NOT NULL; FK → `stg_official_fpl_teams.team_id` and `stg_official_fpl_element_types.element_type_id` |
| `code`, `team_code`, `now_cost`, `cost_change_start`, `cost_change_start_fall`, `cost_change_event`, `cost_change_event_fall`, `price_change_hourly_rate`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `starts`, `tackles`, `recoveries`, `clearances_blocks_interceptions`, `defensive_contribution`, `dreamteam_count`, `total_points`, `event_points`, `transfers_in`, `transfers_out`, `transfers_in_event`, `transfers_out_event`, `creativity_rank`, `creativity_rank_type`, `influence_rank`, `influence_rank_type`, `threat_rank`, `threat_rank_type`, `ict_index_rank`, `ict_index_rank_type`, `now_cost_rank`, `now_cost_rank_type`, `selected_rank`, `selected_rank_type`, `form_rank`, `form_rank_type`, `points_per_game_rank`, `points_per_game_rank_type` | `INTEGER` | NOT NULL in all 667 records |
| `chance_of_playing_this_round`, `chance_of_playing_next_round`, `corners_and_indirect_freekicks_order`, `direct_freekicks_order`, `penalties_order`, `region` | `INTEGER` | NULL |
| `creativity`, `ep_next`, `ep_this`, `expected_assists`, `expected_goal_involvements`, `expected_goals`, `expected_goals_conceded`, `form`, `ict_index`, `influence`, `points_per_game`, `selected_by_percent`, `threat`, `value_form`, `value_season`, `price_change_percent` | `DECIMAL(12,4)` | Source supplies numeric strings; NOT NULL in inspected rows |
| `clean_sheets_per_90`, `defensive_contribution_per_90`, `expected_assists_per_90`, `expected_goal_involvements_per_90`, `expected_goals_per_90`, `expected_goals_conceded_per_90`, `goals_conceded_per_90`, `saves_per_90`, `starts_per_90` | `DECIMAL(12,4)` | Source mixes integer and float JSON numbers; NOT NULL in inspected rows |
| `can_select`, `can_transact`, `in_dreamteam`, `has_temporary_code`, `price_change_calibrating`, `removed`, `special` | `BOOLEAN` | NOT NULL |
| `first_name`, `second_name`, `web_name`, `photo`, `opta_code`, `scout_news_link`, `status` | `TEXT` | NOT NULL in observed payload |
| `known_name`, `news`, `corners_and_indirect_freekicks_text`, `direct_freekicks_text`, `penalties_text` | `TEXT` | NULL after normalizing empty strings; source can be empty |
| `birth_date`, `team_join_date` | `DATE` | NULL |
| `news_added`, `price_change_locked_until` | `TIMESTAMP` or `TEXT` | NULL |
| `price_change_projections`, `scout_risks` | `JSON` | NOT NULL lists; projections contain `{offset, projected_percent, likelihood}`; nonempty risk entries contain property/notes/gameweek/url |

Cast numeric strings such as `expected_goals` to `DECIMAL`, not text. JSON fields need no child tables unless later queries need individual projection/risk entries.

### `stg_official_fpl_events` (`sofev_`) and `stg_official_fpl_event_chip_plays` (`sofevc_`)

`events` is one row per gameweek; put its repeated `chip_plays[]` objects in a small child table.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Events: `event_id` (source `id`) | `INTEGER` | NOT NULL; **PK** |
| Events: `name`, `deadline_time` | `TEXT` / `TIMESTAMP` | NOT NULL |
| Events: `average_entry_score`, `highest_score`, `highest_scoring_entry`, `most_selected`, `most_captained`, `most_vice_captained`, `most_transferred_in`, `top_element`, `transfers_made`, `ranked_count`, `deadline_time_epoch`, `deadline_time_game_offset` | `INTEGER` | Highest/result fields (`highest_score`, `highest_scoring_entry`, `most_selected`, `most_captained`, `most_vice_captained`, `most_transferred_in`, `top_element`) are NULL before results; others NOT NULL; `top_element` FK → elements |
| Events: `finished`, `is_current`, `is_next`, `is_previous`, `can_manage`, `can_enter`, `released`, `cup_leagues_created`, `data_checked`, `h2h_ko_matches_created` | `BOOLEAN` | NOT NULL |
| Events: `top_element_info_player_id`, `top_element_info_points` | `INTEGER` | NULL when no `top_element_info`; player ID FK → elements |
| Events: `release_time`, `overrides` | — | Omit: `release_time` is NULL in all 38 rows and overrides carry only empty configuration |
| Event chip plays: `event_id`, `chip_name` | `INTEGER`, `TEXT` | NOT NULL; **PK** (`event_id`, `chip_name`); event FK → events |
| Event chip plays: `num_played` | `INTEGER` | NOT NULL |

### `stg_official_fpl_fixtures` (`soffx_`) and `stg_official_fpl_fixture_stats` (`soffs_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Fixtures: `fixture_id` (source `id`) | `INTEGER` | NOT NULL; **PK** |
| Fixtures: `code`, `event`, `team_h`, `team_a`, `team_h_difficulty`, `team_a_difficulty`, `minutes`, `pulse_id` | `INTEGER` | `event` may be NULL if unassigned; team FKs → official teams; event FK → official events; `pulse_id` is `0` on every row in this snapshot, so keep it nullable and drop it if later captures stay uninformative |
| Fixtures: `kickoff_time` | `TIMESTAMP` | NULL for unscheduled fixtures |
| Fixtures: `started`, `finished`, `finished_provisional`, `provisional_start_time` | `BOOLEAN` | NOT NULL |
| Fixtures: `team_h_score`, `team_a_score` | `INTEGER` | NULL for unplayed fixtures |
| Fixture stats: `fixture_id`, `identifier`, `side`, `player_id` (source `element`) | `INTEGER`, `TEXT`, `CHAR(1)`, `INTEGER` | NOT NULL; **Candidate PK** (`fixture_id`, `identifier`, `side`, `player_id`); fixture/player FKs |
| Fixture stats: `value` | `INTEGER` | NOT NULL |

The fixture `stats` list becomes one row per `{identifier, side, element, value}`; `side` is `h`/`a`.

### `stg_official_fpl_element_history` (`sofeh_`), `stg_official_fpl_element_history_past` (`sofehp_`), `stg_official_fpl_element_upcoming_fixtures` (`sofeuf_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| History: `player_id` (from filename), `fixture_id` | `INTEGER` | NOT NULL; **PK** (`player_id`, `fixture_id`); FKs to elements and fixtures |
| History: `opponent_team`, `round`, `team_h_score`, `team_a_score`, `minutes`, `total_points`, `bps`, `bonus`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `starts`, `tackles`, `recoveries`, `clearances_blocks_interceptions`, `defensive_contribution`, `value`, `transfers_balance`, `selected`, `transfers_in`, `transfers_out` | `INTEGER` | Scores nullable when unknown; other fields NOT NULL in observed rows; opponent FK → teams |
| History: `kickoff_time` | `TIMESTAMP` | NOT NULL in inspected history rows |
| History: `was_home`, `modified` | `BOOLEAN` | NOT NULL |
| History: `influence`, `creativity`, `threat`, `ict_index`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded` | `DECIMAL(12,4)` | Source numeric strings; NOT NULL in inspected history |
| History past: `element_code`, `season_name` | `INTEGER`, `TEXT` | NOT NULL; **PK** (`element_code`, `season_name`); candidate FK `element_code` → elements.`code` only where the historical player is present in the current element snapshot |
| History past: `start_cost`, `end_cost`, `total_points`, `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `starts`, `clearances_blocks_interceptions`, `recoveries`, `tackles`, `defensive_contribution` | `INTEGER` | NOT NULL in inspected rows; defensive columns carry real values (for example 37/304/1/0 on a 2025/26 row), so they must be staged |
| History past: `influence`, `creativity`, `threat`, `ict_index`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded` | `DECIMAL(12,4)` | Numeric strings; NOT NULL in inspected rows |
| Upcoming: `player_id` (from filename), `fixture_id` (source `id`) | `INTEGER` | NOT NULL; **PK** (`player_id`, `fixture_id`); FKs to elements and fixtures |
| Upcoming: `code`, `event`, `team_h`, `team_a`, `minutes`, `difficulty` | `INTEGER` | Team IDs FK → teams; nullable only if source blank |
| Upcoming: `team_h_score`, `team_a_score` | `INTEGER` | NULL for unplayed fixtures |
| Upcoming: `kickoff_time`, `event_name` | `TIMESTAMP`, `TEXT` | `kickoff_time` may be NULL; event name not null in inspected rows |
| Upcoming: `finished`, `is_home`, `provisional_start_time` | `BOOLEAN` | NOT NULL in inspected rows |

Upcoming summaries repeat the same fixture for many players, so their key is `(player_id, fixture_id)`, not `fixture_id` alone.

### `stg_official_fpl_live_gameweek` (`soflg_`) and `stg_official_fpl_live_explain` (`sofle_`)

`gameweek` is read from `live_gameweeks/gw_<n>.json`; live values are one row per player per gameweek and season, refreshed in place if recaptured. A snapshot may omit players (`gw_04` carries 659 of the 667 elements); do not treat an absent live row as a deletion.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Live: `gameweek`, `player_id` (source `id`) | `INTEGER` | NOT NULL; **PK** (`gameweek`, `player_id`); gameweek FK → events; player FK → elements |
| Live: `minutes`, `goals_scored`, `assists`, `clean_sheets`, `goals_conceded`, `own_goals`, `penalties_saved`, `penalties_missed`, `yellow_cards`, `red_cards`, `saves`, `bonus`, `bps`, `clearances_blocks_interceptions`, `recoveries`, `tackles`, `defensive_contribution`, `starts`, `total_points` | `INTEGER` | NOT NULL in inspected snapshots |
| Live: `influence`, `creativity`, `threat`, `ict_index`, `expected_goals`, `expected_assists`, `expected_goal_involvements`, `expected_goals_conceded` | `DECIMAL(12,4)` | Source numeric strings; NOT NULL |
| Live: `in_dreamteam`, `played`, `modified` | `BOOLEAN` | NOT NULL |
| Explain: `gameweek`, `player_id`, `fixture_id`, `identifier` | `INTEGER`, `INTEGER`, `INTEGER`, `TEXT` | NOT NULL; **Candidate PK** (`gameweek`, `player_id`, `fixture_id`, `identifier`); FKs to live parent, player, fixture |
| Explain: `points`, `value`, `points_modification` | `INTEGER` | NOT NULL |

### `stg_official_fpl_snapshot` (`sofs_`)

`bootstrap-static.json` also has scalar `total_players` and nested `game_settings`/`game_config`. If retained, use one row per season: `season TEXT NOT NULL` (**PK**, as above), `total_players INTEGER NOT NULL`, `game_settings_json JSON NOT NULL`, `game_config_json JSON NOT NULL`. There is no additional source key; do not invent a hash. Refresh the row for the same season rather than appending a duplicate. These are configuration/snapshot summary, not entity facts.

---

## 5. Premier League API

The response-page `pageInfo` is pagination metadata, not a football row, and is not copied into each staged record. IDs arrive as integral JSON numbers represented with decimal points in some responses; type them as integers. Fixture and statistic season folders use slightly different names for 2026-27, so normalize the path to the season row before loading.

### `stg_pl_seasons` (`spls_`), `stg_pl_clubs` (`splc_`), `stg_pl_teams` (`splt_`), `stg_pl_players` (`splp_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Seasons: `season_id` (source `id`) | `INTEGER` | NOT NULL; **PK** |
| Seasons: `season_label` | `TEXT` | NOT NULL |
| Seasons: `season_start_year`, `season_end_year` | `SMALLINT` | NOT NULL; normalized from label for matching file paths |
| Clubs: `club_id` | `BIGINT` | NOT NULL; **PK** |
| Clubs: `name`, `short_name`, `abbreviation` | `TEXT` | Nullable if absent from a team object |
| Teams: `team_id` (source `id`) | `BIGINT` | NOT NULL; **PK** |
| Teams: `name`, `short_name`, `team_type`, `opta_id` | `TEXT` | Nullable when not supplied in an owner object |
| Teams: `club_id` | `BIGINT` | Nullable; FK → `stg_pl_clubs.club_id` |
| Teams: `club_name`, `club_short_name`, `club_abbreviation` | `TEXT` | Nullable; flattened from nested club object |
| Teams: `grounds_json` | `JSON` | Nullable; team-stat owner sometimes supplies grounds/capacity/coordinates |
| Players: `player_id` (owner `id`) | `BIGINT` | NOT NULL; **PK** |
| Players: `player_ref_id` (owner `playerId`) | `BIGINT` | Nullable |
| Players: `opta_id`, `display_name`, `first_name`, `middle_name`, `last_name`, `position`, `position_info`, `birth_date_label`, `birth_country_code`, `birth_country`, `birth_place`, `national_team_code`, `national_team_country`, `national_team_demonym` | `TEXT` | Nullable when omitted; normal name/position values are present |
| Players: `shirt_number` | `DECIMAL(6,2)` | NULL when unknown; source is numeric |
| Players: `birth_date_millis` | `BIGINT` | Nullable; source `birth.date.millis` |
| Players: `on_loan` | `BOOLEAN` | Nullable if absent |

Player stat owners carry no team reference, so there is no `current_team_id` to stage; do not add that column. Owner `age` strings (for example `"35 years 294 days"`) are derivable from the birth date and are not staged.

Player/team identity objects are repeated in stats files. Deduplicate them on provider IDs into the entity tables rather than repeating each biography with every stat value. Enforce player/team FKs only after the entity union is loaded.

### `stg_pl_fixtures` (`splf_`) and `stg_pl_fixture_teams` (`splft_`)

One fixture row from the 143 pages; the two nested `teams[]` objects become child rows so team ID and side are explicit.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Fixtures: `fixture_id` (source `id`) | `BIGINT` | NOT NULL; **PK** |
| Fixtures: `season_id` | `INTEGER` | NOT NULL; FK → `stg_pl_seasons.season_id` |
| Fixtures: `opta_fixture_id` (source `altIds.opta`), `status`, `phase`, `outcome`, `fixture_type` | `TEXT` | Nullable where absent; `outcome` NULL before completion |
| Fixtures: `replay`, `neutral_ground`, `behind_closed_doors`, `extra_time`, `shootout` | `BOOLEAN` | Nullable; some fields appear only in later seasons |
| Fixtures: `attendance`, `kickoff_millis`, `provisional_kickoff_millis`, `ground_id`, `clock_seconds`, `gameweek_id`, `gameweek_number`, `competition_phase_id`, `competition_season_id` | `BIGINT`/`INTEGER` | Nullable where missing; `competition_season_id` FK → seasons; no ground dimension supplied |
| Fixtures: `kickoff_gmt_offset`, `kickoff_completeness`, `provisional_kickoff_gmt_offset`, `provisional_kickoff_completeness` | `DECIMAL(10,4)` | Nullable where absent |
| Fixtures: `kickoff_label`, `provisional_kickoff_label`, `ground_name`, `ground_city`, `ground_source`, `clock_label`, `competition_phase_type` | `TEXT` | Nullable where nested object/field is absent |
| Fixtures: `gameweek_range` | `JSON` | Nullable; nested competition-phase range |
| Fixture teams: `fixture_id`, `side` | `BIGINT`, `SMALLINT` | NOT NULL; **PK** (`fixture_id`, `side`), side is array order 1/2; fixture FK → fixtures |
| Fixture teams: `team_id` | `BIGINT` | NOT NULL; FK → `stg_pl_teams.team_id` |
| Fixture teams: `score` | `INTEGER` | NULL for unplayed fixtures |

Kickoff/provisional-kickoff subobjects are nullable on older matches; `clock` is nullable on 330 rows. Ground identity is sparse and does not merit a separate table yet.

### `stg_pl_fixture_goals` (`splg_`)

One child row per `goals[]` item; use its array position as a simple goal ordinal because no separate goal ID is supplied.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `fixture_id`, `goal_number` | `BIGINT`, `SMALLINT` | NOT NULL; **PK** (`fixture_id`, `goal_number`); fixture FK → `stg_pl_fixtures` |
| `player_id`, `assist_player_id` | `BIGINT` | Nullable scorer/assist IDs; candidate FKs → `stg_pl_players.player_id` (verify owner coverage before enforcement) |
| `clock_seconds` | `INTEGER` | Nullable |
| `clock_label`, `phase`, `goal_type`, `description` | `TEXT` | Nullable where absent |

### `stg_pl_stat_values` (`splsv_`)

One row per owner and stat in `stats/<season>/{players,teams}/<stat>/page-*.json` content arrays. The path supplies season/entity type/stat name; the row supplies owner facts.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_id`, `entity_type`, `stat_name`, `owner_id` | `INTEGER`, `TEXT`, `TEXT`, `BIGINT` | NOT NULL; **Candidate PK** (`season_id`, `entity_type`, `stat_name`, `owner_id`); season FK → seasons; `owner_id` points to players or teams based on `entity_type` (polymorphic FK) |
| `rank` | `INTEGER` | Nullable if unranked |
| `owner_name`, `description` | `TEXT` | Nullable if absent |
| `value` | `DECIMAL(14,4)` | NOT NULL in inspected rows; JSON emits numbers as floats |

`additionalInfo` is `{}` in inspected stat rows and is dropped. `penaltyShootouts` is `[]` on all 13,546 fixtures and is dropped. Stat-row `entity`/`type` repeat the stat path/entity type and need not be retained a second time. Check the composite natural key for duplicates when pages are combined. Some stat files have an empty `content[]` array; loading must tolerate empty pages with no rows.

---

## 6. FotMob

Normalize numeric-string IDs to integers, including match/team IDs that appear as strings in some match/season payloads and integers elsewhere. Use season from file path when present. The provider exposes many nested presentation fields; the tables below keep the actual football rows and use JSON only for the irregular small remainder.

### `stg_fotmob_leagues` (`sfml_`) and `stg_fotmob_league_group_membership` (`sfmg_`)

From `all_leagues.json`. A league can occur in more than one list, so keep one league dimension and a separate membership table rather than duplicating its identity.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Leagues: `league_id` (source `id`) | `INTEGER` | NOT NULL; **PK** |
| Leagues: `league_name`, `localized_name`, `page_url`, `country_code` | `TEXT` | `league_name`, `page_url`, `country_code` NOT NULL; localized name may be NULL |
| Membership: `league_id`, `group_kind`, `group_code` | `INTEGER`, `TEXT`, `TEXT` | NOT NULL; **PK** (`league_id`, `group_kind`, `group_code`); FK `league_id` → leagues |
| Membership: `group_name`, `group_localized_name` | `TEXT` | `group_localized_name` nullable; `group_name` may be absent for the `popular` list |

`group_kind` distinguishes `popular`, `international`, and `country`; use `POPULAR` for the popular list and source country code for `group_code` where available.

### `stg_fotmob_seasons` (`sfmss_`), `stg_fotmob_teams` (`sfmt_`), `stg_fotmob_season_standings` (`sfmstd_`), `stg_fotmob_season_archive` (`sfmsa_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Seasons: `season_slug` (file stem), `season_name` | `TEXT` | `season_slug` **PK**, NOT NULL; `season_name` NOT NULL, taken from `details.selectedSeason` (not `overview.season`, which carries the latest season) |
| Seasons: `season_id`, `league_id` | `INTEGER` | `season_id` nullable when no numeric season ID is supplied; league ID NOT NULL, FK → leagues |
| Seasons: `league_name`, `country`, `gender`, `data_provider`, `selected_season`, `latest_season` | `TEXT` | Nullable where absent |
| Seasons: `can_sync_calendar` | `BOOLEAN` | Nullable where absent |
| Seasons: `overview_json` | `JSON` | Nullable; retain the small season-overview object if its top-player/overview summary is needed rather than duplicating it into another table |
| Teams: `team_id` | `INTEGER` | NOT NULL; **PK**; cast string IDs to integer |
| Teams: `team_name`, `short_name` | `TEXT` | Team name NOT NULL; short name nullable |
| Teams: `page_url`, `image_url` | `TEXT` | Nullable |
| Standings: `season_slug`, `table_variant`, `team_id` | `TEXT`, `TEXT`, `INTEGER` | NOT NULL; **Candidate PK** (`season_slug`, `table_variant`, `team_id`); season/team FKs |
| Standings: `team_name`, `team_short_name`, `scores_text`, `qualification_color` | `TEXT` | Nullable except source team name |
| Standings: `position`, `played`, `wins`, `draws`, `losses`, `goal_difference`, `points` | `INTEGER` | NOT NULL for standard standings rows; source `idx` maps to `position` |
| Standings: `goals_scored` | `INTEGER` | NULL except on `home`/`away`/`form` variants, which carry `goalsScored` |
| Standings: `featured_in_match` | `BOOLEAN` | NULL except on `form` rows, which carry `featuredInMatch` |
| Standings: `deduction` | `INTEGER` | NULL when not supplied |
| Standings: `xg`, `xg_conceded`, `xpoints`, `xg_difference` | `DECIMAL(12,4)` | NULL for non-xG variants and older seasons; source `xPoints` maps to `xpoints` and `xgDiff` maps to `xg_difference` |
| Standings: `xg_metrics_json` | `JSON` | NULL; retains the remaining xG-variant measures (`xPosition`, `position`, `xPositionDiff`, `xPointsDiff`, `xgConcededDiff`) rather than promoting each to a column |
| Season archive: `league_id`, `season_name` | `INTEGER`, `TEXT` | NOT NULL; **PK** (`league_id`, `season_name`); league FK |
| Season archive: `winner_team_id`, `loser_team_id` | `INTEGER` | Nullable; candidate FKs → FotMob teams |
| Season archive: `winner_name`, `loser_name` | `TEXT` | Nullable |

Standings `table_variant` is `all`, `home`, `away`, `form`, or `xg`; `xg` appears only in recent seasons. The source `id` may be text or integer and is cast to team ID; xG rows repeat it as `teamId`/`teamName`, which map to the same team columns. Drop standings `ongoing` and other always-null fields. Season-level `teamForm` (recent-result lists, including non-league friendlies) and in-season `nextOpponent` blocks are not staged; extend the schema with new tables if that form/next-fixture detail is later needed. `season_id` comes from statistic season catalogues when available; the season file itself always provides a useful `season_slug`/name.

### `stg_fotmob_fixtures` (`sfmf_`)

One row per match, combining `seasons/<season>.json` `fixtures.allMatches[]` and detailed `matches/<season>/match_<id>.json` where available.

| Columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| `season_slug`, `match_id` | `TEXT`, `BIGINT` | NOT NULL; **PK** (`season_slug`, `match_id`) |
| `league_id`, `parent_league_id` | `INTEGER` | League FK → `stg_fotmob_leagues`; parent ID nullable if not catalogued |
| `match_name`, `round`, `league_round_name`, `status_reason`, `score_text` | `TEXT` | Nullable when absent |
| `home_team_id`, `away_team_id` | `INTEGER` | NOT NULL where the fixture has teams; FKs → `stg_fotmob_teams` |
| `kickoff_at` | `TIMESTAMP` | Nullable for unscheduled matches |
| `home_score`, `away_score`, `home_red_cards`, `away_red_cards` | `INTEGER` | Scores/red-card counts nullable when unplayed/not provided |
| `started`, `finished`, `cancelled`, `awarded` | `BOOLEAN` | Nullable only if absent in a season fixture summary |
| `context_json` | `JSON` | Nullable; optional player-of-match, weather, H2H, team-form, top-player, stadium/referee/attendance, and half-time-detail objects that vary by match |

Match IDs from `general.matchId` are strings while `matchFacts.matchId` is an integer; they agree in inspected samples and should be cast to `BIGINT`. Scores may be unknown for upcoming fixtures. The detailed match status reason can be kept as a short string; keep the irregular remainder in `context_json` rather than making empty/sparse columns for every UI field.

### `stg_fotmob_players` (`sfmp_`), `stg_fotmob_match_players` (`sfmmp_`), `stg_fotmob_match_events` (`sfme_`)

Use the canonical event array under the match-facts/events structure. Do not also stage the name-keyed home/away goal summary as extra events; it is a duplicate presentation of goal events and uses names as keys.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Players: `player_id` | `BIGINT` | NOT NULL; **PK** |
| Players: `player_name`, `first_name`, `last_name`, `full_name`, `opta_id` | `TEXT` | Name NOT NULL; other names/Opta ID nullable |
| Match players: `season_slug`, `match_id`, `player_id` | `TEXT`, `BIGINT`, `BIGINT` | NOT NULL; **PK** (`season_slug`, `match_id`, `player_id`); match/player FKs |
| Match players: `team_id`, `position_id`, `usual_position_id` | `INTEGER` | Nullable when absent; team FK → FotMob teams |
| Match players: `is_goalkeeper`, `is_potm` | `BOOLEAN` | Nullable if absent; `is_potm` is the source `isPotm` flag and agrees with the match `playerOfTheMatch` object |
| Match players: `shirt_number` | `TEXT` | Nullable; supplied as text |
| Match players: `player_shotmap_json`, `player_facts_json` | `JSON` | Nullable; optional per-player `shotmap` list and `funFacts` list from `playerStats` |
| Events: `season_slug`, `match_id`, `event_id` | `TEXT`, `BIGINT`, `BIGINT` | NOT NULL; **PK** (`season_slug`, `match_id`, `event_id`); match FK |
| Events: `event_type`, `player_name`, `name_str`, `first_name`, `last_name`, `full_name`, `card`, `card_description`, `card_reason`, `assist_str` | `TEXT` | Nullable where event does not carry that detail; `assist_str` only on goals with an assist |
| Events: `minute`, `extra_minute`, `overload_time`, `player_id`, `assist_player_id`, `home_score`, `away_score`, `minutes_added` | `INTEGER` | Nullable when absent; player/assist FKs → FotMob players; `minutes_added` only on `AddedTime` rows |
| Events: `swap_json`, `var_json` | `JSON` | Nullable; `swap` pair (substitution on/off entries plus `injuredPlayerOut`) and the `VAR` decision object |
| Events: `is_home` | `BOOLEAN` | NOT NULL in inspected events |

The canonical array carries `Goal`, `Card`, `MissedPenalty`, `Substitution`, `AddedTime`, `Half`, `Comment`, and `VAR` rows. `Half`/`Comment` rows carry no extra football fact beyond time and score; `Comment` rows are placeholders (`eventId 0`, blank player). Goal `shotmapEvent`/`newScore` detail lives in the shots table and fixture scores, so it is not repeated here.

`event_id` is the provider event ID; if a payload ever omits it, use the array ordinal as a fallback and flag that variation. Card detail fields are often null for non-card events. Do not use player name as a key.

### `stg_fotmob_match_lineups` (`sfmlu_`) and `stg_fotmob_match_lineup_players` (`sfmlp_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Lineups: `season_slug`, `match_id`, `team_id` | `TEXT`, `BIGINT`, `INTEGER` | NOT NULL; **PK** (`season_slug`, `match_id`, `team_id`); FKs to match/team |
| Lineups: `lineup_side`, `lineup_type`, `source`, `formation` | `TEXT` | Side/type/source required when a lineup exists; formation nullable |
| Lineups: `rating`, `average_starter_age` | `DECIMAL(8,3)` | Nullable rating; average age may be absent |
| Lineups: `total_starter_market_value` | `BIGINT` | Nullable |
| Lineups: `coach_json` | `JSON` | Nullable; coach ID/name/age/country/primary team structure |
| Lineup players: `season_slug`, `match_id`, `team_id`, `player_id` | `TEXT`, `BIGINT`, `INTEGER`, `BIGINT` | NOT NULL; **PK** (`season_slug`, `match_id`, `team_id`, `player_id`); FKs to lineup parent/player/team |
| Lineup players: `slot`, `player_name`, `first_name`, `last_name`, `country_name`, `country_code`, `shirt_number` | `TEXT` | `slot` required (`starter`/`sub`/`unavailable`); other fields nullable |
| Lineup players: `age`, `position_id`, `usual_position_id`, `market_value` | `INTEGER`/`BIGINT` | Nullable; position/layout absent for some subs/unavailable players |
| Lineup players: `horizontal_x`, `horizontal_y`, `horizontal_height`, `horizontal_width`, `vertical_x`, `vertical_y`, `vertical_height`, `vertical_width`, `performance_rating` | `DECIMAL(10,4)` | Nullable; layout/rating not supplied for all slots |
| Lineup players: `fantasy_score` | `TEXT` | Nullable |
| Lineup players: `substitution_events_json`, `unavailability_json`, `rankings_json`, `performance_events_json` | `JSON` | Nullable; substitution events, the `unavailability` object, the `rankings` object (for example distance/speed ranks, non-null on many starters), and other `performance.events` entries (for example assist flags) |

### `stg_fotmob_match_player_stats` (`sfmps_`), `stg_fotmob_match_team_stats` (`sfmts_`), `stg_fotmob_match_shots` (`sfmshot_`), `stg_fotmob_match_momentum` (`sfmm_`)

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Player stats: `season_slug`, `match_id`, `player_id`, `category`, `display_name` | `TEXT`, `BIGINT`, `BIGINT`, `TEXT`, `TEXT` | NOT NULL; **Candidate PK** (`season_slug`, `match_id`, `player_id`, `category`, `display_name`); FKs to match/player |
| Player stats: `stat_key`, `stat_value_type` | `TEXT` | `stat_key` nullable for some rows; type not null when present |
| Player stats: `stat_value`, `stat_total` | `DECIMAL(14,4)`, `INTEGER` | `stat_value` nullable for nonnumeric/toggle entries; `stat_total` nullable |
| Player stats: `stat_value_raw` | `TEXT` or `JSON` | Retain the source value for nonnumeric/toggle entries (and any numeric value that cannot be cast without loss); NULL when `stat_value` fully represents it |
| Player stats: `team_id`, `is_goalkeeper` | `INTEGER`, `BOOLEAN` | Team FK → FotMob teams; goalkeeper flag nullable |
| Team stats: `season_slug`, `match_id`, `period`, `stat_key`, `group_key` | `TEXT`, `BIGINT`, `TEXT`, `TEXT`, `TEXT` | NOT NULL; **Candidate PK** (`season_slug`, `match_id`, `period`, `group_key`, `stat_key`); match FK |
| Team stats: `stat_title`, `home_value`, `away_value`, `format`, `stat_type`, `highlighted` | `TEXT` | Home/away values nullable; keep as text because values can include formatted percentages such as `401 (82%)` |
| Shots: `season_slug`, `match_id`, `shot_id` | `TEXT`, `BIGINT`, `BIGINT` | NOT NULL; **PK** (`season_slug`, `match_id`, `shot_id`); match FK |
| Shots: `team_id`, `player_id`, `keeper_id` | `INTEGER`, `BIGINT`, `BIGINT` | Team/player FKs; keeper nullable and FK when present |
| Shots: `event_type`, `shot_type`, `situation`, `period`, `player_name`, `first_name`, `last_name`, `full_name`, `team_color` | `TEXT` | Nullable where missing |
| Shots: `minute`, `added_minute` | `INTEGER` | `added_minute` nullable |
| Shots: `x`, `y`, `blocked_x`, `blocked_y`, `goal_crossed_y`, `goal_crossed_z`, `expected_goals`, `expected_goals_on_target` | `DECIMAL(12,6)` | Blocked/goal-cross/on-target values nullable |
| Shots: `is_blocked`, `is_on_target`, `is_own_goal`, `is_saved_off_line`, `is_from_inside_box` | `BOOLEAN` | NOT NULL where shot row exists |
| Shots: `on_goal_shot_json` | `JSON` | Nullable; `{x,y,zoomRatio}` object |
| Momentum: `season_slug`, `match_id`, `minute` | `TEXT`, `BIGINT`, `INTEGER` | NOT NULL; **PK** (`season_slug`, `match_id`, `minute`); match FK |
| Momentum: `value` | `DECIMAL(12,4)` | NOT NULL |

For shot IDs, use match ID as part of the key even though inspected IDs were unique globally; this avoids relying on global uniqueness. Team-stat raw display values remain text because some contain both a count and percentage. Do not collapse a nonnumeric/toggle player stat to a NULL numeric value without preserving its source value. The player-stat `stat_key` can be NULL, so the display name remains part of the candidate key.

### `stg_fotmob_stat_catalogue` (`sfmsc_`) and `stg_fotmob_stat_leaders` (`sfmsl_`)

These tables cover `seasons/*.json` leader arrays, `statistics/<season>/{players,teams}/<stat>.json`, and the three `statistics/catalogue_*.json` payloads. Files are top-N leaders (usually 90 players or 20 teams), not a complete player/team season-stat fact table.

| Table / columns (suffixes) | SQL type | Nullable / key |
|---|---|---|
| Catalogue: `stat_name` | `TEXT` | NOT NULL; **Candidate PK** |
| Catalogue: `stat_title`, `localized_title_id`, `stat_category`, `localized_category_id` | `TEXT` | Nullable where omitted from a catalogue variant |
| Leaders: `source_kind`, `season_slug`, `source_season_ref`, `stat_name`, `entity_type`, `entity_id` | `TEXT`, `TEXT`, `TEXT`, `TEXT`, `TEXT`, `INTEGER` | `source_kind`, slug, stat/type/entity NOT NULL; raw season ref nullable; **PK** (`source_kind`, `season_slug`, `stat_name`, `entity_type`, `entity_id`); season/stat catalogue FKs where mapped |
| Leaders: `team_id`, `rank`, `position_id` | `INTEGER` | `team_id` FK → FotMob teams; rank NOT NULL; `position_id` NULL on team rows |
| Leaders: `entity_name`, `country_code`, `stat_format`, `substat_format`, `substat_title`, `substat_localized_title_id` | `TEXT` | `entity_name`/stat format required; `country_code` is the source `ccode` and is NULL on team rows without one; substat metadata nullable |
| Leaders: `stat_value`, `substat_value` | `DECIMAL(14,4)` | `stat_value` NOT NULL; substat may be NULL |
| Leaders: `stat_fractions`, `substat_fractions` | `INTEGER` | Substat fractions nullable |

`source_kind` distinguishes per-season statistic files, `catalogue_players_current`, `catalogue_teams`, and season-overview leader lists, which can contain overlapping snapshots. The source has `currentSeasonId` as an integer in some files and a season-name string in another; keep it as text during loading and resolve to `season_slug` where possible. Tied ranks are possible, so key by entity ID rather than rank alone.

The season file's overview may be retained in `overview_json`; its top-player entries can instead be normalized into the leader table. SEO/navigation fields, empty transfers/playoff/shot-map objects, and `QAData` are not separate staging facts. The match `context_json` field above is the simple place to retain optional irregular player-of-match/weather/H2H detail if it is needed.

---

## Items to resolve during implementation

These are open checks, not blockers to the proposed table shapes:

1. **No payloads for ClubElo or SofaScore.** Their current retrieval attempts failed (ClubElo timeout; SofaScore 403), so there is no actual structure to type. Retry collection before adding schemas for either provider.
2. **Candidate keys need a full-load uniqueness check.** In particular, check the football-data five-column match key, Vaastav player-gameweek four-column key, Understat team-history key, and Premier League stat-value key before adding constraints.
3. **Vaastav early fixtures cannot be joined.** The 2016-17 and 2017-18 gameweek files have a `fixture` value, but those seasons have no `fixtures.csv`/`teams.csv`; keep the value, but do not declare a fixture FK for those seasons. 2019-20 has postponed-fixture duplicates across gameweeks, so do not key gameweek rows by player+fixture alone.
4. **A few source references are ambiguous.** Understat roster `roster_in`/`roster_out` nonzero values did not match shot IDs, and the player IDs in roster/shot/league records should not be linked until their identity semantics are confirmed. Understat league players expose team name, not team ID. Football-data `HBP`/`ABP` meanings were not resolved; retain their source abbreviations.
5. **Normalize file-derived season values consistently.** Football-data filename dates are mixed two-/four-digit years; Vaastav seasons are `YYYY-YY`; Understat season comes from a filename/folder; Premier League 2026-27 has a long folder name; FotMob season IDs/names use inconsistent formats. Store a readable season/year field as proposed; no hash is needed.
6. **Normalize a few raw JSON type differences.** FPL CSVs contain empty/`None` and Python-literal-looking nested cells; Understat numeric IDs/metrics are JSON strings; FotMob IDs are string in some payloads and integer in others, and `currentSeasonId` is not consistently typed. Cast where safe, use NULL for actual empty values, and retain JSON only for the nested fields called out above.
7. **Do not cross-link providers by coincidental IDs or names.** Each source has its own player/team ID namespace. Cross-provider entity matching is a separate decision; the FKs above are provider-local only.

These checks can be handled while creating the actual DDL/load process. The raw data was still profiled through the available providers, and the proposed schemas do not depend on resolving them first.
