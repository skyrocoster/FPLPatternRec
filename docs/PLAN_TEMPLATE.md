# Focused Plan schema

A focused Plan is the durable implementation instrument for one coherent, independently acceptable outcome.
It preserves decisions and progress without becoming an executor script. Detailed
authoring and execution guidance lives in the `plan` and `execute` skills.

## Output schema

```md
# <Outcome name> - <one visible-result line>

> **Status:** pending | in progress | done - <short progress and next boundary>

- **Read trigger:** <when this Plan must be read>
- **Upstream:** <declared signed-off design, grilling, master-plan, or other governing evidence; or none>

## Outcome
<The semantic human-visible result and why it matters.>

## Scope
- **Included:** <behavior and ownership areas included>
- **Expected areas:** `<bounded source or documentation globs>`
- **Excluded:** <adjacent behavior, refactors, contracts, and paths excluded>

## Design fidelity
<Include only when signed-off design evidence is declared; otherwise omit this section.>

- **Authority:** <artifact and role, such as visual composition or behavior/repository meaning>
- **Excluded artifact content:** <review chrome, demo controls, annotations, or none>

| Anchor | Preserve | Allowed adaptation | Acceptance |
|---|---|---|---|
| <upstream section, selector, or state> | <implementation-critical detail> | <canonical translation allowed> | <stage check or visual breakpoint> |

## Stages
1. **pending** - <sequential AI-focused stage and its outcome>
2. **pending** - <next stage, only when partial delivery is meaningful>

Every stage has ordered actions, focused proof, an escalation boundary, and any human or visual breakpoint.
Stages are sequential; no parallel stages. The coordinator may split an oversized stage without changing
the outcome or requiring a new human decision. A passing proof item remains valid until a later change affects
its command, inputs, exercised behavior, configuration, dependencies, or environment; later stages run only
missing or invalidated proof.

## Progress and decisions
- **Stage 1:** pending - proof: <short proof>; breakpoint: <decision or none>

## Proof
- <finite tests or browser scenarios that directly demonstrate the intended behavior>

## Escalation boundaries
- <new product, visual, API, data, dependency, destructive, ownership, or acceptance decision>

## Visible result
> <One concise line a non-developer can verify when the outcome is complete.>
```

## Rules

- Use semantic outcomes, expected areas, and exclusions rather than exact executor authorization lists.
- Keep stages AI-focused and ordered. Record `pending`, `in progress`, or `done` with concise proof and
  breakpoint decisions.
- Link declared upstream evidence when present and restate only implementation-critical facts.
- Do not require or search for design evidence for an ordinary Plan. When signed-off design evidence is declared,
  read it, include the compact `Design fidelity` section, and connect every listed anchor to stage acceptance or a
  real visual breakpoint. Keep detailed design content upstream rather than duplicating it in the Plan.
- Human pauses are for genuine product or visual decisions. User edits at a visual breakpoint are authoritative.
- Prescribe only finite behavioral tests or browser scenarios that directly prove this Plan's outcome. Exclude lint,
  formatting, broad type/build, source-size, aggregate, and repository-hygiene checks unless the outcome specifically
  changes that tool or constraint. Temporary maintenance violations do not block acceptance; complete test/fix runs
  are separate workflows.
- Use a transient `handoff.md` only while rolling context; overwrite it on rollover and delete it at closeout.
- A Plan never records transient executor evidence or a parallel execution graph.
