# Web SSR (Next.js App Router) — package conventions

Copy this file into your Next.js package directory as `CLAUDE.md`. The directory
can be named anything — `next/`, `web/`, `site/` — detection is wrapper-agnostic
(`next.config.*` / `app/*.tsx` / `src/app/`). Layers on the root `CLAUDE.md`.

Next.js App Router: Server Components for data, server actions for mutations,
Client Components for interactivity, ISR/SSG, shadcn/ui components (Base UI by default; an existing Radix
package stays on Radix), Recharts through the shadcn/ui `chart` component, drill-down navigation. Standards ship as the `sdh` plugin's path-scoped `std-*` skills
(`std-nextjs`, `std-shadcn-ui`, `std-accessibility`, `std-i18n`, `std-testing`, `std-clean-architecture`), each
scoped to matching files. Scoping limits when a skill applies — read the one bearing on your change.
The `nextjs-developer` agent (`/sdh:nextjs-dev`) builds UI here with `std-shadcn-ui` and `std-nextjs` preloaded.

## Commands
- Dev: `npm run dev`
- Build: `npm run build`
- Tests: `npx vitest`
- Types: `npx tsc --noEmit`

## Structure
- `app/` — App Router routes, layouts, route handlers (Server Components by default); one route group per area (`app/(app)/(orders)/`), whose layout renders the section nav
- `src/components/` — Client/Server components (target ≤200 lines)
- `src/components/ui/` — shadcn/ui primitives the CLI owns (exempt from the 200-line limit; never split them)
- `components.json` — shadcn config; its `style` names the primitive base (`base-*` → Base UI, `radix-*`/`new-york` → Radix)
- `src/lib/utils.ts` — `cn` (re-exports the `cn` package)
- `src/lib/nav.ts` — `NAV: Area[]` (areas with their sections), filtered per role by `visibleNav`
- `src/actions/` — server actions (mutations)
- `src/hooks/` — client-side hooks
- `src/api/` — Rails API client
- `src/domain/` — pure TypeScript types
- `src/i18n/` — locale config

## Conventions
- Default to Server Components; add `"use client"` only when interactivity is needed.
- Mutations go through server actions; validate input with `zod`; `revalidatePath`/`revalidateTag` after writes (Next.js 16: `updateTag` in server actions).
- Use `next/image` and `next/link`. Add SEO metadata via `generateMetadata`.
- Navigation is drill-down: the app layout filters `NAV` with `visibleNav` and renders an areas-only `AppSidebar` (no `SidebarMenuSub`, no collapsible section trees), and each area's layout renders its section nav. List state lives in `searchParams`; breadcrumbs come from the API's `ancestors`; a command palette is optional and never the only way to a page. Test the navigation rendered per role.
- UI is shadcn/ui components and blocks. shadcn's token names (`destructive`, `sidebar-*`, `chart-1`…`chart-5`) are registered aliases of house tokens, so install primitives unmodified; code you write names the house role (`bg-error`). Write the base's API (`render` on Base UI, `asChild` on Radix); ask a human before `shadcn init`, `apply`, `--overwrite`, or `eject`.
- Forms: shadcn `Field` + `react-hook-form` + `zod`, and the server action re-checks the same schema with `safeParse` (`useActionState`). Toasts go through the house `notify()` helper, never for field errors.
- Theme: `next-themes` `ThemeProvider` (`attribute="class"`, `defaultTheme="system"`) with `suppressHydrationWarning` on `<html>`.
- Charts: shadcn `chart` (Recharts), drawn in a `'use client'` leaf with `isAnimationActive={!reduceMotion}`; the Server Component renders the caption, summary and data table. No other chart library in a Next.js package.
- CASL gates come from the `/me` rules (plain rules, not the ability, cross to Client Components).
- Accessibility: semantic HTML, label associations, `alt` text, visible focus. Use i18n keys, not literals.
