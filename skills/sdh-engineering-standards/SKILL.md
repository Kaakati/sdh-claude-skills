---
name: sdh-engineering-standards
description: Core engineering standards and tech stack for a Software Development House — Rails + Phlex backend, Python (FastAPI/Django) for AI/ML and data services, React Native, ReactJS (Vite) and Next.js on shadcn/ui, PostgreSQL/PostGIS, Redis/Sidekiq, Terraform on AWS/Vercel. Use whenever writing, reviewing, planning, or scaffolding code in this stack, choosing a library, or setting up a project. Detailed per-area conventions live in the std-* skills (each scoped by file path — load the one that fits the task); specialized work routes to the agents.
---

# SDH Engineering Standards

We are a Software Development House building production systems for clients. Quality,
maintainability, and security are non-negotiable. Prefer proven community libraries over
custom code.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Ruby on Rails | API-only, shared by all frontends |
| Backend (Python) | FastAPI (default) or Django + DRF | AI/ML serving, data pipelines; Django for admin-heavy CRUD |
| AI/ML | PyTorch, scikit-learn, MLflow | Served via FastAPI; `pgvector` for embeddings |
| View Layer | Phlex (`phlex-rails` + `class_variants`) | OO Ruby views, Atomic Design; charts through a house Stimulus controller on Chart.js |
| Serialization | Panko Serializer | High-performance JSON (never `to_json`) |
| Database | PostgreSQL + PostGIS | Geospatial relational DB |
| Mobile | React Native | Zustand, TanStack Query, Centrifugo, MMKV |
| Web (SPA) | ReactJS + Vite | React Router 8, Tailwind, shadcn/ui, Framer Motion, Chart.js via `react-chartjs-2` |
| Web (SSR) | Next.js (App Router) | Server Components, server actions, ISR/SSG, shadcn/ui, Recharts via the shadcn/ui `chart` component |
| Web UI | shadcn/ui | Component standard for Next.js and the Vite SPA — Base UI for new packages, Radix kept for existing ones; web only |
| State / Data | Zustand (client) · TanStack Query (server) | Never store server data in Zustand |
| Real-time | Centrifugo | WebSocket channels |
| Cache / Queues | Redis | Rails cache + Sidekiq |
| Cloud | AWS (primary), GCP, Vercel (Next.js) | ECS Fargate, RDS, ElastiCache, S3, CloudFront |
| Infra | Terraform + Docker Compose | All infra as code |

### Library preferences
- Auth: `devise` + `devise-jwt` · Authz: `pundit` · Pagination: `pagy` · Search: `pg_search`
- UI gates: `@casl/ability` + `@casl/react`, both on major 7 (Vite SPA, Next.js, React Native) — rules come from the Rails `/me` payload; UX only, Pundit decides
- Web UI (Next.js + Vite SPA): `shadcn/ui` — Base UI primitives for new packages, Radix kept for existing ones, never two bases in one package (read `components.json` `style`); shadcn's token names (`destructive`, `sidebar-*`, `chart-1`…`chart-5`) are registered aliases of house tokens. React Native keeps the house RN approach
- Geospatial: `rgeo`, `geocoder` · HTTP: `faraday` (Rails), `axios` (JS)
- Forms: `react-hook-form` + `zod` (web: shadcn `Field`; Next.js re-checks the schema with `safeParse` in the server action) · Navigation: `@react-navigation/native` (a root stack, one bottom tab per area, a native stack per tab)
- Web routing: `react-router` (Vite SPA) — import from `react-router`, with `RouterProvider` from `react-router/dom`
- Storage: `react-native-mmkv` · Images: `react-native-fast-image`
- Web styling: `tailwindcss` · `cn` from `@/lib/utils` (re-exports the `cn` package) in shadcn packages, `clsx` + `tailwind-merge` elsewhere · `tw-animate-css` for shadcn primitives only, under a global `prefers-reduced-motion` backstop
- Animations: `framer-motion` (page and list transitions)
- Charts, one library per stack, each chart with a text alternative: the shadcn/ui `chart` component (Recharts) in Next.js · `chart.js` 4.5.1 + `react-chartjs-2` 5.3.1 in the Vite SPA (one registration module, never `chart.js/auto`) · `chart.js` through a house Stimulus controller in Rails Phlex views (not Chartkick). ApexCharts and `react-apexcharts` are not house libraries
- Toasts: shadcn `Toast` (Base UI) or `sonner` (Radix) behind a house `notify()` that takes translation keys · Dark mode: `next-themes` (Next.js), the house theming provider (Vite SPA)
- Web testing: `vitest` + `@testing-library/react` + `msw`
- Python: `uv` + `ruff` + `mypy` · `pydantic` v2 · `httpx` · `celery` (Redis) · SQLAlchemy 2.0 + Alembic (FastAPI) / Django ORM · `pytest`
- Python AI/ML: `mlflow` · `pandera` · `onnxruntime` · `pgvector` · `anthropic` SDK
- Rails packages: `sidekiq` (jobs) · `panko_serializer` (JSON) · `phlex-rails` + `class_variants` (views) · `database_consistency` (the schema-consistency check)
- State packages: `zustand` (client state) · `@tanstack/react-query` (server state)
- Python auth packages: `pyjwt` + `argon2-cffi` (FastAPI) · `djangorestframework-simplejwt` (Django REST framework)

## Non-negotiables (summary)

- **Code**: SOLID, DRY, KISS. Functions ≤30 lines, files ≤300 (≤200 for Rails models and UI components; CLI-owned shadcn/ui primitives in the `components.json` `aliases.ui` directory are exempt). Meaningful names, no magic numbers.
- **Architecture**: Controllers → Services → Models (Rails); Screens/Pages → Hooks → API Client (frontends). Depend on abstractions.
- **Navigation**: drill-down, on every product, new and existing. The global nav lists areas only (≤7 per role on desktop, 3–5 native tabs; a breach triggers a design review), and each area's sections render in that area's own layout. Every level has a URL that holds its list state; breadcrumbs come from the API's `ancestors`; search is the second way in, and a command palette is never the only one → `@skills/ui-ux-patterns/references/drill-down-navigation.md`.
- **APIs**: drill-down-ready. One canonical parent per resource; collection routes nest one level, member routes are flat by ID; a detail carries a permission-filtered `ancestors` chain; scope, then find, at every level (404 outside scope); counts are computed inside the caller's scope → `@skills/std-api-design/references/drill-down-resources.md` (tree storage: `@skills/std-database/references/hierarchies.md`).
- **Orthogonality**: one owner per concept, one mechanism per concern per deployable, and dependencies that follow the declared context map. Look a concept up before adding a model, table, or library. A second representation kept on purpose (a read model, a denormalized column, a client-mandated library) carries an ADR and a `.claude/orthogonality.json` declaration → the `orthogonality` skill.
- **Security**: OWASP Top 10; parameterized queries only; validate input at boundaries; never commit secrets.
- **Testing**: AAA pattern; `should [behavior] when [condition]`; 80% business-logic coverage.
- **Git**: Conventional Commits; feature branches; squash-merge; no direct pushes to protected branches.

## Where the detail lives

Detailed conventions ship as `std-*` skills scoped by file path (wrapper-directory
agnostic — Rails works under `backend/`, `api/`, or repo root; a Vite app under `web/`,
`frontend/`, or root):

- Backend: `std-rails-conventions`, `std-phlex-conventions`, `std-api-design`, `std-database`, `std-monitoring`, `std-error-handling`
- Python: `std-python`, `std-fastapi`, `std-django`, `std-python-ai-ml`, `std-python-performance`
- Frontend: `std-react-native`, `std-reactjs`, `std-nextjs`, `std-shadcn-ui`, `std-accessibility`, `std-i18n`, `std-design-system`
- Cross-cutting: `std-code-standards`, `std-security`, `std-testing`, `std-clean-architecture`, `std-git-workflow`, `std-infrastructure`, `std-terraform-conventions`, `std-agent-teams`

Architecture and database orthogonality is the `orthogonality` workflow skill, which has no path
scope and loads from its description. It covers the concept lookup before adding a model, table, or
library; the ORTHOGONALITY findings the hooks report; declarations for intentional duplicates; and
the scans that double as a CI gate → `@skills/orthogonality/references/scans-and-tools.md`.

Specialized tasks route to the bundled agents (e.g. `code-reviewer`, `security-auditor`,
`architecture-advisor`, `incident-responder`, `phlex-developer`, `nextjs-developer`) and the
slash-command skills (e.g. `/rails-architect`, `/nextjs-dev`). Application roles, the permission
matrix, Pundit policies, and CASL UI gates for the product being built → `/access-control-designer`.
