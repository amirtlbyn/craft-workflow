---
description: Diagnose and fix a bug using the evidence-first debugging workflow
argument-hint: <failure description or command>
---

Load the `debugging` skill and diagnose:

$ARGUMENTS

Diagnose in the main session. Reproduce before editing when possible, test
hypotheses against evidence, and find the root cause. Run reproductions through
`bin/craft-check` so the output stays short and the log stays on disk.

Then make the smallest root-cause fix, inline. A regression test is REQUIRED and
needs no spec: it must fail before the fix and pass after it. When the fix
touches money, authorization, a migration, or a contract, stop and promote to
`/task` so the fix gets a spec. Run focused verification.
