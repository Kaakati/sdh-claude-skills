---
name: reactjs-dev
description: Build ReactJS (Vite) web SPA features with React Router, Zustand client state, TanStack Query server state, Tailwind CSS styling, Framer Motion animations, and ApexCharts dashboards. Use this skill whenever someone asks to build a web page, create a Vite component, add a web dashboard, build a web SPA feature, or says things like "build the web UI for X", "create a web page for Y", "add a dashboard chart", "set up Vite routing", "build the admin panel", or "create a web form". Also trigger when someone mentions Vite configuration, Tailwind component styling, Framer Motion page transitions, or ApexCharts integration.
model: sonnet
---

# ReactJS (Vite SPA) Developer

Build production-ready ReactJS web SPA features using Vite, React Router, TanStack Query, Zustand, Tailwind CSS, Framer Motion, and ApexCharts. All features consume the shared Rails API backend.

the `std-reactjs` skill

## Development Workflow

### Step 1: Understand the Feature

1. Clarify which pages/routes are needed and their URL structure.
2. Identify data requirements — which Rails API endpoints to consume.
3. Determine client-side state needs (filters, sidebar, theme).
4. Check if real-time updates are needed (Centrifugo subscription).
5. Identify animations or chart requirements.

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
- Use Tailwind CSS for all styling.
- Wrap interactive sections in `<Suspense>` boundaries.

### Step 5: Configure Routes

Add lazy-loaded routes in `web/src/router/index.tsx`:

```tsx
const OrdersPage = lazy(() => import('../pages/Orders'));
// Add to router config with appropriate auth guards
```

### Step 6: Add Animations (Optional)

Use Framer Motion for page transitions and micro-interactions:

```tsx
import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence mode="wait">
  <motion.div
    key={pathname}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -20 }}
    transition={{ duration: 0.2 }}
  >
    {children}
  </motion.div>
</AnimatePresence>
```

### Step 7: Add Charts (Optional)

Use ApexCharts for dashboard visualizations:

```tsx
import Chart from 'react-apexcharts';

<Chart
  type="area"
  height={350}
  options={{ chart: { id: 'revenue' }, xaxis: { categories: months } }}
  series={[{ name: 'Revenue', data: revenueData }]}
/>
```

### Step 8: Add Forms

Use react-hook-form + zod for all forms:

```tsx
const schema = z.object({ email: z.string().email(), name: z.string().min(1) });
type FormData = z.infer<typeof schema>;

const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
  resolver: zodResolver(schema),
});
```

### Step 9: Testing

- Write Vitest + React Testing Library tests for all components.
- Mock API calls with MSW.
- Test user interactions, not implementation details.
- Priority: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.

## Checklist Before Done

- [ ] TypeScript strict mode, no `any` types
- [ ] All routes lazy-loaded
- [ ] Server data in TanStack Query, client-only state in Zustand
- [ ] Forms use react-hook-form + zod
- [ ] Tailwind CSS for all styling (no inline styles or CSS modules)
- [ ] Responsive design (mobile-first breakpoints)
- [ ] Accessibility: semantic HTML, keyboard navigation, ARIA labels
- [ ] Tests written with Vitest + React Testing Library
- [ ] Bundle size checked with `vite-bundle-visualizer`

## Deep guides (read on demand, do not preload)

- Page components, auth guards, react-hook-form + zod + Tailwind, the `cn()` utility → `references/component-patterns.md`
- Zustand with persistence, React Router config, the axios client with interceptors, Vitest + MSW tests → `references/data-patterns.md`
- Framer Motion page/list transitions, ApexCharts revenue and donut charts → `references/ui-patterns.md`

### Owned by `std-reactjs` (scoped to Vite SPA work)

These are decision-shaped and carry the bad/good pairs. The three files above are worked
*patterns*; these answer *which* pattern and why:

- **State placement — Zustand vs TanStack Query vs local** → `@skills/std-reactjs/references/state-placement.md`
- **Data fetching (TanStack Query + axios), `staleTime`/`gcTime`, key factories** → `@skills/std-reactjs/references/data-fetching.md`
- **Routing, code splitting, and the bundle budget** → `@skills/std-reactjs/references/routing-and-code-split.md`
- **Forms (react-hook-form + zod)** → `@skills/std-reactjs/references/forms.md`
- **Testing (Vitest + RTL + MSW)** → `@skills/std-reactjs/references/testing.md`
- **Animation (Framer Motion)** → `@skills/std-reactjs/references/animation.md`
- **Charts (ApexCharts)** → `@skills/std-reactjs/references/charts.md`

**Initial JS budget: < 300KB minified/uncompressed** — enforced by `chunkSizeWarningLimit: 300`
in `vite.config.ts`, so it is a number the build already checks. `staleTime` is deliberately
*per query*, not one default: `data-fetching.md` has the table.
