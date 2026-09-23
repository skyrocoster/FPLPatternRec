# Master Plan schema

A master plan records a broad product destination and the independently selectable slices that may later
become focused Plans. It records direction, dependencies, and boundaries; it does not authorize implementation.
Detailed discovery and design guidance lives in the `master-plan` skill.

## Output schema

```md
# <Destination name>

> **Status:** draft | direction settled

## Destination
<One concise broad human outcome.>

## Settled direction
- <principle or decision later slices must preserve>
- <accessibility, safety, ownership, or compatibility boundary>

## Selectable slices
| Slice | Human-visible result | Depends on | Explicit exclusion |
|---|---|---|---|
| <ID> | <one independently reviewable result> | <IDs or none> | <nearby work excluded> |

## Slice results
- **<ID>:** <link to the focused Plan or concise accepted result, when complete>

## Exclusions
- <adjacent product, architecture, data, visual, or workflow work outside this destination>
```

## Rules

- Keep the destination, settled direction, selectable slices, dependencies, and exclusions compact.
- Each slice must be independently reviewable and selectable by a human. Split only when the result or
  acceptance boundary changes.
- Slice results are lightweight links or outcomes, not implementation queues.
- Do not move implementation status into this document. Focused Plans own implementation progress.
