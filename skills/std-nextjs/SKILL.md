---
name: std-nextjs
description: Next.js App Router conventions — Server Components, server actions, ISR/SSG, Vercel. Use when building Next.js pages, layouts, or server actions.
paths:
  - "**/next.config.*"
  - "**/app/**/*.tsx"
  - "**/app/**/*.jsx"
  - "**/src/app/**/*.ts"
  - "**/src/app/**/*.tsx"
  - "**/middleware.ts"
---

# Next.js (App Router) Conventions

Rules for building Next.js web applications with the App Router, consuming the shared Rails API backend.

## Project Structure

```
next/
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── middleware.ts              # Edge middleware (auth, locale, redirects)
├── app/                       # App Router pages and layouts
│   ├── layout.tsx             # Root layout (providers, global styles)
│   ├── page.tsx               # Home page
│   ├── loading.tsx            # Root loading UI
│   ├── error.tsx              # Root error boundary
│   ├── not-found.tsx          # 404 page
│   ├── (auth)/                # Route group for auth pages
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/           # Route group for authenticated pages
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── orders/
│   │       ├── page.tsx
│   │       └── [id]/page.tsx
│   └── api/                   # Route Handlers (BFF endpoints only)
│       └── health/route.ts
├── src/
│   ├── components/            # Shared components
│   │   ├── ui/                # Design system primitives
│   │   └── forms/             # Form components
│   ├── actions/               # Server actions (use cases)
│   ├── hooks/                 # Client-side custom hooks
│   ├── stores/                # Zustand stores (client-only state)
│   ├── api/                   # Rails API client (axios)
│   ├── domain/                # Domain types and business rules
│   ├── types/                 # Shared TypeScript types
│   ├── lib/                   # Utilities (cn, auth helpers, etc.)
│   └── i18n/                  # Internationalization
└── tests/
    ├── setup.ts
    └── utils.tsx
```

## Technology Stack

| Concern | Library | Notes |
|---------|---------|-------|
| Framework | Next.js (App Router) | Server Components by default |
| Styling | Tailwind CSS | Same conventions as ReactJS SPA |
| Server State | TanStack Query | Client Components only |
| Client State | Zustand | Client Components only |
| HTTP | axios | Rails API client |
| Forms | react-hook-form + zod | Client Components |
| i18n | next-intl or react-i18next | Server + Client component support |
| Testing | Vitest + React Testing Library | Server component tests via async patterns |

## Server vs Client Components

### Server Components (Default)
- **Every component is a Server Component by default** — no `'use client'` directive needed.
- Use for: data fetching, static rendering, SEO-critical content, layouts.
- Can `await` async operations directly in the component body.
- Cannot use hooks, browser APIs, event handlers, or state.

### Client Components (`'use client'`)
- Add `'use client'` at the top of files that need interactivity.
- Use for: forms, interactive UI, Zustand stores, TanStack Query, event handlers.
- Keep Client Components as small and leaf-level as possible.
- **Never add `'use client'` to layout or page files** unless absolutely necessary — wrap interactive parts in separate Client Components.

### Composition Pattern
```tsx
// app/orders/page.tsx — Server Component (fetches data)
import { OrderTable } from '@/components/OrderTable'; // Client Component

export default async function OrdersPage() {
  const orders = await fetchOrders(); // Server-side fetch
  return <OrderTable initialData={orders} />;
}
```

## Server Actions

Server actions are the use-case layer for mutations:

```tsx
// src/actions/orders.ts
'use server';

import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const CreateOrderSchema = z.object({
  items: z.array(z.object({ productId: z.string(), quantity: z.number().positive() })),
  paymentMethod: z.string(),
});

export async function createOrder(formData: FormData) {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { error: parsed.error.flatten().fieldErrors };

  const result = await railsApi.post('/api/v1/orders', parsed.data);
  revalidatePath('/orders');
  return { data: result.data };
}
```

### Server Action Rules
- **Always validate input with zod** — server actions are public endpoints.
- **Call `revalidatePath` or `revalidateTag`** after mutations to refresh cached data.
- **Return serializable data only** — no class instances, no functions.
- **Never expose raw errors** — catch and return user-friendly error objects.
- **Use progressive enhancement** — forms should work without JavaScript via `action` attribute.

## Data Fetching

### Server Components (Preferred)
- Fetch data directly in Server Components using `async/await`.
- Use `fetch()` with Next.js cache options or the Rails API client.
- Set `revalidate` for ISR: `export const revalidate = 60;` (seconds).

### Client Components (When Needed)
- Use TanStack Query for client-side data fetching (polling, optimistic updates, infinite scroll).
- Pass initial data from Server Components via props to avoid loading states.

### Caching Strategy
- **Static pages**: `export const dynamic = 'force-static'` or no dynamic data.
- **ISR**: `export const revalidate = N` for time-based revalidation.
- **Dynamic**: `export const dynamic = 'force-dynamic'` for real-time data.
- **On-demand**: `revalidatePath()` / `revalidateTag()` after mutations.

## Middleware

```typescript
// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  // Auth check, locale detection, redirects
}

export const config = { matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'] };
```

- Use for: authentication redirects, locale detection, A/B testing, rate limiting.
- Keep middleware lightweight — runs on the Edge Runtime.
- Do not use for data fetching or heavy computation.

## Metadata and SEO

```tsx
// app/orders/page.tsx
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Orders | MyApp',
  description: 'View and manage your orders',
  openGraph: { title: 'Orders', description: 'View and manage your orders' },
};
```

- **Every page must export `metadata` or `generateMetadata`** for SEO.
- Use `generateMetadata` for dynamic pages that need data-dependent titles.
- Set canonical URLs to prevent duplicate content issues.

## Styling

- Same Tailwind CSS conventions as the ReactJS SPA rule (`reactjs.md`).
- Use `cn()` utility for conditional classes.
- Use CSS Modules only for complex animations that cannot be expressed in Tailwind.

## Performance

- **Prefer Server Components** — reduce client-side JavaScript bundle.
- **Use `next/image`** for all images — automatic optimization, lazy loading, responsive sizes.
- **Use `next/link`** for all internal navigation — prefetching enabled by default.
- **Streaming with `<Suspense>`** — wrap slow data-fetching sections for progressive rendering.
- **Bundle analysis**: Use `@next/bundle-analyzer` to audit client-side chunks.

## Deployment

### Vercel (Primary)
- Connect Git repository for automatic preview + production deployments.
- Environment variables set in Vercel dashboard.
- Use `vercel.json` for redirects, headers, and rewrites.

### AWS ECS (Alternative)
- Build with `next build` (standalone output mode).
- Deploy as a Docker container on ECS Fargate.
- Use CloudFront as CDN for static assets (`_next/static`).
- Set `output: 'standalone'` in `next.config.ts`.

## Anti-Patterns to Avoid

- Adding `'use client'` to page or layout files (extract interactive parts).
- Using `useEffect` for data fetching in pages (use Server Components or TanStack Query).
- Importing server-only code in Client Components.
- Missing `loading.tsx` or `error.tsx` boundaries.
- Using `<img>` instead of `next/image` or `<a>` instead of `next/link`.
- Skipping `metadata` exports on pages.
- Server actions without input validation.
