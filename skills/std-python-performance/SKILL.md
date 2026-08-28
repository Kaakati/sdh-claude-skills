---
name: std-python-performance
description: Python query performance — N+1 prevention in Django ORM and SQLAlchemy, bulk operations, keyset pagination, indexing, EXPLAIN, connection pooling, Redis caching. Use when writing or reviewing Python ORM queries or data-access code.
paths:
  - "**/models.py"
  - "**/app/models/**/*.py"
  - "**/repositories/**/*.py"
  - "**/queries/**/*.py"
  - "**/app/db/**/*.py"
  - "**/migrations/**/*.py"
  - "**/alembic/**/*.py"
---

# Python Query Performance

Rules for keeping Python data access fast against PostgreSQL + PostGIS. Django ORM and
SQLAlchemy 2.0 side by side — the principles are the same, the spellings differ.

## Stack

| Concern | Tool |
|---------|------|
| ORM (Django) | Django 5.x ORM |
| ORM (FastAPI services) | SQLAlchemy 2.0 — `select()`, `Mapped[]`, `mapped_column()`; never the legacy 1.x `Query` API |
| Driver | psycopg 3 (Django); asyncpg for SQLAlchemy async engines (`std-fastapi`) |
| Migrations | Django migrations / Alembic |
| N+1 detection (dev) | django-debug-toolbar, nplusone |
| Query stats (prod) | pg_stat_statements |
| Cache | Redis (redis-py) |

## N+1 Queries

- **Never iterate a lazy relationship in a loop** — one query per row is the most common Python
  performance defect: invisible at 10 rows in dev, fatal at 10,000 in production.
- Django: `select_related()` for FK/OneToOne (SQL JOIN), `prefetch_related()` for M2M and
  reverse FKs (second query + in-memory join). Use `Prefetch(queryset=...)` when the prefetch
  itself needs filtering or ordering.
- SQLAlchemy 2.0: `selectinload()` for collections, `joinedload()` for scalar (many-to-one)
  refs — passed via `select(Model).options(...)`.
- Catch regressions in dev with django-debug-toolbar or nplusone; catch them permanently with
  `assertNumQueries` (Django) or a query-count assertion via engine events (SQLAlchemy).
- **A query count in a test is the only durable N+1 fix** — an eager-load without a pinned
  count silently regresses the next time someone touches the serializer.

## Fetch Less

- Django: `values()` / `values_list()` when you need rows, not model instances; `only()` /
  `defer()` to trim columns on model queries.
- SQLAlchemy: `load_only()` in `options()`, or select columns directly: `select(User.id, User.email)`.
- **Name your columns on hot paths** — wide JSONB columns make `SELECT *` expensive: every row
  drags the whole document over the wire even when the caller wanted an id and a name.

## Bulk Operations

- `bulk_create()` / `bulk_update()` / `in_bulk()` over per-row `save()` loops — one round-trip
  instead of N.
- Mass updates go through queryset `.update()`, never fetch-modify-save (it skips signals and
  `auto_now` — set timestamps explicitly).
- SQLAlchemy batches: `insert(Model).values([...])`, or `session.execute(insert(Model), rows)`.
- Large scans: Django `.iterator(chunk_size=2000)`, SQLAlchemy `yield_per` — stream in chunks
  so the whole table never lands in memory.

## Cheap Predicates

- `exists()` over `count() > 0` — existence stops at the first row; a count scans them all.
- Count only what the UI displays — drop total counts from infinite scroll entirely.

## Indexing

- Index every FK and every column you filter or sort on — Django indexes FKs automatically;
  SQLAlchemy does not, so pass `index=True` on the `mapped_column()`.
- Composite indexes follow the left-prefix rule — `(tenant_id, created_at)` serves `tenant_id`
  alone, never `created_at` alone.
- Partial indexes for soft-delete filters — Django `condition=Q(deleted_at__isnull=True)`,
  SQLAlchemy `postgresql_where=...` — so the index covers only rows queries actually touch.
- GIN for JSONB containment and trigram search; GiST for PostGIS geometry.
- Depth (concurrent creation, migration safety, when not to index) is owned by std-database —
  read it before writing the migration.

## Measure First

- **`EXPLAIN (ANALYZE, BUFFERS)` before optimizing** — a guessed optimization is a coin flip;
  the plan tells you whether the index is used at all.
- Enable pg_stat_statements in production; review top queries by total time, not mean.
- Red flags: seq scans on large tables, high rows-removed-by-filter (the index exists but is
  not selective), nested loops over large row counts.

## Pagination

- **Keyset pagination for deep or infinite lists** — `OFFSET` walks and discards every skipped
  row, so page 500 costs 500x page 1. Filter on the last-seen key instead:
  `WHERE (created_at, id) < (:last_seen, :last_id) ORDER BY created_at DESC, id DESC LIMIT :n`.
- OFFSET is acceptable only for shallow numbered pages (admin tables).
- The pagination response format (cursors, links, meta) is owned by std-api-design.

## Connection Pooling

- Size pools top-down: ECS tasks × workers per task × pool size must stay under the RDS
  `max_connections` ceiling, with headroom for migrations and consoles.
- SQLAlchemy: set `pool_size` + `max_overflow` explicitly; `pool_pre_ping=True` so a recycled
  RDS connection fails fast instead of erroring mid-request.
- Django: `CONN_MAX_AGE` for persistent connections, or the psycopg connection pool.
- At scale, put RDS Proxy or pgbouncer in transaction mode between app and database — but
  beware session state (`SET`, advisory locks, temp tables) and server-side prepared
  statements, which break under transaction pooling.

## Async Discipline

- **A sync ORM call inside a FastAPI `async def` route blocks the event loop** — every
  in-flight request stalls behind one query. Use the async session, or `run_in_threadpool`
  for legitimately sync code; framework wiring is owned by std-fastapi.
- Keep transactions short — do slow I/O (HTTP calls, file uploads) outside the transaction,
  never inside it.
- Queue-like workloads: `select_for_update(skip_locked=True)` (Django) /
  `with_for_update(skip_locked=True)` (SQLAlchemy) so workers skip locked rows instead of
  serializing on them.

## Caching (Redis)

- Cache in Redis with explicit TTLs — no infinite caches (mirroring the Rails caching
  conventions in std-rails-conventions).
- Build cache keys that include `updated_at` (or a version) so invalidation is automatic — a
  stale key is simply never read again.
- Cache serialized responses for hot list endpoints — cache the JSON after serialization, not
  the ORM objects.
- Guard hot keys against stampedes: jitter the TTL or lock-and-recompute.

Related, owned elsewhere — do not duplicate: the JSON error envelope and pagination response
format live in std-api-design; migration safety and indexing depth in std-database; FastAPI
async sessions and route wiring in std-fastapi; general Python layout, typing, and layering
in std-python; the Rails caching conventions this mirrors in std-rails-conventions.
