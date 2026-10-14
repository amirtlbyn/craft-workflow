# PHP — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the plain PHP equivalent
below.

## style

- Item 6 (framework idiom): a controller or handler parses input, calls one service, and shapes the response. No SQL
  or HTML built in the controller.
- Item 2 (typing): `declare(strict_types=1)`, parameter and return types, PSR-4 autoloading, PSR-12 style.

## logic

- Item 3 (money): integer minor units, `brick/money`, or `bcmath`. A `float` amount is High.
- Item 5 (transactions): `PDO::beginTransaction` with `commit` in the success path and `rollBack` in a `catch`. No
  outbound call inside.
- Item 6 (concurrency): `SELECT ... FOR UPDATE` inside a transaction, or an atomic guarded `UPDATE`, protects a
  balance.

## security

- Item 8 (input): validate `$_GET`, `$_POST`, and the JSON body before use. Cast or check types explicitly.
- Item 5 (injection): a SQL string built with a variable is Critical. Use `prepare` with bound parameters, and
  `PDO::ATTR_EMULATE_PREPARES` off. No `eval`, `unserialize` on user data, or `shell_exec` with user input; escape
  output with `htmlspecialchars`.
- Passwords use `password_hash` and `password_verify`. Compare secrets with `hash_equals`.
- Item 7: every cURL or stream call sets a timeout. A user-influenced URL is checked against an allow-list.

## query

- Index evidence: `CREATE INDEX` or `UNIQUE` in a migration or schema file. Quote it with `file:line`.
- N+1: a query inside a loop. Use a join or `WHERE id IN (...)`.
- Boundedness: `LIMIT` on every list, and a cursor or keyset page for large tables.

## concurrency

- Under PHP-FPM a request shares nothing; the shared state is the database, the cache, and files. Guard it with a
  lock or an atomic statement.
- A slow task belongs in a queue worker, not in the request.
- `pcntl_fork` or `sleep` in a web request is item 7 at High.
