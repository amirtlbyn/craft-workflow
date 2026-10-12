---
name: fastapi-practices
description: "FastAPI and Pydantic practices for implementation and review: thin routers, a service layer, dependencies for sessions and auth, Pydantic v2 models at the boundary, settings with pydantic-settings, one exception handler, SQLAlchemy 2.0 access, Alembic migrations, and tests with httpx. Load it with python-style for FastAPI work. Load fastapi-async as well only when the concurrency report says the service is async-ready."
---

# fastapi-practices

Use with `python-style`. First read the repository's own layout, its
`pyproject.toml`, and two neighbouring routers. Follow what is there.

`standards/fastapi_standards.ai.md` holds the detail:
`bin/craft-std fastapi_standards --list`.

## Boundaries

- **Routers stay thin.** Parse the request, call one service function, shape
  the response. No query, no business rule, no outbound call in a router.
- **Services own the rules.** A service function takes plain values and a
  session, and returns domain objects. It does not know about `Request`,
  `Response`, or HTTP status codes.
- **Dependencies inject, they do not decide.** `Depends` gives a session, the
  current user, settings, a client. A dependency that holds a business rule is
  hard to find and hard to test.
- **One exception handler maps domain errors to HTTP.** Services raise
  `InsufficientFunds`, the handler answers 422 with the repository's error
  shape. No `HTTPException` deep in a service.

## Models

- Request and response bodies are Pydantic v2 models, separate from the ORM
  models. `model_config = ConfigDict(extra="forbid")` on input, so a typo in a
  client's field name is a 422, not a silent default.
- Declare `response_model` (or a return annotation) on every endpoint. It is
  the contract, and it stops a field leaking by accident.
- Money is `Decimal` or an integer of minor units, never `float`. Constrain it:
  `Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=8)]`.
- Validate at the boundary once. Do not re-validate the same field in the
  service (`validation-discipline`).

## Settings

`pydantic-settings` `BaseSettings`, read once, injected with a dependency.
No `os.environ[...]` scattered through the code. Secrets are `SecretStr`, and
they are never logged or returned.

## Database

- SQLAlchemy 2.0 style: `select(...)`, `session.execute(...)`, typed
  `Mapped[...]` columns.
- One session per request, from a dependency, closed by it.
- Transactions are explicit: `with session.begin():` (or `async with`). Keep
  them short. No outbound call inside one.
- Alembic for every schema change. Autogenerate, then read and edit the
  migration: autogenerate misses renames, server defaults, and data moves.
  `technical_standards` TS-1 applies to Alembic as it does to Django.

## Endpoints

- `def` or `async def` follows the concurrency report, not taste. A sync
  driver means `def`. See the `concurrency` skill.
- Paginate every list endpoint. A bounded `limit` with a maximum.
- Status codes from the repository's convention. `201` with a `Location` for a
  create, when the repository does that.
- Authentication and authorization are dependencies on the router or the
  endpoint, never an `if` inside it. Object-level checks scope the query to the
  user.

## Tests

- `httpx.AsyncClient` with `ASGITransport`, or `TestClient` for sync suites.
- Override dependencies with `app.dependency_overrides`, and clear them after.
- A real database for queries and locks (a container). SQLite hides locking
  and type bugs.
- One test per criterion, its ID first in the docstring.

## Before finishing

Read the diff for: business logic in a router, an endpoint with no
`response_model`, `float` money, a missing pagination bound, an `HTTPException`
in a service, and a blocking call in `async def`.
