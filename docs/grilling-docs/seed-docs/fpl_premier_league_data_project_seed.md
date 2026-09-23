# Premier League / FPL Predictive Data Project — Planning Seed

## 1. Project Goal

Build a free, reproducible Premier League data pipeline that supplements the official FPL API with as much useful raw player- and team-level football data as practical.

The immediate objective is **data collection and normalisation**, not analysis.

The longer-term objective is to derive a **predictive model for FPL** from the resulting dataset.

Key principles:

- No paid data sources.
- Scraping is acceptable.
- Prefer raw numbers and event data over ratings, opinions, or pre-analysed metrics.
- Retain raw source data so downstream datasets can always be rebuilt.
- Resolve source disagreements before they reach modelling tables.
- Keep modelling features point-in-time safe to prevent leakage.


---

## 2. Proposed Free Data Sources

The FPL API is assumed to already be available and is therefore not treated as a supplementary source below.

### 2.1 WhoScored

**Primary use:** event-level match data.

Potentially the most valuable supplementary source because it can expose individual match events rather than only aggregates.

Useful fields include:

- event type
- player
- team
- minute / second
- period
- outcome
- x / y start coordinates
- x / y end coordinates
- qualifiers
- touches
- shots
- goals
- passes
- tackles
- dribbles
- defensive actions

This makes it possible to derive counts such as passes from the underlying events instead of relying only on provider aggregates.

Preferred role:

> Core event dataset.

---

### 2.2 FotMob

**Primary use:** player-match and team-match box scores, shot maps, supplementary passing and possession statistics.

Potential fields include:

- minutes
- goals
- assists
- shots
- shots on target
- xG
- xA
- passes
- accurate passes
- pass accuracy
- key passes
- long balls
- accurate long balls
- crosses
- touches
- touches in opposition box
- dribbles
- successful dribbles
- duels
- duels won
- aerial duels
- tackles
- interceptions
- clearances
- recoveries
- possession lost
- fouls
- saves

Preferred role:

> Core player-match / team-match dataset and shot-map source.

Because the API is undocumented, raw responses should be archived.

---

### 2.3 Sofascore

**Primary use:** second player-match and team-match source.

Potential fields include:

- passes
- successful passes
- key passes
- long balls
- crosses
- shots
- blocked shots
- tackles
- interceptions
- clearances
- ground duels
- aerial duels
- dribbles
- fouls
- possession lost
- lineups
- incidents
- substitutions

Preferred role:

> Secondary box-score source and gap-filler.

It is particularly useful for cross-source reconciliation.

---

### 2.4 Understat

**Primary use:** shot-level expected-goal data and attacking metrics.

Useful player-level fields include:

- games
- minutes
- goals
- xG
- assists
- xA
- shots
- key passes
- non-penalty goals
- non-penalty xG
- xGChain
- xGBuildup

Useful shot-level fields include:

- player
- minute
- x
- y
- xG
- result
- situation
- shot type
- assisting / key-pass player
- home / away
- match

Preferred role:

> Shot-level xG layer.

---

### 2.5 PremierLeague.com Stats Centre

**Primary use:** official league totals and validation.

Useful categories may include:

- total passes
- goals
- assists
- saves
- clean sheets
- tackles
- interceptions
- clearances
- recoveries
- duels
- aerials
- crosses
- through balls
- long balls

Preferred role:

> Authoritative reconciliation / validation source.

This is especially useful for checking whether derived totals from event feeds align with official league totals.

---

### 2.6 Football-Data.co.uk

**Primary use:** simple historical team-match layer.

Typical fields include:

- date
- home team
- away team
- full-time goals
- half-time goals
- shots
- shots on target
- fouls
- corners
- yellow cards
- red cards
- bookmaker odds

Preferred role:

> Historical match-level dataset.

It is not a strong player-level source, but it is cheap to ingest and useful historically.

---

### 2.7 Transfermarkt

**Primary use:** player availability and squad context.

Useful data includes:

- injuries
- suspensions
- squads
- transfers
- player positions
- appearances
- dates / durations of absences

Preferred role:

> Availability and player-context layer.

---

### 2.8 ClubElo

**Primary use:** historical team-strength ratings.

Preferred role:

> Team strength context.

---

## 3. Sources Not to Make Core Dependencies

### FBref

FBref should not be treated as the current-season advanced-stat source it once was.

The loss of its advanced data feed in 2026 means many formerly useful current-season advanced fields are no longer reliably populated.

It may still be useful historically or for selected basic tables, but it should not be a core dependency for this project.

---

## 4. Identity Resolution

Names should be treated as **matching inputs**, not identifiers.

The key entity-resolution problems are:

- player matching
- team matching
- match matching

### 4.1 Player Name Matching

The practical strategy should be:

1. Resolve teams first.
2. Match players within team + season / match context.
3. Normalise Unicode, accents, punctuation, spacing, and abbreviations.
4. Generate multiple comparable name forms.
5. Apply deterministic matching rules first.
6. Use fuzzy matching only for unresolved cases.
7. Use DOB / nationality as tie-breakers.
8. Persist manual aliases and exceptions.

Examples of name differences:

- `João Pedro` vs `Joao Pedro`
- `M. Salah` vs `Mohamed Salah`
- `Gabriel` vs `Gabriel Magalhães`
- `T. Alexander-Arnold` vs `Trent Alexander Arnold`

Useful comparison features include:

- cleaned full name
- token set
- meaningful token set
- first token
- last token
- first initial
- surname
- token containment
- team
- DOB
- nationality

Do not fuzzily compare a player against the entire league if team context is known.

### 4.2 Matching Method

A useful approach is to perform **team-constrained bipartite matching**.

For each team, generate a similarity matrix between Source A and Source B player names, then solve the assignment problem globally rather than selecting each closest name independently.

This prevents two source records being assigned to the same player.

Use deterministic matching first:

- exact cleaned name
- exact first + last
- surname + first initial
- one token set contained within another
- abbreviation compatibility

Then use fuzzy scores such as:

- token-set similarity
- weighted ratio

Manual exceptions should be expected, but the exception set should become small after initial bootstrapping.

---

## 5. Match Resolution

Build a cross-source match map early.

A match may have different IDs across:

- FPL
- WhoScored
- FotMob
- Sofascore
- Understat

Bootstrap matching using:

- home team
- away team
- competition
- season
- kickoff timestamp

Be careful with:

- postponements
- rescheduled fixtures
- timezone conversion

Once matched, downstream data should refer to the project’s canonical match identity.

---

## 6. Data Architecture

Recommended flow:

```text
RAW
  ↓
STAGING / FIRST PASS
  ↓
RECONCILIATION / NORMALISATION
  ↓
CANONICAL FACTS
  ↓
ANALYTICAL FACTS
  ↓
FEATURE LAYER
  ↓
TRAINING SNAPSHOTS
  ↓
MODELS / PREDICTIONS / BACKTESTS
```

---

## 7. Raw Layer

The raw layer should contain the untouched responses from each source.

Examples:

```text
raw/
    fotmob/
    whoscored/
    sofascore/
    understat/
    premierleague/
    transfermarkt/
```

Store:

- original JSON / HTML
- source
- source endpoint / URL where useful
- scrape timestamp
- HTTP / retrieval metadata
- parser version if applicable

Raw data should be treated as immutable.

The purpose is to allow all downstream tables to be rebuilt without re-scraping.

---

## 8. Staging / First-Pass Layer

The staging layer should mirror each source fairly closely.

Examples:

```text
stg_fotmob_player_match
stg_fotmob_shots
stg_whoscored_events
stg_whoscored_lineups
stg_sofascore_player_match
stg_understat_shots
```

Only minimal transformation should happen here:

- type coercion
- null handling
- timestamp parsing
- extraction from nested JSON
- source identifiers retained
- source field names retained or mapped transparently

This layer should preserve source-specific values.

---

## 9. Reconciliation / Normalisation Layer

This is a critical layer.

The downstream model should not generally see five competing values for the same metric.

Example source disagreement:

```text
WhoScored passes = 63
FotMob passes    = 61
Sofascore passes = 62
```

The reconciliation layer should produce one canonical value according to scripted rules.

Possible result:

```text
canonical passes = 62
```

The source-specific values remain available upstream in staging.

### 9.1 Reconciliation Should Be Metric-Specific

Do not use one rule for all metrics.

Example configuration:

```yaml
passes:
  sources:
    - whoscored
    - fotmob
    - sofascore
  method: median
  cast: integer
  disagreement_tolerance: 3

shots:
  sources:
    - understat
    - whoscored
    - fotmob
  method: majority

xg:
  preferred_source: understat
  fallback:
    - fotmob

minutes:
  preferred_source: fpl
  fallback:
    - premierleague
    - fotmob
```

This logic should live in configuration / code and be version controlled.

Changing reconciliation rules should allow the canonical dataset to be rebuilt.

---

## 10. Three Types of Source Disagreement

### 10.1 Minor Recording Differences

Example:

```text
WS = 63
FM = 62
SS = 62
```

Use:

- majority
- median
- weighted median

For discrete counts, avoid arithmetic averages that create impossible values such as 62.5 passes.

---

### 10.2 Consistently Noisy Sources

Measure source reliability per metric.

Example:

```text
source_metric_quality
---------------------
source
metric
observations
mean_abs_error
median_abs_error
bias
exact_match_rate
within_1_rate
within_5pct_rate
```

The important unit is:

> source + metric

not simply:

> source

A provider may be excellent for one statistic and noisy for another.

Eventually, source weights can be learned empirically.

---

### 10.3 Different Definitions

This is the most dangerous case.

Two fields that look similar may not be semantically compatible.

Examples:

- passes attempted
- completed passes
- passes excluding crosses
- recoveries
- possession won
- possession lost
- chances created
- key passes

If provider definitions differ, the metrics must remain separate.

Do not reconcile semantically different fields simply because their labels look similar.

---

## 11. Metric Registry

Maintain a metric registry.

Example:

```text
metric
source
source_field
level
definition
unit
nullable
compatible_with_canonical
first_seen
last_seen
```

This answers questions such as:

> Does FotMob `totalPass` mean the same thing as WhoScored pass events?

The metric registry should become the project’s reference for provider semantics.

---

## 12. Canonical Facts Layer

The canonical layer should contain one clean value for each accepted metric.

Prefer wide football tables over an EAV-style design for modelling.

Example:

```text
player_match
------------
player_id
match_id
team_id
minutes
passes
passes_completed
shots
shots_on_target
xg
xa
touches
touches_box
tackles
interceptions
clearances
duels
duels_won
...
```

Equivalent team-level tables should exist.

The canonical layer should not contain duplicated source rows for ordinary downstream use.

---

## 13. Reconciliation Audit Log

Keep source disagreement information outside the main fact tables.

Example:

```text
reconciliation_log
------------------
match_id
player_id
metric
canonical_value
method
sources_used
max_disagreement
rule_version
```

This allows questions such as:

> Why does the canonical table say this player had 47 passes?

to be answered without polluting the modelling schema.

---

## 14. Reconciliation Versioning

Version the reconciliation logic.

Example:

```text
reconciliation_version = 1
```

Later:

```text
reconciliation_version = 2
```

A change such as:

> Ignore Sofascore tackles before a particular date because the definition appears inconsistent.

should be implemented in version-controlled configuration and then propagated by rebuilding downstream layers.

---

## 15. Coordinate Normalisation

Different providers may use different pitch coordinate systems.

Possible formats include:

- 0–1
- 0–100
- physical pitch dimensions

Also consider direction of play.

Keep:

- raw x
- raw y
- raw provider orientation
- canonical x
- canonical y

Choose one canonical convention, for example:

```text
x: 0–100
y: 0–100
always attacking left → right
```

Do not discard raw coordinates.

---

## 16. Time Normalisation

Match timing is more complicated than a simple minute number.

Keep:

- period
- provider minute
- provider second
- stoppage-time representation
- canonical elapsed seconds

Be careful with:

- `45+X`
- `90+X`
- substitutions
- extra time if the project expands beyond league fixtures

Do not assume providers calculate minutes played identically.

---

## 17. Lineups and Appearances

Do not derive the player-match universe only from event rows.

A player can play but generate no meaningful events.

Use:

- starting lineups
- substitute benches
- substitutions
- appearance records

as the basis for player-match participation.

Events then attach to that universe.

---

## 18. Data Quality Checks

Automated checks should exist between staging, reconciliation, and canonical outputs.

Examples:

```text
starting XI count ~= 11
completed passes <= attempted passes
shots on target <= shots
duels won <= duels
home goal event count ~= final home score
away goal event count ~= final away score
player shots sum ~= team shots
all player IDs resolve
all team IDs resolve
all match IDs resolve
```

Cross-source disagreements should be flagged, not silently hidden.

---

## 19. Idempotent Ingestion

Collection scripts should be safely repeatable.

Conceptually:

```text
ingest_match(match_id)
```

should produce the same stored state whether run once or twenty times.

Use deterministic keys and upserts where appropriate.

---

## 20. Schema Drift

Undocumented APIs will change.

Track:

- field names
- field types
- missing fields
- new fields
- nested structure changes

A scraper returning HTTP 200 with half the expected fields missing can be more dangerous than one crashing outright.

Add automated schema-drift checks.

---

## 21. Raw Event Qualifiers

Do not flatten away provider-specific event metadata.

For WhoScored-style events, retain the raw qualifier JSON even if selected fields are extracted into explicit columns.

Example extracted fields:

- cross
- through ball
- set piece
- assist
- key pass
- body part
- long ball

Future features may depend on metadata that is not initially considered important.

---

## 22. Historical Team Membership

Do not use current squad membership to resolve historical records.

Player → team affiliation must be fixture-aware.

For match facts, store:

```text
match_id
player_id
team_id
```

This naturally handles transfers.

---

## 23. Competition and Season Dimensions

Even if the first version is Premier-League-only, competition and season should be real dimensions.

Likely future extensions include:

- FA Cup
- EFL Cup
- Champions League
- Europa League
- Conference League
- promoted / relegated club history

This will matter for:

- total minutes
- rotation
- injuries
- fixture congestion
- player form
- team form

---

## 24. Analytical Facts Layer

The analytical layer should contain stable, reusable football concepts.

Examples:

```text
player_match_facts
player_gameweek_facts
team_match_facts
opponent_match_facts
```

Possible values:

- passes_attempted
- passes_completed
- shots
- shots_on_target
- xG
- xA
- touches
- touches_box
- duels
- duels_won
- minutes
- team possession
- team xG
- opponent xG

Derived but still broadly reusable metrics may include:

- passes per 90
- shots per 90
- xG per 90
- xA per 90
- share of team shots
- share of team xG
- touches in box per 90

The analytical layer should not yet be tied to a specific model.

---

## 25. Feature Layer

The feature layer is model-specific.

Examples:

- rolling 3 xG
- rolling 6 xG
- exponentially weighted shots
- last 5 match minutes
- opponent rolling xGA
- home / away flag
- rest days
- predicted starting probability
- recent set-piece share
- team attacking strength
- opponent defensive strength

These can change frequently as modelling ideas evolve.

That is why the feature layer should remain separate from analytical facts.

---

## 26. Point-in-Time Correctness

This is one of the most important modelling safeguards.

Every model feature must answer:

> What information was actually available at prediction time?

If predicting Gameweek 12, the feature set must not include:

- GW12 match results
- later injury news
- later lineup information
- revised statistics published after the cutoff
- future transfers
- retrospective corrections not yet available at prediction time

Useful timestamps include:

- event_time
- published_at
- scraped_at
- effective_from

Feature generation should accept an explicit cutoff.

Example:

```python
build_features(
    gameweek=12,
    cutoff="2026-11-06 18:30"
)
```

---

## 27. Latest vs Historical Snapshots

Maintain separate concepts of:

```text
latest/
historical_snapshots/
```

`latest` is useful for exploration and live predictions.

`historical_snapshots` are used for model training and backtesting.

This prevents later upstream corrections from silently changing historical training rows.

---

## 28. Training Datasets

Training datasets should be frozen outputs of:

```text
canonical
  ↓
analytical
  ↓
features
  ↓
training snapshot
```

A training snapshot should record:

- feature-generation version
- reconciliation version
- cutoff timestamp
- target definition
- feature list
- source-data snapshot / version where practical

This makes model experiments reproducible.

---

## 29. Targets

Keep model targets separate from features.

Potential FPL targets include:

- FPL points
- minutes
- starts
- goals
- assists
- clean-sheet points
- bonus points
- saves
- yellow / red cards

It may be useful to model some components separately rather than modelling total FPL points directly.

---

## 30. Suggested Initial Build Order

### Phase 1 — Identity

Build:

- canonical teams
- team source mappings
- canonical players
- player source mappings
- player name matcher
- match source mappings

Do this before ingesting large amounts of historical data.

### Phase 2 — Raw Collection

Build collectors for:

1. WhoScored
2. FotMob
3. Understat
4. Sofascore
5. PremierLeague.com

Then add:

- Football-Data.co.uk
- Transfermarkt
- ClubElo

Archive all raw payloads.

### Phase 3 — Staging

Create source-shaped staging tables.

Do not aggressively normalise at this stage.

### Phase 4 — Metric Registry

Document each useful provider field and map it to candidate canonical metrics.

### Phase 5 — Reconciliation Engine

Implement:

- definition compatibility rules
- source priority rules
- median / majority rules
- outlier detection
- source-metric quality scoring
- reconciliation logs
- rule versioning

### Phase 6 — Canonical Tables

Produce one clean player-match and team-match dataset.

### Phase 7 — Analytical Facts

Create reusable football metrics.

### Phase 8 — Feature Layer

Build point-in-time-safe modelling variables.

### Phase 9 — Training / Backtesting

Freeze historical feature snapshots and evaluate predictive models.

---

## 31. Core Design Principles

The project should follow these rules:

1. **Raw data is immutable.**
2. **Staging preserves source-specific truth.**
3. **Player, team, and match identity are resolved early.**
4. **Metrics are reconciled before entering canonical tables.**
5. **Provider definitions are not assumed to be equivalent.**
6. **Source reliability is evaluated per metric.**
7. **Canonical tables contain one agreed value where possible.**
8. **Reconciliation remains fully reproducible from scripts/config.**
9. **Audit metadata is retained outside modelling tables.**
10. **Analytical facts are separate from model features.**
11. **Features are point-in-time correct.**
12. **Training datasets are frozen and reproducible.**
13. **Raw provider-specific metadata is never discarded unnecessarily.**
14. **All downstream layers should be rebuildable from raw + code.**

---

## 32. High-Level Target Architecture

```text
                    ┌─────────────────────────┐
                    │       DATA SOURCES      │
                    │                         │
                    │ FPL / WhoScored         │
                    │ FotMob / Sofascore      │
                    │ Understat / PL.com      │
                    │ Transfermarkt / etc.    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │          RAW            │
                    │ immutable payloads      │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        STAGING          │
                    │ source-shaped tables    │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   IDENTITY RESOLUTION   │
                    │ player/team/match maps  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     RECONCILIATION      │
                    │ metric rules / QA       │
                    │ source weighting        │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        CANONICAL        │
                    │ agreed football facts   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      ANALYTICAL         │
                    │ reusable derived stats  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │        FEATURES         │
                    │ point-in-time model vars│
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   TRAINING SNAPSHOTS    │
                    │ frozen X / y datasets   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ MODELS / BACKTESTS /    │
                    │      PREDICTIONS        │
                    └─────────────────────────┘
```

---

## 33. Immediate Next Planning Tasks

The most useful next design work is likely:

1. Define the canonical match, player, and team entities.
2. Build the source-to-canonical entity matching process.
3. Enumerate all fields available from each source.
4. Build the metric registry.
5. Decide the first-pass canonical `player_match` and `team_match` schemas.
6. Define reconciliation rules for the first 20–30 core metrics.
7. Implement one end-to-end match ingestion as a vertical slice.
8. Only then scale the collectors across the season / history.

A good first vertical slice would ingest a single Premier League match from:

- FPL
- WhoScored
- FotMob
- Sofascore
- Understat

and produce:

```text
raw payloads
    ↓
staging tables
    ↓
resolved players / teams / match
    ↓
reconciled canonical player_match
    ↓
reconciled canonical team_match
```

If that process is robust, scaling it across the league becomes a much simpler engineering problem.
