# 05 — Entity Resolution

## 1. Purpose

This document defines how source-specific identities are mapped onto stable project-owned identities.

The main entities are:

```text
players
teams
fixtures
competitions
seasons
```

The aim is not to make names behave like identifiers.

The aim is to use names and context to establish mappings between source identities and canonical project identities, then persist those mappings so future ingestion does not repeat the same matching work.


---

## 2. Core Principle

The project should use:

> **constraint-based matching first, deterministic matching second, fuzzy matching third, manual resolution last.**

Entity resolution should not be reduced to a single generic similarity score.

Context and contradictions matter.


---

## 3. General Resolution Flow

Conceptually:

```text
source entity
    ↓
existing source-ID mapping?
    ├─ yes → use canonical ID
    └─ no
        ↓
construct contextual candidate set
        ↓
apply hard constraints
        ↓
apply deterministic name rules
        ↓
apply supporting attributes
        ↓
fuzzy ranking if still useful
        ↓
exactly one viable candidate?
        ├─ yes → create mapping
        └─ no  → unresolved
```

The key rule is:

> **No name-based rule should automatically resolve an entity unless exactly one viable candidate remains.**


---

## 4. Source IDs

Source IDs are strong identifiers within their own provider.

Examples:

```text
FotMob player 12345
Sofascore player 67890
WhoScored fixture 456789
```

Once a mapping exists:

```text
source + source_entity_id
→ canonical_id
```

future ingestion should use that mapping directly.

Names should not be rematched unnecessarily.


---

## 5. Source Mapping Tables

Prefer dedicated mapping tables rather than one generic polymorphic entity-mapping table.

Examples:

```text
player_source_map
team_source_map
fixture_source_map
competition_source_map
```

Example:

```text
player_source_map
-----------------
psm_source
psm_source_player_id
psm_player_id
psm_source_name
psm_match_method
psm_manual
```

Example:

```text
fixture_source_map
------------------
fsm_source
fsm_source_fixture_id
fsm_fixture_id
fsm_source_home_team_id
fsm_source_away_team_id
fsm_source_kickoff
fsm_match_method
fsm_manual
```

This is less abstract but allows each entity type to carry useful supporting context.


---

## 6. Player Resolution

Player resolution is expected to be the most difficult part of the identity layer.

The preferred order is:

```text
existing source-ID mapping
↓
construct contextual candidate set
↓
apply hard constraints
↓
apply deterministic name rules
↓
use supporting attributes
↓
fuzzy ranking if necessary
↓
require unique remaining candidate
↓
otherwise unresolved
```


---

## 7. Candidate Set Construction

Do not compare every source player against every player in the database.

Candidate sets should be constrained by context.

Useful context may include:

```text
team
fixture
season
date
competition
squad membership
```

The candidate set should usually be based on:

> team + relevant time window

rather than:

> current team roster

This matters because of:

- transfers
- loans
- academy call-ups
- players leaving mid-season
- historical backfills
- temporary squad membership

Team context narrows the candidate set, but does not itself resolve identity.


---

## 8. The Longstaff Problem

A team can contain multiple players with the same surname.

Example:

```text
Source:
Longstaff

Context:
Newcastle

Candidates:
Sean Longstaff
Matty Longstaff
```

This must resolve to:

```text
AMBIGUOUS
```

not arbitrarily to one player.

Likewise, exact matching against a generated surname alias is not enough if multiple canonical players share that alias.

Example:

```text
"longstaff"
→ Sean Longstaff
→ Matty Longstaff
```

The result remains unresolved until additional evidence distinguishes them.


---

## 9. Name Normalisation

Name normalisation should improve comparison without destroying the original source value.

Useful transformations include:

```text
Unicode normalisation
case folding
accent removal
punctuation normalisation
hyphen normalisation
whitespace collapse
```

Examples:

```text
João Pedro
→ joao pedro

T. Alexander-Arnold
→ t alexander arnold
```

Never overwrite the original source name.

Keep both:

```text
source_name
normalised_name
```


---

## 10. Name Features

Do not rely on one normalised string.

Generate useful comparison features such as:

```text
full_clean_name
token_set
meaningful_token_set
first_name
last_name
first_initial
surname
```

Potential deterministic relationships include:

```text
M. Salah
↔ Mohamed Salah

B. Fernandes
↔ Bruno Fernandes

Martin Ødegaard
↔ Martin Odegaard
```

Token containment may help with longer formal names:

```text
Mohamed Salah
↔ Mohamed Salah Hamed Mahrous Ghaly
```


---

## 11. Deterministic Name Rules

Useful deterministic rules may include:

```text
exact cleaned full name
exact first + last
surname + compatible first initial
one meaningful token set contained within another
known source-scoped alias
```

However, each rule must still end with:

> exactly one viable candidate remains

If more than one candidate matches the rule, the result is ambiguous.


---

## 12. Supporting Attributes

Supporting attributes may include:

```text
date of birth
shirt number
nationality
position
team
fixture squad
season
```

These should be used as constraints and evidence, not thrown into an undifferentiated score.

Some are much stronger than others.

### Strong evidence

```text
existing source-ID mapping
date of birth
unique full-name match
fixture-specific shirt number
```

### Medium evidence

```text
first initial + surname
team
nationality
position
```

### Weak evidence

```text
surname only
first name only
fuzzy string similarity
```

The exact strength of each source field can be refined after real data is inspected.


---

## 13. Missing vs Contradictory Evidence

Missing evidence and contradictory evidence are not the same.

Example:

```text
DOB missing
```

means:

> no evidence available from this field

Example:

```text
source DOB = 1997-10-30
candidate DOB = 1999-06-15
```

means:

> evidence actively contradicts the candidate

Contradictory strong evidence should generally block automatic matching.

Do not simply subtract a few points from a generic score and continue.


---

## 14. Fuzzy Matching

Fuzzy matching should be used late.

It is useful for:

- ranking plausible candidates
- spelling variation
- minor transcription differences
- ordering candidates for manual review

It should not normally be the sole reason for an automatic match.

Example:

```text
Source:
Longstaff

Candidate scores:
Sean Longstaff   94
Matty Longstaff  91
```

This does not mean Sean is the correct identity.

The source input simply lacks enough distinguishing information.

Therefore:

> **Never break a genuine identity tie using fuzzy score alone.**


---

## 15. One-to-One Assignment

When bootstrapping a full squad from a source, independent nearest-neighbour matching can produce duplicate assignments.

Example:

```text
source player A → canonical player X
source player B → canonical player X
```

A better approach may be:

1. resolve deterministic matches first
2. remove resolved players from the candidate pool
3. build a similarity matrix for unresolved players
4. perform one-to-one assignment
5. reject any assignment that does not meet uniqueness / confidence rules

The Hungarian algorithm is a possible implementation if needed.

This is particularly useful during initial source onboarding.


---

## 16. Player Aliases

An explicit alias mechanism is useful.

Example structure:

```text
player_aliases
--------------
pa_player_id
pa_source
pa_alias
pa_alias_normalised
```

Aliases may be:

- global
- source-specific

Examples:

```text
Gabriel
→ Gabriel Magalhães

João Pedro
→ João Pedro Junqueira de Jesus
```

Aliases are exception-handling tools, not canonical identifiers.


---

## 17. Short Names

One-token names require extra caution.

Examples:

```text
Gabriel
Alisson
Ederson
Antony
```

These should generally require contextual evidence such as:

```text
team
fixture
DOB
nationality
shirt number
```

A short name should not automatically resolve merely because it appears plausible.


---

## 18. Manual Resolution

Manual intervention is expected and acceptable.

The goal is not:

```text
zero manual resolution
```

The goal is:

```text
rare
explicit
repeatable
persistent
```

Once a manual mapping exists, it should override automatic matching unless deliberately changed.


---

## 19. Unresolved Entities

Keep unresolved cases explicit.

A simple structure is sufficient:

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

Optional additional fields may include:

```text
ue_candidate_count
ue_notes
```

An unresolved entity should remain unresolved rather than being guessed.


---

## 20. Match Method

A lightweight match-method field is useful.

Examples:

```text
existing_mapping
exact
deterministic
contextual
fuzzy
manual
```

Avoid pretending that an arbitrary numeric confidence score is more rigorous than it really is.

Numeric scores may still be useful internally for candidate ranking, but the persisted method should remain understandable.


---

## 21. Team Resolution

Team resolution follows the same general model but is simpler.

Possible names:

```text
Manchester United
Man Utd
Manchester Utd
MUN
```

Preferred resolution:

```text
existing source mapping
↓
normalised alias / deterministic mapping
↓
competition / country / season context
↓
manual resolution if required
```

A manual alias table will likely solve most team-name differences.

Avoid broad fuzzy matching across global clubs without context.


---

## 22. Team Temporal Context

Team identity should not be reduced purely to a current display name.

Historical backfills may eventually encounter:

- club renames
- rebrands
- naming variations
- reserve / youth teams
- promoted and relegated teams

Source aliases should map onto canonical team identity rather than becoming identity themselves.


---

## 23. Fixture Resolution

Fixture resolution should use structure rather than names alone.

Typical candidate fields:

```text
competition season
home team
away team
kickoff
```

Preferred flow:

```text
existing source fixture mapping
↓
resolve home team
↓
resolve away team
↓
filter to competition season
↓
compare kickoff within configurable tolerance
↓
require one viable fixture
↓
otherwise unresolved
```

Kickoff tolerance may be needed because of:

- timezone handling
- daylight-saving conversion
- provider rounding
- rescheduling
- stale source schedules


---

## 24. Fixture Uniqueness

The same uniqueness rule applies to fixtures.

Do not assume:

```text
home team + away team + season
```

is always sufficient.

Cup ties, replays, friendlies, or future project expansion may create repeated pairings.

Competition, date, kickoff, and context should narrow the candidate set to one fixture before automatic resolution.


---

## 25. Rescheduled Fixtures

A source may contain an old kickoff while the canonical fixture contains a revised kickoff.

Therefore fixture matching should not rely on exact kickoff equality alone.

Useful evidence:

```text
same competition season
same home team
same away team
kickoff near expected date
known reschedule context
```

Once resolved, persist the source fixture mapping so future ingestion no longer depends on kickoff comparison.


---

## 26. Competition Resolution

Competition resolution should mostly use explicit mappings and aliases.

Examples:

```text
Premier League
English Premier League
EPL
ENG Premier League
```

all map to the same competition.

Do not over-engineer this unless real source data demands it.


---

## 27. Season Resolution

Season labels may vary:

```text
2026/27
2026-27
2026
2026-2027
```

These can normally be handled with deterministic parsing and explicit source mapping.

The canonical project should own the season identity.


---

## 28. Source Errors

The resolver must allow for the possibility that the provider is wrong.

Examples:

- wrong name
- wrong team
- duplicate player record
- incorrect DOB
- recycled source ID
- stale squad association

The system should be able to represent:

```text
source record is incorrect / cannot be trusted
```

rather than forcing every source record onto a canonical entity.


---

## 29. Source ID Changes and Reuse

Source IDs are strong evidence but should not be treated as metaphysically permanent.

If a provider:

- replaces an ID
- merges records
- duplicates an identity
- recycles an identifier

the mapping must be repairable.

Manual overrides should be possible.


---

## 30. Canonical Merge and Split Repair

Canonical identities may occasionally be created incorrectly.

Two possible repair cases:

### Merge

Two canonical records are later discovered to represent the same real player.

Required action:

```text
choose surviving canonical identity
remap source mappings
update dependent canonical references
rebuild affected downstream data
```

### Split

One canonical player is later discovered to represent two different real players.

Required action:

```text
create correct canonical identities
reassign source mappings
rebuild affected records
```

The entity model should not assume canonical IDs are infallible.


---

## 31. Transfers and Historical Context

Do not assume:

```text
current team = historical team
```

Player resolution for historical records should use fixture- or date-aware team context.

Useful candidate logic:

```text
source player
+ source team
+ fixture date
```

matched against the player’s known team membership at that time.

This becomes increasingly important during historical backfill.


---

## 32. Duplicate Names

Exact name equality does not guarantee identity.

Possible case:

```text
same name
same season
different players
```

Useful tie-breakers may include:

```text
team
DOB
nationality
position
shirt number
fixture squad
```

But automatic resolution still requires one viable candidate after constraints are applied.


---

## 33. No Destructive Normalisation

Always retain original provider identity data.

Keep:

```text
source_name
source_id
source_team
source_context
```

alongside any cleaned or derived matching fields.

Never replace original source identity values with normalised versions.

This is essential for debugging.


---

## 34. Manual Overrides

Manual mappings should have precedence over automatic logic.

Example:

```text
source + source_player_id
→ manually mapped p_id
```

The resolver should check manual mappings before any automatic candidate generation.

Manual mappings should remain until explicitly changed.


---

## 35. Automatic Mapping Rebuilds

Automatic mappings should be rebuildable if matching logic improves.

A useful distinction is:

```text
manual mapping
automatic mapping
```

Possible future workflow:

```text
retain manual mappings
clear selected automatic mappings
rerun resolver
compare results
```

This allows improvements to name logic without destroying known human decisions.


---

## 36. Failure Semantics

Failure to resolve means:

```text
unresolved
```

It does not mean:

```text
entity does not exist
```

These states must remain separate.


---

## 37. Resolution Should Not Block Everything

A small number of ambiguous identities should not necessarily stop unrelated ingestion.

Example:

```text
1000 source records
997 resolved
3 unresolved
```

The 997 resolved records should generally be able to progress.

The 3 unresolved records remain visible for review.

Exactly how far partial records are allowed downstream can be decided per pipeline stage.


---

## 38. Scope of This Layer

Entity resolution should answer:

```text
Who is this player?
Which team is this?
Which fixture is this?
Which competition / season is this?
```

It should not answer:

```text
Which provider has the correct pass count?
What is the canonical xG value?
How reliable is this metric?
What model feature should be built?
```

Those belong in reconciliation, canonicalisation, and modelling layers.


---

## 39. Guiding Rules

1. Source IDs are mapped once and reused.
2. Names are matching evidence, not identity.
3. Candidate sets should be context-constrained.
4. Team context narrows candidates but does not guarantee uniqueness.
5. Every automatic name-based match must leave exactly one viable candidate.
6. Missing evidence is not the same as contradictory evidence.
7. Strong contradictions should block automatic matching.
8. Fuzzy similarity should rank candidates, not resolve genuine ambiguity by itself.
9. Manual mappings override automatic logic.
10. Source errors must be representable.
11. Canonical identities must be repairable through merge / split workflows.
12. Historical team context matters.
13. Original source identity values must never be destroyed.
14. Unresolved means unresolved, not nonexistent.
15. Entity resolution remains separate from metric reconciliation.
