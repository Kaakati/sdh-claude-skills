# Components and Blocks — The Catalog, the Two Bases, the Sidebar, the Palette, Adopting a Block

Load-bearing rules restated (hold even if you read nothing else):

1. **Primitives are atoms and stay where the CLI wrote them** — `aliases.ui`, kebab-case — even
   `dialog` and `sidebar`, which import `Button`. House compositions around them follow the atomic
   ladder, PascalCase.
2. **The installed file is the truth.** `'use client'`, props, strings and classes differ by base
   and by style. Read what `add` wrote, not what another project's copy looks like.
3. **Base UI composes with `render`, Radix with `asChild`.** A link styled as a button is the link
   element with `buttonVariants()`, in both.
4. **Never mix bases in one package.** `add --dry-run` lists the dependencies; an item that pulls
   the other base's headless package is a stop-and-ask.
5. **A block becomes house code the moment it is adopted** — copy into message files, demo data
   deleted, nav filtered by permission key and cut to areas only, palette classes to tokens, charts
   on the `chart` component (Next.js), files moved onto the atomic ladder — and it is never re-added.
6. **The global `AppSidebar` lists areas only.** Static group labels are allowed; `SidebarMenuSub`
   and collapsible groups are not. The active area comes from `areaState`, never a bare `startsWith`.
7. **The command palette is one organism, fed by `visibleNav` and the search endpoint.** A visible
   button opens it as well as Cmd/Ctrl+K, and nothing is reachable only through it.

---

## The catalog, by the level of the house component around it

Every item installs at `aliases.ui`. The level names where the **house** composition that uses it
lives (the `atomic-design` skill) — never a reason to move the primitive.

| House level | Items | Notes |
|---|---|---|
| **Atoms** — used directly | `button`, `input`, `textarea`, `label`, `checkbox`, `radio-group`, `switch`, `slider`, `toggle`, `select`, `native-select`, `badge`, `avatar`, `separator`, `skeleton`, `spinner`, `kbd`, `progress`, `aspect-ratio`, `scroll-area`, `tooltip` | `spinner` names itself `Loading` — a label prop |
| **Composites** — house molecules and organisms assemble them | `field`, `input-group`, `input-otp`, `button-group`, `toggle-group`, `item`, `alert`, `card`, `empty`, `breadcrumb`, `pagination`, `tabs`, `accordion`, `collapsible`, `popover`, `hover-card`, `dropdown-menu`, `context-menu`, `menubar`, `navigation-menu`, `command` (cmdk), `combobox`, `calendar` (react-day-picker + date-fns), `carousel` (embla), `table`, `resizable`, `dialog`, `alert-dialog`, `sheet`, `drawer` | A date picker is a docs composition (`popover` + `calendar`), not an item. `breadcrumb` items come from the API's `ancestors`, and the trail's `aria-label` from `t()` |
| **Organism scaffolds** — a house organism owns them, with their data | `sidebar`, `chart` (Recharts v3, Next.js packages), `toast` (Base UI) or `sonner` (Radix), the chat set (`message`, `message-scroller`, `bubble`, `attachment`, `marker`), `questionnaire` | `message-scroller` and `questionnaire` depend on `@shadcn/react`; the data table is a guide, not an item (below) |
| **Providers** | `direction` (`DirectionProvider`) | → @skills/std-shadcn-ui/references/accessibility-and-i18n.md |
| **Never add** | `form` — the legacy react-hook-form wrapper: no docs page, and its base-nova item has no files | `field` → @skills/std-shadcn-ui/references/forms-and-feedback.md |

`typography` is docs examples only and ships no styles.

### Which items exist for which base

Read `--dry-run` before believing any of this — the registry changes month to month.

- **`toast` is Base UI only.** The Radix docs mark the old toast deprecated in favor of `sonner`,
  and the Base UI docs have no `sonner` page.
- **`questionnaire`** is in the base-nova registry, not new-york-v4.
- **React Aria** has no `menubar` or `navigation-menu` docs page.
- **`drawer`** is `vaul` on Radix and `@base-ui/react` on base-nova.
- **The new-york-v4 `combobox` depends on `@base-ui/react`.** In a Radix package that is the second
  base: ask, or compose `command` inside `popover`.
- **`command` is `cmdk` in both registries, and `CommandDialog` differs.** new-york-v4's wraps its
  children in `Command` — so `Command`'s own props (`label`, `shouldFilter`) have no way in — and
  shows the dialog's close button by default. base-nova's renders its children straight into
  `DialogContent`, so the caller renders `Command`, and hides the close button by default. Both
  render a visually hidden title and description that default to English (`Command Palette`,
  `Search for a command to run...`).
- **`chart-*` blocks exist only in the new-york-v4 (Radix) registry.** A Base UI package composes
  from the `chart` component, which is Recharts and base-agnostic. Neither concerns a Vite SPA,
  whose charts are Chart.js (@skills/std-reactjs/references/charts.md).
- **`'use client'`:** 41 of the 61 new-york-v4 primitives carry it. The 20 that do not — `alert`,
  `attachment`, `badge`, `breadcrumb`, `bubble`, `button`, `button-group`, `card`, `empty`, `input`,
  `item`, `kbd`, `marker`, `message`, `native-select`, `navigation-menu`, `pagination`, `skeleton`,
  `spinner`, `textarea` — render in Server Components. base-nova differs: `accordion`,
  `aspect-ratio` and `slider` have no directive, `questionnaire` and `toast` do.

---

## Base UI vs Radix — the differences that bite

| Concern | Base UI (`base-*`) | Radix (`radix-*`, `new-york`, `default`) |
|---|---|---|
| Headless package | `@base-ui/react/<part>` | `radix-ui` — unified since 2026-02-02; `migrate radix` moves `@radix-ui/react-*` imports |
| Render as another element | `render={<Link href="/orders" />}` | `asChild` plus exactly one child element |
| Trigger styled as a button | `<DialogTrigger render={<Button variant="outline" />}>` | `<DialogTrigger asChild><Button variant="outline">` |
| Link styled as a button | `<Link className={buttonVariants()}>`. Never `<Button render={<a />} nativeButton={false}>`: Base UI's `Button` always sets `role="button"`, overriding the link role | `<Link className={buttonVariants()}>` — the house pattern in both bases — or `<Button asChild><Link>` |
| Sidebar nav item | `<SidebarMenuButton render={<Link href={href} />}>` | `<SidebarMenuButton asChild><Link href={href}>` |
| Breadcrumb link | `<BreadcrumbLink render={<Link href={href} />}>` | `<BreadcrumbLink asChild><Link href={href}>` |
| Command palette | `<CommandDialog …><Command label shouldFilter>…</Command></CommandDialog>` | `CommandDialog` renders `Command` itself: when `Command` needs props, compose `Dialog` + `DialogContent` + a visually hidden `DialogTitle` + `Command` |
| `AlertDialogAction` | A plain `Button` (takes `variant`) — it does **not** close the dialog | Radix `Action` inside a `Button` (takes `variant`) — it **closes** on click |
| `AlertDialogCancel` | Base UI `Close` rendered as an outline `Button` | Radix `Cancel` inside an outline `Button` |
| Toasts | The `toast` item is Base UI's toast manager: `toast.add({ title, type, priority, timeout })`, `toast.promise`; `<Toaster />` from `@/components/ui/toast` | `sonner`: `toast.success()`, `toast.error()` imported from `sonner`; `<Toaster />` from `@/components/ui/sonner`, which reads `next-themes` |
| Blocked control that must stay focusable | `disabled` plus `focusableWhenDisabled` on `Button` — it renders `aria-disabled="true"` and no `disabled` attribute, so it stays in the tab order | `aria-disabled` plus a no-op handler — native `disabled` leaves the tab order |
| `DirectionProvider` | Base UI's own, re-exported; prop `direction` | A wrapper over Radix `Direction`; accepts `direction` or `dir` — pass `direction` in both |
| State styling | `data-open:`, `data-closed:` variants from `shadcn/tailwind.css` | `data-[state=open]:` attribute variants (new-york-v4 source) |
| Overlay, stock | `bg-black/10` with a backdrop blur | `bg-black/50` |
| Destructive button, stock | A tint: `bg-destructive/10 text-destructive` | Solid: `bg-destructive text-white` |
| Focus ring, stock | `focus-visible:ring-3 focus-visible:ring-ring/50` | `focus-visible:ring-[3px] focus-visible:ring-ring/50` |
| RTL rewrite at install | Yes — `base-nova` and the other new styles | `radix-nova` and the other new styles: yes; `new-york`, `default`: no |
| Moving to the other base | — | shadcn ships Radix → Base UI as an agent skill, not a codemod; the house does not migrate |

### The sanctioned local edits to stock classes

Alias token names (`bg-destructive`, `text-sidebar-foreground`) compile as shipped — leave them.
Palette classes are not tokens, so they are the one class-level edit:

| Stock | Where | House replacement |
|---|---|---|
| `text-white` on a solid destructive | new-york-v4 `button`, `badge` | `text-destructive-foreground` |
| `bg-black/50`, `bg-black/10` | Overlays: `dialog`, `sheet`, `alert-dialog`, `drawer` | `bg-background/80` — follows the theme in both modes |
| `bg-white` | new-york-v4 `slider` thumb | `bg-background` |
| `ring-ring/50`, `ring-destructive/20` | Focus rings | Full opacity → @skills/std-shadcn-ui/references/accessibility-and-i18n.md |

Stock variant and size names (`default`, `link`, `icon-sm`) stay as shipped inside a shadcn package:
every block and every `--diff` depends on them. The `std-design-system` axis names govern the
components the house writes from scratch. One non-class edit is sanctioned too: `BreadcrumbPage`
loses its `role="link"` and `aria-disabled` (@skills/std-shadcn-ui/references/accessibility-and-i18n.md).

---

## The global sidebar — areas only

```tsx
// src/components/organisms/AppSidebar/AppSidebar.tsx — Next.js, Base UI package
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  Sidebar, SidebarContent, SidebarGroup, SidebarMenu, SidebarMenuBadge, SidebarMenuButton, SidebarMenuItem,
} from '@/components/ui/sidebar';
import { areaState, type VisibleArea } from '@/lib/nav';

export function AppSidebar({ areas }: { areas: VisibleArea[] }) { // filtered in the layout: denied areas never arrive
  const t = useTranslations();
  const pathname = usePathname();
  return (
    <Sidebar mobileTitle={t('nav.title')} mobileDescription={t('nav.description')}>
      <SidebarContent>
        <nav aria-label={t('nav.main')}>
          <SidebarGroup>
            <SidebarMenu>
              {areas.map((area) => {
                const state = areaState(pathname, area); // whole segments + the area's match prefixes
                return (
                  <SidebarMenuItem key={area.key}>
                    <SidebarMenuButton render={<Link href={area.href} aria-current={state} />} isActive={Boolean(state)}>
                      {t(area.label)}
                    </SidebarMenuButton>
                    {area.locked && <SidebarMenuBadge>{t('plans.locked')}</SidebarMenuBadge>}
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroup>
        </nav>
      </SidebarContent>
    </Sidebar>
  );
}
```

- **Never in the global sidebar:** `SidebarMenuSub` at any depth (the active area included), a
  collapsible group, an area's `sections`, a recursive renderer, contents that swap per area.
  Sections render in the area's own layout — the Next.js `SectionNav` →
  @skills/std-nextjs/references/navigation.md; the Vite SPA's area layout route →
  @skills/std-reactjs/references/routing-and-code-split.md.
- **Group labels come from `area.group`** — when a role sees about six or more areas falling into
  two or three clusters: one `SidebarGroup` per group with a static `SidebarGroupLabel`, never a
  link, never collapsible. A group with one visible area loses its label; an empty one is not rendered.
- **`areaState(pathname, area)`** returns `page` on the area's own URL and `true` anywhere inside it
  — its `href`, its `match` prefixes, its sections' hrefs — by whole path segments: `/orders` stays
  inactive on `/orders-archive`, and a flat member route listed in `match` marks its home area. The
  stock `isActive` styling is the second cue beside `aria-current`.
- **It ships open:** `SidebarProvider defaultOpen`, with the person's collapse remembered in the
  `sidebar_state` cookie. Never `collapsible="icon"` as the shipped state.
- **One visible area → no `AppSidebar`.** That area's section nav is the role's primary nav.
- **Radix:** `<SidebarMenuButton asChild isActive={…}><Link href={area.href} aria-current={…}>{t(area.label)}</Link></SidebarMenuButton>`.
  **Vite:** `useLocation().pathname`, React Router's `<Link to>` and react-i18next's `useTranslation()`;
  `AppLayout` runs `visibleNav` over the ability built from `['me']`.
- `mobileTitle` and `mobileDescription` are house label props replacing the stock `Sidebar` /
  `Displays the mobile sidebar.` strings. The config, `visibleNav` and `areaState` →
  @skills/access-control-designer/references/ui-gates.md; when an area is locked rather than hidden →
  @skills/ui-ux-patterns/references/role-based-ux.md; the rules →
  @skills/ui-ux-patterns/references/drill-down-navigation.md.

---

## The command palette

One organism, optional per product. Its "Go to" entries are the `visibleNav` output, so it offers
only pages the person can open; its records come from the permission-scoped search endpoint, each
shown with its `ancestors` path (@skills/std-api-design/references/drill-down-resources.md). It is an
accelerator: the sidebar, the section nav and the header's search field stay the way in.

```tsx
// src/components/organisms/CommandPalette/CommandPalette.tsx — Next.js, Base UI package
'use client';

import { useDeferredValue, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Kbd } from '@/components/ui/kbd';
import { useRecordSearch } from '@/api/search'; // the search endpoint: hits carry type, id, name, ancestors
import { recordHref } from '@/lib/record-href'; // hit type → its canonical URL
import type { VisibleArea } from '@/lib/nav';

export function CommandPalette({ areas }: { areas: VisibleArea[] }) {
  const t = useTranslations();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const hits = useRecordSearch(useDeferredValue(query.trim())); // disabled below the endpoint's minimum length
  useToggleShortcut(setOpen);

  const needle = query.trim().toLowerCase();
  const destinations = areas // the sidebar's own visibleNav output: areas and their sections, never a second config
    .flatMap((area) => [
      { href: area.href, label: t(area.label) },
      ...area.sections.map((section) => ({ href: section.href, label: `${t(area.label)} › ${t(section.label)}` })),
    ])
    .filter((entry, index, all) => all.findIndex((other) => other.href === entry.href) === index) // a landing is often its first section
    .filter((entry) => entry.label.toLowerCase().includes(needle));
  const go = (href: string) => { setOpen(false); router.push(href); };

  return (
    <>
      <Button variant="outline" onClick={() => setOpen(true)}>{t('palette.open')} <Kbd>{t('palette.shortcut')}</Kbd></Button>
      <CommandDialog open={open} onOpenChange={setOpen} title={t('palette.title')}
        description={t('palette.description')} closeLabel={t('common.close')}>
        <Command label={t('palette.label')} shouldFilter={false}>
          <CommandInput value={query} onValueChange={setQuery} placeholder={t('palette.placeholder')} />
          <CommandList>
            <CommandEmpty>{t('palette.empty')}</CommandEmpty>
            {destinations.length > 0 && (
              <CommandGroup heading={t('palette.goTo')}>
                {destinations.map(({ href, label }) => (
                  <CommandItem key={href} value={href} onSelect={() => go(href)}>{label}</CommandItem>
                ))}
              </CommandGroup>
            )}
            {!!hits.data?.length && (
              <CommandGroup heading={t('palette.records')}>
                {hits.data.map((hit) => (
                  <CommandItem key={`${hit.type}:${hit.id}`} value={`${hit.type}:${hit.id}`} onSelect={() => go(recordHref(hit))}>
                    <span>{hit.name}</span>
                    <span className="text-xs text-muted-foreground">{hit.ancestors.map((node) => node.name).join(' › ')}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  );
}

function useToggleShortcut(setOpen: (update: (open: boolean) => boolean) => void) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'k' || !(event.metaKey || event.ctrlKey)) return;
      event.preventDefault();
      setOpen((open) => !open);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [setOpen]);
}
```

- **Read the installed `command.tsx` first.** The two `CommandDialog` shapes above decide the
  composition: on Radix, compose `Dialog` + `DialogContent` + a visually hidden `DialogTitle` +
  `Command` whenever `Command` needs `label` or `shouldFilter`.
- **`shouldFilter={false}`:** the records are already filtered by the server, and cmdk's own filter
  would hide hits whose `value` does not contain the typed text. The organism filters the "Go to"
  entries itself.
- **An accessible dialog:** the dialog primitive traps focus, closes on Escape and returns focus when
  it closes. `title` and `description` become its visually hidden title and description — required
  label props, never the English defaults — and `closeLabel` threads through to `DialogContent`.
  `label` names cmdk's input; cmdk renders combobox, listbox and option roles with
  `aria-activedescendant` (cmdk — README). Assert in a test that the open dialog is named by the
  translated title, and that focus returns to where it was on Escape.
- **The shortcut is only an accelerator:** Cmd/Ctrl+K with `preventDefault`, the visible button
  always beside it, and never a single-character binding.
- **Selecting is a level change:** `router.push` adds a history entry, the dialog closes, and the
  route's focus leaf moves focus to the new `h1`. Escape closes and returns focus to the opener.
- **Recent** — pages and records opened this session — is its own `CommandGroup`, kept in
  `sessionStorage`; it never reorders the nav. **Actions**, if a product adds them, are only page
  actions also visible on their page, gated by the same permission key.
- **Search:** one query hook over the search endpoint, enabled from the endpoint's minimum query
  length. cmdk's `Command.Loading` is not re-exported by the shadcn file — import it from `cmdk`
  when a pending search needs a progress row.
- **Mounted once, in the app header**, fed the same `areas` the sidebar receives (the Next.js app
  layout → @skills/std-nextjs/references/navigation.md). **Vite:** the same organism under
  `AppLayout`, with `useNavigate()` and react-i18next.
- **A record opens its canonical URL**, so the sidebar's highlight moves to the record's home area.
- The palette's rules — optional per product, never the only route →
  @skills/ui-ux-patterns/references/drill-down-navigation.md.

---

## Blocks

Install with `npx shadcn add login-01 --dry-run`, then `add`. The CLI picks the Radix or Base UI
variant from `components.json` — every login, signup, sidebar and dashboard block exists for both
since 2026-02-06. In a monorepo, primitives land in `packages/ui` and the block's own files in the
app.

| Family | Items | Registry |
|---|---|---|
| Dashboard | `dashboard-01` — sidebar, interactive area chart, section cards, a drag-to-reorder data table | Both bases |
| Sidebar | `sidebar-01` … `sidebar-16` | Both bases |
| Auth | `login-01` … `login-05`, `signup-01` … `signup-05` (`login-01` is a card form on `Field` + `Input`) | Both bases |
| Charts | `chart-area-*` (10), `chart-bar-*` (10), `chart-line-*` (10), `chart-pie-*` (11), `chart-radar-*` (14), `chart-radial-*` (6), `chart-tooltip-*` (9) | new-york-v4 only |
| Previews | `preview`, `preview-02`, `preview-03` | base-nova only |

`dashboard-01` (new-york-v4) writes `app/dashboard/page.tsx`, `app/dashboard/data.json`, and
`app-sidebar`, `chart-area-interactive`, `data-table`, `nav-documents`, `nav-main`,
`nav-secondary`, `nav-user`, `section-cards`, `site-header`. It installs `@dnd-kit/*`,
`@tabler/icons-react`, `@tanstack/react-table` and `zod`, and pulls `chart`, `sidebar`, `table`,
`drawer` and `sonner` among its registry dependencies.

### Adoption — what changes before a block ships

| The block ships | The house changes it to | Why |
|---|---|---|
| Literal copy — `Login to your account`, `Forgot your password?`, `placeholder="m@example.com"` | Message-file keys, placeholders included | `std-i18n`: no user-facing literals, and a placeholder is user-facing |
| Demo data (`app/dashboard/data.json`) | Deleted; Server Components (Next.js) or TanStack Query (Vite) pass data in as props | A component that imports JSON is a demo |
| Hardcoded nav arrays in `app-sidebar`, `nav-main`, `nav-secondary` | The one nav config filtered by `visibleNav`; areas with nothing permitted not rendered; locked areas per plan | Gates check permission keys, never role names |
| Collapsible groups and `SidebarMenuSub` sub-items (`nav-main`, the `sidebar-*` blocks) | Areas only in the global sidebar; sub-items move to the area layout's section nav; no recursive tree | @skills/ui-ux-patterns/references/drill-down-navigation.md |
| `nav-user`'s demo avatar and email | The session from `/me` | Demo identity |
| `href="#"` | Real routes through `next/link` or React Router's `Link` | A dead link fails link-purpose and every navigation test |
| `chart-area-interactive`, `chart-*` blocks | Next.js: the `chart` component on `var(--chart-N)`, data from a Server Component, a server-rendered text alternative, `isAnimationActive={!reduceMotion}`. Vite SPA: deleted — its charts are Chart.js | @skills/std-shadcn-ui/references/charts.md; @skills/std-reactjs/references/charts.md |
| `@tabler/icons-react` in a package whose `iconLibrary` is `lucide` | Imports swapped to the package's icon library | One icon package per app |
| Drag-to-reorder rows (`@dnd-kit`) | Plus a single-pointer alternative: Move up / Move down in the row menu | WCAG 2.5.7 Dragging Movements |
| `sonner` in a Base UI package | `notify()` over the Base UI `toast` | Never mix bases |
| Palette classes | Tokens (table above) | `std-design-system` rule 1 |
| Files at the block's paths, kebab-case | Compositions moved into the atomic directories, PascalCase (`app-sidebar.tsx` → `organisms/AppSidebar/AppSidebar.tsx`); route files stay route files | Primitives stay put; compositions are house code |

After adoption a block is never re-added and never diffed: its files have moved and are ours. Split
an adopted block file that grows past the component line limit; never split a vendored primitive to
satisfy one — splitting `sidebar.tsx` breaks `add --diff` and the registry's dependency resolution.

---

## Data tables — TanStack Table v9

The data table is a guide, not an item: `add table`, plus `@tanstack/react-table` v9. v9 is
feature-based — declare the features once, and type the columns against them.

```tsx
// src/components/organisms/OrdersTable/columns.tsx
'use client';

import { useMemo } from 'react';
import {
  columnVisibilityFeature, createColumnHelper, createPaginatedRowModel, createSortedRowModel,
  rowPaginationFeature, rowSelectionFeature, rowSortingFeature, sortFn_alphanumeric, tableFeatures,
} from '@tanstack/react-table';
import { useTranslation } from 'react-i18next';
import { Checkbox } from '@/components/ui/checkbox';
import type { Order } from '@/types/order';

export const orderTableFeatures = tableFeatures({
  columnVisibilityFeature,
  rowPaginationFeature,
  rowSelectionFeature,
  rowSortingFeature,
  paginatedRowModel: createPaginatedRowModel(),
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric },
});

const columnHelper = createColumnHelper<typeof orderTableFeatures, Order>();

export function useOrderColumns() {
  const { t } = useTranslation();
  return useMemo(() => columnHelper.columns([
    columnHelper.display({
      id: 'select',
      header: ({ table }) => (
        <Checkbox checked={table.getIsAllPageRowsSelected()}
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)} aria-label={t('table.selectAll')} />
      ),
      cell: ({ row }) => (
        <Checkbox checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)} aria-label={t('table.selectRow')} />
      ),
      enableSorting: false,
    }),
    columnHelper.accessor('reference', { header: () => t('orders.reference') }),
    columnHelper.accessor('status', { header: () => t('orders.status'), cell: (info) => t(`orders.statuses.${info.getValue()}`) }),
  ]), [t]);
}
```

The table component renders with `useTable({ features: orderTableFeatures, data, columns })` and
`<table.FlexRender header={header} />` / `<table.FlexRender cell={cell} />` — the names TanStack's
v9 migration guide uses. The guide's header checkbox passes Radix's `checked="indeterminate"`. Base
UI's `checked` is boolean only: the mixed state is its own `indeterminate` prop, rendered as
`aria-checked="mixed"`, and base-nova's `checkbox` spreads its props onto that root — so the header
adds `indeterminate={!table.getIsAllPageRowsSelected() && table.getIsSomePageRowsSelected()}`.
base-nova's indicator draws the same check icon in both states.

- **Next.js:** `page.tsx` stays a Server Component and passes the rows; the columns and table files
  are `'use client'`.
- **Vite:** rows come from `useQuery`. When the API paginates, the table renders the page the API
  returned — the contract is @skills/std-api-design/references/pagination-clients.md.
- **Accessible names from `t()`**: the guide's `Select all` / `Select row` are English.
- **Row actions check the record:** `allows(ability, key, record)` per item, and no menu trigger
  when no item survives (@skills/access-control-designer/references/ui-gates.md).
- **Sortable headers expose the sort** to assistive tech with `aria-sort` on the header cell.
- **The row is the drill-in link** to the record's canonical URL; sort and filter state live in the
  list's URL, not in table state alone (@skills/std-nextjs/references/navigation.md).
- **The same table is a chart's text alternative** — `sr-only`, or behind a visible toggle.

---

## Sources

- shadcn/ui — Command (Base UI and Radix docs) — https://ui.shadcn.com/docs/components/base/command, https://ui.shadcn.com/docs/components/radix/command
- shadcn/ui registry — `command` items (base-nova, new-york-v4) — https://ui.shadcn.com/r/styles/base-nova/command.json, https://ui.shadcn.com/r/styles/new-york-v4/command.json
- cmdk — README — https://github.com/dip/cmdk
