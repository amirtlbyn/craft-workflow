---
name: go-practices
description: "Go backend practices for implementation and review: package layout, errors wrapped with %w and checked with errors.Is/As, small interfaces declared by the consumer, context as the first parameter, slog structured logging, database/sql or sqlc access, money as integer minor units, table-driven tests with subtests. Load it for Go changes. Load go-concurrency as well before any goroutine, channel, or shared state."
---

# go-practices

First read `go.mod` (the Go version decides which features exist), the
repository's `.golangci.yml`, and two neighbouring packages. Follow what is
there.

`standards/go_standards.ai.md` holds the detail:
`bin/craft-std go_standards --list`.

## Layout

- Packages are named for what they provide (`wallet`, `ledger`), not for what
  they are (`utils`, `common`, `models`). No package named `util`.
- `internal/` for code no other module may import. `cmd/<binary>/main.go` only
  wires: config, dependencies, the root context, shutdown.
- No package-level mutable state. No `init()` that does I/O.

## Errors

- Return errors. Do not panic for an expected failure.
- Wrap with context, once per layer: `fmt.Errorf("debit wallet %d: %w", id, err)`.
- Compare with `errors.Is(err, ErrInsufficientFunds)` and `errors.As`, never
  with `==` on a wrapped error or with `strings.Contains(err.Error(), ...)`.
- Sentinel errors for conditions callers branch on: `var ErrNotFound =
  errors.New("not found")`. A typed error when callers need fields.
- Handle an error once: log it or return it, not both.
- Every `err` is checked. `errcheck` in golangci-lint enforces it.

## Interfaces

- Declare an interface where it is used, with the methods that user needs.
  Return concrete types.
- No interface with one implementation "for testing" unless a test really
  substitutes it.

## Context and I/O

- `ctx context.Context` first, on every function that does I/O.
- `http.NewRequestWithContext`, `db.QueryContext`, `rows.Close()` deferred,
  `rows.Err()` checked after the loop.
- Every HTTP client has a timeout: `&http.Client{Timeout: 5 * time.Second}`,
  created once and reused. `http.DefaultClient` has none.

## Data

- `database/sql` with a driver, or `sqlc`-generated queries, or the ORM the
  repository already uses. Parameterized queries only: `$1`, never `fmt.Sprintf`
  into SQL.
- Transactions: `tx, err := db.BeginTx(ctx, nil)`, `defer tx.Rollback()`, then
  `tx.Commit()`. The deferred rollback is a no-op after commit.
- Money is `int64` minor units, or a decimal type (`shopspring/decimal`,
  `cockroachdb/apd`) where the repository uses one. Never `float64`.
- Migrations are versioned SQL files (golang-migrate, goose, atlas). Each has
  a down step or a written reason it cannot.

## Logging

`log/slog` with key-value pairs: `slog.InfoContext(ctx, "debit", "wallet_id",
id, "amount_minor", amount)`. No `fmt.Println` in service code. Never log
secrets, tokens, or full card numbers.

## Tests

- Table-driven tests with `t.Run(tc.name, ...)`. Put the criterion ID first in
  the case name or the comment above the test: `t.Run("WDL-2 resets at
  midnight", ...)`.
- `t.Helper()` in helpers. `t.Cleanup` over `defer` in helpers.
- `testify` only when the repository already uses it. Otherwise `if got !=
  want { t.Fatalf(...) }`.
- A real database (a container) for queries and locks.
- `go test -race ./...` for any package with goroutines.

## Before finishing

Run `gofmt`, `go vet`, and the linter through `bin/craft-check`. Read the diff
for: an ignored error, an error compared with `==`, `float64` money, a missing
`ctx`, a client without a timeout, and SQL built with `Sprintf`.
