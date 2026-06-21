# Backend (Rails API) — package conventions

Copy this file into your Rails package directory as `CLAUDE.md`. The directory can
be named anything — `backend/`, `api/`, `server/` — detection is wrapper-agnostic.
This file loads automatically when Claude works in this package (or starts here);
it layers on top of the repository-root `CLAUDE.md`.

Rails API-only backend: Phlex views, Panko serializers, PostgreSQL + PostGIS,
Redis/Sidekiq, Centrifugo. Full standards ship as the `sdh` plugin's path-scoped `std-*` skills
(`std-rails-conventions`, `std-phlex-conventions`, `std-api-design`, `std-database`, `std-monitoring`,
`std-clean-architecture`) and auto-load for matching files.

## Commands
- Tests: `bundle exec rspec`
- Lint: `bundle exec rubocop --autocorrect-all`
- Migrate: `bin/rails db:migrate` (status: `bin/rails db:migrate:status`)
- Routes: `bin/rails routes`
- Console: `bin/rails console`

## Structure
- `app/models/` — ActiveRecord models, validations, scopes (target ≤200 lines)
- `app/controllers/` — thin; delegate to services; render Panko serializers
- `app/services/` — business logic (single responsibility, Result objects)
- `app/serializers/` — Panko serializers (never `render json: model.to_json`)
- `app/components/`, `app/views/` — Phlex components/pages (Atomic Design)
- `app/jobs/` — Sidekiq jobs (`retry_on` transient, `discard_on` permanent)
- `db/migrate/` — reversible migrations (expand/contract for destructive ops)

## Conventions
- Service objects return Result objects; never raise for business-logic failures.
- Parameterized queries only. Authorize at the service layer (Pundit), not just controllers.
- Structured logs include `request_id`; never log passwords, tokens, or PII.
- Prefer community gems over custom code (`devise`/`devise-jwt`, `pundit`, `pagy`, `pg_search`).
