---
description: Measure how much code a change added, from the real diff
argument-hint: <base ref, default the merge base with main>
---

Measure the change against $ARGUMENTS. With no argument, use
`git merge-base HEAD main` as the base and include uncommitted work.

Run these from the host repository root. They only read.

- `git diff --numstat <base>` — lines added and removed per file
- `git diff --diff-filter=A --name-only <base>` — new files
- `ast-grep` for the definitions the diff added: functions and classes in the
  changed files that were absent at the base

Report:

```
Minimal-code gain — <base>..working tree
- Lines: +<added> −<removed> (net <n>) in <files> files
- New files: <n>
- New functions and classes: <n>
- Of the added lines, in tests: <n>, in code: <n>
```

Then read the "Minimal-code decisions" block from the last report or from
`log.md`, and list what was reused instead of written.

State plainly that this measures the diff, not a counterfactual. The workflow
does not know how many lines an unassisted run would have written, so it never
reports a percentage saved.
