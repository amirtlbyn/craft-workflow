# Go — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the Go equivalent below.

## style

- Item 2 (typing): exported identifiers have doc comments that start with the name. Errors are the last return
  value. Receivers are short and consistent.
- Item 6 (framework idiom): `ctx` first, errors wrapped with `%w`, small consumer-side interfaces, no `util`
  package, no package-level mutable state.
- Formatting belongs to `gofmt` and the linter, not to this lens.

## logic

- Item 3 (money): `int64` minor units or the repository's decimal type. `float64` money is High.
- Item 5 (transactions): `BeginTx(ctx, ...)`, `defer tx.Rollback()`, no outbound call before `Commit`.
- Errors: an ignored error on a write path is High. `errors.Is` and `errors.As`, never `==` on a wrapped error.

## security

- Item 5 (injection): SQL is parameterized (`$1`, `?`). `fmt.Sprintf` into SQL is Critical.
- Item 7: every `http.Client` has a `Timeout`. `http.DefaultClient` on a partner call is Medium.
- The server sets `ReadHeaderTimeout`. Request bodies are bounded with `http.MaxBytesReader`.

## query

- Index evidence: a `CREATE INDEX` in a migration file, or the schema file `sqlc` reads. Quote it with
  `file:line`.
- N+1: a query inside a loop over rows. Batch with `= ANY($1)` or a join.
- `rows.Close()` deferred and `rows.Err()` checked. A missing one leaks a pooled connection: Medium.

## concurrency

- Load `go-concurrency` and walk its "Review" list as items 3 to 10.
- A `go` statement with no owner, no stop path, or no bound is High.
- `go test -race ./...` is in the recorded checks of this session. Missing on a diff that adds a goroutine: item 11
  at Medium.
