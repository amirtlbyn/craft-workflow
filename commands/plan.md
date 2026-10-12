---
description: Turn the approved project spec into design.md and sessions in tasks.md
argument-hint: [empty for the active spec]
---

Load the `planner` skill and plan the active spec. $ARGUMENTS

Run `bin/craft-spec status` first. The spec must be `approved`. When it is not,
stop and say which step is missing.

Write `design.md` and the `## Session N` blocks of `tasks.md` in the active spec
directory. Every task names a file and the criterion it serves. Add no behavior
the spec does not state. Finish with the standards review in `design.md`, then
present the sessions and stop. Do not edit implementation files.
