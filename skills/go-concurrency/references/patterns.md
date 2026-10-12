# go-concurrency — patterns

Go 1.22 or newer (each loop iteration has its own variable, so `for _, item :=
range items { g.Go(func() error { use(item) }) }` is safe). `errgroup` and
`semaphore` are in `golang.org/x/sync`, `rate` in `golang.org/x/time`.

## Bounded fan-out with errgroup

The first error cancels `ctx` for the others, and `Wait` returns it.

```go
func (s *QuoteService) QuoteAll(ctx context.Context, symbols []string) ([]Quote, error) {
	if len(symbols) > maxSymbolsPerRequest {
		return nil, ErrTooManySymbols
	}
	quotes := make([]Quote, len(symbols)) // each goroutine writes its own index
	g, ctx := errgroup.WithContext(ctx)
	g.SetLimit(quoteConcurrency) // from the partner's rate limit
	for i, symbol := range symbols {
		g.Go(func() error {
			q, err := s.partner.Quote(ctx, symbol)
			if err != nil {
				return fmt.Errorf("quote %s: %w", symbol, err)
			}
			quotes[i] = q
			return nil
		})
	}
	if err := g.Wait(); err != nil {
		return nil, err
	}
	return quotes, nil
}
```

`g.Go` blocks when `SetLimit` goroutines are running, so the loop itself is the
back-pressure.

## A worker pool for a stream

```go
// Pool runs n workers over jobs until jobs closes or ctx is cancelled.
// The caller owns the pool: it closes jobs and reads results until it closes.
func Pool(ctx context.Context, n int, jobs <-chan Job, work func(context.Context, Job) Result) <-chan Result {
	results := make(chan Result)
	var wg sync.WaitGroup
	for range n {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				select {
				case <-ctx.Done():
					return
				case job, ok := <-jobs:
					if !ok {
						return
					}
					select {
					case results <- work(ctx, job):
					case <-ctx.Done():
						return
					}
				}
			}
		}()
	}
	go func() {
		wg.Wait()
		close(results) // the sender side closes, once, after every worker is done
	}()
	return results
}
```

With Go 1.25, `wg.Go(func() { ... })` replaces the `Add(1)` / `defer Done()` pair.

## A semaphore around one resource

```go
type Exporter struct {
	slots *semaphore.Weighted // at most maxExports run at once, program-wide
}

func NewExporter() *Exporter {
	return &Exporter{slots: semaphore.NewWeighted(maxExports)}
}

func (e *Exporter) Export(ctx context.Context, id int64) error {
	if err := e.slots.Acquire(ctx, 1); err != nil {
		return err // ctx cancelled while waiting
	}
	defer e.slots.Release(1)
	return e.export(ctx, id)
}
```

A buffered channel does the same with no dependency:
`slots := make(chan struct{}, n)`, `slots <- struct{}{}` to take one,
`<-slots` to give it back.

## A rate limit

```go
limiter := rate.NewLimiter(rate.Limit(20), 5) // 20 per second, bursts of 5

for _, order := range orders {
	if err := limiter.Wait(ctx); err != nil {
		return err
	}
	if err := partner.Submit(ctx, order); err != nil {
		return err
	}
}
```

## One result with a timeout, and no leak

```go
func firstPrice(ctx context.Context, fetch func(context.Context) (Price, error)) (Price, error) {
	ctx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()

	type answer struct {
		price Price
		err   error
	}
	done := make(chan answer, 1) // buffer of 1: the goroutine can always send, even after we left
	go func() {
		p, err := fetch(ctx)
		done <- answer{p, err}
	}()
	select {
	case a := <-done:
		return a.price, a.err
	case <-ctx.Done():
		return Price{}, ctx.Err()
	}
}
```

Without the buffer, a late `fetch` blocks on `done <-` forever: a goroutine
leak per timeout.

## A pipeline

```go
func parse(ctx context.Context, lines <-chan string) <-chan Event {
	out := make(chan Event)
	go func() {
		defer close(out)
		for line := range lines {
			event, err := ParseEvent(line)
			if err != nil {
				continue // or send it to an errors channel the owner reads
			}
			select {
			case out <- event:
			case <-ctx.Done():
				return
			}
		}
	}()
	return out
}
```

Each stage owns and closes its output. The last stage's reader decides the pace.

## Shared state behind one mutex

```go
// Limits holds the per-tier daily totals of this process.
// mu guards totals. Hold it only to read or change totals, never across I/O.
type Limits struct {
	mu     sync.Mutex
	totals map[TierID]int64
}

func (l *Limits) Add(tier TierID, amountMinor int64) int64 {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.totals[tier] += amountMinor
	return l.totals[tier]
}
```

This is a cache or a metric, not the guard of money. The database holds the
real total.

## A counter

```go
var processed atomic.Int64

processed.Add(1)
log.Info("done", "processed", processed.Load())
```

## Graceful shutdown

```go
func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	server := &http.Server{Addr: ":8080", Handler: routes()}
	g, ctx := errgroup.WithContext(ctx)
	g.Go(func() error {
		if err := server.ListenAndServe(); !errors.Is(err, http.ErrServerClosed) {
			return err
		}
		return nil
	})
	g.Go(func() error { return outbox.Run(ctx) }) // a worker that returns when ctx is done
	g.Go(func() error {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
		defer cancel()
		return server.Shutdown(shutdownCtx)
	})
	if err := g.Wait(); err != nil {
		slog.Error("stopped", "err", err)
		os.Exit(1)
	}
}
```

## Money: the database is the guard

```go
func (r *Wallets) Debit(ctx context.Context, walletID, amountMinor int64) error {
	res, err := r.db.ExecContext(ctx,
		`UPDATE wallets SET balance_minor = balance_minor - $1
		 WHERE id = $2 AND balance_minor >= $1`, amountMinor, walletID)
	if err != nil {
		return fmt.Errorf("debit wallet %d: %w", walletID, err)
	}
	if n, _ := res.RowsAffected(); n != 1 {
		return ErrInsufficientFunds
	}
	return nil
}
```

## The pool is a bound too

```go
db.SetMaxOpenConns(25)          // the database's share for this service ÷ replicas
db.SetMaxIdleConns(25)
db.SetConnMaxLifetime(30 * time.Minute)
```

A fan-out of 100 against `MaxOpenConns(25)` runs 25 queries and queues 75.

## Anti-patterns

| Do not | Why | Instead |
|---|---|---|
| `go process(item)` in a loop over input | Unbounded, nobody waits, errors vanish | `errgroup` with `SetLimit` |
| `go func() { ... }()` in a handler, nobody waits | Outlives the request, leaks on error, no shutdown | Do it inline, or hand it to a worker `main` owns |
| `results = append(results, r)` from goroutines | A data race | Write to `results[i]`, or send on a channel |
| An unbuffered send after a timeout | The sender blocks forever | A buffer of 1, or `select` with `ctx.Done()` |
| `close(ch)` in the receiver | Panics the sender | The sender closes |
| A map shared without a lock | `fatal error: concurrent map writes` | A mutex, or one owning goroutine |
| `time.Sleep` to wait for a goroutine | Flaky, slow | `WaitGroup`, a channel, `synctest` in tests |
| `context.Background()` deep in a call chain | Cancellation stops there | Pass `ctx` down |
| A `sync.Mutex` around a balance | Guards one process of several | `SELECT ... FOR UPDATE` or an atomic `UPDATE` |
| Holding a mutex across an HTTP call | Every caller queues behind one slow partner | Copy what you need, unlock, then call |
