# Mobile (React Native) — package conventions

Copy this file into your React Native package directory as `CLAUDE.md`. The
directory can be named anything — `mobile/`, `app/`, `native/` — detection is
wrapper-agnostic (metro.config / app.json / `react-native` in package.json).
Layers on top of the repository-root `CLAUDE.md`.

React Native: Zustand (client state), TanStack Query (server state), Centrifugo
(real-time), MMKV (storage). Standards ship as the `sdh` plugin's path-scoped `std-*` skills
(`std-react-native`, `std-accessibility`, `std-i18n`, `std-clean-architecture`), each scoped to
matching files. Scoping limits when a skill applies — read the one bearing on your change.

## Commands
- Tests: `npm test`
- Types: `npx tsc --noEmit`
- Lint: `npx eslint .`
- Start: `npx react-native start` (iOS: `npm run ios`, Android: `npm run android`)

## Structure
- `src/screens/` — screen components (target ≤200 lines)
- `src/components/` — shared UI components (Atomic Design)
- `src/hooks/` — TanStack Query hooks (all server state)
- `src/stores/` — Zustand stores (client-only state, never server data)
- `src/navigation/` — `@react-navigation/native`: a root stack, one bottom tab per area, a native stack per tab, and the linking config (a path per screen that matches the web URL)
- `src/api/` — axios API client
- `src/domain/` — pure TypeScript types
- `src/i18n/` — locale config

## Conventions
- Server state → TanStack Query; client state → Zustand. Never mix them.
- Screens and tabs are registered conditionally from the CASL ability built off the `['me']` query.
- Navigation is drill-down: tabs come from `visibleNav` once `['me']` loads — 3–5 including Account, never toggled at runtime, and no drawer for switching areas. Screen depth follows the drill levels inside each tab's stack; a link a role cannot open goes to the no-access screen. Test the navigator rendered per role.
- Use `react-native-fast-image` for images, `react-native-mmkv` for storage.
- Accessibility: use `accessibilityLabel`/`accessibilityRole` (RN), not web `alt`/ARIA.
- shadcn/ui is web-only: React Native keeps the house theme provider and `std-react-native` component patterns.
- Forms: `react-hook-form` + `zod`. No hardcoded user-facing strings — use i18n keys.
