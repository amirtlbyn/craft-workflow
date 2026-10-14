# Symfony — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the Symfony equivalent
below.

## style

- Item 6 (framework idiom): thin controllers, a DTO with `#[MapRequestPayload]` and Validator constraints, services
  injected by the constructor, autowiring. No `$container->get()` in a service.
- Item 2 (typing): `declare(strict_types=1)`, typed properties, `readonly` value objects.

## logic

- Item 3 (money): integer minor units, `brick/money`, or `bcmath`. A `float` amount is High.
- Item 5 (transactions): `EntityManager::wrapInTransaction` stays short, with no `HttpClient` call or mail inside.
  Dispatch Messenger messages after the flush.
- Item 6 (concurrency): `LockMode::PESSIMISTIC_WRITE` inside a transaction, or `#[ORM\Version]`, protects a
  balance.

## security

- Item 8 (input): every payload goes through a DTO and Validator constraints before use.
- Item 5 (injection): DQL or `QueryBuilder` with user input concatenated into the string is Critical. Use
  `setParameter`. The same applies to `Connection::executeQuery` without parameters.
- Authorization through Voters, `#[IsGranted]`, or `access_control`, never an `if` in the controller. Scope queries
  to the user.
- Item 7: every `HttpClient` call has `timeout` and `max_duration`. A user-influenced URL is checked against an
  allow-list (`NoPrivateNetworkHttpClient`).

## query

- Index evidence: `#[ORM\Index]`, `#[ORM\UniqueConstraint]`, or `CREATE INDEX` in a migration. Quote it with
  `file:line`.
- N+1: a lazy association read inside a loop. Use a fetch join (`addSelect` with `leftJoin`) or `EXTRA_LAZY`.
- Boundedness: `setMaxResults` or a `Paginator` on every list. `toIterable()` with `clear()` for batches.

## concurrency

- A slow call in the request belongs in a Messenger handler. A handler is idempotent and has a retry strategy.
- Under RoadRunner, FrankenPHP, or Swoole, a service holding request data leaks between requests. Implement
  `ResetInterface`.
- Concurrent `HttpClient` requests are bounded and have a timeout.
