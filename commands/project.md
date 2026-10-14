---
description: Multi-session work — spec, design, sessions in tasks.md, coder per session
argument-hint: <the project>
---

Run the **project** route for:

$ARGUMENTS

Load the `craft` skill.

1. Load `spec`. Create the spec with `bin/craft-spec new --route project`, write
   it, and **stop and wait** for approval. Record it with `bin/craft-approve`.
2. Draft the scenarios (`spec` Step 7), present them, and **stop and wait**.
   Record them with `bin/craft-approve --scenarios` only on the developer's
   word. The gate denies test files until then.
3. Run `/design-brainstorm` when the architecture is unsettled.
4. Run `/plan`. `planner` writes `design.md` and the sessions in `tasks.md`.
5. For each session: `/implement`, which delegates to `coder` with the plugin
   root, the spec directory, and the session number, runs Gate A with
   `bin/craft-spec trace --session N`, and routes the review.
6. **Close the session only when both gates pass.** Loop through `/fix-review`
   until Gate B is green, or record each deferral with its reason in `log.md`.
   A session whose checkpoint never ran is `blocked`.
7. Run `/finish` per merge request.
