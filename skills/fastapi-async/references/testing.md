# fastapi-async — testing

Every test still names its criterion ID first in the docstring. These patterns
make async behavior testable without long sleeps and without a live network.

## The client

```python
import asyncio

import anyio
import httpx
import pytest
from asgi_lifespan import LifespanManager      # runs the app's lifespan in tests

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.mark.anyio
async def test_withdrawal_over_limit_is_refused(client):
    """WDL-1: Given a tier limit of 100, when a withdrawal of 101 arrives, then 422 limit_exceeded."""
    response = await client.post("/withdrawals", json={"amount_minor": 101})
    assert response.status_code == 422
    assert response.json()["code"] == "limit_exceeded"
```

`httpx.ASGITransport` does not run the lifespan by itself. `LifespanManager`
does. FastAPI's sync `TestClient`, used as a context manager, runs it too, but
it cannot test concurrency.

## Replace the partner, not the network

Override the dependency that returns the client, or mount an
`httpx.MockTransport`:

```python
def partner_transport(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://partner.test")
```

## Prove the bound

```python
@pytest.mark.anyio
async def test_quotes_never_exceed_the_partner_limit(monkeypatch):
    """QTE-3: Given 50 symbols, when quotes are fetched, then at most 5 calls are in flight."""
    in_flight = 0
    peak = 0

    async def handler(request):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)          # hold the call, so concurrent calls overlap
        in_flight -= 1
        return httpx.Response(200, json={"price": "1.00"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://p") as http:
        await quote_all(http, SYMBOLS_50)

    assert peak == 5          # unbounded code would reach 50
```

## Prove the timeout

```python
@pytest.mark.anyio
async def test_profile_times_out_within_the_budget():
    """PRF-2: Given a partner that never answers, when the profile is read, then the answer comes within 2 s."""
    async def never(request):
        await asyncio.Event().wait()

    async with httpx.AsyncClient(transport=httpx.MockTransport(never), base_url="https://p") as http:
        with anyio.fail_after(3):
            profile = await read_profile(http, user_id=1)
    assert profile is None
```

`anyio.fail_after` makes the test fail instead of hang if the code under test
has no timeout.

## Prove the money is serialized

Two concurrent debits of one wallet against a real database (a container, not
SQLite: SQLite has no row locks):

```python
@pytest.mark.anyio
async def test_two_concurrent_debits_cannot_overdraw(sessionmaker, wallet_with_100):
    """WDL-3: Given a balance of 100, when two debits of 60 run at once, then exactly one succeeds."""
    async def attempt():
        async with sessionmaker() as session, session.begin():
            return await debit_atomic(session, wallet_with_100.id, 60)

    results = await asyncio.gather(attempt(), attempt())
    assert sorted(results) == [False, True]
```

## Catch blocking calls

Run the suite once with asyncio's debug mode:

```bash
PYTHONASYNCIODEBUG=1 pytest -q -W error::RuntimeWarning
```

asyncio logs `Executing <Task ...> took 0.250 seconds` for every step that
blocked the loop for over 100 ms, and warns about coroutines never awaited.
Treat either as a failure.
