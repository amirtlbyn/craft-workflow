---
description: Implement the next open session or task of the active spec
argument-hint: [session number or task, or empty for the next open one]
---

Load the `craft` skill and run the implement step of the active spec's route (task: step 3; project: step 5) for: $ARGUMENTS

With no argument, take the first session in `tasks.md` that is `pending` or
`in progress`. Use the session's `Model:` line to pick the `coder` model.
Follow the skill for every step.
