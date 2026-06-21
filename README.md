# SDH Claude Skills

**Enterprise-grade Claude Code plugin for a professional Software Development House.**

A complete, audited system of skills, agents, and hooks that transforms Claude Code into a full SDLC partner — from requirements gathering through production incident response.

## What This Is

This repository is a **Claude Code plugin** (`sdh`) that enforces enterprise development standards across the entire software development lifecycle. It is designed for teams building **Rails API (Phlex views) + React Native mobile + ReactJS Vite SPA + Next.js App Router** applications deployed on **AWS** and **Vercel**.

Instead of relying on ad-hoc prompting, this plugin provides:

- **58 skills** — 37 workflow skills (`/sdh:code-reviewer`, `/sdh:rails-architect`, …), **20 `std-*` convention skills** that auto-load by file path (e.g. `std-rails-conventions`, `std-accessibility`), plus the always-on `sdh-engineering-standards` skill
- **12 specialized agents** (4 with team lead protocols) that handle complex tasks with constrained tool access
- **6 pre-defined agent team templates** for coordinated multi-agent work
- **Quality-gate hooks** (PreToolUse blockers + a single PostToolUse dispatcher) with **wrapper-agnostic framework detection**
- A core **`sdh-engineering-standards`** skill carrying the stack + library conventions

## Install

```bash
# Add this repo as a marketplace, then install the plugin
/plugin marketplace add Kaakati/sdh-claude-skills
/plugin install sdh@sdh-claude-skills

# Or test locally without installing
claude --plugin-dir /path/to/sdh-claude-skills
```

Skills are namespaced under the plugin: `/sdh:code-reviewer`, `/sdh:rails-architect`, etc.
Run `/plugin` to manage it, and `claude plugin validate .` to validate changes.

### What a plugin can't ship — add these to your project `.claude/settings.json`

A plugin cannot ship `permissions`, `env`, or `worktree` settings. Copy them from this
repo's [`.claude/settings.json`](.claude/settings.json) into your own project settings to get
the secret/build-artifact `Read` denies, the agent-teams env flag, and worktree symlinks.
See [`docs/monorepo-setup.md`](docs/monorepo-setup.md).

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

### What Convention Skills Auto-Load (wrapper-agnostic globs)

The `std-*` convention skills are path-scoped — they auto-load when you edit files matching their globs:

```
File you edit (under any wrapper)          std-* skills that auto-load
--------------------------------------     --------------------------------------
**/app/**/*.rb                           -> std-rails-conventions, std-clean-architecture
**/app/components/**/*.rb                 -> std-phlex-conventions
**/app/views/**/*.rb                      -> std-phlex-conventions, std-i18n
**/src/pages/**/*.tsx                     -> std-reactjs, std-accessibility
**/src/screens/**/*.tsx                   -> std-react-native
**/app/**/*.tsx + **/next.config.*        -> std-nextjs, std-accessibility
**/i18n/**, **/config/locales/**          -> std-i18n
**/migrations/**, **/migrate/**           -> std-database
**/*.tf, **/*.tfvars                      -> std-terraform-conventions, std-infrastructure, std-monitoring
**/*.test.*, **/*.spec.*                  -> std-testing
```

### Hook Domain-Aware Limits (wrapper-agnostic)

The PostToolUse checkers apply a 200-line limit to models and UI components (300 elsewhere),
matched by canonical structure under any wrapper:

| Canonical path (any wrapper) | File Limit | Rationale |
|------------------------------|-----------|-----------|
| `**/app/models/**/*.rb` | 200 lines | Rails models |
| `**/src/screens/**`, `**/src/pages/**`, `**/src/components/**` | 200 lines | Frontend components |
| `**/app/components/**/*.rb`, `**/app/views/**/*.rb` | 200 lines | Phlex components |
| `**/app/**/*.tsx` (Next.js app router) | 200 lines | Next.js components |
| All other source files | 300 lines | General limit per the std-code-standards skill |

### Recommended Monorepo Structure

The structure below is the **recommended** convention, not a requirement — detection works under any wrapper name. It is shown so teams have a sensible default.

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
│   │   ├── components/               # UI components
│   │   ├── stores/                   # Zustand stores
│   │   ├── api/                      # API client + query hooks
│   │   ├── router/                   # React Router config
│   │   ├── i18n/                     # i18n config
│   │   └── lib/                      # Utilities (cn, etc.)
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
| Web (SPA) | ReactJS + Vite | Single-page app with React Router |
| Web (SSR) | Next.js (App Router) | Server Components, server actions, ISR/SSG |
| Web Styling | Tailwind CSS | Utility-first CSS for all web frontends |
| Web Animations | Framer Motion | Page transitions, animated lists |
| Web Charts | ApexCharts | Revenue charts, donut charts, dashboards |
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
│   ├── plugin.json                   (manifest: name "sdh", version 1.0.0)
│   └── marketplace.json              (single-plugin marketplace, source "./")
├── skills/                        ← 58 skills total (20 std-* convention skills below)
│   ├── sdh-engineering-standards/    (always-on stack + library conventions)
│   ├── std-code-standards/           (path-scoped: all source files)
│   ├── std-security/                 (path-scoped: all source files)
│   ├── std-testing/
│   ├── std-clean-architecture/
│   ├── std-rails-conventions/
│   ├── std-phlex-conventions/        (**/app/components/**, **/app/views/**)
│   ├── std-react-native/
│   ├── std-reactjs/                  (**/src/pages/**)
│   ├── std-nextjs/                   (**/app/**/*.tsx + next.config.*)
│   ├── std-accessibility/            (web/next/frontend/mobile components)
│   ├── std-design-system/            (styles/**, components/ui/**, tailwind.config.*)
│   ├── std-api-design/
│   ├── std-database/
│   ├── std-error-handling/
│   ├── std-git-workflow/
│   ├── std-infrastructure/
│   ├── std-terraform-conventions/    (**/*.tf, **/*.tfvars)
│   ├── std-monitoring/
│   ├── std-i18n/
│   ├── std-agent-teams/              (always loaded — no path glob)
│   └── … (37 workflow skills, see below)
├── agents/                        ← 12 specialized agents (bundled in the plugin)
│   ├── requirements-consultant.md    (Opus, discovery)
│   ├── architecture-advisor.md       (Opus, plan mode)
│   ├── clean-architecture.md         (Opus, plan mode)
│   ├── code-reviewer.md              (Sonnet, review)
│   ├── security-auditor.md           (Sonnet, audit)
│   ├── test-generator.md             (Sonnet, testing)
│   ├── devops-engineer.md            (Sonnet, infra)
│   ├── refactor-specialist.md        (Opus, refactoring)
│   ├── incident-responder.md         (Opus, operations)
│   ├── phlex-developer.md            (Sonnet, Phlex + Atomic Design)
│   ├── design-system-architect.md    (Opus, plan mode, design tokens + components)
│   └── design-critique.md            (Opus, plan mode, visual quality review)
├── skills/                        ← 37 workflow slash-command skills (/sdh:<name>)
│   ├── api-designer/
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
│   ├── nextjs-dev/
│   ├── onboarding/
│   ├── performance-profiler/
│   ├── phlex-dev/                    (Phlex view components, patterns, examples)
│   ├── rails-architect/
│   ├── react-best-practices/         (57 React/Next.js perf rules)
│   ├── react-native-best-practices/  (35+ React Native perf rules)
│   ├── react-native-dev/
│   ├── reactjs-dev/
│   ├── requirements-consultant/
│   ├── security-auditor/
│   ├── sprint-planner/
│   ├── technical-rfc/
│   ├── terraform/                    (47 Terraform IaC rules, 9 categories)
│   ├── test-generator/
│   ├── theming/                      (Design tokens, dark mode, presets)
│   ├── web-design-guidelines/        (100+ accessibility/UX rules)
│   ├── brand-identity/               (Brand archetypes, color system, brand book)
│   ├── ui-ux-patterns/               (Screen patterns, heuristic evaluation)
│   ├── marketing-assets/             (Ad specs, email templates, landing pages)
│   ├── figma-handoff/                (Auto Layout mapping, design-to-code)
│   ├── design-critique/              (Visual quality review → agent)
│   ├── design-to-code/               (Design translation → agent)
│   └── accessibility-auditor/        (WCAG 2.2 AA audit, ARIA patterns)
├── hooks/                         ← 15 automation scripts + hooks.json (wired via ${CLAUDE_PLUGIN_ROOT})
│   ├── security-scan.py              (PreToolUse: blocks secrets)
│   ├── dangerous-command-blocker.py  (PreToolUse: blocks destructive cmds)
│   ├── pre-commit-check.py           (PreToolUse: validates commits)
│   ├── migration-validator.py        (PreToolUse: validates migrations)
│   ├── deployment-gate.py            (PreToolUse: deployment confirmation)
│   ├── run-python.sh                 (Cross-platform Python 3 launcher)
│   ├── auto-format.py                (PostToolUse: formats code)
│   ├── test-runner.py                (PostToolUse: reminds to test)
│   ├── atomic-design-checker.py      (PostToolUse: validates component hierarchy)
│   ├── terraform-checker.py          (PostToolUse: validates .tf conventions)
│   ├── design-token-checker.py       (PostToolUse: validates design token usage)
│   ├── audit-logger.py               (PostToolUse: compliance logging)
│   ├── vague-request-detector.py     (UserPromptSubmit: catches ambiguity)
│   ├── teammate-idle-checker.py      (TeammateIdle: validates deliverables)
│   ├── task-completed-checker.py     (TaskCompleted: validates completion)
│   ├── team-task-validator.py        (TaskCompleted: lint/format check)
│   ├── hooks.json                    (hook wiring — commands use ${CLAUDE_PLUGIN_ROOT})
│   └── tests/
│       └── run-all.py                (Hook test harness)
└── .claude/settings.json          ← Reference settings consumers copy (permissions/env/worktree)
```

### Lifecycle Hooks

Every action Claude takes passes through deterministic quality gates:

| Event | Hook | What It Does |
|-------|------|-------------|
| **Before editing files** | `security-scan.py` | Blocks writes to protected files, detects hardcoded secrets |
| **Before writing migrations** | `migration-validator.py` | Validates reversibility, checks for raw SQL injection, warns on destructive ops |
| **Before running commands** | `dangerous-command-blocker.py` | Blocks `rm -rf`, `DROP TABLE`, privilege escalation |
| **Before deployments** | `deployment-gate.py` | Requires confirmation for `git push main`, `terraform apply`, `vercel deploy` |
| **Before git commits** | `pre-commit-check.py` | Validates conventional commit format, blocks force pushes |
| **After editing files** | `auto-format.py` | Runs rubocop, prettier, terraform fmt |
| **After editing files** | `test-runner.py` | Reminds to run corresponding tests |
| **After editing files** | Code quality checker | 30-line functions, 4-param max, 3-level nesting, domain-aware file limits |
| **After editing files** | Error handling checker | Empty catch blocks, `rescue Exception` detection |
| **After editing files** | Test coverage checker | Missing test file detection |
| **After editing files** | Clean architecture checker | Layer boundary violation detection |
| **After editing files** | i18n checker | Hardcoded user-facing string detection |
| **After editing files** | `atomic-design-checker.py` | Validates component hierarchy, composition rules, naming |
| **After editing files** | `terraform-checker.py` | Validates .tf file conventions (secrets, naming, tags, providers) |
| **After editing files** | `design-token-checker.py` | Validates design token usage (colors, spacing, focus, motion) |
| **After any tool use** | `audit-logger.py` | Logs execution to JSON-lines for compliance |
| **Before processing input** | `vague-request-detector.py` | Suggests requirements-consultant for ambiguous requests |
| **On session start** | Environment check prompt | Git repo, branch, working tree status |
| **When subagent starts** | Tech stack prompt | Injects full tech stack and team context |
| **When teammate idles** | `teammate-idle-checker.py` | Validates actual deliverables, checks test coverage |
| **When task completes** | `task-completed-checker.py` | Validates deliverables match description, PR-ready state |
| **When task completes** | `team-task-validator.py` | Validates modified files pass linting/formatting |
| **When session ends** | Completion prompt | Validates task completion |

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
| **Feature Team** | architecture-advisor (Opus) | rails-architect, reactjs-dev/react-native-dev, test-generator, security-auditor | Full-stack features spanning backend + frontend + tests |
| **Review Team** | code-reviewer | security-auditor, clean-architecture, test-generator | Large PRs, release reviews, audit preparation |
| **Incident Team** | incident-responder (Opus) | devops-engineer, rails-architect, security-auditor | Production outages, performance degradation |
| **Refactor Team** | architecture-advisor (Opus) | refactor-specialist, test-generator, code-reviewer | Module extraction, pattern migration, dependency upgrades |
| **Infrastructure Team** | devops-engineer | security-auditor, architecture-advisor | Terraform modules, CI/CD pipelines, cloud migrations |
| **Design Team** | design-system-architect (Opus) | phlex-developer, design-critique | Design system creation, component libraries, visual consistency |

#### Quality Gate Hooks

Teams are protected by two dedicated hooks:
- **`teammate-idle-checker.py`** (TeammateIdle) — ensures teammates produce deliverables, not just research
- **`task-completed-checker.py`** (TaskCompleted) — validates deliverables match task description, checks PR-readiness
- **`team-task-validator.py`** (TaskCompleted) — validates modified files pass linting/formatting

#### Dynamic Spawning

Claude automatically suggests creating a team when:
1. Task involves 3+ layers (backend, frontend, tests, infrastructure)
2. User asks to "review", "audit", or "investigate" across multiple dimensions
3. Task description includes multiple independent deliverables
4. User explicitly asks for parallel work

### Convention Skills (Auto-Loaded by File Path)

The 20 `std-*` convention skills (the former `.claude/rules/`, now path-scoped skills) load
automatically when you edit files matching their globs:

| Skill | Triggers On | Key Standards |
|------|------------|---------------|
| `std-code-standards` | All source files | SOLID, 30-line functions, 4-param max, naming conventions |
| `std-security` | All source files | OWASP Top 10, input validation, parameterized queries |
| `std-testing` | Test/spec files + web source | AAA pattern, 80% coverage target, Vitest + RTL |
| `std-clean-architecture` | `**/app/**`, `**/src/**` (Rails/RN/web/Next) | Dependency direction, layer boundaries, violation detection |
| `std-rails-conventions` | `**/app/**/*.rb` | Models, controllers, services, Panko, Sidekiq patterns |
| `std-phlex-conventions` | `**/app/components/**/*.rb`, `**/app/views/**/*.rb` | Phlex components, Atomic Design, `class_variants`, Stimulus/Turbo |
| `std-react-native` | `**/src/screens/**`, `**/src/**/*.{ts,tsx}` (RN) | Zustand, TanStack Query, Centrifugo, component patterns |
| `std-reactjs` | `**/src/pages/**` (Vite SPA) | React Router, Tailwind CSS, Framer Motion, ApexCharts |
| `std-nextjs` | `**/app/**/*.tsx` + `next.config.*` | Server Components, server actions, ISR/SSG, Vercel |
| `std-accessibility` | web/Next/Vite/RN component files | WCAG 2.2 AA, semantic HTML, keyboard navigation, focus appearance, target size |
| `std-design-system` | `**/styles/**`, `**/components/ui/**`, `**/theme/**`, `**/app/components/**`, `**/tailwind.config.*` | Design tokens, color/typography/spacing/motion rules, component styling |
| `std-api-design` | API controllers/routes | REST conventions, error formats, pagination, versioning |
| `std-database` | Migrations, schema | Safe migrations, indexing strategy, N+1 prevention |
| `std-error-handling` | All source files | Rails rescue patterns, React Native error boundaries |
| `std-git-workflow` | Git operations | Conventional commits, branch naming, PR requirements |
| `std-infrastructure` | Terraform, Docker, CI | AWS, Vercel, Docker, cost optimization |
| `std-terraform-conventions` | `**/*.tf`, `**/*.tfvars` | HCL structure, provider pins, resource naming, required tags, security |
| `std-monitoring` | Logging, health checks | Structured logging, CloudWatch, Sentry, correlation IDs |
| `std-i18n` | Locale/translation files | Key naming, pluralization, RTL support, CI validation |
| `std-agent-teams` | All files (no glob) | Team coordination, file ownership, task sizing, worktree isolation |

### Agents

Agents are specialized Claude instances with constrained tools and focused expertise:

| Agent | Model | Mode | Specialization |
|-------|-------|------|---------------|
| `requirements-consultant` | Opus | Interactive | Discovery, feasibility, compliance, user stories, spike scoping |
| `architecture-advisor` | Opus | Plan | ADRs, quality attributes, build-vs-buy, architectural decisions |
| `clean-architecture` | Opus | Plan | Layer boundary validation, dependency direction, conformance |
| `code-reviewer` | Sonnet | Interactive | SOLID review, complexity analysis, security scan, PR review |
| `security-auditor` | Sonnet | Interactive | OWASP audit, secret scanning, SBOM, supply chain security |
| `test-generator` | Sonnet | Interactive | Test generation, AAA pattern, coverage analysis, mocking |
| `devops-engineer` | Sonnet | Interactive | CI/CD, Terraform, Docker, deployment automation, GitOps |
| `refactor-specialist` | Opus | Interactive | Code smells, Fowler's patterns, incremental refactoring |
| `incident-responder` | Opus | Interactive | Production incident diagnosis, mitigation, post-mortem |
| `phlex-developer` | Sonnet | Interactive | Phlex view components, Atomic Design, Tailwind tokens |
| `design-system-architect` | Opus | Plan | Design tokens, component spec matrices, grid systems |
| `design-critique` | Opus | Plan | Nielsen's heuristics, visual hierarchy, token compliance |

### Skills (Slash Commands)

Invoke with `/sdh:skill-name` (skills are namespaced under the plugin) for templated,
repeatable workflows. The command column below omits the `sdh:` prefix for brevity:

| Command | Routes To Agent | Description |
|---------|----------------|-------------|
| `/code-reviewer` | code-reviewer | PR review with auto-injected git diff |
| `/security-auditor` | security-auditor | OWASP audit, SBOM generation, license compliance |
| `/clean-architecture` | clean-architecture | Architecture conformance validation |
| `/test-generator` | test-generator | Generate tests with AAA pattern |
| `/requirements-consultant` | requirements-consultant | Requirements discovery, user stories, feasibility (Opus) |
| `/api-designer` | — | REST API design and review |
| `/rails-architect` | — | Rails backend architecture |
| `/react-native-dev` | — | React Native feature implementation |
| `/reactjs-dev` | — | ReactJS Vite SPA features (Tailwind, Framer Motion, ApexCharts) |
| `/nextjs-dev` | — | Next.js App Router features (Server Components, server actions) |
| `/db-migration` | — | Schema design and safe migrations |
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
| `/phlex-dev` | phlex-developer | Phlex view components with Atomic Design and Tailwind |
| `/terraform` | — | Terraform IaC best practices (47 rules, 9 categories) |
| `/theming` | — | Cross-platform design tokens, dark/light mode, presets |
| `/web-design-guidelines` | — | Web interface design review (100+ accessibility/UX rules) |
| `/brand-identity` | — | Brand archetypes, color system, typography, brand book (Opus) |
| `/ui-ux-patterns` | — | Screen patterns, heuristic evaluation, visual hierarchy |
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

The hooks require Python 3 and Bash. All Python hooks are launched via `run-python.sh`, which automatically finds `python3` (Linux/macOS) or `python` (Windows/conda) — no manual setup needed.

```bash
# Verify the launcher finds Python 3
bash hooks/run-python.sh --version

# Run the hook test harness to verify all hooks work
bash hooks/run-python.sh hooks/tests/run-all.py
```

> **Windows note**: Git for Windows includes Bash. Ensure `python` is on your PATH (the Microsoft Store stub does not count — install from python.org or use conda/pyenv-win).

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

The `audit-logger.py` hook logs every tool execution in JSON-lines format, providing a complete audit trail for compliance reviews.

## Key Design Decisions

1. **Convention skills over instructions** — The `std-*` skills are scoped to file paths and auto-loaded. This means Rails conventions only apply when editing Ruby files under `app/`, ReactJS patterns only for `src/pages/` files, Next.js patterns only for `app/**/*.tsx` files — regardless of the wrapper directory name.

2. **Agents over prompts** — Complex tasks use agents with constrained tool access and specialized system prompts. A security auditor agent can't edit files. A code reviewer has read-only access.

3. **Hooks over trust** — Quality gates are deterministic scripts, not AI judgment calls. The security scanner blocks secrets before they're written, not after review.

4. **Skills over repetition** — Common workflows are templated. A deployment always follows the same pre-flight checklist. An ADR always uses the same format.

5. **Community libraries over custom code** — The entire configuration assumes and enforces the use of established gems and npm packages (devise, pundit, pagy, react-hook-form, zod, etc.).

6. **Wrapper-agnostic detection** — Framework detection does **not** depend on directory names. Rails activates from canonical structure (`app/models/`) plus marker files (`Gemfile`), whether the code lives under `backend/`, `api/`, or the repo root. The same holds for `src/pages/` (Vite SPA), `src/screens/` (React Native), and `app/**/*.tsx` + `next.config.*` (Next.js). Path globs in the convention skills and hooks match canonical sub-paths under any wrapper — directory names are recommended examples, not requirements.

## Repository Structure

```
.
├── .claude-plugin/
│   ├── plugin.json                    # Plugin manifest (name "sdh", version 1.0.0)
│   └── marketplace.json               # Single-plugin marketplace (source "./")
├── skills/              (58 skills: 37 workflow + 20 std-* conventions + sdh-engineering-standards)
├── agents/              (12 agents, 4 with team lead protocols)
├── hooks/               (15 automation scripts + hooks.json + test harness)
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
