# Clean Architecture on ReactJS (Vite SPA)

Layer mapping, rules, and boundary violations for the Vite single-page app (React Router +
Tailwind CSS + Framer Motion + ApexCharts + TanStack Query + Zustand).

**The rule this file enforces:** dependencies point inward. Entities (domain types, domain utils)
know nothing about use cases, pages, or frameworks. Use cases (hooks) know about entities but not
about pages or React components. Interface adapters (pages, components, API client, router
config) translate between use cases and external concerns. Frameworks (React, Vite, TanStack
Query, Zustand, React Router) are implementation details — pluggable and replaceable.

## Decision: which layer does this Vite SPA file belong to?

| Clean Architecture Layer | Vite SPA Component | Directory |
|--------------------------|-------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `web/src/domain/`, `web/src/types/` |
| Use Cases | Custom hooks (business logic + data fetching) | `web/src/hooks/`, `web/src/api/` |
| Interface Adapters | Pages, components, API client, router config | `web/src/pages/`, `web/src/components/`, `web/src/api/`, `web/src/router/` |
| Frameworks | React, Vite, TanStack Query, Zustand, React Router | Framework code |

Rules per component:

- **Domain types** are pure TypeScript — no React, no framework dependencies.
- **Hooks** encapsulate business logic and data fetching (TanStack Query). Pages call hooks, not
  API clients directly.
- **Pages** are thin — compose hooks and presentational components. Minimal logic in JSX.
- **API client** is an interface adapter — transforms API responses to domain types.
- **Zustand stores** hold client-only state (UI preferences, sidebar, theme). Never duplicate
  server state.
- **React Router** config is framework-level. Auth guards wrap routes as adapter-layer components.

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
- **Use Cases** (hooks): Vitest unit tests with the network mocked via MSW — exercise with
  `renderHook` inside a `QueryClientProvider`.
- **Interface Adapters** (pages, components, API client): integration tests with
  `@testing-library/react` + MSW.
- **Frameworks** (React, Vite, TanStack Query, Zustand, React Router): minimal testing — trust the
  framework, test your configuration.
