# Next.js App Router — Client Patterns

## Progressive Enhancement Form (Client Component)

```tsx
// next/src/components/forms/CreateOrderForm.tsx
'use client';

import { useActionState } from 'react';
import { createOrder, type CreateOrderState } from '@/actions/orders';
import { cn } from '@/lib/cn';

export function CreateOrderForm() {
  const [state, formAction, isPending] = useActionState<CreateOrderState, FormData>(
    createOrder,
    null,
  );

  return (
    <form action={formAction} className="space-y-4">
      <div>
        <label htmlFor="customerName" className="block text-sm font-medium">
          Customer Name
        </label>
        <input
          id="customerName"
          name="customerName"
          className={cn(
            'mt-1 block w-full rounded-md border px-3 py-2',
            state?.errors?.customerName ? 'border-red-500' : 'border-gray-300',
          )}
        />
        {state?.errors?.customerName && (
          <p className="mt-1 text-sm text-red-600">{state.errors.customerName[0]}</p>
        )}
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          className={cn(
            'mt-1 block w-full rounded-md border px-3 py-2',
            state?.errors?.email ? 'border-red-500' : 'border-gray-300',
          )}
        />
        {state?.errors?.email && (
          <p className="mt-1 text-sm text-red-600">{state.errors.email[0]}</p>
        )}
      </div>

      {state?.message && (
        <p className="text-sm text-red-600">{state.message}</p>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isPending ? 'Creating...' : 'Create Order'}
      </button>
    </form>
  );
}
```

## Client Component with TanStack Query (Real-Time Data)

```tsx
// next/src/components/LiveOrderTracker.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import type { Order } from '@/domain/order';

interface LiveOrderTrackerProps {
  orderId: string;
  initialData: Order;
}

export function LiveOrderTracker({ orderId, initialData }: LiveOrderTrackerProps) {
  const { data: order } = useQuery({
    queryKey: ['orders', orderId],
    queryFn: () => apiClient.get<Order>(`/api/v1/orders/${orderId}`),
    initialData,
    refetchInterval: 10_000, // Poll every 10 seconds
  });

  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-semibold">Order #{order.id}</h3>
      <p className="text-sm text-gray-600">Status: {order.status}</p>
    </div>
  );
}
```
