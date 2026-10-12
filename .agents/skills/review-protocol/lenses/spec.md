# Lens: spec — does the diff do what the spec says, and only that

- **Ceiling:** High
- **Minimum confidence:** 0.7
- **Reads:** `spec.md` in full, `design.md` when present. No standards.

This lens is the reason the workflow is spec-driven. The other lenses ask "is
this code good". This one asks "is this the code we agreed to build".

On the project route, items 1 to 3 cover the criteria the session lists on its
`Covers:` line in `tasks.md`. A criterion of a later session is not a gap yet.

## Checklist — answer every item

1. **Criteria implemented** — for every acceptance criterion, name the
   `file:line` that implements it. A criterion with no implementation is a
   `fail` at High.
2. **Criteria tested** — for every criterion, name the test that carries its ID
   in the docstring, and say whether the test asserts the criterion's observable
   response. A test that names the ID but asserts something else is a `fail`.
3. **One test per criterion** — no criterion has two tests, and no new test
   serves no criterion. An orphan test is a finding at Low: it needs a spec
   delta or removal.
4. **Nothing extra** — the diff adds no behavior the spec does not state: no new
   endpoint, field, setting, flag, retry, or fallback outside the criteria and
   the design. Unrequested behavior is a finding at Medium. At High when it
   changes an external contract.
5. **Non-goals held** — for every non-goal, say whether the diff respects it.
   A violated non-goal is a finding at High.
6. **Invariants have a mechanism** — for every invariant, name the constraint,
   lock, transaction, or check in the diff that enforces it, as the spec says.
   Correctness of that mechanism belongs to the `logic` lens.
7. **Contracts match** — every change to an external contract in the diff is
   listed under "Contracts" in the spec, with the same shape.
8. **Spec still true** — nothing in the diff shows that the spec is wrong. When
   it does, report it as a finding titled `Spec delta needed`, at Medium, and
   say which row.

## Severity

**High** — a criterion not implemented or not tested, a violated non-goal, an
unlisted contract change. **Medium** — unrequested behavior, a test that does
not assert its criterion. **Low** — an orphan test, an ID missing from a
docstring when the test is otherwise correct.
