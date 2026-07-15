# Routing, Code Splitting & Bundle Budget (Vite SPA)

Load-bearing rules restated (hold even if you read nothing else):

1. **Every page component is lazy-loaded.** No eager `import Dashboard from '@/pages/Dashboard'`
   inside the router.
2. **`<Suspense>` lives at the layout level**, not wrapped around each `<Route>`.
3. **Auth guards are route-level** (loader or a guard layout element) — never an `if (!user)`
   scattered inside a page body.
4. **Initial JS budget: < 300KB minified, uncompressed** — the same thing
   `build.chunkSizeWarningLimit: 300` compares against and what `dist/assets/*.js` shows on disk,
   so the number in the config and the number in this rule are one number. **State the unit
   whenever you restate the budget**: gzipped and uncompressed are *different measures* of the same
   bundle, and converting between them needs that bundle's actual compression ratio — which varies
   with its content and is not a constant you can carry in your head. So "150KB" and "300KB" may
   describe the same artifact or wildly different ones, and a reader given both without units
   cannot tell which. Read the build output: it prints both. Verify with `vite-bundle-visualizer` before
   shipping a new heavy dependency.

---

## Decision: how do I add a route?

Use `createBrowserRouter` with a nested layout, `React.lazy` for every page, and one `<Suspense>`
in the layout's outlet position.

### Bad — eager imports, per-route Suspense, inline auth check

```tsx
// src/router/index.tsx  ❌
import { createBrowserRouter } from 'react-router-dom';
import Dashboard from '../pages/Dashboard';       // ❌ pulls the whole page into the entry chunk
import Orders from '../pages/Orders';             // ❌ …and ApexCharts with it
import OrderDetail from '../pages/OrderDetail';

export const router = createBrowserRouter([
  { path: '/', element: <AppLayout />, children: [
    { index: true, element: <Suspense fallback={<Spinner />}><Dashboard /></Suspense> },  // ❌ noise
    { path: 'orders', element: <Orders /> },
  ]},
]);
```

```tsx
// src/pages/Orders.tsx  ❌ auth check inside the page
export default function Orders() {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" />;   // ❌ page already mounted, queries already fired
  return <OrderTable />;
}
```

### Good

```tsx
// src/router/index.tsx  ✅
import { createBrowserRouter, redirect } from 'react-router-dom';
import { lazy } from 'react';
import { AppLayout } from '@/components/layouts/AppLayout';
import { useAuthStore } from '@/stores/auth-store';

const Dashboard   = lazy(() => import('@/pages/Dashboard'));
const Orders      = lazy(() => import('@/pages/Orders'));
const OrderDetail = lazy(() => import('@/pages/OrderDetail'));
const Login       = lazy(() => import('@/pages/Login'));

function requireAuth() {
  if (!useAuthStore.getState().accessToken) {
    throw redirect(`/login?next=${encodeURIComponent(location.pathname)}`);
  }
  return null;
}

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    path: '/',
    element: <AppLayout />,
    errorElement: <RouteError />,
    loader: requireAuth,               // ✅ runs before the page chunk even loads
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'orders', element: <Orders /> },
      { path: 'orders/:id', element: <OrderDetail />, loader: orderDetailLoader },
    ],
  },
]);
```

```tsx
// src/components/layouts/AppLayout.tsx  ✅ one Suspense boundary for all lazy children
import { Suspense } from 'react';
import { Outlet } from 'react-router-dom';

export function AppLayout() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <Suspense fallback={<PageSkeleton />}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  );
}
```

Page components are default exports — `React.lazy` requires a module whose `default` is the
component. This is the one place the "named exports only" habit does not apply.

---

## Decision: loader vs. useQuery for route data

**Default: `useQuery` inside the page.** Loaders bypass the Query cache, so data fetched in a
loader is invisible to `invalidateQueries` and will not refetch after a mutation.

Use a loader only for:
- **Auth/permission gates** (no data, just a `redirect` throw).
- **Param validation** (throw a 404 `Response` for a malformed `:id`).
- **Prefetching into the Query cache** — the one legitimate data loader.

### Good — loader that prefetches into the cache, page still uses `useQuery`

```ts
// src/router/loaders.ts
import type { LoaderFunctionArgs } from 'react-router-dom';
import { queryClient } from '@/api/query-client';
import { orderKeys, fetchOrder } from '@/api/orders';

export async function orderDetailLoader({ params }: LoaderFunctionArgs) {
  const id = params.id;
  if (!id) throw new Response('Not found', { status: 404 });

  // Warm the cache; the page's useQuery reads it instantly and still owns refetching.
  await queryClient.ensureQueryData({
    queryKey: orderKeys.detail(id),
    queryFn: () => fetchOrder(id),
  });
  return null;
}
```

```tsx
// src/pages/OrderDetail.tsx
export default function OrderDetail() {
  const { id } = useParams<{ id: string }>();
  const { data: order } = useOrder(id!);   // ✅ cache hit, and still invalidatable
  return <OrderSummary order={order!} />;
}
```

### Bad — loader returns data the page consumes via `useLoaderData`

```tsx
// ❌ this data is now outside TanStack Query: no invalidation, no refetch-on-focus,
//    and mutating the order elsewhere leaves this view stale until a full navigation.
export async function loader({ params }) {
  const { data } = await api.get(`/orders/${params.id}`);
  return data.data;
}
export default function OrderDetail() {
  const order = useLoaderData() as Order;
  return <OrderSummary order={order} />;
}
```

---

## Decision: this chunk is too big — what do I split?

Split at two seams: **routes** (already done via `lazy`) and **heavy leaf dependencies**.

Heavy deps in this stack that deserve their own chunk when used on only some pages:
`react-apexcharts` + `apexcharts` (~150KB gzip), rich-text editors, PDF viewers, map SDKs.

### Bad — a chart library in the entry chunk

```tsx
// src/components/RevenueChart.tsx  ❌
import Chart from 'react-apexcharts';   // static import

export function RevenueChart({ series }: { series: ApexAxisChartSeries }) {
  return <Chart type="area" series={series} options={chartOptions} height={320} />;
}
```

If `RevenueChart` is imported by a shared component barrel (`components/index.ts`), ApexCharts
lands in the entry bundle for every route — including the login page.

### Good — lazy the heavy component, not just the page

```tsx
// src/components/charts/RevenueChart.tsx  ✅
import { lazy, Suspense } from 'react';
import type { ApexOptions } from 'apexcharts';

const Chart = lazy(() => import('react-apexcharts'));

interface RevenueChartProps {
  series: ApexAxisChartSeries;
  options: ApexOptions;
}

export function RevenueChart({ series, options }: RevenueChartProps) {
  return (
    <Suspense fallback={<div className="h-80 animate-pulse rounded bg-slate-200 dark:bg-slate-800" />}>
      <Chart type="area" series={series} options={options} height={320} />
    </Suspense>
  );
}
```

Also: **never barrel-export heavy components.** A `components/index.ts` that re-exports
`RevenueChart` defeats tree-shaking for every consumer. Import from the concrete path.

---

## Decision: named manual chunks

Vendor splitting stops the whole `node_modules` tree from invalidating on every app change.

```ts
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-charts': ['apexcharts', 'react-apexcharts'],
          'vendor-motion': ['framer-motion'],
        },
      },
    },
    chunkSizeWarningLimit: 300, // KB — matches the initial-JS budget
  },
});
```

Do not over-split: a chunk under ~10KB costs more in request overhead than it saves.

---

## Prefetching on intent

Lazy routes cost a network round-trip on click. Warm them on hover.

```tsx
// src/components/NavLink.tsx
import { Link } from 'react-router-dom';

const routeImports = {
  '/orders': () => import('@/pages/Orders'),
  '/reports': () => import('@/pages/Reports'),
} as const;

export function PrefetchLink({ to, children }: { to: keyof typeof routeImports; children: React.ReactNode }) {
  return (
    <Link to={to} onMouseEnter={() => void routeImports[to]()} onFocus={() => void routeImports[to]()}>
      {children}
    </Link>
  );
}
```

---

## Verifying the budget

```bash
npx vite-bundle-visualizer          # opens a treemap of the built chunks
npm run build -- --sourcemap        # then inspect dist/assets/*.js sizes
```

What to look for, in order:
1. Anything in the **entry chunk** that only one route needs → move behind `lazy`.
2. A **date library** imported wholesale (`import moment from 'moment'`) → replace with
   `date-fns` named imports or `Intl.DateTimeFormat`.
3. **Icon packs** imported as a namespace (`import * as Icons from 'lucide-react'`) → import the
   two icons you use by name.
4. **Duplicated vendor copies** — usually two versions of the same transitive dep; dedupe in
   `resolve.dedupe`.
