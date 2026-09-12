---
name: std-shadcn-ui
description: "shadcn/ui conventions for Next.js and the ReactJS Vite SPA — components.json, the CLI (docs/view/search, add --dry-run/--diff), Base UI by default with Radix kept for existing apps, house token aliases, Recharts charts via the chart component in Next.js, Field + react-hook-form + zod forms, toasts, dark mode, reduced motion, i18n label props, WCAG 2.2 AA, CASL-gated areas-only sidebars, the command palette. Use when adding, updating, or composing shadcn/ui components or blocks."
paths:
  - "**/components.json"
  - "**/components/ui/**"
---

# shadcn/ui Conventions (Next.js and Vite SPA)

shadcn/ui is the component standard for both React web stacks. It is not a library you upgrade: the
CLI copies source into the package, and after `add` every line is ours — shadcn's own framing is
"not a component library… how you build your component library". The headless base underneath
(focus, keyboard, ARIA) *is* a dependency, and upgrades like one.

**Web only.** shadcn ships no React Native templates — React Native keeps the house theme provider
(`std-react-native`), Phlex keeps `class_variants` (`std-phlex-conventions`). This skill's
`**/components/ui/**` glob matches those stacks' directories too: a `components/ui` with no
`components.json` above it is not shadcn, and nothing below applies.

## First: read `components.json`

Glob `**/components.json`, or run `npx shadcn info --json` in the package.

| Field | Decides |
|---|---|
| `style` prefix | **The base.** `base-*` → Base UI · `radix-*`, `new-york`, `default` → Radix · `aria-*` → React Aria |
| `rsc` | `true` (Next.js): the CLI writes `'use client'` into client primitives · `false` (Vite) |
| `aliases.ui` | Where primitives live — the atom tier, kebab-case, CLI-owned |
| `tailwind.css` | The token file: house tokens, alias wiring, dark variant, reduced-motion backstop |
| `rtl`, `iconLibrary` | Whether installs rewrite to logical classes; the one icon package the app ships |

**No `components.json` → stop and ask.** `init` on an existing app writes shadcn's theme over the
house token block, and `style`, `baseColor` and `cssVariables` cannot change afterwards.

## Load-bearing rules

1. **You own the copied code, so keep the diff to upstream small.** Registry updates never arrive
   on their own: `add <item> --diff`, review, merge by hand. The sanctioned local edits are few and
   named — label props, palette classes → tokens, focus-ring opacity, target size, the breadcrumb
   page's link role. Everything else stays as shipped, variant names included, so the next `--diff`
   is still readable.
2. **Detect the base, write that base's API.** Base UI composes with `render`, Radix with
   `asChild`; neither understands the other's. New packages start on **Base UI** (shadcn's default
   since 2026-07-02); existing Radix packages **stay on Radix** — no migration. **Never mix bases in
   one package**: an item whose `--dry-run` pulls the other base's headless package is a
   stop-and-ask. For `aria-*`, write React Aria's API from `npx shadcn docs <component> -b aria`.
3. **Ask a human before** `init` on an existing app, `apply`, `add --overwrite`, `eject`, and
   `mcp init` — they overwrite house tokens, discard local edits, cannot be undone, or write MCP
   configuration from inside the CLI (a human adds servers through `/mcp-advisor`). Look up with `docs` / `view` / `search`,
   preview with `add --dry-run`, then `add` and read back every written file, `package.json`, and
   the CSS diff. No shadcn MCP server by default, and never shadcn's own agent skill beside this one.
4. **Tokens are aliases — never remap classes by hand.** `destructive`, `destructive-foreground`,
   `chart-1`…`chart-5` and the eight `sidebar-*` names are registered in the theming registry as
   aliases of house roles (`destructive` → `error`; `sidebar-*` → card, accent, primary, border,
   ring), so a vendored `bg-destructive` compiles as shipped. Code **you** write names the house
   role (`bg-error`). Palette classes no alias covers (`text-white`, `bg-black/50`, `bg-white`)
   become tokens. In arbitrary CSS a token is `var(--error)`, never `hsl(var(--error))` — the
   variable already holds a complete color.
5. **No English inside a primitive.** Every hardcoded name or string (`Close`, `Toggle Sidebar`,
   `Go to next page`, `Loading`, `Command Palette`) becomes a required label prop (`closeLabel`,
   `toggleLabel`, `title`, …) the caller fills from `t()`. Block copy moves to message files.
6. **Focus rings are full opacity, at least 2px, at least 3:1.** Stock `ring-ring/50` measures about
   1.5:1 on white with shadcn's neutral tokens: drop the `/50` unless the house pair measures ≥ 3:1.
   Contrast is recomputed for every pair a primitive renders, and pointer targets are at least 32×32
   on web — the house minimum (`std-design-system`); WCAG 2.5.8's floor is 24×24.
7. **Reduced motion:** `tw-animate-css` may animate the primitives only because the global
   `prefers-reduced-motion` backstop sits in the `tailwind.css` file. House page and list
   transitions stay Framer Motion with `useReducedMotion`.
8. **Charts, in Next.js, are the `chart` component composing Recharts** — `ChartConfig` colors as
   `var(--chart-N)`, `ChartTooltip` + `ChartTooltipContent`, `ChartLegend`, `accessibilityLayer`,
   `isAnimationActive={!reduceMotion}` — with the caption, summary and data table rendered by the
   Server Component → `references/charts.md`. The Vite SPA does not use it: its charts are Chart.js
   through react-chartjs-2 → @skills/std-reactjs/references/charts.md.
9. **Forms are `Field` + react-hook-form + zod**, one schema module shared by client and server;
   Next.js re-checks it with `safeParse` inside the server action. Never `add form` (legacy).
10. **Toasts follow the base** — Base UI → shadcn `toast`, Radix → `sonner` — behind one house
    `notify()` helper that takes translation keys. A toast never carries field validation.
11. **Primitives are atoms; house molecules and organisms compose them** (the `atomic-design`
    skill). Primitives stay at `aliases.ui`, kebab-case, even the ones that import `Button`.
    Compositions — including every file a block writes — move to the atomic directories, PascalCase.
12. **Sidebars and nav are gated by permission key, and the global sidebar lists areas only.** The
    layout filters one nav config with the CASL ability (`visibleNav`); sidebar primitives receive
    plain, already-filtered areas — never the ability, never a role name. Static `SidebarGroupLabel`
    headings are allowed; `SidebarMenuSub`, collapsible groups and section trees are not. The active
    area is `areaState` (whole path segments), never a bare `startsWith`. Sections render in the
    area's own layout. The sidebar ships open (`defaultOpen`), and only the person collapses it →
    @skills/ui-ux-patterns/references/drill-down-navigation.md
13. **One command palette organism, optional per product, never the only route.** `command` (cmdk)
    fed by the same `visibleNav` output and the permission-scoped search endpoint, opened by a
    visible button as well as Cmd/Ctrl+K, its dialog title and description from `t()` →
    `references/components-and-blocks.md`.

```tsx
// Base UI (style base-*): compose with render
<DialogTrigger render={<Button variant="outline" />}>{t('orders.cancel.open')}</DialogTrigger>
<SidebarMenuButton render={<Link href={area.href} />} isActive={active}>{t(area.label)}</SidebarMenuButton>

// Radix (style radix-*, new-york, default): compose with asChild
<DialogTrigger asChild><Button variant="outline">{t('orders.cancel.open')}</Button></DialogTrigger>
<SidebarMenuButton asChild isActive={active}><Link href={area.href}>{t(area.label)}</Link></SidebarMenuButton>

// Both bases: a link that looks like a button stays a link (Base UI's Button always sets role="button")
<Link href="/orders/new" className={buttonVariants({ variant: 'outline' })}>{t('orders.new')}</Link>
```

## Next.js (App Router)

- **`rsc: true`.** The CLI writes `'use client'` into client primitives, and which ones differs by
  base (`accordion` carries it in new-york-v4, not in base-nova) — read the installed file. A Server
  Component may render any primitive with server-rendered children and plain-data props; pages and
  layouts never take the directive (`std-nextjs`).
- **Dark mode:** `next-themes` `ThemeProvider` with `attribute="class"`, `defaultTheme="system"`,
  `enableSystem`, `disableTransitionOnChange`, in a client providers file; `suppressHydrationWarning`
  on `<html>`. `sonner`'s `Toaster` reads this provider.
- **Mutations:** a `Field` form on `useActionState`. The action `safeParse`s the shared schema and
  returns the submitted values with the errors, because React resets the form after an action.
- **Links:** `next/link` through `render` or `asChild`, or `buttonVariants()` on the link itself.
- **Sidebar:** the app layout filters `NAV` on the server and passes plain areas to the client
  `AppSidebar`; each area layout renders that area's sections. `defaultOpen` stays true unless the
  person's `sidebar_state` cookie, written by the primitive, says otherwise →
  @skills/std-nextjs/references/navigation.md.

## Vite SPA

- **`rsc: false`** — no directives.
- **Dark mode:** the house theming provider toggles the same `.dark` class on `<html>`. A vendored
  `sonner.tsx` imports `useTheme` from `next-themes` — point it at the house provider instead.
- **Mutations:** a TanStack Query `useMutation`. `VALIDATION_ERROR` details land on their fields
  with `setError`; every other failure is `setError('root', …)` carrying `requestId`, rendered as a
  `FieldError`. A `notify()` error toast may add to it, never replace it.
- **Links:** React Router's `<Link to>` through `render` or `asChild`. Routes stay lazy-loaded
  (`std-reactjs`) — chart routes especially. The SPA's charts are Chart.js, not this skill's `chart`.
- **Nav:** `AppLayout` builds the ability from the `['me']` query and runs `visibleNav`; the sidebar
  organism lists areas only, and each area's layout route renders its sections around its
  `<Outlet />` (`std-reactjs`).

## Deep guides (read on demand, do not preload)

- Every CLI command and flag with when the house allows it, `components.json` field by field, the
  fields that cannot change after init, the `add --diff` update workflow, monorepos, registries,
  and the MCP policy → `references/cli-and-registry.md`
- The catalog by atomic level, which items exist for which base (including `command`'s two
  `CommandDialog` shapes), the Base UI vs Radix API table (`render` / `asChild`, alert-dialog
  actions, `toast` / `sonner`, overlays, focus rings), the areas-only `AppSidebar`, the command
  palette organism, blocks and what changes on adoption, data tables on TanStack Table v9 →
  `references/components-and-blocks.md`
- `Field` + react-hook-form + zod (`aria-invalid` / `data-invalid`), the shared schema, Next.js
  `useActionState` + `safeParse`, Vite mutations with server errors on fields, `notify()` per base,
  alert dialogs for destructive confirmation, loading and empty states → `references/forms-and-feedback.md`
- What the primitives guarantee and the measured gaps (focus ring, `muted-foreground` on `muted`,
  borders, targets at the house 32×32, the breadcrumb page), label props for every hardcoded string, RTL
  (`rtl: true`, `DirectionProvider`, `dir` on portals), the reduced-motion backstop, chart text
  alternatives → `references/accessibility-and-i18n.md`
- Next.js charts: the `chart` component, the Server/Client split, loading, empty and error states,
  the server-rendered text alternative, reduced motion, lazy chart modules, tests →
  `references/charts.md`

## Owned elsewhere — do not duplicate

- **Token values, the alias registry, Tailwind v4 wiring** (`@theme inline`,
  `@custom-variant dark (&:is(.dark *))`) → @skills/theming/references/platform-integration.md and
  the `theming` skill; the measured contrast table → @skills/theming/references/design-tokens.md
- **Charts on the other stacks** — the Vite SPA's Chart.js + react-chartjs-2 →
  @skills/std-reactjs/references/charts.md; Rails Phlex views on Chart.js through Stimulus →
  @skills/std-phlex-conventions/references/charts.md
- **Navigation structure** — areas, levels, breadcrumbs, the palette's rules →
  @skills/ui-ux-patterns/references/drill-down-navigation.md; App Router mechanics →
  @skills/std-nextjs/references/navigation.md; the search endpoint and `ancestors` →
  @skills/std-api-design/references/drill-down-resources.md
- **Permission gates** — `NAV`, `visibleNav`, `areaState`, `AbilityProvider`, the `['me']` query,
  row actions → @skills/access-control-designer/references/ui-gates.md; not rendered / disabled with
  a reason / locked → @skills/ui-ux-patterns/references/role-based-ux.md
- **Motion** — durations, easing, the backstop block, Framer Motion →
  @skills/std-design-system/references/motion.md
- **Next.js data and rendering** — Server Components, caching, server action rules → the
  `std-nextjs` skill (@skills/std-nextjs/references/server-actions.md)
- **Which atomic level a composition is** → @skills/atomic-design/references/choosing-the-atomic-level.md
- **ARIA for each state** → the `std-accessibility` skill; **the API error envelope** →
  @skills/std-api-design/references/errors-typescript.md; **vetting an MCP server** →
  @skills/mcp-advisor/references/vetting-servers.md
