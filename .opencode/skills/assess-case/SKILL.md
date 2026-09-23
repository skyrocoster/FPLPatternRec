---
name: assess-case
description: "Use during PHASE: ASSESS to investigate one repository request and select the smallest safe route without editing."
---

# Assess one case

Investigate one bounded request and select the smallest safe route. Never edit, write a workflow record, or start
downstream work.

1. Read the relevant active Plan or destination record when one exists, the owning source,
   focused tests, and only the nearest consumer or precedent needed to establish the change shape. When the request
   or existing record declares upstream evidence, read the relevant declared artifacts too; do not require or search
   for a design document when none is declared.
2. Separate observed facts from desired behavior. Treat grilling records and master plans as optional evidence,
   not mandatory steps.
3. Define the observable outcome, included and excluded behavior, expected paths, implementation-critical facts,
   proof, acceptance, useful support skills, and exact escalation boundary.
4. For a design-backed UI outcome, identify which declared artifact governs composition and which document governs
   behavior or repository meaning. Extract only the fidelity anchors, allowed adaptations, excluded artifact chrome,
   and visual breakpoint needed downstream. Do not duplicate the full design hand-off.
5. When the target is a production-backed Storybook candidate, treat the selected HTML artifact as visual input and
   Storybook as the executable design workspace. Prefer a bounded `DIRECT-CANDIDATE`, explicitly exclude runtime
   application imports and integration, and do not require a Plan or `DESIGN.md`. Do not propose Git branches,
   worktrees, stashes, or commits as workflow steps.

Choose:

- `DIRECT-CANDIDATE` for one settled outcome with exact paths, focused proof, and no durable coordination need.
- `PLAN-CANDIDATE` for one coherent outcome needing durable context, multiple sequential stages, or breakpoints.
- `MASTER-PLAN-CANDIDATE` for a broad destination with at least two independently selectable outcomes.
- `QUESTION`, `BLOCKED`, or `NO-PROBLEM` only when the evidence supports that result.

Return:

```text
RESULT: DIRECT-CANDIDATE | PLAN-CANDIDATE | MASTER-PLAN-CANDIDATE | QUESTION | BLOCKED | NO-PROBLEM
TARGET: <surface or destination>
OUTCOME: <observable result>
ROUTE BASIS: <why this is the smallest safe route>
EVIDENCE: <concise path:line or symbol facts>
UPSTREAM: none | <declared evidence, each artifact's authority, and relevant read trigger>
SCOPE: <included behavior; expected paths; explicit exclusions>
CHANGE SHAPE: <one logical change, sequential stages, or selectable slices>
KNOWN FACTS: <facts execution must preserve>
FIDELITY: n/a | <compact anchors, allowed adaptations, excluded artifact content, and visual breakpoint>
SUPPORT SKILLS: none | <explicit skill names and purpose>
PROOF: <regression guard, exact focused commands, full/live proof when required>
ACCEPTANCE: <observable pass condition and any real breakpoint>
ESCALATE IF: <specific decision or scope boundary>
ISSUE: none | <question or blocker>
```

Stop after the result.
