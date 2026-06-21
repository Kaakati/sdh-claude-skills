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

## Project Structure

```
web/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── public/
│   └── assets/
├── src/
│   ├── main.tsx              # Entry point
│   ├── App.tsx               # Root component + providers
│   ├── router/               # React Router configuration
│   │   └── index.tsx
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

## Component Architecture

### Rules
- **Functional components only** — no class components.
- **Max 200 lines per component file** — extract sub-components or hooks when exceeded.
- **One exported component per file** — internal helper components are fine.
- **Props interface** above the component, always typed — no `any`.
- **Co-locate styles** — use Tailwind classes inline; extract to `cn()` for conditional styles.

### File Naming
- Components: `PascalCase.tsx` — e.g., `OrderTable.tsx`, `UserAvatar.tsx`
- Hooks: `useCamelCase.ts` — e.g., `useOrders.ts`, `useAuth.ts`
- Utilities: `kebab-case.ts` — e.g., `format-date.ts`, `cn.ts`
- Pages: `PascalCase.tsx` in `pages/` — e.g., `Dashboard.tsx`, `OrderDetail.tsx`

## Routing

Use `createBrowserRouter` with lazy-loaded routes:

```tsx
// src/router/index.tsx
import { createBrowserRouter } from 'react-router-dom';
import { lazy } from 'react';

const Dashboard = lazy(() => import('../pages/Dashboard'));
const Orders = lazy(() => import('../pages/Orders'));

export const router = createBrowserRouter([
  { path: '/', element: <AppLayout />, children: [
    { index: true, element: <Dashboard /> },
    { path: 'orders', element: <Orders /> },
  ]},
]);
```

- **Every route must be lazy-loaded** — no eager imports for page components.
- **Use `<Suspense>` with a fallback** at the layout level for lazy routes.
- **Auth guards** via route loader or wrapper component, not inline checks.

## State Management Rules

- **TanStack Query** for all server-fetched data — never store API responses in Zustand.
- **Zustand** for client-only state: sidebar collapsed, selected theme, table filters, draft form data.
- **No `useEffect` for data fetching** — always use `useQuery` / `useMutation`.
- **Stale time**: Set appropriate `staleTime` per query (default 30s for lists, 5min for reference data).

## Styling with Tailwind CSS

- Use `cn()` utility (clsx + tailwind-merge) for conditional classes.
- Extract repeated patterns into component variants, not CSS classes.
- Use Tailwind `@apply` sparingly — only in global styles for base elements.
- Responsive design: mobile-first with `sm:`, `md:`, `lg:` breakpoints.
- Dark mode: use `dark:` variant with class strategy.

## Forms

- **Always use `react-hook-form` + `zod`** — no uncontrolled forms, no Formik.
- Define the zod schema first, infer the TypeScript type from it.
- Display inline validation errors below each field with Tailwind styling.
- Disable submit button while `isSubmitting`.

## Performance

- **Lazy-load all page routes** with `React.lazy` + `Suspense`.
- **Memoize expensive computations** with `useMemo`; callbacks with `useCallback`.
- **Virtualize long lists** with `@tanstack/react-virtual` or `react-window`.
- **Image optimization**: Use modern formats (WebP/AVIF), lazy-load below-fold images.
- **Bundle analysis**: Use `vite-bundle-visualizer` to audit chunk sizes. Target <300KB initial JS.

## TypeScript

- **Strict mode enabled** (`strict: true` in tsconfig).
- **No `any` types** — use `unknown` and narrow with type guards.
- **Path aliases**: `@/` maps to `src/` via Vite config.
- **Infer types from zod schemas** — single source of truth for validation + types.

## Testing

- **Vitest** as test runner (Vite-native, Jest-compatible API).
- **React Testing Library** for component tests — test behavior, not implementation.
- **Query priority**: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- **MSW** (Mock Service Worker) for API mocking in tests.
- Co-locate test files: `Component.tsx` → `Component.test.tsx`.

## Anti-Patterns to Avoid

- Storing server data in Zustand (use TanStack Query).
- Eagerly importing page components (use lazy loading).
- Using `useEffect` for data fetching (use `useQuery`).
- Inline styles or CSS modules (use Tailwind).
- `any` types or missing type annotations.
- Direct axios calls from components (use API client + TanStack Query hooks).
