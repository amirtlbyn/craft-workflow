<!-- ═══════════════════════════════════════════════════════════════
     A team that adopts this file should take ownership of it: rename it
     to implementation_standards.human.md (and update config/workflow.md).
     The craft hooks then refuse any agent edit to it.

     ▸ While it is human-owned, a coding assistant must NOT edit it
       inline. In its reply to the developer it states (a) the exact
       fragment(s) to add or change and (b) the exact file and location
       for each, and the developer applies them.
     ═══════════════════════════════════════════════════════════════ -->

# Implementation Standards — rules for the implementation stage

> **MUST-READ before you produce any implementation-stage artifact:** writing unit tests, generating a migration,
> adding i18n strings, registering a new model (admin + permission group), adding metrics/alerting, or wiring a
> deployment. No such artifact may be produced in a session where this file has not been loaded into context, and
> the result must be checked against the relevant checklist below before it is finalized. These rules govern the
> *mechanics* of shipping a change — the reviewer checklists an MR is judged against.

> **Companion standards (each loads when its stage begins):**
> - Python language style → [python_code_style.ai.md](python_code_style.ai.md) — read before writing any
>   Python code.
> - Django & logic architecture (serializers, ORM/DRF, transactions, service layer, settings-driven constants) →
>   [django_standards.ai.md](django_standards.ai.md) — read before planning/design.
> - The engineering standards → [technical_standards.ai.md](technical_standards.ai.md).

> **Audience vs. ownership.** The **reader is the AI/developer** implementing a change — this guide exists to be
> consumed at implementation time. Once a team makes it **human-owned** (`*.human.md`), only humans change it, and
> **only by explicit human request** — never from automatic AI detection. Coding assistants then may only *flag* a
> suggested change for a human to apply. When a convention and the code disagree, the code is authoritative — open
> an issue, do not silently weaken the convention.

---

## Tests

These rules assume **unittest via Django's test framework** — `django.test.TestCase`
/ `TransactionTestCase`, and DRF's `APITestCase` / `APIClient` for API tests.

- Place tests in the app's `tests.py` or a `tests/` package; name files
  `test_*.py`.
- Use `TestCase` for DB tests (wrapped in a transaction, rolled back) and
  `TransactionTestCase` when the test must commit / span transactions. Use
  `APITestCase` for endpoint tests.
- Test class names match the unit and end in `Test`/`TestCase`; methods start
  with `test_`; prefer `test_<method_under_test>_<state>`.
- Structure bodies **given → when → then**. For parametrized cases use
  `subTest` (table-driven). Provision/clean up fixtures in `setUp()`/`tearDown()`.
- `assert` is acceptable in tests (it is only forbidden in application logic).
- No `if __name__ == "__main__"` guard is needed — the Django test runner
  discovers test classes.
- **Assert behavior, not implementation.** Tests must assert observable
  interface behavior — return values, persisted state, raised exceptions — not
  implementation details such as which internal helper ran, the exact
  `service_name` string passed to an alert, or internal call wiring. Prefer
  asserting the outcome over mocking-and-asserting-the-call. Reason: a test
  bound to internals breaks under a behavior-preserving refactor even though the
  externally-observable behavior is unchanged, which makes it brittle and
  eventually flaky and discourages safe refactoring.

```python
from django.test import TestCase

class ThrowDiceTest(TestCase):
    def test_throw_dice_boundary_probabilities(self) -> None:
        for case in (
            {"name": "always_false", "prob": 0.0, "expected": False},
            {"name": "always_true", "prob": 1.0, "expected": True},
        ):
            with self.subTest(name=case["name"]):
                # given
                prob = case["prob"]
                expected = case["expected"]

                # when
                got = throw_dice(prob=prob)

                # then
                self.assertEqual(got, expected)
```

### Tests are DAMP, not DRY

Test code is **not** production code and is not optimized the same way.
Production code follows **DRY** (Don't Repeat Yourself) — duplication is
abstracted behind functions. Tests follow **DAMP** (Descriptive And Meaningful
Phrases): a test's job is to tell a clear story the reader understands from the
test body *alone*, without chasing a dozen helpers to reconstruct what is set up
and asserted. When a test fails at 2am, the on-call engineer must see what broke
immediately. A little repetition is acceptable — even good — when it keeps each
test self-contained.

- **Don't put logic in tests.** No conditionals, loops, or computation in a
  test or its helpers. The moment a helper computes the expected result it can
  re-derive it with the *same* logic the production code uses — so the same bug
  lives in both places and the test passes while being wrong. Humans are bad at
  spotting bugs inside logic; prefer straight-line code and hardcoded literals
  over computed values.

  ```python
  # bad — recomputes the expected value with the code-under-test's own formula
  expected = base + "?" + query
  assert create_uri(base, query) == expected

  # good — hardcode the literal you expect
  assert create_uri("http://google.com/search", "q=cat") == "http://google.com/search?q=cat"
  ```

- **Construction helpers are fine; validation helpers are not.** Helpers that
  *build* test data (fixtures, object factories) are encouraged. What you avoid
  is the **shared validation helper** — a `validate_account(account)` /
  `assert_pnl(...)`-style method called from many tests. These start innocent
  then accrete conditional checks over time (each caller needs a slightly
  different subset), until no one can tell what any individual test actually
  verifies — the helper itself grows enough logic that it arguably needs its own
  tests. Inline the assertions instead so each test states its own expected
  values. If a helper makes the test *less* clear about its inputs, outputs, and
  the single behavior it checks, prefer the redundancy.

  Anti-pattern: an `assert_pnl(...)` helper that guards every assertion behind
  `if average_entry_price:`, is reused across `test_open_short_...` /
  `test_open_long_...` / `test_multiple_orders_...`, and computes the expected
  `price` with the same weighted-average formula the production code uses. Good
  DAMP shape: each test charges accounts with hardcoded `Decimal` literals and
  asserts a hardcoded `call_count` inline, fully self-contained.

- **Helpers and constructors take their salient values as call-site
  arguments.** A construction/setup helper must expose the values that matter to
  the test as explicit arguments passed *at the call site*, so the reader sees
  the inputs inline in the test body. A **no-argument helper that hides the data
  and the logic inside itself — `create_test_orders()`, `setup_scenario()` — is
  forbidden**: the reader cannot tell what was created, or with what amounts /
  sides / states, without opening the helper. Pass the price/amount/side/state
  the test actually depends on as arguments; let the helper default only the
  irrelevant boilerplate. Prefer
  `create_order(trader, btc_usd, side=Sell, amount=Decimal("0.001"), price=Decimal("65000"))`
  over `create_test_sell_order()`, and
  `create_trade_for_order(order, [(Decimal("0.001"), Decimal("65000"))])` over a
  helper that picks the fills itself — every value the test reasons about is
  visible at the call site, not buried in the helper. (Building data with
  explicit args is good; the shared validation helper is the part to avoid.)

---

## Admin registration

- **Admin classes**: always subclass the project's shared admin base (e.g.
  `BaseAdmin` / `BaseAdminWithActions` in `utils/`), never plain
  `admin.ModelAdmin`.

- **Every new model must be registered in admin AND granted access in a
  permission group.** Two steps, both mandatory when a model is added:
  1. Register the model in its app's `admin.py` with `@admin.register(Model)` on
     a `BaseAdmin` subclass (see the rule above).
  2. Grant **view** access to it by adding the model to the permission group
     that owns its product surface (for example, the group's `models_class`
     list, which grants `view` by default; `add`/`change` stay opt-in on the
     maintainer groups). Reason: a model registered in admin but absent from
     every group is invisible to all non-superuser staff — operators silently
     cannot see it.

---

## Alerting

- When calling the alerting helpers (e.g. `alert_request` /
  `periodic_alert_request` and their async variants), pass `server_name`,
  `service_name`, and `timeout` as **literal values inline at the call site**.
  Do not hoist them into class-level constants, module-level variables, or
  function parameters. Reason: when an alert fires in production, the on-call
  engineer greps the codebase for the `service_name` string and must land on the
  exact line that raised it — indirection through a constant or a parameter
  breaks that lookup.

---

## Metrics (Prometheus)

Rules for white-box Prometheus metrics. Keep the how-to (delivery models, the
infinitely-running-job pattern, a code template) next to the metrics module,
for example in `utils/README.ai.md`; the rules below are mandatory.

- **Always go through one `MetricsFactory`** (e.g. `utils/prometheus.py`).
  Never instantiate `prometheus_client` `Counter`/`Gauge`/`Histogram`/`Summary`
  directly. The factory returns a `NoOpMetric` when metrics are disabled, so call
  sites need no `if enabled:` guards — `.inc()`/`.set()`/`.observe()` are always
  safe.
- **Define metric objects once, at module level.** Declare them in an app-level
  `metrics.py`, never inside a function, request handler, or loop body. Call
  sites only update them. Re-creating a metric per call/iteration is a bug.
- **Pick the delivery model by where the code runs**, not by preference:
  - **Scrape** (web/ASGI pods) — use the multiprocess scrape registry exposed at
    the metrics endpoint.
  - **Push** (non-web Celery workers, cron jobs, and any infinitely-running /
    standalone daemon) — give the job its **own** `CollectorRegistry` and a
    `MetricsFactory(job_name=..., grouping_key=...)`, then push to the
    Pushgateway. A standalone loop cannot be scraped, so it **must** push.
- **Push targets need a unique `instance` in `grouping_key` per replica.**
  `push_sync`/`push` overwrite everything under `job + grouping_key`; two
  replicas sharing a grouping_key clobber each other on the gateway.
- **Pushing is a third-party HTTP call** — it obeys the third-party rules: never
  inside a `transaction.atomic()` block, and it relies on the factory's built-in
  request timeout (don't strip it). Use the factory's `push*`/`delete*` methods;
  never hand-roll the Pushgateway HTTP request.
- **Prefer `push_sync()` for standalone daemons.** Use an async `push()` (one
  that enqueues a push task on a metrics Celery queue) only from inside a
  Celery-backed context where a worker will drain the queue.

---

## Reviewer checklists

Mandatory checks when finalizing or reviewing an MR against the latest main
branch (`master` below).

### Migrations

1. **Fetch latest master**: `git fetch origin master`; check which migrations
   exist on `origin/master`.
2. **No dangling dependencies**: every migration's `dependencies` must reference
   migrations that exist on `origin/master`, not local-only ones from another
   branch.
3. **No duplicate numbering**: new migration numbers must not conflict with
   master's.
4. **Single migration per app per MR**: at most one new migration per Django
   app. If you already pushed one and then change the same app's models again,
   delete and regenerate it — do not stack a sequential migration.
5. **Applies cleanly**: operations must be valid for the current model state.
6. **No data scripts**: REJECT any migration with `RunPython`/`RunSQL` that
   inserts, updates, or deletes rows — schema operations only (`AddField`,
   `AlterField`, `CreateModel`, `RemoveField`, index/constraint changes). Django
   **management commands are also forbidden** for this — do not put data
   seeding/mutation in `management/commands/`. Instead, write it as an
   **operator-run script** in the project's script runner — for example a
   `Script` model that maps a script name to a method:
   - Add the logic as a method on the `Script` model:
     `def <script_name>(self, use_celery, **params)`.
   - Register it by name: add `"<script_name>": "<method_name>"` to the name →
     method map, and create its `Script` row (with a description) in the
     runner's initialization.
   - An operator runs it explicitly after deploy (admin action). Dispatch is by
     name, synchronously or on Celery, and every run is tracked in a run log
     with its status and kill support.
   The only in-migration exception is a schema-only backfill (e.g. populating a
   new NOT NULL column from existing columns), called out explicitly in the MR
   description.
7. **FK fields have no DB constraint**: every new/altered `ForeignKey` (and the
   migration it generates) must use `on_delete=models.DO_NOTHING` and
   `db_constraint=False`. Reject `CASCADE` and any FK that creates a DB-level
   constraint. See the ForeignKey rule in
   [django_standards.ai.md](django_standards.ai.md) "Django logic and
   style", and engineering standard TS-1 in
   [technical_standards.ai.md](technical_standards.ai.md).

### i18n

1. **No hardcoded user-facing strings**: all error/exception/response text uses
   `_("KeyName")` — never English in Python. (See the i18n principle in
   [django_standards.ai.md](django_standards.ai.md) "Django logic and
   style".)
2. **`.po` files updated**: new/changed `_()` strings update the `.po` files of
   every supported locale (via `makemessages`).
3. **`.mo` files compiled**: committed alongside `.po` (via `compilemessages`).
4. **English translations present**: every new `msgid` has a non-empty `msgstr`
   in the English locale.
5. **No fuzzy entries**: `.po` files MUST NOT contain `#, fuzzy` markers — Django
   ignores them. If `makemessages` adds them, remove before committing.

---

## Deployment

These rules assume a manual production deploy through one deploy script that
assembles a `helm upgrade --install` command per release, with the deploy
sources (Helm values files, charts, the script, and the deploy CI file) on the
main branch.

**Author deployment changes on the main branch.** If a deploy branch is only a
snapshot of the main branch that the deployer merges at release time, do not
open a separate MR against it — that merge is the deployer's release step, and
the main branch running ahead of the deploy branch between deploys is the
normal state. A branch that does **not** inherit from main (for example a
staging deploy branch with its own script) does need its own MR. See
[technical_standards.ai.md](technical_standards.ai.md) TS-7.

- **A new Helm release must be wired into the deploy script.** When you add a
  deployment Helm file (a new `values-<name>.yaml` / leaf values file or chart)
  that is meant to run **in production** and is **not a passive addition**, you
  must also add its rollout to the deploy script: the `helm upgrade --install`
  invocation plus whatever function and dispatch entry the script uses. A values
  file with no entry in the script is **never deployed** — the manual deploy
  path only rolls out releases the script knows about.
  - **Passive addition (exempt):** a file that nothing rolls out on its own —
    e.g. a vendored sub-chart only pulled in by an existing release, a values
    fragment merged into an already-wired release, or a non-production/example
    file. If adding it does not create a new production release, no script entry
    is required.

---

## Related

- [python_code_style.ai.md](python_code_style.ai.md) — Python language style.
- [django_standards.ai.md](django_standards.ai.md) — Django logic & architecture (planning-stage).
- [technical_standards.ai.md](technical_standards.ai.md) — the engineering standards.
