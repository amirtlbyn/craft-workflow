# Lens: concurrency — concurrent code for throughput, and whether the system was built for it

- **Ceiling:** High
- **Minimum confidence:** 0.6
- **Reads:** the diff, `bin/craft-stack concurrency --json` for the stacks the diff touches, the stack's
  concurrency skill when it has one (`fastapi-async`, `go-concurrency`), and `bin/craft-stack lens concurrency
  --paths <changed paths>` for the stack's own items. The spec's bound and latency criterion, when it has one.

This lens owns concurrency **for throughput**: async code, goroutines, worker pools, threads, executors, parallel
batches, and the event loop. Races that cost money or break an invariant belong to `logic` (item 6), at Critical.
When one defect is both, file it under `logic`, once.

## Checklist — answer every item

1. **Model fit** — the code uses the concurrency model `bin/craft-stack concurrency` reports, and only the
   patterns its allowed list names. New async code in a `not-ready` system, or a new model (reactive in an MVC
   service, threads in a sync Django view), is a finding at High unless the route is `project` and `design.md`
   covers it.
2. **Need** — the spec names what is slow and how it was measured, and a criterion with a number. Concurrency
   added with no measured need is a finding at Medium (`minimal-code`).
3. **Owner** — every concurrent unit (task, goroutine, promise, future) has an owner that waits for it and sees
   its error.
4. **Stop path** — every unit stops on cancellation, a closed input, or the end of finite work. Every blocking
   wait selects on cancellation.
5. **Bound** — every fan-out has a number that comes from a resource, and the number is consistent with the
   connection pool. A fan-out sized by input is a finding at High.
6. **Timeouts** — every outbound call inside the concurrent path has a timeout, and the group has a total budget.
7. **Blocking** — no blocking call on an event loop (FastAPI `async def`, Node, reactive). Found one: High.
8. **Shared state** — every shared value has one named guard. No unguarded map, list, or counter.
9. **Resources** — clients, pools, and executors are created once, sized, and closed on shutdown.
10. **Errors and cancellation** — no swallowed cancellation (`CancelledError`, `context.Canceled`, `AbortError`).
    Partial failure is handled as the spec says.
11. **Tests** — a test runs the concurrent path concurrently and proves the bound or the serialization. The race
    detector ran for Go.

## Severity

**High** — the wrong model for the system, an unbounded fan-out, a blocking call on an event loop, a goroutine or
task that can never stop, a missing timeout on a path that can hang a worker. **Medium** — a missing owner, a
missing test of the bound, concurrency with no measured need. **Low** — naming or structure that hides the bound.

In each finding, name the unit, its owner (or its absence), its bound, and the resource it competes for.
