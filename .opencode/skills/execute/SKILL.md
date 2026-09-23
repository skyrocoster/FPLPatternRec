---
name: execute
description: Use during an execute phase to implement one approved direct change or one Plan stage and prove it.
---

# Execute

Require a coordinator packet containing the phase, outcome, exact paths or bounded Plan area, known facts,
ordered actions, proof commands, acceptance, exclusions, support skills if any, and escalation boundaries. Return
`BLOCKED` before editing when any required field is missing or contradictory.

1. Inspect only the approved paths and trust the packet's dirty-state baseline. If the packet or Plan declares
   upstream evidence or a read trigger relevant to this stage, inspect those approved read-only references before
   editing; do not infer that an undeclared design document should exist. Preserve unrelated changes.
2. For a bug, capture a meaningful red regression when it is cheap and deterministic; never manufacture a brittle
   source-text failure.
3. Make the smallest approved change. Do not refactor, polish, or repair adjacent behavior.
4. Reuse supplied passing proof unless an edit in this execution affects its command, inputs, exercised behavior,
   configuration, dependencies, or environment. Run only missing or invalidated behavioral tests or browser
   scenarios via the `bash` tool with an explicit finite timeout in milliseconds (missing, zero, or non-finite
   timeouts are forbidden because commands can hang). Do not run lint, formatting, broad type/build, source-size,
   aggregate, or repository-hygiene checks unless the approved outcome specifically changes that tool or constraint.
   Temporary maintenance violations do not block execution acceptance.
5. Perform one final changed-path and semantic scope audit against the packet. For a design-backed visual stage,
   also audit the changed result against its declared fidelity anchors and report intentional adaptations separately
   from unexplained drift. Component tests, DOM assertions, accessibility checks, and no-overflow checks do not by
   themselves prove visual fidelity; complete the packet's screenshot comparison or human visual breakpoint before
   claiming visual acceptance. Do not repeatedly run `git status` or `git diff`. On a failed check, make at most one
   deterministic, in-scope repair and rerun that check once; never weaken proof.
6. Stop without updating Plan progress. The coordinator records accepted results.

Escalate before crossing a path boundary or making a new product, visual, API, data, dependency, destructive,
ownership, or acceptance decision.

```text
RESULT: DONE | BLOCKED | ESCALATED | FAILED
EDITS: <changed paths or none>
REGRESSION: <red/green evidence or why red was not useful>
PROOF: <retained proof plus exact newly run commands and results>
INVALIDATION: <later changes and proof they invalidated, or none>
SCOPE AUDIT: clean | <discrepancy, including fidelity-anchor drift when applicable>
ACCEPTANCE: <observable result or remaining breakpoint>
RESIDUAL RISK: none | <specific risk>
ISSUE: none | <blocker>
```

Never create workflow artifacts, commit, or push.
