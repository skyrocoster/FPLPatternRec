---
name: coordinator-workflow
description: Use for every repository-dependent request; routes decisions, assessment, Plans, execution, Exploration, and optional validation.
---

# Coordinator workflow

The coordinator owns decisions, routing, scope, records, acceptance, and stopping. Keep decision context at the
frontier; delegate repository reads and edits.

## 1. Choose the route

- Answer informational questions directly. Use one bounded `scout` lookup first when the answer depends on
  repository facts.
- Use `grilling` for an explicit interview or material unsettled product, visual, architecture, data, contract,
  or direction decisions. Write the grilling synthesis doc under `docs/grilling-docs/` yourself; it is a
  coordinator-owned workflow record, not an implementation task to delegate.
- When substantial UI or interaction direction is unsettled, invoke `design-exploration`. Start with disposable
  HTML under `experiments/`, then route the selected direction into an application-isolated candidate in the
  existing production Storybook. Keep selection and approval in the coordinator. Send disposable artifacts to
  `exploration` and Storybook creation/iteration to the selected case-worker with
  `frontend-component-iteration` support.
- For one disposable mock-up or prototype that does not need iterative narrowing, send one bounded brief directly
  to `exploration`.
- For canonical repository work that may change files or create a workflow record, ask once whether Luna or Flash
  should own the case, explain the tradeoff, make one recommendation, and retain the choice. Reserve the
  medium-reasoning Sol case-worker for an explicit user request or particularly hard emergency work; do not offer
  it as a routine option. Launch the selected case-worker with `PHASE: ASSESS`. Use the bulk-task case-worker
  (`coordinator-caseworker-bulk`, Luna at low reasoning, unrestricted permissions with `external_directory` and
  bulk copy) only when the user explicitly requests it or explicitly requests bulk work such as bulk copy.
- Use `scout` whenever a coordinator decision needs one bounded missing or stale fact. Case-workers may invoke
  `research` for a less-bounded repository investigation when its expanded result is likely to be useful throughout
  the later assessment; do not decompose that work into a chain of narrow Scout questions. Do not repeat clean
  case-worker or delegated reads.

When assessment needs `research`, name it under `SUPPORT SKILLS` in the `PHASE: ASSESS` packet. Include a research
objective, relevant paths and known facts, expected output, and a stop condition. Do not send `research` as a
separate subagent task: the selected case-worker invokes the skill so the expanded context remains in its retained
assessment session.

Design exploration ends only after the user explicitly approves the production-backed Storybook candidate for
integration. Do not require a `DESIGN.md` or Plan during HTML or Storybook iteration. After approval, assess and
Plan only the remaining route, state, data, API, and application integration work. Do not silently skip Storybook
or treat a selected HTML mock-up as integration approval.

Keep the design workflow in the current checkout. Never create or switch Git branches, worktrees, stashes, or
commits as workflow steps unless the user explicitly requests the exact Git operation.

## 2. Review assessment

Ask the user only when an answer changes the outcome, behavior, contract, dependency, destructive effect, or
acceptance. Handle the case-worker result as follows:

- `DIRECT-CANDIDATE`: resume with `PHASE: EXECUTE DIRECT` and the approved execution packet, including any
  declared upstream reads and fidelity requirements from assessment.
- `PLAN-CANDIDATE`: resume with `PHASE: WRITE PLAN`, the approved Plan path, outcome, scope, stages, proof,
  acceptance, escalation boundaries, and any upstream evidence explicitly declared by the assessment. When that
  evidence includes a signed-off design, include its authority roles, compact fidelity anchors, allowed adaptations,
  excluded artifact content, and required visual breakpoint. Do not introduce design-document requirements for a
  case whose assessment declares no such evidence.
- `MASTER-PLAN-CANDIDATE`: obtain explicit user approval for the destination and slice envelope, then resume with
  `PHASE: WRITE MASTER PLAN`. Do not implement or choose a slice.
- `QUESTION`, `BLOCKED`, or `NO-PROBLEM`: resolve or report exactly that result; do not force another route.

For a selected HTML direction moving into Storybook, prefer one bounded direct candidate rather than a Plan. Reuse
the retained case-worker for user-led Storybook rounds; update the execute packet with the latest feedback and
invalidated proof instead of reassessing or replanning the whole component. Keep application integration explicitly
excluded until approval.

Before resuming a retained case-worker, call `context_budget`. When assessment returns `PLAN-CANDIDATE`, prefer
resuming that case-worker with `PHASE: WRITE PLAN` while its assessment context is available; this priority applies
through `DECISION-REQUIRED` because writing the Plan externalizes that context. Only start a fresh Plan writer when
the tool reports `ROLLOVER-DEFAULT` or the retained session is unusable. For other results, follow the tool's default
action. At `DECISION-REQUIRED`, resume only if continuity is important and the remaining phase is small; otherwise
start a fresh case-worker with a compact approved packet. When telemetry is unavailable, prefer a fresh case-worker
unless untransferred reasoning makes a short resume safer.

## 3. Execute

Every execute packet must name the outcome, exact paths or bounded Plan area, known facts, ordered actions,
proof commands — each with an explicit finite `bash` tool timeout in milliseconds (missing, zero, or non-finite
timeouts are forbidden because commands can hang) — acceptance, exclusions, support skills if any, and
escalation boundaries. For a Plan, execute one stage at a time with `PHASE: EXECUTE PLAN STAGE`; stages never
run in parallel. The coordinator may split an oversized stage only when the Plan outcome and acceptance remain
unchanged.

When the Plan or approved case declares upstream evidence relevant to the stage, include those artifacts as
approved read-only paths and carry forward the applicable read trigger and fidelity anchors. For a design-backed
visual stage, require representative visual evidence or a human visual breakpoint; behavioral tests, DOM checks,
accessibility checks, and no-overflow checks cannot alone satisfy visual fidelity. No extra visual process applies
when no signed-off visual evidence is declared.

Review the returned proof and diff scope. Do not silently expand behavior. User edits at a visual breakpoint are
authoritative: bound them, preserve them, and continue from the resulting state.

Maintain one proof ledger in the active conversation. For every passing command or browser check, retain its
exact command/scenario, working directory, finite timeout, result, covered behavior or check step, and the paths,
configuration, dependencies, and environment it relied on. Passing proof remains valid until a later edit or
environment change could affect what it established. Before requesting any check, compare changes since its pass:
reuse unaffected proof, rerun only invalidated proof, and add only genuinely missing coverage. A broader command
must not be used merely to rerun already-covered tests.

## 4. Accept and record

Accept implementation when finite behavioral tests or browser scenarios establish the Plan or direct-change outcome
and all required human or visual breakpoints pass. A stage governed by declared signed-off visual evidence remains
unaccepted until its fidelity anchors have visual evidence or the named human breakpoint passes; record intentional
canonical adaptations and reject unexplained drift. Do not use lint, formatting, broad type/build, source-size,
aggregate, or other repository-hygiene checks as implementation proof unless the outcome specifically changes that
tool or constraint. Temporary maintenance violations do not block Plan acceptance; do not append a
complete repository-suite closeout.

After behavioral proof and any required human or visual breakpoint pass, update only the active Plan's progress,
decisions, and concise proof. An active Plan may contain one transient `handoff.md` during context rollover; it is
coordinator-reviewed, overwritten on rollover, and deleted at closeout. When every stage is accepted, set the Plan to
done, remove any transient `handoff.md`, and move its feature directory from `docs/plans/active/` to
`docs/plans/done/`. Complete test/fix runs belong to a separate maintenance workflow and do not block Plan completion.

Never create legacy lifecycle artifacts, commit, push, rewrite completed records, or disturb unrelated changes.
