# Versioning & Release — one version in, many artifacts out

Load-bearing rules restated (hold even if you read nothing else):

1. **Single lockfile; one version of React/TypeScript/ESLint across the repo.**
2. **A divergent pin is fine when deliberate and documented; fatal when accidental.**
3. **Release per app, not per repo.** Deploy on affected-path detection, never "anything merged."

---

## One version policy

Divergent versions of shared dependencies are the **second-biggest source of monorepo pain
after missing boundaries**, and the reason is mechanical rather than aesthetic: two copies of
React in one bundle is not "slightly bigger," it is a runtime error (`Invalid hook call`). Two
TypeScript versions means the types a package publishes are not the types its consumer reads.

### Bad — drift nobody chose

```json
// apps/web/package.json        { "react": "^18.2.0" }
// apps/admin/package.json      { "react": "^18.3.1" }
// packages/ui/package.json     { "react": "^17.0.2" }   ❌ peer? dep? nobody remembers
```

`packages/ui` now pulls its own React into every consumer's bundle. It works in dev, and fails
in a way that looks like a hooks bug.

### Good — one version, enforced

```yaml
# pnpm-workspace.yaml  ✅
packages:
  - "apps/*"
  - "packages/*"
  - "tooling/*"

catalog:
  react: 18.3.1
  react-dom: 18.3.1
  typescript: 5.6.3
```

```json
// packages/ui/package.json  ✅
{
  "name": "@acme/ui",
  // A shared UI package must PEER-depend on React: it uses the host's copy rather
  // than bringing its own. This is the single most common monorepo bundle bug.
  "peerDependencies": { "react": "catalog:" },
  "devDependencies": { "react": "catalog:", "typescript": "catalog:" }
}
```

Enforce it so it cannot regress:

```json
// package.json (root)  ✅  a hard stop, not a convention
{
  "pnpm": {
    "overrides": { "react": "18.3.1", "react-dom": "18.3.1" }
  }
}
```

```bash
pnpm dedupe --check      # CI: fails when a duplicate version sneaks in
```

**One lockfile.** Multiple lockfiles mean multiple resolution universes; the whole point is
that a single resolution is shared.

## The React Native exception

**React Native routinely forces a genuine pin** — its version couples to a specific React, a
specific Metro, and native module ABIs. This is the case the one-version policy must bend for,
and bending deliberately is the difference between an isolated pin and a landmine.

```json
// apps/mobile/package.json  ✅ deliberate, isolated, documented
{
  "name": "@acme/mobile",
  "dependencies": {
    "react": "18.3.1",
    "react-native": "0.76.5"
  }
}
```

```md
<!-- apps/mobile/DEPENDENCIES.md  ✅ the "why", where the next person will look -->
# Pinned dependencies

`react-native` 0.76.5 pins `react` to exactly 18.3.1 (RN ships against one React release).
This currently MATCHES the catalog, so nothing is isolated today.

**If the catalog moves ahead of what RN supports:** do NOT bump the catalog for mobile's sake
and do NOT let mobile float. Add `react` to `pnpm.overrides` scoped to `@acme/mobile` and
record the RN release that unblocks the upgrade. Shared packages consumed by mobile must
peer-depend on React so they follow the host.
```

The rule: **isolate the pin to the one app, never to a shared package**, and write down what
would let you remove it. A pin without an exit condition is permanent.

## Release per app, not per repo

A repo-wide version number is meaningless the moment two apps ship on different days — which
is immediately.

```
rails-api/v1.4.0        # tag the deployable, not the repo
web/v2.11.0
mobile/v3.0.1
```

```bash
git tag rails-api/v1.4.0 && git push origin rails-api/v1.4.0
```

For **published packages**, use Changesets — it computes the version bumps and the dependent
cascade so you don't:

```bash
pnpm changeset            # author writes intent at PR time, in the PR
pnpm changeset version    # CI: applies bumps + updates dependents + writes CHANGELOGs
pnpm changeset publish
```

```md
<!-- .changeset/olive-pugs-repeat.md — written by the author, reviewed with the diff -->
---
"@acme/api-client": minor
---

Add `cancelOrder`. `@acme/web` and `@acme/mobile` bump automatically as dependents.
```

The value is that **intent is captured in the PR that made the change**, by the person who knows
it — not reconstructed at release time from commit messages.

## Deploy on affected paths, not on merge

### Bad — every merge deploys everything

```yaml
# ❌ a README fix redeploys the API, the web app, and cuts a mobile build
on:
  push:
    branches: [main]
jobs:
  deploy-all:
    steps:
      - run: ./deploy-rails.sh && ./deploy-web.sh
```

Beyond waste, this destroys the signal: when everything deploys constantly, "what shipped?" has
no answer, and a rollback rolls back unrelated work.

### Good — the deployable decides

```yaml
# .github/workflows/deploy.yml  ✅
on:
  push:
    branches: [main]

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      rails: ${{ steps.f.outputs.rails }}
      web: ${{ steps.f.outputs.web }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: f
        with:
          filters: |
            rails:
              - 'apps/rails-api/**'
              - 'Gemfile.lock'
            web:
              # A shared package changing MUST redeploy its consumers — this is the
              # line teams forget, and it ships a web app against a stale api-client.
              - 'apps/web/**'
              - 'packages/api-client/**'
              - 'packages/ui/**'
              - 'pnpm-lock.yaml'

  deploy-rails:
    needs: changes
    if: needs.changes.outputs.rails == 'true'
    # ... deployment-gate.py will ASK before this runs; that is layer 6 working.
    runs-on: ubuntu-latest
    steps:
      - run: ./deploy-rails.sh
```

**The dependent problem.** Path filters do not know that `apps/web` depends on
`packages/api-client`. Either enumerate consumers by hand (above — simple, drifts) or derive
the affected set from the graph (`turbo run build --filter='...[HEAD^1]' --dry=json`, correct,
more setup). Enumerating is acceptable *only* if a boundary lint keeps the real dependencies
matching the declared ones — see `references/boundaries.md`.

## Generated code and lockfile churn

Committed generated artifacts conflict on every parallel PR and teach people to resolve
conflicts by regenerating — which is how a hand-edit survives.

**Commit generated code only when consumers cannot generate it themselves.** The api-client
generated from the Rails schema is the interesting case: commit it (mobile CI should not need a
running Rails), but generate it in CI and **fail if the committed output differs** — see
`references/api-contract.md`.
