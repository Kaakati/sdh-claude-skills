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

```tsx
// next/src/actions/orders.ts
'use server';

import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { z } from 'zod';
import { railsApi } from '@/api/client';

const CreateOrderSchema = z.object({
  customerName: z.string().min(1, 'Customer name is required'),
  email: z.string().email('Invalid email'),
  items: z.string().transform((val) => {
    const parsed = JSON.parse(val);
    return z.array(z.object({
      productId: z.string(),
      quantity: z.number().positive(),
    })).parse(parsed);
  }),
});

export type CreateOrderState = {
  errors?: Record<string, string[]>;
  message?: string;
} | null;

export async function createOrder(
  prevState: CreateOrderState,
  formData: FormData,
): Promise<CreateOrderState> {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));

  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors };
  }

  try {
    await railsApi.post('/api/v1/orders', parsed.data);
  } catch {
    return { message: 'Failed to create order. Please try again.' };
  }

  revalidatePath('/orders');
  redirect('/orders');
}
```

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
