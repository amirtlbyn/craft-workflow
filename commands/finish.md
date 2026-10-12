---
description: Final diff hygiene and merge-request text, traced to the spec, without committing
argument-hint: [optional context]
---

Load the `git-hygiene` skill. $ARGUMENTS

Inspect the staged and unstaged diffs. Identify unrelated edits, secrets,
generated artifacts, migrations, and formatting churn. Confirm which checks
actually ran with `bin/craft-session status` — never report one that did not.

Confirm every review finding is fixed, rejected with a reason, or deferred with a
reason. Prepare an atomic commit suggestion and a merge-request summary:
problem (from the spec), the acceptance criteria and the test that proves each
one, implementation, verification, rollout and migration notes, risks.

Write both to the rules in `skills/asd-ste100/references/card.md`. Do not commit
or push. Close the spec with `bin/craft-spec close` only when the developer says
the work is merged.
