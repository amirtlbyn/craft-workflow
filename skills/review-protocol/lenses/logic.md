# Lens: logic — correctness, money, and the tests that prove it

- **Ceiling:** Critical
- **Minimum confidence:** 0.6
- **Reads:** the spec's invariants and criteria, the diff, the callers and
  states it touches, the touched directories' `README.ai.md` and
  `INVARIANTS.human.md`, and `aidocs/ISSUES.human.md`, when present. Sections
  only when an item needs them:
  `bin/craft-std django_standards "Django logic and style"` for transactions and
  layering, `bin/craft-std implementation Tests Migrations` for test and
  migration mechanics, `bin/craft-std technical TS-1 TS-4` for migrations and
  replica reads. Load `validation-discipline` and `test-discipline` for items 9
  and 10.

Money is this lens's: balance arithmetic, freeze and unfreeze pairing, ledger
consistency, idempotency, and races that cost money. Pure application security
is not: injection, authorization bypass, secret leakage, and crypto misuse
belong to `security`.

**Other stacks.** The items below name Django constructs. On another stack, run
`bin/craft-stack lens logic --paths <changed paths>` and apply its notes in their
place.

## Checklist — answer every item

1. **Requirement** — does the code behave as each criterion states, including
   its boundary? (`spec` checks that it exists. This item checks that it is right.)
2. **Invariants** — does the mechanism for each invariant actually hold it, on
   every code path, including the error path?
3. **Money** — are amounts, units, currency, and rounding correct, with
   `Decimal`, and does every balance change go through the sanctioned path?
4. **Idempotency** — can this run twice without a second effect?
5. **Transactions** — is the atomic block minimal, not nested, and free of any
   network call? Is post-commit work in `transaction.on_commit()`?
6. **Concurrency** — what happens under two concurrent callers, and is the lock
   or uniqueness that prevents it present?
7. **Replica reads** — does any code read its own write from a replica?
8. **Migration** — safe on a large populated table, reversible, and correct
   during a mixed-version deploy?
9. **Validation** — is each added check REQUIRED or USEFUL, at the layer that
   owns the invariant? Redundant or speculative validation is a finding at Low.
   Name the layer that already enforces it.
10. **Tests** — does each test fail before the change, and assert behavior, not
    implementation? Framework-behavior, implementation-detail, and duplicate
    tests are findings at Low. A missing test for money, authorization,
    concurrency, or a state transition is a finding at its consequence.
11. **Change risk** — does a touched directory's checklist name a consequence
    the diff does not address?
