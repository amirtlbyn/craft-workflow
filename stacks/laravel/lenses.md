# Laravel — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the Laravel equivalent
below.

## style

- Item 6 (framework idiom): thin controllers, a `FormRequest` for validation, an API Resource for output, services
  or actions for rules. No query in a Blade view or a route closure.
- Item 2 (typing): `declare(strict_types=1)`, parameter and return types, no untyped array as a domain object.

## logic

- Item 3 (money): integer minor units, `brick/money`, or `bcmath`. A `float` amount, or a `decimal` cast to float,
  is High.
- Item 5 (transactions): `DB::transaction` stays short, with no `Http` call, mail, or queue dispatch inside.
  Dispatch after commit (`afterCommit`).
- Item 6 (concurrency): `lockForUpdate()` inside a transaction, or an atomic `update` with a guard in the `where`,
  protects a balance.

## security

- Item 8 (input): `$request->validated()`, never `$request->all()`. Mass assignment is guarded by `$fillable`;
  `$guarded = []` on a model that takes user input is High.
- Item 5 (injection): `DB::raw`, `whereRaw`, `orderByRaw` with user input and no bindings is Critical.
- Authorization through a policy, gate, or `authorize()`, never an `if` in the controller. Scope queries to the
  user.
- Item 7: every `Http::` call has `timeout()`. A user-influenced URL is checked against an allow-list.

## query

- Index evidence: `->index()` or `->unique()` in a migration. Quote it with `file:line`.
- N+1: a relation read inside a loop. Use `with()` or `load()`; check `preventLazyLoading`.
- Boundedness: `paginate()`, `chunkById()`, `cursor()`, or `lazy()` on every large list. `->get()` on a growing
  table is High.

## concurrency

- A slow call in the request cycle belongs in a queued job (Horizon). A job is idempotent and has `$tries` and a
  `timeout`.
- Under Octane, a static property, a singleton, or a binding that holds the request leaks between requests.
- `Http::pool` has a bounded size and a timeout.
