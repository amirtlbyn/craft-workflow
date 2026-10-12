# FastAPI — stack notes for the review lenses

Read these beside the core lens files. Where a core item names a Django construct, apply the FastAPI equivalent
below.

## style

- Item 6 (framework idiom): thin routers, a service layer, `response_model` on every endpoint, Pydantic v2 models
  with `extra="forbid"` on input, settings through `BaseSettings` and a dependency. `HTTPException` only in routers
  and dependencies.
- Annotated dependencies (`Annotated[Session, Depends(get_session)]`) where the repository uses them.

## logic

- Item 5 (transactions): `with session.begin():` or `async with session.begin():`, minimal, with no outbound call
  inside. Post-commit work runs after the block, or through an outbox.
- Item 3 (money): `Decimal` or an integer of minor units in schemas and columns. No `float`.

## security

- Item 4 (access decorator): every endpoint carries the repository's auth dependency, on the router or the
  endpoint. A new router with no dependency is item 1 at High.
- CORS from settings. `allow_origins=["*"]` with `allow_credentials=True` is High.
- Item 7: every `httpx` client has a timeout. A user-influenced URL is validated against an allow-list.

## query

- Index evidence: `index=True`, `unique=True`, `Index(...)` in `__table_args__`, or `op.create_index` in an Alembic
  migration. Quote it with `file:line`.
- N+1: a relationship read in a loop without `selectinload` or `joinedload`. In async code a lazy load raises
  `MissingGreenlet`: report it as N+1 and as a crash.
- Boundedness: every list endpoint has a `limit` with a maximum.

## concurrency

- Load `fastapi-async` and walk its "Review" list as items 3 to 10.
- A blocking call (`requests`, `time.sleep`, a sync driver, `open().read()` of a large file) in `async def` is
  item 7 at High, with the call chain that reaches it.
- An `AsyncSession` passed into a `TaskGroup` or `gather` is item 8 at High.
