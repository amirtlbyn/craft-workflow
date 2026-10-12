# Node Standards — backend services on Node.js and TypeScript

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for craft-workflow 0.7. It applies when
> `bin/craft-stack` detects the `node` stack. The engineering standards TS-1 to TS-5 of
> [technical_standards.ai.md](technical_standards.ai.md) apply to any database a Node service owns. A team that
> adopts this file can rename it to `.human.md` to make it human-owned.

## TypeScript

- `strict: true`, `noUncheckedIndexedAccess` where the repository has it.
- No `any` in new code. `unknown` with a narrowing check. No `!` to silence the compiler.
- Types for boundary data are inferred from one schema.

## Layers

- Route handler or controller → service → repository or ORM. A handler validates, calls one service, shapes the
  response.
- One error middleware or exception filter maps domain errors to HTTP.

## Validation

- Every body, query, param, and header that the code reads is validated at the edge with a schema.
- Config is validated once at startup. The process refuses to start with a missing value.

## Async

- No floating promises: every promise is awaited, returned, or owned. Lint enforces
  `@typescript-eslint/no-floating-promises`.
- `Promise.all` over a bounded batch, or a limiter with a number.
- Every outbound call has a timeout (`AbortSignal.timeout(ms)` or the client's option).
- No sync I/O or sync crypto on a request path.
- CPU-bound work runs in the worker pool the service already has, or a queue.

## Data access

- Prisma, TypeORM, Drizzle, Knex, or the repository's own layer. Select the fields and relations a use case needs.
- Paginate with a maximum `take` or `limit`.
- Raw SQL only through parameterized tagged templates.
- Transactions are short. No outbound call inside one.
- Migrations through the ORM's tool, reviewed by hand. TS-1 applies.

## Money

- An integer of minor units, or a decimal library. Never a floating-point `number` for amounts.
- A balance changes under a row lock or an atomic guarded update. An in-process mutex guards one process only.

## Security

- Helmet (or the framework's equivalent), CORS from config, a body size limit.
- Authentication and authorization are middleware or guards, never an `if` inside a handler.
- Object-level checks scope every query to the requesting user.
- No secrets in logs, responses, or error messages.

## Logging

- Structured logging (pino or the repository's logger) with a request id.

## Tests

- Vitest, Jest, or `node:test`, as the repository has.
- The criterion ID is first in the test name.
- Fake timers for time. A real database in a container for queries and locks.
- `--detectOpenHandles` (Jest) or an explicit teardown that closes servers, pools, and timers.

## Tooling

- ESLint (or Biome) and Prettier with the repository's config. `tsc --noEmit` in Gate A when a `tsconfig.json`
  exists.
