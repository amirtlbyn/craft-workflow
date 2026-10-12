---
name: minimal-code
description: "Write the least code that satisfies the spec. Load before you write a new function, class, module, helper, or dependency. Use it to stop code nobody asked for: reimplemented stdlib or framework features, speculative abstractions, and new layers where one line would do. It is built for a large, heavily loaded system: it never trades correctness or performance for fewer lines."
---

# minimal-code

Load this skill with `python-style`, and with `django-practices` for Django work.
It decides **whether** to write code. `python-style` and `django-practices`
decide **how**. `validation-discipline` and `test-discipline` apply the same
reasoning to checks and tests. Repository standards win when they are more
specific.

Idea credit: the "laziness ladder" of the open-source `ponytail` plugin
(github.com/DietrichGebert/ponytail). That plugin suits small projects. This
skill is our own version for a large system under heavy load, so it adds
performance and correctness guards and the workflow does not depend on the plugin.

## The rule

The cheapest line is the one you do not write. Every line costs tokens to
write, to review, and to maintain. Write the least code that meets the spec's
acceptance criteria **and** holds up under production load. Do not maximize
code. Maximize behavior per line.

**Fewer lines is never the goal by itself.** Never pick the shorter option when
it is slower, less safe, or less correct at production scale. A longer,
set-based, indexed, or bounded solution beats a short naive one. When the two
conflict, performance and correctness win.

## The ladder — stop at the first rung that works

Before you write new code, go down this list in order. Stop as soon as a rung
solves the problem.

1. **Does it need to exist?** Check the spec. If no acceptance criterion needs
   it, do not write it.
2. **Is it already in this codebase?** Search with `Grep`, `rg`, or `ast-grep`
   for a function, mixin, manager, serializer, or util that already does it.
   Reuse it. Extend it only when the change is small and stays compatible.
3. **Does the standard library do it?** `itertools`, `functools`, `collections`,
   `dataclasses`, `pathlib`, `decimal`, `enum`, `contextlib`.
4. **Does the framework do it?** Django and DRF already give you querysets,
   `F()`/`Q()`, `bulk_create`, `get_or_create`, constraints, signals,
   serializers, permissions, pagination, filters, and Celery options such as
   `autoretry_for`. A native feature beats a hand-written one.
5. **Does an installed dependency do it?** Check `requirements*.txt` or
   `pyproject.toml`. Never add a new dependency without saying so in the report.
6. **Can it be one expression or one line?** A comprehension, a
   `queryset.update()`, a `dict.get()`. Do not build a loop, a class, or a helper
   for it. Never reach for a short form that does more work: a per-row loop
   where one bulk or aggregate query works is longer *and* slower, and a
   comprehension that materializes a large list where a generator or a queryset
   iterator works costs memory.
7. **Only then build the minimum.** Smallest function that meets the criteria,
   in the layer that owns it, with no options nobody asked for.

## Patterns to reject

Reject these unless a criterion in the spec names them:

- A helper, class, or module used exactly once. Inline it.
- A base class, protocol, factory, or strategy with one implementation.
- A parameter, flag, or config value that no caller sets.
- A wrapper that only forwards to another call.
- A re-implementation of something in rungs 2 to 5.
- A generalization for a future case the spec does not mention.
- A new file where an existing module is the right owner.
- A new abstraction. A **query, index, or batch strategy that the load
  requires is not an abstraction**; keep it.
- Code that duplicates a line the framework or database already guarantees.
- Comments, docstrings, and logging beyond what the repository standard
  requires. Follow `skills/asd-ste100/references/card.md`.

## What this skill never removes

Minimal does not mean careless. Always keep, and never count as "extra":

- Authorization and permission checks on every new entry point.
- Money handling: `Decimal`, units, limits from settings, idempotency keys.
- Transactions, locks, and constraints that protect data integrity.
- State-machine transition guards.
- Code that an acceptance criterion, a repository standard, or the spec's
  invariants require.
- Tests that `test-discipline` requires.
- **Performance code on hot or growing paths.** Indexes and migrations that add
  them, `select_related`/`prefetch_related`, `bulk_create`/`bulk_update`,
  `iterator()`, pagination and batch-size bounds, `only()`/`values()` on wide
  tables, caching that the spec or the repository already uses, and narrow lock
  scope. Cutting these to save lines is a defect, not a saving.
- Retry, timeout, idempotency, and back-pressure code around external calls and
  Celery tasks.
- Logging, metrics, and tracing that the repository standard requires.

When the ladder and one of these conflict, the safety or performance code wins.
Say so in the report. When you do not know whether a path is hot, treat it as hot
if it touches a table that grows, a money or order flow, or a Celery task, and
ask `arch-assistant` or the developer in the spec.

## Report what you decided

On `task` and `project`, add this short block to your report. Keep it to the
meaningful decisions, one line each. Skip it for `quick`.

```
Minimal-code decisions
- <need> — reused <file>:<line>, wrote nothing new
- <need> — used <stdlib / framework feature>, wrote nothing new
- <need> — built the minimum: <file>, <N> lines, because rungs 2 to 5 did not fit
```

## Audit and gain

- `/minimal-audit` walks the ladder backwards over existing code and proposes
  deletions. It never edits.
- `/minimal-gain` measures the real diff: lines added and removed, new files,
  new definitions. It reports no percentage, because the unassisted baseline is
  unknown.

## Related

- `python-style`, `django-practices` — how to write the code you decided to write.
- `validation-discipline`, `test-discipline` — the same reasoning for checks and tests.
- `arch-assistant` — when the smallest change still needs a structural opinion.
