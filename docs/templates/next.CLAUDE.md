# Web SSR (Next.js App Router) — package conventions

Copy this file into your Next.js package directory as `CLAUDE.md`. The directory
can be named anything — `next/`, `web/`, `site/` — detection is wrapper-agnostic
(`next.config.*` / `app/*.tsx` / `src/app/`). Layers on the root `CLAUDE.md`.

Next.js App Router: Server Components for data, server actions for mutations,
Client Components for interactivity, ISR/SSG. Standards in the root `.claude/rules/`
(`nextjs`, `accessibility`, `i18n`, `testing`, `clean-architecture`) auto-load.

## Commands
- Dev: `npm run dev`
- Build: `npm run build`
- Tests: `npx vitest`
- Types: `npx tsc --noEmit`

## Structure
- `app/` — App Router routes, layouts, route handlers (Server Components by default)
- `src/components/` — Client/Server components (target ≤200 lines)
- `src/actions/` — server actions (mutations)
- `src/hooks/` — client-side hooks
- `src/api/` — Rails API client
- `src/domain/` — pure TypeScript types
- `src/i18n/` — locale config

## Conventions
- Default to Server Components; add `"use client"` only when interactivity is needed.
- Mutations go through server actions; validate input with `zod`; `revalidatePath`/`revalidateTag` after writes.
- Use `next/image` and `next/link`. Add SEO metadata via `generateMetadata`.
- Accessibility: semantic HTML, label associations, `alt` text, visible focus. Use i18n keys, not literals.
