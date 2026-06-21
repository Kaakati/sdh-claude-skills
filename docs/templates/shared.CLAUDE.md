# Shared library — package conventions

Copy this file into a shared/common package directory as `CLAUDE.md` (e.g.
`shared/`, `common/`, `packages/core/`). Layers on the repository-root `CLAUDE.md`.

Framework-agnostic code imported by the frontends (and mirrored against the Rails
API contract): pure TypeScript types, validation schemas, and utilities.

## Commands
- Tests: `npx vitest`
- Types: `npx tsc --noEmit`
- Build: `npm run build`

## Structure
- `src/types/` — shared TypeScript types (mirror Panko serializer output)
- `src/schemas/` — `zod` schemas shared across web/mobile forms and API validation
- `src/utils/` — pure utilities (no framework or DOM/native dependencies)

## Conventions
- No React, React Native, or Node-only APIs here — this package must import cleanly
  into every frontend. Keep it pure and side-effect free.
- A change here usually ripples into the frontends that consume it. Update the
  shared edit and its call sites in one session (grant cross-package access with
  `--add-dir` or `additionalDirectories` — see `docs/monorepo-setup.md`).
- Keep types in sync with the Rails serializers that produce the JSON.
