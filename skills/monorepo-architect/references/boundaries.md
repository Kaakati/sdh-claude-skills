# Boundaries — the rule a machine has to enforce

Load-bearing rules restated (hold even if you read nothing else):

1. **If you wouldn't allow the coupling across two repos, don't allow it inside one.**
2. **Every dependency is declared.** Co-location is not permission to import.
3. **A boundary a human enforces is not a boundary.** It must fail CI.

---

## Why this is the failure mode, not a style preference

Two repos give you a boundary for free: you physically cannot import what you have not
published. A monorepo removes that, and gives nothing back by default. So the coupling that
separate repos made *impossible* becomes merely *impolite* — and impolite loses, every time,
under deadline.

The result is an **undeclared big ball of mud**: the dependency graph in `package.json` says
one thing, the imports say another. Everything that reads the declared graph — affected-only
CI, remote cache keys, release tagging — is now working from a lie. This is why boundaries rank
with tooling rather than below it: a wrong graph silently poisons every tool built on it.

## Decision: which enforcement mechanism?

| You need | Use | Cost |
|---|---|---|
| Stop deep/relative cross-package imports (JS/TS) | ESLint `no-restricted-imports` | Near zero — start here |
| Typed layering rules (`ui` may not import `app`) | Nx tags + module boundaries | Adopt Nx, or nothing |
| Boundaries *inside* one large Rails app | **packwerk** | Real; only worth it when the app is big |
| Stop `packages/` importing `apps/` | ESLint + `dependency-cruiser` | Low |

Start with ESLint. It catches the overwhelming majority — deep relative paths — for one config
file and no new tool.

## JS/TS — ESLint

### Bad — the coupling nothing prevents

```ts
// packages/order-domain/src/status.ts  ❌ a package reaching into an app
import { API_BASE } from '../../../apps/web/src/config/env';

// apps/mobile/src/screens/Orders.tsx  ❌ an app reaching into another app's internals
import { OrderRow } from '../../../web/src/components/OrderRow';

// apps/web/src/app/page.tsx  ❌ bypassing a package's public entry point
import { Button } from '@acme/ui/src/components/Button';
```

Each is a dependency the graph does not record. `packages/order-domain` now silently depends on
the web app: change the web app, and the domain package's tests should rerun — but affected-only
CI has no idea, so they don't.

### Good — the rule fails CI

```js
// tooling/eslint-config/boundaries.js  ✅
module.exports = {
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [
        {
          // Anything climbing out of its own package.
          group: ['../../*', '../../../*'],
          message:
            'Cross-package imports must go through the package name (e.g. `@acme/ui`), not a ' +
            'relative path. Relative escapes are invisible to the dependency graph, so ' +
            'affected-only CI and the remote cache will both be wrong.',
        },
        {
          // A package must never depend on a deployable.
          group: ['@acme/*/src/*'],
          message:
            'Import from the package root (`@acme/ui`), not its internals. The `exports` map ' +
            'is the contract; the file tree is private.',
        },
      ],
    }],
  },
};
```

```json
// packages/order-domain/package.json  ✅ dependencies are declared, so the graph is true
{
  "name": "@acme/order-domain",
  "dependencies": { "@acme/types": "workspace:*" }
}
```

Add the direction rule that ESLint patterns can't express — *no package may import any app* —
with `dependency-cruiser`:

```js
// .dependency-cruiser.js  ✅
module.exports = {
  forbidden: [{
    name: 'packages-may-not-import-apps',
    severity: 'error',
    comment:
      'A shared package that imports a deployable is not shared — it is that app in disguise, ' +
      'and it drags the app into every other consumer\'s build.',
    from: { path: '^packages/' },
    to: { path: '^apps/' },
  }],
};
```

## Rails — packwerk

Only when the Rails app is **large enough to have internal seams worth defending**. On a small
app it is ceremony.

### Bad — a "boundary" that is a naming convention

```ruby
# apps/rails-api/app/services/billing/charge_order.rb  ❌
module Billing
  class ChargeOrder
    def call(order)
      # Reaches straight into Shipping's internals. Nothing stops this; the module
      # nesting is decoration.
      rate = Shipping::RateCalculator.new(order).internal_rate
      # ...
    end
  end
end
```

### Good — the boundary is declared and checked

```yaml
# apps/rails-api/packwerk.yml  ✅
include:
  - "app/**/*.rb"
package_paths:
  - "app/packages/*"
```

```yaml
# apps/rails-api/app/packages/billing/package.yml  ✅
enforce_dependencies: true
enforce_privacy: true
dependencies:
  - app/packages/shipping   # declared: Billing may use Shipping's PUBLIC api
```

```ruby
# apps/rails-api/app/packages/shipping/app/public/shipping/rates.rb  ✅
module Shipping
  # Everything under app/public/ is the contract. Everything else is private, and
  # packwerk fails the build when another package reaches past it.
  class Rates
    def self.for(order) = RateCalculator.new(order).call
  end
end
```

```ruby
# apps/rails-api/app/packages/billing/app/services/billing/charge_order.rb  ✅
rate = Shipping::Rates.for(order)
```

Run `bin/packwerk check` in CI. Adopt incrementally: `packwerk update-todo` records existing
violations so the rule applies to *new* code from day one — a boundary you cannot adopt
gradually is a boundary you will not adopt.

## Making it stick

- **Fail CI, don't warn.** A warning in a monorepo is a permanent resident.
- **The message must name the remedy.** "Restricted import" invites a workaround; "import from
  `@acme/ui`, the file tree is private" teaches the rule.
- **Record the debt, then hold the line.** `packwerk update-todo` / ESLint overrides let you
  enforce on new code without a big-bang migration.
- **Re-check the graph after the lint lands.** The declared dependencies were fiction until
  now; expect the first true `turbo run build --dry` to look nothing like you assumed.
