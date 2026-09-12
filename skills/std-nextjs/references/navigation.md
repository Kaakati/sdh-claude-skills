# Navigation — Drill-down in the App Router

How a Next.js package builds the house drill-down model: area → overview → list → detail →
sub-detail, the global sidebar holding areas only, every level with a URL and its location cues.

**Owned elsewhere — do not duplicate:** the rules (areas and their budget, levels, location cues, Up
and Back, the palette, anti-patterns) → @skills/ui-ux-patterns/references/drill-down-navigation.md ·
the API contract (levels → endpoints, flat member URLs, `ancestors`, list parameters, search, 404 for
out-of-scope records) → @skills/std-api-design/references/drill-down-resources.md · `NAV`,
`visibleNav`, `areaState` and the `/me` fixtures → @skills/access-control-designer/references/ui-gates.md ·
the areas-only `AppSidebar` and the command palette → @skills/std-shadcn-ui/references/components-and-blocks.md ·
ARIA → the `std-accessibility` skill · revalidating a level → `references/caching.md`.

Load-bearing rules restated (this file is read standalone):

1. **One route group per area.** A group adds no URL segment, so an area's flat member routes
   (`/shipments/[shipmentId]`, listed in the area's `match`) still render inside it.
2. **Filter before building.** The app layout runs `visibleNav` on the server; `AppSidebar` renders
   **areas only**, never `SidebarMenuSub`. A role with one area gets no sidebar.
3. **Sections render in the area layout**, from a client leaf that reads `usePathname()`.
4. **List state lives in `searchParams`** — the API's list parameters. Applying a filter pushes a
   history entry; typing in a search box replaces it.
5. **A triage list may open its detail as a panel** (a parallel slot plus an intercepting route);
   the canonical URL still renders the full page on a hard load, and the slot's own `page.tsx`
   returns `null`, so a soft navigation back to the list closes the panel.
6. **Breadcrumbs come from the detail's `ancestors`**, from level 3 — never history, never URL
   segments. The list crumb carries the list's last query string.
7. **A level change moves focus to the new `h1`**; a same-view update leaves focus where it was.
8. **Structure is tested per role, on the rendered layout** — each role sees a filtered subset.

---

## The route tree

```text
app/
├── error.tsx                                   # catches the (app) layout, which builds the ability
└── (app)/
    ├── layout.tsx                              # visibleNav → AppSidebar (areas) + AppHeader (search, palette) + RouteFocus
    ├── (orders)/                               # the Orders area: one collection, so no section nav
    │   ├── layout.tsx                          # the area's title template
    │   ├── orders/page.tsx                     # L3 list — state in searchParams
    │   ├── orders/loading.tsx                  # renders the list's h1, so focus has a target while streaming
    │   ├── orders/[orderId]/layout.tsx         # L4: breadcrumb, h1, navigation tabs
    │   ├── orders/[orderId]/shipments/page.tsx # a tab — same level, its own URL
    │   └── shipments/[shipmentId]/page.tsx     # L5 — flat URL; NAV's match marks Orders current
    ├── (organization)/                         # an area with sections
    │   ├── layout.tsx                          # area layout: title template + SectionNav (Members · Billing)
    │   ├── members/page.tsx
    │   └── billing/page.tsx                    # gates itself (ui-gates.md)
    └── (invoices)/invoices/                    # a triage area: list-detail
        ├── layout.tsx                          # {children} beside {detail}
        ├── page.tsx                            # L3 triage list
        ├── @detail/default.tsx                 # returns null: a hard load renders no panel
        ├── @detail/page.tsx                    # returns null: a soft navigation to /invoices (Close, a filter) closes the panel
        ├── @detail/(.)[invoiceId]/page.tsx     # opened from the list: the detail as a panel
        └── [invoiceId]/page.tsx                # L4 full page: hard load, shared link, "Open full page"
```

Folders map to URL segments and layouts nest with the folder tree (Next.js docs — Layouts and
Pages). A record has one home area and one route: a Dashboard tile or a customer's Orders tab links
to `/orders/[orderId]`, never to a second nested copy.

---

## Decision: the app layout — filter, then build the chrome

```tsx
// app/(app)/layout.tsx — Server Component
import type { ReactNode } from 'react';
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar';
import { AppHeader } from '@/components/organisms/AppHeader';
import { AppSidebar } from '@/components/organisms/AppSidebar';
import { RouteFocus } from '@/components/organisms/RouteFocus';
import { AbilityProvider } from '@/components/providers/AbilityProvider';
import { requireSession } from '@/lib/auth';
import { getAbility } from '@/lib/ability.server';
import { NAV, visibleNav } from '@/lib/nav';

export default async function AppShellLayout({ children }: { children: ReactNode }) {
  const session = await requireSession(); // cache()-memoized: one /me call per request
  const areas = visibleNav(NAV, await getAbility(), session.entitlements); // denied areas never reach the RSC payload

  return (
    <AbilityProvider rules={session.permissions.rules}>
      <SidebarProvider defaultOpen>
        {areas.length > 1 && <AppSidebar areas={areas} />}
        <SidebarInset>
          <AppHeader areas={areas} showSidebarTrigger={areas.length > 1} />
          <RouteFocus />
          {children}
        </SidebarInset>
      </SidebarProvider>
    </AbilityProvider>
  );
}
```

- **Never a section tree in `AppSidebar`.** `SidebarMenuSub` under each area rebuilds the mega
  sidebar the house bans: the chrome grows with the product instead of staying at the area budget.
  It marks the active area with `areaState(pathname, area)` — whole segments plus the area's `match`
  prefixes, never a bare `startsWith`.
- **`defaultOpen`:** the desktop nav ships visible; the person may collapse it, and the
  `sidebar_state` cookie the primitive writes may carry that choice.
- **`AppHeader`** holds the global search and the palette trigger, fed the same `areas`.

---

## Decision: the area layout — sections stay visible inside their area

```tsx
// app/(app)/(organization)/layout.tsx
export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations();
  const suffix = `${t('nav.organization')} · ${t('app.name')}`;
  return { title: { template: `%s · ${suffix}`, default: suffix } }; // most specific first; pages title their own segment
}

export default async function OrganizationAreaLayout({ children }: { children: ReactNode }) {
  const session = await requireSession();
  const area = visibleNav(NAV, await getAbility(), session.entitlements).find(({ key }) => key === 'organization');
  if (!area) return <NoAccessPage feature="nav.organization" />; // a feature reached by URL — not notFound()

  return (
    <div className="flex flex-col gap-6 p-6">
      {area.sections.length > 1 && <SectionNav label="nav.organization.sections" sections={area.sections} />}
      {children}
    </div>
  );
}
```

```tsx
// src/components/organisms/SectionNav/SectionNav.tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { areaState, type Section } from '@/lib/nav';

const tab = 'inline-flex min-h-11 items-center border-b-2 border-transparent text-sm text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

export function SectionNav({ label, sections }: { label: string; sections: Section[] }) {
  const pathname = usePathname(); // the layout above does not rerender on navigation; this leaf does
  const t = useTranslations();
  return (
    <nav aria-label={t(label)} data-keep-focus>
      <ul className="flex gap-6 border-b border-border">
        {sections.map((section) => {
          const current = areaState(pathname, section); // 'page' on its URL, 'true' inside it — whole segments
          return (
            <li key={section.key}>
              <Link href={section.href} aria-current={current}
                className={cn(tab, current && 'border-primary font-semibold text-foreground')}>{t(section.label)}</Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

- **Why a client leaf:** "On navigation, layouts preserve state, remain interactive, and do not
  rerender" (Next.js docs — Layouts and Pages). A current state computed in the layout goes stale on
  the first click.
- **`aria-current` comes from `areaState`**, the helper the sidebar uses: `page` on the section's
  own URL, `true` on a page inside it, whole segments only. The selected tab carries two cues — the
  border and the weight — never colour alone.
- **Placement by section count** (tabs in the area header, a local list, or an overview) and one
  placement per product → the drill-down rules. An area with one permitted section renders no
  section nav.

---

## Decision: list state lives in `searchParams`

```tsx
// app/(app)/(orders)/orders/page.tsx — L3, excerpt
export default async function OrdersPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const parsed = orderListState.safeParse(await searchParams); // zod: status, sort, q — the API's list parameters
  const state = parsed.success ? parsed.data : orderListState.parse({}); // a stale or tampered URL falls back
  const orders = await listOrders(state);
  return <OrdersView state={state} orders={orders.data} />; // h1 (tabIndex={-1}), OrderFilters, OrderList
}
```

```tsx
// src/components/organisms/OrderFilters/OrderFilters.tsx — 'use client', excerpt
useEffect(() => { rememberListState(pathname, searchParams.toString()); }, [pathname, searchParams]); // the crumb returns here

function apply(changes: Record<string, string | null>, mode: 'push' | 'replace' = 'push') {
  const next = new URLSearchParams(searchParams);
  Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
  router[mode](next.size ? `${pathname}?${next}` : pathname, { scroll: false }); // push: Back undoes a filter
}
```

```ts
// src/lib/list-state.ts — this tab's last query string per list path
const storageKey = (path: string) => `list-state:${path}`;
export function rememberListState(path: string, query: string): boolean {
  try { sessionStorage.setItem(storageKey(path), query ? `?${query}` : ''); return true; } catch { return false; }
}
export function readListState(path: string): string | null {
  try { return sessionStorage.getItem(storageKey(path)); } catch { return null; }
}
```

- **The URL parameters are the API's list parameters, one-to-one**, so a shared or restored URL
  replays the same request. A cursor never goes in the URL — it is valid only with the parameters
  that produced it. The pagination contract → @skills/std-api-design/references/pagination-clients.md.
- **Push, never replace, when a filter is applied.** A replaced entry makes Back leave the list.
- **The list shows its active filters with a Clear action**, so a filter restored through the crumb
  is never a surprise.

---

## Decision: list-detail with a parallel slot and an intercepting route

"Parallel Routes can be used together with Intercepting Routes to create modals that support deep
linking" (Next.js docs — Parallel Routes). A side panel is the same mechanism.

```tsx
// app/(app)/(invoices)/invoices/layout.tsx — after a soft navigation, the panel sits beside the list
export default function InvoicesListLayout({ children, detail }: { children: ReactNode; detail: ReactNode }) {
  return <div className="flex gap-6"><div className="min-w-0 flex-1">{children}</div>{detail}</div>;
}
```

```tsx
// app/(app)/(invoices)/invoices/@detail/(.)[invoiceId]/page.tsx — a row opened from the list
export default async function InvoicePanelPage({ params }: { params: Promise<{ invoiceId: string }> }) {
  const { invoiceId } = await params;
  const invoice = await getInvoice(invoiceId); // null on the API's 404: outside the caller's scope
  if (!invoice) notFound();
  return <InvoicePanel invoice={invoice} />; // a non-modal region: h2, "Open full page", Close
}
```

```tsx
// app/(app)/(invoices)/invoices/@detail/page.tsx — default.tsx has the same body
export default function NoPanel() {
  return null; // /invoices matches the slot: a soft navigation back to the list closes the panel
}
```

- **Back closes the panel and Forward reopens it; a refresh or a shared link renders
  `[invoiceId]/page.tsx` as a full page**, with the slot on `default.tsx`, which returns `null`
  (Next.js docs — Parallel Routes).
- **A soft navigation needs `@detail/page.tsx` as well.** Next.js keeps a slot's active subpage on a
  soft navigation "even if they don't match the current URL", so without a slot page for `/invoices`
  the Close link, a filter push and the area's sidebar link all leave the panel open: "client-side
  navigations to a route that no longer match the slot will remain visible, we need to match the
  slot to a route that returns `null`" (Next.js docs — Parallel Routes). `default.tsx` covers hard
  loads, `page.tsx` soft ones. A segment with child routes besides `[invoiceId]` also adds
  `@detail/[...catchAll]/page.tsx`, returning `null`.
- **"Open full page" is a plain `<a href>`** to the canonical URL, because a soft navigation to the
  same URL is intercepted again — the one sanctioned exception to the `next/link` rule, with a
  comment saying so. **Close** is a `Link` to the list URL with its remembered query string.
- **At compact widths the panel covers the list** — one pane at a time.
- **A role-conditional slot is not authorization:** both slots render on the server regardless of
  which one the layout returns (Next.js docs — Parallel Routes). The panel authorizes through the API.

---

## Decision: the breadcrumb from `ancestors`

```tsx
// src/components/organisms/RecordBreadcrumb/RecordBreadcrumb.tsx — Server Component, Base UI package
export async function RecordBreadcrumb({ root, ancestors, current }: RecordBreadcrumbProps) {
  const t = await getTranslations();
  const rootCrumb = <ListCrumbLink href={root.href}>{t(root.label)}</ListCrumbLink>;
  const crumb = (node: Ancestor) => <BreadcrumbLink render={<Link href={recordHref(node)} />}>{node.name}</BreadcrumbLink>;
  const parent = ancestors.at(-1); // ancestors: { type, id, name }, root → parent, permission-filtered

  return (
    <Breadcrumb aria-label={t('breadcrumb.label')}>
      <BreadcrumbList className="hidden md:flex">
        <BreadcrumbItem>{rootCrumb}</BreadcrumbItem>
        {ancestors.map((node) => (
          <Fragment key={node.id}><BreadcrumbSeparator /><BreadcrumbItem>{crumb(node)}</BreadcrumbItem></Fragment>
        ))}
        <BreadcrumbSeparator />
        <BreadcrumbItem><BreadcrumbPage>{current}</BreadcrumbPage></BreadcrumbItem>
      </BreadcrumbList>
      <BreadcrumbList className="md:hidden">
        <BreadcrumbItem>{parent ? crumb(parent) : rootCrumb}</BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  );
}
```

```tsx
// src/components/organisms/RecordBreadcrumb/ListCrumbLink.tsx — the list crumb returns to the list as it was left
'use client';

const noSubscription = () => () => {};

export function ListCrumbLink({ href, children }: { href: string; children: ReactNode }) {
  // Server snapshot: the plain list URL. Client snapshot: plus this tab's last query string.
  const query = useSyncExternalStore(noSubscription, () => readListState(href) ?? '', () => '');
  return <BreadcrumbLink render={<Link href={`${href}${query}`} />}>{children}</BreadcrumbLink>;
}
```

- **The record's layout renders it:** `orders/[orderId]/layout.tsx` awaits the order (deduped with
  the page's read), calls `notFound()` on the API's 404, and renders `RecordBreadcrumb`, the `h1` and
  the navigation tabs above `children`.
- **An ancestor the caller cannot read never arrives** — render what the API sends. Radix packages
  write `<BreadcrumbLink asChild><Link …/></BreadcrumbLink>`.
- **Two stock details in both registries:** `Breadcrumb` defaults to `aria-label="breadcrumb"`
  (English; the caller's `aria-label` wins because props spread after it), and `BreadcrumbPage`
  renders a `span` with `role="link"` and `aria-disabled` — the house edit makes it plain text with
  `aria-current="page"` → @skills/std-shadcn-ui/references/accessibility-and-i18n.md.
- **A wide trail past four items** keeps the first link and the last two, with `BreadcrumbEllipsis`
  (its `label` prop from `t()`) standing in for the middle.

---

## Decision: focus on drill-in, Up and Back

Next.js ships a route announcer for client-side transitions: it announces `document.title` first,
then the `h1`, then the pathname (Next.js docs — Accessibility), so the area title template is what
people hear. Announcing is not focus: single-page apps must also "ensure that the focus is placed
appropriately when new screens are generated" (W3C WAI Curricula — Module 7: Rich Applications).

```tsx
// src/components/organisms/RouteFocus/RouteFocus.tsx — 'use client', mounted once in the app layout
export function RouteFocus() {
  const pathname = usePathname(); // a query-string change (filter, sort) leaves it unchanged: focus stays put
  const previous = useRef<string | null>(null);

  useEffect(() => {
    const firstRender = previous.current === null;
    const unchanged = previous.current === pathname;
    previous.current = pathname;
    if (firstRender || unchanged) return; // a full page load keeps the browser's own behaviour
    if (document.activeElement?.closest('[data-keep-focus]')) return; // section tabs keep focus
    const target = document.querySelector<HTMLElement>('[data-panel] h2') ?? document.querySelector<HTMLElement>('main h1');
    target?.focus(); // both headings carry tabIndex={-1}
  }, [pathname]);

  return null;
}
```

- **Verify on the pinned version first.** Keep this leaf only if, without it, focus stays on a link
  that left the DOM or falls to `body` after a soft navigation.
- **Back to a list** focuses the row link that drilled in when it is still there, otherwise the
  list's `h1`. A sticky header never covers the focused heading — `scroll-mt-*` (WCAG 2.4.11).
- **A palette selection** is a level change like any other: the dialog closes, the route changes,
  and this leaf moves focus to the new `h1`.

---

## Testing — the rendered nav, per role

A static check cannot see what a role sees; the rendered layout can. The fixtures and the per-role
table → @skills/access-control-designer/references/ui-gates.md; the Server Component idiom →
@skills/std-testing/references/nextjs-server.md.

```tsx
// app/(app)/layout.test.tsx
vi.mock('@/lib/auth');
vi.mock('@/lib/ability.server');
vi.mock('next/navigation', () => ({ usePathname: () => '/orders', useRouter: () => ({ push: vi.fn() }) }));

const AREA_BUDGET = 7; // this project's areas-per-role budget

describe.each(Object.entries(meByRole))('AppShellLayout for %s', (role, me) => {
  it(`should list areas only, within the budget, when the caller is ${role}`, async () => {
    // Arrange
    vi.mocked(requireSession).mockResolvedValue(me);
    vi.mocked(getAbility).mockResolvedValue(buildAbility(me.permissions.rules));
    // Act
    renderWithProviders(await AppShellLayout({ children: <main /> })); // NextIntlClientProvider + the package's providers
    // Assert
    const nav = screen.queryByRole('navigation', { name: /main/i });
    expect(nav?.querySelector('ul ul') ?? null).toBeNull(); // nothing nested under an area
    expect(nav ? within(nav).getAllByRole('link').length : 0).toBeLessThanOrEqual(AREA_BUDGET);
  });
});
```

- The sidebar's mobile check reads `window.matchMedia`, which jsdom lacks — stub it in the setup file.
- **Add:** a one-area role renders no main nav; the area layout renders its sections and the app
  layout does not; a detail's breadcrumb matches the fixture's `ancestors`.
- **Back, Up and focus run in a browser:** at every level, drill in (focus on the `h1`), apply a
  filter (focus stays; Back undoes it), open a record and press Back (the list returns with its
  query and scroll).
- **The list-detail panel closes on a soft navigation:** open a row and press Close — the panel is
  gone and focus is on the list's `h1`. Reopen a row and apply a filter, then reopen one and use the
  area's sidebar link — the panel is gone each time.

---

## Sources

- Next.js docs — Layouts and Pages — https://nextjs.org/docs/app/getting-started/layouts-and-pages
- Next.js docs — Parallel Routes — https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes
- Next.js docs — Accessibility — https://nextjs.org/docs/architecture/accessibility
- W3C WAI Curricula — Module 7: Rich Applications — https://www.w3.org/WAI/curricula/developer-modules/rich-applications/
