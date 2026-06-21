# Web SPA (ReactJS + Vite) — package conventions

Copy this file into your Vite SPA package directory as `CLAUDE.md`. The directory
can be named anything — `web/`, `frontend/`, `spa/` — detection is wrapper-agnostic
(`vite.config.*` / `index.html` / `src/pages/`). Layers on the root `CLAUDE.md`.

ReactJS SPA: React Router, Zustand (client state), TanStack Query (server state),
Tailwind CSS, Framer Motion, ApexCharts. Standards in the root `.claude/rules/`
(`reactjs`, `accessibility`, `i18n`, `testing`, `clean-architecture`) auto-load.

## Commands
- Dev: `npm run dev`
- Build: `npm run build`
- Tests: `npx vitest`
- Types: `npx tsc --noEmit`

## Structure
- `src/pages/` — route page components (target ≤200 lines)
- `src/components/` — UI components (Atomic Design; `components/ui/` = primitives)
- `src/hooks/` — TanStack Query hooks
- `src/stores/` — Zustand stores (client-only state)
- `src/api/` — axios API client + query hooks
- `src/router/` — React Router config (lazy-loaded routes)
- `src/domain/` — pure TypeScript types
- `src/styles/`, `src/i18n/` — Tailwind layers and locale config

## Conventions
- Server state → TanStack Query; client state → Zustand. Never store server data in Zustand.
- Style with Tailwind + design tokens (`bg-primary`, not hardcoded colors); merge with `clsx`/`tailwind-merge`.
- Accessibility: semantic HTML, label/`htmlFor`, `alt` text, visible focus (`focus-visible`).
- Tests: Vitest + React Testing Library + MSW. No hardcoded strings — use i18n keys.
