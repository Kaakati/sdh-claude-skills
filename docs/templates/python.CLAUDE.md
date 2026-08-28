# Python Service (FastAPI / Django) — package conventions

Copy this file into your Python service package directory as `CLAUDE.md`. The
directory can be named anything — `svc/`, `api/`, `ml/` — detection is marker-based
(`pyproject.toml` deps, `manage.py`, `alembic.ini`). This file loads automatically
when Claude works in this package; it layers on the repository-root `CLAUDE.md`.

Python backend: FastAPI by default (Django + DRF for admin-heavy CRUD), pydantic v2,
SQLAlchemy 2.0 + Alembic (or Django ORM), Celery + Redis, PostgreSQL + PostGIS.
Full standards ship as the `sdh` plugin's path-scoped `std-*` skills (`std-python`,
`std-fastapi`, `std-django`, `std-python-performance`, `std-python-ai-ml`) — scoping
limits when a skill applies, so read the one bearing on your change.

## Commands
- Install: `uv sync`
- Tests: `uv run pytest`
- Lint/format: `uv run ruff format && uv run ruff check`
- Types: `uv run mypy src/` (or `app/`)
- Migrate: `alembic upgrade head` (FastAPI) / `python manage.py migrate` (Django)
- Dev: `uvicorn app.main:app --reload` (FastAPI) / `python manage.py runserver` (Django)
- Worker: `celery -A app.worker worker`

## Structure
- `app/main.py` — FastAPI app factory, router registration, middleware
- `app/core/config.py` — pydantic-settings config (env vars, never literals)
- `app/api/routers/` — thin routers; delegate to services; `response_model` everywhere
- `app/schemas/` — pydantic v2 request/response schemas
- `app/models/` — SQLAlchemy models (one file per aggregate, target ≤200 lines)
- `app/services/` — business logic (single responsibility, typed result objects)
- `app/db/session.py` — engine + session factory; `alembic/` — migrations
- Django variant: `config/` settings split, `apps/` per bounded context, `models.py` ≤200 lines

## Conventions
- Services own business logic and return typed result objects; routers stay thin.
- pydantic schemas at every boundary — never return or leak ORM objects.
- Eager-load relations in list endpoints; assert query counts in tests.
- Never log secrets, tokens, or PII. Bare `except:` / `except BaseException` is flagged by the hooks.
- Prefer community libraries over custom code (`pydantic-settings`, `httpx`, `sqlalchemy`, `celery`).
