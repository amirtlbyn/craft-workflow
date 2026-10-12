# Django — stack notes for the review lenses

The lens files in `skills/review-protocol/lenses/` are written for Django first. Their Django items apply as
written. These notes add what the core lenses leave out.

## concurrency

- The concurrency report for a Django service is usually `not-ready`: WSGI and sync. An `async def` view, an
  `asyncio.run`, a `ThreadPoolExecutor` in a view, or `sync_to_async` sprinkled to make code "faster" is item 1 at
  High.
- Parallel work belongs in Celery: idempotent tasks, `acks_late` where the repository uses it, and
  `transaction.on_commit()` to enqueue after the commit.
- `select_for_update` and unique constraints are correctness, and they belong to `logic`.
