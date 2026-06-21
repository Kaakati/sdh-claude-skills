---
name: nextjs-dev
description: Build Next.js App Router web features with Server Components, server actions, data fetching, Suspense streaming, middleware, SEO metadata, and deployment to Vercel or AWS. Use this skill whenever someone asks to build a server-rendered page, create a server component, implement a server action, set up Next.js routing, configure ISR/SSG, or says things like "create a server component for X", "build the SSR page", "add a server action", "set up Next.js middleware", "configure ISR for Y", "deploy to Vercel", or "add SEO metadata". Also trigger when someone mentions App Router patterns, Server vs Client Components, streaming with Suspense, or Next.js deployment.
model: sonnet
---

# Next.js (App Router) Developer

Build production-ready Next.js web features using the App Router with Server Components, server actions, Suspense streaming, and Tailwind CSS. All features consume the shared Rails API backend.

@rules/nextjs.md

## Development Workflow

### Step 1: Understand the Feature

1. Clarify the page structure and URL hierarchy.
2. Determine which parts need server rendering (SEO, initial data) vs client interactivity.
3. Identify data sources — Rails API endpoints, ISR revalidation strategy.
4. Determine if server actions are needed for mutations.
5. Check if middleware is required (auth, locale, redirects).

### Step 2: Define Domain Types

Same as ReactJS SPA — create in `next/src/domain/` or `next/src/types/`:

```typescript
// next/src/domain/order.ts — Pure TypeScript, no framework imports
export interface Order { id: string; status: OrderStatus; totalAmount: number; }
export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';
```

### Step 3: Build Server Component Pages

```tsx
// next/app/orders/page.tsx
import type { Metadata } from 'next';
import { OrderTable } from '@/components/OrderTable';
import { railsApi } from '@/api/client';

export const metadata: Metadata = {
  title: 'Orders | MyApp',
  description: 'View and manage your orders',
};

export const revalidate = 60; // ISR: revalidate every 60 seconds

export default async function OrdersPage() {
  const orders = await railsApi.get('/api/v1/orders');
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Orders</h1>
      <OrderTable initialData={orders} />
    </div>
  );
}
```

### Step 4: Build Server Actions

Create server actions in `next/src/actions/` for mutations:

```tsx
// next/src/actions/orders.ts
'use server';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const CreateOrderSchema = z.object({ /* ... */ });

export async function createOrder(prevState: unknown, formData: FormData) {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { errors: parsed.error.flatten().fieldErrors };
  // Call Rails API, then revalidate
  revalidatePath('/orders');
  return { success: true };
}
```

### Step 5: Add Loading and Error Boundaries

```tsx
// next/app/orders/loading.tsx
export default function OrdersLoading() {
  return <OrderTableSkeleton />;
}

// next/app/orders/error.tsx
'use client';
export default function OrdersError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="text-center">
      <p className="text-red-600">Failed to load orders</p>
      <button onClick={reset} className="mt-2 text-blue-600 underline">Try again</button>
    </div>
  );
}
```

### Step 6: Add Client Components (When Needed)

Extract interactive parts into separate Client Components:

```tsx
// next/src/components/OrderFilters.tsx
'use client';
import { useRouter, useSearchParams } from 'next/navigation';

export function OrderFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // Client-side filtering with URL state
}
```

### Step 7: Configure Metadata and SEO

- Every page exports `metadata` or `generateMetadata`.
- Dynamic pages use `generateMetadata` with data fetching.
- Add Open Graph and Twitter card metadata for social sharing.
- Set canonical URLs to prevent duplicate content.

### Step 8: Add Middleware (If Needed)

```typescript
// next/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token');
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

### Step 9: Testing

- **Server Components**: Test as async functions — call and assert on returned JSX.
- **Server Actions**: Test as async functions with FormData input.
- **Client Components**: Test with React Testing Library (same as ReactJS SPA).
- **MSW** for mocking Rails API responses.

### Step 10: Deployment

#### Vercel
```bash
# Install CLI
npm i -g vercel

# Deploy preview
vercel

# Deploy production
vercel --prod
```

#### AWS ECS (standalone)
```bash
# Set standalone output in next.config.ts
# Build and deploy as Docker container
next build
docker build -t myapp-next .
```

## Checklist Before Done

- [ ] Server Components used for data fetching (no `'use client'` on pages)
- [ ] Every page exports `metadata` or `generateMetadata`
- [ ] `loading.tsx` and `error.tsx` boundaries in place
- [ ] Server actions validate input with zod
- [ ] Server actions call `revalidatePath` / `revalidateTag` after mutations
- [ ] `next/image` for images, `next/link` for navigation
- [ ] Responsive Tailwind CSS design
- [ ] Accessibility: semantic HTML, keyboard navigation, WCAG AA contrast
- [ ] Tests for server components, server actions, and client components
