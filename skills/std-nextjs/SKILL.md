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

## Stack

| Concern | Library |
|---------|---------|
| Framework | **Next.js 15+** (App Router) — Server Components by default. React 19 minimum |
| Styling | Tailwind CSS (same conventions as the `std-reactjs` skill; use `cn()` for conditional classes) |
| Server state | TanStack Query — Client Components only |
| Client state | Zustand — Client Components only |
| HTTP | axios (Rails API client) for client + server actions; `fetch` for cacheable server reads |
| Forms | react-hook-form + zod (Client Components) |
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

## Project Structure

```
app/                    # Routes: layout.tsx, page.tsx, loading.tsx, error.tsx, not-found.tsx
  (auth)/ (dashboard)/  # Route groups
  api/                  # Route Handlers — BFF/webhooks/health only, never a second API
src/
  components/ui|forms/  # Design system primitives, form components
  actions/              # Server actions (use-case layer for mutations)
  hooks/ stores/        # Client hooks, Zustand stores
  api/                  # Rails API client
  domain/ types/ lib/ i18n/
middleware.ts           # Edge middleware (auth gate, locale, redirects)
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
- TanStack Query only when you need polling, infinite scroll, or optimistic updates — seed it with
  server data via `initialData` so there is no loading flash.
- ISR: `export const revalidate = N`. Static: nothing, or `dynamic = 'force-static'`. Per-request:
  `dynamic = 'force-dynamic'`. On-demand: `revalidatePath()` / `revalidateTag()`.

### Server actions
- **Always validate input with zod** — a server action is a public endpoint.
- **Always authorize inside the action**; never take identity from the form payload.
- **Always `revalidatePath`/`revalidateTag`** after a successful mutation.
- Return serializable data only. Never return a raw error — catch, log, return a user-safe message.
- Prefer progressive enhancement: `<form action={formAction}>` + `useActionState`.

### Metadata
- **Every page exports `metadata` or `generateMetadata`.** Use `generateMetadata` when the title
  depends on fetched data. Set a canonical URL to avoid duplicate content.

### Middleware
- Auth redirects, locale detection, A/B bucketing, rate limiting. Runs on the Edge Runtime —
  keep it lightweight, no data fetching, always set a `matcher`. It is a coarse gate, not the
  security boundary.

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

## Deep guides (read on demand, do not preload)

- Server/Client boundary, composition, streaming, `<Suspense>`, error boundaries → `references/rendering.md`
- Server actions: validation, forms, optimistic UI, redirects, testing → `references/server-actions.md`
- Caching, ISR, `revalidateTag` vs `revalidatePath`, request dedupe → `references/caching.md`
- Edge middleware, SEO/`generateMetadata`/sitemaps, Vercel & ECS deploy → `references/middleware-seo-deploy.md`
