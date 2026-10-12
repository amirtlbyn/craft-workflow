---
name: node-practices
description: "Node.js and TypeScript backend practices for implementation and review: strict TypeScript, schema validation at the boundary (zod or the framework's pipes), thin controllers or routes with a service layer, no floating promises, AbortSignal timeouts, money as integer minor units or a decimal library, Prisma/TypeORM/Drizzle query discipline, and tests that name the criterion ID. Load it for JavaScript or TypeScript backend changes, Express, Fastify, NestJS, or Next.js route handlers."
---

# node-practices

First read `package.json` (runtime, framework, test runner, lint and format
scripts), `tsconfig.json`, and two neighbouring modules. Follow what is there.

`standards/node_standards.ai.md` holds the detail:
`bin/craft-std node_standards --list`.

## TypeScript

- `strict: true`. No `any` in new code: `unknown` and a narrowing check
  instead. No non-null assertion (`!`) to silence the compiler.
- Types for data that crosses a boundary come from one schema
  (`z.infer<typeof Schema>`), not a hand-written interface beside it.

## Boundaries

- Validate every request body, query, and header at the edge with a schema
  (zod, valibot, class-validator pipes in NestJS, Fastify's JSON schema).
  Reject unknown fields where the repository does.
- Controllers or route handlers stay thin. Services own rules. Repositories or
  the ORM layer own queries.
- One error middleware or exception filter maps domain errors to HTTP.

## Promises

- Every promise is awaited, returned, or handed to an owner that awaits it.
  `@typescript-eslint/no-floating-promises` enforces it. A floating promise
  loses its error and outlives the request.
- `Promise.all` over a bounded batch, or `p-limit` with a number. Never over an
  array the caller sized.
- `Promise.allSettled` when each item may fail on its own.
- Every outbound call has a timeout: `fetch(url, { signal:
  AbortSignal.timeout(5000) })`, or the client's own timeout option.
- No sync I/O on a request path: `readFileSync`, `execSync`, `crypto.pbkdf2Sync`.
  They block every request in the process.

## Data

- Money is an integer of minor units (`bigint` or a safe `number` range), or a
  decimal library (`decimal.js`, `big.js`), or Prisma's `Decimal`. Never a
  plain floating-point `number` for amounts.
- Select only the fields you need, `include` only the relations a use case
  reads, and paginate with a maximum `take`.
- Transactions: `prisma.$transaction(async (tx) => ...)`, a TypeORM
  `QueryRunner`, or Drizzle's `db.transaction`. No outbound call inside one.
- Money under concurrency: a row lock (`SELECT ... FOR UPDATE` through
  `$queryRaw` with parameters), or an atomic update with a guard in its
  `WHERE`. An in-process mutex guards one process only.
- Raw SQL through tagged templates (`Prisma.sql`, `sql\`\``), never string
  concatenation.
- Migrations through the ORM's migration tool, reviewed by hand before they
  run. `technical_standards` TS-1 applies.

## Configuration and logging

- Config read and validated once at startup (a schema over `process.env`). The
  process refuses to start with a missing value.
- Structured logging (pino or the repository's logger), with a request id.
  Never log tokens, passwords, or full card numbers.

## Tests

- The repository's runner: Vitest, Jest, or `node:test`.
- The criterion ID first in the test name: `it('PAY-3: given ..., when ...,
  then ...', ...)`.
- Fake timers for time, not real waits. A real database (a container) for
  queries and locks.
- Jest: `--detectOpenHandles` once, to catch a server or a timer left open.

## Before finishing

Run lint, format, `tsc --noEmit`, and the tests through `bin/craft-check`.
Read the diff for: a floating promise, an unbounded `Promise.all`, a fetch
without a timeout, `number` money, sync I/O on a request path, an unvalidated
body, and SQL built by concatenation.
