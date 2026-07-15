# Data Fetching (TanStack Query + axios)

Load-bearing rules restated (hold even if you read nothing else):

1. **TanStack Query owns all server data.** No API response is ever copied into a Zustand store or
   `useState`.
2. **No `useEffect` for data fetching.** `useQuery` / `useMutation` only.
3. **Components never call axios directly.** Components → hooks (`src/hooks` or `src/api`) → the
   shared axios client in `src/api/client.ts`.
4. **One query-key factory per resource**, exported from the same module as the hooks.

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
// src/api/orders.ts
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

The list key takes the filter object as its last segment — filters live in Zustand or the URL and
are the *input* to the query (see `references/state-placement.md`). A query hook built on this
factory:

```ts
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

Pass `signal` through to axios — Query aborts in-flight requests when the key changes, which is
what stops a fast-typing search box from racing itself.

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

## Decision: the axios client (single instance, interceptors)

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
