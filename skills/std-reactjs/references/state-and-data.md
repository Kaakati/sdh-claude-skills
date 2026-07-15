# State Placement & Data Fetching (Vite SPA)

Load-bearing rules restated (hold even if you read nothing else):

1. **TanStack Query owns every byte that came from the API.** Zustand owns only client-invented
   state. If a `fetch`/axios response can reach a Zustand store, the design is wrong.
2. **No `useEffect` for data fetching.** `useQuery` / `useMutation` only.
3. **Components never call axios directly.** Components → hooks (`src/hooks` or `src/api`) → API
   client.

---

## Decision: where does this piece of state live?

| The value… | Home | Why |
|---|---|---|
| Came from the Rails API | TanStack Query | It has an owner (server); cache it, don't copy it |
| Is a UI preference (theme, sidebar, density) | Zustand | Never leaves the browser |
| Is a table filter / sort / page cursor | Zustand (or URL search params) | Client intent; it's the *input* to a query |
| Is a draft form value | `react-hook-form` state | Lives and dies with the form |
| Is derived from server data | Nowhere — compute it | Derived state is a bug factory |
| Is transient UI (modal open, hovered row) | `useState` | Local by default |

**Rule of thumb:** filters go in Zustand or the URL; results come back from TanStack Query keyed
*by* those filters. The filter is the input, the data is the output. They never share a home.

### Bad — server data copied into Zustand

```ts
// src/stores/order-store.ts  ❌
import { create } from 'zustand';
import { api } from '@/api/client';
import type { Order } from '@/domain/order';

interface OrderStore {
  orders: Order[];
  loading: boolean;
  fetchOrders: () => Promise<void>;
}

export const useOrderStore = create<OrderStore>((set) => ({
  orders: [],
  loading: false,
  fetchOrders: async () => {
    set({ loading: true });
    const { data } = await api.get<{ data: Order[] }>('/orders');
    set({ orders: data.data, loading: false });
  },
}));
```

```tsx
// src/pages/Orders.tsx  ❌
export default function Orders() {
  const { orders, loading, fetchOrders } = useOrderStore();
  useEffect(() => { fetchOrders(); }, [fetchOrders]);  // manual fetch, no dedupe, stale forever
  if (loading) return <Spinner />;
  return <OrderTable orders={orders} />;
}
```

Failure modes this ships: two mounted components double-fetch, nothing refetches on focus, a
mutation elsewhere leaves the list stale, and errors have no home.

### Good — Zustand holds the filter, Query holds the data

```ts
// src/stores/order-filter-store.ts  ✅  client-only intent
import { create } from 'zustand';

export interface OrderFilters {
  status: 'all' | 'pending' | 'shipped';
  search: string;
}

interface OrderFilterStore extends OrderFilters {
  setStatus: (status: OrderFilters['status']) => void;
  setSearch: (search: string) => void;
}

export const useOrderFilterStore = create<OrderFilterStore>((set) => ({
  status: 'all',
  search: '',
  setStatus: (status) => set({ status }),
  setSearch: (search) => set({ search }),
}));
```

```ts
// src/api/orders.ts  ✅  server state
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Order } from '@/domain/order';
import type { OrderFilters } from '@/stores/order-filter-store';

export const orderKeys = {
  all: ['orders'] as const,
  list: (filters: OrderFilters) => [...orderKeys.all, 'list', filters] as const,
  detail: (id: string) => [...orderKeys.all, 'detail', id] as const,
};

export function useOrders(filters: OrderFilters) {
  return useQuery({
    queryKey: orderKeys.list(filters),
    queryFn: async ({ signal }) => {
      const { data } = await api.get<{ data: Order[] }>('/orders', {
        params: { status: filters.status, q: filters.search },
        signal,
      });
      return data.data;
    },
    staleTime: 30_000,
  });
}
```

```tsx
// src/pages/Orders.tsx  ✅
export default function Orders() {
  const filters = useOrderFilterStore((s) => ({ status: s.status, search: s.search }));
  const { data: orders, isPending, isError } = useOrders(filters);

  if (isPending) return <Spinner />;
  if (isError) return <ErrorState onRetry={() => location.reload()} />;
  return <OrderTable orders={orders} />;
}
```

---

## Decision: how do I structure query keys?

Ad-hoc string arrays make invalidation guesswork. Use a **key factory per resource**, exported
from the same module as the hooks.

### Bad

```ts
useQuery({ queryKey: ['orders', status], queryFn: ... });          // ❌ page A
useQuery({ queryKey: ['order-list', { status }], queryFn: ... });  // ❌ page B — different key, same data
queryClient.invalidateQueries({ queryKey: ['orders'] });           // ❌ misses page B entirely
```

### Good

```ts
// One factory, hierarchical, so invalidating the prefix invalidates everything below it.
export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (filters: OrderFilters) => [...orderKeys.lists(), filters] as const,
  detail: (id: string) => [...orderKeys.all, 'detail', id] as const,
};

queryClient.invalidateQueries({ queryKey: orderKeys.lists() }); // ✅ every list variant
queryClient.invalidateQueries({ queryKey: orderKeys.all });     // ✅ lists + details
```

---

## Decision: staleTime for this query

`staleTime` is "how long is this data trustworthy without a background refetch". `gcTime` is
"how long to keep it after nothing uses it". Default `staleTime` is `0` — which refetches on
every mount. Set it deliberately.

| Data | `staleTime` | Rationale |
|---|---|---|
| Lists that change with user action | `30_000` (30s) | Default for the SPA |
| Detail views | `30_000` | Same |
| Reference data (countries, categories, roles) | `5 * 60_000` (5min) | Changes rarely |
| Truly immutable (an invoice PDF's metadata) | `Infinity` | Never refetch |
| Live dashboards | `0` + `refetchInterval` | Freshness is the point |

Set app-wide defaults once, override per query:

```tsx
// src/App.tsx
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: (failureCount, error) => {
        if (isAxiosError(error) && error.response?.status === 404) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: true,
    },
  },
});
```

---

## Decision: mutating server data

### Bad — mutate, then hand-patch the cache with a guess

```tsx
const handleShip = async (id: string) => {
  await api.post(`/orders/${id}/ship`);            // ❌ raw axios in a component
  setLocalOrders((prev) =>                          // ❌ hand-maintained shadow copy
    prev.map((o) => (o.id === id ? { ...o, status: 'shipped' } : o)),
  );
};
```

### Good — `useMutation` + invalidate

```ts
// src/api/orders.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useShipOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<{ data: Order }>(`/orders/${id}/ship`);
      return data.data;
    },
    onSuccess: (order) => {
      queryClient.setQueryData(orderKeys.detail(order.id), order);
      queryClient.invalidateQueries({ queryKey: orderKeys.lists() });
    },
  });
}
```

```tsx
// src/pages/OrderDetail.tsx
const shipOrder = useShipOrder();

<button
  onClick={() => shipOrder.mutate(order.id)}
  disabled={shipOrder.isPending}
  className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
>
  {shipOrder.isPending ? 'Shipping…' : 'Ship order'}
</button>
```

### Optimistic updates — only when you also write the rollback

```ts
export function useToggleFavorite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/orders/${id}/favorite`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: orderKeys.detail(id) });
      const previous = queryClient.getQueryData<Order>(orderKeys.detail(id));
      queryClient.setQueryData<Order>(orderKeys.detail(id), (old) =>
        old ? { ...old, favorited: !old.favorited } : old,
      );
      return { previous };
    },
    onError: (_err, id, context) => {
      // Rollback is not optional. Without it, an optimistic update is a lie.
      if (context?.previous) queryClient.setQueryData(orderKeys.detail(id), context.previous);
    },
    onSettled: (_data, _err, id) => {
      queryClient.invalidateQueries({ queryKey: orderKeys.detail(id) });
    },
  });
}
```

---

## The axios client (single instance, interceptors)

### Bad

```ts
// Scattered across pages ❌
const res = await axios.get('https://api.example.com/orders', {
  headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
});
```

### Good

```ts
// src/api/client.ts  ✅
import axios from 'axios';
import { useAuthStore } from '@/stores/auth-store';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().signOut();
      window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);
```

Note `useAuthStore.getState()` — interceptors are outside React, so read the store imperatively.
Never call a hook from an interceptor.

---

## Zustand store shape

### Bad — one god store, whole-store subscription

```ts
const useAppStore = create((set) => ({
  theme: 'light', sidebarOpen: true, orders: [], user: null, /* ... */  // ❌ mixes everything
}));

// ❌ subscribes to the entire store — rerenders on every unrelated change
const { theme } = useAppStore();
```

### Good — one store per concern, selector subscriptions

```ts
// src/stores/ui-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UiStore {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setTheme: (theme: UiStore['theme']) => void;
}

export const useUiStore = create<UiStore>()(
  persist(
    (set) => ({
      theme: 'light',
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-preferences' },
  ),
);
```

```tsx
const theme = useUiStore((s) => s.theme);              // ✅ rerenders only on theme change
const toggleSidebar = useUiStore((s) => s.toggleSidebar);
```

When selecting multiple fields, use `useShallow` or the object identity changes every render:

```tsx
import { useShallow } from 'zustand/react/shallow';
const { status, search } = useOrderFilterStore(useShallow((s) => ({ status: s.status, search: s.search })));
```
