---
name: validation-discipline
description: "Decide which validation to write, and at which layer. Load before you add a check, a guard clause, a serializer validator, a raise, or a database constraint. Use it to stop speculative, redundant, or defensive validation, and to keep the checks that protect security, money, data integrity, and explicit contracts."
---

# validation-discipline

Load this skill with `python-style`, and with `django-practices` for Django work. It decides
**which** validation to write. `python-style` and `django-practices` decide **how** to write
it. Repository standards win over this skill when they are more specific.

## The rule

Add validation when it protects a security boundary, a business invariant, a
data-integrity requirement, a resource-safety requirement, or an explicit
contract. Do not add validation that is speculative, redundant, defensive, or
already guaranteed by the framework.

The goal is not less validation. The goal is the correct validation, in one
place, owned by the correct layer.

This skill shares a principle with `test-discipline`:
**do not maximize code. Maximize confidence per line of code.**

---

## Step 1 — Answer these before you write the check

Answer these for each validation you consider. Keep the answers short. Skip the
step for a check that a repository standard already requires.

1. Which invariant does this protect?
2. Who can violate the invariant? Name the caller or the input source.
3. What happens when the invariant is violated?
4. Is the consequence security-sensitive?
5. Is the consequence data-integrity-sensitive?
6. Is the consequence business-critical?
7. Is this an explicit product requirement or API contract?
8. Which layer owns this invariant?
9. Is the invariant already enforced somewhere else? Name the file and line.
10. Is the scenario realistic, or only imaginable?
11. What is the simplest mechanism that enforces it?

**If you cannot name the invariant, there is no validation to write.**

---

## Step 2 — Classify the validation

| Class | Meaning | Action |
|---|---|---|
| **REQUIRED** | Security, data integrity, a critical business rule, an explicit contract, or system safety | Implement |
| **USEFUL** | Prevents a real failure or gives clearly better behavior | Implement when the complexity is justified |
| **DEFENSIVE** | Possibly useful, but not clearly necessary at this layer | Implement only with a concrete written justification |
| **REDUNDANT** | Already guaranteed by another layer | Do not implement |
| **SPECULATIVE** | Based on hypothetical future misuse or an unlikely scenario | Do not implement |

A DEFENSIVE check needs a justification that names the caller, the failure, and
the cost of the failure. "It is safer" is not a justification.

---

## Step 3 — Put the check in the layer that owns the invariant

Each invariant has one owner. Enforce it there.

| Layer | It owns |
|---|---|
| Authentication and authorization | Identity, permissions, `trader.can.<action>()` |
| API or request boundary | Shape, type, and range of untrusted external input |
| Serializer or form | Field-level input rules for one endpoint |
| Service or business layer | Business rules, state transitions, cross-object invariants |
| Model | Small local invariants and field constraints |
| Database constraint | Uniqueness, and structural rules that must survive every code path |
| Framework | Routing, type coercion, field parsing, decorator gates |

Do not repeat the same check in two layers. Repeat it only when you can name a
second entry point that misses the first check, or when the second layer must
hold under a race. Write that reason in a comment.

### Trust these. Do not re-check them

- Framework guarantees. A parsed URL parameter, a resolved view, and a decorator
  gate already hold.
- An authenticated request context. `request.user` is present after the auth
  layer ran.
- Validated serializer input. The service layer receives clean fields.
- Database constraints, including `unique_together` and `NOT NULL`.
- An established internal function contract. A private helper may trust its
  caller inside the same module.
- Type and structure guarantees that an earlier boundary established.

In this Django codebase, `@api_access_required` on HTTP views is a CI-enforced
gate. Do not re-implement its check inside the view body.

---

## Not sufficient reasons to add validation

Reject the validation when the only argument is one of these:

- The input could theoretically be malformed.
- Another developer could theoretically misuse an internal function.
- A malicious caller could theoretically send something strange.
- Python could theoretically receive the wrong type.
- The database could theoretically return unexpected data.
- Defensive programming sounds safer.
- Best practice suggests it.
- An edge case is imaginable.
- You cannot prove the edge case is impossible.

A theoretical failure is not a justification. Require evidence, an explicit
contract, or a named consequence.

---

## Keep these five ideas separate

Agents add unnecessary code because they merge these. They are different things.

- **Validation** rejects bad input at a boundary.
- **Error handling** decides what happens after an operation fails.
- **Invariant enforcement** keeps stored state correct, often with a constraint,
  a lock, or a transaction.
- **Authorization** decides who may act.
- **Framework behavior** is the platform's own guarantee.

The fact that an exception is possible does not justify a validation. Ask
whether an invariant is at risk. When the correct answer is a transaction
boundary, a lock, an idempotency key, or a database constraint, use that. Do not
add an `if` statement instead.

---

## This skill does not permit under-validation

Always implement these. They are REQUIRED by default:

- Authorization and permission checks on every new entry point.
- Financial amounts: sign, precision, `Decimal` type, currency, and limits read
  from `settings`.
- Idempotency keys on every operation that moves money or calls a provider.
- Uniqueness that the data model depends on. Use `Meta.unique_together`.
- State-machine transitions. Reject a transition from an invalid source state.
- Limits that bound resource use: page size, batch size, and query range.
- Every field of untrusted external input at the outermost boundary.

When you remove or skip a check in one of these areas, say so in your report and
name the layer that now owns it.

---

## Report what you decided

On the `task` and `project` routes, this block goes into the "Validation
decisions" section of `spec.md`, before approval, so the developer sees what you
chose not to check. On `quick`, and for a check you find you need during
implementation, add it to your report:

```
Validation decisions
- <invariant> — REQUIRED — enforced in <layer>, <file>:<line>
- <invariant> — REDUNDANT — already enforced by <file>:<line>, not added
- <invariant> — SPECULATIVE — no named caller can violate it, not added
```

Keep the block to the meaningful checks. Do not list every field rule that a
serializer already covers.

---

## Related

- `python-style` — Python style, exceptions, typing, and naming.
- `django-practices` — boundaries, ORM correctness, transactions, and Celery.
- `test-discipline` — the same reasoning for tests.
- `standards/python_code_style.ai.md` — Python style.
- `standards/django_standards.ai.md` — layering, service-layer logic, and
  settings-driven constants. This is where the layer-ownership rules come from.
- Optional host-repository documents, read only when present:
  `aidocs/INVARIANTS.human.md` for the invariants the codebase already states,
  and `aidocs/code_review_playbook.ai.md` for the financial-safety checks.
