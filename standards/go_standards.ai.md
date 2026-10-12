# Go Standards — backend services written in Go

> **Scope & ownership:** factual `*.ai.md` (bot-maintainable), written for craft-workflow 0.7. It applies when
> `bin/craft-stack` detects the `go` stack. The engineering standards TS-1 to TS-5 of
> [technical_standards.ai.md](technical_standards.ai.md) apply to any database a Go service owns. A team that adopts
> this file can rename it to `.human.md` to make it human-owned.

## Layout

- `cmd/<binary>/main.go` wires configuration, dependencies, the root context, and shutdown. No business logic.
- `internal/<domain>/` holds the code. A package is named for what it provides. No `util`, `common`, or `helpers`.
- No package-level mutable state. No `init()` that does I/O or reads the environment.

## Errors

- Errors are values. Wrap once per layer with `%w` and a short context: `fmt.Errorf("debit wallet %d: %w", id, err)`.
- Callers branch with `errors.Is` and `errors.As`. Never `==` on a wrapped error. Never a string match.
- An error is handled once: logged or returned.
- `panic` only for a programmer error that must stop the process.

## Interfaces

- Declared by the consumer, with the methods it uses. Constructors return concrete types.
- One implementation and no test substitute means no interface.

## Context

- `ctx context.Context` is the first parameter of every function that does I/O or blocks.
- No context in a struct field, except a type that lives for one request.
- `context.Background()` only in `main`, tests, and a worker's root.

## Concurrency

The `go-concurrency` skill holds the rules. In short: every goroutine has an owner, a stop path, and a bound.
`go test -race ./...` is part of Gate A for any package that starts goroutines or shares memory.

## Data access

- `database/sql` (or `pgx`), `sqlc`, or the ORM the repository already uses. Parameterized queries only.
- `rows.Close()` deferred, `rows.Err()` checked.
- `tx.Rollback()` deferred right after `BeginTx`. Commit at the end.
- The pool is configured: `SetMaxOpenConns`, `SetMaxIdleConns`, `SetConnMaxLifetime`.
- Migrations are versioned SQL files with a down step. TS-1 applies.

## Money

- An `int64` of minor units, or the decimal type the repository uses. Never `float64`.
- A balance changes through one function, under a row lock or an atomic `UPDATE ... WHERE balance >= $1`.

## HTTP

- One `http.Client` per partner, created at startup, with a `Timeout` and a tuned `Transport`.
- Handlers decode, validate, call a service, encode. Request bodies are size-limited with `http.MaxBytesReader`.
- The server sets `ReadHeaderTimeout`, `ReadTimeout`, `WriteTimeout`, and `IdleTimeout`.

## Logging and metrics

- `log/slog` with structured keys, `InfoContext`/`ErrorContext` to carry the request id.
- No secrets, tokens, or full card numbers in logs.

## Tests

- Table-driven, with `t.Run`. The criterion ID is first in the subtest name or the comment above the test.
- A real database in a container for queries and locks.
- `goleak` in `TestMain` for packages with goroutines.
- `testing/synctest` (Go 1.25) for code that waits on time.

## Tooling

- `gofmt` (or `gofumpt` when configured), `go vet`, and `golangci-lint` with the repository's config.
- `go mod tidy` leaves `go.mod` and `go.sum` unchanged in CI.
