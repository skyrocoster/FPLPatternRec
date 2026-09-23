---
name: research
description: "Use during assessment for less-bounded repository research when a broader map and retained context will support later assessment decisions."
---

# Research repository context

Investigate a repository question whose useful answer is broader than one bounded fact. Use this skill when the
case-worker should retain the discovered context for the rest of the assessment. For a narrow factual lookup with
an exact answer, delegate to `scout` instead.

1. Start from the assessment packet's objective, named paths, known facts, and stop condition. Read
   any directly relevant active Plan before source when it has not already been read.
2. Search outward from the named surface only as needed to map ownership, behavior, callers or consumers, tests,
   conventions, and nearby precedents. Prefer `glob`, `grep`, and `read`; use `bash` only for read-only commands and
   always provide an explicit finite tool timeout.
3. Keep exact `path:line` or symbol evidence for implementation-critical findings. Separate observed facts from
   interpretations, contradictions, and remaining unknowns.
4. Stop when the question is answered well enough to continue the current assessment, or when further expansion
   would no longer change its scope, route, proof, or escalation boundary.
5. Carry the useful findings directly into the assessment. Do not create a separate research document unless the
   coordinator explicitly requests one.

Research is read-only. Do not edit, run destructive commands, inspect unrelated `Scratch` content, make product or
visual decisions, select the assessment route, or begin implementation. Do not delegate broad research back to
`scout` as a chain of narrow questions.
