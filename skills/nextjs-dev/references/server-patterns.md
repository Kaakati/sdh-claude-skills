# Next.js App Router — Server Patterns

## Server Component Page with Data Fetching

```tsx
// next/app/orders/page.tsx
import type { Metadata } from 'next';
import { Suspense } from 'react';
import { OrderTable } from '@/components/OrderTable';
import { OrderTableSkeleton } from '@/components/OrderTableSkeleton';
import { railsApi } from '@/api/client';
import type { Order } from '@/domain/order';

export const metadata: Metadata = {
  title: 'Orders | MyApp',
  description: 'View and manage all orders',
};

export const revalidate = 60;

async function OrdersContent() {
  const orders = await railsApi.get<Order[]>('/api/v1/orders');
  return <OrderTable initialData={orders} />;
}

export default function OrdersPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Orders</h1>
      <Suspense fallback={<OrderTableSkeleton />}>
        <OrdersContent />
      </Suspense>
    </div>
  );
}
```

## Dynamic Page with generateMetadata

```tsx
// next/app/orders/[id]/page.tsx
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { railsApi } from '@/api/client';
import { OrderDetail } from '@/components/OrderDetail';
import type { Order } from '@/domain/order';

interface OrderPageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: OrderPageProps): Promise<Metadata> {
  const { id } = await params;
  const order = await railsApi.get<Order>(`/api/v1/orders/${id}`);
  if (!order) return { title: 'Order Not Found' };
  return { title: `Order #${order.id} | MyApp` };
}

export default async function OrderPage({ params }: OrderPageProps) {
  const { id } = await params;
  const order = await railsApi.get<Order>(`/api/v1/orders/${id}`);
  if (!order) notFound();
  return <OrderDetail order={order} />;
}
```

## Server Action with Validation and Revalidation

The schema is not defined here. It lives in `src/schemas/order.ts`, which the client form's
`zodResolver` imports too (`@skills/nextjs-dev/references/client-patterns.md`), so the action
re-checks exactly what the form checked — the client check is UX, and a server action is a public
endpoint. Its messages are translation keys, which is why `fieldErrors` can go straight back into
the form's `FieldError`.

```tsx
// next/src/actions/orders.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { railsApi } from '@/api/client';
import type { ActionResult } from '@/actions/result';
import { requireSession } from '@/lib/auth';
import { CreateOrderSchema } from '@/schemas/order'; // the form's zodResolver imports the same schema

export async function createOrder(
  _prev: ActionResult<null> | null,
  formData: FormData,
): Promise<ActionResult<null>> {
  await requireSession(); // identity comes from the session, never from the form

  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData)); // re-check: the client can be bypassed
  if (!parsed.success) {
    const { formErrors, fieldErrors } = parsed.error.flatten();
    return { ok: false, formErrors, fieldErrors }; // translation keys, rendered by FieldError
  }

  try {
    await railsApi.post('/api/v1/orders', parsed.data);
  } catch {
    return { ok: false, formErrors: ['orders.errors.createFailed'] }; // a key, never the raw error
  }

  revalidatePath('/orders');
  redirect('/orders');
}
```

`ActionResult` is the one result shape every action returns →
`@skills/std-nextjs/references/server-actions.md`.

## Route Handler (BFF Pattern)

```typescript
// next/app/api/health/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
  });
}
```
