---
name: concurrency
description: "The concurrency readiness gate. Load it before you write code that runs work concurrently for throughput or latency: async/await, asyncio.gather or TaskGroup, goroutines, worker pools, threads, executors, CompletableFuture, reactive types, Promise.all, or a parallel batch job. Also load it when a request asks for 'high concurrency', 'make it faster', 'parallelize', 'handle more requests', or 'async'. It decides whether this system is built for that model, and loads the stack's concurrency skill only when it is."
---

# concurrency — use high concurrency only where the system was built for it

There are two kinds of concurrency work. Keep them apart.

| Kind | What it is | Rule |
|---|---|---|
| **Concurrency for correctness** | Two callers at once must not break an invariant: locks, `SELECT ... FOR UPDATE`, unique constraints, idempotency keys, optimistic versions | **Always required.** It is the `logic` lens's item 6, on every stack. This skill never turns it off |
| **Concurrency for throughput** | Do more work at once: async I/O, goroutines, worker pools, threads, parallel batches | **Gated.** Use it only when the system already runs that model. This skill is the gate |

A sync Django service with one `async def` view is not faster. It is slower,
and it has a new class of bugs. A FastAPI service with `requests.get` inside
`async def` stalls every request on the worker. A Go handler that starts one
goroutine per item with no bound falls over under load. The pattern is right
in one system and wrong in another, so the system decides, not the pattern.

## Step 1 — Read what the system runs

```bash
bin/craft-stack concurrency                 # the primary stack
bin/craft-stack concurrency --stack go      # one stack of a monorepo
```

It prints the model the system runs, a verdict, the evidence, what is allowed,
and what to avoid. It reads dependencies, the deployment files, and how the
handlers are declared. It does not run anything. Exit 1 means `not-ready`.

| Verdict | Meaning | What you do |
|---|---|---|
| `ready` | The system runs this model already | Load the stack's concurrency skill. Follow the model the code already has |
| `limited` | Part of it is safe, and the report names that part | Stay inside the allowed list. Anything else is a change of model |
| `not-ready` | The system was not built for it | Do not introduce it on this route. Go to Step 3 |

When the evidence is wrong, say so, and name the file that proves it. Do not
work around the report. Fix the evidence, or override with
`bin/craft-stack set <id>` and a reason in `log.md`.

## Step 2 — Prove the need before you add the mechanism

Concurrency is code that is hard to test and easy to get wrong. The
`minimal-code` ladder applies first. Before you add any concurrent mechanism,
answer these in the spec:

1. **What is slow, measured?** A profile, a trace, a slow-query log, a p95. Not
   a guess.
2. **Is the slow part I/O wait, CPU, or a lock?** Concurrency helps I/O wait.
   It does not help a slow query, a missing index, or N+1. Fix those first:
   they are cheaper and they stay fixed.
3. **What is the bound?** Every concurrent mechanism has a number: workers,
   in-flight requests, a semaphore size, a pool size. Write it in the spec,
   with the resource it protects (database connections, a partner's rate limit,
   memory).
4. **What happens on cancel, timeout, and partial failure?** Name it as a
   criterion.

Add one acceptance criterion with a number when throughput is the goal:
`WHEN 200 requests arrive within one second, THE service SHALL answer 99% of them within 300 ms.`
A concurrency change with no number is a change nobody can verify.

## Step 3 — When the verdict is not-ready

Pick one, and write the choice in the spec under "Validation decisions":

1. **Fix the bottleneck without concurrency.** Index, bulk query, select the
   columns you need, cache, paginate, move work off the request path. This is
   the usual answer.
2. **Move the work to the system's own background mechanism.** Celery for
   Django, a queue for Node (BullMQ), an `@Async` executor that already exists
   in Spring. Idempotent, retried, observable.
3. **Change the model on purpose.** This is the `project` route with
   `Risk: high`. `design.md` covers the server (WSGI to ASGI, MVC to WebFlux),
   the drivers, the connection pools, the deployment, the failure modes, the
   rollback, and the load criterion. Never as a side effect of a `task`.

Say it to the developer in one line:

```
🧵 concurrency: django is WSGI and sync. Async views are off here. Plan: bulk_update plus an index (choice 1).
```

## Step 4 — When the verdict is ready or limited

Load the stack's concurrency skill. `bin/craft-stack concurrency` names it on
its `load` line:

| Stack | Skill | The model |
|---|---|---|
| FastAPI | `fastapi-async` | asyncio on one event loop per worker |
| Go | `go-concurrency` | goroutines, channels, `context.Context` |
| Java | this skill, and `java-practices` | thread-per-request, virtual threads, or reactive: the report says which |
| Node | this skill, and `node-practices` | one event loop, promises |
| Laravel, Symfony, PHP | this skill, and `php-practices` (no concurrency skill) | a process per request, long-lived workers, or an event loop: the report says which |
| Django | this skill | sync. Celery for parallel work |

The rules that hold on every stack:

- **Every concurrent unit has an owner** that waits for it, and a way to stop
  it: a context, a cancel scope, an abort signal, a shutdown hook.
- **Every fan-out has a bound.** No `gather`, `Promise.all`, or goroutine loop
  over input whose size a user controls.
- **Every outbound call has a timeout.** Concurrency multiplies a slow
  dependency.
- **Shared state has one guard.** A lock, a channel that owns it, an atomic, or
  no sharing. Name the guard in a comment beside the state.
- **One pool per resource.** A database pool, an HTTP client, a worker pool:
  created once, at startup, sized against the resource, closed at shutdown.
- **No blocking call on an event loop.** Async code that calls a sync library
  blocks every other request. Wrap it, replace it, or keep the code sync.
- **Money stays serialized where it must.** Concurrency never replaces the
  lock or the constraint that protects a balance.

## Gate A for concurrent code

Add these to the checkpoint, through `bin/craft-check`:

| Stack | Check |
|---|---|
| Go | `go test -race ./...` (the `race` row of `bin/craft-stack checks`) |
| FastAPI | the async tests, with a test that proves a blocking call is absent or wrapped |
| Java | the concurrency test with a latch or a barrier, and no `Thread.sleep` waits |
| Node | the tests with fake timers, and `--detect-open-handles` for Jest |

The `concurrency` review lens runs on every diff that this skill touched.

## What this skill will not do

- It will not introduce async, threads, or a worker pool into a system whose
  report says `not-ready`, on any route but `project`.
- It will not remove a lock, a constraint, or a transaction to make code
  faster.
- It will not add concurrency without a bound, a timeout, and an owner.
- It will not claim a speed-up without a measured number.
