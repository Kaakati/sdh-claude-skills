---
name: std-nextjs
description: Next.js App Router conventions — Server Components, server actions, ISR/SSG, drill-down navigation (a route group per area, section sub-nav in area layouts, list state in searchParams, breadcrumbs from ancestors), Vercel. Use when building Next.js pages, layouts, navigation, or server actions.
paths:
  - "**/next.config.*"
  - "**/app/**/*.tsx"
  - "**/app/**/*.jsx"
  - "**/src/app/**/*.ts"
  - "**/src/app/**/*.tsx"
  - "**/middleware.ts"
  - "**/proxy.ts"
---

# Next.js (App Router) Conventions

Rules for building Next.js web applications with the App Router, consuming the shared Rails API backend.

## Stack

| Concern | Library |
|---------|---------|
| Framework | **Next.js 15+** (App Router) — Server Components by default. React 19 minimum |
| Components | shadcn/ui — the base (Base UI, Radix, or React Aria) is read from `components.json` `style` and never mixed in one package; the `std-shadcn-ui` skill owns the rest |
| Styling | Tailwind CSS (same conventions as the `std-reactjs` skill); `cn()` from `@/lib/utils`, which re-exports the `cn` package |
| Theme | `next-themes` — `attribute="class"`, `suppressHydrationWarning` on `<html>` |
| Server state | TanStack Query — Client Components only |
| Client state | Zustand — Client Components only |
| HTTP | axios (Rails API client) for client + server actions; `fetch` for cacheable server reads |
| Forms | shadcn `Field` + react-hook-form + zod (Client Components); the server action re-checks the same schema with `safeParse` |
| Charts | Recharts through shadcn's `chart` component — the Server Component renders the caption, summary and data table, a `'use client'` leaf draws |
| i18n | next-intl or react-i18next |
| Testing | Vitest + React Testing Library + MSW |

CSS Modules only for animations Tailwind cannot express.

## This targets Next.js 15+ — and 14 answers differently

The version is part of the convention (`std-infrastructure`: *pin every version*). Next.js 15
changed **caching defaults and request APIs**, so the same code behaves differently on 14 — and
guidance that does not say which major it means is guidance you cannot check.

| | Next.js 14 | **Next.js 15+ (this repo)** |
|---|---|---|
| `fetch` | cached by default | **not cached by default** — opt in with `cache: 'force-cache'` |
| `GET` Route Handlers | cached by default | **not cached** — opt in with `export const dynamic = 'force-static'` |
| Client Router Cache | page segments reused on `<Link>` nav | **not reused** (back/forward and shared layouts still are); tune via `experimental.staleTimes` |
| `cookies`, `headers`, `draftMode` | synchronous | **async — `await cookies()`** |
| `params`, `searchParams` | plain objects | **Promises — `await params`** |

Two consequences that shape every example in this skill:

- **`params: Promise<{…}>` and `await cookies()` are not style — they are required.** Sync usage
  is a 14-ism that warns in dev and breaks.
- **Never rely on the `fetch` default.** Since 15 makes uncached the default and 14 made cached
  the default, *any* code whose correctness depends on the default is a version bug waiting to
  happen. State intent explicitly — `next: { revalidate, tags }` or `cache: 'force-cache'` — which
  is why `references/caching.md` always does, and why it reads as verbose. That verbosity is the
  point.

Upgrading from 14: `npx @next/codemod@canary upgrade latest` handles the async-API migration.

### Next.js 16 renames two things this skill uses

Keep 15's names until the package pins 16 — 15 has neither `updateTag` nor a proxy convention
(Next.js docs — proxy.js, revalidateTag, updateTag, Upgrading to version 16).

| | Next.js 15 | **Next.js 16** |
|---|---|---|
| Request-time gate | `middleware.ts` exporting `middleware`; Edge runtime by default | **`proxy.ts` exporting `proxy`**, Node.js runtime only — a `runtime` config in the file throws. `middleware.ts` still runs, deprecated, and is the only way to stay on Edge. Codemod: `npx @next/codemod@canary middleware-to-proxy .` |
| Tags after a write | `revalidateTag(tag)` | **Server action: `updateTag(tag)`** — read-your-own-writes, Server Actions only. **Route Handler: `revalidateTag(tag, { expire: 0 })`**, or `revalidateTag(tag, 'max')` where serving stale content while it refreshes is acceptable. The one-argument form is deprecated and fails type-checking |

## Project Structure

```
app/                        # Routes: layout.tsx, page.tsx, loading.tsx, error.tsx, not-found.tsx
  (auth)/ (app)/(orders)/   # Route groups — one per area; a group adds no URL segment
  api/                      # Route Handlers — BFF/webhooks/health only, never a second API
src/
  components/ui/            # shadcn primitives — CLI-owned (aliases.ui), kebab-case
  components/<level>/       # house compositions on the atomic ladder, PascalCase
  actions/                  # Server actions (use-case layer for mutations)
  schemas/                  # zod schemas — one per form or list state, imported by both sides
  hooks/ stores/            # Client hooks, Zustand stores
  api/                      # Rails API client
  domain/ types/ lib/ i18n/
middleware.ts               # Request-time gate: session cookie, locale, redirects (proxy.ts on Next.js 16)
tests/
```

## Core Rules

### Server vs Client Components
- Every component is a Server Component by default — no directive needed. Use for data fetching,
  static rendering, SEO-critical content, layouts.
- Add `'use client'` only for interactivity: state, event handlers, browser APIs, Zustand,
  TanStack Query. Keep Client Components small and leaf-level.
- **Never add `'use client'` to a page or layout file** — extract the interactive part instead.
- Server Components can `await` directly; they cannot use hooks, state, or event handlers.

```tsx
// app/orders/page.tsx — Server Component fetches, Client Component renders interaction
import { OrderTable } from '@/components/OrderTable'; // 'use client'

export default async function OrdersPage() {
  const orders = await fetchOrders();
  return <OrderTable initialData={orders} />;
}
```

### Data fetching
- Fetch in Server Components with `async/await`. Parallelize independent reads with `Promise.all`.
- TanStack Query only when you need polling, infinite scroll, optimistic updates, or a client
  typeahead (the command palette's search) — seed it with server data via `initialData` where
  there is any, so there is no loading flash.
- ISR: `export const revalidate = N`. Static: nothing, or `dynamic = 'force-static'`. Per-request:
  `dynamic = 'force-dynamic'`. On-demand: `revalidatePath()` / `revalidateTag()`, and `updateTag()`
  in a server action on Next.js 16 (the table above).

### Server actions
- **Always validate input with zod** — a server action is a public endpoint. When a form validates
  on the client, the action `safeParse`s the same schema module; the client check is UX only.
- **Always authorize inside the action**; never take identity from the form payload.
- **Always invalidate** after a successful mutation — `revalidatePath`, or the tag: `updateTag` on
  16, `revalidateTag` on 15.
- Return serializable data only. Never return a raw error — catch, log, return a user-safe message.
- Prefer progressive enhancement: `<form action={formAction}>` + `useActionState`.

### Navigation (drill-down)
- **One route group per area.** The app layout filters `NAV` with `visibleNav` on the server, and
  the global `AppSidebar` lists **areas only** — never a nested section tree.
- **Each area layout renders its section sub-nav** from a client leaf reading `usePathname()` —
  layouts do not rerender on navigation.
- **List state lives in `searchParams`** — the API's list parameters, one-to-one. Applying a filter
  pushes a history entry; typing in a search box replaces it.
- **Every detail renders its breadcrumb from the API's `ancestors`**, from level 3. A triage list may
  open its detail as a panel (a parallel slot plus an intercepting route); the canonical URL still
  renders the full page.
- **A level change moves focus to the new `h1`**, and the area layout's title template names the area.
- Mechanics → `references/navigation.md`; the rules →
  `@skills/ui-ux-patterns/references/drill-down-navigation.md`.

### Metadata
- **Every page exports `metadata` or `generateMetadata`.** Use `generateMetadata` when the title
  depends on fetched data. Set a canonical URL to avoid duplicate content.

### Middleware (`proxy.ts` on Next.js 16)
- Auth redirects, locale detection, A/B bucketing, rate limiting. Edge Runtime on 15, Node.js on 16
  (the table above) — either way keep it lightweight, no data fetching, always set a `matcher`. It
  is a coarse gate, not the security boundary.

### Performance
- Prefer Server Components — less client JS.
- `next/image` for every image; `next/link` for every internal link.
- Wrap slow data-fetching regions in `<Suspense>` to stream the shell first.
- Audit client chunks with `@next/bundle-analyzer`.

## Anti-Patterns to Avoid

- `'use client'` on a page or layout file.
- `useEffect` for data fetching in pages.
- Importing server-only code in Client Components (mark those modules `import 'server-only'`).
- Missing `loading.tsx` / `error.tsx` boundaries (`error.tsx` must be a Client Component).
- `<img>` instead of `next/image`; `<a>` instead of `next/link`.
- Missing `metadata` export.
- Server actions without input validation or without revalidation.
- A secret behind a `NEXT_PUBLIC_` prefix.
- Rebuilding the Rails API inside `app/api`.
- `asChild` in a Base UI package, or `render` in a Radix one — `components.json` names the base.
- A toast for a validation error; a chart with no text alternative.
- `SidebarMenuSub` or any section tree in the global sidebar; an active state from a bare `startsWith`.
- Breadcrumbs built from history or URL segments; an in-app Back that calls `history.back()`;
  list filters kept in component state instead of the URL.

## Deep guides (read on demand, do not preload)

- Server/Client boundary, composition, streaming, `<Suspense>`, error boundaries → `references/rendering.md`
- Server actions: validation, forms, optimistic UI, redirects, testing → `references/server-actions.md`
- Caching, ISR, `revalidateTag` vs `revalidatePath`, `updateTag` on 16, request dedupe, revalidating a drill-down level → `references/caching.md`
- Middleware (`proxy.ts` on 16), SEO/`generateMetadata`/sitemaps, Vercel & ECS deploy → `references/middleware-seo-deploy.md`
- Drill-down navigation: route groups per area, the area layout's section sub-nav, list state in
  `searchParams`, list-detail with parallel and intercepting routes, breadcrumbs from `ancestors`,
  focus on a level change, per-role nav tests → `references/navigation.md`

Owned elsewhere — do not duplicate:

- **shadcn/ui components** — which base, the CLI and what never runs without a human, shadcn's
  token names as registered aliases, primitives and blocks, the areas-only `AppSidebar` and the
  command palette → the `std-shadcn-ui` skill
  (`@skills/std-shadcn-ui/references/cli-and-registry.md`,
  `@skills/std-shadcn-ui/references/components-and-blocks.md`); `Field` forms and toasts →
  `@skills/std-shadcn-ui/references/forms-and-feedback.md`.
- **Charts** — Recharts through shadcn's `chart`, the server-rendered text alternative, reduced
  motion → `@skills/std-shadcn-ui/references/charts.md`.
- **Drill-down rules and the API behind them** — areas, levels, location cues, Back, the palette →
  `@skills/ui-ux-patterns/references/drill-down-navigation.md`; levels → endpoints, `ancestors`,
  list parameters, search → `@skills/std-api-design/references/drill-down-resources.md`.
- **Permission-gated nav, menus, and actions** (the layout builds the CASL ability from
  `getSession()`; plain rules, not the ability, cross to Client Components; gates check permission
  keys, never role names; `NAV`, `visibleNav`, `areaState`) →
  `@skills/access-control-designer/references/ui-gates.md`.
