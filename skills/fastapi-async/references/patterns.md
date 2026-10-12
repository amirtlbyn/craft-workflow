# fastapi-async — patterns

Python 3.11 or newer, FastAPI with its `lifespan` parameter, SQLAlchemy 2.0,
httpx. Each section is self-contained. Adapt names to the repository's own.

## Lifespan

Create every long-lived client once per process. Close it on shutdown.

```python
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = create_async_engine(
        settings.database_url,          # postgresql+asyncpg://...
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
    )
    app.state.sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=2.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    app.state.background = set()     # tasks the app owns, see "Owned background tasks"
    try:
        yield
    finally:
        for task in app.state.background:
            task.cancel()
        await asyncio.gather(*app.state.background, return_exceptions=True)
        await app.state.http.aclose()
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
```

## A session per request

```python
from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


@router.post("/withdrawals")
async def create_withdrawal(body: WithdrawalIn, session: AsyncSession = Depends(get_session)):
    async with session.begin():                       # commit on success, rollback on error
        return await withdrawals.create(session, body)
```

## Money: lock the row, not the process

```python
from sqlalchemy import select, update


async def debit(session: AsyncSession, wallet_id: int, amount_minor: int) -> None:
    """Debit a wallet. The row lock serializes concurrent debits of one wallet."""
    wallet = (
        await session.execute(select(Wallet).where(Wallet.id == wallet_id).with_for_update())
    ).scalar_one()
    if wallet.balance_minor < amount_minor:
        raise InsufficientFunds(wallet_id)
    wallet.balance_minor -= amount_minor


async def debit_atomic(session: AsyncSession, wallet_id: int, amount_minor: int) -> bool:
    """The same rule in one statement. False when the balance is too low."""
    result = await session.execute(
        update(Wallet)
        .where(Wallet.id == wallet_id, Wallet.balance_minor >= amount_minor)
        .values(balance_minor=Wallet.balance_minor - amount_minor)
    )
    return result.rowcount == 1
```

## Load relations explicitly

```python
from sqlalchemy.orm import relationship, selectinload


class Order(Base):
    lines = relationship("OrderLine", lazy="raise")    # a missed load fails loudly


orders = (
    await session.execute(select(Order).options(selectinload(Order.lines)).limit(50))
).scalars().all()
```

## Bounded fan-out

All must succeed, and the rest stop on the first failure:

```python
import asyncio


async def quote_all(client: httpx.AsyncClient, symbols: list[str]) -> dict[str, Quote]:
    if len(symbols) > MAX_SYMBOLS_PER_REQUEST:
        raise TooManySymbols(len(symbols))
    limit = asyncio.Semaphore(QUOTE_CONCURRENCY)       # from the partner's rate limit

    async def one(symbol: str) -> Quote:
        async with limit:
            response = await client.get(f"/quotes/{symbol}")
            response.raise_for_status()
            return Quote.model_validate(response.json())

    async with asyncio.timeout(QUOTE_BUDGET_SECONDS):
        async with asyncio.TaskGroup() as group:
            tasks = {symbol: group.create_task(one(symbol)) for symbol in symbols}
    return {symbol: task.result() for symbol, task in tasks.items()}
```

Each may fail on its own:

```python
results = await asyncio.gather(*(notify(user) for user in batch), return_exceptions=True)
failed = [user for user, result in zip(batch, results) if isinstance(result, Exception)]
```

`batch` is bounded. For a large list, loop over slices of `BATCH_SIZE`.

A TaskGroup failure raises an `ExceptionGroup`. Catch the types you handle
with `except*`:

```python
try:
    async with asyncio.TaskGroup() as group:
        ...
except* httpx.HTTPStatusError as errors:
    raise PartnerUnavailable() from errors.exceptions[0]
```

## Parallel queries need one session each

```python
async def dashboard(sessionmaker) -> Dashboard:
    async def count(statement):
        async with sessionmaker() as session:          # its own session, its own connection
            return (await session.execute(statement)).scalar_one()

    async with asyncio.TaskGroup() as group:
        users = group.create_task(count(select(func.count()).select_from(User)))
        orders = group.create_task(count(select(func.count()).select_from(Order)))
    return Dashboard(users=users.result(), orders=orders.result())
```

Two parallel queries take two pooled connections. Count them against the pool.

## Timeouts

```python
try:
    async with asyncio.timeout(2.0):
        profile = await partner.get_profile(user_id)
except TimeoutError:
    profile = None          # or raise a 504 through the exception handler
```

Python 3.11 raises the built-in `TimeoutError`. On 3.10 use
`asyncio.wait_for(coro, timeout)`, which raises `asyncio.TimeoutError`.

## Do not swallow cancellation

```python
try:
    await stream_prices(websocket)
except asyncio.CancelledError:
    await websocket.close()
    raise                                   # always re-raise
finally:
    await unsubscribe(websocket)
```

## Blocking libraries

```python
from fastapi.concurrency import run_in_threadpool


@router.get("/reports/{report_id}")
async def report(report_id: int):
    pdf = await run_in_threadpool(legacy_sdk.render_pdf, report_id)   # sync SDK, in a thread
    return Response(pdf, media_type="application/pdf")
```

`asyncio.to_thread(fn, *args)` does the same outside FastAPI. CPU-bound work
belongs in a `ProcessPoolExecutor` created in the lifespan, or a task queue.

## Owned background tasks

```python
def spawn(app: FastAPI, coroutine) -> asyncio.Task:
    """Start a task the app owns. It is cancelled and awaited on shutdown."""
    task = asyncio.create_task(coroutine)
    app.state.background.add(task)
    task.add_done_callback(app.state.background.discard)
    task.add_done_callback(_log_failure)
    return task


def _log_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.error("background task failed", exc_info=task.exception())
```

## A shared rate limit

```python
# In lifespan: one limiter for the process, not one per request.
app.state.partner_limit = asyncio.Semaphore(settings.partner_max_in_flight)


async def call_partner(request: Request, payload: dict) -> dict:
    async with request.app.state.partner_limit:
        response = await request.app.state.http.post("/v1/orders", json=payload)
    response.raise_for_status()
    return response.json()
```

A Semaphore bounds one process. Across N workers the bound is N times larger:
divide the partner's limit by the worker count, or use a shared limiter in Redis.

## Anti-patterns

| Do not | Why | Instead |
|---|---|---|
| `requests.get(...)` in `async def` | Blocks the loop for every request on the worker | `await app.state.http.get(...)` |
| `time.sleep(1)` in `async def` | Same | `await asyncio.sleep(1)` |
| `httpx.AsyncClient()` per request | A new pool per request, no keep-alive, leaked sockets | One client in `lifespan` |
| `asyncio.gather(*(f(x) for x in body.items))` | Unbounded fan-out sized by the caller | A size check plus a Semaphore |
| One `AsyncSession` in a TaskGroup | Not safe for concurrent use | One session per task |
| `await partner.call()` inside `session.begin()` | Holds a lock and a connection while the partner is slow | Call first, then open the transaction, or use an outbox |
| `asyncio.Lock()` around a balance | Guards one process only | `with_for_update()` or an atomic `UPDATE` |
| `except BaseException: pass` | Swallows cancellation | Re-raise `CancelledError` |
| `asyncio.create_task(x)` and forget it | May be collected mid-flight, errors vanish | `spawn(app, x)` |
| `async def` with a sync driver | Slower than `def`, and stalls the loop | Keep `def`, or switch drivers as a project |
