# SDH Claude Skills

**Enterprise-grade Claude Code plugin for a professional Software Development House.**

A complete, audited system of skills, agents, and hooks that transforms Claude Code into a full SDLC partner — from requirements gathering through production incident response.

## What This Is

This repository is a **Claude Code plugin** (`sdh`) that enforces enterprise development standards across the entire software development lifecycle. It is designed for teams building **Rails API (Phlex views) + React Native mobile + ReactJS Vite SPA + Next.js App Router** applications deployed on **AWS** and **Vercel**, with **Python (FastAPI/Django)** services for AI/ML and data work.

Instead of relying on ad-hoc prompting, this plugin provides:

- **73 skills** — 46 workflow skills (`/sdh:code-reviewer`, `/sdh:rails-architect`, `/sdh:python-dev`, `/sdh:access-control-designer`, `/sdh:monorepo-architect`, `/sdh:orthogonality`, …), **26 `std-*` convention skills** scoped by file path (e.g. `std-rails-conventions`, `std-fastapi`, `std-shadcn-ui`, `std-accessibility`), plus the unscoped `sdh-engineering-standards` skill (no `paths:`, so it is eligible anywhere; Claude loads it from its description)
- **14 specialized agents** (4 with team lead protocols) that handle complex tasks with constrained tool access
- **6 pre-defined agent team templates** for coordinated multi-agent work
- **Quality-gate hooks** (PreToolUse blockers, a single PostToolUse dispatcher, and two background orthogonality hooks) with **wrapper-agnostic framework detection**
- A core **`sdh-engineering-standards`** skill carrying the stack + library conventions

## Install

Current release: **`v4.0.0`**. It is a **major** release: the permission floor gains two Bash deny
rules and a `PowerShell(...)` mirror of every shell deny, and several gates now deny or ask where
they did not.

What it adds:
- **drill-down navigation as the house standard, for new and existing products**: areas in the
  global navigation, each area's sections in that area's own layout, a URL per level, and
  breadcrumbs from the API's `ancestors`, with APIs shaped to match (shallow nesting, scoped counts,
  authorization at every level)
- **one chart library per stack**: shadcn/ui's `chart` (Recharts) in Next.js, Chart.js through
  `react-chartjs-2` in the Vite SPA, and Chart.js through a Stimulus controller in Rails views.
  ApexCharts leaves the house over its licence
- application access-control design (`/access-control-designer`)
- a `nextjs-developer` agent
- relationship-first database design, and hierarchy storage
- a plan-first database-design checker that never blocks
- **early detection of non-orthogonal architecture and database elements** (`/sdh:orthogonality`):
  a second model or table for an existing concept, a second library for a concern already covered,
  and imports or writes across bounded contexts. An advisory edit-time checker and two background
  hooks never ask or deny, and the skill's scans double as a CI gate
- **shadcn/ui as the component standard for Next.js and the Vite SPA** (`std-shadcn-ui`)
- darker `--border` and `--input` tokens, so field edges reach 3:1

It also re-audits every hook against the current Claude Code hook contract, so **gate decisions
changed**:
- some commands that used to be denied now pass;
- a few new ones are denied or asked;
- the three security gates now block when Python is missing;
- the five shell gates now judge PowerShell and Monitor commands too, which reached no gate before.

Read [`CHANGELOG.md`](CHANGELOG.md#400---2026-09-11) before taking it.

**Upgrading from v3.x?** Five things; the changelog's *Upgrade steps* has the detail:
1. **Permission floor.** One deny rule you copied was malformed, so Claude Code skipped it: replace
   `Bash(rm -rf /)*` with `Bash(rm -rf /)` in your `.claude/settings.json`. Add
   `Bash(terraform apply -destroy:*)` and `Bash(tofu apply -destroy:*)` beside the destroy rules,
   and the 16 `PowerShell(...)` mirrors listed under *Required: copy the permission floor into your
   project* below. The SessionStart sentinel names each missing rule until you do.
2. **Design tokens.** If you copied the design tokens, re-copy the Tailwind v4 stylesheet from
   `theming/references/platform-integration.md`. It registers shadcn's token names as aliases of
   the house tokens and carries the darker `--border` / `--input` values (about 3.2:1; a field on a
   tinted panel still needs its own `bg-background` fill).
3. **Charts.** ApexCharts leaves the house over its licence. Move existing charts to your stack's
   library: shadcn's `chart` (Recharts) in Next.js, Chart.js through `react-chartjs-2` in the Vite
   SPA, and Chart.js through the house Stimulus controller in Rails views.
4. **Navigation and APIs.** Drill-down applies to existing products now: flatten nested global
   sidebars into areas, with each area's section nav in its own layout. `design-critique` scores
   legacy screens at full severity. APIs follow the drill-down contract: shallow nesting, a
   permission-filtered `ancestors` chain, and counts inside the caller's scope.
5. **Hook decisions.** Read the changelog's *Changed → Hook decisions* before rolling it out to a
   team. The shell gates now judge PowerShell and Monitor commands. A bare `git push` or
   `git push origin HEAD` that lands on a protected branch now asks, and a forced one is denied. MCP
   tools reach the file gates only through an anchored list of file-writing tool names, GitHub
   `push_files` included.

Orthogonality asks nothing of you. Its index is a cache in the plugin's data directory, removed
with the plugin, and nothing is written into your project unless a scan runs with `--write-report`.
`.claude/orthogonality.json` is optional: commit it when you want to declare bounded contexts or
intentional duplicates. `SDH_ORTHOGONALITY=off` turns its hooks off.

**Upgrading from v2.0.0?** Also read the v3.0.0 entry (a major), and **if
you copied the design tokens or a theme preset, re-copy them** — 13 preset contrast pairs shipped
below WCAG AA (worst 2.54:1) and were fixed in v3.0.0.

### Pin a release (recommended for a team)

Put a small marketplace file in your repo that points at a **tag**:

```json
// .claude-plugin/marketplace.json  (in YOUR repo)
{
  "name": "sdh-pinned",
  "owner": { "name": "your-team" },
  "plugins": [
    {
      "name": "sdh",
      "source": {
        "source": "github",
        "repo": "Kaakati/sdh-claude-skills",
        "ref": "v4.0.0"
      }
    }
  ]
}
```

```bash
/plugin marketplace add ./.claude-plugin
/plugin install sdh@sdh-pinned
```

`sha` is also accepted and **wins over `ref`** when both are set — use it if you want the pin to
survive a tag being moved or deleted upstream.

### Or evaluate it (floats on `main`)

```bash
/plugin marketplace add Kaakati/sdh-claude-skills
/plugin install sdh@sdh-claude-skills

# Or run it locally without installing
claude --plugin-dir /path/to/sdh-claude-skills
```

> **This form floats on `main`** — a standards change or a hook bug reaches everyone the moment
> it is pushed, with no review gate in between. Fine for trying the plugin; wrong for running a
> team on it. See [`docs/releasing.md`](docs/releasing.md) for pinning, release channels, and the
> branch-protection posture this repo holds itself to.

Skills are namespaced under the plugin: `/sdh:code-reviewer`, `/sdh:rails-architect`, etc.
Run `/plugin` to manage it, and `claude plugin validate .` to validate changes.

## ⚠️ Required: copy the permission floor into your project

**A plugin cannot ship `permissions`.** Everything else here — skills, agents, hooks — installs
and activates on its own. The innermost enforcement ring does not, and a project without it looks
fully protected while the permission layer is simply absent.

Copy the `permissions`, `env`, and `worktree` blocks from this repo's
[`.claude/settings.json`](.claude/settings.json) into your own project settings. That gives you
the secret and build-artifact `Read` denies, the agent-teams env flag, and worktree symlinks.

**v4.0.0 corrects one rule and adds 18.** `Bash(rm -rf /)*` was malformed (Claude Code drops a
malformed rule rather than guessing) and is now `Bash(rm -rf /)`. Two new Bash denies,
`Bash(terraform apply -destroy:*)` and `Bash(tofu apply -destroy:*)`, sit beside the 6 Terraform
denies v2.0.0 added. Copy all of these by hand if you have not already:

```
Bash(rm -rf /)
Bash(terraform destroy:*)           Bash(terraform state rm:*)
Bash(tofu destroy:*)                Bash(terraform state mv:*)
Bash(terraform apply -destroy:*)    Bash(terraform state push:*)
Bash(tofu apply -destroy:*)         Bash(terraform force-unlock:*)
```

**And the 16 `PowerShell(...)` mirrors**, exactly as `.claude/settings.json` lists them. A
`Bash(...)` rule never matches the PowerShell tool, and that tool is on by default on Windows: for
claude.ai and Console accounts even with Git Bash installed, and automatically without it.

```
PowerShell(sudo:*)
PowerShell(chmod 777:*)
PowerShell(Remove-Item / *)
PowerShell(Remove-Item * /)
PowerShell(Remove-Item * / *)
PowerShell(Remove-Item *:/)
PowerShell(Remove-Item *:/ *)
PowerShell(Invoke-Expression:*)
PowerShell(terraform destroy:*)
PowerShell(tofu destroy:*)
PowerShell(terraform apply -destroy:*)
PowerShell(tofu apply -destroy:*)
PowerShell(terraform state rm:*)
PowerShell(terraform state mv:*)
PowerShell(terraform state push:*)
PowerShell(terraform force-unlock:*)
```

- **How they match.** A PowerShell rule takes the same shape as a Bash rule (`:*` equals a trailing
  ` *`), a rule for a cmdlet also matches its aliases, and matching ignores case. Claude Code checks
  each command of a pipeline on its own, so `irm <url> | iex` is denied at `Invoke-Expression`, and
  so is every other `Invoke-Expression`, `fnm env | Out-String | Invoke-Expression` included. Run
  those outside Claude Code.
- **Drive roots are spelled `/` and `C:/`**, with no backslash in any rule. The
  `dangerous-command-blocker` hook covers `Remove-Item -Recurse -Force C:\`.
- **Monitor needs no mirror.** When the Monitor tool runs a command, it uses the Bash rules.

You do not have to remember this: the **SessionStart sentinel** compares your floor against the
plugin's reference on every session and names the exact rules you are missing — including when a
floor you copied earlier has gone stale. If you see `GOVERNANCE GAP` at session start, that is
this check, and it is telling the truth.

An org can make the floor non-optional instead, via managed settings — see
[`docs/org-policy.md`](docs/org-policy.md). `.claude/managed-settings.template.json` carries the
catastrophic tier: the Bash denies, the same 16 PowerShell mirrors, and `PowerShell(nc:*)` and
`PowerShell(ncat:*)`. The sentinel treats a managed floor that carries that tier as complete;
`Read(**/*secret*)` stays a project rule, and a missing one is then reported to the model as a note.
For monorepos, see [`docs/monorepo-setup.md`](docs/monorepo-setup.md).

### Configuration

The rules are universal; the specifics are yours. Everything has a working default — set nothing
and the plugin behaves exactly as documented.

| Variable | Default | What it changes |
|---|---|---|
| `SDH_PROTECTED_BRANCHES` | `main,master,develop` | Which branches a direct push or force push is gated on. Set it if your trunk is named something else — otherwise those hooks protect branches you don't have. |
| `SDH_HOOK_MAX_WARNINGS` | `20` | Lines of advisory hook output the model gets per edit. `0` shows everything — useful when you run a checker by hand. |
| `SDH_ORTHOGONALITY` | on | `off` turns off the three orthogonality hooks: the edit-time checker, the session-start index refresh, and the background watcher. |
| `SDH_ORTHOGONALITY_TOOLS` | `0` | `1` lets the background watcher run the boundary and clone tools your project already has installed (packwerk, import-linter, tach, dependency-cruiser, jscpd, squawk). None is ever installed. |
| `SDH_ORTHOGONALITY_DIR` | `$CLAUDE_PLUGIN_DATA/orthogonality` | Where the architecture index cache lives. With neither set, it goes to the temp directory. |

```bash
# a repo whose trunk is `trunk` and which also guards `staging`
export SDH_PROTECTED_BRANCHES="trunk,staging"
```

A blank value means "unset" and falls back to the defaults — it never leaves every branch
unprotected.

**Missing formatters are fine.** If `rubocop`, `prettier`, `htmlbeautifier`, `ruff`, or
`terraform` isn't installed, nothing breaks and nothing is blocked. The auto-format hook says so once
per session, names the install command, and stays quiet after that. It prefers the project's own
binary over PATH:
- `bundle exec` when `Gemfile.lock` pins it
- `node_modules/.bin`
- `.venv`

## Project Directory Convention

The system **auto-detects each framework** — your wrapper directory can be named
anything (`backend/`, `api/`, `server/`, `web/`, `frontend/`, `next/`, `mobile/`, or even
the repository root). Conventions load from each framework's own layout and marker files,
**not** from a forced top-level folder name.

### How Detection Works

Detection uses two wrapper-agnostic signals:

1. **Canonical internal structure** — each framework's own conventional sub-paths, matched
   anywhere in the tree. `app/models/*.rb` is Rails whether it lives in `backend/app/models/`,
   `api/app/models/`, or `app/models/`. `src/pages/` is a Vite SPA; `src/screens/` is React
   Native — regardless of the wrapper.
2. **On-disk project markers** — when structure alone is ambiguous (e.g. a `src/components/*.tsx`
   that could be web or mobile), the hooks walk up the tree to the nearest marker file:

   | Framework | Marker files |
   |-----------|-------------|
   | **Rails** | `Gemfile`, `config/application.rb`, `bin/rails` |
   | **Next.js** | `next.config.{js,ts,mjs,cjs}`, `"next"` in `package.json` |
   | **ReactJS (Vite)** | `vite.config.{js,ts}`, `index.html` |
   | **React Native** | `metro.config.js`, `app.json`, `"react-native"` in `package.json` |

So putting your Rails code in `api/` instead of `backend/` works fine — the Rails rules and
hooks still activate.

### What Convention Skills Are Scoped To (wrapper-agnostic globs)

The `std-*` convention skills are path-scoped — their `paths:` globs limit them to matching files.
Scoping is a gate, not a push: it decides *whether* a skill may load, and Claude loads it when the
work calls for it. Rules that must hold whether or not a skill is read are enforced by the hooks.
Which skills are eligible for which files:

```
File you edit (under any wrapper)          std-* skills scoped to it
--------------------------------------     --------------------------------------
**/app/**/*.rb                           -> std-rails-conventions, std-clean-architecture
**/app/controllers/**/*.rb                -> std-api-design, std-monitoring
**/app/components/**/*.rb                 -> std-phlex-conventions
**/app/views/**/*.rb                      -> std-phlex-conventions, std-i18n
**/app/javascript/controllers/{chart,disclosure}_controller.js, **/app/javascript/charts/** -> std-phlex-conventions
**/src/pages/**/*.tsx                     -> std-reactjs, std-accessibility
**/src/screens/**/*.tsx                   -> std-react-native
**/app/**/*.tsx + **/next.config.*        -> std-nextjs, std-accessibility
**/middleware.ts, **/proxy.ts             -> std-nextjs
**/app/**/route.ts, **/app/**/route.js    -> std-api-design
**/components.json, **/components/ui/**  -> std-shadcn-ui, std-design-system (preloaded by nextjs-developer)
**/i18n/**, **/config/locales/**          -> std-i18n
**/migrations/**, **/migrate/**, **/db/**  -> std-database (+ **/models/**, **/models.py, **/alembic/**, **/repositories/**, **/*.sql)
**/*.tf, **/*.tfvars                      -> std-terraform-conventions, std-infrastructure, std-monitoring
**/*.test.*, **/*.spec.*                  -> std-testing
**/*.py, **/pyproject.toml                -> std-python
**/app/routers/**, **/app/schemas/**      -> std-fastapi (+ **/alembic/**, shared with std-database)
**/app/routers/**/*.py, **/app/api/**/*.py -> std-api-design, std-monitoring
**/manage.py, **/views.py, **/urls.py     -> std-django
**/services/**/*.py, **/tasks/**/*.py     -> std-monitoring (+ **/views/**/*.py, **/views.py, **/viewsets.py, **/services.py, **/tasks.py)
**/models.py, **/queries/**               -> std-python-performance (with std-django and std-database on models.py)
**/ml/**, **/training/**, **/*.ipynb      -> std-python-ai-ml
```

### Hook Domain-Aware Limits (wrapper-agnostic)

The PostToolUse checkers apply a 200-line limit to models and UI components (300 elsewhere),
matched by canonical structure under any wrapper:

| Canonical path (any wrapper) | File Limit | Rationale |
|------------------------------|-----------|-----------|
| `**/app/models/**` (any source file) | 200 lines | Rails models; FastAPI models package |
| `**/models.py` (Django per-app models file) | 200 lines | Django models |
| `**/src/screens/**`, `**/src/pages/**`, `**/src/components/**` | 200 lines | Frontend components |
| `**/app/components/**/*.rb`, `**/app/views/**/*.rb` | 200 lines | Phlex components |
| `**/app/**/*.tsx` (Next.js app router) | 200 lines | Next.js components |
| All other source files | 300 lines | General limit per the std-code-standards skill |

shadcn/ui primitives the CLI owns are exempt from these limits. They live in the directory that
`components.json` names in `aliases.ui`, and the hooks do not ask for them to be split or restyled.
See [`hooks/README.md`](hooks/README.md) → *Vendored shadcn/ui primitives*.

### Recommended Monorepo Structure

The structure below is the **recommended** convention, not a requirement — detection works under any wrapper name. It is shown so teams have a sensible default.

> **Sharing code between the apps?** Once packages are shared across deployables, prefer the
> `apps/` + `packages/` + `tooling/` layout and run **`/sdh:monorepo-architect`** — it covers
> boundary enforcement, Turborepo, affected-only CI, the one-version policy, and generating a
> shared `api-client` from the Rails schema. Both layouts scope `std-*` identically
> (`apps/rails-api/app/models/user.rb` is still Rails); the flat layout below is simply the
> smaller default for repos with no shared packages.

```
your-project/
├── CLAUDE.md                         # Your project's own config (optional)
├── .claude/                          # Your project settings (permissions/env/worktree)
├── backend/                          # Rails API backend
│   ├── app/
│   │   ├── controllers/
│   │   ├── models/
│   │   ├── serializers/
│   │   ├── services/
│   │   ├── jobs/
│   │   ├── components/              # Phlex components (Atomic Design)
│   │   │   ├── base.rb              # Components::Base < Phlex::HTML
│   │   │   ├── atoms/               # Indivisible primitives
│   │   │   ├── molecules/           # Atom compositions
│   │   │   ├── organisms/           # UI sections (data-aware)
│   │   │   └── templates/           # Layout skeletons
│   │   └── views/                   # Phlex pages (data-bound)
│   │       ├── base.rb              # Views::Base < Phlex::HTML
│   │       └── articles/            # Views::Articles::Index, Show
│   ├── config/
│   │   └── locales/                  # i18n YAML locales
│   ├── db/
│   │   └── migrate/                  # Rails migrations
│   ├── lib/
│   └── spec/                         # Rails RSpec tests
├── mobile/                           # React Native mobile app
│   └── src/
│       ├── domain/                   # Pure TypeScript types
│       ├── hooks/                    # TanStack Query hooks
│       ├── screens/                  # Screen components
│       ├── components/               # Shared components
│       ├── stores/                   # Zustand stores
│       ├── api/                      # API client
│       └── i18n/                     # i18n config
├── web/                              # ReactJS Vite SPA
│   ├── src/
│   │   ├── domain/                   # Pure TypeScript types
│   │   ├── hooks/                    # TanStack Query hooks
│   │   ├── pages/                    # Page components
│   │   ├── components/               # UI components (ui/ = shadcn/ui primitives, CLI-owned)
│   │   ├── stores/                   # Zustand stores
│   │   ├── api/                      # API client + query hooks
│   │   ├── router/                   # React Router config
│   │   ├── i18n/                     # i18n config
│   │   └── lib/                      # utils.ts: cn (re-exports the cn package)
│   ├── components.json               # shadcn/ui config (style → primitive base)
│   └── tests/                        # Integration/E2E tests
├── next/                             # Next.js App Router
│   ├── app/                          # App Router pages/layouts
│   │   ├── (dashboard)/              # Route groups
│   │   ├── api/                      # Route handlers
│   │   └── layout.tsx
│   ├── src/
│   │   ├── domain/                   # Pure TypeScript types
│   │   ├── actions/                  # Server actions
│   │   ├── hooks/                    # Client-side hooks
│   │   ├── components/               # Client/Server components
│   │   ├── api/                      # Rails API client
│   │   └── i18n/                     # i18n config
│   ├── components.json               # shadcn/ui config (style → primitive base)
│   └── tests/                        # Tests
├── terraform/                        # Infrastructure as code
└── docker-compose.yml                # Local development
```

### Monorepo & large codebases

For scaling this config across a monorepo or large single-tree codebase — where to
start Claude, layering per-package `CLAUDE.md` files, excluding packages you don't
touch, blocking reads of generated/vendored code, code-intelligence plugins,
cross-package access, and worktree sparse-checkout for agent teams — see
**[docs/monorepo-setup.md](docs/monorepo-setup.md)**. Per-package `CLAUDE.md`
starter templates live in [`docs/templates/`](docs/templates/), and per-developer
overrides in [`.claude/settings.local.json.template`](.claude/settings.local.json.template).
The committed `.claude/settings.json` already denies reads of build artifacts
(`dist/`, `build/`, `.next/`, `coverage/`, `*.min.*`, `vendor/`, Rails compiled
assets) and symlinks `node_modules`/`vendor/bundle` into worktrees.

## Technology Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Backend | Ruby on Rails (API-only) | Server-side logic, shared REST APIs |
| View Layer | Phlex + `class_variants` | Object-oriented Ruby views (~1.4 Gbps rendering) |
| Serialization | Panko Serializer | High-performance JSON serialization |
| Database | PostgreSQL + PostGIS | Relational + geospatial data |
| Mobile | React Native | Cross-platform iOS/Android |
| Web (SPA) | ReactJS + Vite | Single-page app with React Router 8 |
| Web (SSR) | Next.js (App Router) | Server Components, server actions, ISR/SSG |
| Web Styling | Tailwind CSS | Utility-first CSS for all web frontends |
| Web Animations | Framer Motion | Page transitions, animated lists |
| Web UI | shadcn/ui (Base UI; Radix kept in existing packages) | Component standard for Next.js and the Vite SPA |
| Charts (Next.js) | Recharts via the shadcn/ui `chart` component | Dashboards and reports, each with a text alternative |
| Charts (Vite SPA) | Chart.js via `react-chartjs-2` | One registration module, lazy-loaded chart modules, a text alternative outside the canvas |
| Charts (Rails views) | Chart.js via a house Stimulus controller | Phlex views, not Chartkick; a caption, summary and data table outside the canvas |
| State Management | Zustand | Client-only state (never server data) |
| Data Fetching | TanStack Query | All server state and caching |
| Real-time | Centrifugo | WebSocket channels for live updates |
| Cache / Queues | Redis | Rails cache + Sidekiq background jobs |
| Cloud (Primary) | AWS | ECS Fargate, RDS, ElastiCache, S3, CloudFront |
| Cloud (Secondary) | GCP | Specific services (Maps, ML, BigQuery) |
| Cloud (Next.js) | Vercel | Primary Next.js deployment platform |
| Infrastructure | Terraform | All infrastructure as code |
| Local Dev | Docker Compose | PostgreSQL, Redis, Centrifugo, Rails |
| Web Testing | Vitest + React Testing Library | Component and hook testing |

**Philosophy**: Community libraries first — prefer proven gems and npm packages over custom implementations.

## How It Works

### Architecture Overview

```
.claude-plugin/                    ← Plugin manifests
│   ├── plugin.json                   (manifest: name "sdh", semver version — bumped every release)
│   └── marketplace.json              (single-plugin marketplace, source "./")
├── skills/                        ← 73 skills total (26 std-* convention skills below)
│   ├── sdh-engineering-standards/    (stack + library conventions, no path scope)
│   ├── std-code-standards/           (path-scoped: all source files)
│   ├── std-security/                 (path-scoped: all source files)
│   ├── std-testing/
│   ├── std-clean-architecture/
│   ├── std-rails-conventions/
│   ├── std-phlex-conventions/        (**/app/components/**, **/app/views/**, the house chart and disclosure Stimulus controllers)
│   ├── std-react-native/
│   ├── std-reactjs/                  (vite.config.*, index.html, **/src/pages/**)
│   ├── std-nextjs/                   (**/app/**/*.tsx + next.config.*, middleware.ts, proxy.ts)
│   ├── std-shadcn-ui/                (**/components.json, **/components/ui/**; preloaded by nextjs-developer)
│   ├── std-python/                   (**/*.py, pyproject.toml)
│   ├── std-fastapi/                  (**/app/routers/**, **/app/schemas/**, alembic)
│   ├── std-django/                   (manage.py, models.py, views.py, migrations)
│   ├── std-python-ai-ml/             (**/ml/**, **/training/**, *.ipynb)
│   ├── std-python-performance/       (models.py, **/queries/**, **/repositories/**)
│   ├── std-accessibility/            (web/next/frontend/mobile components)
│   ├── std-design-system/            (styles/**, components/ui/**, theme/**, tailwind.config.*, globals.css)
│   ├── std-api-design/
│   ├── std-database/                 (migrations, models, db/, alembic, *.sql)
│   ├── std-error-handling/
│   ├── std-git-workflow/
│   ├── std-infrastructure/
│   ├── std-terraform-conventions/    (**/*.tf, **/*.tfvars)
│   ├── std-monitoring/
│   ├── std-i18n/
│   ├── std-agent-teams/              (no path glob — eligible everywhere)
│   └── … (46 workflow skills, see below)
├── agents/                        ← 14 specialized agents (bundled in the plugin)
│   ├── requirements-consultant.md    (Opus, discovery)
│   ├── architecture-advisor.md       (Opus, read-only)
│   ├── monorepo-architect.md         (Opus, read-only)
│   ├── clean-architecture.md         (Opus, read-only)
│   ├── code-reviewer.md              (Sonnet, review)
│   ├── security-auditor.md           (Sonnet, audit)
│   ├── test-generator.md             (Sonnet, testing)
│   ├── devops-engineer.md            (Sonnet, infra)
│   ├── refactor-specialist.md        (Opus, refactoring)
│   ├── incident-responder.md         (Opus, operations)
│   ├── phlex-developer.md            (Sonnet, Phlex + Atomic Design)
│   ├── nextjs-developer.md           (Sonnet, Next.js UI: base-aware shadcn/ui, CASL gates; preloads std-shadcn-ui + std-nextjs)
│   ├── design-system-architect.md    (Opus, plan mode, design tokens + components)
│   └── design-critique.md            (Opus, plan mode, visual quality review)
├── skills/                        ← 46 workflow slash-command skills (/sdh:<name>)
│   ├── access-control-designer/      (application roles, permission matrix, Pundit + CASL gates)
│   ├── api-designer/
│   ├── architecture-advisor/         (→ agent)
│   ├── atomic-design/                (Atomic Design methodology, 10 rules)
│   ├── clean-architecture/
│   ├── code-reviewer/
│   ├── compliance-auditor/
│   ├── composition-patterns/         (React composition, compound components)
│   ├── db-migration/
│   ├── deploy/
│   ├── doc-generator/
│   ├── i18n/
│   ├── incident-response/
│   ├── log-search/
│   ├── mcp-advisor/
│   ├── mobile-beta-release/
│   ├── mobile-signing/
│   ├── monorepo-architect/           (→ agent)
│   ├── nextjs-dev/                   (Next.js App Router → nextjs-developer agent)
│   ├── onboarding/
│   ├── orthogonality/                (duplicate concepts, competing mechanisms, context coupling; scripts/ for scans)
│   ├── performance-profiler/
│   ├── phlex-dev/                    (Phlex view components, patterns, examples)
│   ├── python-dev/
│   ├── rails-architect/
│   ├── react-best-practices/         (57 React/Next.js perf rules)
│   ├── react-native-best-practices/  (35+ React Native perf rules)
│   ├── react-native-dev/
│   ├── reactjs-dev/
│   ├── refactor/                     (→ refactor-specialist agent)
│   ├── requirements-consultant/
│   ├── security-auditor/
│   ├── sprint-planner/
│   ├── technical-rfc/
│   ├── terraform/                    (47 Terraform IaC rules, 9 categories)
│   ├── test-generator/
│   ├── theming/                      (Design tokens, dark mode, presets)
│   ├── toolchain/
│   ├── web-design-guidelines/        (fetches rules from an upstream URL; no rules shipped)
│   ├── brand-identity/               (Brand archetypes, color system, brand book)
│   ├── ui-ux-patterns/               (Screen patterns, heuristic evaluation, role-based UX)
│   ├── marketing-assets/             (Ad specs, email templates, landing pages)
│   ├── figma-handoff/                (Auto Layout mapping, design-to-code)
│   ├── design-critique/              (Visual quality review → agent)
│   ├── design-to-code/               (Design translation → agent)
│   └── accessibility-auditor/        (WCAG 2.2 AA audit, ARIA patterns)
├── hooks/                         ← 35 hook scripts + 46 shared _*.py modules + _mechanisms.json + run-python.sh + hooks.json (wired via ${CLAUDE_PLUGIN_ROOT})
│   ├── security-scan.py              (PreToolUse, fail-closed: protected files, provider keys; asks on CI workflows)
│   ├── dangerous-command-blocker.py  (PreToolUse, fail-closed: destructive Bash, PowerShell and Monitor commands, read by a shell lexer)
│   ├── pre-commit-check.py           (PreToolUse: commit subject, force push, pushes that name no destination)
│   ├── migration-validator.py        (PreToolUse: asks on Rails/Alembic/Django migration risks)
│   ├── deployment-gate.py            (PreToolUse: deployment confirmation)
│   ├── terraform-command-gate.py     (PreToolUse, fail-closed: three-tier terraform gate)
│   ├── mcp-install-gate.py           (PreToolUse: asks before adding or approving an MCP server, shadcn mcp init included)
│   ├── run-python.sh                 (launcher: interpreter per OS, cache, --fail-closed)
│   ├── _hooklib.py                   (shared library: events, emit, run loops; re-exports _hookpaths and _hookaudit)
│   ├── _hookpaths.py                 (project-relative path matching, framework detection)
│   ├── _hookaudit.py                 (audit trail: redaction, audit dir, append)
│   ├── _protected.py                 (protected-file and provider-key tables that security-scan reads)
│   ├── _shell.py                     (shell lexer API shared by the five shell gates)
│   ├── _shellcore.py                 (POSIX lexer: subshells, $(...), if/for bodies, bash -c)
│   ├── _shellpwsh.py                 (PowerShell lexer, and the forms that run a script or write a file)
│   ├── _dangerpwsh.py                (PowerShell's destructive forms, for dangerous-command-blocker)
│   ├── _gitpush.py                   (git push parser shared by pre-commit-check and deployment-gate)
│   ├── _jsx.py                       (JSX tag/token scanner shared by four checkers)
│   ├── _teamgate.py                  (git and team-gate helpers for the three team gates)
│   ├── _testpaths.py                 (test-file candidates shared by test-runner and test-coverage-checker)
│   ├── _vendored.py                  (is_vendored_ui: shadcn/ui aliases.ui detection)
│   ├── _hooktools.py                 (project-local tool resolution for the orthogonality tool runner; never npx/dlx/uvx)
│   ├── _arch*.py                     (32 modules: the orthogonality engine: parsers, index, lock, watcher, detectors, scans)
│   ├── _mechanisms.json              (house mechanism registry: one library per concern per stack)
│   ├── auto-format.py                (PostToolUse: the project's own formatter, safe autocorrect only)
│   ├── post-edit-dispatch.py         (PostToolUse: runs the 15 advisory checkers in one process)
│   ├── test-runner.py                (PostToolUse: reminds to test)
│   ├── atomic-design-checker.py      (PostToolUse: validates component hierarchy)
│   ├── rails-routes-checker.py       (PostToolUse: unauthenticated Sidekiq::Web mount)
│   ├── terraform-checker.py          (PostToolUse: validates .tf conventions)
│   ├── design-token-checker.py       (PostToolUse: validates design token usage)
│   ├── database-design-checker.py    (PostToolUse: plan-first notice, HABTM, unindexed FKs)
│   ├── orthogonality-checker.py      (PostToolUse, dispatched: duplicate concepts, competing mechanisms, context coupling)
│   ├── orthogonality-watch.py        (PostToolUse and PostToolUseFailure, asyncRewake: installs, generators, git pulls; wakes Claude with ≤ 5 lines)
│   ├── audit-logger.py               (PostToolUse/PostToolUseFailure/PermissionDenied: redacted audit trail)
│   ├── session-start-check.py        (SessionStart: environment + GOVERNANCE GAP sentinel)
│   ├── orthogonality-index.py        (SessionStart, async: refreshes the architecture index in the background)
│   ├── vague-request-detector.py     (UserPromptSubmit: catches ambiguity)
│   ├── session-stop-summary.py       (Stop: working-tree summary for you)
│   ├── subagent-context.py           (SubagentStart: house stack for subagents)
│   ├── teammate-idle-checker.py      (TeammateIdle: untested source in the teammate's own worktree)
│   ├── task-completed-checker.py     (TaskCompleted: worktree commits, promised tests)
│   ├── team-task-validator.py        (TaskCompleted: debug statements, whitespace faults)
│   ├── hooks.json                    (hook wiring — commands use ${CLAUDE_PLUGIN_ROOT})
│   └── tests/
│       └── run-all.py                (Hook test harness)
└── .claude/settings.json          ← Reference settings consumers copy (permissions/env/worktree)
```

### Lifecycle Hooks

Every action Claude takes passes through deterministic hooks. They are all command hooks launched by
`hooks/run-python.sh`; [`hooks/README.md`](hooks/README.md) has the output contract per event and
each hook's fail stance.

| Event | Hook | What It Does |
|-------|------|-------------|
| **Before editing files** (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`, MCP file writes, GitHub `push_files` included) | `security-scan.py` | **Fail-closed.** Denies protected files (`.env*` except templates, key material, data files in `secrets/`, `credentials/`, `private/`) and provider-format keys. Asks on CI workflow edits and credential-shaped literals |
| **Before writing migrations** | `migration-validator.py` | Asks on Rails, Alembic, and Django migration risks: irreversibility, destructive forward operations, interpolated SQL. Judges the file as it will be after the edit |
| **Before running commands** (`Bash`, `PowerShell`, `Monitor`) | `dangerous-command-blocker.py` | **Fail-closed.** Denies the program that actually runs, not a quoted mention: `rm -rf` of root, home, or system paths; PowerShell's `Remove-Item -Recurse` on a drive root or home, `Format-Volume`, and a download run through `Invoke-Expression`; destructive SQL through a database client; remote Redis FLUSH; world-writable `chmod`; `curl` and `Invoke-WebRequest` uploads to external URLs; and shell writes into `.env` or key material, or carrying a live provider key |
| **Before deployments** | `deployment-gate.py` | Asks on pushes to protected branches (a bare `git push` that lands on one included) and force pushes, and on ECS, Vercel, image pushes, fastlane/EAS releases, and `gcloud … deploy` |
| **Before terraform** | `terraform-command-gate.py` | **Fail-closed** three-tier gate. **Denies** `destroy`, `apply -destroy`, `apply -auto-approve`, `state rm|mv|push`, `force-unlock`. **Asks** on `apply`. Allows the read-only surface |
| **Before adding an MCP** | `mcp-install-gate.py` | **Asks** on `claude mcp add` (showing the real scope), on `shadcn mcp init` through any runner, on writes to `.mcp.json` / `.claude.json` servers, and on settings writes that approve every project server (`enableAllProjectMcpServers: true`, a new `enabledMcpjsonServers` name). An MCP server is an instruction source, so a human picks it |
| **Before git commits** | `pre-commit-check.py` | Denies a commit whose **subject** is not a Conventional Commit, and a force push or deletion of a protected branch. Asks on a direct push, including a bare `git push` that lands on a protected branch |
| **After editing files** | `auto-format.py` | Runs the project's own rubocop (**`--autocorrect`, safe only**), prettier, htmlbeautifier, ruff format, and terraform fmt. A missing tool is announced once. Vendored shadcn primitives are skipped |
| **After editing files** | `post-edit-dispatch.py` | Runs the 15 advisory checkers below in one process, after auto-format finishes. Output reaches the model as context, capped per checker |
| ↳ | `test-runner.py` | Reminds you which tests to run (JS/TS, Rails `spec/`/`test/`, pytest mirrors) |
| ↳ | Code quality checker | 30-line functions, 4-param max, 3-level nesting, domain-aware file limits |
| ↳ | Error handling checker | Empty catch blocks, `rescue Exception`, bare `except:`/`except BaseException` |
| ↳ | Test coverage checker | Source files with no test file (JS/TS, Rails, pytest layouts) |
| ↳ | Clean architecture checker | Layer boundary violations, HTTP concerns in services |
| ↳ | i18n checker | Hardcoded user-facing text, checked per JSX text node |
| ↳ | Accessibility checker | Semantic HTML, alt text, labels, focus indicators, ARIA misuse |
| ↳ | API design checker | URL nouns, `data` wrapper, error envelope, status codes (Rails, `src/api`, FastAPI, Next.js route handlers) |
| ↳ | Monitoring checker | Sensitive data in log statements |
| ↳ | `atomic-design-checker.py` | Component hierarchy, composition rules, naming |
| ↳ | `rails-routes-checker.py` | `Sidekiq::Web` mounted without authentication |
| ↳ | `terraform-checker.py` | Secrets, naming, AWS tags (module-aware), backend, provider pins |
| ↳ | `design-token-checker.py` | Hardcoded colors, arbitrary values, unregistered tokens, focus, reduced motion |
| ↳ | `database-design-checker.py` | A plan-first notice once per session; `has_and_belongs_to_many`; unindexed foreign-key columns. Advisory — never blocks |
| ↳ | `orthogonality-checker.py` | A second model or table for an existing concept, a copied fact, a second library for a covered concern, and cross-context imports, cycles, and writes. New findings only, at most 3 lines, read from the architecture index. Advisory — never blocks |
| **After editing files or running commands** (in the background, a failed command included) | `orthogonality-watch.py` | After a package install, a generator, or a `git pull`, from Bash or PowerShell, updates the architecture index and wakes Claude with at most 5 lines, only for new findings. Never asks or denies |
| **After any tool use** (success, failure, auto-mode denial) | `audit-logger.py` | Redacted JSON-lines audit trail in `<project>/.claude/audit/`, including every gate deny and ask |
| **Before processing input** | `vague-request-detector.py` | Suggests `sdh:requirements-consultant` for underspecified requests; stays quiet on concrete ones |
| **On session start** | `session-start-check.py` | Gives the model the git state and framework area. Shows you a **GOVERNANCE GAP** when the deny floor is missing from every settings source |
| **On session start** (in the background) | `orthogonality-index.py` | Refreshes the project's architecture index, a cache in the plugin's data directory that is never written into your repo. Prints nothing |
| **When subagent starts** | `subagent-context.py` | Gives every subagent the house stack, plus team context for members of this session's team only |
| **When teammate idles** | `teammate-idle-checker.py` | Keeps a teammate working while its own worktree has untested source |
| **When a task is created** | `task-completed-checker.py` | Snapshots the task's baseline, so the completion gates judge only the task's own changes. Never blocks |
| **When task completes** | `task-completed-checker.py` | Rejects the completion when worktree changes are uncommitted or promised tests are missing |
| **When task completes** | `team-task-validator.py` | Rejects the completion over debug statements and whitespace faults in files the task touched |
| **When Claude stops responding** | `session-stop-summary.py` | Shows you the working-tree summary when it changed |

### Agent Teams

Agent teams coordinate multiple Claude Code instances for parallel work on complex tasks.

#### When to Use What

| Approach | Best For | Example |
|----------|----------|---------|
| Single Session | Sequential tasks, simple features, bug fixes | "Fix the login timeout" |
| Subagents | Focused research, parallel reads, independent queries | "Search for all usages of UserService" |
| Agent Teams | Cross-layer features, parallel review, competing hypotheses | "Build user dashboard (API + web + mobile)" |

#### Pre-defined Team Templates

| Template | Lead | Teammates | Use When |
|----------|------|-----------|----------|
| **Feature Team** | architecture-advisor (Opus) | rails-architect, reactjs-dev/nextjs-developer/react-native-dev, test-generator, security-auditor | Full-stack features spanning backend + frontend + tests |
| **Review Team** | code-reviewer | security-auditor, clean-architecture, test-generator | Large PRs, release reviews, audit preparation |
| **Incident Team** | incident-responder (Opus) | devops-engineer, rails-architect, security-auditor | Production outages, performance degradation |
| **Refactor Team** | architecture-advisor (Opus) | refactor-specialist, test-generator, code-reviewer | Module extraction, pattern migration, dependency upgrades |
| **Infrastructure Team** | devops-engineer | security-auditor, architecture-advisor | Terraform modules, CI/CD pipelines, cloud migrations |
| **Design Team** | design-system-architect (Opus) | phlex-developer, nextjs-developer, design-critique | Design system creation, component libraries, visual consistency |

#### Quality Gate Hooks

Three dedicated hooks protect teams. Each one:
- rejects with exit 2 and gives the reason on stderr;
- judges only changes it can attribute to the teammate or the task;
- gives up after 3 identical rejections, and tells you instead.

- **`teammate-idle-checker.py`** (TeammateIdle) — source changed in the teammate's own linked worktree without a test change. Read-only agents are exempt
- **`task-completed-checker.py`** (TaskCompleted) — a worktree teammate's changes must be committed, and a task that promises tests must change test files (commits count)
- **`team-task-validator.py`** (TaskCompleted) — no leftover debug statements or whitespace faults in the files the task touched

#### Dynamic Spawning

Claude automatically suggests creating a team when:
1. Task involves 3+ layers (backend, frontend, tests, infrastructure)
2. User asks to "review", "audit", or "investigate" across multiple dimensions
3. Task description includes multiple independent deliverables
4. User explicitly asks for parallel work

### Convention Skills (Scoped by File Path)

The 26 `std-*` convention skills (the former `.claude/rules/`, now path-scoped skills) are limited
by `paths:` to files matching their globs — Claude loads one when the work calls for it:

| Skill | Triggers On | Key Standards |
|------|------------|---------------|
| `std-code-standards` | All source files | SOLID, 30-line functions, 4-param max, naming conventions |
| `std-security` | All source files | OWASP Top 10, input validation, parameterized queries |
| `std-testing` | Test/spec files + web source | AAA pattern, 80% coverage target, Vitest + RTL |
| `std-clean-architecture` | `**/app/**`, `**/src/**` (Rails/RN/web/Next) | Dependency direction, layer boundaries, violation detection |
| `std-rails-conventions` | `**/app/**/*.rb` | Models, controllers, services, Panko, Sidekiq patterns |
| `std-phlex-conventions` | `**/app/components/**/*.rb`, `**/app/views/**/*.rb`, `**/app/javascript/controllers/chart_controller.js`, `**/app/javascript/controllers/disclosure_controller.js`, `**/app/javascript/charts/**` | Phlex components, Atomic Design, `class_variants`, Stimulus/Turbo, drill-down navigation, Chart.js via Stimulus |
| `std-react-native` | `**/src/screens/**`, `**/src/**/*.{ts,tsx}` (RN) | Zustand, TanStack Query, Centrifugo, component patterns, drill-down navigation (area tabs) |
| `std-reactjs` | `**/vite.config.*`, `**/index.html`, `**/src/pages/**` (Vite SPA) | React Router 8 (drill-down area layouts), Tailwind CSS, shadcn/ui primitives, Framer Motion, Chart.js via `react-chartjs-2` |
| `std-nextjs` | `**/app/**/*.tsx` + `next.config.*`, `**/middleware.ts`, `**/proxy.ts` | Server Components, server actions, ISR/SSG, drill-down navigation (a route group per area), Vercel |
| `std-shadcn-ui` | `**/components.json`, `**/components/ui/**`; preloaded by `nextjs-developer` | Base detection (Base UI by default, Radix kept), CLI safety, token aliases, Field forms, toasts, Next.js charts (`chart`, Recharts), an areas-only `AppSidebar`, the command palette, label props, WCAG 2.2 AA |
| `std-python` | `**/*.py`, `**/pyproject.toml` | src/ layout, typing, uv/ruff/mypy, models/services/controllers layering |
| `std-fastapi` | `**/app/routers/**`, `**/app/schemas/**`, alembic | Routers, Pydantic schemas, SQLAlchemy 2.0, dependency injection, Celery |
| `std-django` | `**/manage.py`, `**/models.py`, `**/views.py`, migrations | Models, DRF viewsets/serializers, services, GeoDjango/PostGIS |
| `std-python-ai-ml` | `**/ml/**`, `**/training/**`, `**/*.ipynb` | MLflow tracking, model serving, pgvector, LLM (Anthropic) integration, evals |
| `std-python-performance` | `**/models.py`, `**/queries/**`, `**/repositories/**` | N+1 prevention, bulk ops, keyset pagination, pooling, Redis caching |
| `std-accessibility` | web/Next/Vite/RN component files | WCAG 2.2 AA, semantic HTML, keyboard navigation, focus appearance, target size |
| `std-design-system` | `**/styles/**`, `**/components/ui/**`, `**/theme/**`, `**/app/components/**`, `**/tailwind.config.*`, `**/globals.css` | Design tokens, color/typography/spacing/motion rules, component styling |
| `std-api-design` | `**/app/controllers/**/*.rb`, `**/src/api/**`, `**/src/actions/**`, `**/routes/**`, `**/controllers/**`, `**/endpoints/**`; Next.js route handlers `**/app/**/route.ts`, `**/app/**/route.js`; FastAPI `**/app/routers/**/*.py`, `**/app/api/**/*.py` | REST conventions, error formats, pagination, versioning, drill-down-ready resources |
| `std-database` | `**/migrations/**`, `**/migrate/**`, `**/models/**`, `**/models.py`, `**/alembic/**`, `**/db/**`, `**/repositories/**`, `**/*.sql` | Relationships in Rails association terms, plan first (relationships → query/index plan → constraints → migration plan → verify), indexing, N+1 prevention, hierarchy storage |
| `std-error-handling` | All source files | Rails rescue patterns, React Native error boundaries |
| `std-git-workflow` | Git operations | Conventional commits, branch naming, PR requirements |
| `std-infrastructure` | Terraform, Docker, CI | AWS, Vercel, Docker, cost optimization |
| `std-terraform-conventions` | `**/*.tf`, `**/*.tfvars` | HCL structure, provider pins, resource naming, required tags, security |
| `std-monitoring` | `**/app/controllers/**/*.rb`, `**/app/jobs/**/*.rb`, `**/config/initializers/**/*.rb`, `**/*.tf`, `**/docker-compose*.yml`, `**/.github/workflows/**`; Python `**/app/routers/**/*.py`, `**/app/api/**/*.py`, `**/services/**/*.py`, `**/tasks/**/*.py`, `**/views/**/*.py`, `**/views.py`, `**/viewsets.py`, `**/services.py`, `**/tasks.py` | Structured logging, CloudWatch, Sentry, correlation IDs |
| `std-i18n` | Locale/translation files | Key naming, pluralization, RTL support, CI validation |
| `std-agent-teams` | All files (no glob) | Team coordination, file ownership, task sizing, worktree isolation |

### Agents

Agents are specialized Claude instances with constrained tools and focused expertise:

| Agent | Model | Capability | Specialization |
|-------|-------|------------|---------------|
| `architecture-advisor` | Opus | Read-only | ADRs, quality attributes, build-vs-buy, architectural decisions |
| `clean-architecture` | Opus | Read-only | Layer boundary validation, dependency direction, conformance |
| `code-reviewer` | Sonnet | Read-only | SOLID review, complexity analysis, security scan, PR review |
| `design-critique` | Opus | Read-only | Nielsen's heuristics, visual hierarchy, token compliance, per-role lens, drill-down navigation structure |
| `design-system-architect` | Opus | Read-only | Design tokens, component spec matrices, grid systems |
| `devops-engineer` | Sonnet | Read-write | CI/CD, Terraform, Docker, deployment automation, GitOps |
| `incident-responder` | Opus | Read-write | Production incident diagnosis, mitigation, post-mortem |
| `monorepo-architect` | Opus | Read-only | Monorepo layout, dependency boundaries, affected-only CI, one-version policy, per-app releases |
| `nextjs-developer` | Sonnet | Read-write | Next.js App Router UI from base-aware shadcn/ui on house tokens, shadcn `chart` (Recharts), drill-down navigation, CASL permission gates; preloads `std-shadcn-ui` + `std-nextjs` |
| `phlex-developer` | Sonnet | Read-write | Phlex view components, Atomic Design, Tailwind tokens, drill-down navigation, Chart.js charts |
| `refactor-specialist` | Opus | Read-write | Code smells, Fowler's patterns, incremental refactoring |
| `requirements-consultant` | Opus | Read-only | Discovery, feasibility, compliance, user stories, spike scoping |
| `security-auditor` | Sonnet | Read-write | OWASP audit, secret scanning, SBOM, supply chain security |
| `test-generator` | Sonnet | Read-write | Test generation, AAA pattern, coverage analysis, mocking |

### Skills (Slash Commands)

Invoke with `/sdh:skill-name` (skills are namespaced under the plugin) for templated,
repeatable workflows. The command column below omits the `sdh:` prefix for brevity:

| Command | Routes To Agent | Description |
|---------|----------------|-------------|
| `/code-reviewer` | code-reviewer | PR review with auto-injected git diff |
| `/security-auditor` | security-auditor | OWASP audit, SBOM generation, license compliance |
| `/clean-architecture` | clean-architecture | Architecture conformance validation |
| `/monorepo-architect` | monorepo-architect | Workspace layout, boundaries, Turborepo/affected-only CI, one-version policy, api-client contract (Opus) |
| `/orthogonality` | — | Duplicate concepts and tables, competing libraries, context coupling and cycles: a concept lookup before adding, scans that double as a CI gate, declarations with ADRs |
| `/mobile-signing` | — | Certificates, provisioning profiles, .p8 keys, keystores, Play App Signing, CI secrets |
| `/mobile-beta-release` | — | TestFlight + Play testing tracks, fastlane beta lanes, staged rollout |
| `/log-search` | — | CloudWatch Logs Insights, `aws logs tail`, GCP Cloud Logging (LQL), tracing a request |
| `/mcp-advisor` | — | Discover/vet MCP servers, scope choice, and the ask-before-adding gate |
| `/toolchain` | — | Linters/formatters/typecheckers/compilers, install checks, safe vs unsafe autocorrect |
| `/test-generator` | test-generator | Generate tests with AAA pattern |
| `/requirements-consultant` | requirements-consultant | Requirements discovery, user stories, feasibility (Opus) |
| `/api-designer` | — | REST API design and review, drill-down levels |
| `/access-control-designer` | — | Application roles, permission matrix, Pundit policies + CASL gates, role-lens UX — not Claude Code permission settings (Opus) |
| `/rails-architect` | — | Rails backend architecture |
| `/python-dev` | — | Python backend features: FastAPI (default) or Django+DRF, Alembic, Celery, uv/ruff/mypy/pytest ladder |
| `/react-native-dev` | — | React Native feature implementation, area tabs and drill-down navigation |
| `/reactjs-dev` | — | ReactJS Vite SPA features (Tailwind, shadcn/ui, Framer Motion, Chart.js via `react-chartjs-2`, drill-down routing) |
| `/nextjs-dev` | nextjs-developer | Next.js App Router features (Server Components, server actions, base-aware shadcn/ui on house tokens, shadcn `chart` (Recharts), drill-down navigation, CASL gates) |
| `/db-migration` | — | Schema design and safe migrations (Rails, Django, Alembic) |
| `/performance-profiler` | — | Performance investigation and optimization |
| `/deploy` | devops-engineer | Deployment with pre-flight checks, canary/blue-green (user-invoked only) |
| `/doc-generator` | — | ADRs, runbooks, specs, retrospectives, change management |
| `/i18n` | — | Rails + React Native + Vite SPA + Next.js internationalization |
| `/compliance-auditor` | — | SOC2, HIPAA, PCI-DSS, GDPR auditing |
| `/sprint-planner` | — | Sprint planning, estimation, velocity tracking |
| `/technical-rfc` | — | RFC proposals for significant changes |
| `/onboarding` | — | Developer setup guides |
| `/incident-response` | incident-responder | Production incident diagnosis, chaos engineering (Opus) |
| `/architecture-advisor` | architecture-advisor | Architectural decisions, ADRs, tech evaluation (Opus) |
| `/refactor` | refactor-specialist | Safe incremental refactoring, Fowler's patterns (Opus) |
| `/react-best-practices` | — | React/Next.js performance optimization (57 rules, 8 categories) |
| `/composition-patterns` | — | React composition patterns (compound components, context, React 19) |
| `/react-native-best-practices` | — | React Native/Expo performance best practices (35+ rules) |
| `/atomic-design` | — | Atomic Design methodology (10 rules, composition hierarchy) |
| `/phlex-dev` | phlex-developer | Phlex view components with Atomic Design and Tailwind, drill-down navigation, Chart.js charts |
| `/terraform` | — | Terraform IaC best practices (47 rules, 9 categories) |
| `/theming` | — | Cross-platform design tokens, dark/light mode, presets, the Tailwind v4 stylesheet with shadcn token aliases |
| `/web-design-guidelines` | — | Web interface design review — **fetches** rules from an unpinned upstream URL (needs WebFetch); falls back to `std-accessibility` |
| `/brand-identity` | — | Brand archetypes, color system, typography, brand book (Opus) |
| `/ui-ux-patterns` | — | Screen patterns, heuristic evaluation, visual hierarchy, the drill-down navigation standard, role-based UX (per-role states, access-management screens) |
| `/marketing-assets` | — | Ad specs (Google/Meta/TikTok/LinkedIn), email, landing pages |
| `/figma-handoff` | — | Figma Auto Layout to CSS/Tailwind, component extraction |
| `/design-critique` | design-critique | Visual quality review, heuristic scoring (Opus) |
| `/design-to-code` | design-system-architect | Design-to-code translation |
| `/accessibility-auditor` | — | WCAG 2.2 AA audit, POUR framework, ARIA patterns |

## Getting Started

### 1. Install the plugin

```bash
# Add this repo as a marketplace, then install the plugin
/plugin marketplace add Kaakati/sdh-claude-skills
/plugin install sdh@sdh-claude-skills

# Or test locally without installing (from a checkout of this repo)
claude --plugin-dir /path/to/sdh-claude-skills
```

Skills, agents, and hooks ship inside the plugin — there is nothing to copy into your
project. Skills are namespaced under the plugin (`/sdh:code-reviewer`, etc.).

### 2. Copy the settings a plugin can't ship

A plugin cannot ship `permissions`, `env`, or `worktree` settings. Copy those blocks from
this repo's [`.claude/settings.json`](.claude/settings.json) into your own project's
`.claude/settings.json` to get the secret/build-artifact `Read` denies, the agent-teams
env flag, and worktree symlinks.

Your project layout is up to you — detection is wrapper-agnostic (see
[Project Directory Convention](#project-directory-convention)). Rails works under
`backend/`, `api/`, or the repo root; the recommended monorepo tree above is a sensible
default, not a requirement.

### 3. Customize for your project

```bash
# Create your personal overrides (gitignored)
cp CLAUDE.local.md.template CLAUDE.local.md
```

Edit `CLAUDE.local.md` to set your preferences:
- Explanation style (concise vs verbose)
- Primary work area (backend, mobile, web SPA, web SSR, full-stack)
- Development environment (ports, platforms)
- Current focus area

### 4. Verify hooks work

The hooks require Python 3 and Bash. Every hook is launched through `run-python.sh`, which finds a working Python 3 and caches the interpreter; no manual setup is needed:
- **Linux/macOS:** `python3`, then `python`.
- **Windows:** `python`, then `py -3`, then `python3`.

If no Python 3 is found, the three security gates **block** their actions, and every other hook shows a non-blocking error.

```bash
# Verify the launcher finds Python 3
bash hooks/run-python.sh --version

# Run the hook test harness to verify all hooks work
bash hooks/run-python.sh hooks/tests/run-all.py
```

> **Windows note**: Git for Windows includes Bash, and the hooks need it. Without Git Bash, `bash` is missing or resolves to WSL, so no hook runs. Claude Code then turns on its PowerShell tool and registers no Bash tool, and the copied floor's `PowerShell(...)` denies are what still hold. Install Python from python.org (the `py` launcher is enough), conda, or pyenv-win. The Microsoft Store `python3` stub does not count.

### 5. Use slash commands

```
/sdh:code-reviewer          # Review your latest changes
/sdh:security-auditor       # Run OWASP security audit
/sdh:phlex-dev              # Build a Phlex view component
/sdh:reactjs-dev            # Build a Vite SPA feature
/sdh:nextjs-dev             # Build a Next.js feature
/sdh:atomic-design          # Check component hierarchy
/sdh:theming                # Design token system
/sdh:deploy                 # Start deployment workflow
/sdh:sprint-planner         # Plan your next sprint
/sdh:incident-response      # Diagnose a production issue
```

## Enterprise Governance

### For IT Administrators

Use `managed-settings.template.json` to deploy non-overridable organization policies:

- Force authentication method and org UUID
- Restrict MCP server access
- Deny access to sensitive file patterns
- Control auto-update channels
- Set environment variable overrides

### Compliance Support

The `/compliance-auditor` skill covers:
- **SOC 2** Type I & II — All 9 Trust Service Criteria (CC1-CC9)
- **HIPAA** — Administrative, Technical, and Physical Safeguards
- **PCI-DSS** — All 12 Requirements with scope reduction guidance
- **GDPR** — Data Processing Principles, Data Subject Rights, PIA templates

### Audit Trail

The `audit-logger.py` hook writes the audit trail for compliance reviews as JSON lines in
`<project>/.claude/audit/audit.log`.
- **What it records:** every tool call (successful, failed, or denied by auto mode), plus every hook
  deny or ask.
- **Redaction:** secrets are redacted before they are written.
- **Location:** the directory ignores itself with its own `.gitignore`, and a worktree writes to its
  main checkout.
- **Failures:** a write failure is announced, never left as a silent gap.

## Key Design Decisions

1. **Convention skills over instructions** — The `std-*` skills are scoped to file paths. This means Rails conventions only apply when editing Ruby files under `app/`, ReactJS patterns only for `src/pages/` files, Next.js patterns only for `app/**/*.tsx` files — regardless of the wrapper directory name.

2. **Agents over prompts** — Complex tasks use agents with constrained tool access and specialized system prompts. A security auditor agent can't edit files. A code reviewer has read-only access.

3. **Hooks over trust** — Quality gates are deterministic scripts, not AI judgment calls. The security scanner blocks secrets before they're written, not after review.

4. **Skills over repetition** — Common workflows are templated. A deployment always follows the same pre-flight checklist. An ADR always uses the same format.

5. **Community libraries over custom code** — The entire configuration assumes and enforces the use of established gems and npm packages (devise, pundit, pagy, react-hook-form, zod, etc.).

6. **Wrapper-agnostic detection** — Framework detection does **not** depend on directory names. Rails activates from canonical structure (`app/models/`) plus marker files (`Gemfile`), whether the code lives under `backend/`, `api/`, or the repo root. The same holds for `src/pages/` (Vite SPA), `src/screens/` (React Native), and `app/**/*.tsx` + `next.config.*` (Next.js). Path globs in the convention skills and hooks match canonical sub-paths under any wrapper — directory names are recommended examples, not requirements.

## Repository Structure

```
.
├── .claude-plugin/
│   ├── plugin.json                    # Plugin manifest (name "sdh", semver version)
│   └── marketplace.json               # Single-plugin marketplace (source "./")
├── skills/              (73 skills: 46 workflow + 26 std-* conventions + sdh-engineering-standards)
├── agents/              (14 agents, 4 with team lead protocols)
├── hooks/               (35 hook scripts + 46 shared _*.py modules + _mechanisms.json + run-python.sh + hooks.json + test harness)
├── CLAUDE.local.md.template           # Personal override template
├── AUDIT-REPORT.md                    # SDLC v2.0 audit report
├── .gitignore
└── .claude/
    ├── settings.json                  # Reference settings (permissions/env/worktree) consumers copy
    └── managed-settings.template.json # IT admin template
```

## Contributing

1. Follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
2. Branch naming: `feature/TICKET-ID-description`
3. PRs under 400 lines changed
4. Squash merge to main

## License

This configuration is provided as-is for teams using Claude Code with Rails (Phlex) + React Native + ReactJS + Next.js projects. Adapt the rules, agents, and skills to match your tech stack and standards.
