# Clean Architecture on ReactJS (Vite SPA)

Layer mapping, rules, and boundary violations for the Vite single-page app (React Router +
Tailwind CSS + shadcn/ui primitives + Framer Motion + Chart.js through react-chartjs-2 +
TanStack Query + Zustand).

**The rule this file enforces:** dependencies point inward. Entities (domain types, domain utils)
know nothing about use cases, pages, or frameworks. Use cases (hooks) know about entities but not
about pages or React components. Interface adapters (pages, components, chart modules, API client,
router config) translate between use cases and external concerns. Frameworks (React, Vite,
TanStack Query, Zustand, React Router, shadcn/ui primitives, Chart.js and react-chartjs-2) are
implementation details — pluggable and replaceable.

## Decision: which layer does this Vite SPA file belong to?

| Clean Architecture Layer | Vite SPA Component | Directory |
|--------------------------|-------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils (including the functions that shape chart data) | `web/src/domain/`, `web/src/types/` |
| Use Cases | Custom hooks (business logic + data fetching) | `web/src/hooks/`, `web/src/api/` |
| Interface Adapters | Pages, house components, chart modules, API client, router config | `web/src/pages/`, `web/src/components/`, `web/src/api/`, `web/src/router/` |
| Frameworks | React, Vite, TanStack Query, Zustand, React Router, shadcn/ui primitives, Chart.js, react-chartjs-2 | Framework code, and the CLI-owned `web/src/components/ui/` |

Rules per component:

- **Domain types** are pure TypeScript — no React, no framework dependencies.
- **Hooks** encapsulate business logic and data fetching (TanStack Query). Pages call hooks, not
  API clients directly.
- **Pages** are thin — compose hooks and presentational components. Minimal logic in JSX.
- **API client** is an interface adapter — transforms API responses to domain types.
- **Zustand stores** hold client-only state (UI preferences, sidebar, theme). Never duplicate
  server state.
- **React Router** config is framework-level. Auth guards wrap routes as adapter-layer components.
- **shadcn/ui primitives** (`components/ui/`) are vendored framework code. They import other
  primitives, `cn`, their base library, and hooks the CLI wrote alongside them — never the app's
  use-case hooks, stores, or `api/`. House components compose them and pass data in.
- **Chart modules** are presentational adapters on react-chartjs-2: points arrive as props, already
  shaped by a domain function, and colours come from the CSS tokens through `useChartTokens`. They
  never call `useQuery`.

## Decision: may a page import the API client directly?

No. Violation: **Page imports API client directly (Vite SPA)** — the page should call a hook, not
axios directly.

```tsx
// BAD — web/src/pages/OrdersPage.tsx
import { useEffect, useState } from 'react';
import axios from 'axios';
import type { Order } from '../domain/order';

export function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    // Adapter (page) skips the use-case layer and talks to the network itself
    axios.get('/api/v1/orders').then((res) => setOrders(res.data.data));
  }, []);

  return (
    <ul>
      {orders.map((order) => (
        <li key={order.id}>{order.reference}</li>
      ))}
    </ul>
  );
}
```

```ts
// GOOD — web/src/hooks/useOrders.ts (use case)
import { useQuery } from '@tanstack/react-query';
import { fetchOrders } from '../api/orders';
import type { Order } from '../domain/order';

export function useOrders() {
  return useQuery<Order[]>({
    queryKey: ['orders'],
    queryFn: fetchOrders,
    staleTime: 30_000,
  });
}
```

```tsx
// GOOD — web/src/pages/OrdersPage.tsx (thin adapter)
import { useOrders } from '../hooks/useOrders';
import { OrderTable } from '../components/OrderTable';
import { Spinner } from '../components/Spinner';

export function OrdersPage() {
  const { data: orders = [], isPending, error } = useOrders();

  if (isPending) return <Spinner />;
  if (error) return <p className="text-red-600">Could not load orders.</p>;

  return <OrderTable orders={orders} />;
}
```

## Decision: may a domain type import React or framework modules?

No. Violation: **Domain type imports React modules** — the entity would depend on the framework.
Keep domain types framework-free.

```ts
// BAD — web/src/domain/order.ts
import type { ReactNode } from 'react';                  // entity depends on React
import type { UseQueryResult } from '@tanstack/react-query';

export interface Order {
  id: string;
  reference: string;
  statusBadge: ReactNode;                                 // presentation inside the entity
  query: UseQueryResult<Order>;
}
```

```ts
// GOOD — web/src/domain/order.ts (pure TypeScript)
export type OrderStatus = 'pending' | 'paid' | 'shipped' | 'cancelled';

export interface Order {
  id: string;
  reference: string;
  status: OrderStatus;
  totalCents: number;
  placedAt: string;
}

export function isCancellable(order: Order): boolean {
  return order.status === 'pending' || order.status === 'paid';
}
```

## Decision: does this state belong in Zustand or TanStack Query?

Server state belongs in TanStack Query. Zustand holds client-only state (UI preferences, sidebar,
theme) and must never duplicate server state.

```ts
// BAD — web/src/stores/orderStore.ts
import { create } from 'zustand';
import type { Order } from '../domain/order';

interface OrderState {
  orders: Order[];                      // server state mirrored into a client store
  setOrders: (orders: Order[]) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  orders: [],
  setOrders: (orders) => set({ orders }),
}));
```

```ts
// GOOD — web/src/stores/uiStore.ts (client-only state)
import { create } from 'zustand';

interface UiState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  theme: 'light',
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme }),
}));
```

## Decision: may a chart module fetch or shape its own data?

No. Violation: **Chart module reaches into a use case (Vite SPA)** — a chart drawn through
react-chartjs-2 is an interface adapter. Fetching inside it skips the page → hook flow, and
converting units inside it puts a domain rule in the view, where no unit test reaches it.

```tsx
// BAD — web/src/components/organisms/RevenuePanel/RevenueChart.tsx
import '../../../lib/charts/register';
import { Line } from 'react-chartjs-2';
import { useTranslation } from 'react-i18next';
import { useRevenue } from '../../../hooks/useRevenue';

export function RevenueChart() {
  const { t } = useTranslation();
  const { data } = useRevenue();                                        // adapter calls a use case
  const days = data ?? [];
  const revenue = days.map((d) => d.totalCents / 100);                 // domain rule in the view

  return (
    <div className="relative h-64 w-full">
      <Line
        data={{ labels: days.map((d) => d.date), datasets: [{ label: t('dashboard.revenue.series'), data: revenue }] }}
        aria-label={t('dashboard.revenue.title')}
      />
    </div>
  );
}
```

```ts
// GOOD — web/src/domain/revenue.ts (entity: the shaping rule, pure and unit-testable)
export interface RevenueDay {
  date: string;
  totalCents: number;
}

export interface RevenuePoint {
  day: string;
  revenue: number;
}

export function toRevenuePoints(days: RevenueDay[]): RevenuePoint[] {
  return [...days]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => ({ day: d.date, revenue: d.totalCents / 100 }));
}
```

```tsx
// GOOD — web/src/pages/DashboardPage.tsx (thin adapter: hook in, shaped points out)
import { useMemo } from 'react';
import { useRevenue } from '../hooks/useRevenue';
import { toRevenuePoints } from '../domain/revenue';
import { RevenueChart } from '../components/organisms/RevenuePanel/RevenueChart';
import { Spinner } from '../components/Spinner';

export function DashboardPage() {
  const { data, isPending } = useRevenue();
  const points = useMemo(() => toRevenuePoints(data ?? []), [data]);

  if (isPending) return <Spinner />;
  return <RevenueChart points={points} />;
}
```

The chart module keeps the `Line` markup from the BAD version and loses the hook and the
arithmetic: it takes `points` as a prop. Its memoised `data` and `options`, lazy-loading it, its
empty and error states, and its text alternative → `@skills/std-reactjs/references/charts.md`.

## Decision: where do route config and auth guards live?

React Router config is framework-level. Auth guards wrap routes as adapter-layer components — they
read a use case (a hook) and redirect; they never contain business rules themselves.

```tsx
// GOOD — web/src/components/RequireAuth.tsx (adapter-layer guard)
import { Navigate, Outlet, useLocation } from 'react-router';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { Spinner } from './Spinner';

export function RequireAuth() {
  const { data: user, isPending } = useCurrentUser();
  const location = useLocation();

  if (isPending) return <Spinner />;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;

  return <Outlet />;
}
```

```tsx
// GOOD — web/src/router/index.tsx (framework-level config, lazy-loaded)
import { lazy } from 'react';
import { createBrowserRouter } from 'react-router';
import { RequireAuth } from '../components/RequireAuth';

const OrdersPage = lazy(() => import('../pages/OrdersPage'));

export const router = createBrowserRouter([
  {
    element: <RequireAuth />,
    children: [{ path: '/orders', element: <OrdersPage /> }],
  },
]);
```

## Decision: what does the API client do?

The API client is an interface adapter: it transforms API responses into domain types. It holds no
business rules, and pages never call it directly.

```ts
// GOOD — web/src/api/orders.ts
import { apiClient } from './client';
import type { Order } from '../domain/order';

interface OrderPayload {
  id: string;
  reference: string;
  status: string;
  total_cents: number;
  placed_at: string;
}

const toDomain = (payload: OrderPayload): Order => ({
  id: payload.id,
  reference: payload.reference,
  status: payload.status as Order['status'],
  totalCents: payload.total_cents,
  placedAt: payload.placed_at,
});

export async function fetchOrders(): Promise<Order[]> {
  const response = await apiClient.get<{ data: OrderPayload[] }>('/orders');
  return response.data.data.map(toDomain);
}
```

## Decision: how do I test each Vite SPA layer?

- **Entities** (domain types, domain utils): Vitest unit tests, no mocks needed — pure domain logic.
  A chart's shaping function (`toRevenuePoints`) is tested here, with no DOM.
- **Use Cases** (hooks): Vitest unit tests with the network mocked via MSW — exercise with
  `renderHook` inside a `QueryClientProvider`.
- **Interface Adapters** (pages, components, chart modules, API client): integration tests with
  `@testing-library/react` + MSW. A chart module is asserted through its text alternative and
  `Chart.getChart(canvas)`, never its canvas pixels, with `vitest-canvas-mock` in setup →
  `@skills/std-testing/references/react-components.md`.
- **Frameworks** (React, Vite, TanStack Query, Zustand, React Router, shadcn/ui primitives,
  Chart.js): minimal testing — trust the framework, test your configuration and your composition.
