---
description: Write the spec for a change — EARS acceptance criteria, non-goals, invariants, risk — and stop for approval
argument-hint: <what to specify, or "delta: <change>" for an approved spec>
---

Load the `spec` skill and specify:

$ARGUMENTS

With no active spec, create one with `bin/craft-spec new` and the route the
`craft` rules pick (`task` or `project`). With an active, approved spec and an
argument that starts with `delta:`, follow the skill's "Spec deltas" section.

Present the criteria table, the "Not tested, and why" list, the non-goals, the
risk tier, and the open questions. **Stop and wait** for approve, cut, add, or
change. Record the approval with `bin/craft-approve` only after the developer
gives it. Write no code and no test.
