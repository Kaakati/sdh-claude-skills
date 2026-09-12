---
name: std-reactjs
description: ReactJS Vite SPA conventions — React Router 8, drill-down routing (area layouts, list state in the URL), Zustand, TanStack Query, Tailwind, shadcn/ui primitives on house tokens, Framer Motion, Chart.js through react-chartjs-2. Use when building Vite web SPA pages or components.
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
| Build | Vite 8 (Rolldown) | TypeScript, path aliases via `@/`; vendor chunks are Rolldown `codeSplitting` groups |
| Routing | React Router 8 (`react-router`) | Data router: `createBrowserRouter`, lazy pages, one pathless layout route per area; `RouterProvider` from `react-router/dom` |
| Server State | TanStack Query | All API data — never in Zustand |
| Client State | Zustand | UI preferences, sidebar, theme, panel filters |
| HTTP | axios | Shared instance with interceptors |
| Styling | Tailwind CSS | Utility-first on house tokens; `cn()` from `@/lib/utils` |
| Components | shadcn/ui | Primitives copied into `components/ui/` on house tokens; Base UI for new packages, an existing Radix package stays Radix |
| Forms | react-hook-form + zod | Schema-first validation, rendered with shadcn `Field` |
| Animations | Framer Motion | Page transitions, micro-interactions; `tw-animate-css` only inside shadcn primitives |
| Charts | Chart.js 4.5.1 via react-chartjs-2 5.3.1 | One registration module (never `chart.js/auto`); colours read from the `--chart-N` tokens at runtime |
| i18n | react-i18next | Locale detection via `navigator.language` |
| Testing | Vitest + React Testing Library | Co-located test files |

## Project Structure

```
web/
├── index.html
├── vite.config.ts
├── components.json           # shadcn/ui — `style` names the base; aliases; the Tailwind CSS entry
├── tsconfig.json
├── public/assets/
├── src/
│   ├── main.tsx              # Entry point — RouterProvider from react-router/dom
│   ├── App.tsx               # Root component + providers (theme, i18n, Query, toaster)
│   ├── router/index.tsx      # React Router configuration — exports `routes` and `router`
│   ├── pages/                # Page-level components (one per route), grouped by area
│   ├── components/           # House compositions on the atomic ladder — molecules/, organisms/, templates/
│   │   └── ui/               # shadcn/ui primitives — the atom tier, CLI-owned, kebab-case
│   ├── hooks/                # Custom hooks (business logic, use cases)
│   ├── stores/               # Zustand stores (client-only state)
│   ├── api/                  # API client (axios) and TanStack Query hooks
│   ├── domain/               # Domain types, interfaces, business rules
│   ├── types/                # Shared TypeScript types
│   ├── lib/                  # utils.ts (`cn`), nav.ts (areas → sections), charts/ (register, tokens), form-errors.ts, notify.ts
│   ├── i18n/                 # react-i18next setup and locale files
│   └── styles/               # Tailwind entry: tokens, @theme inline, reduced-motion backstop
└── tests/
    ├── setup.ts              # Vitest setup
    └── utils.tsx             # Test utilities (render with providers)
```

## Component Architecture

- **Functional components only** — no class components.
- **Max 200 lines per component file** — extract sub-components or hooks when exceeded. The limit
  governs house components; shadcn primitives in `components/ui/` are CLI output and are never
  split, moved, or renamed — the CLI finds them by path.
- **One exported component per file** — internal helper components are fine.
- **Props interface** above the component, always typed — no `any`.
- **Co-locate styles** — Tailwind classes inline; `cn()` for conditional styles.

### File Naming
- Components: `PascalCase.tsx` — `OrderTable.tsx`, `UserAvatar.tsx`
- shadcn primitives: kebab-case, as the CLI wrote them — `components/ui/button.tsx`, `components/ui/card.tsx`
- Hooks: `useCamelCase.ts` — `useOrders.ts`, `useAuth.ts`
- Utilities: `kebab-case.ts` — `format-date.ts`; `cn` lives in `lib/utils.ts`
- Pages: `PascalCase.tsx` in `pages/` — `Dashboard.tsx`, `orders/OrderDetail.tsx`

## The Four Non-Negotiables

1. **TanStack Query owns all server data. Zustand owns client-only state.** Never store an API
   response in Zustand. A list's filters, sort and query live in the URL; a panel's view state and
   the theme live in Zustand; results come back from Query keyed by them.
2. **No `useEffect` for data fetching** — `useQuery` / `useMutation` only. Components never call
   axios directly: component → hook → API client.
3. **Every page route is lazy-loaded** with `React.lazy`, under a layout-level `<Suspense>`.
   Auth guards are route loaders or a guard layout, never inline checks in a page body.
   Permission gates are the same loaders plus a CASL ability built from the `['me']` query —
   checked by permission key, never role name → `@skills/access-control-designer/references/ui-gates.md`.
   Each area is a pathless layout route that renders its section nav and its own `<Suspense>`
   around `<Outlet />`; `<ScrollRestoration />` renders once → `references/routing-and-code-split.md`.
4. **Strict TypeScript, no `any`.** Requires `"strict": true` in `tsconfig.json`; `@/` must map
   to `src/` (path alias configured in `vite.config.ts` + `tsconfig.json`).
   Use `unknown` + type guards. Infer types from zod schemas —
   the schema is the single source of truth for validation *and* types.

## Navigation (drill-down)

- **The global sidebar holds areas only**, from `visibleNav(NAV, ability, entitlements)` — never
  sections, never a nested `SidebarMenuSub`. Sections render only in the area's own layout.
- **Every level has a URL** — area → overview → list → detail → sub-detail, member URLs flat by
  ID. Filters, sort and query are search params: a filter change pushes a history entry, typing
  replaces it.
- **Breadcrumbs come from the API's `ancestors`**, never from route params or history. Up is a
  real link, never `history.back()`.
- **Import from `react-router`.** React Router 8 removed the `react-router-dom` package; a package
  still on v7 keeps one name until it upgrades, never both.
- The rules → `@skills/ui-ux-patterns/references/drill-down-navigation.md`; the API contract →
  `@skills/std-api-design/references/drill-down-resources.md`; the React Router mechanics →
  `references/routing-and-code-split.md`.

## UI Primitives (shadcn/ui)

- **Read `components.json` before writing UI.** Its `style` names the base: `base-*` → Base UI;
  `radix-*`, `new-york` or `default` → Radix; `aria-*` → React Aria. Write that base's API — Base
  UI composes with `render={<Button />}`, Radix with `asChild` — and never mix bases in one
  package. New packages start on Base UI; an existing Radix package stays on Radix.
- **Reuse before `add`.** An installed primitive beats a new one, and a new one comes in through
  the package's own CLI (`add --dry-run`, then `add`), never pasted. `init` on an existing app,
  `--overwrite`, `apply`, `eject` and `mcp init` wait for the human.
- **Primitives are the atoms; house compositions climb the ladder.** Molecules, organisms and
  templates compose primitives (the `atomic-design` skill). A heavy module — a chart — is imported
  by its file path, never through its directory's `index.ts`.
- **Every English string a primitive ships becomes a label prop filled from `t()`.**
- **Charts are Chart.js through react-chartjs-2, not a shadcn primitive.** shadcn's `chart`
  (Recharts) is the Next.js standard and never enters a Vite package → `references/charts.md`.

## Styling with Tailwind CSS

- Use `cn()` from `@/lib/utils` for conditional classes. In a shadcn package that file is
  `export { cn } from "cn"` — the package every registry component imports; a package without
  shadcn/ui may keep `clsx` + `tailwind-merge` behind the same import.
- Extract repeated patterns into `cva` variants, not CSS classes.
- `@apply` sparingly — only in global styles for base elements.
- Mobile-first responsive: `sm:`, `md:`, `lg:`.
- Dark mode is the `.dark` class, toggled by the house theming provider. Tailwind v4's `dark:`
  follows `prefers-color-scheme` until the CSS entry declares `@custom-variant dark (&:is(.dark *))`.
- Design tokens only — no literal hex, no raw palette classes. Code you write names the house role
  (`bg-error`); shadcn's names (`destructive`, `sidebar-*`) are registered aliases so vendored
  primitives compile as shipped. Chart colours are the `--chart-N` tokens read at runtime — a
  canvas cannot resolve `var()`.

## Forms

- Always `react-hook-form` + `zod`, rendered with shadcn's `Field`, `FieldLabel` and `FieldError`
  through RHF's `Controller`. No Formik, and never `npx shadcn add form` — the legacy wrapper.
- Define the zod schema first, `z.infer` the type from it; its messages are translation keys.
- `aria-invalid` on the control and `aria-describedby` pointing at the `FieldError`.
- Disable the submit button while `isSubmitting`.
- A field error stays under its field — never a toast.

## Performance

- **Lazy-load all page routes**; also lazy-load heavy leaf deps (chart modules, editors).
- **Memoize** expensive computations with `useMemo`, callbacks with `useCallback`.
- **Virtualize long lists** with `@tanstack/react-virtual` or `react-window`.
- **Images**: modern formats (WebP/AVIF), lazy-load below the fold.
- **Bundle budget: <300KB initial JS.** Audit with `vite-bundle-visualizer`.
- **Animate `transform` and `opacity` only**; always honour `prefers-reduced-motion` — Framer
  Motion through `useReducedMotion()`, Chart.js through `animation: false`, shadcn primitives
  through the global CSS backstop.

## Testing

- **Vitest** runner, **React Testing Library** for components — test behavior, not implementation.
- **Query priority**: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- **MSW** for API mocking — never `vi.mock` axios or your own query hooks.
- Co-locate: `Component.tsx` → `Component.test.tsx`.
- Coverage: 80% business logic, 60% overall minimum.
- **Charts**: `vitest-canvas-mock` plus a `ResizeObserver` stub in setup — jsdom has neither a 2D
  context nor the observer. Assert the text alternative and the data mapping, never pixels.
- **Navigation per role**: render the real routes for each role's `/me` fixture and assert areas
  only in the main nav, the section nav inside its area, and `aria-current`.
- **Portaled primitives** (dialogs, menus, popovers) render into `document.body` — query them
  with `screen`.

## Anti-Patterns to Avoid

- Storing server data in Zustand (use TanStack Query).
- Eagerly importing page components (use lazy loading).
- Using `useEffect` for data fetching (use `useQuery`).
- Inline styles or CSS modules (use Tailwind).
- `any` types or missing type annotations.
- Direct axios calls from components (use API client + TanStack Query hooks).
- `import 'chart.js/auto'`, a literal or `var()` chart colour, or chart `data`/`options` rebuilt on every render.
- Sections nested under areas in the global sidebar, list filters kept outside the URL, or a Back button calling `history.back()`.
- Importing from `react-router-dom` in a React Router 8 package.
- Mixing Base UI and Radix primitives in one package, or `asChild` on a Base UI primitive.
- Renaming, moving, or splitting CLI-owned primitives in `components/ui/`.

## Deep guides (read on demand, do not preload)

- Where state lives (Query vs. URL vs. Zustand vs. local), server-data-in-Zustand failure modes, Zustand store shape & selectors → `references/state-placement.md`
- Query key factories (hierarchical keys per drill level), `staleTime`/`gcTime`, mutations & optimistic updates, invalidating ancestors, axios client & interceptors → `references/data-fetching.md`
- React Router 8 imports, loader vs. `useQuery` (`queryClient.query`), areas as pathless layout routes, list state in search params, `ScrollRestoration`, chunk splitting (chart modules as heavy leaves, Vite 8 `codeSplitting` vendor groups), prefetch on intent, bundle budget audit → `references/routing-and-code-split.md`
- Chart.js via react-chartjs-2 — the registration module, lazy chart modules, memoised `data`/`options`, tokens read from CSS variables, reduced motion, text alternatives, StrictMode, testing with a canvas mock → `references/charts.md`
- Framer Motion reduced motion, `tw-animate-css` scope and its mandatory backstop, transform-only rule, page & list transitions → `references/animation.md`
- react-hook-form + zod rendered with shadcn `Field`, `ApiError` mapping onto fields → `references/forms.md`
- Provider test harness, MSW handlers, RTL assertions, form tests, charts, navigation per role, Zustand reset → `references/testing.md`

## Owned elsewhere — do not duplicate

- Drill-down navigation rules — levels, location cues, Up and Back, what the sidebar holds, the command palette → `@skills/ui-ux-patterns/references/drill-down-navigation.md`
- The endpoints behind each level — `ancestors`, list parameters, search → `@skills/std-api-design/references/drill-down-resources.md`
- Next.js charts (shadcn `chart`, Recharts) → `@skills/std-shadcn-ui/references/charts.md`
- The shadcn/ui protocol — base detection, CLI safety, the registry → `@skills/std-shadcn-ui/references/cli-and-registry.md`
- The primitive catalog, blocks, the Base UI vs Radix API table, and where compositions live → `@skills/std-shadcn-ui/references/components-and-blocks.md`
- `Field` wiring for every control, the `TextField` molecule, toasts by base behind the house `notify()` → `@skills/std-shadcn-ui/references/forms-and-feedback.md`
- Primitive label props, RTL, focus-ring contrast → `@skills/std-shadcn-ui/references/accessibility-and-i18n.md`
- The token registry, including the shadcn aliases → `@skills/theming/references/platform-integration.md`
