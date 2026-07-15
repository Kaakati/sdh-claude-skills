# Rendering: choosing the Server/Client boundary

Load-bearing rules restated (this file is read standalone):

- **Every component in `app/` is a Server Component unless the file starts with `'use client'`.**
- **Never put `'use client'` on a `page.tsx` or `layout.tsx`.** Push it to a leaf.
- `'use client'` is a *boundary*, not a file marker: everything imported by a Client Component
  is bundled to the browser too.

---

## Decision: does this component need `'use client'`?

Answer **no** unless it needs one of: `useState`/`useReducer`/`useEffect`, an event handler
(`onClick`, `onChange`), a browser API (`window`, `localStorage`), a Zustand store, a TanStack
Query hook, or a third-party library that itself calls hooks (Framer Motion, ApexCharts).

Everything else — data fetching, layout, formatting, SEO-critical markup — stays on the server.

### Bad — the whole page becomes client-side to get one click handler

```tsx
// app/(dashboard)/orders/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { railsApi } from '@/api/client';
import type { Order } from '@/types/order';

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    railsApi.get('/api/v1/orders').then((r) => setOrders(r.data.data));
  }, []);

  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Orders</h1>
      <ul>
        {orders.map((order) => (
          <li key={order.id} onClick={() => setSelected(order.id)}>
            {order.reference} — {order.total}
          </li>
        ))}
      </ul>
    </main>
  );
}
```

Problems: an empty-then-populate loading flash, the API base URL and axios ship to the browser,
no SEO content in the HTML, and the page cannot `await`.

### Good — server page, client leaf

```tsx
// app/(dashboard)/orders/page.tsx  — Server Component
import type { Metadata } from 'next';
import { fetchOrders } from '@/api/orders';
import { OrderList } from '@/components/orders/OrderList';

export const metadata: Metadata = { title: 'Orders | MyApp' };

export default async function OrdersPage() {
  const orders = await fetchOrders(); // runs on the server, never bundled

  return (
    <main className="p-6">
      <h1 className="text-2xl font-semibold">Orders</h1>
      <OrderList orders={orders} />
    </main>
  );
}
```

```tsx
// src/components/orders/OrderList.tsx — Client Component (interactivity only)
'use client';

import { useState } from 'react';
import type { Order } from '@/types/order';

export function OrderList({ orders }: { orders: Order[] }) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <ul>
      {orders.map((order) => (
        <li
          key={order.id}
          onClick={() => setSelected(order.id)}
          className={selected === order.id ? 'bg-accent' : undefined}
        >
          {order.reference} — {order.total}
        </li>
      ))}
    </ul>
  );
}
```

---

## Decision: I need a client wrapper but the children are server-rendered

Passing Server Components *through* a Client Component works — via `children` or any prop —
because the server renders them before the client boundary is reached. Importing them does not.

### Bad — importing a Server Component inside a Client Component

```tsx
'use client';

import { useState } from 'react';
import { OrderSummary } from '@/components/orders/OrderSummary'; // async server component

export function Accordion() {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)}>Details</button>
      {/* OrderSummary is now compiled as a Client Component and its server-only
          imports (db, secrets, fs) break the build or leak to the bundle. */}
      {open && <OrderSummary />}
    </div>
  );
}
```

### Good — the server component is passed in as `children`

```tsx
// src/components/ui/Accordion.tsx
'use client';

import { useState, type ReactNode } from 'react';

export function Accordion({ label, children }: { label: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button onClick={() => setOpen(!open)} aria-expanded={open}>
        {label}
      </button>
      {open && children}
    </div>
  );
}
```

```tsx
// app/(dashboard)/orders/[id]/page.tsx — Server Component composes them
import { Accordion } from '@/components/ui/Accordion';
import { OrderSummary } from '@/components/orders/OrderSummary';

export default async function OrderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <Accordion label="Details">
      <OrderSummary orderId={id} />
    </Accordion>
  );
}
```

---

## Decision: keeping server-only code out of the bundle

Any module a Client Component imports is bundled. Guard modules that hold secrets.

### Bad

```ts
// src/api/rails-server.ts
export const railsServer = axios.create({
  baseURL: process.env.RAILS_INTERNAL_URL,
  headers: { 'X-Api-Key': process.env.RAILS_API_KEY! }, // secret
});
```

A stray `import { railsServer }` in a Client Component inlines `RAILS_API_KEY` into JS sent to
the browser — silently, because Next only strips `NEXT_PUBLIC_`-less vars it can prove are unused.

### Good — fail the build instead

```ts
// src/api/rails-server.ts
import 'server-only'; // throws at build time if imported from a Client Component
import axios from 'axios';

export const railsServer = axios.create({
  baseURL: process.env.RAILS_INTERNAL_URL,
  headers: { 'X-Api-Key': process.env.RAILS_API_KEY! },
});
```

Mirror image: mark browser-only modules with `import 'client-only'`.

---

## Decision: hydrating a Client Component that also needs TanStack Query

Do not refetch on mount what the server already has. Seed the cache.

### Bad — double fetch, loading spinner on a page that had the data

```tsx
'use client';
import { useQuery } from '@tanstack/react-query';

export function OrderList() {
  const { data, isLoading } = useQuery({ queryKey: ['orders'], queryFn: fetchOrders });
  if (isLoading) return <Spinner />;
  return <ul>{data!.map((o) => <li key={o.id}>{o.reference}</li>)}</ul>;
}
```

### Good — server fetch, passed as `initialData`

```tsx
// app/(dashboard)/orders/page.tsx
import { fetchOrders } from '@/api/orders';
import { OrderList } from '@/components/orders/OrderList';

export default async function OrdersPage() {
  const orders = await fetchOrders();
  return <OrderList initialOrders={orders} />;
}
```

```tsx
// src/components/orders/OrderList.tsx
'use client';
import { useQuery } from '@tanstack/react-query';
import type { Order } from '@/types/order';

export function OrderList({ initialOrders }: { initialOrders: Order[] }) {
  const { data } = useQuery({
    queryKey: ['orders'],
    queryFn: fetchOrdersClient,
    initialData: initialOrders, // no spinner, no waterfall
    staleTime: 30_000,
  });

  return <ul>{data.map((o) => <li key={o.id}>{o.reference}</li>)}</ul>;
}
```

Use TanStack Query in Next.js only when you need polling, infinite scroll, or optimistic updates.
A plain server fetch is the default.

---

## Decision: the page has one slow query — block or stream?

`await`ing at the top of a page blocks the whole HTML response. Wrap the slow part in
`<Suspense>` so the shell streams immediately.

### Bad — fast header waits on a slow analytics call

```tsx
export default async function DashboardPage() {
  const user = await fetchUser();          // 20ms
  const analytics = await fetchAnalytics(); // 2500ms — blocks everything, and it's sequential
  return (
    <>
      <Header user={user} />
      <AnalyticsPanel data={analytics} />
    </>
  );
}
```

### Good — stream the slow region

```tsx
// app/(dashboard)/page.tsx
import { Suspense } from 'react';
import { fetchUser } from '@/api/users';
import { AnalyticsPanel } from '@/components/dashboard/AnalyticsPanel';
import { AnalyticsSkeleton } from '@/components/dashboard/AnalyticsSkeleton';

export default async function DashboardPage() {
  const user = await fetchUser();

  return (
    <>
      <Header user={user} />
      <Suspense fallback={<AnalyticsSkeleton />}>
        {/* AnalyticsPanel does its own await; the shell ships first */}
        <AnalyticsPanel />
      </Suspense>
    </>
  );
}
```

```tsx
// src/components/dashboard/AnalyticsPanel.tsx — Server Component
import { fetchAnalytics } from '@/api/analytics';

export async function AnalyticsPanel() {
  const data = await fetchAnalytics();
  return <ApexWrapper series={data.series} />;
}
```

If two independent fetches must both complete, run them in parallel — never sequential `await`s:

```tsx
const [user, orders] = await Promise.all([fetchUser(), fetchOrders()]);
```

---

## Decision: which boundary file does this route need?

Every route segment that fetches data needs both. They are per-segment, and they compose with
the segment's `layout.tsx`.

| File | Purpose | Component type |
|------|---------|----------------|
| `loading.tsx` | Automatic `<Suspense>` fallback for the segment | Server |
| `error.tsx` | Recoverable render/fetch errors in the segment | **Must** be `'use client'` |
| `not-found.tsx` | Rendered by `notFound()` from `next/navigation` | Server |
| `global-error.tsx` | Root-layout failures only; must render `<html>`/`<body>` | `'use client'` |

```tsx
// app/(dashboard)/orders/error.tsx
'use client';

import { useEffect } from 'react';

export default function OrdersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('orders segment failed', { digest: error.digest });
  }, [error]);

  return (
    <div role="alert" className="p-6">
      <h2 className="text-lg font-semibold">Could not load orders</h2>
      <button onClick={reset} className="mt-4 underline">
        Try again
      </button>
    </div>
  );
}
```

Note `error.tsx` does **not** catch errors thrown in `layout.tsx` of the same segment — put the
boundary in the parent segment if the layout itself can fail.

---

## Testing rendering (Vitest + RTL)

Async Server Components are just async functions returning JSX — call and render the result.

```tsx
// tests/orders-page.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import OrdersPage from '@/app/(dashboard)/orders/page';

vi.mock('@/api/orders', () => ({
  fetchOrders: vi.fn().mockResolvedValue([{ id: '1', reference: 'ORD-1', total: '10.00' }]),
}));

describe('OrdersPage', () => {
  it('should render each order when the API returns results', async () => {
    render(await OrdersPage());
    expect(screen.getByText(/ORD-1/)).toBeInTheDocument();
  });
});
```

Client Components render normally; use MSW to intercept their HTTP calls rather than mocking axios.
