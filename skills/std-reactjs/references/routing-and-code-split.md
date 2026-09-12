# Routing, Code Splitting & Bundle Budget (Vite SPA)

Load-bearing rules restated (hold even if you read nothing else):

1. **Every page component is lazy-loaded.** No eager `import Dashboard from '@/pages/Dashboard'`
   inside the router.
2. **`<Suspense>` lives at the layout level** — the app layout, and each area layout around its own
   `<Outlet />` — never wrapped around each `<Route>`.
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
5. **Every drill level has a URL, and each area is a pathless layout route.** The area layout
   renders the section nav; the global sidebar holds areas only. A list's filters, sort and query
   are search params, `<ScrollRestoration />` renders once, and breadcrumbs come from the API's
   `ancestors` — never from route params or history.
6. **Import from `react-router`** (React Router 8), and `RouterProvider` from `react-router/dom`.

---

## Decision: which package do I import from?

React Router 8 "removes the `react-router-dom` re-export package": DOM-specific APIs — in data mode,
`RouterProvider` — come from `react-router/dom`, and everything else from `react-router` (React
Router docs — Upgrading from v7; React Router docs — Installation, Data mode). v8 needs React 19.2.7+
and Node 22.22+; on npm, `react-router-dom` stops at 7.18.3.

- **A package still on v7 keeps `react-router-dom` until it upgrades** — one package name per app,
  never both. The upgrade is `npm uninstall react-router-dom`, the import rename, and the guide's
  other changes (`useMatches()` entries expose `loaderData`, not `data`).
- Every example in this skill is v8.

---

## Decision: how do I add a route?

Use `createBrowserRouter`, `React.lazy` for every page, one pathless layout route per area, and
`<Suspense>` in the layouts' outlet positions.

### Bad — eager imports, per-route Suspense, inline auth check

```tsx
// src/router/index.tsx  ❌
import { createBrowserRouter } from 'react-router';
import Dashboard from '../pages/Dashboard';       // ❌ pulls the whole page into the entry chunk
import Orders from '../pages/Orders';             // ❌ …and Chart.js with it
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

### Good — lazy pages, loaders as gates, one pathless layout route per area

```tsx
// src/router/index.tsx  ✅
import { lazy, Suspense } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router';
import { AppLayout } from '@/components/templates/AppLayout/AppLayout';
import { AreaLayout } from '@/components/templates/AreaLayout/AreaLayout';
import { PageSkeleton } from '@/components/molecules/PageSkeleton/PageSkeleton';
import { RouteError } from '@/components/organisms/RouteError/RouteError';
import { requirePermission } from '@/router/require-permission';
import { landingRedirect, orderDetailLoader, orderListLoader, requireAuth } from '@/router/loaders';

const Login = lazy(() => import('@/pages/Login'));
const OrderList = lazy(() => import('@/pages/orders/OrderList'));
const OrderDetail = lazy(() => import('@/pages/orders/OrderDetail'));
const OrderLines = lazy(() => import('@/pages/orders/OrderLines'));
const OrderShipments = lazy(() => import('@/pages/orders/OrderShipments'));
const ShipmentDetail = lazy(() => import('@/pages/orders/ShipmentDetail'));
const Members = lazy(() => import('@/pages/organization/Members'));
const Billing = lazy(() => import('@/pages/organization/Billing'));

export const routes: RouteObject[] = [
  { path: '/login', element: <Suspense fallback={<PageSkeleton />}><Login /></Suspense> }, // outside AppLayout: its own boundary
  {
    path: '/',
    element: <AppLayout />,                          // AbilityProvider around AppShell: areas-only sidebar, header search, <ScrollRestoration />
    errorElement: <RouteError />,                    // only a failure in requireAuth or AppLayout itself: no shell left to keep
    loader: requireAuth,                             // ✅ runs before any page chunk loads
    children: [
      { index: true, loader: landingRedirect },      // the role's first reachable area, never a fixed page
      {
        errorElement: <RouteError />,                // 403 → the no-access page, 404 → not found, both inside the shell (ui-gates.md)
        children: [                                  // pathless and element-less: this route adds only the boundary
          {
            element: <AreaLayout areaKey="orders" />,    // pathless: an area adds no URL segment
            children: [
              { path: 'orders', element: <OrderList />, loader: orderListLoader },             // list
              {
                path: 'orders/:orderId', element: <OrderDetail />, loader: orderDetailLoader,   // detail: header, trail, tabs, <Outlet />
                children: [
                  { index: true, element: <OrderLines /> },
                  { path: 'shipments', element: <OrderShipments /> },                          // a tab with its own URL
                ],
              },
              { path: 'shipments/:shipmentId', element: <ShipmentDetail /> },                  // sub-detail: flat URL, same area
            ],
          },
          {
            element: <AreaLayout areaKey="organization" />, // two sections: its layout renders them as tabs
            children: [
              { path: 'members', element: <Members /> },
              { path: 'billing', element: <Billing />, loader: requirePermission('billing.update') },
            ],
          },
        ],
      },
    ],
  },
];

export const router = createBrowserRouter(routes);   // tests build a memory router from the same `routes`
```

- **Two boundaries, and the one for pages sits inside the shell.** "When an error is thrown, the
  'closest error boundary' will be rendered" (React Router docs — Error Boundaries), in place of the
  route that owns it — so a boundary only on `'/'` replaces `AppLayout`, sidebar included, for every
  403 and 404. The pathless boundary route keeps the shell; the one on `'/'` catches only what fails
  before a shell exists.

Page components are default exports — `React.lazy` requires a module whose `default` is the
component. This is the one place the "named exports only" habit does not apply. `AppLayout`,
`AppShell`, `AreaLayout` and what they render → *an area, its list state, and returning to it*,
below.

---

## Decision: loader vs. useQuery for route data

**Default: `useQuery` inside the page.** A loader that returns data bypasses the Query cache: that
data is invisible to `invalidateQueries` and will not refetch after a mutation.

Use a loader only for:
- **Auth/permission gates** (no data — a `redirect` or a 403 `Response`).
- **Param and URL-state validation** (a 404 `Response` for a malformed `:orderId`; a redirect to the
  plain list for tampered search params).
- **Prefetching into the Query cache** — the one legitimate data loader.

**Prefetch with `queryClient.query`.** TanStack Query 5 deprecates `ensureQueryData`,
`prefetchQuery` and `fetchQuery` in its favour, and "those methods will be removed in the next major
version" (TanStack — Prefetching & Router Integration). `query` returns cached data while it is
fresh by the `staleTime` you pass and fetches otherwise: "Prefetch only fires when data is older
than the staleTime, so in a case like this you definitely want to set one." `staleTime: 'static'`
reproduces `ensureQueryData` exactly — any cached data, whatever its age.

A permission loader is both a gate and a prefetch: it warms `['me']` through `queryClient.query`,
builds the CASL ability from those rules, and stops the route when its key is not granted — so the
`/me` payload stays in the Query cache, never in Zustand. Ability construction, the rules contract,
and why a denied *feature* is a page rather than a redirect →
`@skills/access-control-designer/references/ui-gates.md`.

### Good — gates and a prefetch in the loader, `useQuery` in the page

```ts
// src/router/loaders.ts
import { redirect, type LoaderFunctionArgs } from 'react-router';
import { queryClient } from '@/api/query-client';
import { fetchOrder, orderKeys } from '@/api/orders';
import { useAuthStore } from '@/stores/auth-store';

export function requireAuth({ request }: LoaderFunctionArgs) {
  if (!useAuthStore.getState().accessToken) {
    throw redirect(`/login?next=${encodeURIComponent(new URL(request.url).pathname)}`);
  }
  return null;
}

export async function orderDetailLoader({ params }: LoaderFunctionArgs) {
  const id = params.orderId;
  if (!id) throw new Response('Not found', { status: 404 });

  // Warm the cache; the page's useQuery reads it instantly and still owns refetching.
  await queryClient.query({ queryKey: orderKeys.detail(id), queryFn: () => fetchOrder(id), staleTime: 30_000 });
  return null;
}
```

```tsx
// src/pages/orders/OrderDetail.tsx
export default function OrderDetail() {
  const { orderId } = useParams<{ orderId: string }>();
  const { data: order } = useOrder(orderId!);   // ✅ cache hit, and still invalidatable
  return <OrderSummary order={order!} />;
}
```

A record is awaited, so a record outside the caller's scope — a 404 — reaches the page-level
`errorElement` inside the shell before the page mounts. A list is warmed fire-and-forget instead
(below), so its page and skeleton paint at once.

### Bad — loader returns data the page consumes via `useLoaderData`

```tsx
// ❌ this data is now outside TanStack Query: no invalidation, no refetch-on-focus,
//    and mutating the order elsewhere leaves this view stale until a full navigation.
export async function loader({ params }) {
  const { data } = await api.get(`/orders/${params.orderId}`);
  return data.data;
}
export default function OrderDetail() {
  const order = useLoaderData() as Order;
  return <OrderSummary order={order} />;
}
```

---

## Decision: an area, its list state, and returning to it

The rules — the levels, what the sidebar may hold, location cues, Up and Back — are
`@skills/ui-ux-patterns/references/drill-down-navigation.md`'s. The endpoints, `ancestors` and list
parameters are `@skills/std-api-design/references/drill-down-resources.md`'s. `NAV`, `visibleNav`
and `areaState` are `@skills/access-control-designer/references/ui-gates.md`'s. This is the React
Router half.

- **An area is a pathless layout route.** Child routes render through the parent's `<Outlet />`,
  an index route is the parent's default child, and a route with no `path` adds layout without a
  URL segment (React Router docs — Routing) — so a flat member URL like `/shipments/:shipmentId`
  still renders inside the Orders area.
- **The area layout renders the section nav and its own `<Suspense>`**, so the sections stay on
  screen while a page chunk loads. The global sidebar lists areas only.
- **Permissions filter before anything is built:** every nav surface reads one
  `visibleNav(NAV, ability, entitlements)` output.
- **A list's filters, sort and query are search params.** "Setting the search params causes a
  navigation" (React Router docs — useSearchParams): a filter change pushes a history entry and
  Back undoes it; typing replaces the entry until the query is committed. The params mirror the API
  list's; a cursor never enters the URL (`references/data-fetching.md`).
- **`<ScrollRestoration />` renders once.** It emulates the browser's restoration, keyed by
  `location.key` unless `getKey` says otherwise, and keeps positions in `sessionStorage` (React
  Router docs — ScrollRestoration). Key list routes by pathname plus search, so a return to the same
  filtered list — by Back, or by its crumb, a fresh navigation — lands where people left (Nielsen
  Norman Group — Designing Scroll Behavior; Baymard Institute — Return Users to the Same Place in
  the Product List). A live queue keeps the default key and starts at the top.
- **Up is a `<Link>` with a real `href`, never `history.back()`**, which leaves the app on a deep
  link (Baymard Institute — 4 Design Patterns That Violate "Back" Button UX Expectations). The trail
  comes from the record's `ancestors`, never from `useParams` or history.

```tsx
// src/hooks/useVisibleAreas.ts — every nav surface reads the same filtered output
import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAppAbility } from '@/components/providers/AbilityProvider';
import { meQuery } from '@/api/me';
import { NAV, visibleNav } from '@/lib/nav';

export function useVisibleAreas() {
  const ability = useAppAbility();   // @casl/react 7: under the AbilityProvider that AppLayout renders around AppShell
  const { data: me } = useQuery(meQuery);
  const areas = useMemo(() => (me ? visibleNav(NAV, ability, me.entitlements) : []), [me, ability]);
  return { areas, ready: me !== undefined };
}
```

```tsx
// src/components/templates/AppLayout/AppLayout.tsx — provides the ability and reads nothing from it
import { useQuery } from '@tanstack/react-query';
import { meQuery } from '@/api/me';
import { AbilityProvider } from '@/components/providers/AbilityProvider';
import { AppShell } from '@/components/templates/AppShell/AppShell';
import type { AppRule } from '@/lib/ability';

const NO_RULES: AppRule[] = [];   // a module constant, so the provider's memo holds until ['me'] arrives

export function AppLayout() {
  const { data: me } = useQuery(meQuery);
  return (
    <AbilityProvider rules={me?.permissions.rules ?? NO_RULES}>
      <AppShell />
    </AbilityProvider>
  );
}
```

```tsx
// src/components/templates/AppShell/AppShell.tsx — excerpt: rendered by AppLayout, inside the AbilityProvider
const LIST_PATHS = new Set(NAV.flatMap((area) => [area.href, ...(area.sections ?? []).map((s) => s.href)]));
const { areas } = useVisibleAreas();

<ScrollRestoration
  getKey={(location) => (LIST_PATHS.has(location.pathname) ? location.pathname + location.search : location.key)}
/>
{areas.length > 1 && <AppSidebar areas={areas} />}   {/* one area: its section nav is the primary nav */}
{/* …then the header with search on every page, and <Suspense> around <Outlet /> */}
```

- **The provider and its readers are separate components.** `useContext()` "does not consider
  providers in the component from which you're calling `useContext()`" (React docs — useContext).
  An `AppLayout` that rendered the provider and also called `useVisibleAreas()` would see no
  provider, and @casl/react 7's `useAbility()` throws ("AbilityContext is not provided"). The
  per-role tests keep rendering `<AppLayout />`.

```tsx
// src/components/templates/AreaLayout/AreaLayout.tsx — one template for every area
import { Suspense } from 'react';
import { Outlet } from 'react-router';
import { PageSkeleton } from '@/components/molecules/PageSkeleton/PageSkeleton';
import { NoAccessPage } from '@/components/organisms/NoAccessPage/NoAccessPage';
import { SectionNav } from '@/components/organisms/SectionNav/SectionNav';
import { useVisibleAreas } from '@/hooks/useVisibleAreas';

export function AreaLayout({ areaKey }: { areaKey: string }) {
  const { areas, ready } = useVisibleAreas();
  if (!ready) return <PageSkeleton />;               // before ['me'] nothing is permitted: never flash no-access

  const area = areas.find(({ key }) => key === areaKey);
  if (!area) return <NoAccessPage />;                // a feature reached by URL, not a missing record

  return (
    <div className="flex flex-col gap-6">
      {area.sections.length > 1 && <SectionNav label={`${area.label}.sections`} sections={area.sections} />}
      <Suspense fallback={<PageSkeleton />}>
        <Outlet />
      </Suspense>
    </div>
  );
}
```

```tsx
// src/components/organisms/SectionNav/SectionNav.tsx — excerpt: the Vite copy differs only in its router imports
import { Link, useLocation } from 'react-router';
import { areaState, type Section } from '@/lib/nav';

const { pathname } = useLocation();
<Link to={section.href} aria-current={areaState(pathname, section)}>{t(section.label)}</Link>   // per section
```

- **`SectionNav` is one organism across both web stacks** — the labelled `nav`, `aria-current` from
  `areaState` (`page` on the section's URL, `true` inside it, whole segments only), two visual cues
  and 44px-tall targets → `@skills/std-nextjs/references/navigation.md`. The Vite copy swaps
  `next/link` and `usePathname()` for React Router's `Link` and `useLocation()`.
- **`AppSidebar`** is the areas-only organism in
  `@skills/std-shadcn-ui/references/components-and-blocks.md`, marking its area with the same
  `areaState` and linking through `render={<Link to={area.href} />}` on Base UI or `asChild` on Radix.
- Where focus lands on a level change — the new `h1`, or the control that changed a filter →
  `@skills/ui-ux-patterns/references/drill-down-navigation.md`.

```ts
// src/router/loaders.ts — excerpt: the list URL is validated, remembered and warmed
export async function orderListLoader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url);
  const parsed = orderListState.safeParse(Object.fromEntries(url.searchParams));
  if (!parsed.success) throw redirect(url.pathname);   // a stale or tampered URL falls back to the plain list
  rememberListState(url.pathname, url.search);         // what the list crumb returns to
  void queryClient
    .query({ queryKey: orderKeys.list(parsed.data), queryFn: () => fetchOrders(parsed.data), staleTime: 30_000 })
    .catch(() => {});                                  // warm, never block the navigation
  return null;
}
```

```ts
// src/lib/list-state.ts — the list crumb reopens a list the way this session last left it
const storageKey = (pathname: string) => `list-state:${pathname}`;

export function rememberListState(pathname: string, search: string) {
  sessionStorage.setItem(storageKey(pathname), search);
}

export function listHref(pathname: string) {
  return pathname + (sessionStorage.getItem(storageKey(pathname)) ?? '');
}
```

```tsx
// src/pages/orders/OrderList.tsx — excerpt
const [params, setParams] = useSearchParams();
const state = orderListState.parse(Object.fromEntries(params));   // the loader already validated it
const { data, isPending } = useOrders(state);

const showStatus = (status: OrderStatus) =>
  setParams((next) => { next.set('status', status); return next; });            // pushes: Back undoes the filter
const typeQuery = (q: string) =>
  setParams((next) => { next.set('q', q); return next; }, { replace: true });   // replaces while typing
```

- **One `setParams` call per change.** The function form does not queue like React's `setState`:
  "Multiple calls to `setSearchParams` in the same tick will not build on the prior value" (React
  Router docs — useSearchParams). **Commit the query with a push** (Enter, or leaving the field), so
  Back returns to the list as it was before the search.

```tsx
// src/pages/orders/ShipmentDetail.tsx — excerpt: the trail is hierarchy; only the list crumb remembers
const trail = [
  { label: t('nav.orders'), href: listHref('/orders') },
  ...shipment.ancestors.map((ancestor) => ({ label: ancestor.name, href: hrefFor(ancestor) })), // server-filtered
  { label: shipment.name },                                                                    // the current page: plain text
];
```

- `hrefFor` maps an ancestor's type to its canonical, flat URL. An ancestor the caller cannot read
  never arrives, so the trail renders exactly what it receives; its markup — a labelled `nav`, an
  `ol`, `aria-current="page"` last — is the `std-accessibility` skill's.
- Rendering this tree per role in a test → `@skills/std-testing/references/react-components.md`.

---

## Decision: this chunk is too big — what do I split?

Split at two seams: **routes** (already done via `lazy`) and **heavy leaf dependencies** used on
only some pages — `chart.js` with `react-chartjs-2`, rich-text editors, PDF viewers, map SDKs. Read
their sizes off the build output instead of carrying a remembered number — rule 4's unit problem
applies to every figure you did not just measure.

### Bad — a chart module reachable from the entry chunk

```ts
// src/components/index.ts  ❌ a barrel that re-exports a chart module
export { RevenueChart } from './organisms/RevenuePanel/RevenueChart';   // imports @/lib/charts/register → Chart.js
export { OrderTable } from './OrderTable';
```

If `RevenueChart` is imported statically — through a barrel like this one, or by a layout — Chart.js
lands in the entry bundle for every route, the login page included. Importing only the registration
module changes nothing: it imports Chart.js itself.

### Good — lazy the chart module at its call site, not just the page

```tsx
// src/pages/Dashboard.tsx  ✅ the page is lazy, and so is the chart inside it
import { lazy, Suspense, useMemo } from 'react';
import { ChartSkeleton } from '@/components/molecules/ChartSkeleton/ChartSkeleton';
import { useRevenue } from '@/api/revenue';
import { toRevenuePoints } from '@/domain/revenue';

const RevenueChart = lazy(() =>
  import('@/components/organisms/RevenuePanel/RevenueChart').then((m) => ({ default: m.RevenueChart })),
);

export default function Dashboard() {
  const { data } = useRevenue({ range: '30d' });
  const points = useMemo(() => toRevenuePoints(data?.days ?? []), [data]);
  if (!data) return <ChartSkeleton />;

  return (
    <Suspense fallback={<ChartSkeleton />}>
      <RevenueChart points={points} currency={data.currency} />
    </Suspense>
  );
}
```

The page is already a lazy chunk, and the chart is lazied again so the page's own content never
waits on Chart.js: filters and tables paint when the page chunk arrives, and the chart fills its
skeleton when its chunk does. Empty and error states, and the chart's text alternative →
`references/charts.md`. **Never barrel-export heavy components** — import from the concrete path.

---

## Decision: named vendor chunks

Vendor splitting stops the whole `node_modules` tree from invalidating on every app change. This is
**Vite 8**, which bundles with Rolldown: "The object form `output.manualChunks` option is not
supported anymore. The function form `output.manualChunks` is deprecated", and `build.rollupOptions`
is now `build.rolldownOptions` (Vite — Migration from v7). Vendor chunks are `codeSplitting` groups.

```ts
// vite.config.ts — Vite 8
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/ },
            { name: 'vendor-query', test: /node_modules[\\/]@tanstack[\\/](react-query|query-core)[\\/]/ },
            { name: 'vendor-charts', test: /node_modules[\\/](chart\.js|@kurkle[\\/]color|react-chartjs-2)[\\/]/ },
            { name: 'vendor-motion', test: /node_modules[\\/](framer-motion|motion-dom|motion-utils)[\\/]/ },
          ],
        },
      },
    },
    chunkSizeWarningLimit: 300, // KB — matches the initial-JS budget
  },
});
```

- **End every `test` with `[\\/]`.** Without it, `react` also matches `react-chartjs-2`, and the chart
  wrapper joins the chunk every route preloads. `[\\/]` is also Rolldown's advice for Windows paths.
- **A group is a name, not a lazy boundary.** A group captures what its `test` matches *and*, by
  default, those modules' dependencies (`includeDependenciesRecursively`, default `true`) — so
  `@kurkle/color`, Chart.js's one runtime dependency, rides along in `vendor-charts`. A module two
  groups match goes to the higher `priority` (default `0`), then to the group declared first
  (Rolldown — codeSplitting). If the entry imports anything that ended up in `vendor-charts`, the
  entry imports `vendor-charts` — and Chart.js is back in the initial load while every `lazy()`
  still looks correct. After adding a group for a lazy-only library, open `dist/index.html`: it must
  not `modulepreload` that chunk.
- **A package still on Vite 7 keeps `build.rollupOptions.output.manualChunks`** until it upgrades.
  On Vite 8 the object form fails the build; the function form still builds but is deprecated.

Do not over-split: a chunk under ~10KB costs more in request overhead than it saves.

---

## Prefetching on intent

Lazy routes cost a network round-trip on click, and the next level's data costs another. Warm both
when a person shows intent:

```tsx
// src/components/molecules/OrderLink/OrderLink.tsx
import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { useQueryClient } from '@tanstack/react-query';
import { fetchOrder, orderKeys } from '@/api/orders';

export function OrderLink({ orderId, children }: { orderId: string; children: ReactNode }) {
  const queryClient = useQueryClient();
  const warm = () => {
    void import('@/pages/orders/OrderDetail');
    void queryClient
      .query({ queryKey: orderKeys.detail(orderId), queryFn: () => fetchOrder(orderId), staleTime: 30_000 })
      .catch(() => {});                          // a prefetch never surfaces an error
  };
  return <Link to={`/orders/${orderId}`} onMouseEnter={warm} onFocus={warm}>{children}</Link>;
}
```

`onFocus` as well as `onMouseEnter`, so keyboard users get the same head start; touch has no hover,
so a prefetch is a bonus, never a dependency. The `staleTime` is what stops a hover storm from
refetching data that is already fresh (TanStack — Prefetching & Router Integration).

---

## Verifying the budget

```bash
npx vite-bundle-visualizer          # opens a treemap of the built chunks
npm run build -- --sourcemap        # then inspect dist/assets/*.js sizes
```

What to look for, in order:
1. Anything in the **entry chunk** that only one route needs → move behind `lazy`.
2. A **vendor chunk `dist/index.html` preloads** that holds a lazy-only library
   (`vendor-charts`) → a dependency the entry shares was pulled into it; give that dependency a
   group of its own with a higher `priority`, or drop the entry.
3. A **date library** imported wholesale (`import moment from 'moment'`) → replace with
   `date-fns` named imports or `Intl.DateTimeFormat`.
4. **Icon packs** imported as a namespace (`import * as Icons from 'lucide-react'`) → import the
   two icons you use by name.
5. **Duplicated vendor copies** — usually two versions of the same transitive dep; dedupe in
   `resolve.dedupe`. A second `chart.js` copy also brings its own component registry
   (`references/charts.md`).

---

## Sources

- React Router docs — Upgrading from v7 — https://reactrouter.com/upgrading/v7
- React Router docs — Installation (Data mode) — https://reactrouter.com/start/data/installation
- React Router docs — Routing (Declarative mode) — https://reactrouter.com/start/declarative/routing
- React Router docs — Error Boundaries — https://reactrouter.com/how-to/error-boundary
- React Router docs — ScrollRestoration — https://reactrouter.com/api/components/ScrollRestoration
- React Router docs — useSearchParams — https://reactrouter.com/api/hooks/useSearchParams
- React docs — useContext — https://react.dev/reference/react/useContext
- TanStack — Prefetching & Router Integration — https://tanstack.com/query/latest/docs/framework/react/guides/prefetching
- Nielsen Norman Group — Designing Scroll Behavior: When to Save a User's Place — https://www.nngroup.com/articles/saving-scroll-position/
- Baymard Institute — Return Users to the Same Place in the Product List When Returning from the Product Page — https://baymard.com/blog/return-same-place
- Baymard Institute — 4 Design Patterns That Violate "Back" Button UX Expectations — https://baymard.com/blog/back-button-expectations
- Vite — Migration from v7 — https://vite.dev/guide/migration
- Rolldown — codeSplitting — https://rolldown.rs/reference/OutputOptions.codeSplitting
