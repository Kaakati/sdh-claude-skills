---
name: sdh-engineering-standards
description: Core engineering standards and tech stack for a Software Development House — Rails + Phlex backend, React Native, ReactJS (Vite), Next.js, PostgreSQL/PostGIS, Redis/Sidekiq, Terraform on AWS/Vercel. Use whenever writing, reviewing, planning, or scaffolding code in this stack, choosing a library, or setting up a project. Detailed per-area conventions live in the std-* skills (each scoped by file path — load the one that fits the task); specialized work routes to the agents.
---

# SDH Engineering Standards

We are a Software Development House building production systems for clients. Quality,
maintainability, and security are non-negotiable. Prefer proven community libraries over
custom code.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Ruby on Rails | API-only, shared by all frontends |
| View Layer | Phlex (`phlex-rails` + `class_variants`) | OO Ruby views, Atomic Design |
| Serialization | Panko Serializer | High-performance JSON (never `to_json`) |
| Database | PostgreSQL + PostGIS | Geospatial relational DB |
| Mobile | React Native | Zustand, TanStack Query, Centrifugo, MMKV |
| Web (SPA) | ReactJS + Vite | React Router, Tailwind, Framer Motion, ApexCharts |
| Web (SSR) | Next.js (App Router) | Server Components, server actions, ISR/SSG |
| State / Data | Zustand (client) · TanStack Query (server) | Never store server data in Zustand |
| Real-time | Centrifugo | WebSocket channels |
| Cache / Queues | Redis | Rails cache + Sidekiq |
| Cloud | AWS (primary), GCP, Vercel (Next.js) | ECS Fargate, RDS, ElastiCache, S3, CloudFront |
| Infra | Terraform + Docker Compose | All infra as code |

### Library preferences
- Auth: `devise` + `devise-jwt` · Authz: `pundit` · Pagination: `pagy` · Search: `pg_search`
- Geospatial: `rgeo`, `geocoder` · HTTP: `faraday` (Rails), `axios` (JS)
- Forms: `react-hook-form` + `zod` · Navigation: `@react-navigation/native`
- Storage: `react-native-mmkv` · Images: `react-native-fast-image`
- Web styling: `tailwindcss` + `clsx` + `tailwind-merge` · Animations: `framer-motion` · Charts: `react-apexcharts`
- Web testing: `vitest` + `@testing-library/react` + `msw`

## Non-negotiables (summary)

- **Code**: SOLID, DRY, KISS. Functions ≤30 lines, files ≤300 (≤200 for Rails models and UI components). Meaningful names, no magic numbers.
- **Architecture**: Controllers → Services → Models (Rails); Screens/Pages → Hooks → API Client (frontends). Depend on abstractions.
- **Security**: OWASP Top 10; parameterized queries only; validate input at boundaries; never commit secrets.
- **Testing**: AAA pattern; `should [behavior] when [condition]`; 80% business-logic coverage.
- **Git**: Conventional Commits; feature branches; squash-merge; no direct pushes to protected branches.

## Where the detail lives

Detailed conventions ship as `std-*` skills scoped by file path (wrapper-directory
agnostic — Rails works under `backend/`, `api/`, or repo root; a Vite app under `web/`,
`frontend/`, or root):

- Backend: `std-rails-conventions`, `std-phlex-conventions`, `std-api-design`, `std-database`, `std-monitoring`, `std-error-handling`
- Frontend: `std-react-native`, `std-reactjs`, `std-nextjs`, `std-accessibility`, `std-i18n`, `std-design-system`
- Cross-cutting: `std-code-standards`, `std-security`, `std-testing`, `std-clean-architecture`, `std-git-workflow`, `std-infrastructure`, `std-terraform-conventions`, `std-agent-teams`

Specialized tasks route to the bundled agents (e.g. `code-reviewer`, `security-auditor`,
`rails-architect`, `architecture-advisor`, `incident-responder`) and the slash-command skills.
