# Node — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the Node equivalent
below.

## style

- Item 2 (typing): no `any`, no non-null assertion to silence the compiler, boundary types inferred from a schema.
- Item 6 (framework idiom): thin handlers or controllers, a service layer, one error filter or middleware.

## logic

- Item 3 (money): integer minor units or a decimal library. A floating-point `number` amount is High.
- Item 5 (transactions): short, no outbound call inside. Prisma interactive transactions have a timeout: keep work
  inside it small.
- A floating promise on a write path is High: its error is lost and it may outlive the request.

## security

- Item 8 (input): every body, query, and param is validated by a schema before use.
- Item 5 (injection): raw SQL through parameterized tagged templates. `$queryRawUnsafe` with user input is
  Critical. No `eval`, `new Function`, or `child_process.exec` with user input.
- Item 7: every `fetch` or client call has a timeout. A user-influenced URL is validated against an allow-list.

## query

- Index evidence: `@@index` or `@unique` in `schema.prisma`, `@Index()` on a TypeORM entity, or `CREATE INDEX` in
  a migration. Quote it with `file:line`.
- N+1: a query inside a loop or a `.map(async ...)`. Use `include`, `in`, or a join.
- Boundedness: `take` or `limit` with a maximum on every list.

## concurrency

- `Promise.all` over input the caller sized is item 5 at High. Use a batch or a limiter.
- Sync I/O or sync crypto on a request path is item 7 at High.
- A promise not awaited, returned, or owned is item 3 at Medium, High when it moves money.
