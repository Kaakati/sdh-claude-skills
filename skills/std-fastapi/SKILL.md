---
name: std-fastapi
description: FastAPI service conventions — routers, Pydantic schemas, SQLAlchemy 2.0 + Alembic, dependency injection, Celery background jobs, the house error envelope. Use when building or reviewing FastAPI APIs.
paths:
  - "**/app/main.py"
  - "**/app/api/**/*.py"
  - "**/app/routers/**/*.py"
  - "**/app/schemas/**/*.py"
  - "**/app/services/**/*.py"
  - "**/app/core/**/*.py"
  - "**/app/db/**/*.py"
  - "**/alembic.ini"
  - "**/alembic/**/*.py"
---

# FastAPI Conventions

Rules for FastAPI services on the Python secondary stack (AI/ML serving, data pipelines,
client-mandated projects). A FastAPI service shares the house infrastructure — PostgreSQL,
Redis, Centrifugo — and speaks the same API contract as the Rails backend.

## Stack

| Concern | Library |
|---------|---------|
| Framework | **FastAPI** (latest) on uvicorn — deployed to ECS Fargate behind an ALB |
| ORM / migrations | SQLAlchemy 2.0 async (`select()`, `Mapped[]`, `mapped_column`) + Alembic |
| Validation / config | pydantic v2 + pydantic-settings |
| Background jobs | Celery with the Redis broker |
| Real-time | Centrifugo (house standard — do **not** add Socket.IO) |
| Pagination | fastapi-pagination |
| Auth | OAuth2 bearer + `pyjwt` + `argon2-cffi` — **NOT `python-jose`, NOT `passlib`** (both unmaintained) |
| Tooling | uv (packages), ruff (lint + format), mypy strict, pytest |

## Project Structure

```
app/
  main.py           # create_app() factory + lifespan context manager (engine, clients)
  core/config.py    # pydantic-settings Settings — env-driven, never hardcoded secrets
  api/routers/      # One module per resource: users.py, orders.py
  schemas/          # Pydantic request/response models, mirrored per resource
  models/           # SQLAlchemy models — a package, one module per aggregate
  services/         # Business logic — plain classes/functions, no HTTP awareness
  db/session.py     # Async engine + async_sessionmaker + get_session dependency
alembic/            # Migrations — safety rules owned by std-database
```

- **`app/models/` is a package with one module per aggregate — never a single `models.py`.**
  A lone `models.py` is the Django idiom and that filename is claimed by the `std-django`
  skill's paths; the package layout keeps the two skills off each other's files.
- Wire startup/shutdown in `lifespan`, not deprecated `@app.on_event` handlers.

## Routers

- One `APIRouter` per resource with explicit `prefix` and `tags`:
  `router = APIRouter(prefix="/orders", tags=["orders"])`, included from `create_app()`.
- **`response_model` is always explicit** — it is the serialization contract; without it
  FastAPI returns whatever the function returns, leaking ORM internals and extra fields.
- **Status codes are explicit**: `status_code=201` on create, `204` on delete — the 200
  default on a POST misreports what happened and clients key retry logic off status.
- **Routers never contain business logic** — parse, authorize, delegate to a service,
  serialize. Same rule as thin Rails controllers; logic in a route cannot be reused by
  Celery tasks or scripts.
- Auth and the DB session arrive via `Depends` — never construct a session inside a route.

```python
@router.post("", response_model=OrderRead, status_code=201)
async def create_order(
    payload: OrderCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> OrderRead:
    order = await OrderService(session).create(payload, actor=user)
    return OrderRead.model_validate(order)
```

## Schemas (pydantic v2)

- Separate `XCreate` / `XUpdate` / `XRead` models per resource — one shared model forces
  every field optional and lets clients write server-managed fields.
- Read models set `model_config = ConfigDict(from_attributes=True)` and are built with
  `XRead.model_validate(orm_obj)`.
- **Never return an ORM object from a route** — the `response_model` + read model is the
  boundary; a raw ORM object couples the wire format to the table and can lazy-load
  outside the session.
- Use v2 idioms only: `model_dump()` / `model_dump_json()`, never the v1 `.dict()` / `.json()`.
- Update models declare optional fields and apply with `model_dump(exclude_unset=True)`
  so PATCH distinguishes "omitted" from "set to null".

## Dependency Injection

- `Depends` wires the session (`get_session` yields from `async_sessionmaker`, one session
  per request), the current user (bearer token → `get_current_user`), and services.
- **No import-time singletons except settings** — a module-level engine or HTTP client
  binds config and event loop at import, breaking test overrides and worker forks. Build
  them in `lifespan` and reach them through dependencies.
- Settings come from one `@lru_cache`-wrapped `get_settings()` returning the
  pydantic-settings `Settings` — env-driven, never hardcoded (secret handling owned by
  `std-security`).

## Async

- Routes are `async def` with the async session end-to-end (`postgresql+asyncpg://`) —
  do not mix a sync engine into an async app.
- Sync-only libraries (boto3, some SDKs) go through `run_in_threadpool` from
  `starlette.concurrency`.
- **Never call blocking I/O in an async route** — `requests`, `time.sleep`, a sync driver —
  it stalls the event loop for every in-flight request, not just this one. Deep guidance
  owned by `std-python-performance`.

## Errors

- `HTTPException` only in routers; services raise domain exceptions
  (`OrderNotFoundError`), never HTTP — services must stay callable from Celery and scripts.
- **ONE app-level exception handler** (`app.exception_handler`) translates domain
  exceptions into the house JSON error envelope owned by `std-api-design` — one
  translation point, do not restate the envelope or hand-build error JSON per route.

## Background Jobs (Celery + Redis)

- Mirror the Sidekiq conventions: tasks are **idempotent** — Celery retries deliver
  at-least-once, so a non-idempotent task double-charges on redelivery.
- **Pass IDs, not objects** — re-fetch inside the task; a serialized object is stale by
  the time the worker runs it.
- Queues are named `default`, `critical`, `low_priority` — the same names as the Sidekiq
  queues, so operators reason about one queue taxonomy across both stacks.
- Set explicit retry limits and `acks_late=True`; JSON serializer only, never pickle.

## Testing

- `httpx.AsyncClient` with `ASGITransport(app=app)` — in-process, no live server, no ports.
- `app.dependency_overrides` swaps `get_session` for a rollback-per-test session and
  `get_current_user` for a stub user — never patch auth internals.
- `pytest-asyncio` with `asyncio_mode = "auto"`; AAA structure and coverage targets owned
  by `std-testing`.

Related, owned elsewhere — do not duplicate: the JSON error envelope and pagination
response format live in `std-api-design`; migration safety and indexing depth in
`std-database`; OWASP and secret management in `std-security`; structured logging and
PII-in-logs in `std-monitoring`; AAA and coverage targets in `std-testing`; general Python
layout, typing, and layering in `std-python`; blocking-I/O and ORM query performance in
`std-python-performance`; Django specifics in `std-django`; ML/LLM serving conventions in
`std-python-ai-ml`.
