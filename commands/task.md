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
2. Write a short checklist into `tasks.md`. Each line names a file and a
   criterion ID.
3. Implement in this session. Do not spawn `coder`. One test per criterion, with
   the ID in its docstring.
4. Gate A: run the checkpoint, lint, import order, and format through
   `bin/craft-check`, and run `bin/craft-spec trace`.
5. Gate B: route the lenses with `config/workflow.md` §3. Spawn `reviewer`, and
   `deep-reviewer` in parallel when the spec says `Risk: high`. Adjudicate before
   you show the findings.
6. Fix confirmed findings. Re-review only the delta, only after a confirmed
   Critical or High. Append both gates to `log.md`.
7. **The task is done only when both gates pass.** Then run `/finish`.
