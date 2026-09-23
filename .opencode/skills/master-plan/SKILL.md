---
name: master-plan
description: "Use during PHASE: WRITE MASTER PLAN to record an approved broad destination as selectable slices without implementation."
---

# Master plan

Require explicit user-approved destination, direction, slice envelope, exclusions, and target under
`docs/master-plans/`. Read `docs/MASTER_PLAN_TEMPLATE.md`, the router, relevant current evidence, and an existing
matching destination when present.

Record only the broad human outcome, settled principles, independently selectable slices, dependencies, explicit
exclusions, and lightweight links or results for completed slices. Each slice must have one independently
reviewable human-visible result. Do not choose a slice, create a focused Plan, add implementation status, or edit
a completed historical master plan. Any check command must run via the `bash` tool with an explicit finite
timeout in milliseconds; missing, zero, or non-finite timeouts are forbidden because commands can hang.

```text
RESULT: WRITTEN | UNDER-CAPTURED | BLOCKED
PATH: <approved master-plan path or none>
DESTINATION: <broad outcome>
SLICES: <IDs, results, and dependencies>
UNRESOLVED: none | <decision still required>
CHECKS: <command and result, or manual template review>
ISSUE: none | <blocker>
```
