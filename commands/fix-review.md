---
description: Fix confirmed review findings, verify, and re-review only the delta
argument-hint: <the findings to fix>
---

Fix the confirmed findings:

$ARGUMENTS

Fix `Confirmed` findings, and `Plausible` ones you verify first. Fix in this
session on the task route, or through `coder` on the project route. Make the
smallest correct fix. A new test needs a criterion: when a finding shows a
missing criterion, propose a spec delta first.

Re-run Gate A through `bin/craft-check`. Explain every finding you reject or
defer, with the evidence. When a finding was a false positive, propose the
suppression rule for `aidocs/reviewer-memory.md`.

**Re-review only when a Critical or High was confirmed.** Re-run only the
reviewer that raised it, only on the diff since the review, and give it the
findings to verify. Report only the delta. Append the round to `log.md`.
