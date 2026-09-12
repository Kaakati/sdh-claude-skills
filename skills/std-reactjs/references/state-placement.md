# State Placement (Zustand vs. TanStack Query vs. the URL vs. local)

Load-bearing rules restated (hold even if you read nothing else):

1. **TanStack Query owns every byte that came from the API.** Zustand owns only client-invented
   state. If a `fetch`/axios response can reach a Zustand store, the design is wrong.
2. **No `useEffect` for data fetching.** `useQuery` / `useMutation` only.
3. **One Zustand store per concern**, subscribed to with selectors — never a god store, never a
   whole-store subscription.
4. **A list's filters, sort and query live in the URL.** People open a record and come back, reload,
   and share the link — the state is part of the location.

---

## Decision: where does this piece of state live?

| The value… | Home | Why |
|---|---|---|
| Came from the Rails API | TanStack Query | It has an owner (server); cache it, don't copy it |
| Is a UI preference (theme, sidebar, density) | Zustand | Never leaves the browser |
| Is a list's filter / sort / search query | URL search params | Client intent that is also a location: Back, the list's breadcrumb and a shared link restore it |
| Is a filter on a panel nobody links to (a dashboard widget's range) | Zustand | Client intent that is not a place |
| Is a page cursor | TanStack Query (`useInfiniteQuery`'s page param) | Only valid with the parameters that produced it — never the URL, never a store |
| Is a draft form value | `react-hook-form` state | Lives and dies with the form |
| Is derived from server data | Nowhere — compute it | Derived state is a bug factory |
| Is transient UI (modal open, hovered row) | `useState` | Local by default |

**Rule of thumb:** filters go in the URL (a list) or Zustand (a panel); results come back from
TanStack Query keyed *by* those filters. The filter is the input, the data is the output. They
never share a home.

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

### Good — Zustand holds a panel's filter, Query holds the data

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
// src/api/orders.ts  ✅  server state — the filter is the query key INPUT
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';
import type { Order } from '@/domain/order';
import type { OrderFilters } from '@/stores/order-filter-store';
// `orderKeys` is the hierarchical key factory — `references/data-fetching.md` owns that
// decision and defines it. Reproduced here only as far as this example needs it.
import { orderKeys } from '@/api/orders';

export function useOrders(filters: OrderFilters) {
  // The filter object goes straight into the key: change the filter, the key changes, Query
  // refetches. That is the whole mechanism — no effect, no copy of the results into a store.
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
// src/components/organisms/RecentOrdersPanel/RecentOrdersPanel.tsx  ✅ a dashboard panel: its filter is not a place
import { useShallow } from 'zustand/react/shallow';

export function RecentOrdersPanel() {
  const filters = useOrderFilterStore(useShallow((s) => ({ status: s.status, search: s.search })));
  const { data: orders, isPending, isError } = useOrders(filters);

  if (isPending) return <Spinner />;
  if (isError) return <ErrorState onRetry={() => location.reload()} />;
  return <OrderTable orders={orders} />;
}
```

**The orders *list page* keeps the same filters in the URL instead.** Same mechanism — the state
feeds the key — with `useSearchParams` as the home, validated by the route's loader →
`references/routing-and-code-split.md`.

For the query hook's full shape — key factories, `staleTime` choice, mutations, and the axios
client behind `api` — see `references/data-fetching.md`.

---

## Decision: how do I shape a Zustand store?

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

Stores are module-level singletons: they persist across tests and must be reset between them —
see `references/testing.md`.
