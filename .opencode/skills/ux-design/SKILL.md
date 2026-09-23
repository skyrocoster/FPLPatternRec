---
name: ux-design
description: Use during planning to settle interaction behavior for a page, dialog, editor, board, or flow without coding.
---

# UX design

Work at planning time only. Read existing design, accessibility, and interaction contracts plus the nearest
surface with the same task shape. Identify the user, their primary task, devices, interruption risk, and safety
constraints. Missing guidance is an open decision, not permission to invent a project-wide rule.

Settle only behavior that applies: entry and exit, information priority, loading/empty/error/success states,
primary and destructive actions, persistence and failure feedback, keyboard/pointer/touch/focus behavior,
responsive transformation, accessibility, and recovery from data loss.

Return a Plan-ready block:

```text
## UX Decisions - <surface name>

User and task: <role and one primary outcome>
Entry/exit: <arrival, cancel/back, and work preservation>
Priority/layout: <what leads; wide and constrained behavior>
States: <applicable loading, empty, error, success, and no-selection behavior>
Actions: <primary, secondary, destructive, and recovery behavior>
Persistence: <save model and failure feedback>
Input: <keyboard, pointer, touch, focus, and target expectations>
Accessibility: <semantics, contrast, announcements, and assistive technology>
Exclusions: <adjacent behavior not authorized>
```

Every state must provide a useful next action or an honest explanation. Escalate unresolved product or visual
choices; do not implement them.
