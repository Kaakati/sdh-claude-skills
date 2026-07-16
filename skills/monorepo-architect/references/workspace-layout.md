# Workspace Layout — structure by deployable unit

Load-bearing rules restated (hold even if you read nothing else):

1. **Top-level directories are deployable units, not layers.** `apps/`, `packages/`, `tooling/`.
2. **Shared code lives in `packages/`** with its own tests and its own owner — never reached
   into via relative paths.
3. **Every package has one purpose.** A package that accepts anything becomes a dumping ground.

---

## The layout

```
apps/                    # deployables — each ships somewhere
  rails-api/             # Rails API  -> ECS Fargate
  web/                   # Next.js    -> Vercel
  admin/                 # Vite SPA   -> S3/CloudFront
  mobile/                # React Native -> App Store / Play
packages/                # shared libs — each has tests + an owner
  api-client/            # generated from the Rails schema
  types/                 # shared domain types
  ui/                    # shared components
  config/                # runtime config helpers
tooling/                 # dev-time only, never shipped
  eslint-config/
  tsconfig/
  generators/
```

**Why deployable unit and not layer.** A layer-first tree (`frontend/`, `backend/`, `shared/`)
answers "what kind of code is this?" — a question nobody asks. A deployable-first tree answers
"what breaks if I change this, and what ships when I merge it?" — the question CI, CODEOWNERS,
and release tagging all need. Affected-only CI is nearly free on the second and near-impossible
on the first.

## Decision: where does this code go?

| The code… | Home | Test |
|---|---|---|
| Ships as its own artifact | `apps/<name>` | Does it have a deploy target? |
| Is imported by 2+ apps | `packages/<domain>` | Would you publish it if apps were separate repos? |
| Is imported by exactly 1 app | Stay in that app | Moving it early buys nothing and costs a boundary |
| Configures the toolchain | `tooling/` | Does it run at dev/build time only? |
| Is generated from an API schema | `packages/api-client` | See `references/api-contract.md` |

**Do not promote to `packages/` on speculation.** A package used by one app is a cost with no
benefit: an extra boundary, an extra build edge, an extra owner. Promote on the *second*
consumer.

## `std-*` path-scoping survives this layout

This plugin's convention skills load by **canonical structure + marker files**, not by wrapper
directory name. Verified:

| Path | Loads |
|---|---|
| `apps/rails-api/app/models/user.rb` | `std-rails-conventions` |
| `apps/rails-api/app/controllers/orders_controller.rb` | `std-rails-conventions` |
| `apps/web/src/pages/Dashboard.tsx` | `std-reactjs` |
| `apps/mobile/src/screens/Home.tsx` | `std-react-native` |
| `packages/ui/src/components/Button.tsx` | **nothing** |

**The last row is the real gap.** A shared package matches no framework's canonical structure,
so no framework's `std-*` conventions are scoped to it. Give each package a `CLAUDE.md` — copy
[`docs/templates/shared.CLAUDE.md`](../../../docs/templates/shared.CLAUDE.md) — stating its
purpose, its public entry point, and who owns it.

## Decision: public entry points

A package's directory layout is **private**. Its `exports` map is the contract.

### Bad — every file is public surface

```json
// packages/ui/package.json  ❌
{
  "name": "@acme/ui",
  "main": "./src/index.ts"
}
```

```tsx
// apps/web/src/app/orders/page.tsx  ❌
// Consumers now depend on @acme/ui's internal file tree. Moving Button.tsx is a
// breaking change to three apps, and nothing tells you that until CI goes red.
import { Button } from '@acme/ui/src/components/Button';
import { formatCents } from '@acme/ui/src/internal/money';
```

### Good — the exports map is the boundary

```json
// packages/ui/package.json  ✅
{
  "name": "@acme/ui",
  "exports": {
    ".": "./src/index.ts",
    "./styles.css": "./src/styles.css"
  }
}
```

```ts
// packages/ui/src/index.ts  ✅  the whole public API, in one reviewable file
export { Button } from './components/Button';
export { Card } from './components/Card';
// `formatCents` is intentionally NOT exported — it is an implementation detail.
```

```tsx
// apps/web/src/app/orders/page.tsx  ✅
import { Button } from '@acme/ui';
```

Now the internal tree is free to move, and `src/index.ts` is a diff a reviewer can actually
read. Widening the API becomes a deliberate, visible act.

## Decision: splitting a dumping-ground package

`packages/utils` that imports half the repo is the classic failure. It is not a package; it is
a namespace with a build step.

### Bad — one package, no purpose

```
packages/utils/src/
  money.ts          # imports nothing
  dates.ts          # imports nothing
  api-retry.ts      # imports @acme/api-client
  order-status.ts   # imports @acme/types, knows Rails enum values
  analytics.ts      # imports the web app's env vars   <-- packages -> apps
```

Everything depends on `utils`, so `utils` depends on everything, so every change to anything
invalidates every cache entry in the repo. The build graph has one node.

### Good — split by domain, one purpose each

```
packages/money/          # pure, zero deps
packages/dates/          # pure, zero deps
packages/api-client/     # owns retry; the only package that talks HTTP
packages/order-domain/   # order status rules; depends on @acme/types
```

`analytics.ts` moves **into the app that owns its env vars** — a package must never import an
app. Cache invalidation now tracks real dependencies, and each package has one owner.

**Migration sequencing** (a monorepo cannot be restructured in one PR):

1. Create the new packages; re-export from `utils` so nothing breaks.
2. Migrate consumers per domain, one PR each.
3. When `utils` only re-exports, delete it and update the last imports.
4. Add the boundary lint (`references/boundaries.md`) so it cannot regrow.

Ship at every step.
