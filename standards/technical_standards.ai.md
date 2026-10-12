# Technical Standards — Engineering conventions every change must satisfy

> **MUST-READ before you write ANY implementation plan or design**, together with
> [django_standards.ai.md](django_standards.ai.md) — no implementation plan may be written in a session where
> both files have not been loaded into context. These are seven engineering standards for new code in a large,
> high-write service. Read this file, then the touched directory's `README.ai.md` and `INVARIANTS.human.md` when
> they exist.
>
> **Companion standards (each loads when its stage begins):** Python language style →
> [python_code_style.ai.md](python_code_style.ai.md); Django logic & architecture →
> [django_standards.ai.md](django_standards.ai.md); implementation mechanics (tests, migrations, i18n, admin,
> metrics, alerting, deployment) → [implementation_standards.ai.md](implementation_standards.ai.md).

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable). It DESCRIBES standards and the shapes that satisfy
> them; it does not restate per-app invariants (those live in each directory's `INVARIANTS.human.md`). When a
> standard and the code disagree, the code is authoritative — open an issue, do not silently weaken the standard.

## Why this exists

The standards assume a high-write Django monolith on one primary MySQL/MariaDB database with read replicas,
deployed as many Kubernetes releases. At that scale a single careless migration, an unbounded table, or an N+1 in a
hot path degrades the whole platform. These standards keep new code from regressing production health. Teams on
another database or deploy shape keep the rule and adapt the mechanism.

---

## TS-1 — Database migrations must avoid downtime

**Standard.** A schema migration must not require downtime. If the design genuinely cannot avoid a
downtime-bearing migration, three things are mandatory and must be written into the architecture document for that
change:
1. The migration's measured duration, determined by a test against a production-sized dataset.
2. A defined, tested recovery/rollback scenario.
3. Both of the above recorded in the architecture/design doc reviewed before the change ships.

**The avoidable operations that cause downtime migrations on MySQL/MariaDB — and their safe alternative:**

| Avoidable operation | Why it locks / breaks | Safe alternative |
|---|---|---|
| Add a **non-nullable** column | `ALTER TABLE ... ADD COLUMN ... NOT NULL` without a default rewrites/locks the table on large tables and fails mid-deploy while old code still inserts | Split into three migrations: (a) add the column **nullable**, (b) backfill in batches, (c) set `NOT NULL` once backfilled |
| Add a column with **any constraint** (unique, check, FK) | Constraint validation scans/locks the whole table | Add the bare column first; add the constraint later, off the hot path, or as a validated background step |
| Add a **ForeignKey without `db_constraint=False`** | Creating the physical FK constraint takes a metadata lock and an implicit index build on large tables | Declare the FK with `db_constraint=False` (the ORM relation works, no physical constraint is created) |
| **Change a column's type** | In-place type change rewrites every row under lock | Add a **new column**, migrate data from the old to the new in batches, switch readers/writers, then drop the old column |
| **Rename a column** on a large table | Pending writes against the old name fail mid-deploy | Avoid on large tables; if unavoidable, add the new column, dual-write, backfill, then drop — keep the old name as an alias during the transition |
| Add an **index** on a large table | Index build can hold a lock for minutes | Schedule in a maintenance window / online-DDL strategy; flag it in the migration MR |
| Add a **unique constraint** on a large table | Validation scans the whole table under lock | Same as index; validate off the hot path |

**Shapes that satisfy it.**
- New FKs to business models declare `db_constraint=False` (and `on_delete=models.DO_NOTHING`).
- An additive column is either nullable, or has both a `default` and `null=True` (the belt-and-suspenders form).
- A ledger or balance table changes only additively: destructive renames break in-flight rows that still carry the
  old shape.

**Known-large tables.** Keep a list of them in the repository (users/accounts, orders, trades, wallet transactions,
API logs, notifications, and every append-only history table are typical members). Treat every operation above as
downtime-bearing on them.

**Enforcement.** Migration MRs are reviewed against this checklist. Migration safety is a review responsibility, not
a CI gate. Author one migration per app per MR; never edit an already-deployed migration (it desyncs replicas).

---

## TS-2 — Do not grow the main database

**Standard.** The architecture must not grow the **main** (`default`) database. A table that is potentially large
must live in a non-main database. Choose the destination by purpose:

| Non-main DB alias | Purpose |
|---|---|
| `analytics` | analytics / reporting / daily snapshots |
| `messages` | notifications / messaging |
| `history` | historical / archival records |
| `accounting` | reconciliation / accounting records |
| a domain alias | high-volume data owned by one domain |

**How routing works.** A model declares two class attributes and a database router does the rest:
- `db_for_read` returns `read_db_alias or write_db_alias`
- `db_for_write` returns `write_db_alias`
- `allow_migrate` confines the model's migration to its `write_db_alias` (and otherwise to `default`).

```python
class MyLargeLog(BaseModel):
    # ... fields ...
    write_db_alias = 'analytics'   # writes + migration go here
    read_db_alias = 'analytics'    # reads go here
```

A model with **no** alias attributes lives on `default` — so adding a high-volume table without these attributes
silently grows the main DB. That is the failure this standard prevents.

**If data must land on the main DB** (sometimes unavoidable for transactional integrity), the design must define a
**lifecycle process that periodically drains the table** — see TS-3.

---

## TS-3 — Aggressively growing data needs a retention solution

**Standard.** Any process that grows data aggressively must ship, as part of its design, a periodic
cleanup / archival / compaction / retention mechanism. "We'll clean it later" is not acceptable; the retention job
is part of the feature.

**Retention patterns to reuse:**
- **Time-windowed batch delete.** A scheduled job deletes rows older than N days in id-batches (10,000 is a sane
  start), as a cron script or a Celery beat task.
- **Load-adaptive batch delete.** For a hot table, chunk the delete and **back off when the database is busy** (for
  example when MySQL `Threads_running` exceeds a threshold), so the purge never starves live traffic.
- **Blob / media cleanup.** Delete stored files of records that reached a terminal state more than N days ago.
- **Scratch-table clear.** Reconciliation scratch tables are cleared on each run.

**Counter-example to avoid.** Orders and trades that are *copied* to a data warehouse for analytics but never evicted
from the operational database keep growing forever. That is how tables land on the known-large list (TS-1), where
every schema change becomes downtime-bearing. Do not add another table in this shape without a real retention plan.

**Enforcement.** Review responsibility; no automated gate.

---

## TS-4 — Heavy-table reads must hit a read replica

**Standard.** Read queries against heavy tables (trades, orders, ledger history, and other high-volume/append-only
tables) must be served from a **read replica**, not the primary, unless correctness requires fresh state.

**Two mechanisms (pick the right one):**
1. **Pinned per-model alias** — for a model that lives entirely on a non-main DB, set `read_db_alias` /
   `write_db_alias` (TS-2) and all ORM access is routed automatically; no `.using()` needed.
2. **Explicit replica fan-out** — for a model on the `default` DB that stays on the primary for writes, route the
   read through one helper, for example `get_read_db()`:
   ```python
   from db.utils import get_read_db
   Trade.objects.using(alias=get_read_db()).filter(market=market).order_by('-id')[:50]
   ```
   `get_read_db()` returns a random alias from `settings.REPLICA_DATABASES`, with one replica as the fallback.

**Typical call sites.** Feeds of recent trades, portfolio and trade-list reads, fraud-detection counts, and
order-history reads.

**CRITICAL caveat — replicas are asynchronous.** Never read a replica to make a **mutation or correctness
decision**: replication lag means the row may be stale, and a balance/ledger decision on stale data corrupts state.
For any read-then-write where freshness matters, use the **write DB** or a locked row (`select_for_update`). This is
a hard financial invariant. Cron jobs must not use replica reads for mutation decisions.

**Enforcement.** Review responsibility; reviewers check every change to the router and the replica helper. No
automated gate.

---

## TS-5 — Queries must be optimized; eliminate N+1

**Standard.** Queries must be optimized. The most common offense is the N+1 query — iterating a queryset and
touching a related object per row. Eliminate it:
- Use **`select_related(...)`** for forward `ForeignKey` / `OneToOne` relations (a SQL join).
- Use **`prefetch_related(...)`** (optionally with `Prefetch(...)`) for `ManyToMany` and reverse-FK relations (a
  second batched query).

**Shapes in hot paths.**
- A trade-list view — `.select_related("market", "maker_order", "taker_order", "maker", "taker")` before
  serializing the list.
- A recent-trades endpoint — `Trade.objects.select_related("taker_order")...`.
- A borrow/repay history — `.prefetch_related(Prefetch("currency"), Prefetch("pair__base_currency"),
  Prefetch("pair__quote_currency"), ...)` to fold a whole relation tree into a bounded number of queries.
- A liquidation scan — `...select_related("pair").prefetch_related("trigger_prices")`.

**Enforcement.** There is **no** CI/lint gate for N+1 — it is a review responsibility and an author responsibility.
A lookup such as `Currency.objects.get(symbol=...)` inside a loop is the classic case. When adding a list endpoint or
a batch job, inspect the generated SQL (e.g. with `assertNumQueries` in a test or `django-debug-toolbar` locally)
before shipping.

---

## TS-6 — Long-running jobs rely on a health-check DB engine, not manual connection management

**Standard.** A long-lived process (root script, infinite loop, standalone daemon, consumer) must **not** hand-roll
Django DB connection recovery — no `close_old_connections()` sprinkled through the loop, no manual
`connection.close()` before each query, no reconnect helper. Stale/dropped MySQL connections are handled once, by a
**health-check DB engine** that every deployment inherits.

**How it works.** A setting such as `DB_ENGINE` selects the backend (`mysql` or `mysql-with-health-check`). The
health-check backend wraps `CursorWrapper.execute`: it catches `OperationalError`, and if the error code is one of
the "connection is gone" codes — `4031` (disconnected for inactivity), `2006` (server has gone away), `2013` (lost
connection during query), `2055` (lost connection reading auth packet) — it closes, reconnects and re-executes, up
to a small retry count (3).

**Turn it on by default.** Set `DB_ENGINE: "mysql-with-health-check"` in the shared default environment that every
release inherits, so a new long-running job normally needs **no** DB config at all.

**What you must do:**
- Do **not** add `close_old_connections()` / manual reconnect logic to a loop. It is redundant, and it hides which
  layer actually owns recovery.
- **Do** confirm your deployment inherits `DB_ENGINE`. If a release overrides it to plain `mysql`, or does not
  inherit the shared defaults, set the health-check engine in that release's values rather than compensating in
  Python.
- A query that still fails after the backend's retries is a real outage: let it raise. Cache-and-continue is fine when
  the job can genuinely proceed on slightly stale data (say so in a comment); otherwise raise and let the pod die so
  Kubernetes surfaces it.

**Enforcement.** Review responsibility; no automated gate. Older loop scripts that still call
`close_old_connections()` are not a licence to add more.

---

## TS-7 — A new Helm values file must be wired into its deploy script, on the main branch

**Standard.** Adding a `values-<name>.yaml` does **not** deploy anything when rollout is manual and the deploy
script only rolls out releases it knows about. A new Helm release needs a script entry: a
`helm upgrade --install …` invocation plus whatever function and dispatch entry the script uses. A values file with
no script entry is dead weight: the feature merges, looks shipped, and never runs.

**Deployment changes ship through the main branch.** When the Helm files, the deploy script and the charts live on
the main branch, and a deploy branch receives them because the deployer merges main into it at deploy time, that
merge is the deployer's step, not the feature author's. Do not open a separate MR against the deploy branch: it
duplicates content that was going to arrive anyway.

**A deploy branch is a deploy-time snapshot, not a running mirror.** Between deploys the main branch runs ahead, so
it is normally *not* an ancestor of the deploy branch, and the commit counts are never zero. That is the healthy
steady state. What matters is that your merged commit reaches the deploy branch at the next deploy.

**The exception: a deploy branch that does not inherit from main.** A staging branch with its own script and its own
values layout gets nothing from main, so a staging rollout needs its own MR on that branch. Check with
`git merge-base --is-ancestor origin/<main> origin/<staging-branch>`.

**Three things make this easy to get wrong:**
1. **The stale belief that the deploy sources live on the deploy branch.** Author on the main branch.
2. **Two environments, two values paths.** When production and staging read values from different paths, copying a
   production entry verbatim into the staging script points at a path that does not exist on that branch.
3. **The main-branch MR merges looking complete.** If CI validates neither script, a values file with no rollout entry
   passes every gate. Whoever adds the values file owns the script entry in the same MR, and owns the paired staging
   MR when the release must run on staging.

**Exempt — passive additions:** a file nothing rolls out on its own (a vendored sub-chart pulled in by an existing
release, a values fragment merged into an already-wired release, a non-production/example file). If adding it does
not create a new release, no script entry is required.

This restates, from the planning/design side, the "Deployment" rule in
[implementation_standards.ai.md](implementation_standards.ai.md).

**Enforcement.** Review responsibility; no automated gate in either direction.

---

## How these standards are enforced (be honest about the gaps)

| Standard | Automated gate? | Enforcement path |
|---|---|---|
| TS-1 migrations | No | Migration-review pass + this doc; one migration/app/MR; never edit deployed migrations |
| TS-2 main-DB growth | No | Review; per-model `read_db_alias`/`write_db_alias` |
| TS-3 retention | No | Review; design-time requirement |
| TS-4 replica reads | No | Review + the read-after-write financial invariant |
| TS-5 N+1 | No | Review + author self-check (`assertNumQueries`) |
| TS-6 health-check DB engine | No | Review; `DB_ENGINE` inherited from the shared defaults |
| TS-7 Helm → deploy scripts | No | Review; wire the deploy script on the main branch; a staging branch that does not inherit from main needs its own MR |

None of these has a deterministic CI check by default. They are upheld by code review and by this document being
**required reading before development**. If a team adds automated checks (a migration linter, an N+1 test helper, a
main-DB-table guard), record them here.

## Related

- [python_code_style.ai.md](python_code_style.ai.md) — Python language style (load before writing code).
- [django_standards.ai.md](django_standards.ai.md) — Django logic & architecture (load with this file before
  planning/design).
- [implementation_standards.ai.md](implementation_standards.ai.md) — tests, migration/i18n checklists, admin
  registration, metrics, alerting, deployment (load before implementation-stage artifacts).
