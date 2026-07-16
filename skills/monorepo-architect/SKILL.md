---
name: monorepo-architect
description: Monorepo architecture and management — workspace layout by deployable unit (apps/packages/tooling), dependency boundary enforcement, task orchestration and caching (Turborepo, Nx, Bazel), affected-only CI with remote cache and merge queue, one-version policy, per-app release tagging, and a generated api-client/types contract between the Rails API and its web/mobile consumers. Use this skill when someone asks about monorepo structure, workspace layout, "where should this package live", cross-package imports, module boundaries, packwerk, Turborepo or Nx setup, slow monorepo CI, affected-only builds, remote caching, merge queues, CODEOWNERS, one lockfile vs many, Changesets, or says "our monorepo is slow", "everything imports everything", or "should we use a monorepo".
agent: monorepo-architect
context: fork
model: sonnet
---

# Monorepo Architecture

A monorepo is a bet that **atomic cross-cutting change** is worth more than repo isolation. It
pays off only if two things hold: the build graph is understood by a tool, and the boundaries
are enforced by a machine. Without both, it degrades into *one giant slow repo* — all of the
coupling, none of the leverage.

Order matters below. **Tooling and boundaries cause most monorepo failures**; everything else
is tuning.

## 1. Tooling is the make-or-break decision

Use a task runner that understands the dependency graph and rebuilds/retests **only what
changed**. Without it, every PR pays for the whole repo.

| Situation | Use | Why |
|---|---|---|
| JS/TS workspaces (this stack) | **Turborepo** | Graph-aware tasks + remote cache, near-zero config |
| JS/TS, want generators + boundary lint built in | **Nx** | More power, more opinion, more upkeep |
| Polyglot **at scale** | Bazel / Pants | Hermetic, correct — **rarely worth its cost below ~50 engineers** |
| Ruby-centric, simpler | Rake + CI path filtering | No build graph to maintain |

**For a Rails + Next.js + React Native repo: Turborepo for the JS side, plus CI path filtering
for Rails.** That is the pragmatic middle ground. Reaching for Bazel below ~50 engineers is a
real error, not a cautious default — it stalls migrations halfway.

→ `references/task-orchestration.md`

## 2. Enforce boundaries explicitly

The main monorepo failure mode is **everything importing everything**, producing an undeclared
big ball of mud. Being in one repo is not permission to couple.

> **If you wouldn't allow the coupling across two repos, don't allow it inside one.**

- Each package/app **declares its dependencies**; nothing is reachable just because it is
  co-located.
- Cross-package imports go through **public entry points only** — never `../../apps/web/lib`.
- Enforce with a machine: ESLint `no-restricted-imports`, Nx module boundaries, or **packwerk**
  for boundaries *inside* a large Rails app.

→ `references/boundaries.md`

## 3. Structure by deployable unit, not by layer

```
apps/        # deployables: rails-api, web (next), mobile (rn)
packages/    # shared libs: ui, api-client, config, types
tooling/     # eslint config, tsconfig bases, generators
```

Shared code lives in `packages/` with **its own tests and its own owner**. A `packages/utils`
that accepts anything becomes a dumping ground — split by domain and give every package one
purpose.

**This layout keeps `std-*` path-scoping intact.** Detection is wrapper-agnostic: it keys on
canonical structure (`app/models`, `src/pages`, `src/screens`) plus marker files (`Gemfile`,
`next.config.*`, `vite.config.*`, `metro.config.js`) — so `apps/rails-api/app/models/user.rb`
loads the Rails conventions and `apps/web/src/pages/Dashboard.tsx` loads the Vite ones.
**Shared packages are the gap**: `packages/ui/src/components/Button.tsx` matches no framework
structure and auto-loads nothing. Give each package a `CLAUDE.md` — see
[`docs/templates/shared.CLAUDE.md`](../../docs/templates/shared.CLAUDE.md).

→ `references/workspace-layout.md`

## 4. CI must scale sublinearly with repo size

Three rules, in order of payoff:

1. **Affected-only execution** — compute what changed, run only those pipelines.
2. **Remote caching** — a build done on one machine is never repeated on another.
3. **Merge queue** — once past a few concurrent PRs. Trunk breakage in a monorepo blocks
   *everyone*, which is the cost the merge queue buys down.

Route review with **path-based CODEOWNERS**. Git performance matters earlier than teams expect:
partial clone (`--filter=blob:none`) and sparse checkout in CI.

→ `references/ci-at-scale.md`

## 5. One version policy where possible

**Single lockfile. One version of React, TypeScript, ESLint across the repo.** Divergent
versions of shared dependencies are the **second-biggest source of monorepo pain after missing
boundaries**.

Where a package genuinely must pin differently — **React Native routinely forces this** —
isolate it deliberately and **document why**. A deliberate, documented pin is fine. An
accidental one is a landmine.

→ `references/versioning-and-release.md`

## 6. Trunk-based development, small PRs

Long-lived branches hurt more in a monorepo because the trunk moves fast underneath them.
**Feature flags over feature branches.** Atomic cross-cutting changes are the monorepo's main
payoff — use them, but keep each PR reviewable.

## 7. Version and release per app, not per repo

Tag `rails-api/v1.4.0`, not one repo-wide version. Use **Changesets** for published packages.
**Deploys trigger on affected-path detection**, never "anything merged."

→ `references/versioning-and-release.md`

## The highest-value move for this stack

One Rails API with three TypeScript consumers has one dominant risk: **web and mobile drifting
from the API and from each other.** Generate a shared `packages/api-client` + `packages/types`
**from the Rails API schema** (OpenAPI or similar) so drift becomes a compile error instead of
a production bug. Then Turborepo with remote cache for the JS workspaces, and packwerk only if
the Rails app is large enough to need internal boundaries.

→ `references/api-contract.md`

## What commonly goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `packages/utils` imports half the repo | Dumping ground | Split by domain; one purpose per package |
| Constant lockfile/generated-code conflicts | Committing artifacts consumers could generate | Commit generated code **only** when consumers can't generate it |
| Clones and CI checkouts crawl | Git at scale | Partial clone + sparse checkout — **before** you think you need it |
| Quality decays uniformly | No ownership model | Every directory has an owning team (CODEOWNERS) |
| Services drift despite one repo | "Monorepo means we can skip API contracts" | Internal packages still need stable interfaces and boundary tests |

## Deep guides (read on demand, do not preload)

- Layout, what belongs in `apps/` vs `packages/` vs `tooling/`, public entry points, splitting a dumping-ground package → `references/workspace-layout.md`
- Enforcing boundaries: ESLint `no-restricted-imports`, Nx tags, packwerk for Rails → `references/boundaries.md`
- Turborepo tasks, cache inputs/outputs, remote cache, why a task is a cache miss → `references/task-orchestration.md`
- Affected-only CI, Rails path filtering, merge queue, CODEOWNERS, partial clone & sparse checkout → `references/ci-at-scale.md`
- One-version policy, the React Native pin exception, Changesets, per-app tags, deploy on affected paths → `references/versioning-and-release.md`
- Generating `api-client`/`types` from the Rails schema so web and mobile cannot drift → `references/api-contract.md`

Claude Code configuration for a large repo (CLAUDE.md layering, excludes, worktrees) is a
separate concern — see [`docs/monorepo-setup.md`](../../docs/monorepo-setup.md).
