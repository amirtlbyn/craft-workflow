# PHP Standards — backend services on Laravel, Symfony, and plain PHP

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for craft-workflow 0.9. It applies when
> `bin/craft-stack` detects the `laravel`, `symfony`, or `php` stack. The engineering standards TS-1 to TS-5 of
> [technical_standards.ai.md](technical_standards.ai.md) apply to any database a PHP service owns. A team that
> adopts this file can rename it to `.human.md` to make it human-owned.

## Language

- `declare(strict_types=1);` in every new file. Typed parameters, returns, and properties.
- PHPStan (Larastan on Laravel) at the repository's level. No new baseline entry to pass a check.

## Layers

- Controller → service → Eloquent model or Doctrine repository. A controller validates, calls one service, shapes
  the response.
- One exception handler maps domain errors to HTTP.

## Validation

- Every request is validated at the edge: `FormRequest` and `validated()`, or a DTO with Validator constraints.
- Config is read from `config()`; `env()` appears only in config files.

## Data access

- Select the columns and relations a use case needs. `with()`, `load()`, or a fetch join against N+1.
- Paginate, or use `chunkById`, `cursor`, or `toIterable` for large sets.
- Mass assignment is guarded by `$fillable`.
- SQL takes bound parameters. No user input in `DB::raw`, `whereRaw`, DQL strings, or a PDO statement string.
- Transactions are short. No outbound call, mail, or dispatch inside one. Migrations are reviewed by hand. TS-1
  applies.

## Money

- An integer of minor units, `brick/money`, or `bcmath`. Never a `float` for amounts.
- A balance changes under `lockForUpdate`, `PESSIMISTIC_WRITE`, or an atomic guarded update.

## Security

- Authorization through policies, gates, Voters, or `#[IsGranted]`, never an `if` inside a controller.
- Object-level checks scope every query to the requesting user.
- Passwords use `password_hash`. No secrets in logs, responses, or error messages.
- No `eval`, `unserialize` on user data, or shell call with user input.

## Async and workers

- Slow work runs in a queue (Laravel queues, Horizon, Symfony Messenger). Jobs are idempotent, with a timeout and a
  retry limit.
- Every outbound call has a timeout. Concurrent calls are bounded.
- Under Octane, RoadRunner, FrankenPHP, or Swoole, no request data in static state, singletons, or bindings.

## Logging

- Structured logging with a request id. No tokens or passwords.

## Tests

- Pest or PHPUnit, as the repository has. The criterion ID is first in the test title.
- A real database for queries and locks. Fake the clock and outbound HTTP.

## Tooling

- Pint or PHP-CS-Fixer for format. PHPStan or Psalm for types. Tests through `composer test`, Pest, or PHPUnit.
