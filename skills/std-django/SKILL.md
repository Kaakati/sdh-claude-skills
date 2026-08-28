---
name: std-django
description: Django conventions — models, DRF viewsets and serializers, service functions, QuerySet managers, GeoDjango/PostGIS, Celery, migrations. Use when building or reviewing Django or Django REST Framework code.
paths:
  - "**/manage.py"
  - "**/settings.py"
  - "**/urls.py"
  - "**/wsgi.py"
  - "**/models.py"
  - "**/views.py"
  - "**/admin.py"
  - "**/serializers.py"
  - "**/forms.py"
  - "**/apps.py"
  - "**/migrations/**/*.py"
---

# Django Conventions

Rules for building Django + DRF services on the secondary Python stack, consuming the same
PostgreSQL/PostGIS and Redis infrastructure as the Rails apps.

## When Django

- Choose Django for admin-heavy back-offices, CMS-like domains, and batteries-included CRUD —
  the admin, auth, and ORM migrations pay for the framework weight
- The API is still API-only via Django REST Framework — the house ships no server-rendered
  Django templates for clients (`forms.py` serves admin customization, not client pages)
- FastAPI is the default Python backend otherwise — the decision tree lives in `std-python`

## Stack

| Concern | Library |
|---------|---------|
| Framework | **Django 5.x** |
| API | Django REST Framework |
| OpenAPI | drf-spectacular — schema generated from the code it documents |
| Auth | djangorestframework-simplejwt (pyjwt underneath); `Argon2PasswordHasher` via argon2-cffi |
| Config | django-environ — settings read from env, never hardcoded |
| DB driver | psycopg 3 |
| Cache | django-redis |
| Jobs | Celery + Redis broker |
| Filtering | django-filter |
| Geospatial | GeoDjango (`django.contrib.gis`) on the house PostGIS database |
| Testing | pytest-django + factory_boy |

Package management (uv), lint/format (ruff), and mypy strict are house-wide — see `std-python`.

## Project Layout

```
config/               # Project package: urls.py, wsgi.py, celery.py
  settings/           # base.py / dev.py / prod.py — DJANGO_SETTINGS_MODULE picks one
apps/
  orders/             # One Django app per bounded context
    models.py  serializers.py  views.py  services.py  tasks.py
    migrations/  tests/
manage.py
```

- Split settings: shared config in `base.py`, environment deltas in `dev.py` / `prod.py`
- One Django app per bounded context — small, focused apps over one `core` monolith app

## Models

- **Database constraints in `Meta.constraints` (`UniqueConstraint`, `CheckConstraint`)
  alongside model validators** — validators run only where `full_clean` is called (forms, DRF
  serializers); constraints guard every write path, including `bulk_create`, `.update()`, and
  raw SQL
- Custom QuerySet + `.as_manager()` for reusable queries — the Rails scope analog, and chainable:
  ```python
  class OrderQuerySet(models.QuerySet):
      def active(self) -> "OrderQuerySet":
          return self.filter(status=Order.Status.ACTIVE)

  class Order(models.Model):
      objects = OrderQuerySet.as_manager()
  ```
- **No signals for domain logic** — they hide the call graph; a `save()` that fires three
  receivers is untraceable. Business logic lives in services that are called explicitly
- Use `TextChoices` / `IntegerChoices` for enumerations; give every model a `__str__` (the
  admin renders it)

## Views & DRF

- Thin ViewSets exposing the standard actions (list/retrieve/create/update/destroy); an extra
  endpoint gets its own ViewSet and router registration, not a grab-bag of `@action` methods —
  the analog of the Rails max-7-actions rule
- Serializers validate input; services perform mutations — keep `create`/`update` overrides to
  a one-line delegation into `services.py`
- **`DEFAULT_PERMISSION_CLASSES = ["rest_framework.permissions.IsAuthenticated"]` in settings —
  never a global `AllowAny`** — a policy nobody enforces returns `200 OK` with someone else's
  data. Per-view `AllowAny` is an explicit, visible opt-out on deliberately public endpoints
- Filter with django-filter `FilterSet` classes, never hand-parsed query params
- Configure a global DRF paginator; the pagination response format is owned by `std-api-design`
- Map DRF exceptions into the house error envelope with a custom `EXCEPTION_HANDLER` — the
  envelope itself is owned by `std-api-design`

## Services

- `services.py` per app (a `services/` package once it outgrows one file)
- Plain typed functions or small classes — take IDs and values in, return domain objects
- **`transaction.atomic` at the service boundary, not sprinkled through views** — one use case,
  one transaction; scattering `atomic` makes partial-commit bugs invisible

## Migrations

- **Every `RunPython` gets a reverse function** — an irreversible migration turns a bad deploy
  into a restore-from-backup
- **Never combine a schema change and a data backfill in one migration** — split into
  add-column → backfill → constrain so each step deploys and reverts alone; deep safety rules
  are owned by `std-database`
- Name migrations (`makemigrations --name add_order_status`) — never ship `000N_auto_`
- Run `makemigrations --check` in CI to catch model/migration drift

## GeoDjango (PostGIS)

- `PointField(srid=4326)` for coordinates — the Python face of the same PostGIS database the
  Rails apps use, same SRID
- Geometry fields index themselves (`spatial_index=True` is the default) — keep it; `dwithin`
  and `distance_lte` lookups depend on it
- Use the GEOS API (`django.contrib.gis.geos`) for geometry operations — the `rgeo` analog
- `geography=True` when distance queries must return meters

## Celery

- **Idempotent tasks that take IDs, never model instances** — the row can change between
  enqueue and run, and retries must be safe to repeat
- Re-fetch inside the task; a missing row is a normal outcome, not an exception to swallow
- Retries with backoff (`autoretry_for`, `retry_backoff=True`) and a bounded `max_retries`
- Celery beat for scheduled work — schedules live in code, versioned, not in crontabs
- Queues mirror the Sidekiq convention: `default`, `critical`, `low_priority`

## Testing

- pytest-django; **mark database access explicitly with `@pytest.mark.django_db`** — the
  unmarked tier stays a fast pure-unit suite, and an accidental DB hit fails loudly
- DRF `APIClient` for endpoint tests; factory_boy factories over static fixture files
- AAA structure and coverage targets are owned by `std-testing`

Related, owned elsewhere — do not duplicate: the JSON error envelope
(`error`/`code`/`status`/`details`/`requestId`) and pagination response format live in
`std-api-design`; migration safety depth and indexing live in `std-database`; OWASP and secret
management in `std-security`; structured logging and PII-in-logs in `std-monitoring`; AAA and
coverage targets in `std-testing`; Python layout, typing, and layering in `std-python`; ORM
query performance in `std-python-performance`; FastAPI specifics in `std-fastapi`; ML/LLM
conventions in `std-python-ai-ml`.
