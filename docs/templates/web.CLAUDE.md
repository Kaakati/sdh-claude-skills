# Web SPA (ReactJS + Vite) — package conventions

Copy this file into your Vite SPA package directory as `CLAUDE.md`. The directory
can be named anything — `web/`, `frontend/`, `spa/` — detection is wrapper-agnostic
(`vite.config.*` / `index.html` / `src/pages/`). Layers on the root `CLAUDE.md`.

ReactJS SPA: React Router 8, Zustand (client state), TanStack Query (server state),
Tailwind CSS, shadcn/ui (Base UI by default; an existing Radix package stays on Radix), Framer Motion,
Chart.js through `react-chartjs-2`. Standards ship as the `sdh` plugin's path-scoped `std-*` skills
(`std-reactjs`, `std-shadcn-ui`, `std-accessibility`, `std-i18n`, `std-testing`, `std-clean-architecture`). Scoping
limits when a skill applies; it does not open the skill for you — read the one bearing on your change.

## Commands
- Dev: `npm run dev`
- Build: `npm run build`
- Tests: `npx vitest`
- Types: `npx tsc --noEmit`

## Structure
- `src/pages/` — route page components (target ≤200 lines)
- `src/components/` — UI components (Atomic Design)
- `src/components/ui/` — shadcn/ui primitives the CLI owns (kebab-case files; never split them — the hooks exempt them from the size checks)
- `components.json` — shadcn config; its `style` names the primitive base (`base-*` → Base UI, `radix-*`/`new-york` → Radix)
- `src/lib/utils.ts` — `cn` (re-exports the `cn` package)
- `src/lib/nav.ts` — `NAV: Area[]` (areas with their sections), filtered per role by `visibleNav`
- `src/lib/charts/register.ts` — the one Chart.js registration module
- `src/hooks/` — TanStack Query hooks
- `src/stores/` — Zustand stores (client-only state)
- `src/api/` — axios API client + query hooks
- `src/router/` — React Router config: each area a pathless layout route whose layout renders its section nav; routes lazy-loaded
- `src/domain/` — pure TypeScript types
- `src/styles/`, `src/i18n/` — Tailwind layers and locale config

## Conventions
- Server state → TanStack Query; client state → Zustand. Never store server data in Zustand.
- Permission gates: a CASL ability built from the `['me']` query, checked by permission key, never role name.
- Navigation is drill-down: the global sidebar lists areas only (no nested sections), and each area's layout renders its sections. List filters, sort and query live in search params; breadcrumbs come from the API's `ancestors`; the active item comes from `areaState` (whole path segments), never `pathname.startsWith`. Test the navigation rendered per role.
- Routing: import from `react-router`, with `RouterProvider` from `react-router/dom`. React Router 8 removed `react-router-dom`; an app still on React 18 stays on v7.
- Style with Tailwind + design tokens (`bg-primary`, not hardcoded colors); merge classes with `cn` from `@/lib/utils`. shadcn's token names (`destructive`, `sidebar-*`, `chart-1`…`chart-5`) are registered aliases so stock primitives compile; code you write names the house role (`bg-error`).
- Components: write the base's API (`render` on Base UI, `asChild` on Radix). Preview with `shadcn add --dry-run` / `--diff`; ask a human before `init`, `apply`, `--overwrite`, or `eject`.
- Forms: shadcn `Field` + `react-hook-form` + `zod`. Toasts go through the house `notify()` helper (translation keys), never for field errors.
- Charts: Chart.js 4.5.1 via `react-chartjs-2` 5.3.1. Register only what a chart uses (never `chart.js/auto`), lazy-load chart modules, read colours from the CSS tokens (`useChartTokens`), turn animation off under reduced motion, and render a text alternative (a summary or a data table) outside the canvas. Tests add `vitest-canvas-mock` and a `ResizeObserver` stub. shadcn's `chart` (Recharts) is for Next.js only.
- Accessibility: semantic HTML, label/`htmlFor`, `alt` text, visible focus (`focus-visible`).
- Tests: Vitest + React Testing Library + MSW. No hardcoded strings — use i18n keys.
