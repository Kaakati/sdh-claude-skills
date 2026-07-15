---
name: std-reactjs
description: ReactJS Vite SPA conventions — React Router, Zustand, TanStack Query, Tailwind, Framer Motion, ApexCharts. Use when building Vite web SPA pages or components.
paths:
  - "**/vite.config.*"
  - "**/index.html"
  - "**/src/pages/**/*.ts"
  - "**/src/pages/**/*.tsx"
  - "**/src/pages/**/*.jsx"
---

# ReactJS (Vite SPA) Conventions

Rules for building ReactJS single-page applications with Vite, consuming the shared Rails API backend.

## Technology Stack

| Concern | Library | Notes |
|---------|---------|-------|
| Build | Vite | TypeScript, path aliases via `@/` |
| Routing | React Router v6+ | Lazy-loaded routes, `createBrowserRouter` |
| Server State | TanStack Query | All API data — never in Zustand |
| Client State | Zustand | UI preferences, sidebar, theme, filters |
| HTTP | axios | Shared instance with interceptors |
| Styling | Tailwind CSS | Utility-first, `cn()` helper with `clsx` + `tailwind-merge` |
| Forms | react-hook-form + zod | Schema-first validation |
| Animations | Framer Motion | Page transitions, micro-interactions |
| Charts | ApexCharts (react-apexcharts) | Dashboards and data visualization |
| i18n | react-i18next | Locale detection via `navigator.language` |
| Testing | Vitest + React Testing Library | Co-located test files |

## Project Structure

```
web/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── public/assets/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Root component + providers
│   ├── router/index.tsx      # React Router configuration
│   ├── pages/                # Page-level components (one per route)
│   ├── components/           # Shared presentational components
│   │   └── ui/               # Design system primitives
│   ├── hooks/                # Custom hooks (business logic, use cases)
│   ├── stores/               # Zustand stores (client-only state)
│   ├── api/                  # API client (axios) and TanStack Query hooks
│   ├── domain/               # Domain types, interfaces, business rules
│   ├── types/                # Shared TypeScript types
│   ├── lib/                  # Utility functions and helpers
│   ├── i18n/                 # react-i18next setup and locale files
│   └── styles/               # Global CSS and Tailwind config
└── tests/
    ├── setup.ts              # Vitest setup
    └── utils.tsx             # Test utilities (render with providers)
```

## Component Architecture

- **Functional components only** — no class components.
- **Max 200 lines per component file** — extract sub-components or hooks when exceeded.
- **One exported component per file** — internal helper components are fine.
- **Props interface** above the component, always typed — no `any`.
- **Co-locate styles** — Tailwind classes inline; `cn()` for conditional styles.

### File Naming
- Components: `PascalCase.tsx` — `OrderTable.tsx`, `UserAvatar.tsx`
- Hooks: `useCamelCase.ts` — `useOrders.ts`, `useAuth.ts`
- Utilities: `kebab-case.ts` — `format-date.ts`, `cn.ts`
- Pages: `PascalCase.tsx` in `pages/` — `Dashboard.tsx`, `OrderDetail.tsx`

## The Four Non-Negotiables

1. **TanStack Query owns all server data. Zustand owns client-only state.** Never store an API
   response in Zustand. Filters/sort/theme go in Zustand; results come back from Query keyed by them.
2. **No `useEffect` for data fetching** — `useQuery` / `useMutation` only. Components never call
   axios directly: component → hook → API client.
3. **Every page route is lazy-loaded** with `React.lazy`, under one layout-level `<Suspense>`.
   Auth guards are route loaders or a guard layout, never inline checks in a page body.
4. **Strict TypeScript, no `any`.** Requires `"strict": true` in `tsconfig.json`; `@/` must map
   to `src/` (path alias configured in `vite.config.ts` + `tsconfig.json`).
   Use `unknown` + type guards. Infer types from zod schemas —
   the schema is the single source of truth for validation *and* types.

## Styling with Tailwind CSS

- Use `cn()` (clsx + tailwind-merge) for conditional classes.
- Extract repeated patterns into component variants, not CSS classes.
- `@apply` sparingly — only in global styles for base elements.
- Mobile-first responsive: `sm:`, `md:`, `lg:`.
- Dark mode via the `dark:` variant, class strategy.
- Use design tokens, not literal hex values.

## Forms

- Always `react-hook-form` + `zod` — no uncontrolled forms, no Formik.
- Define the zod schema first, `z.infer` the type from it.
- Inline validation errors below each field, associated via `aria-describedby`.
- Disable the submit button while `isSubmitting`.

## Performance

- **Lazy-load all page routes**; also lazy-load heavy leaf deps (ApexCharts, editors).
- **Memoize** expensive computations with `useMemo`, callbacks with `useCallback`.
- **Virtualize long lists** with `@tanstack/react-virtual` or `react-window`.
- **Images**: modern formats (WebP/AVIF), lazy-load below the fold.
- **Bundle budget: <300KB initial JS.** Audit with `vite-bundle-visualizer`.
- **Animate `transform` and `opacity` only**; always honour `prefers-reduced-motion`.

## Testing

- **Vitest** runner, **React Testing Library** for components — test behavior, not implementation.
- **Query priority**: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- **MSW** for API mocking — never `vi.mock` axios or your own query hooks.
- Co-locate: `Component.tsx` → `Component.test.tsx`.
- Coverage: 80% business logic, 60% overall minimum.

## Anti-Patterns to Avoid

- Storing server data in Zustand (use TanStack Query).
- Eagerly importing page components (use lazy loading).
- Using `useEffect` for data fetching (use `useQuery`).
- Inline styles or CSS modules (use Tailwind).
- `any` types or missing type annotations.
- Direct axios calls from components (use API client + TanStack Query hooks).

## Deep guides (read on demand, do not preload)

- State placement, query keys, `staleTime`, mutations & optimistic updates, axios interceptors, Zustand store shape → `references/state-and-data.md`
- Router setup, loader vs. `useQuery`, chunk splitting, prefetch on intent, bundle budget audit → `references/routing-and-code-split.md`
- ApexCharts options/memoization/a11y, Framer Motion reduced motion, page & list transitions → `references/charts-and-animation.md`
- react-hook-form + zod patterns, API error mapping, provider test harness, MSW handlers, RTL assertions → `references/forms-and-testing.md`
