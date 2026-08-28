---
name: std-python
description: Python code standards — src/ layout, typing, uv, ruff, mypy, pydantic, pytest, and the models/services/controllers layering shared by FastAPI and Django services. Use when writing or reviewing any Python code.
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/requirements*.txt"
---

# Python Code Standards

Rails is the primary backend — Python services exist for AI/ML serving, data pipelines, and
client-mandated stacks, not as a parallel general-purpose backend. FastAPI is the default for
new Python APIs; choose Django 5.x + DRF when an admin UI or batteries-included CRUD outweighs
FastAPI's leanness. Framework specifics live in `std-fastapi` and `std-django` — this skill owns
everything the two share.

## Toolchain

| Concern | Tool | Notes |
|---------|------|-------|
| Language | **Python 3.12+** | Declare in `requires-python`; pin the same version in Docker images |
| Packaging | **uv** | One tool for venv, install, and lockfile. **Commit `uv.lock`** — an unpinned dependency tree is an unreproducible build |
| Lint + format | **ruff** | Both jobs — replaces black, flake8, and isort. One tool, one config |
| Type checking | **mypy `--strict`** on `src/` | pyright is acceptable in-editor; mypy is the CI gate |
| Tests | pytest + pytest-cov | Coverage targets live in `std-testing` |
| Validation | pydantic v2 | At boundaries only — `model_dump()`, `ConfigDict`, `from_attributes`. Never v1 idioms (`.dict()`, `class Config`) |
| HTTP client | httpx | Not `requests` — same API sync and async, so a service can go async without a client rewrite |
| Logging | structlog | Conventions in `std-monitoring` |
| JSON (hot path) | orjson | Serialization-heavy endpoints and pipeline hops; stdlib `json` elsewhere |

- Auth primitives: `pyjwt` for tokens, `argon2-cffi` for password hashing. **Never `python-jose`
  or `passlib`** — both are unmaintained; unpatched crypto is a liability, not a dependency

## Project Layout

- **Use the src layout (`src/<package>/`), never a top-level package directory** — src layout
  makes the installed package the only importable one, so tests cannot silently pass against
  uninstalled code
- `tests/` mirrors the package: `src/<package>/services/billing.py` →
  `tests/services/test_billing.py`
- **`pyproject.toml` is the single config home** — `[tool.ruff]`, `[tool.mypy]`, and
  `[tool.pytest.ini_options]` all live there. No `setup.cfg`, `.flake8`, `mypy.ini`, or
  `pytest.ini` scattered around the repo
- `requirements*.txt` exists only when a client platform demands it — generate it from the lock
  (`uv export`), never hand-edit

## Typing

- Annotate every public function — parameters and return type. `mypy --strict` enforces it
- **No bare `Any` at module boundaries** — `Any` on an exported signature switches type checking
  off for every caller. Use a precise type, a `TypeVar`, or a `Protocol`
- Use `Protocol` for dependency seams (repositories, gateways, external clients) — structural
  typing keeps services testable without inheritance trees
- pydantic models at I/O boundaries (HTTP, queues, files, LLM calls); plain `@dataclass`
  (frozen where possible) for internal value objects — validation cost belongs at the edge,
  not on every internal construction

## Layering — Models, Services, Controllers

The Python mirror of the Rails `Controllers → Services → Models` architecture. Same rules,
same direction.

### Controllers (FastAPI routers / DRF viewsets)
- HTTP only: parse and validate input, delegate to one service call, serialize the result
- No business logic, no ORM queries, no branching beyond input handling — a controller that
  needs an `if` about the domain is a service call in disguise
- Translate domain exceptions to HTTP responses here (envelope format → `std-api-design`)

### Services
- Own all business logic. One service per use case, named for it: `CreateOrder`,
  `IngestDataset`
- **Single public entry point — `execute()` on a class, or one module-level function.** A
  service with five public methods is five services sharing state by accident
- **Return typed result objects (dataclass or pydantic), never bare dicts** — a dict return
  hides exactly the contract mypy exists to check
- Inject dependencies (repositories, clients, clock) through `__init__` against `Protocol`s

### Models
- Persistence only. SQLAlchemy 2.0 style: `Mapped[]`, `mapped_column()`, `select()` — **never
  the legacy 1.x `Query` API** (`session.query(...)`); it predates typing and mixes ORM
  generations in one codebase
- Django models likewise: fields, constraints, managers — no business rules
- **Never let an ORM object cross a layer boundary — convert to a pydantic schema
  (`ConfigDict(from_attributes=True)`) at the edge.** A leaked ORM object drags the session,
  lazy-loading, and the table schema into every consumer
- Query performance (N+1, eager loading) → `std-python-performance`

### Dependency direction
- **Controllers → services → models, never backwards; models never import services.** One
  upward import and the layers are decoration, not architecture

## Error Handling

- **One exception hierarchy per service, rooted in a domain base class**
  (`class BillingError(Exception)`) — callers catch the base, not a grab-bag of library errors
- **Never bare `except:` or `except BaseException`** (any form, tuple included) — both also
  swallow `SystemExit` and `KeyboardInterrupt`, so shutdown and Ctrl-C die silently; the
  error-handling hook flags them. **Never `except Exception:` without re-raise** — swallowing
  at that width hides the defect and keeps the process limping in unknown state
- Raise domain exceptions in services; translate to HTTP status + envelope only at the
  controller boundary — services must not know HTTP exists
- Chain when translating: `raise PaymentDeclined(...) from exc` — losing the cause loses the
  trace

## Testing

- pytest fixtures over `setUp` classes — composition and scoping, no inheritance
- Test data via `factory_boy` (Django models) and `polyfactory` (pydantic schemas) — no
  hand-rolled dict fixtures
- Names read as behavior: `test_should_reject_order_when_inventory_empty`
- Fake at the `Protocol` seam, not with `patch()` on internals — patch paths break on every
  refactor

Related, owned elsewhere — do not duplicate: the JSON error envelope
(`error`/`code`/`status`/`details`/`requestId`) and pagination response format are
`std-api-design`; migration safety and indexing depth are `std-database`; OWASP and secret
management are `std-security`; structured logging and PII-in-logs are `std-monitoring`; AAA and
coverage targets are `std-testing`; ORM query performance is `std-python-performance`; framework
specifics are `std-fastapi` and `std-django`; ML/LLM conventions are `std-python-ai-ml`.
