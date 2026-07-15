# Consuming a Paginated API from the Frontend

Covers the Vite SPA and React Native. For the server side of the contract — keyset cursors,
pagy, PostGIS — see `pagination-rails.md`.

Load-bearing rules restated (these hold even if you read nothing else):

- Collections arrive wrapped in `data`, never as a bare array:
  `{ "data": [...], "pagination": {...} }`.
- The cursor envelope the client reads:

  ```json
  {
    "data": [],
    "pagination": { "nextCursor": "eyJpZCI6MTAwfQ==", "hasMore": true, "limit": 25 }
  }
  ```

- Default page size **25**, maximum **100**, requested via `?limit=`. The server clamps it — do
  not assume an oversized `limit` is honoured.
- `hasMore` is the authority on whether another page exists. Never infer it from
  `data.length === limit`.

---

## Decision: how do I consume a cursor API from the frontend?

Use TanStack Query's `useInfiniteQuery` — the pagination envelope maps onto it directly.

### Bad — manual page state, appended by hand

```typescript
const [items, setItems] = useState<Order[]>([]);
const [cursor, setCursor] = useState<string | null>(null);

useEffect(() => {
  apiClient.get('/orders', { params: { cursor } }).then((res) => {
    setItems((prev) => [...prev, ...res.data.data]); // double-fires in StrictMode; duplicates rows
    setCursor(res.data.pagination.nextCursor);
  });
}, [cursor]); // and this loops forever
```

### Good — useInfiniteQuery reading nextCursor from the envelope

```typescript
// src/api/orders.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export type Order = { id: string; total: number; createdAt: string };
export type Paginated<T> = {
  data: T[];
  pagination: { nextCursor: string | null; hasMore: boolean; limit: number };
};

export function useOrders(limit = 25) {
  return useInfiniteQuery({
    queryKey: ['orders', { limit }],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }) => {
      const res = await apiClient.get<Paginated<Order>>('/orders', {
        params: { cursor: pageParam ?? undefined, limit },
      });
      return res.data;
    },
    getNextPageParam: (last) => (last.pagination.hasMore ? last.pagination.nextCursor : undefined),
  });
}
```

```tsx
// src/pages/orders/OrdersList.tsx
export function OrdersList() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders();
  const orders = data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div>
      <ul className="divide-y divide-slate-200">
        {orders.map((o) => (
          <li key={o.id} className="py-3">{o.id}</li>
        ))}
      </ul>
      {hasNextPage && (
        <button
          type="button"
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  );
}
```

---

## Decision: how do I wire the same hook to a React Native FlatList?

Same hook, same envelope — only the list primitive changes.

```tsx
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders();

<FlatList
  data={data?.pages.flatMap((p) => p.data) ?? []}
  keyExtractor={(item) => item.id}
  renderItem={({ item }) => <OrderRow order={item} />}
  onEndReachedThreshold={0.5}
  onEndReached={() => {
    if (hasNextPage && !isFetchingNextPage) fetchNextPage();
  }}
/>;
```

`onEndReached` fires repeatedly while scrolling — the `!isFetchingNextPage` guard is what stops
it from firing the same cursor request five times.
