---
name: spec
description: "Write, approve, and change the spec that drives a task or project: problem, non-goals, EARS acceptance criteria, invariants, contracts, and risk tier. Use it when the user runs /spec, when the craft router picks the task or project route, when a request needs acceptance criteria before code, or when implementation shows that an approved spec is wrong."
---

# spec — the source of truth for a change

This workflow is **spec-driven**. On the `task` and `project` routes, nobody
writes code or tests until the developer approves a spec. After approval, the
spec is the contract: the tests prove it, the review checks the code against it,
and the gates are derived from it.

The spec states **what** and **why**. It never states **how**. The how lives in
the code, and on the project route in `design.md`.

A spec is also the cheapest context there is. A fresh session, a subagent, or a
reviewer reads one page instead of re-exploring the repository. Write it so that
a reader with no history can act on it.

---

## Step 1 — Create the spec directory

The plugin root is two directories above this skill's base directory.
`"${CLAUDE_PLUGIN_ROOT}"` holds it when the host sets that variable.

```bash
<plugin root>/bin/craft-spec new --route task --title "Daily withdrawal limit per tier" \
    --checkpoint "docker compose exec web pytest apps/wallet -q"
```

This writes `.claude/specs/<date>-<slug>/` from the templates, sets
`.claude/specs/ACTIVE`, and starts the craft session with the route and the
checkpoint. From now on the spec gate is shut: no file outside `.claude/` can be
written until the spec is approved. Use `--route project` for the project route.
It also creates `design.md`.

`--key` sets the ID prefix for acceptance criteria, for example `--key WDL`.
Use the ticket key when the team has one. The default is the initials of the
title.

## Step 2 — Learn just enough

Read the code the change touches, its callers, and the tests that already cover
it. Search for existing tests before you propose a criterion. Read the touched
directories' `README.ai.md` and `INVARIANTS.human.md` when they exist.

Stop reading when you can fill every section. The spec is not a design review.

## Step 3 — Write `spec.md`

Fill the template. Delete each template comment when you fill its section.

**Problem.** Two to four sentences. Say who is affected and how we know.

**Non-goals.** List what this change will not do. Every non-goal removes one way
to overbuild, and the reviewer's `spec` lens checks that each one held.

**Acceptance criteria.** One observable behavior per row, in EARS form. Use the
pattern that fits:

| Pattern | Shape |
|---|---|
| Ubiquitous | THE `<component>` SHALL `<response>`. |
| Event | WHEN `<trigger>`, THE `<component>` SHALL `<response>`. |
| State | WHILE `<state>`, THE `<component>` SHALL `<response>`. |
| Unwanted | IF `<condition>`, THEN THE `<component>` SHALL `<response>`. |
| Optional | WHERE `<feature is enabled>`, THE `<component>` SHALL `<response>`. |

Rules for a criterion:

- It is observable from outside the unit: a return value, a stored row, a state
  transition, a response, an emitted event. "Uses `select_for_update`" is not a
  criterion. It is an invariant mechanism or a design choice.
- It gets exactly one test. That test puts the ID in its docstring, for example
  `"""WDL-2: Given ..., when ..., then ...."""`. `bin/craft-spec trace` finds it.
- It has a class and a failure story. Use the classes of `test-discipline`:
  CRITICAL BEHAVIOR, BUSINESS RULE, SECURITY BOUNDARY, IMPORTANT FAILURE MODE,
  REGRESSION, INTEGRATION CONTRACT. A behavior with no realistic failure story
  goes under "Not tested, and why", with its class.
- Money, authorization, idempotency, concurrency, and state transitions that
  the change touches always get a criterion. "Minimal" never means "none".

**Invariants.** State that must hold on every code path. Name the owning layer
and the mechanism. The `logic` lens and `deep-reviewer` check each one.

**Contracts.** Every externally visible change. Write `None.` when there is none.

**Validation decisions.** Apply `validation-discipline` when the change adds a
check. Keep only the meaningful lines.

**Standards that apply.** Name the sections, not the files. Run
`bin/craft-std --list` to see the names. Add the checkpoint command from
`config/workflow.md` §6.

**Risk.** Set `Risk: high` in the header when the change touches money,
authentication, authorization, a migration, concurrency, or an external
integration. The risk tier decides whether `deep-reviewer` runs.

**Size.** A task spec fits on one screen: usually two to seven criteria. A longer
list means the request is a project, or the criteria test implementation.

See `examples/withdrawal-limit.spec.md` for a finished task spec.

## Step 4 — Check the spec before you show it

- [ ] Every criterion is observable, testable, and has a failure story.
- [ ] No criterion describes an implementation detail.
- [ ] Every non-goal is a real temptation, not filler.
- [ ] The risk tier matches the rule above.
- [ ] Every open question is decided, or its assumption is written.
- [ ] The checkpoint command is the real one.
- [ ] Every standards section named exists in `bin/craft-std --list`.

## Step 5 — Present it and stop

Show the developer the criteria table, the "Not tested, and why" list, the
non-goals, the risk tier, and the open questions. Give the path of the file for
the rest. Do not paste the whole file. Then ask for one of:

- **approve** — the spec is the contract.
- **cut** — name the IDs to drop.
- **add** or **change** — in any form, including one line of Persian or English.

A criterion the developer adds is **REQUIRED**. Mark it `[developer]` in its row.
Do not argue it down. When you think it duplicates an existing test, say so in
one line and keep it unless they withdraw it.

Do not write code or tests while you wait. Silence is not approval.

## Step 6 — Record the approval

After the developer says approve, and only then:

```bash
<plugin root>/bin/craft-approve
```

It records the SHA-256 of the active `spec.md` and opens the spec gate. It also
appends the approval to `log.md`. The approval survives a new session, so work
can resume after a usage-limit reset without a second approval.

On the project route, run `/plan` next. On the task route, fill `tasks.md` with
a short checklist and implement.

---

## Spec deltas — when the code shows the spec is wrong

The spec is anchored, not frozen. When implementation shows a criterion is
wrong, missing, or impossible:

1. Stop. Do not build the unapproved behavior, and do not quietly leave a
   criterion unimplemented.
2. Show the delta: the rows to add, change, or remove, and why, in three lines
   or fewer.
3. After the developer approves, edit `spec.md`, append a `spec delta` entry to
   `log.md`, and run `bin/craft-approve` again. The gate was shut from the
   moment `spec.md` changed.

A delta that removes a MUST-class criterion needs the developer's words, not a
silence.

## What this skill will not do

- It will not write code before the spec is approved.
- It will not put state, progress, or test names into `spec.md`. They change,
  and every change to `spec.md` closes the gate.
- It will not record an approval the developer did not give.
- It will not edit a `*.human.md` document.

## Related

- `test-discipline` — the classes, and the audit after the tests exist.
- `validation-discipline` — which checks deserve a line in the spec.
- `planner` — turns an approved project spec into `design.md` and `tasks.md`.
- `review-protocol` — the `spec` lens that checks code against this file.
