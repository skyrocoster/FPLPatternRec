---
name: design-exploration
description: Use when designing a UI piece from a basic HTML mock-up through production-backed Storybook iteration and explicit approval before application integration.
---

# Design exploration

Own one simple, sequential design loop:

`basic HTML mock-up -> production Storybook candidate -> user approval -> integration assessment`

Keep user decisions and approval in the coordinator. Delegate repository facts to `scout`, disposable HTML work to
`exploration`, and production-backed Storybook work to the selected case-worker with
`frontend-component-iteration` support. Do not create a Plan or require `DESIGN.md` while the design itself is still
being explored.

Use the current repository checkout in place. Do not create or switch Git branches, worktrees, stashes, or commits
as part of this workflow unless the user explicitly requests that Git operation. A Git branch is not a design gate.

## Decision frontier

Retain only the information needed for the next useful move:

- the latest authoritative artifact and its parent concept;
- the narrower question currently being explored;
- inherited decisions and constraints that remain fixed;
- material unresolved decisions;
- whether the user has selected the HTML direction;
- whether the Storybook candidate is still exploratory or approved for integration; and
- what application integration remains after approval.

Do not impose a stage checklist, numbering scheme, one-file-per-round rule, or documentation chain. Work may enter
midway, revisit an earlier question, or stop when the user chooses.

## Route the loop

1. Retrieve only the lightweight facts needed to avoid designing the wrong thing: the current interface, genuine
   user-visible states, retained capabilities, and obvious constraints. Treat implementation as evidence, not as
   the required design.
2. If no useful artifact exists, send `exploration` a bounded `mock-up` brief for a basic self-contained HTML/CSS
   artifact with minimal JavaScript when needed. For comparison work, send a `design-catalogue` brief naming the
   parent, question, inherited decisions, baseline facts, and minimum sufficient fidelity.
3. Present the result as a decision aid. Ask the user to select, reject, combine, refine, or stop. Selection does not
   authorize deletion of alternatives or application integration.
4. For another HTML round, vary only the selected concept around a narrower question. "Branch" here means a design
   alternative, never a Git branch. Resume the same exploration session when its context is useful; otherwise send a
   complete frontier packet to a fresh session.
5. Use `grilling` only when an option exposes a material decision that artifacts cannot settle.
6. Treat direct user edits to the latest artifact as authoritative. Bound and inspect them before continuing; never
   restore an older interpretation. Report contradictions or consequences instead of silently overruling edits.
7. When the user selects the HTML direction, retrieve the nearest Storybook, component, token, styling,
   accessibility, and focused-test conventions. Do not retrieve routes, APIs, or product integration details unless
   they are necessary to render a truthful design state.
8. Route one bounded direct execution to create the candidate in the existing production Storybook. The candidate
   must use real production tools and live in the normal frontend source tree, but it must not be imported by the
   runtime application or connected to real routes, state, data, or APIs. Use a clearly temporary Storybook title
   such as `Exploration/<Name>`.
9. Iterate organically in Storybook with the retained case-worker and `frontend-component-iteration`. Each round
   implements the user's latest visual or interaction feedback, runs only focused proof invalidated by that change,
   and returns to visual review. Do not reassess the whole feature or write a Plan for every adjustment.
10. Ask the user explicitly whether the Storybook candidate is approved for application integration. Storybook
    completion alone is not approval. Before approval, continue iterating, replace the candidate, or remove it as
    directed; do not integrate it.
11. After approval, route only the remaining application integration through ordinary assessment. Use a direct
    change when small or a Plan when integration genuinely needs durable multi-stage coordination. Do not redesign
    the approved component in the integration Plan.

Use `design-synthesis` only when the user asks for durable design notes or important behavior cannot be expressed by
the mock-up, stories, component API, or focused tests. It is optional and must never block Storybook iteration or
integration assessment.

## Fidelity and authority

- **HTML:** self-contained HTML and CSS with minimal JavaScript and representative states. Use it to settle the
  broad visual and interaction direction cheaply.
- **Production Storybook:** React after the HTML direction is selected, using actual production tokens, styles,
  component conventions, semantics, focus behavior, and representative states.

Start a new UI-piece workflow with basic HTML. After selection, rebuild the idea rather than importing runtime code
from `experiments/`. Storybook is the required place to test the design against production tools before integration;
do not skip directly from HTML into an application route.

Before integration, visual and interaction changes return to the Storybook loop. After integration begins, a
material change to the approved design returns to Storybook and requires renewed approval. If HTML and Storybook
conflict, Storybook is authoritative after the user has approved it; before approval, ask rather than inventing
precedence.
