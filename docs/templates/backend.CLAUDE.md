# Backend (Rails API) — package conventions

Copy this file into your Rails package directory as `CLAUDE.md`. The directory can
be named anything — `backend/`, `api/`, `server/` — detection is wrapper-agnostic.
This file loads automatically when Claude works in this package (or starts here);
it layers on top of the repository-root `CLAUDE.md`.

Rails API-only backend: Phlex views, Panko serializers, PostgreSQL + PostGIS,
Redis/Sidekiq, Centrifugo. Full standards ship as the `sdh` plugin's path-scoped `std-*` skills
(`std-rails-conventions`, `std-phlex-conventions`, `std-api-design`, `std-database`, `std-monitoring`,
`std-clean-architecture`) — scoping limits when a skill applies, so read the one bearing
on your change.

## Commands
- Tests: `bundle exec rspec`
- Lint: `bundle exec rubocop` (safe fixes: `--autocorrect`; run `-A` only by hand and read the diff)
- Migrate: `bin/rails db:migrate` (status: `bin/rails db:migrate:status`)
- Routes: `bin/rails routes`
- Console: `bin/rails console`

## Structure
- `app/models/` — ActiveRecord models, validations, scopes (target ≤200 lines)
- `app/controllers/` — thin; delegate to services; render Panko serializers
- `app/services/` — business logic (single responsibility, Result objects)
- `app/serializers/` — Panko serializers (never `render json: model.to_json`); detail serializers carry `ancestors`
- `app/components/`, `app/views/` — Phlex components/pages (Atomic Design)
- `app/javascript/controllers/` — Stimulus controllers, including the house `chart` controller
- `app/jobs/` — Sidekiq jobs (`retry_on` transient, `discard_on` permanent)
- `db/migrate/` — reversible migrations (expand/contract for destructive ops)

## Conventions
- Service objects return Result objects; never raise for business-logic failures.
- Parameterized queries only. Authorize at the service layer (Pundit), not just controllers.
- Pundit policies check permission keys (`orders.update`), never role names; `/me` returns the user's rules for frontend CASL gates.
- APIs are drill-down-ready: collection routes nest one level under their one canonical parent, and member routes are flat by ID (shallow routes). Find the parent through `policy_scope` before the child (404 outside scope); detail serializers carry a permission-filtered `ancestors` chain; badge counts are computed inside the caller's scope. The contract is `std-api-design`'s drill-down resources reference; tree storage is `std-database`'s hierarchies reference.
- Phlex navigation is drill-down: the controller builds the visible areas and breadcrumb items, the global sidebar lists areas only, and each area's layout renders its section nav. Row links into a list-detail frame use `data-turbo-action="advance"`.
- Charts in Phlex views: Chart.js 4.5.1 through the house `chart` Stimulus controller, never Chartkick, with a caption, summary and data table outside the canvas. Importmap apps commit a single-file build instead of `bin/importmap pin chart.js`.
- Structured logs include `request_id`; never log passwords, tokens, or PII.
- Prefer community gems over custom code (`devise`/`devise-jwt`, `pundit`, `pagy`, `pg_search`).
