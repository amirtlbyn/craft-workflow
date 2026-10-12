# Java Standards — backend services on the JVM with Spring Boot

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for craft-workflow 0.7. It applies when
> `bin/craft-stack` detects the `java` stack. The engineering standards TS-1 to TS-5 of
> [technical_standards.ai.md](technical_standards.ai.md) apply to any database a Java service owns. A team that
> adopts this file can rename it to `.human.md` to make it human-owned.

## Layers

- `controller` → `service` → `repository`. A controller calls services only. A service owns its transaction.
- DTOs are `record`s. Entities never leave the service layer.
- Constructor injection with `final` fields. No field injection.

## Transactions

- `@Transactional` on public service methods. Self-invocation skips the proxy: the boundary goes on the method the
  other bean calls.
- `readOnly = true` on read paths.
- `rollbackFor` when a checked exception must roll back.
- No network call, message publish, or long computation inside a transaction. Publish after commit, or through an
  outbox table.

## JPA

- Every association is `LAZY`. Fetch joins or `@EntityGraph` per use case.
- `spring.jpa.open-in-view=false`.
- Pagination with `Pageable` and a maximum page size.
- Money under concurrency: `@Version` with a retry, `@Lock(PESSIMISTIC_WRITE)`, or an atomic `@Modifying` update
  with the guard in its `WHERE`.

## Values

- Money is `BigDecimal` with an explicit scale and `RoundingMode`, compared with `compareTo`. Or a `long` of minor
  units. Never `double`.
- `Optional` only as a return type.
- `Instant` or `OffsetDateTime` for time, in UTC. No `java.util.Date`.

## Validation and errors

- Bean Validation on request DTOs, triggered by `@Valid` at the controller.
- One `@RestControllerAdvice` maps domain exceptions to the repository's error body.

## Migrations

- Flyway or Liquibase. An applied migration is never edited.
- `ddl-auto` is `validate` or `none` outside local development.
- TS-1 applies: additive first, backfill in batches, destructive steps in a later deploy.

## Concurrency

- The model comes from `bin/craft-stack concurrency`: thread-per-request, virtual threads, or reactive.
- Executors are beans, bounded, and named. `@Async` names its executor.
- No `parallelStream()` for I/O. No unbounded cached thread pool. No `.block()` in reactive code.

## HTTP clients

- One client bean per partner (`RestClient`, `WebClient`, or the repository's client), with connect and read
  timeouts.
- Retries only for idempotent calls, with backoff and a total budget.

## Logging

- SLF4J with parameters (`log.info("debit {} {}", walletId, amount)`), never string concatenation.
- No secrets or full card numbers in logs.

## Tests

- JUnit 5. `@DisplayName` starts with the criterion ID.
- Slice tests for one layer. `@SpringBootTest` for flows.
- Testcontainers for the database. No H2 for code that depends on locks or the SQL dialect.
- No `Thread.sleep` in tests. `CountDownLatch`, `CyclicBarrier`, or Awaitility.
