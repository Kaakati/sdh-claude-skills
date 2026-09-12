---
name: nextjs-dev
description: Build Next.js App Router web features with Server Components, server actions, data fetching, Suspense streaming, middleware, SEO metadata, and deployment to Vercel or AWS — UI built from shadcn/ui components and blocks (Base UI or Radix, read from components.json) on house design tokens, drill-down navigation (areas-only sidebar, section sub-nav in area layouts, list state in the URL, breadcrumbs from the API's ancestors, a command palette), shadcn Field forms re-validated in server actions, Recharts charts through shadcn's chart component, and CASL permission gates on sidebars, menus, and actions. Use this skill whenever someone asks to build a server-rendered page, create a server component, implement a server action, set up Next.js routing, configure ISR/SSG, add a shadcn/ui component or block, build a form or a dashboard chart, build a role-gated sidebar or dashboard, or says things like "create a server component for X", "build the SSR page", "add a server action", "add the shadcn sidebar block", "add a revenue chart", "set up Next.js middleware", "configure ISR for Y", "deploy to Vercel", or "add SEO metadata". Also trigger when someone mentions App Router patterns, Server vs Client Components, streaming with Suspense, shadcn/ui, Recharts in Next.js, or Next.js deployment.
model: sonnet
agent: nextjs-developer
context: fork
---

# Next.js (App Router) Developer

Build production-ready Next.js web features using the App Router with Server Components, server actions, Suspense streaming, shadcn/ui components on house design tokens, and Tailwind CSS. All features consume the shared Rails API backend.

This skill runs as the `nextjs-developer` agent in a forked context — it owns the UI protocol (detect the shadcn base from `components.json`, look up and `add` with the CLI, keep shadcn's aliased token names, gate with CASL, place on the atomic ladder). The agent preloads two skills: `std-nextjs` (App Router conventions) and `std-shadcn-ui` (the component standard).

## Development Workflow

### Step 1: Understand the Feature

1. Clarify the page structure and URL hierarchy.
2. Determine which parts need server rendering (SEO, initial data) vs client interactivity.
3. Identify data sources — Rails API endpoints, ISR revalidation strategy.
4. Determine if server actions are needed for mutations.
5. Check if middleware is required (auth, locale, redirects).
6. Place each route in the drill-down model — its area (one route group per area) and level, its
   URL and query parameters, its breadcrumb from the API's `ancestors`, where Up and Back go, and
   where focus lands → `@skills/std-nextjs/references/navigation.md`. An existing nested sidebar or
   history-built breadcrumb on a screen you touch is migrated as part of the work.

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

Create server actions in `next/src/actions/` for mutations. The zod schema lives in its own module
so the form's resolver and the action import the same one — the action re-checks what the form
already checked, because a server action is a public endpoint:

```tsx
// next/src/actions/orders.ts
'use server';
import { revalidatePath } from 'next/cache';
import type { ActionResult } from '@/actions/result';
import { CreateOrderSchema } from '@/schemas/order'; // the form's zodResolver imports this too

export async function createOrder(_prev: ActionResult<null> | null, formData: FormData): Promise<ActionResult<null>> {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false, fieldErrors: parsed.error.flatten().fieldErrors };
  // Authorize from the session, call the Rails API, then revalidate
  revalidatePath('/orders');
  return { ok: true, data: null };
}
```

### Step 5: Add Loading and Error Boundaries

```tsx
// next/app/orders/loading.tsx — built from shadcn's Skeleton
export default function OrdersLoading() {
  return <OrderTableSkeleton />;
}

// next/app/orders/error.tsx
'use client';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';

export default function OrdersError({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations('orders');
  return (
    <div role="alert" className="text-center">
      <p className="text-error">{t('loadFailed')}</p>
      <Button variant="outline" onClick={reset} className="mt-2">{t('retry')}</Button>
    </div>
  );
}
```

### Step 6: Add Client Components (When Needed)

Extract interactive parts into separate Client Components. Compose them from the shadcn/ui
primitives already in the package before adding new ones — and write them for the package's base.
`style` in `components.json` decides: `base-*` is Base UI, `radix-*` / `new-york` / `default` is
Radix, `aria-*` is React Aria. One base per package, and the APIs differ:

```tsx
// Radix package — the trigger merges onto its child
<DialogTrigger asChild>
  <Button variant="outline">{t('edit')}</Button>
</DialogTrigger>

// Base UI package — the trigger renders as the element you pass
<DialogTrigger render={<Button variant="outline" />}>{t('edit')}</DialogTrigger>
```

Look a component up with the CLI before writing it — `npx shadcn@latest docs <component>` answers
for the project's base — and preview with `npx shadcn@latest add <item> --dry-run`. What never runs
without a human (`init` on an existing app, `apply`, `--overwrite`, `eject`, `mcp init`) →
`@skills/std-shadcn-ui/references/cli-and-registry.md`.

```tsx
// next/src/components/OrderFilters.tsx
'use client';
import { useRouter, useSearchParams } from 'next/navigation';

export function OrderFilters() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // List state lives in the URL: router.push when a filter is applied (Back undoes it),
  // router.replace while typing in the search box; the list crumb restores the last query
}
```

Filters, sort and query are the API's list parameters, one-to-one, and a list-detail triage view is
a parallel slot plus an intercepting route → `@skills/std-nextjs/references/navigation.md`.

### Step 7: Forms, Charts, Feedback, and Theme

These have fixed house answers:

- **Forms** — shadcn `Field` + react-hook-form + zod on the client, the same schema re-checked with
  `safeParse` in the server action, errors in `FieldError` as translated messages, and
  `action={formAction}` kept on the `<form>` so it posts without JavaScript. Never `add form` (the
  legacy wrapper). → `references/client-patterns.md`
- **Charts** — `add chart`; a Server Component fetches, renders the loading, empty and error
  paths, and renders the caption, summary and `sr-only` data table; a `'use client'` leaf composes
  Recharts inside a sized `ChartContainer` with `ChartConfig` colors as `var(--chart-N)`,
  `accessibilityLayer` on, and `isAnimationActive={!reduceMotion}`. Only plain points cross. No other
  chart library. → `@skills/std-shadcn-ui/references/charts.md`
- **Navigation** — the app layout filters `NAV` with `visibleNav`; the global `AppSidebar` lists
  areas only; each area layout renders its section sub-nav; a detail renders its breadcrumb from
  `ancestors`; a command palette, where the product has one, mirrors the nav from a visible button
  and Cmd/Ctrl+K. → `@skills/std-nextjs/references/navigation.md`,
  `@skills/std-shadcn-ui/references/components-and-blocks.md`
- **Feedback** — outcomes go through the house `notify()` helper (translation keys) over the base's
  toast: Base UI → shadcn `Toast`, Radix → `sonner`, one `<Toaster />` in the root layout. A
  validation error never goes in a toast. → `@skills/std-shadcn-ui/references/forms-and-feedback.md`
- **Theme** — next-themes `ThemeProvider` (`attribute="class"`) + `suppressHydrationWarning` on
  `<html>` → `references/infrastructure-patterns.md`

### Step 8: Configure Metadata and SEO

- Every page exports `metadata` or `generateMetadata`.
- Dynamic pages use `generateMetadata` with data fetching.
- Add Open Graph and Twitter card metadata for social sharing.
- Set canonical URLs to prevent duplicate content.

### Step 9: Add Middleware — `proxy.ts` on Next.js 16 (If Needed)

Next.js 16 renames the convention: `proxy.ts` exporting `proxy`, on the Node.js runtime only
(`npx @next/codemod@canary middleware-to-proxy .`). The example is 15's `middleware.ts`, which 16
still runs, deprecated; 15 has no proxy convention →
`@skills/std-nextjs/references/middleware-seo-deploy.md`.

```typescript
// next/middleware.ts — Next.js 16: next/proxy.ts with `export function proxy`
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token');
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

### Step 10: Testing

- **Server Components**: Test as async functions — call and assert on returned JSX.
- **Server Actions**: Test as async functions with FormData input.
- **Client Components**: Test with React Testing Library (same as ReactJS SPA).
- **MSW** for mocking Rails API responses.

### Step 11: Deployment

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
- [ ] Server actions validate input with zod — the same schema module the form's resolver uses
- [ ] Server actions invalidate after mutations — `revalidatePath`, or `updateTag` (Next.js 16) / `revalidateTag` (15)
- [ ] `next/image` for images, `next/link` for navigation
- [ ] Responsive Tailwind CSS design
- [ ] UI composed from existing shadcn/ui primitives first, written for the package's base (`render` on Base UI, `asChild` on Radix); shadcn's token names left as written, raw palette colors replaced
- [ ] Forms on `Field`; outcomes through `notify()`
- [ ] Charts on shadcn's `chart` + Recharts in a client leaf, with the caption, summary and data table rendered by the Server Component and `isAnimationActive={!reduceMotion}` on every series
- [ ] Each route at one level of one area (its route group); the global sidebar lists areas only, sections render in the area layout; list state in the URL; breadcrumbs from `ancestors`; Back, Up and focus checked at every level
- [ ] Sidebars, menus, and actions gated by CASL permissions (never role names); the Rails policy stays the authority
- [ ] Accessibility: semantic HTML, keyboard navigation, WCAG AA contrast, focus rings at 3:1 or better
- [ ] Tests for server components, server actions, and client components

## Deep guides (read on demand, do not preload)

- Server Component pages, `generateMetadata`, server actions that re-check the form's shared schema, Route Handlers (BFF) → `references/server-patterns.md`
- `Field` forms on a server action (react-hook-form + zod, progressive enhancement), what a chart page adds on top of the chart standard, Client Components with TanStack Query → `references/client-patterns.md`
- Root layout (next-themes `ThemeProvider`, the base's `<Toaster />`), `Skeleton` loading and error boundaries, auth+locale middleware, Server Component and server-action tests → `references/infrastructure-patterns.md`

### Owned by `std-nextjs` (scoped to App Router work)

**This targets Next.js 15+.** That is not a footnote: 15 changed caching defaults and request
APIs, so the same code behaves differently on 14 — `fetch` is **not** cached by default,
`GET` route handlers are **not** cached, and `cookies()`/`params` are **async**
(`await params`, `await cookies()`). Guidance that does not say which major it means is guidance
you cannot check. The version table and both consequences live in the `std-nextjs` skill body.

- **Choosing the Server/Client boundary** → `@skills/std-nextjs/references/rendering.md`
- **Server actions: writing mutations** → `@skills/std-nextjs/references/server-actions.md`
- **Caching, ISR, revalidation, revalidating a drill-down level** → `@skills/std-nextjs/references/caching.md`
- **Middleware, SEO metadata, deployment** → `@skills/std-nextjs/references/middleware-seo-deploy.md`
- **Drill-down navigation** — route groups per area, the area layout's section sub-nav, list state
  in `searchParams`, list-detail panels, breadcrumbs from `ancestors`, focus, per-role nav tests →
  `@skills/std-nextjs/references/navigation.md`

### Owned elsewhere — do not duplicate

- **Building the UI** — the full protocol (base detection, CLI lookup and the ask-first list, the
  token rules, Atomic placement) → the `nextjs-developer` agent this skill runs as.
- **The component standard** — which base, the CLI and what never runs without a human, shadcn's
  token names as registered aliases of house roles, primitives and blocks, `Field` / Toast / sonner,
  focus-ring contrast, label props, RTL → the `std-shadcn-ui` skill:
  `@skills/std-shadcn-ui/references/cli-and-registry.md`,
  `@skills/std-shadcn-ui/references/components-and-blocks.md`,
  `@skills/std-shadcn-ui/references/forms-and-feedback.md`,
  `@skills/std-shadcn-ui/references/accessibility-and-i18n.md`. The token registry itself:
  `@skills/theming/references/platform-integration.md`.
- **Charts** — Recharts through shadcn's chart component, the server-rendered text alternative,
  reduced motion, never color alone → `@skills/std-shadcn-ui/references/charts.md`
- **The drill-down rules and the API behind them** — areas, levels, location cues, Back, the
  palette → `@skills/ui-ux-patterns/references/drill-down-navigation.md`; levels → endpoints,
  `ancestors`, search → `@skills/std-api-design/references/drill-down-resources.md`
- **Permission-gated sidebars, menus, and actions** — the layout builds the CASL ability from
  `getSession()` and filters the nav on the server, plain rules cross to the client
  `AbilityProvider`, `<Can>` / `allows()` only in client leaves, the Rails 403 is the authority →
  `@skills/access-control-designer/references/ui-gates.md`
- **What each role sees, and the three-state rule** (not rendered → locked → disabled with a
  visible reason, resolved permission → entitlement → record state) →
  `@skills/ui-ux-patterns/references/role-based-ux.md`
