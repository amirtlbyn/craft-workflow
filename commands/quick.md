---
description: Small fix — implement inline, no spec, no reviewer subagent
argument-hint: <the small change>
---

Run the **quick** route for:

$ARGUMENTS

Load the `craft` skill, then `python-style` and `django-practices` as the files
require. Read `skills/asd-ste100/references/card.md` before you write any
comment or docstring.

Make the change yourself in this session. Do not spawn a subagent. Run the
focused checks from `config/workflow.md` §6 through `bin/craft-check`, then read
your own diff once against `skills/review-protocol/lenses/style.md`.

Gate A is the focused checks, actually run. Gate B is your style-lens read with
nothing above Low left open. Report `done` only when both pass. When the
developer says "review it", spawn `reviewer` with the `style` lens.

**Stop and promote to `/task` when the change touches money, authentication,
authorization, a migration, concurrency, or an externally visible contract, or
when it grows past a few lines.** Say why you promoted it.

Write no spec and no `.claude/specs/` entry.
