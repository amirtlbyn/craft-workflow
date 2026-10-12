<!-- ═══════════════════════════════════════════════════════════════
     A team that adopts this file should take ownership of it: rename it
     to django_standards.human.md (and update config/workflow.md). The
     craft hooks then refuse any agent edit to it.

     ▸ While it is human-owned, a coding assistant must NOT edit it
       inline. In its reply to the developer it states (a) the exact
       fragment(s) to add or change and (b) the exact file and location
       for each, and the developer applies them.
     ═══════════════════════════════════════════════════════════════ -->

# Django Standards — logic & architecture rules for planning and design

> **MUST-READ before you write ANY implementation plan or design**, together with
> [technical_standards.ai.md](technical_standards.ai.md). No implementation plan may be written in a session where
> both files have not been loaded into context, and every finished plan must be reviewed against them before it is
> presented. These are the Django-specific logic gotchas — how business logic is layered, how the ORM/DRF are used,
> how transactions and settings-driven configuration work — the decisions a plan has to get right *before* any code
> is written.

> **Companion standards (each loads when its stage begins):**
> - Python language style (formatting, imports, naming, typing, OOP) →
>   [python_code_style.ai.md](python_code_style.ai.md) — read before writing any Python code.
> - Implementation-stage mechanics (tests, migrations, i18n workflow, admin/permission-group registration, metrics,
>   alerting, deployment wiring) → [implementation_standards.ai.md](implementation_standards.ai.md).
> - The engineering standards (downtime-free migrations, don't grow the main DB, retention, replica routing, N+1,
>   long-running jobs, deploy wiring) → [technical_standards.ai.md](technical_standards.ai.md).

> **Audience vs. ownership.** The **reader is the AI/developer** about to plan or design a change — this guide
> exists to be consumed before development. Once a team makes it **human-owned** (`*.human.md`), only humans change
> it, and **only by explicit human request** — never from automatic AI detection. Coding assistants then may only
> *flag* a suggested change for a human to apply. When a convention and the code disagree, the code is authoritative
> — open an issue, do not silently weaken the convention.

---

## Configuration and business constants

Configuration flows through Django settings, not env reads scattered in business
logic.

- Read configuration via `django.conf.settings`, not by calling `os.environ` /
  `os.getenv` inside business code. `<project>/settings.py` is the single place
  the environment is read; app code references `settings.<NAME>`.
- **No hardcoded business constants.** Any numeric/string constant for a
  business rule (rates, costs, limits, thresholds) is defined in `settings.py`
  and referenced via `settings.<NAME>` — never inlined in a model/service
  method, even if used once. **Exception — per-tier config**: values that vary
  by subscription tier are DB-driven (stored on the plan's JSON/config and read
  via the tier's own helpers like `get_commission_rate`/`get_limit`) so admins
  change them without a deploy.

```python
# <project>/settings.py — the one definition site.
MAX_DAILY_WITHDRAWAL = Decimal("...")

# wallet/services.py — referenced via settings, never re-hardcoded.
if amount > settings.MAX_DAILY_WITHDRAWAL:
    raise WithdrawLimitExceeded()
```

- Constant **placement/naming** (`UPPER_SNAKE_CASE` at the top of the
  file/class) is a language-style rule — see
  [python_code_style.ai.md](python_code_style.ai.md) "Constants and module
  globals".

---

## Django logic and style

Rules for a Django codebase, each with the shape it takes.

- **Prefer custom serializers over DRF serializers.** Hand-rolled serializers
  give explicit control over the output shape. Keep one shared base (e.g.
  `utils/serializers.py` `BaseCustomSerializer`) and subclass it per resource.
  DRF `ModelSerializer` may still appear in older code but is not the default
  for new code.

- **Avoid N+1 in API views** — use `select_related` (FK/1:1) and
  `prefetch_related` (reverse/M2M), e.g.
  `.select_related('market__base_currency', 'market__quote_currency')` or
  `.select_related('market').prefetch_related('trigger_prices')`. **Do not
  abuse it** — a few extra queries can be more robust than forcing one huge
  join; prefetch the relations you actually use, not everything. (This is
  engineering standard **TS-5** — see
  [technical_standards.ai.md](technical_standards.ai.md) for the full statement
  and the replica-read companion TS-4.)

- **ForeignKey `on_delete` + `db_constraint`**: default to
  `on_delete=models.DO_NOTHING` with `db_constraint=False`. Rationale: no
  DB-level foreign-key constraint means the database never auto-cascades or
  auto-restricts on delete, and avoids the row/index locks those constraints
  take — a common source of lock contention and deadlocks under load. Deletion
  edge cases are handled **manually in application code** instead. Never use
  `CASCADE` for business models (silent data loss). The same FK fields then
  carry these settings into the generated migration automatically. (This is
  engineering standard **TS-1** for FKs — see
  [technical_standards.ai.md](technical_standards.ai.md).)

- **Default ordering**: do NOT set `ordering = ["-id"]` in `Meta` — Django
  already orders by `id`. Only set `ordering` when you need something different.

- **Choice fields**: always back with `TextChoices`/`IntegerChoices`, never raw
  strings. Prefer `TextChoices` — except when the value is used directly in
  logic or an external API call (then the string value carries meaning). With
  `IntegerChoices`, always display the **label**, not the numeric value, in
  admin and logging.

- **State/constant lists** live as `@staticmethod` getters inside the relevant
  Choices class, not as class-level constants on the model (e.g.
  `TicketState.get_final_states()`, `OrderState.get_active_states()`).

- **i18n — no hardcoded user-facing strings.** All user/API-visible text
  (exceptions, error responses, validation) uses `gettext_lazy as _` with a key
  name; English lives in `locale/en/LC_MESSAGES/django.po` (plus one directory
  per supported language). Prefer raising a translatable exception class over
  returning `{"error": _("Key")}` — keep one base (e.g.
  `BaseTranslationException`) whose subclasses set
  `translated_message = _('...')`. The `.po`/`.mo` workflow and the `#, fuzzy`
  rule are in the **i18n reviewer checklist** in
  [implementation_standards.ai.md](implementation_standards.ai.md).

- **Celery tasks are thin triggers** — the task fetches the object and calls a
  model/service method; no business logic in the task body. Good:
  `execute_trigger_price_task` → `trigger_price.execute()`; `notify_user_task`
  → `Message.notify_user()`. Anti-pattern: a task that computes balances, calls
  providers, and writes rows itself.

- **No fat views.** A view parses the request, calls a service/model method, and
  returns the response. If a view exceeds ~10 lines of logic, extract. Good:
  `TransferView.create()` → `TransferRequest.deposit(...)`.

- **Logic lives in the service layer — avoid fat models.** Business logic
  (queries, calculations, decisions, orchestration) belongs in service/manager
  classes, not piled onto model methods or views. Models stay thin (fields,
  simple accessors, light invariants) and delegate to the service. Shape: an
  app's `model_managers/` package holds `OrderManager`, `TransferRequestManager`,
  `TradeManager`; views, Celery tasks, and models call into these managers
  rather than holding the logic themselves.

- **Transactions (`transaction.atomic`)** — keep atomic blocks small and clean:
  - **No fat atomic blocks.** Wrap only the minimal set of writes that must
    commit together; do not put unrelated work, queries, or computation inside.
  - **No atomic-in-atomic.** Do not nest `transaction.atomic()` inside another
    atomic block (nesting creates savepoints and hides the real boundary);
    structure the code so there is one clear outermost transaction.
  - **No API/network calls inside atomic.** Never call an external service / HTTP
    API while holding a transaction — it pins a DB connection and holds row locks
    for the entire round-trip, causing contention and deadlocks. Do the I/O
    before/after, or queue it via `transaction.on_commit(...)`.
  - **Do not use db-level decorators at all.** Never decorate a function with
    `@transaction.atomic` (or similar db-level decorators) — the decorator wraps
    the *entire* function in one transaction, a fat atomic block by construction.
    Always use an explicit `with transaction.atomic():` block scoping exactly the
    critical section.

- **Migrations**: one migration per app per MR, schema-only (no data scripts).
  Full rules in the **Migrations reviewer checklist** in
  [implementation_standards.ai.md](implementation_standards.ai.md), and the
  downtime-safety standard in [technical_standards.ai.md](technical_standards.ai.md)
  (TS-1).

---

## Related

- [python_code_style.ai.md](python_code_style.ai.md) — Python language style.
- [implementation_standards.ai.md](implementation_standards.ai.md) — tests, migration/i18n checklists, admin
  registration, metrics, alerting, deployment.
- [technical_standards.ai.md](technical_standards.ai.md) — the engineering standards.
