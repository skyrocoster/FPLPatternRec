# 03 — Pipeline and Runbook

## 1. Purpose

This document defines how data moves through the Premier League / FPL project.

It is intentionally operational rather than football-specific.

The goal is to establish:

- processing order
- responsibilities of each stage
- rebuild behaviour
- failure handling
- what can be safely overwritten
- what should be treated as canonical
- where validation occurs

The pipeline should remain simple enough to change rapidly during early development.


---

## 2. Pipeline Overview

```text
COLLECT
  ↓
RAW
  ↓
STAGING
  ↓
ENTITY RESOLUTION
  ↓
RECONCILIATION
  ↓
CANONICAL
  ↓
VALIDATION
  ↓
ANALYTICAL
  ↓
FEATURE BUILD
  ↓
TRAINING / PREDICTION INPUT
```

Each stage should have one clear responsibility.

Do not allow later stages to compensate silently for errors introduced earlier.


---

## 3. General Principle

The project should favour:

```text
simple
rebuildable
replaceable
script-driven
```

over:

```text
heavily versioned
over-audited
enterprise-style process
```

during early development.

The system should become more historical and more controlled only where the data or modelling process actually requires it.


---

## 4. Collection

Collection means:

> Retrieve source data and write it to raw storage with minimal interpretation.

Collector responsibilities:

```text
request source
capture response
capture retrieval timestamp
capture source identifier
capture endpoint / page where useful
write raw payload
log success or failure
```

Collectors should not:

```text
match players
match teams
match fixtures
rename canonical metrics
reconcile sources
derive modelling features
```

Collection and interpretation should remain separate.


---

## 5. Raw Storage

### 5.1 Early-stage rule

Raw data is **replaceable** during development.

A bad or incomplete scrape should normally be overwritten.

Example:

```text
raw/
  fotmob/
    fixture_12345.json
```

If that scrape is wrong:

```text
re-scrape fixture_12345
overwrite fixture_12345.json
```

No additional version is required by default.

This keeps iteration fast and avoids unnecessary storage and operational overhead.


### 5.2 When history becomes useful

Historical raw snapshots should be introduced only where there is a demonstrated reason.

Examples:

- pre-deadline FPL snapshots
- injury-status snapshots
- fixture schedule changes relevant to historical prediction
- source data known to change retrospectively
- stable production data where auditability becomes useful

Possible structure later:

```text
raw/current/
raw/snapshots/
```

This is not required for the initial pipeline.


---

## 6. Staging

Staging converts raw source payloads into queryable source-specific structures.

Examples:

```text
stg_fotmob_fixture
stg_fotmob_player_fixture
stg_whoscored_event
stg_sofascore_player_fixture
stg_understat_shot
```

Staging responsibilities:

```text
extract JSON / HTML structures
parse fields
convert obvious types
parse timestamps
retain source IDs
retain source-specific terminology
standardise mechanical formatting
```

Staging should remain close enough to the source that debugging is straightforward.

Do not reconcile provider meanings here.


---

## 7. Entity Resolution

Entity resolution maps source identities onto canonical project identities.

Examples:

```text
FotMob player ID    → p_id
Sofascore team ID   → t_id
WhoScored fixture   → f_id
Understat fixture   → f_id
```

Entities likely to require resolution:

```text
players
teams
fixtures
competitions
seasons
```

Resolution behaviour should be:

```text
known mapping
    → use mapping

deterministic high-confidence match
    → create mapping

ambiguous match
    → unresolved / manual review
```

Do not guess silently.

A small number of unresolved records should not necessarily prevent unrelated records from progressing.


---

## 8. Reconciliation

Reconciliation combines compatible values from multiple providers into canonical values.

The pipeline mechanism should be generic:

```text
load eligible source values
    ↓
apply configured reconciliation rule
    ↓
produce canonical value
    ↓
record reconciliation result where useful
```

The specific reconciliation rule for each metric will be defined later after the datasets are understood.

Possible future rule types include:

```text
preferred source
fallback source
majority
median
weighted median
outlier removal
```

The runbook should define the process, not assume the final rules.


---

## 9. Canonical Build

Canonical tables are project-owned representations of football data.

Examples:

```text
players
teams
fixtures
team_fixture_stats
player_fixture_stats
```

Canonical data should be:

- source-agnostic
- entity-resolved
- reconciled
- consistently named
- consistently typed
- reproducible from upstream layers

### Core rule

> Do not manually repair canonical data if the underlying problem is upstream.

Examples:

Wrong player mapping:

```text
fix entity resolution
rebuild
```

Wrong parsed value:

```text
fix staging parser
rebuild
```

Wrong agreed metric:

```text
fix reconciliation rule
rebuild
```

The canonical layer should be treated as generated output.


---

## 10. Validation

Validation occurs after the canonical build and before downstream analytical or modelling use.

Initial validation can remain structural.

Examples:

```text
PK uniqueness
FK integrity
required columns present
expected data types
no duplicate table grain
known entity mappings
no parser failures affecting required records
```

Football-specific validation rules can be added after actual datasets are understood.

Examples to add later may include:

```text
shots_on_target <= shots
passes_completed <= passes_attempted
```

but these should not be invented before the data semantics are verified.


---

## 11. Analytical Layer

Analytical tables or views are disposable outputs built from canonical data.

Examples may eventually include:

```text
player_fixture_analysis
team_fixture_analysis
player_gameweek_analysis
team_gameweek_analysis
```

Analytical structures may contain:

- opponent IDs
- home / away flags
- per-90 values
- ratios
- rolling values
- convenience fields

These should not become the source of truth.

They should always be rebuildable from canonical data.


---

## 12. Feature Build

The feature layer sits downstream of analytical and canonical data.

A feature build should eventually accept explicit inputs such as:

```text
cutoff timestamp
feature version
dataset / reconciliation version
```

Example concept:

```python
build_features(
    cutoff=...,
    feature_version=...
)
```

The feature layer should not alter canonical data.


---

## 13. Run Types

The pipeline should support a small number of practical run modes.

### Incremental collection

Collect and process newly available data.

```text
new fixtures
new player data
updated source responses
```

### Fixture rebuild

Reprocess one fixture from existing raw data.

```text
raw
→ staging
→ resolution
→ reconciliation
→ canonical
```

Useful during parser development.

### Source rebuild

Reparse one source after scraper or parser changes.

Example:

```text
rebuild all FotMob staging data
```

### Canonical rebuild

Recreate canonical tables from existing staging data.

Useful after:

```text
entity mapping changes
reconciliation changes
schema changes
```

### Full rebuild

Recreate the complete derived pipeline from available raw data.

```text
raw
→ staging
→ canonical
→ downstream
```

### Historical backfill

Collect and process prior fixtures or seasons.

This should use the same pipeline as current data wherever possible.


---

## 14. Idempotency

Pipeline stages should be safely rerunnable.

The target behaviour is:

```text
same input
+ same code
+ same configuration
=
same output
```

Examples:

```text
process_fixture(123)
```

should not create duplicate fixture or player-stat rows when rerun.

Use deterministic keys and upserts where appropriate.


---

## 15. Failure Handling

Keep failure handling simple.

Useful categories:

### Retryable failure

Examples:

```text
network error
timeout
temporary source failure
```

Action:

```text
retry later
```

### Parsing / source failure

Examples:

```text
unexpected response
schema changed
required section missing
```

Action:

```text
log
fix parser or collector
rerun
```

### Entity-resolution failure

Examples:

```text
ambiguous player
unknown team
fixture cannot be matched
```

Action:

```text
store unresolved record
resolve mapping
rerun affected stage
```

There is no requirement for elaborate workflow infrastructure in the initial version.


---

## 16. Unresolved Records

A lightweight unresolved table is sufficient initially.

Example:

```text
unresolved_entities
-------------------
ue_id
ue_entity_type
ue_source
ue_source_id
ue_source_name
ue_context
ue_created_at
ue_resolved_at
```

This should be enough to support manual review without creating a full quarantine subsystem.

If operational complexity later justifies something more elaborate, it can be added then.


---

## 17. Logging

Initial logging should answer:

```text
what ran?
when?
did it succeed?
how many records were processed?
what failed?
```

A file log or simple database run table is sufficient.

Possible later table:

```text
pipeline_runs
-------------
pr_id
pr_run_type
pr_started_at
pr_completed_at
pr_status
pr_rows_processed
pr_error_count
```

Do not create excessive run metadata unless it becomes useful.


---

## 18. Versioning

Version only the things whose behaviour can materially alter downstream outputs.

Likely useful concepts:

```text
schema version
reconciliation version
feature version
code commit / release
```

These can initially live in configuration or deployment metadata.

There is no requirement to stamp every row with every version.


---

## 19. Rebuild Philosophy

The architecture should assume that downstream layers will be rebuilt frequently during development.

Expected workflow:

```text
change parser
→ rebuild staging

change player mapping
→ rebuild affected canonical records

change reconciliation
→ rebuild canonical

change feature logic
→ rebuild feature dataset
```

The cost of rebuilding should remain low enough that fixing the source of an error is easier than patching the output manually.


---

## 20. Early Development Philosophy

During the first phase of the project:

Prefer:

```text
overwrite
rerun
rebuild
inspect
adjust
```

Avoid introducing complexity purely for theoretical future audit requirements.

History should be preserved where it has a real analytical purpose, not by default.


---

## 21. Target Pipeline Shape

```text
SOURCE
  ↓
COLLECTOR
  ↓
RAW FILE / PAYLOAD
  ↓
SOURCE-SPECIFIC STAGING
  ↓
ENTITY RESOLUTION
  ↓
RECONCILIATION
  ↓
CANONICAL TABLES
  ↓
STRUCTURAL VALIDATION
  ↓
ANALYTICAL TABLES / VIEWS
  ↓
FEATURE BUILD
  ↓
TRAINING / PREDICTION DATA
```

The important property is that every downstream layer can be regenerated from earlier layers plus code/configuration.


---

## 22. Guiding Rules

1. Keep collection separate from interpretation.
2. Raw data may be overwritten during active development.
3. Introduce historical raw snapshots only where they have demonstrated value.
4. Keep staging source-specific.
5. Resolve identities before canonicalisation.
6. Reconcile source disagreements before canonical tables.
7. Treat canonical data as generated output.
8. Fix errors at the earliest responsible layer.
9. Make stages idempotent where practical.
10. Keep failure handling simple initially.
11. Keep validation structural until the actual data semantics are known.
12. Make downstream layers disposable and rebuildable.
13. Add operational complexity only when the project actually needs it.
