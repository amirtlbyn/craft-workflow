# go-concurrency — testing

Every test names its criterion ID first, in the subtest name or the comment
above it, so `bin/craft-spec trace` finds it.

## The race detector is part of Gate A

```bash
bin/craft-check -- go test -race ./...
```

It reports races on code paths the tests execute. A test that never runs two
goroutines at once proves nothing about races. Write one that does.

## Run the code from many goroutines at once

```go
// WDL-3: Given a balance of 100, when two debits of 60 run at once, then exactly one succeeds.
func TestDebitIsSerialized(t *testing.T) {
	wallets := newTestWallets(t, 100) // a real database in a container, not a fake
	var ok atomic.Int32
	var wg sync.WaitGroup
	start := make(chan struct{})
	for range 2 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			<-start // release both at the same moment
			if err := wallets.Debit(context.Background(), walletID, 60); err == nil {
				ok.Add(1)
			}
		}()
	}
	close(start)
	wg.Wait()
	if got := ok.Load(); got != 1 {
		t.Fatalf("successful debits = %d, want 1", got)
	}
}
```

## Prove the bound

```go
// QTE-3: Given 50 symbols, when quotes are fetched, then at most 5 calls are in flight.
func TestQuoteAllRespectsTheLimit(t *testing.T) {
	var inFlight, peak atomic.Int32
	partner := fakePartner(func(ctx context.Context, symbol string) (Quote, error) {
		n := inFlight.Add(1)
		for {
			old := peak.Load()
			if n <= old || peak.CompareAndSwap(old, n) {
				break
			}
		}
		time.Sleep(5 * time.Millisecond) // hold the call so calls overlap
		inFlight.Add(-1)
		return Quote{Symbol: symbol}, nil
	})
	svc := &QuoteService{partner: partner}

	if _, err := svc.QuoteAll(context.Background(), symbols(50)); err != nil {
		t.Fatal(err)
	}
	if got := peak.Load(); got != 5 {
		t.Fatalf("peak in flight = %d, want 5", got)
	}
}
```

## Prove nothing leaks

`go.uber.org/goleak` fails a test that leaves goroutines running:

```go
func TestMain(m *testing.M) {
	goleak.VerifyTestMain(m)
}
```

Or per test: `defer goleak.VerifyNone(t)`.

## Test time without waiting for it

Go 1.25's `testing/synctest` runs a test in a bubble with a fake clock. Time
advances only when every goroutine in the bubble is blocked, so a 2-second
timeout takes no real time:

```go
// PRF-2: Given a partner that never answers, when the price is read, then it times out after 2 s.
func TestFirstPriceTimesOut(t *testing.T) {
	synctest.Test(t, func(t *testing.T) {
		never := func(ctx context.Context) (Price, error) {
			<-ctx.Done()
			return Price{}, ctx.Err()
		}
		start := time.Now()
		_, err := firstPrice(context.Background(), never)
		if !errors.Is(err, context.DeadlineExceeded) {
			t.Fatalf("err = %v, want DeadlineExceeded", err)
		}
		if elapsed := time.Since(start); elapsed != 2*time.Second {
			t.Fatalf("elapsed = %v, want exactly 2s on the fake clock", elapsed)
		}
	})
}
```

`synctest.Wait()` blocks until every other goroutine in the bubble is blocked,
which replaces `time.Sleep` "to let the goroutine run".

## Shutdown

```go
// OBX-4: Given a running outbox worker, when ctx is cancelled, then Run returns within 1 s.
func TestOutboxStopsOnCancel(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- outbox.Run(ctx) }()
	cancel()
	select {
	case err := <-done:
		if err != nil && !errors.Is(err, context.Canceled) {
			t.Fatal(err)
		}
	case <-time.After(time.Second):
		t.Fatal("Run did not return after cancel")
	}
}
```
