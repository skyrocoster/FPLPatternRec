---
name: design-catalogue
description: Use in early HTML UI exploration to compare broad alternatives or vary a selected concept around one narrower design question before Storybook.
---

# Design catalogue

Create a comparative decision aid under `experiments/mock-ups/<topic>/`. Require a parent concept or starting
surface, one question, inherited decisions and constraints, lightweight repository facts, and the minimum fidelity
needed to decide. When continuing existing work, inspect the latest artifact first and preserve authoritative user
edits.

## Shape the alternatives

- For broad exploration, make options structurally different in mental model, hierarchy, information, or
  interaction. Cosmetic variations alone are insufficient unless appearance is the explicit question.
- For a variation, inherit the selected parent unchanged except for the narrower question. Make lineage legible in
  the artifact regardless of filenames or folder structure. Do not create a Git branch or worktree.
- Give every option concise decision support: central idea, meaningful differences, and important trade-offs. Do not
  write the exhaustive specification reserved for the final choice.
- Use realistic content and genuine user-visible states. Preserve important existing capabilities unless their
  removal is explicitly being explored.
- Include only enough interaction to evaluate the question. Keep rejected alternatives until the user explicitly
  authorizes cleanup.

## Choose fidelity

Use one self-contained HTML/CSS page, with minimal JavaScript when useful. Keep the catalogue cheap to compare and
discard. If the decision requires real React composition, production tokens, shared component behavior, or detailed
keyboard interaction, select the broad HTML direction first and evaluate those details in the existing production
Storybook instead of building a parallel React environment under `experiments/`.

Use responsive layout, semantic elements, visible keyboard focus, and reduced-motion handling at either fidelity.
When browser tooling is available, verify the comparison surface loads without console errors and exercise only the
interaction required by the decision.

```text
RESULT: CREATED | UPDATED | BLOCKED
PATHS: <exact catalogue paths>
LINEAGE: <parent; current question; inherited decisions>
OPTIONS: <central idea and trade-off for each option>
FIDELITY: STATIC | INTERACTIVE-LIGHT
VERIFICATION: <finite command or browser scenario and observed result>
NEXT DECISION: <one selection or unresolved question for the user>
LIMITS: none | <known limitation>
```

Do not choose the winner, delete alternatives, edit product source or tests, or turn catalogue notes into an
implementation Plan.
