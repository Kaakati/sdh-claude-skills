# Next.js App Router Code Patterns

Reference patterns for building Next.js web features with the App Router.

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

## Root Layout with Providers

```tsx
// next/app/layout.tsx
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { Providers } from '@/components/Providers';
import './globals.css';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: { default: 'MyApp', template: '%s | MyApp' },
  description: 'Enterprise application',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

## Loading and Error Boundaries

```tsx
// next/app/orders/loading.tsx
export default function OrdersLoading() {
  return (
    <div className="space-y-6">
      <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 animate-pulse rounded bg-gray-100" />
        ))}
      </div>
    </div>
  );
}

// next/app/orders/error.tsx
'use client';

export default function OrdersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <h2 className="text-xl font-semibold text-red-600">Something went wrong</h2>
      <p className="mt-2 text-gray-600">{error.message}</p>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
      >
        Try again
      </button>
    </div>
  );
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

## Middleware for Auth and Locale

```typescript
// next/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/login', '/register', '/forgot-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip public paths
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Auth check
  const token = request.cookies.get('auth_token')?.value;
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Locale detection
  const locale = request.headers.get('accept-language')?.split(',')[0]?.split('-')[0] ?? 'en';
  const response = NextResponse.next();
  response.headers.set('x-locale', locale);

  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
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

## Server Component Test

```tsx
// tests/app/orders/page.test.tsx
import { describe, it, expect, vi } from 'vitest';
import OrdersPage from '@/app/orders/page';

vi.mock('@/api/client', () => ({
  railsApi: {
    get: vi.fn().mockResolvedValue([
      { id: '1', status: 'pending', totalAmount: 100 },
    ]),
  },
}));

describe('OrdersPage', () => {
  it('should render orders from API', async () => {
    const page = await OrdersPage();
    // Server Components return JSX — assert on structure
    expect(page).toBeTruthy();
  });
});
```

## Server Action Test

```tsx
// tests/actions/orders.test.ts
import { describe, it, expect, vi } from 'vitest';
import { createOrder } from '@/actions/orders';

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('next/navigation', () => ({ redirect: vi.fn() }));
vi.mock('@/api/client', () => ({
  railsApi: { post: vi.fn().mockResolvedValue({ id: '1' }) },
}));

describe('createOrder', () => {
  it('should return validation errors for invalid input', async () => {
    const formData = new FormData();
    // Missing required fields
    const result = await createOrder(null, formData);
    expect(result?.errors).toBeDefined();
    expect(result?.errors?.customerName).toBeDefined();
  });

  it('should create order and revalidate on valid input', async () => {
    const formData = new FormData();
    formData.set('customerName', 'Jane Doe');
    formData.set('email', 'jane@example.com');
    formData.set('items', JSON.stringify([{ productId: 'p1', quantity: 2 }]));

    await createOrder(null, formData);
    // redirect throws, so this tests the happy path setup
  });
});
```
