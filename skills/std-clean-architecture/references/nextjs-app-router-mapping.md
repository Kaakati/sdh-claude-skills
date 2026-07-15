# Clean Architecture on Next.js (App Router)

Layer mapping, rules, and boundary violations for the Next.js App Router app (Server Components,
server actions, TanStack Query, Zustand, Vercel).

**The rule this file enforces:** dependencies point inward. Entities (domain types, domain utils)
know nothing about use cases, pages, or frameworks. Use cases (server actions, client hooks) know
about entities but not about UI or React components. Interface adapters (pages, layouts, route
handlers, components) translate between use cases and external concerns. Frameworks (Next.js,
React Server Components, TanStack Query, Zustand) are implementation details — pluggable and
replaceable.

## Decision: which layer does this Next.js file belong to?

| Clean Architecture Layer | Next.js Component | Directory |
|--------------------------|-------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `next/src/domain/`, `next/src/types/` |
| Use Cases (Server) | Server actions | `next/src/actions/` |
| Use Cases (Client) | Custom hooks | `next/src/hooks/` |
| Interface Adapters | Pages, layouts, route handlers, components | `next/app/`, `next/src/components/`, `next/src/api/` |
| Frameworks | Next.js, React Server Components, TanStack Query, Zustand | Framework code |

Rules per component:

- **Server actions** are use cases — they validate input (zod), call the Rails API, and trigger
  revalidation. No UI or framework concerns.
- **Server Components** (pages, layouts) are interface adapters — they fetch data and compose
  components. Keep them thin.
- **Client Components** (`'use client'`) should be leaf-level and minimal. Extract interactive
  parts, keep data fetching in Server Components.
- **Domain types** are pure TypeScript — shared across server and client boundaries.
- **Route handlers** (`route.ts`) are interface adapters for BFF endpoints. Thin wrappers that
  delegate to services.

## Decision: what belongs in a server action?

A server action is a use case: validate input with zod, call the Rails API, revalidate. Violation:
**Server action contains UI logic** — returning JSX or importing React components. Keep actions
data-only.

```tsx
// BAD — next/src/actions/createOrder.ts
'use server';

import { OrderRow } from '../components/OrderRow';   // use case imports a React component

export async function createOrder(formData: FormData) {
  const res = await fetch(`${process.env.API_URL}/orders`, {
    method: 'POST',
    body: JSON.stringify({ sku: formData.get('sku') }),  // unvalidated input
  });
  const order = await res.json();

  return <OrderRow order={order} />;                  // use case returns UI
}
```

```ts
// GOOD — next/src/actions/createOrder.ts (data-only use case)
'use server';

import { z } from 'zod';
import { revalidatePath } from 'next/cache';
import { apiClient } from '@/src/api/client';
import type { Order } from '@/src/domain/order';

const CreateOrderSchema = z.object({
  sku: z.string().min(1),
  quantity: z.coerce.number().int().positive(),
});

export type CreateOrderResult =
  | { ok: true; order: Order }
  | { ok: false; errors: string[] };

export async function createOrder(formData: FormData): Promise<CreateOrderResult> {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    return { ok: false, errors: parsed.error.issues.map((i) => i.message) };
  }

  const order = await apiClient.post<Order>('/orders', parsed.data);
  revalidatePath('/orders');
  return { ok: true, order };
}
```

## Decision: how should a Client Component get its data?

Not with `useEffect`. Violation: **Client Component fetches data via `useEffect`** — use TanStack
Query's `useQuery` instead, or move the fetch up into a Server Component.

```tsx
// BAD — next/src/components/OrderList.tsx
'use client';

import { useEffect, useState } from 'react';
import type { Order } from '@/src/domain/order';

export function OrderList() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    fetch('/api/orders')                       // no caching, no dedupe, races on unmount
      .then((res) => res.json())
      .then((json) => setOrders(json.data));
  }, []);

  return <ul>{orders.map((o) => <li key={o.id}>{o.reference}</li>)}</ul>;
}
```

```tsx
// GOOD — next/app/orders/page.tsx (Server Component fetches, stays thin)
import { fetchOrders } from '@/src/api/orders';
import { OrderList } from '@/src/components/OrderList';

export default async function OrdersPage() {
  const orders = await fetchOrders();

  return <OrderList orders={orders} />;
}
```

```tsx
// GOOD — next/src/components/OrderList.tsx (leaf-level, minimal Client Component)
'use client';

import { useState } from 'react';
import type { Order } from '@/src/domain/order';

export function OrderList({ orders }: { orders: Order[] }) {
  const [query, setQuery] = useState('');
  const visible = orders.filter((o) => o.reference.includes(query));

  return (
    <>
      <input value={query} onChange={(e) => setQuery(e.target.value)} className="border p-2" />
      <ul>{visible.map((o) => <li key={o.id}>{o.reference}</li>)}</ul>
    </>
  );
}
```

When a Client Component genuinely owns its own fetching (polling, infinite scroll, post-hydration
filters), it uses a hook — the client-side use case:

```ts
// GOOD — next/src/hooks/useOrders.ts (client use case)
'use client';

import { useQuery } from '@tanstack/react-query';
import type { Order } from '@/src/domain/order';

export function useOrders(initialData: Order[]) {
  return useQuery<Order[]>({
    queryKey: ['orders'],
    queryFn: async () => {
      const res = await fetch('/api/orders');
      return (await res.json()).data as Order[];
    },
    initialData,
    refetchInterval: 30_000,
  });
}
```

## Decision: may a domain type import React or Next.js modules?

No. Violation: **Domain type imports React or Next.js modules** — keep domain types framework-free
so they can be shared across the server and client boundaries.

```ts
// BAD — next/src/domain/order.ts
import type { ReactNode } from 'react';           // entity depends on React
import type { Metadata } from 'next';             // entity depends on Next.js

export interface Order {
  id: string;
  reference: string;
  statusBadge: ReactNode;
  metadata: Metadata;
}
```

```ts
// GOOD — next/src/domain/order.ts (pure TypeScript, server- and client-safe)
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

## Decision: what goes in a route handler?

Route handlers (`route.ts`) are interface adapters for BFF endpoints — thin wrappers that delegate
to services/use cases. No business logic.

```ts
// BAD — next/app/api/orders/route.ts
import { NextResponse } from 'next/server';
import { db } from '@/src/db';

export async function POST(request: Request) {
  const body = await request.json();
  const total = body.items.reduce(
    (sum: number, i: { qty: number; price: number }) => sum + i.qty * i.price,
    0,
  );
  const discounted = total >= 10_000 ? total * 0.95 : total;   // business rule in an adapter
  const order = await db.order.create({ data: { total: discounted } });

  return NextResponse.json(order);
}
```

```ts
// GOOD — next/app/api/orders/route.ts (thin adapter)
import { NextResponse } from 'next/server';
import { createOrderFromPayload } from '@/src/actions/createOrder';

export async function POST(request: Request) {
  const result = await createOrderFromPayload(await request.json());

  if (!result.ok) {
    return NextResponse.json({ errors: result.errors }, { status: 422 });
  }

  return NextResponse.json({ data: result.order }, { status: 201 });
}
```

## Decision: how do I test each Next.js layer?

- **Entities** (domain types, domain utils): Vitest unit tests, no mocks needed — pure domain logic.
- **Use Cases** (server actions, client hooks): Vitest unit tests with the API/network mocked
  (MSW). Assert on returned data and on revalidation calls, never on rendered output.
- **Interface Adapters** (Server Components, Client Components, route handlers): integration tests
  with `@testing-library/react` + MSW; call route handlers directly with a `Request`.
- **Frameworks** (Next.js, RSC, TanStack Query, Zustand): minimal testing — trust the framework,
  test your configuration.
