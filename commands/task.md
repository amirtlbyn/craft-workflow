---
description: One merge request — spec, approval, implement inline, one review pass
argument-hint: <the task>
---

Run the **task** route for:

$ARGUMENTS

Load the `craft` skill.

1. Load `spec`. Create the spec with `bin/craft-spec new --route task`, write it,
   present it, and **stop and wait** for approval. Record it with
   `bin/craft-approve`.
2. Draft the scenarios (`spec` Step 7), present them, and **stop and wait**.
   Record them with `bin/craft-approve --scenarios` only on the developer's
   word. The gate denies test files until then. Source files stay open.
3. Write a short checklist into `tasks.md`. Each line names a file and a
   criterion ID.
4. Implement in this session. Do not spawn `coder`. One test per criterion, with
   the ID in its docstring.
5. Gate A: run the checkpoint, lint, import order, and format through
   `bin/craft-check`, and run `bin/craft-spec trace`.
6. Gate B: route the lenses with `config/workflow.md` §3. Spawn `reviewer`, and
   `deep-reviewer` in parallel when the spec says `Risk: high`. Adjudicate before
   you show the findings.
7. Fix confirmed findings. Re-review only the delta, only after a confirmed
   Critical or High. Append both gates to `log.md`.
8. **The task is done only when both gates pass.** Then run `/finish`.
