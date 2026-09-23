---
name: design-synthesis
description: Use only when requested to record durable design decisions that an approved Storybook candidate, its stories, API, and focused tests cannot express.
---

# Design synthesis

This is optional. Never require it between HTML selection, Storybook iteration, approval, and integration. Require
an explicitly approved Storybook candidate, a concrete reason durable notes are needed, settled behavior decisions,
relevant repository facts, and an approved `DESIGN.md` path under `experiments/`. Inspect the latest candidate and
stories before writing so authoritative user edits are carried forward.

Write only what is supported by the selected design, settled decisions, and repository evidence. Report a
contradiction between them instead of inventing precedence. The document should include the applicable parts of:

- purpose, mental model, terminology, non-goals, and retained capabilities;
- visible anatomy, information hierarchy, responsive behavior, and visual roles;
- meaningful states, conditions, transitions, action visibility, and empty states;
- persistence, pending, error, recovery, and replacement semantics;
- copy rules, component-owned or model-owned language, and anti-duplication rules;
- tokens, reusable component boundaries, and motion behavior;
- keyboard, focus, semantics, announcements, contrast, and reduced motion;
- current repository components, models, APIs, ownership boundaries, and focused tests affected; and
- settled invariants and unresolved technical facts clearly separated.

Include a compact adoption boundary that distinguishes details canonical implementation must preserve, details it
may translate onto repository conventions, and artifact-only content it must exclude. Give the most important
visual or interaction anchors stable section references so a downstream Plan can link them without copying the
whole document.

Keep the document implementation-ready but not implementation-prescriptive. Do not define Plan stages, progress,
proof execution, lifecycle mechanics, or implementation authorization. The approved Storybook candidate
communicates composition and executable behavior; the design document records only important context that those
artifacts cannot express without duplication.

```text
RESULT: WRITTEN | CONTRADICTION | BLOCKED
STORYBOOK: <approved story and component paths>
DESIGN: <exact DESIGN.md path>
GROUNDING: <repository areas mapped>
UNRESOLVED: none | <technical facts that planning must resolve>
HAND-OFF: <concise evidence summary for assessment and planning>
ISSUE: none | <contradiction or blocker>
```

Do not edit product source, tests, Plans, canonical documentation, rejected alternatives, or unrelated `Scratch`
content.
