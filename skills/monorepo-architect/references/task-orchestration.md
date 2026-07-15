# Task Orchestration & Caching — Turborepo for this stack

Load-bearing rules restated (hold even if you read nothing else):

1. **The task runner must understand the dependency graph** — otherwise every PR pays for the
   whole repo.
2. **Declare `inputs` and `outputs` honestly.** A cache that lies is worse than no cache.
3. **Bazel is rarely worth its cost below ~50 engineers.**

---

## Decision: which tool?

| Situation | Tool | Honest cost |
|---|---|---|
| JS/TS workspaces (this stack) | **Turborepo** | One config file; no code changes |
| Want generators, boundary lint, graph viz in one | **Nx** | Adopt Nx's opinions repo-wide; plugin upkeep |
| Polyglot, hermetic, huge | Bazel / Pants | Rewrite every build; a dedicated owner. **Below ~50 engineers this stalls.** |
| Ruby-centric, few JS packages | Rake + CI path filtering | Nothing to maintain, no cross-language graph |

**This stack: Turborepo for the JS workspaces + CI path filtering for Rails.** Turborepo does
not need to understand Ruby, and the Rails app is one deployable — path filtering is the whole
requirement. Do not adopt Bazel to unify them; the unification is worth less than its cost.

## Turborepo — the config that matters

```json
// turbo.json  ✅
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      // ^ = "this package's dependencies must build first". This one caret is what
      // makes the runner graph-aware instead of a glorified `npm-run-all`.
      "dependsOn": ["^build"],
      "inputs": ["src/**", "package.json", "tsconfig.json"],
      "outputs": ["dist/**", ".next/**", "!.next/cache/**"]
    },
    "test": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "tests/**", "package.json"],
      "outputs": ["coverage/**"]
    },
    "lint": {
      "inputs": ["src/**", ".eslintrc*", "package.json"]
    },
    "typecheck": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "tsconfig.json"]
    },
    "dev": {
      // Long-running: never cache, never batch.
      "cache": false,
      "persistent": true
    }
  }
}
```

Run affected-only work:

```bash
turbo run test --filter='...[origin/main]'   # changed packages AND their dependents
turbo run build --filter='@acme/web...'      # a package and everything it depends on
turbo run build --dry=json                   # what WOULD run, and why — read this before trusting it
```

## Decision: what belongs in `inputs`?

This is where caching quietly goes wrong. Both directions are real bugs.

| Mistake | Symptom | Fix |
|---|---|---|
| `inputs` too **narrow** | Cache **hit** when it should miss → stale artifacts ship | Include every file that changes the output |
| `inputs` too **wide** (e.g. `**`) | Cache always misses; the tool "doesn't work" | Exclude logs, coverage, editor files |
| `outputs` missing a dir | Task reruns, or the artifact vanishes on a cache hit | Declare every produced path |

### Bad — a cache that lies

```json
{
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["src/**"],
      "outputs": ["dist/**"]
    }
  }
}
```

Change `tsconfig.json` — a compiler-options change that alters every emitted file — and
Turborepo replays a cached `dist/`. The build is green and wrong. Then someone hits it, decides
"the cache is flaky," and adds `--force` to CI, which throws away the entire point.

### Good — inputs match reality

```json
{
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "inputs": ["src/**", "tsconfig.json", "package.json", "!**/*.test.ts"],
      "outputs": ["dist/**"]
    }
  }
}
```

`!**/*.test.ts` is deliberate: test files do not change the build output, so excluding them
turns "touched a test" into a build cache hit. That exclusion is only safe *because* `test`
declares those files in its own `inputs`.

## Remote caching — the point of the exercise

Local caching helps one machine. **Remote caching means a build done on CI is never repeated on
your laptop, and vice versa.** For a team, this is most of the payoff.

```bash
npx turbo login && npx turbo link          # Vercel-hosted
# or self-host: TURBO_API / TURBO_TOKEN / TURBO_TEAM against any compatible server
```

```yaml
# .github/workflows/ci.yml
env:
  TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
  TURBO_TEAM: ${{ vars.TURBO_TEAM }}
```

**Cache keys must not contain secrets**, and a cache shared across trust boundaries is a supply
chain surface: anyone who can write to it can hand you an artifact. Restrict write access to CI
and give local developers read-only tokens.

## Debugging "why did this rerun?"

Do not guess. The tool will tell you:

```bash
turbo run build --dry=json | jq '.tasks[] | {task, cache, hash}'
turbo run build --summarize      # writes .turbo/runs/*.json: inputs, hash, and what changed
```

A task that misses on every run almost always has a file in `inputs` that changes every run —
a log, a coverage report, a generated timestamp. A task that hits when it should not has an
input you forgot to declare.

## The Rails side

Turborepo does not orchestrate Ruby. Filter in CI on path instead — see
`references/ci-at-scale.md`. If the Rails app grows internal seams worth defending, that is a
**packwerk** question (`references/boundaries.md`), not a build-graph question.
