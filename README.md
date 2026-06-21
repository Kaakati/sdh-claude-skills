# SDH Claude Skills

**Enterprise-grade Claude Code plugin for a professional Software Development House.**

A complete, audited system of skills, agents, and hooks that transforms Claude Code into a full SDLC partner — from requirements gathering through production incident response.

## What This Is

This repository is a **Claude Code plugin** (`sdh`) that enforces enterprise development standards across the entire software development lifecycle. It is designed for teams building **Rails API (Phlex views) + React Native mobile + ReactJS Vite SPA + Next.js App Router** applications deployed on **AWS** and **Vercel**.

Instead of relying on ad-hoc prompting, this plugin provides:

- **57 skills** — 37 workflow skills (`/sdh:code-reviewer`, `/sdh:rails-architect`, …) plus **20 `std-*` convention skills** that auto-load by file path (e.g. `std-rails-conventions`, `std-accessibility`)
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

### What Rules Auto-Load (wrapper-agnostic globs)

```
File you edit (under any wrapper)          Rules that auto-load
--------------------------------------     --------------------------------------
**/app/**/*.rb                           -> rails-conventions, clean-architecture
**/app/components/**/*.rb                 -> phlex-conventions
**/app/views/**/*.rb                      -> phlex-conventions, i18n
**/src/pages/**/*.tsx                     -> reactjs, accessibility
**/src/screens/**/*.tsx                   -> react-native
**/app/**/*.tsx + **/next.config.*        -> nextjs, accessibility
**/i18n/**, **/config/locales/**          -> i18n
**/migrations/**, **/migrate/**           -> database
**/*.tf, **/*.tfvars                      -> terraform-conventions, infrastructure, monitoring
**/*.test.*, **/*.spec.*                  -> testing
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
| All other source files | 300 lines | General limit per code-standards.md |

### Recommended Monorepo Structure

The structure below is the **recommended** convention, not a requirement — detection works under any wrapper name. It is shown so teams have a sensible default.

```
your-project/
├── CLAUDE.md                         # Master config (always loaded)
├── .claude/                          # All Claude Code configuration
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
CLAUDE.md                          ← Master configuration (loaded every session)
├── .claude/rules/                 ← 20 auto-loaded rules (path-scoped)
│   ├── code-standards.md
│   ├── security.md
│   ├── testing.md
│   ├── clean-architecture.md
│   ├── rails-conventions.md
│   ├── phlex-conventions.md          (backend/app/components/**, backend/app/views/**)
│   ├── react-native.md
│   ├── reactjs.md                    (web/**, frontend/**)
│   ├── nextjs.md                     (next/**)
│   ├── accessibility.md              (web/**, next/**, frontend/**, mobile/**)
│   ├── design-system.md              (web/src/styles/**, components/ui/**, tailwind.config.*)
│   ├── api-design.md
│   ├── database.md
│   ├── error-handling.md
│   ├── git-workflow.md
│   ├── infrastructure.md
│   ├── terraform-conventions.md      (terraform/**/*.tf, terraform/**/*.tfvars)
│   ├── monitoring.md
│   ├── i18n.md
│   └── agent-teams.md                (always loaded — no path glob)
├── .claude/agents/                ← 12 specialized agents
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
├── .claude/skills/                ← 37 slash-command skills
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
├── .claude/hooks/                 ← 15 automation scripts
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
│   └── tests/
│       └── run-all.py                (Hook test harness)
└── .claude/settings.json          ← Permissions, hooks, deny/allow lists
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

### Rules (Auto-Loaded by File Path)

Rules are loaded automatically when you edit files matching their `paths` globs:

| Rule | Triggers On | Key Standards |
|------|------------|---------------|
| `code-standards.md` | All source files | SOLID, 30-line functions, 4-param max, naming conventions |
| `security.md` | All source files | OWASP Top 10, input validation, parameterized queries |
| `testing.md` | Test/spec files + web source | AAA pattern, 80% coverage target, Vitest + RTL |
| `clean-architecture.md` | `backend/app/**`, `mobile/src/**`, `web/**`, `next/**` | Dependency direction, layer boundaries, violation detection |
| `rails-conventions.md` | `backend/app/**/*.rb` | Models, controllers, services, Panko, Sidekiq patterns |
| `phlex-conventions.md` | `backend/app/components/**/*.rb`, `backend/app/views/**/*.rb` | Phlex components, Atomic Design, `class_variants`, Stimulus/Turbo |
| `react-native.md` | `mobile/src/**/*.{ts,tsx}` | Zustand, TanStack Query, Centrifugo, component patterns |
| `reactjs.md` | `web/**`, `frontend/**` | React Router, Tailwind CSS, Framer Motion, ApexCharts |
| `nextjs.md` | `next/**` | Server Components, server actions, ISR/SSG, Vercel |
| `accessibility.md` | `web/**`, `next/**`, `frontend/**`, `mobile/**` | WCAG 2.2 AA, semantic HTML, keyboard navigation, focus appearance, target size |
| `design-system.md` | `web/src/styles/**`, `web/src/components/ui/**`, `next/src/components/ui/**`, `mobile/src/theme/**`, `backend/app/components/**`, `**/tailwind.config.*` | Design tokens, color/typography/spacing/motion rules, component styling |
| `api-design.md` | API controllers/routes | REST conventions, error formats, pagination, versioning |
| `database.md` | Migrations, schema | Safe migrations, indexing strategy, N+1 prevention |
| `error-handling.md` | All source files | Rails rescue patterns, React Native error boundaries |
| `git-workflow.md` | Git operations | Conventional commits, branch naming, PR requirements |
| `infrastructure.md` | Terraform, Docker, CI | AWS, Vercel, Docker, cost optimization |
| `terraform-conventions.md` | `terraform/**/*.tf`, `terraform/**/*.tfvars` | HCL structure, provider pins, resource naming, required tags, security |
| `monitoring.md` | Logging, health checks | Structured logging, CloudWatch, Sentry, correlation IDs |
| `i18n.md` | Locale/translation files | Key naming, pluralization, RTL support, CI validation |
| `agent-teams.md` | All files (no glob) | Team coordination, file ownership, task sizing, worktree isolation |

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

Invoke with `/skill-name` for templated, repeatable workflows:

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

### 1. Clone into your project

```bash
# Clone this repo
git clone git@github.com:Kaakati/sdh-claude-skills.git

# Copy .claude/ directory and CLAUDE.md into your project
cp -r sdh-claude-skills/.claude/ your-project/.claude/
cp sdh-claude-skills/CLAUDE.md your-project/CLAUDE.md
```

### 2. Set up your project directories

Ensure your project follows the required directory naming convention:

```bash
# Your project must use these directory names:
mkdir -p backend/app/  # Rails API backend
mkdir -p mobile/src/   # React Native mobile
mkdir -p web/src/      # ReactJS Vite SPA
mkdir -p next/app/     # Next.js App Router
```

Each directory name is a contract — path globs in rules, hooks, and skills depend on these exact names.

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
bash .claude/hooks/run-python.sh --version

# Run the hook test harness to verify all hooks work
python .claude/hooks/tests/run-all.py
```

> **Windows note**: Git for Windows includes Bash. Ensure `python` is on your PATH (the Microsoft Store stub does not count — install from python.org or use conda/pyenv-win).

### 5. Use slash commands

```
/code-reviewer          # Review your latest changes
/security-auditor       # Run OWASP security audit
/phlex-dev              # Build a Phlex view component
/reactjs-dev            # Build a Vite SPA feature
/nextjs-dev             # Build a Next.js feature
/atomic-design          # Check component hierarchy
/theming                # Design token system
/deploy                 # Start deployment workflow
/sprint-planner         # Plan your next sprint
/incident-response      # Diagnose a production issue
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

1. **Rules over instructions** — Rules are scoped to file paths and auto-loaded. This means Rails conventions only apply when editing Ruby files, ReactJS patterns only for `web/` files, Next.js patterns only for `next/` files.

2. **Agents over prompts** — Complex tasks use agents with constrained tool access and specialized system prompts. A security auditor agent can't edit files. A code reviewer has read-only access.

3. **Hooks over trust** — Quality gates are deterministic scripts, not AI judgment calls. The security scanner blocks secrets before they're written, not after review.

4. **Skills over repetition** — Common workflows are templated. A deployment always follows the same pre-flight checklist. An ADR always uses the same format.

5. **Community libraries over custom code** — The entire configuration assumes and enforces the use of established gems and npm packages (devise, pundit, pagy, react-hook-form, zod, etc.).

6. **Directory naming is a contract** — `backend/` means Rails, `mobile/` means React Native, `web/` means Vite SPA, `next/` means Next.js. This is not arbitrary — path globs in rules, hooks, and skills depend on these exact directory names.

## Repository Structure

```
.
├── CLAUDE.md                          # Master configuration
├── CLAUDE.local.md.template           # Personal override template
├── AUDIT-REPORT.md                    # SDLC v2.0 audit report
├── .gitignore
└── .claude/
    ├── settings.json                  # Permissions + hooks
    ├── managed-settings.template.json # IT admin template
    ├── agents/          (12 agents, 4 with team lead protocols)
    ├── skills/          (37 skills, each with SKILL.md + references/)
    ├── rules/           (20 rule files)
    └── hooks/           (15 automation scripts + test harness)
```

## Contributing

1. Follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
2. Branch naming: `feature/TICKET-ID-description`
3. PRs under 400 lines changed
4. Squash merge to main

## License

This configuration is provided as-is for teams using Claude Code with Rails (Phlex) + React Native + ReactJS + Next.js projects. Adapt the rules, agents, and skills to match your tech stack and standards.
