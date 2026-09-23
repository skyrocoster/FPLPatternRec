---
name: mock-up
description: Use for one basic standalone HTML UI mock-up under experiments before production-backed Storybook design work.
---

# Mock-up

Create one isolated review artifact under `experiments/mock-ups/<topic>/`. Use `frontend-design` first when the
brief needs a visual direction. For comparative alternatives or a branch from a selected concept, use
`design-catalogue` instead. When continuing an artifact, inspect the latest version first and preserve authoritative
user edits.

Use one self-contained HTML/CSS file with minimal optional JavaScript. Its job is to make the broad visual and
interaction direction cheap to review, change, or discard. Do not turn the normal UI-piece workflow into an
isolated React implementation: after the user selects the HTML direction, rebuild it in the existing production
Storybook instead.

Use realistic content, responsive layout, semantic elements, visible keyboard focus, and reduced-motion handling.
Keep HTML exploration isolated from application imports and network requests. Verify the artifact loads without
console errors when browser tooling is available. Do not create or switch Git branches or worktrees for the mock-up.

```text
RESULT: CREATED | UPDATED | BLOCKED
PATHS: <exact artifact paths>
FIDELITY: STATIC | INTERACTIVE-LIGHT
VERIFICATION: <how it was viewed and observed result>
REVIEW: <direction or decision presented>
LIMITS: none | <known limitation>
```

Do not edit product source, tests, Plans, canonical documentation, or unrelated `Scratch` content.
