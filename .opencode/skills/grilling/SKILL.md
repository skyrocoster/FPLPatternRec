---
name: grilling
description: Use when the user requests an interview or material decisions must be settled before routing work.
---

# Grilling

Use only for an explicit interview or genuine unsettled product, visual, architecture, data, contract, or direction
choices. It is optional and does not create a mandatory document chain.

Treat grilling as both discovery and decision coaching. Help the user make strong, repeatable, well-structured
decisions by making the relevant goal, criteria, tradeoffs, and reasoning visible without taking the decision away
from them.

1. Build and update an internal decision tree. A question is ready only when its prerequisites are settled.
2. Retrieve repository facts through bounded `scout` lookups; do not ask the user for facts the tools can answer.
3. Ask exactly one highest-leverage ready question per turn in a light ELI5 style: use plain language, short
   sentences, and concrete examples when helpful, but never talk down to the user or hide important nuance.
4. Offer distinct options when useful, identify one recommendation, and explain it briefly in terms of the current
   goal, decision criteria, and tradeoffs. Frame the reasoning so the user could apply it again in a similar case.
5. Record the answer, reason, uncertainty, exclusions, and any new dependent decisions. Never decide for the user
   or repeat a settled question.
6. When no material frontier remains, present a concise shared-understanding summary and ask for confirmation.

After confirmation, write one free-form synthesis under `docs/grilling-docs/` only when the user asks or future
work needs durable directional evidence. It is historical evidence, not a Plan or implementation authorization.
Do not edit completed records or begin implementation.

## Grilling Q&A Template

**What changed**
- <the decision just settled by the user's previous answer>
- <any important consequence, constraint, or newly unlocked decision>
- <omit on the first question>

**Decision**
<Ask exactly one highest-leverage ready question in plain, concrete language. Briefly explain why it matters when
that is not obvious.>

**Options**
- **A. <Option name>** — <brief consequence or tradeoff>
- **B. <Option name>** — <brief consequence or tradeoff>
- **C. <Option name>** — <brief consequence or tradeoff>

**Recommendation:** **<recommended option>**  
<Briefly explain why this option best fits the goal and criteria, what tradeoff it accepts, and how the same
reasoning could guide a similar decision later.>
