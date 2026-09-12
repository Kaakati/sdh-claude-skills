---
name: reactjs-dev
description: Build ReactJS (Vite) web SPA features with React Router, Zustand client state, TanStack Query server state, Tailwind CSS styling, shadcn/ui primitives on house tokens, Framer Motion animations, Chart.js dashboards through react-chartjs-2, and drill-down navigation (area layouts, list state in the URL). Use this skill whenever someone asks to build a web page, create a Vite component, add a web dashboard, build a web SPA feature, or says things like "build the web UI for X", "create a web page for Y", "add a dashboard chart", "set up Vite routing", "build the admin panel", or "create a web form". Also trigger when someone mentions Vite configuration, Tailwind component styling, shadcn/ui components in a Vite app, Framer Motion page transitions, Chart.js or react-chartjs-2 charts, or sidebar, breadcrumb and sub-navigation structure in a Vite app.
model: sonnet
---

# ReactJS (Vite SPA) Developer

Build production-ready ReactJS web SPA features using Vite, React Router, TanStack Query, Zustand, Tailwind CSS, shadcn/ui, Framer Motion, and Chart.js through react-chartjs-2. All features consume the shared Rails API backend.

Conventions come from the `std-reactjs` skill (Vite SPA rules) and the `std-shadcn-ui` skill (primitives, the CLI, base detection).

## Development Workflow

### Step 1: Understand the Feature

1. Clarify which pages/routes are needed, which area owns them and at which drill-down level
   (list, detail, sub-detail), and which filters belong in the URL.
2. Identify data requirements — which Rails API endpoints to consume.
3. Determine client-side state needs (panel view state, sidebar, theme).
4. Check if real-time updates are needed (Centrifugo subscription).
5. Identify animations or chart requirements.
6. Read `components.json`. Its `style` names the base — `base-*` → Base UI; `radix-*`,
   `new-york` or `default` → Radix; `aria-*` → React Aria — and `components/ui/` holds the
   primitives already installed.

### Step 2: Define Domain Types

Create TypeScript types in `web/src/domain/` or `web/src/types/`:

```typescript
// web/src/domain/order.ts
export interface Order {
  id: string;
  status: OrderStatus;
  totalAmount: number;
  items: OrderItem[];
  createdAt: string;
}

export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
```

- Pure TypeScript — no React imports.
- Shared across hooks, components, and API client.

### Step 3: Build API Layer

Create TanStack Query hooks in `web/src/api/`:

```typescript
// web/src/api/orders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { Order, CreateOrderPayload } from '../domain/order';

export function useOrders(params?: { status?: string; page?: number }) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => apiClient.get<Order[]>('/api/v1/orders', { params }),
    staleTime: 30_000,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateOrderPayload) => apiClient.post('/api/v1/orders', payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  });
}
```

### Step 4: Build Page Components

Create page components in `web/src/pages/`:

- Keep pages thin — compose hooks and presentational components.
- Compose from the installed shadcn/ui primitives before adding one, in the package's base API —
  Base UI composes with `render={<Button />}`, Radix with `asChild` — and never mix bases.
- Use Tailwind CSS on house tokens for all styling.
- Wrap interactive sections in `<Suspense>` boundaries.

### Step 5: Configure Routes

Add lazy-loaded routes in `web/src/router/index.tsx`, inside their area's pathless layout route:

```tsx
const OrderList = lazy(() => import('../pages/orders/OrderList'));
// { element: <AreaLayout areaKey="orders" />, children: [{ path: 'orders', element: <OrderList />, loader: orderListLoader }] }
```

Imports come from `react-router` (React Router 8). The global sidebar lists areas only; the area
layout renders the section nav. Area layouts, list state in search params, `ScrollRestoration` and
the list crumb → `@skills/std-reactjs/references/routing-and-code-split.md`; the rules →
`@skills/ui-ux-patterns/references/drill-down-navigation.md`.

### Step 6: Add Animations (Optional)

Use Framer Motion for page transitions and micro-interactions, always through `useReducedMotion()`:

```tsx
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

const reduceMotion = useReducedMotion();

<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ opacity: 0, y: reduceMotion ? 0 : 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: reduceMotion ? 0 : -20 }}
    transition={{ duration: 0.2 }}
  >
    {children}
  </motion.div>
</AnimatePresence>
```

shadcn primitives animate themselves with `tw-animate-css`; the global reduced-motion backstop
covers them, and house code never uses those classes.

### Step 7: Add Charts (Optional)

Charts are Chart.js through react-chartjs-2 — typed components on one registration module, with
colours read from the CSS tokens:

```tsx
import '@/lib/charts/register';                // registers elements, scales, plugins — never chart.js/auto
import { Bar } from 'react-chartjs-2';
import type { ChartData, ChartOptions } from 'chart.js';
import { useChartTokens } from '@/lib/charts/useChartTokens';

const tokens = useChartTokens();               // complete hsl() values, re-read when `.dark` toggles

const data = useMemo<ChartData<'bar'>>(() => ({
  labels: points.map((p) => p.month),
  datasets: [{
    label: t('dashboard.orders.series'),       // unique: react-chartjs-2 matches datasets by label
    data: points.map((p) => p.orders),
    backgroundColor: tokens.series[1],
    hoverBackgroundColor: tokens.series[1],
  }],
}), [points, t, tokens]);

const options = useMemo<ChartOptions<'bar'>>(() => ({
  maintainAspectRatio: false,
  animation: reduceMotion ? false : { duration: 400 },
  locale: i18n.language,
  scales: {
    x: { ticks: { color: tokens.text }, grid: { color: tokens.grid } },
    y: { ticks: { color: tokens.text }, grid: { color: tokens.grid } },
  },
}), [reduceMotion, i18n.language, tokens]);

<div className="relative h-64 w-full">
  <Bar data={data} options={options} aria-label={t('dashboard.orders.title')} />
</div>
```

Then the parts a snippet cannot show — lazy-load the chart module by file path, render loading,
empty and error states before it, ship its text alternative, and test it with a canvas mock →
`@skills/std-reactjs/references/charts.md`.

### Step 8: Add Forms

Use react-hook-form + zod for all forms, rendered with shadcn's `Field` components through
`Controller` — never `npx shadcn add form`, the legacy wrapper:

```tsx
const schema = z.object({
  email: z.string().email('signup.emailInvalid'),
  name: z.string().min(1, 'signup.nameRequired'),
});
type FormData = z.infer<typeof schema>;

const form = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email: '', name: '' } });

<Controller
  name="email"
  control={form.control}
  render={({ field, fieldState }) => (
    <Field data-invalid={fieldState.invalid}>
      <FieldLabel htmlFor="email">{t('signup.email')}</FieldLabel>
      <Input {...field} id="email" type="email" aria-invalid={fieldState.invalid}
        aria-describedby={fieldState.invalid ? 'email-error' : undefined} />
      {fieldState.invalid && <FieldError id="email-error">{errorText(t, fieldState.error)}</FieldError>}
    </Field>
  )}
/>
```

`errorText` (`@/lib/form-errors`) translates client messages, which are keys, and shows a server
message as sent → `@skills/std-shadcn-ui/references/forms-and-feedback.md`. Server-side field
errors, the `ApiError` mapping, and the root error → `@skills/std-reactjs/references/forms.md`.

### Step 9: Testing

- Write Vitest + React Testing Library tests for all components.
- Mock API calls with MSW.
- Test user interactions, not implementation details.
- Priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.
- Charts: `vitest-canvas-mock` plus a `ResizeObserver` stub in setup; assert the text alternative
  and the data mapping, never pixels.
- Navigation: render the real routes for each role's `/me` fixture; assert areas only in the main
  nav, the section nav inside its area, and `aria-current`.

## Checklist Before Done

- [ ] TypeScript strict mode, no `any` types
- [ ] All routes lazy-loaded; chart modules lazy-loaded too
- [ ] Each page sits at one level of one area: the sidebar holds areas only, list state is in the URL, breadcrumbs come from `ancestors`, Back and Up tested
- [ ] Server data in TanStack Query, client-only state in Zustand
- [ ] UI composed from installed shadcn/ui primitives, in the base `components.json` names — no mixed bases
- [ ] Forms use react-hook-form + zod rendered with shadcn `Field`; errors tied to fields with `aria-describedby`
- [ ] Every chart: registered parts only (no `chart.js/auto`), memoised `data`/`options` with labelled datasets, colours from `useChartTokens`, a text alternative, `animation: false` under reduced motion, loading and empty states
- [ ] Tailwind CSS on house tokens (no inline styles, CSS modules, hex, or raw palette classes)
- [ ] Responsive design (mobile-first breakpoints)
- [ ] Accessibility: semantic HTML, keyboard navigation, ARIA labels; primitives' built-in strings passed from `t()`
- [ ] Tests written with Vitest + React Testing Library
- [ ] Bundle size checked with `vite-bundle-visualizer`

## Deep guides (read on demand, do not preload)

- Page components, auth guards, a `Field` form, composing a primitive across bases, the `cn()` utility → `references/component-patterns.md`
- Zustand with persistence, a React Router config with an area layout, the axios client with interceptors, Vitest + MSW tests → `references/data-patterns.md`
- Framer Motion page/list transitions, an order-status doughnut chart on Chart.js → `references/ui-patterns.md`

### Owned by `std-reactjs` (scoped to Vite SPA work)

These are decision-shaped and carry the bad/good pairs. The three files above are worked
*patterns*; these answer *which* pattern and why:

- **State placement — Zustand vs TanStack Query vs the URL vs local** → `@skills/std-reactjs/references/state-placement.md`
- **Data fetching (TanStack Query + axios), `staleTime`/`gcTime`, key factories per drill level** → `@skills/std-reactjs/references/data-fetching.md`
- **Routing (React Router 8), area layouts and list state, code splitting, and the bundle budget** → `@skills/std-reactjs/references/routing-and-code-split.md`
- **Forms (react-hook-form + zod, shadcn `Field`)** → `@skills/std-reactjs/references/forms.md`
- **Testing (Vitest + RTL + MSW)** → `@skills/std-reactjs/references/testing.md`
- **Animation (Framer Motion; `tw-animate-css` scope and backstop)** → `@skills/std-reactjs/references/animation.md`
- **Charts (Chart.js via react-chartjs-2)** → `@skills/std-reactjs/references/charts.md`

**Initial JS budget: < 300KB minified/uncompressed** — enforced by `chunkSizeWarningLimit: 300`
in `vite.config.ts`, so it is a number the build already checks. `staleTime` is deliberately
*per query*, not one default: `data-fetching.md` has the table.

### Owned by `std-shadcn-ui` (primitives in both web frontends)

- **Base detection, the CLI (`add --dry-run`, `add --diff`), what never runs without a human** → `@skills/std-shadcn-ui/references/cli-and-registry.md`
- **The primitive catalog, blocks, and where compositions live** → `@skills/std-shadcn-ui/references/components-and-blocks.md`
- **`Field` wiring for every control, toasts by base behind `notify()`** → `@skills/std-shadcn-ui/references/forms-and-feedback.md`
- **Primitive label props, RTL, focus-ring contrast** → `@skills/std-shadcn-ui/references/accessibility-and-i18n.md`

### Owned by `ui-ux-patterns` and `std-api-design`

- **Drill-down navigation — levels, location cues, Up and Back, what the sidebar holds** → `@skills/ui-ux-patterns/references/drill-down-navigation.md`
- **The endpoints behind each level — `ancestors`, list parameters, search** → `@skills/std-api-design/references/drill-down-resources.md`

### Owned by `access-control-designer`

- **Permission-gated routes, nav, and actions** (a CASL ability from the `['me']` query, keyed by
  permission, never role) → `@skills/access-control-designer/references/ui-gates.md`
