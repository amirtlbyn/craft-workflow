---
description: Run one routed review pass against the spec and adjudicate the findings
argument-hint: [target, or empty for uncommitted changes; "full" for one reviewer per lens]
---

Review target: $ARGUMENTS

With no target, review the current uncommitted changes against the active spec.

Load `review-protocol`. When Jev is on, run `bin/craft-jev decide --stage
review --base <base>` and use the lenses, reviewer, and deep-reviewer it prints.
Otherwise pick the lenses with `config/workflow.md` §3 from what the diff
touches. `spec` and `style` always run when a spec is active. State the
lenses and why, in one line.

Spawn `reviewer` once with the plugin root as an absolute path, the spec
directory, the lens list, and the diff command. When the spec says `Risk: high`, spawn `deep-reviewer` in parallel for
`logic` and `security`, and leave those two lenses out of `reviewer`. With
"full", spawn `reviewer` once per lens instead.

Wait for all of them. Adjudicate with `skills/review-protocol/references/adjudication.md`.
Carry every `unclear` checklist item into the report as an open question. Do
not edit code. Append the result to `log.md` when a spec is active.
