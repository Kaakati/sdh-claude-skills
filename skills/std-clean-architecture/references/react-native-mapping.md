# Clean Architecture on React Native

Layer mapping, rules, and boundary violations for the React Native mobile app (Zustand +
TanStack Query + Reanimated + React Navigation).

**The rule this file enforces:** dependencies point inward. Entities (domain types, domain utils)
know nothing about use cases, screens, or frameworks. Use cases (hooks) know about entities but
not about screens or React Native components. Interface adapters (screens, API client,
navigation) translate between use cases and external concerns. Frameworks (React Native, TanStack
Query, Zustand) are implementation details — pluggable and replaceable.

## Decision: which layer does this React Native file belong to?

| Clean Architecture Layer | React Native Component | Directory |
|--------------------------|------------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `mobile/src/domain/`, `mobile/src/types/` |
| Use Cases | Custom hooks (business logic) | `mobile/src/hooks/` |
| Interface Adapters | Screens, API client, navigation | `mobile/src/screens/`, `mobile/src/api/`, `mobile/src/navigation/` |
| Frameworks | React Native, TanStack Query, Zustand | Framework code |

Rules per component:

- **Domain types** are pure TypeScript — no React, no framework dependencies.
- **Hooks** encapsulate business logic and data fetching (TanStack Query). Screens call hooks, not
  API clients directly.
- **Screens** are thin — compose hooks and presentational components. Minimal logic in JSX.
- **API client** is an interface adapter — transforms API responses to domain types.
- **Zustand stores** hold client-only state (UI preferences, offline queue). Never duplicate
  server state.

## Decision: may a screen call the API client directly?

No. Violation: **Screen calls API client directly** — use a hook as the intermediary.

```tsx
// BAD — mobile/src/screens/OrdersScreen.tsx
import { useEffect, useState } from 'react';
import { FlatList, Text } from 'react-native';
import { apiClient } from '../api/client';
import type { Order } from '../domain/order';

export function OrdersScreen() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    // Adapter (screen) reaches straight past the use-case layer to the network
    apiClient.get('/orders').then((res) => setOrders(res.data.data));
  }, []);

  return (
    <FlatList
      data={orders}
      keyExtractor={(o) => o.id}
      renderItem={({ item }) => <Text>{item.reference}</Text>}
    />
  );
}
```

```tsx
// GOOD — mobile/src/hooks/useOrders.ts (use case)
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
// GOOD — mobile/src/screens/OrdersScreen.tsx (thin adapter)
import { ActivityIndicator, FlatList } from 'react-native';
import { useOrders } from '../hooks/useOrders';
import { OrderRow } from '../components/OrderRow';

export function OrdersScreen() {
  const { data: orders = [], isPending } = useOrders();

  if (isPending) return <ActivityIndicator />;

  return (
    <FlatList
      data={orders}
      keyExtractor={(order) => order.id}
      renderItem={({ item }) => <OrderRow order={item} />}
    />
  );
}
```

## Decision: may a hook import React Native components?

No. Violation: **Hook imports React Native components** — the use case would depend on the
framework. Keep hooks logic-only; return data and callbacks, let the screen render.

```ts
// BAD — mobile/src/hooks/useOrderActions.ts
import { Alert, View } from 'react-native'; // use case now depends on the UI framework
import { useMutation } from '@tanstack/react-query';
import { cancelOrder } from '../api/orders';

export function useOrderActions(orderId: string) {
  const mutation = useMutation({
    mutationFn: () => cancelOrder(orderId),
    onError: () => Alert.alert('Could not cancel this order'), // UI concern in a use case
  });

  return { cancel: mutation.mutate, Banner: View };
}
```

```ts
// GOOD — mobile/src/hooks/useOrderActions.ts (logic only)
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { cancelOrder } from '../api/orders';

export function useOrderActions(orderId: string) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => cancelOrder(orderId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['orders'] }),
  });

  return {
    cancel: mutation.mutate,
    isCancelling: mutation.isPending,
    error: mutation.error,
  };
}
```

```tsx
// GOOD — mobile/src/screens/OrderDetailScreen.tsx (screen owns the UI reaction)
import { useEffect } from 'react';
import { Alert, Button } from 'react-native';
import { useOrderActions } from '../hooks/useOrderActions';

export function OrderDetailScreen({ orderId }: { orderId: string }) {
  const { cancel, isCancelling, error } = useOrderActions(orderId);

  useEffect(() => {
    if (error) Alert.alert('Could not cancel this order');
  }, [error]);

  return <Button title="Cancel order" onPress={() => cancel()} disabled={isCancelling} />;
}
```

## Decision: may a domain type import framework modules?

No. Violation: **Domain type imports framework modules** — the entity would depend on the
framework. Keep types pure TypeScript.

```ts
// BAD — mobile/src/domain/order.ts
import type { ViewStyle } from 'react-native';   // entity depends on React Native
import type { UseQueryResult } from '@tanstack/react-query';

export interface Order {
  id: string;
  reference: string;
  rowStyle: ViewStyle;                            // presentation leaked into the entity
  query: UseQueryResult<Order>;
}
```

```ts
// GOOD — mobile/src/domain/order.ts (pure TypeScript)
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

Server state belongs in TanStack Query. Zustand holds client-only state (UI preferences, offline
queue) and must never duplicate server state.

```ts
// BAD — mobile/src/stores/orderStore.ts
import { create } from 'zustand';
import type { Order } from '../domain/order';

interface OrderState {
  orders: Order[];                     // server state mirrored into a client store
  setOrders: (orders: Order[]) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  orders: [],
  setOrders: (orders) => set({ orders }),
}));
```

```ts
// GOOD — mobile/src/stores/preferencesStore.ts (client-only state)
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { MMKV } from 'react-native-mmkv';

const storage = new MMKV();

interface PreferencesState {
  listDensity: 'compact' | 'comfortable';
  setListDensity: (density: 'compact' | 'comfortable') => void;
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      listDensity: 'comfortable',
      setListDensity: (listDensity) => set({ listDensity }),
    }),
    {
      name: 'preferences',
      storage: createJSONStorage(() => ({
        getItem: (key) => storage.getString(key) ?? null,
        setItem: (key, value) => storage.set(key, value),
        removeItem: (key) => storage.delete(key),
      })),
    },
  ),
);
```

## Decision: what does the API client do?

The API client is an interface adapter: it transforms API responses into domain types. It does not
hold business rules, and screens never call it directly.

```ts
// GOOD — mobile/src/api/orders.ts
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

## Decision: how do I test each React Native layer?

- **Entities** (domain types, domain utils): unit tests, no mocks needed — pure domain logic.
- **Use Cases** (hooks): unit tests with the API module mocked — render via
  `renderHook` and assert on returned data/callbacks.
- **Interface Adapters** (screens, API client): integration tests — render the screen with a
  mocked network layer.
- **Frameworks** (React Native, TanStack Query, Zustand): minimal testing — trust the framework,
  test your configuration.
