# Premier League / FPL Data Project — Normalised Schema Seed

## 1. Purpose

This document captures the agreed schema-design principles for the Premier League / FPL predictive data project.

The focus is the **canonical relational model** that sits downstream of raw ingestion, staging, identity resolution, and reconciliation.

The intended downstream use is predictive modelling, so the schema should favour:

- clear table grain
- wide canonical fact tables where appropriate
- reproducibility
- easy joins
- explicit naming
- rebuildability from upstream data
- minimal unnecessary fragmentation


---

## 2. Core Design Philosophy

The key rule is:

> If columns describe the same entity at the same grain and roughly the same lifecycle, they should usually live in the same table.

Wide tables are not considered a problem in themselves.

For this project, splitting a single logical grain into many narrow tables merely to avoid width is generally undesirable.

Example:

```text
player_fixture_stats
```

represents:

> one player in one fixture

Therefore it is reasonable for that table to contain:

- attacking stats
- passing stats
- possession stats
- defensive stats
- discipline stats
- minutes
- starting information

even if the result is 100+ columns.

Likewise:

```text
team_fixture_stats
```

represents:

> one team in one fixture

and should contain the full team statistical record for that fixture.

The main reason to split data is **different grain**, not table width.


---

## 3. Grain First

Every table should have an explicitly documented grain.

Examples:

```text
fixtures
one row per fixture

team_fixture_stats
one row per team per fixture

player_fixture_stats
one row per player appearance per fixture

fixture_squads
one row per player selected in a fixture squad

shots
one row per shot

passes
one row per pass

events
one row per event
```

Grain should be treated as a first-class schema property.

Most structural errors become much easier to spot if every table clearly states:

> What does one row represent?


---

## 4. Core Fixture Model

The preferred high-level structure is:

```text
fixtures
--------
f_id
f_competition_season_id
f_gameweek_id
f_home_team_id
f_away_team_id
f_kickoff
f_status
f_venue_id
f_referee_id
f_home_goals
f_away_goals
...
```

The fixture row contains match-level context and selected fixture-level outcomes.

Potential fixture-level fields include:

- home team
- away team
- kickoff
- competition season
- gameweek
- venue
- referee
- status
- attendance
- home goals
- away goals

It is acceptable for some values such as goals to also appear in the corresponding team-level fact rows.

This is deliberate and controlled duplication rather than accidental denormalisation.


---

## 5. Team Fixture Statistics

The team fixture table should use one row per team per fixture.

Preferred structure:

```text
team_fixture_stats
------------------
tfs_fixture_id
tfs_team_id

tfs_goals
tfs_shots
tfs_shots_on_target
tfs_xg
tfs_possession
tfs_passes_attempted
tfs_passes_completed
tfs_crosses_attempted
tfs_crosses_completed
tfs_long_balls_attempted
tfs_long_balls_completed
tfs_tackles
tfs_interceptions
tfs_clearances
tfs_recoveries
tfs_duels
tfs_duels_won
tfs_aerial_duels
tfs_aerial_duels_won
tfs_fouls
tfs_corners
tfs_yellow_cards
tfs_red_cards
...
```

Natural key:

```text
(tfs_fixture_id, tfs_team_id)
```

A synthetic key is optional, but not required unless there is a practical reason to add one.

The canonical row should contain the agreed reconciled values after upstream source reconciliation.


---

## 6. Why Team Statistics Should Be Row-Oriented by Team

Avoid a structure such as:

```text
f_home_shots
f_away_shots
f_home_passes
f_away_passes
f_home_tackles
f_away_tackles
...
```

for the full statistical record.

The fixture can still contain high-value fixture-level fields such as home and away goals, but the complete team statistical record is cleaner as two rows:

```text
fixture 5001
team ARS
team CHE
```

This makes downstream team queries simpler.

For example:

```sql
SELECT
    tfs_team_id,
    AVG(tfs_shots)
FROM team_fixture_stats
GROUP BY tfs_team_id;
```

rather than repeatedly switching between home and away columns.


---

## 7. Opponent and Home/Away Flags

The canonical team fixture table does not need to store:

```text
opponent_id
is_home
```

because these are derivable from:

```text
fixtures.f_home_team_id
fixtures.f_away_team_id
```

However, they are extremely useful in analytical and modelling layers.

Therefore the analytical layer may expose:

```text
team_id
opponent_id
is_home
goals_for
goals_against
goal_difference
result
league_points
...
```

This is a useful general rule:

> Canonical tables store facts. Analytical tables may store convenient interpretations and derived context.


---

## 8. Player Fixture Statistics

The player-level equivalent is:

```text
player_fixture_stats
--------------------
pfs_fixture_id
pfs_player_id
pfs_team_id

pfs_started
pfs_minutes

pfs_goals
pfs_assists
pfs_shots
pfs_shots_on_target
pfs_xg
pfs_xa

pfs_passes_attempted
pfs_passes_completed
pfs_key_passes
pfs_crosses_attempted
pfs_crosses_completed
pfs_long_balls_attempted
pfs_long_balls_completed

pfs_touches
pfs_touches_in_box

pfs_tackles
pfs_interceptions
pfs_clearances
pfs_blocks
pfs_recoveries

pfs_duels
pfs_duels_won
pfs_aerial_duels
pfs_aerial_duels_won

pfs_dribbles_attempted
pfs_dribbles_completed

pfs_fouls_committed
pfs_fouls_won

pfs_yellow_cards
pfs_red_cards

...
```

Natural key:

```text
(pfs_fixture_id, pfs_player_id)
```

The player’s team should remain on the row:

```text
pfs_team_id
```

because this records the team represented in that specific fixture.

That is useful for:

- transfers
- historical seasons
- cup matches
- promoted/relegated teams


---

## 9. Wide Tables Are Preferred When Grain Is Stable

The preferred design is **not**:

```text
player_fixture_attacking
player_fixture_passing
player_fixture_defending
player_fixture_possession
player_fixture_discipline
```

if all those tables still have the same grain:

```text
(fixture_id, player_id)
```

That creates unnecessary joins without changing the conceptual entity.

The preferred design is:

```text
player_fixture_stats
```

with all stable same-grain columns together.

Similarly:

```text
team_fixture_stats
```

should remain wide rather than being split into arbitrary metric families.

Width alone is not considered a design problem.


---

## 10. When Data Should Be Split

Split data when the **grain changes**.

Examples:

```text
player_fixture_stats
one row per player per fixture

passes
many rows per player per fixture

shots
many rows per player per fixture

events
many rows per player/team per fixture
```

A pass event is fundamentally a different object from a player-match aggregate.

Likewise:

```text
fixture_squads
```

may contain players who were selected but never appeared.

That has a different grain and meaning from:

```text
player_fixture_stats
```

which should represent an actual appearance.


---

## 11. Event Layer

A generic event table may look like:

```text
events
------
e_id
e_fixture_id
e_team_id
e_player_id
e_period
e_match_second
e_event_type
e_x
e_y
e_end_x
e_end_y
...
```

The exact architecture may later evolve into:

```text
events
pass_events
shot_events
card_events
substitution_events
```

where `events` stores common event metadata and specialist subtype tables store event-specific attributes.

Example:

```text
pass_events
-----------
pe_event_id
pe_recipient_player_id
pe_end_x
pe_end_y
pe_successful
pe_cross
pe_through_ball
pe_long_ball
...
```

```text
shot_events
-----------
se_event_id
se_xg
se_body_part
se_result
se_shot_type
...
```

This avoids creating one extremely sparse universal event table while preserving event-level detail.


---

## 12. Player Selection and Appearance

It may be useful to distinguish:

```text
fixture_squads
```

from:

```text
player_fixture_stats
```

Example:

```text
fixture_squads
--------------
fs_fixture_id
fs_player_id
fs_team_id
fs_selection_status
```

Possible values:

```text
starter
bench
```

An unused substitute may exist in `fixture_squads` but not in `player_fixture_stats`.

This removes ambiguity between:

- player did not play
- player played but recorded zero events


---

## 13. Position Should Not Be One Simple Player Attribute

Position can mean several different things.

Possible concepts include:

```text
registered position
FPL position
nominal football position
starting match position
in-match role
```

Examples:

```text
MID
RW
AM
RWB
```

These should not automatically be collapsed into one field on `players`.

Possible locations:

```text
player_season_registration
fixture_squads
player_fixture_stats
player_position_history
```

The exact structure can be finalised later, but the concepts should remain distinct.


---

## 14. Competitions and Seasons

Avoid repeating free-text season labels across fixture data.

Suggested structure:

```text
competitions
------------
c_id
c_name
c_country
...
```

```text
competition_seasons
-------------------
cs_id
cs_competition_id
cs_start_year
cs_end_year
...
```

Then:

```text
fixtures.f_competition_season_id
```

This gives room for future expansion into:

- Premier League
- FA Cup
- EFL Cup
- Champions League
- Europa League
- Conference League

This matters because non-league fixtures can later contribute useful predictive context such as:

- fatigue
- minutes played
- rotation
- injuries
- fixture congestion


---

## 15. Gameweeks

Gameweeks should probably be their own entity.

Example:

```text
gameweeks
---------
gw_id
gw_competition_season_id
gw_number
gw_name
gw_deadline
gw_start_date
gw_end_date
...
```

Then:

```text
fixtures.f_gameweek_id
```

This matters especially for FPL because:

- blank gameweeks exist
- double gameweeks exist
- postponed fixtures move between gameweeks
- FPL gameweek assignment is not always equivalent to ordinary matchweek numbering


---

## 16. Fixture Rescheduling

Fixtures can change kickoff time or gameweek.

For predictive backtesting, what was known at a given point in time may matter.

Two possible approaches:

### Simple approach

Keep current values on `fixtures`:

```text
f_kickoff
f_gameweek_id
```

and maintain:

```text
fixture_schedule_history
```

Example:

```text
fixture_schedule_history
------------------------
fsh_fixture_id
fsh_kickoff
fsh_gameweek_id
fsh_effective_from
fsh_effective_to
```

### Fully temporal approach

Move all schedule information into a temporal history table.

The simpler current-value-plus-history design is probably sufficient initially.


---

## 17. Result Fields

Avoid storing every derived interpretation in canonical storage.

For example, from team goals it is possible to derive:

```text
win
draw
loss
goal_difference
league_points
```

These are suitable for analytical views or derived tables.

The canonical layer should primarily store the underlying observed facts:

```text
goals_for
goals_against
```

That said, controlled duplication such as:

```text
fixtures.f_home_goals
fixtures.f_away_goals
```

plus:

```text
team_fixture_stats.tfs_goals
```

is acceptable if it improves usability.


---

## 18. NULL vs Zero

This distinction is critical.

Example:

```text
pfs_shots = 0
```

means:

> The player appeared and took zero shots.

Whereas:

```text
pfs_shots = NULL
```

may mean:

> The statistic is unavailable or was not supplied.

The canonical model must preserve this distinction.

Do not automatically convert missing statistics to zero.


---

## 19. Naming Convention

The agreed preference is:

> Prefix column names using a short table-specific prefix.

Examples:

```text
players                -> p_
teams                  -> t_
fixtures               -> f_
player_fixture_stats   -> pfs_
team_fixture_stats     -> tfs_
gameweeks              -> gw_
competitions           -> c_
competition_seasons    -> cs_
fixture_squads         -> fs_
events                 -> e_
pass_events            -> pe_
shot_events            -> se_
```

Example:

```text
player_fixture_stats
--------------------
pfs_fixture_id
pfs_player_id
pfs_team_id
pfs_minutes
pfs_goals
pfs_assists
pfs_shots
pfs_passes_attempted
pfs_passes_completed
```

This provides explicitness without creating excessively long identifiers.

The convention should be consistent across the project.


---

## 20. PK and FK Naming

Primary and foreign keys should still use the table prefix.

Examples:

```text
fixtures
--------
f_id
f_home_team_id
f_away_team_id
```

```text
teams
-----
t_id
t_name
```

```text
player_fixture_stats
--------------------
pfs_fixture_id
pfs_player_id
pfs_team_id
```

This makes joins explicit and avoids ambiguous column names in wide modelling queries.


---

## 21. Naming Canonical Metrics

Provider field names should not leak into canonical tables.

Avoid canonical names such as:

```text
totalPass
accurateLongBalls
wonContest
```

Prefer consistent project terminology:

```text
pfs_passes_attempted
pfs_passes_completed

pfs_long_balls_attempted
pfs_long_balls_completed

pfs_dribbles_attempted
pfs_dribbles_completed

pfs_aerial_duels
pfs_aerial_duels_won
```

Provider-specific terminology belongs in staging.


---

## 22. Units

Choose canonical units early and apply them consistently.

Examples:

```text
time          -> seconds where precision matters
percentages   -> choose either 0–1 or 0–100 consistently
coordinates   -> 0–100
distance      -> metres
xG            -> decimal
```

The raw provider representation should remain available upstream.


---

## 23. Avoid Unnecessary Database Enums

Football-data categories can evolve.

Potentially unstable categories include:

- fixture status
- event type
- player role
- injury type
- position

Prefer constrained strings or lookup tables where practical rather than hard database enums that are difficult to evolve.


---

## 24. Derived Metrics

Canonical facts should favour raw observed values.

Example:

Store:

```text
pfs_passes_attempted
pfs_passes_completed
```

Derive:

```text
pass_completion_pct
```

Store:

```text
tfs_goals
```

Derive from paired team rows:

```text
goal_difference
result
league_points
```

Derived values belong naturally in:

- analytical views
- materialised analytical tables
- feature tables


---

## 25. Reconciliation Metadata

The canonical wide tables should contain the agreed reconciled values.

Do not clutter them with:

```text
fotmob_passes
whoscored_passes
sofascore_passes
```

Source disagreement remains upstream in staging and in a separate audit structure.

Possible metadata:

```text
reconciliation_log
------------------
rl_fixture_id
rl_player_id
rl_metric
rl_canonical_value
rl_method
rl_sources_used
rl_max_disagreement
rl_rule_version
```

The modelling tables should generally not need to know which provider supplied the final value.


---

## 26. Data Versioning

Because canonical tables are generated products, they should be rebuildable.

Relevant versions may include:

```text
reconciliation_version
canonical_schema_version
feature_version
```

The schema should support the principle:

> Raw data + configuration + code = rebuildable canonical dataset.


---

## 27. Controlled Denormalisation

This project is closer to a modelling warehouse than an OLTP transactional system.

Therefore controlled duplication is acceptable when it improves usability.

Examples:

```text
fixtures.f_home_goals
fixtures.f_away_goals
```

and:

```text
team_fixture_stats.tfs_goals
```

may coexist.

Likewise an analytical layer may duplicate:

```text
opponent_id
is_home
```

even though both are derivable.

The important requirement is that duplication should be:

- intentional
- reproducible
- script-generated
- internally validated


---

## 28. Indexing

Likely useful indexes include:

```text
fixtures:
    f_id
    f_kickoff
    f_gameweek_id
    f_home_team_id
    f_away_team_id

team_fixture_stats:
    (tfs_fixture_id, tfs_team_id)
    (tfs_team_id, tfs_fixture_id)

player_fixture_stats:
    (pfs_fixture_id, pfs_player_id)
    (pfs_player_id, pfs_fixture_id)
    (pfs_team_id, pfs_fixture_id)

events:
    e_fixture_id
    e_player_id
    e_team_id
```

Index for actual access patterns rather than theoretical completeness.


---

## 29. Partitioning

Do not prematurely partition tables.

Premier League aggregate tables remain small by modern database standards even across many seasons.

Event-level data may grow substantially, but partitioning should be introduced only when actual performance measurements justify it.


---

## 30. JSON Usage

JSON is suitable for irregular provider-specific metadata.

Good use case:

```text
event qualifiers
```

Poor use case:

```text
core player statistics
```

Canonical modelable statistics should generally be explicit columns.

The canonical warehouse should not become a collection of JSON blobs simply because source APIs use JSON.


---

## 31. Schema Evolution

Adding a new canonical metric should be straightforward.

Example:

```text
pfs_progressive_passes
```

The expected process should be:

```text
source ingestion
    ↓
staging mapping
    ↓
metric registry
    ↓
reconciliation rule
    ↓
new canonical column
    ↓
rebuild downstream
```

If adding one metric requires redesigning multiple unrelated tables, the schema is too tightly coupled.


---

## 32. Current Core Schema Sketch

```text
competitions
------------
c_id
c_name
...

competition_seasons
-------------------
cs_id
cs_competition_id
cs_start_year
cs_end_year
...

gameweeks
---------
gw_id
gw_competition_season_id
gw_number
gw_deadline
...

teams
-----
t_id
t_name
...

players
-------
p_id
p_name
...

fixtures
--------
f_id
f_competition_season_id
f_gameweek_id
f_home_team_id
f_away_team_id
f_kickoff
f_status
f_venue_id
f_referee_id
f_home_goals
f_away_goals
...

fixture_squads
--------------
fs_fixture_id
fs_player_id
fs_team_id
fs_selection_status
...

team_fixture_stats
------------------
tfs_fixture_id
tfs_team_id
tfs_goals
tfs_shots
tfs_shots_on_target
tfs_xg
tfs_possession
tfs_passes_attempted
tfs_passes_completed
...
PK (tfs_fixture_id, tfs_team_id)

player_fixture_stats
--------------------
pfs_fixture_id
pfs_player_id
pfs_team_id
pfs_started
pfs_minutes
pfs_goals
pfs_assists
pfs_shots
pfs_shots_on_target
pfs_xg
pfs_xa
pfs_passes_attempted
pfs_passes_completed
...
PK (pfs_fixture_id, pfs_player_id)

events
------
e_id
e_fixture_id
e_team_id
e_player_id
e_event_type
e_period
e_match_second
e_x
e_y
e_end_x
e_end_y
...

pass_events
-----------
pe_event_id
pe_recipient_player_id
pe_successful
...

shot_events
-----------
se_event_id
se_xg
se_result
...
```


---

## 33. Guiding Rules

The schema should follow these rules:

1. **Define the grain of every table explicitly.**
2. **Do not split same-grain data merely because a table is wide.**
3. **Split when the grain or semantic entity changes.**
4. **Use wide canonical player- and team-fixture tables.**
5. **Use event tables for genuinely repeated event-level data.**
6. **Keep provider-specific naming upstream.**
7. **Use short, consistent table prefixes for columns.**
8. **Preserve NULL vs zero semantics.**
9. **Keep canonical units consistent.**
10. **Store raw facts canonically and derive convenient interpretations downstream.**
11. **Allow controlled denormalisation where it materially improves usability.**
12. **Ensure all duplication can be regenerated and validated.**
13. **Keep canonical values source-agnostic after reconciliation.**
14. **Do not prematurely optimise through partitioning or table fragmentation.**
15. **Design schema evolution so new metrics are easy to add.**


---

## 34. Next Schema Topics

The next useful schema discussions are likely:

### Player / squad structure

How to represent:

- player master records
- club membership
- transfers
- registration periods
- FPL positions
- nominal positions
- actual match roles

### Fixture squad / appearance logic

How to represent:

- starters
- substitutes
- unused substitutes
- substitutions
- minutes
- positional changes

### Event model

Decide whether to use:

```text
events + subtype tables
```

or specialist event tables directly.

### Gameweek history

Decide how much temporal history is required for:

- fixture moves
- deadline changes
- postponed games
- double / blank gameweeks

### Canonical metric list

Define the first full set of fields for:

```text
team_fixture_stats
player_fixture_stats
```

That will likely be the next major schema-design exercise.
