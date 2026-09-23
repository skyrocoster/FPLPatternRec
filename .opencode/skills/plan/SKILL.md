---
name: plan
description: "Use during PHASE: WRITE PLAN to create or refine one approved focused implementation Plan without coding."
---

# Plan

Require an approved target under `docs/plans/active/<feature>/<feature>.md`, outcome, scope, stage shape, proof,
acceptance, and escalation boundaries. Reuse retained assessment facts; read `docs/PLAN_TEMPLATE.md`, the router,
an existing matching Plan when present, and any upstream evidence explicitly declared by the approved packet or
existing Plan. Do not search for or require design evidence when none is declared. Never implement.

Write the compact template exactly enough to preserve:

- one semantic, human-visible outcome and visible-result line;
- upstream evidence, expected areas, and explicit exclusions;
- sequential AI-focused stages with ordered actions, focused proof, and real breakpoints;
- non-overlapping proof where practical, with reruns only after a stage changes something that could affect the
  earlier result;
- concise progress and decisions; and
- escalation boundaries for any decision not already settled.

When signed-off design evidence is declared, add the template's compact `Design fidelity` section. Identify each
artifact's authority, preserve only the small set of implementation-critical visual or interaction anchors, state
allowed canonical adaptations and excluded artifact chrome, and attach each anchor to a stage acceptance check or
real visual breakpoint. Link to detailed upstream sections instead of copying them. Omit this section when no
signed-off design evidence exists.

For a UI designed through Storybook, require explicit user approval of the Storybook candidate before planning
application integration. Treat the approved component and stories as primary executable design evidence; a
`DESIGN.md` is optional. Plan only remaining integration such as product placement, state, data, routes, APIs, and
integration proof. Do not add stages that recreate the HTML mock-up, redo settled Storybook design, create a Git
branch/worktree, or obtain approval already recorded.

Expected areas describe ownership; they are not exact executor authorization. Do not add parallel stages,
transient execution logs, speculative work, or legacy records. Preserve truthful completed progress when refining
an existing Plan. If outcome, scope, dependency, proof, or acceptance is unresolved, do not guess.

Prescribe only finite behavioral tests or browser scenarios that directly prove this Plan's outcome. Do not include
lint, formatting, broad type/build, source-size, aggregate, or other repository-hygiene checks unless the outcome
specifically changes that tool or constraint. Temporary maintenance violations do not block implementation or Plan
acceptance. State that passing behavioral proof is retained until an affecting change. Independent validation and
complete test/fix runs are separate workflows when requested.

Run the coordinator-supplied documentation check when present, with an explicit finite `bash` tool timeout in
milliseconds (missing, zero, or non-finite timeouts are forbidden because commands can hang); otherwise inspect
the final document against the template and report that no automated Plan checker exists.

```text
RESULT: WRITTEN | UNDER-CAPTURED | BLOCKED
PATH: <approved Plan path or none>
CHECKS: <command and result, or manual template review>
ISSUE: none | <missing decision or blocker>
```
