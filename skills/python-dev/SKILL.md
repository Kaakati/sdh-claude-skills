---
name: python-dev
description: Build Python backend features end to end — FastAPI (default) or Django+DRF services with SQLAlchemy 2.0/Alembic, pydantic v2 schemas, Celery jobs, and the uv/ruff/mypy/pytest ladder. Use this skill whenever someone asks to build a Python backend feature, add a FastAPI endpoint or Django app, write an Alembic migration, add a Celery task, or says things like "build the Python service for X", "add the /orders endpoint", "wire up the ML-serving API", or "take this FastAPI feature to PR".
model: sonnet
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Python Dev

## Purpose
Take a Python backend feature from requirements to PR on the secondary Python stack:
FastAPI + SQLAlchemy 2.0 + Alembic + Celery + Redis (primary path), or Django 5.x + DRF
where the project already made that call. The conventions live in the `std-*` skills —
this skill is the workflow that applies them in order.

## Framework Choice
One decision, made once per service, not per feature: FastAPI is the default; Django + DRF
only when an admin UI or batteries-included CRUD outweighs FastAPI's leanness. The decision
tree is owned by `std-python` — do not relitigate it here.

## Build Protocol (FastAPI — primary path)

### 1. Scaffold
- Confirm the house layout exists; create only what is missing: `app/main.py`
  (`create_app()` factory + lifespan), `app/core/config.py` (pydantic-settings),
  `app/api/routers/`, `app/schemas/`, `app/models/` (a package, one module per
  aggregate — never a single `models.py`), `app/services/`, `app/db/session.py`, `alembic/`
- New service: `uv init`, commit `uv.lock`, all tool config in `pyproject.toml`
- Layout and wiring rules → `std-fastapi`; layering and typing → `std-python`

### 2. Model + Migration
- Add the SQLAlchemy model: `Mapped[]`, `mapped_column()`, explicit `index=True` on FKs
  and filtered columns — SQLAlchemy does not index FKs for you
- `uv run alembic revision --autogenerate -m "add_orders"`, then **read the generated
  migration** — autogenerate misses server defaults, constraint names, and data moves
- Verify `downgrade()` actually reverses; split schema change from backfill
- Migration safety (locking, backfills, concurrent indexes) → `std-database`

### 3. Schemas
- Three pydantic models per resource in `app/schemas/<resource>.py`: `XCreate`,
  `XUpdate` (optional fields, applied with `exclude_unset`), `XRead`
  (`ConfigDict(from_attributes=True)`)
- The schema module mirrors the router module — one resource, one pair of files

### 4. Service
- One service per use case in `app/services/`, single `execute()` entry point
- Return a typed result object (dataclass or pydantic), never a bare dict
- Raise domain exceptions — no `HTTPException` here; the service must stay callable
  from Celery tasks and scripts
- Inject dependencies through `__init__` against `Protocol`s → `std-python`

### 5. Router
- One `APIRouter` per resource with explicit `prefix`/`tags`, included from `create_app()`
- Every route declares `response_model=` and `status_code=` explicitly (201 create,
  204 delete)
- Parse → authorize → one service call → `XRead.model_validate(...)` — no logic in routes
- Domain exceptions become the house envelope in ONE app-level exception handler —
  envelope shape → `std-api-design`

### 6. Celery Task (when the feature has async work)
- Anything slow or retryable — emails, ML inference, exports, third-party calls — is a
  Celery task, not request work
- Idempotent, takes IDs not objects, re-fetches inside the task; explicit retry limits,
  `acks_late=True`, JSON serializer; queues `default` / `critical` / `low_priority`
- Full task rules → `std-fastapi` (Background Jobs)

### 7. Tests
- `httpx.AsyncClient` with `ASGITransport(app=app)` — in-process, no live server
- `app.dependency_overrides` swaps `get_session` (rollback-per-test) and
  `get_current_user` (stub) — never patch auth internals
- `tests/` mirrors the package, one test module per source module; AAA and coverage
  targets → `std-testing`

### 8. Query-Performance Pass
- Before opening the PR, walk every list endpoint: eager-load with `selectinload()` /
  `joinedload()` and pin a query-count assertion in a test — an eager load without a
  pinned count silently regresses
- Keyset pagination for deep lists; `EXPLAIN` anything filtering a large table
- The full checklist → `std-python-performance`

### 9. Run the Ladder

```bash
uv run ruff format && uv run ruff check && uv run mypy && uv run pytest
```

- Fix everything the ladder reports — no `--no-verify`, no bare `# type: ignore`
  without an error code
- Then branch, conventional commit, and PR per `std-git-workflow`

## Django + DRF Variant
Same protocol, different spellings — depth in `std-django`:
1. Scaffold `config/` (split settings) + one app per bounded context under `apps/`
2. Model with `Meta.constraints` and a custom QuerySet manager;
   `makemigrations --name add_order_status`, verify the reverse,
   `makemigrations --check` in CI
3. DRF serializers validate; `services.py` mutates inside `transaction.atomic`
4. Thin ViewSet + router registration; django-filter `FilterSet`; global paginator and
   the envelope via a custom `EXCEPTION_HANDLER`
5. Celery task: identical idempotency and queue rules as the FastAPI path
6. Tests: pytest-django + `APIClient`, explicit `@pytest.mark.django_db`, factory_boy
7. Performance pass: `select_related` / `prefetch_related` + `assertNumQueries`
8. The same ladder: `uv run ruff format && uv run ruff check && uv run mypy && uv run pytest`

## Owned elsewhere — do not duplicate
This skill sequences the work. These own the rules:

- `std-python` — layout, typing, layering, error hierarchy, toolchain
- `std-fastapi` / `std-django` — framework wiring, DI, async discipline, Celery
- `std-python-performance` — N+1, eager loading, keyset pagination, pooling
- `std-python-ai-ml` — ML-serving features: model loading, inference endpoints, LLM calls
- `std-api-design` — the error envelope (`error`/`code`/`status`/`details`/`requestId`)
  and pagination response format
- `std-database` — migration safety, locking, indexing depth
- `std-testing` — AAA structure, coverage targets
- `std-security` — auth (`pyjwt` + `argon2-cffi`, never `python-jose`/`passlib`), secrets

## Done means
- [ ] Ladder green: ruff format + check clean, `mypy --strict` clean, pytest passing
- [ ] List endpoints eager-load with a pinned query-count assertion — no N+1
- [ ] Every route has explicit `response_model` and `status_code`; errors conform to
      the house envelope
- [ ] Migration reversible and read by a human; schema change split from backfill
- [ ] Celery tasks idempotent, ID-passing, bounded retries
- [ ] Conventional commit, branch naming, and docs/CHANGELOG per `std-git-workflow`
