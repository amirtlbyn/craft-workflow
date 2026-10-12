# Java — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the Spring equivalent
below.

## style

- Item 6 (framework idiom): constructor injection, `record` DTOs, no entity returned from a controller, one
  `@RestControllerAdvice`.
- Item 2 (typing): `Optional` only as a return type. No raw types.

## logic

- Item 5 (transactions): `@Transactional` on a public method of another bean (self-invocation skips the proxy), no
  network call inside, `rollbackFor` for checked exceptions that must roll back.
- Item 3 (money): `BigDecimal` with scale and `RoundingMode`, compared with `compareTo`. `double` money is High.
- Item 6 (concurrency): `@Version`, `PESSIMISTIC_WRITE`, or a guarded `@Modifying` update protects a balance.

## security

- Item 4 (access decorator): every new endpoint is covered by the security filter chain or a method-security
  annotation. A `permitAll()` added to a new path needs a justification in the spec.
- Item 5 (injection): JPQL and native queries use parameters. String concatenation into a query is Critical.
- Item 6: no secret in `application.yml` committed to the repository.

## query

- Index evidence: `@Index` in `@Table`, `@Column(unique = true)`, or `CREATE INDEX` in a Flyway or Liquibase
  migration. Quote it with `file:line`.
- N+1: a lazy association read in a loop or in a DTO mapper. Fetch join or `@EntityGraph`.
- Boundedness: `Pageable` with a maximum size. `findAll()` on a growing table is High.

## concurrency

- The model is in `bin/craft-stack concurrency`. Reactive types in an MVC service, `parallelStream()` for I/O, an
  unbounded executor, or `@Async` with no named executor is item 1 or 5 at High.
- `.block()` inside reactive code is item 7 at High.
- Tests use latches or Awaitility, never `Thread.sleep`.
