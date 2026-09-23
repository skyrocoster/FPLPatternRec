# 04 — Project Conventions

## 1. Purpose

This document defines project-wide engineering conventions that can be agreed before the datasets are fully understood.

The aim is consistency.

These conventions should make the project easier to:

- read
- query
- rebuild
- extend
- debug
- automate

They are intentionally independent of specific football metrics.


---

## 2. Naming Philosophy

Names should be:

- explicit
- consistent
- short enough to remain readable
- predictable from the table or object they belong to

The agreed database convention is:

> Prefix columns with a short table-specific prefix.

Examples:

```text
players               -> p_
teams                 -> t_
fixtures              -> f_
player_fixture_stats  -> pfs_
team_fixture_stats    -> tfs_
gameweeks             -> gw_
competitions          -> c_
competition_seasons   -> cs_
fixture_squads        -> fs_
events                -> e_
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
```

This convention should be applied consistently.


---

## 3. Table Naming

Use:

```text
snake_case
lowercase
```

Examples:

```text
players
teams
fixtures
player_fixture_stats
team_fixture_stats
competition_seasons
```

Prefer descriptive table names over abbreviating the table itself.

The abbreviation belongs in the column prefix.


---

## 4. Primary Keys

Primary keys should use the table prefix.

Examples:

```text
players.p_id
teams.t_id
fixtures.f_id
competitions.c_id
gameweeks.gw_id
```

For naturally composite fact tables, a synthetic key is optional.

Example:

```text
player_fixture_stats
PRIMARY KEY (pfs_fixture_id, pfs_player_id)
```

Example:

```text
team_fixture_stats
PRIMARY KEY (tfs_fixture_id, tfs_team_id)
```

Do not add synthetic keys merely because every table is expected to have one.


---

## 5. Foreign Keys

Foreign-key names should use the prefix of the table containing the column.

Examples:

```text
fixtures.f_home_team_id
fixtures.f_away_team_id

player_fixture_stats.pfs_player_id
player_fixture_stats.pfs_fixture_id
player_fixture_stats.pfs_team_id
```

The referenced entity is clear from the remainder of the name.


---

## 6. Source IDs

External provider IDs should never replace project-owned canonical IDs.

Where source mappings are stored, use explicit names.

Examples:

```text
ps_source
ps_source_player_id
```

or source-specific staging columns such as:

```text
sfm_player_id
sws_player_id
```

depending on the staging-table naming convention eventually selected.

Canonical tables should use project IDs.


---

## 7. Canonical Metric Names

Provider terminology should not leak directly into canonical schemas.

Source fields such as:

```text
totalPass
accurateLongBalls
wonContest
```

should be translated upstream into project terminology.

Canonical naming should favour forms such as:

```text
passes_attempted
passes_completed
long_balls_attempted
long_balls_completed
dribbles_attempted
dribbles_completed
```

The exact metric set will be defined only after source data is inspected.


---

## 8. Boolean Naming

Use positive boolean names.

Prefer:

```text
pfs_started
f_neutral_venue
```

over:

```text
pfs_not_substitute
f_not_home_venue
```

Avoid encoding multiple meanings into a boolean where a state or lookup would be clearer.


---

## 9. Timestamp Naming

Use explicit suffixes.

Examples:

```text
_created_at
_updated_at
_scraped_at
_kickoff
_deadline
_effective_from
_effective_to
```

Prefer timezone-aware timestamps.

Store timestamps consistently, ideally in UTC at the database layer unless there is a clear reason not to.

Presentation or local-time conversion should happen downstream.


---

## 10. Date Naming

Use `_date` for date-only values.

Examples:

```text
p_date_of_birth
cs_start_date
cs_end_date
```

Do not store date-only values as arbitrary strings.


---

## 11. NULL Semantics

`NULL` and `0` must remain distinct.

Example:

```text
pfs_shots = 0
```

means:

> The player had zero shots.

Example:

```text
pfs_shots = NULL
```

means:

> No accepted value is available.

Do not globally replace missing values with zero.

The meaning of missing data should be decided per field once actual source behaviour is understood.


---

## 12. Units

Canonical units should be selected once and applied consistently.

Likely conventions:

```text
coordinates  -> 0 to 100
distance     -> metres
time         -> seconds where precise duration is required
xG           -> decimal
percentages  -> one consistent scale
```

The precise percentage convention can be chosen when the first canonical metrics are implemented.

Raw provider units remain in staging.


---

## 13. Numeric Types

Avoid premature micro-optimisation of numeric storage.

Prefer sensible types that make transformations safe and obvious.

Examples:

```text
integer counts      -> INTEGER
IDs                 -> BIGINT / INTEGER as appropriate
probabilities / xG  -> DECIMAL or floating type
coordinates         -> DECIMAL / floating type
```

Choose exact precision based on actual source data later.


---

## 14. Strings

Use strings for categorical fields unless there is a strong reason to create a lookup table.

Avoid hard database enums for categories likely to evolve.

Examples:

```text
fixture status
event type
position
injury type
```

can initially be strings or lookup-backed values.

Hard enums can become awkward when providers introduce new values.


---

## 15. Directory Layout

A practical initial project structure could be:

```text
project/
│
├── config/
│
├── data/
│   ├── raw/
│   ├── staging/
│   ├── exports/
│   └── snapshots/
│
├── src/
│   ├── collectors/
│   ├── parsers/
│   ├── entity_resolution/
│   ├── reconciliation/
│   ├── canonical/
│   ├── analytical/
│   └── features/
│
├── sql/
│   ├── schema/
│   ├── views/
│   └── migrations/
│
├── tests/
│
├── docs/
│
└── scripts/
```

This is a starting convention, not a requirement to create every directory immediately.


---

## 16. Raw File Naming

Raw file names should make the source object obvious.

Examples:

```text
fixture_12345.json
player_6789.json
team_123.json
season_2026_27.json
```

Avoid embedding excessive metadata in filenames when it can be determined from directory structure or stored inside the payload.

Prefer predictable paths over clever ones.


---

## 17. Staging Naming

Staging tables should clearly identify the source.

Possible convention:

```text
stg_fotmob_fixture
stg_fotmob_player_fixture
stg_whoscored_event
stg_sofascore_player_fixture
stg_understat_shot
```

Staging column prefixes can be introduced if they remain useful, but the source-specific table name may already provide enough context.

This can be decided once the staging schemas are actually created.


---

## 18. Canonical Naming

Canonical tables should not contain provider names.

Good:

```text
player_fixture_stats
```

Avoid:

```text
combined_fotmob_whoscored_player_stats
```

The canonical layer belongs to the project, not to any provider.


---

## 19. Analytical Naming

Use clear suffixes or namespaces for derived structures.

Examples:

```text
player_fixture_analysis
player_gameweek_analysis
team_fixture_analysis
```

or database schemas such as:

```text
canonical.player_fixture_stats
analysis.player_fixture
features.player_gameweek
```

The exact database namespace strategy can be chosen once the database technology is fixed.


---

## 20. Configuration

Behaviour likely to change without code changes should live in configuration.

Possible examples:

```text
source URLs
enabled collectors
season IDs
competition IDs
reconciliation settings
feature versions
local paths
database connection settings
```

Configuration files should be human-readable.

Likely formats:

```text
YAML
TOML
JSON
```

Do not place secrets in version-controlled configuration.


---

## 21. Secrets

Credentials and tokens should be separated from ordinary project configuration.

Possible approaches:

```text
environment variables
.env for local development
secret manager later if required
```

Never commit secrets to Git.


---

## 22. Logging

Logs should initially be useful rather than exhaustive.

A collector or transformation should normally log:

```text
start
source / operation
record count
success
failure
exception detail
completion
```

Avoid large volumes of debug output by default.

Debug logging can be enabled when developing a source.


---

## 23. Error Messages

Errors should include enough context to reproduce the issue.

Good:

```text
Failed to parse FotMob fixture 12345: expected lineup.players, field missing
```

Bad:

```text
Parsing failed
```

Useful identifiers include:

```text
source
source object ID
canonical ID if known
pipeline stage
```

---

## 24. Code Organisation

Keep provider-specific logic isolated.

Example:

```text
collectors/fotmob.py
parsers/fotmob.py

collectors/whoscored.py
parsers/whoscored.py
```

Canonical transformations should not depend directly on provider response formats.

Provider changes should ideally be contained in:

```text
collector
parser
staging mapping
```

rather than propagating through the entire project.


---

## 25. Functions and Modules

Prefer functions with clear input/output boundaries.

Examples:

```text
collect_fixture(source_fixture_id)
parse_fixture(raw_payload)
resolve_player(source, source_player_id)
build_canonical_fixture(fixture_id)
```

Avoid hidden global state where practical.

Pipeline steps should be callable independently so individual fixtures or stages can be rebuilt.


---

## 26. Idempotency Convention

Any command named:

```text
build
load
process
sync
```

should ideally be safe to rerun.

A rerun should update or reproduce the intended state rather than append duplicates unexpectedly.


---

## 27. Migration Philosophy

Database schema changes should be scripted.

Avoid manually changing production or long-lived development databases without recording the change.

Initially this may simply mean ordered SQL files:

```text
001_initial_schema.sql
002_add_fixture_status.sql
003_add_player_fixture_stats.sql
```

A migration framework can be introduced later if useful.


---

## 28. Schema Versioning

Maintain a simple project schema version.

Example:

```text
schema_version = 4
```

This does not need to appear on every row.

Its main purpose is to identify which code/schema combination produced a database or export.


---

## 29. Code Versioning

Git should be the primary history for:

```text
collectors
parsers
schema
reconciliation logic
feature logic
configuration templates
documentation
```

Commit messages should describe behavioural changes rather than arbitrary file changes where possible.


---

## 30. Reconciliation Versioning

Once reconciliation rules exist, give them an explicit version.

Example:

```text
reconciliation_version = 3
```

A rule change that materially changes canonical data should increment the version.

The exact implementation can remain lightweight.


---

## 31. Feature Versioning

Feature-generation logic should eventually have its own version.

Example:

```text
feature_version = 7
```

This allows training datasets to be tied to the feature-generation logic that created them.

No feature-version implementation is required until modelling begins.


---

## 32. Testing Conventions

Tests should mirror the project layers.

Possible structure:

```text
tests/
  collectors/
  parsers/
  entity_resolution/
  reconciliation/
  canonical/
  integration/
```

Early tests should focus on:

```text
known payload parses correctly
same input produces same output
entity matcher handles known aliases
canonical build does not duplicate grain
```

Football-statistical assertions should be added only after actual source semantics are known.


---

## 33. Test Fixtures

Keep small real or representative source payloads for regression testing.

Example:

```text
tests/fixtures/fotmob_fixture_12345.json
tests/fixtures/whoscored_fixture_67890.html
```

These are test assets, not the same thing as the project's live raw store.

They should be deliberately selected and stable.


---

## 34. Comments and Documentation

Document:

- table grain
- non-obvious field semantics
- reconciliation behaviour
- source quirks
- assumptions that could otherwise be forgotten

Do not document obvious syntax simply for completeness.

The best documentation should explain **why**, not repeat **what** the code already makes clear.


---

## 35. Derived vs Stored Data

The convention should be:

> Store raw or canonical facts when they are stable and useful. Derive convenience values downstream.

Examples:

Store:

```text
goals_for
goals_against
passes_attempted
passes_completed
```

Derive:

```text
goal_difference
pass_completion_rate
```

Controlled denormalisation remains acceptable where it materially improves usability.


---

## 36. Rebuild Convention

Do not hand-edit generated downstream tables.

If generated data is wrong:

```text
identify responsible upstream layer
fix code / mapping / configuration
rebuild
```

This applies to:

```text
staging
canonical
analytical
features
```

where appropriate.


---

## 37. Early Development Bias

During the exploratory phase, favour:

```text
simple scripts
clear SQL
wide tables
replaceable raw data
repeatable rebuilds
small configuration files
```

over:

```text
complex orchestration
microservices
distributed processing
mandatory audit history
premature partitioning
abstract frameworks
```

Complexity should be earned by an actual problem.


---

## 38. Guiding Rules

1. Use `snake_case`.
2. Prefix canonical columns with short table-specific prefixes.
3. Keep table names descriptive.
4. Use project-owned canonical IDs.
5. Keep provider terminology in staging.
6. Keep `NULL` distinct from zero.
7. Standardise units before canonicalisation.
8. Prefer strings / lookup tables over rigid enums where categories may change.
9. Keep provider-specific code isolated.
10. Keep configuration separate from code where behaviour is expected to change.
11. Never commit secrets.
12. Make processing steps rerunnable.
13. Script schema changes.
14. Use Git as the primary code/config history.
15. Keep tests layer-specific.
16. Fix generated data upstream and rebuild.
17. Avoid architectural complexity until a real need appears.
