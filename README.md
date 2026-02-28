# SDH Claude Skills

**Enterprise-grade Claude Code configuration for a professional Software Development House.**

A complete, audited system of rules, agents, skills, and hooks that transforms Claude Code into a full SDLC partner — from requirements gathering through production incident response.

## What This Is

This repository contains a production-ready `.claude/` configuration that enforces enterprise development standards across the entire software development lifecycle. It is designed for teams building **Rails API + React Native mobile + ReactJS Vite SPA + Next.js App Router** applications deployed on **AWS** and **Vercel**.

Instead of relying on ad-hoc prompting, this system provides:

- **16 rules** that are automatically loaded based on file paths being edited
- **8 specialized agents** that handle complex tasks with constrained tool access
- **20 slash-command skills** that provide repeatable, templated workflows
- **9 hook scripts + 8 prompt hooks** that enforce quality gates on every action

## Project Directory Convention

**This is critical.** Rules, hooks, and skills use path-scoped globs to auto-load the correct conventions for each framework. Your project directories **must** follow these naming conventions for the system to work correctly:

### Required Directory Names

| Framework | Required Directory | Alternatives | Example |
|-----------|-------------------|--------------|---------|
| **Rails API** | `app/` | `lib/`, `config/`, `db/` | `app/models/user.rb` |
| **React Native** | `src/` | `mobile/`, `app/` (with `.tsx`) | `src/screens/HomeScreen.tsx` |
| **ReactJS (Vite SPA)** | `web/` | `frontend/` | `web/src/pages/Dashboard.tsx` |
| **Next.js (App Router)** | `next/` | — | `next/app/page.tsx` |

### Why This Matters

Rules are auto-loaded by file path. If you put your Vite SPA code in `client/` instead of `web/`, the ReactJS rules (`reactjs.md`, `accessibility.md`) will **not** activate. Similarly, if you put Next.js code in `webapp/` instead of `next/`, the Next.js rules will not trigger.

### Path Glob Mapping

Here is exactly which rules activate for which paths:

```
File you edit                         Rules that auto-load
─────────────────────────────────     ──────────────────────────────────────
app/**/*.rb                         → rails-conventions, clean-architecture
src/**/*.tsx                        → react-native, clean-architecture
web/**                              → reactjs, accessibility, clean-architecture
web/src/i18n/**                     → i18n
next/**                             → nextjs, accessibility, clean-architecture
next/src/i18n/**                    → i18n
config/locales/**                   → i18n
**/migrations/**                    → database
terraform/**                        → infrastructure, monitoring
**/*.test.*, **/*.spec.*            → testing
```

### PostToolUse Hook Path Awareness

The PostToolUse prompt hooks also use these paths for domain-aware limits:

| Path Pattern | File Limit | Rationale |
|--------------|-----------|-----------|
| `app/models/**` | 200 lines | Rails models per rails-conventions.md |
| `src/screens/**`, `src/components/**` | 200 lines | React Native components |
| `web/src/components/**`, `web/src/pages/**` | 200 lines | Vite SPA components per reactjs.md |
| `next/src/components/**`, `next/app/**` | 200 lines | Next.js components per nextjs.md |
| All other source files | 300 lines | General limit per code-standards.md |

### Recommended Monorepo Structure

```
your-project/
├── CLAUDE.md                         # Master config (always loaded)
├── .claude/                          # All Claude Code configuration
├── app/                              # Rails API backend
│   ├── controllers/
│   ├── models/
│   ├── serializers/
│   ├── services/
│   └── values/
├── src/                              # React Native mobile app
│   ├── domain/                       # Pure TypeScript types
│   ├── hooks/                        # TanStack Query hooks
│   ├── screens/                      # Screen components
│   ├── components/                   # Shared components
│   ├── stores/                       # Zustand stores
│   └── api/                          # API client
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
├── config/                           # Rails config
│   └── locales/                      # i18n YAML locales
├── db/
│   └── migrate/                      # Rails migrations
├── spec/                             # Rails RSpec tests
├── terraform/                        # Infrastructure as code
└── docker-compose.yml                # Local development
```

## Technology Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Backend | Ruby on Rails (API-only) | Server-side logic, shared REST APIs |
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
├── .claude/rules/                 ← 16 auto-loaded rules (path-scoped)
│   ├── code-standards.md
│   ├── security.md
│   ├── testing.md
│   ├── clean-architecture.md
│   ├── rails-conventions.md
│   ├── react-native.md
│   ├── reactjs.md                    (web/**, frontend/**)
│   ├── nextjs.md                     (next/**)
│   ├── accessibility.md              (web/**, next/**, frontend/**)
│   ├── api-design.md
│   ├── database.md
│   ├── error-handling.md
│   ├── git-workflow.md
│   ├── infrastructure.md
│   ├── monitoring.md
│   └── i18n.md
├── .claude/agents/                ← 8 specialized agents
│   ├── requirements-consultant.md    (Opus, discovery)
│   ├── architecture-advisor.md       (Opus, plan mode)
│   ├── clean-architecture.md         (Opus, plan mode)
│   ├── code-reviewer.md              (Sonnet, review)
│   ├── security-auditor.md           (Sonnet, audit)
│   ├── test-generator.md             (Sonnet, testing)
│   ├── devops-engineer.md            (Sonnet, infra)
│   └── refactor-specialist.md        (Opus, refactoring)
├── .claude/skills/                ← 20 slash-command skills
│   ├── api-designer/
│   ├── clean-architecture/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── layer-examples.md
│   ├── code-reviewer/
│   ├── compliance-auditor/
│   ├── db-migration/
│   ├── deploy/
│   ├── doc-generator/
│   ├── i18n/
│   ├── incident-response/
│   ├── onboarding/
│   ├── performance-profiler/
│   ├── rails-architect/
│   ├── react-native-dev/
│   ├── reactjs-dev/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── component-patterns.md
│   │       ├── data-patterns.md
│   │       └── ui-patterns.md
│   ├── nextjs-dev/
│   │   ├── SKILL.md
│   │   └── references/
│   │       ├── server-patterns.md
│   │       ├── client-patterns.md
│   │       └── infrastructure-patterns.md
│   ├── requirements-consultant/
│   ├── security-auditor/
│   ├── sprint-planner/
│   ├── technical-rfc/
│   └── test-generator/
├── .claude/hooks/                 ← 9 automation scripts
│   ├── security-scan.py              (PreToolUse: blocks secrets)
│   ├── dangerous-command-blocker.py  (PreToolUse: blocks destructive cmds)
│   ├── pre-commit-check.py           (PreToolUse: validates commits)
│   ├── migration-validator.py        (PreToolUse: validates migrations)
│   ├── deployment-gate.py            (PreToolUse: deployment confirmation)
│   ├── run-python.sh                 (Cross-platform Python 3 launcher)
│   ├── auto-format.py                (PostToolUse: formats code)
│   ├── test-runner.py                (PostToolUse: reminds to test)
│   ├── audit-logger.py               (PostToolUse: compliance logging)
│   ├── vague-request-detector.py     (UserPromptSubmit: catches ambiguity)
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
| **After editing files** | Code quality prompt | 30-line functions, 4-param max, 3-level nesting, domain-aware file limits |
| **After editing files** | Error handling prompt | Empty catch blocks, `rescue Exception` detection |
| **After editing files** | Test coverage prompt | Missing test file detection |
| **After editing files** | Clean architecture prompt | Layer boundary violation detection |
| **After editing files** | i18n prompt | Hardcoded user-facing string detection |
| **After any tool use** | `audit-logger.py` | Logs execution to JSON-lines for compliance |
| **Before processing input** | `vague-request-detector.py` | Suggests requirements-consultant for ambiguous requests |
| **On session start** | Environment check prompt | Git repo, branch, working tree status |
| **When subagent starts** | Tech stack prompt | Injects full tech stack context |
| **When session ends** | Completion prompt | Validates task completion |

### Rules (Auto-Loaded by File Path)

Rules are loaded automatically when you edit files matching their `paths` globs:

| Rule | Triggers On | Key Standards |
|------|------------|---------------|
| `code-standards.md` | All source files | SOLID, 30-line functions, 4-param max, naming conventions |
| `security.md` | All source files | OWASP Top 10, input validation, parameterized queries |
| `testing.md` | Test/spec files + web source | AAA pattern, 80% coverage target, Vitest + RTL |
| `clean-architecture.md` | `app/**`, `src/**`, `web/**`, `next/**` | Dependency direction, layer boundaries, violation detection |
| `rails-conventions.md` | `app/**/*.rb` | Models, controllers, services, Panko, Sidekiq patterns |
| `react-native.md` | `src/**/*.{ts,tsx}` | Zustand, TanStack Query, Centrifugo, component patterns |
| `reactjs.md` | `web/**`, `frontend/**` | React Router, Tailwind CSS, Framer Motion, ApexCharts |
| `nextjs.md` | `next/**` | Server Components, server actions, ISR/SSG, Vercel |
| `accessibility.md` | `web/**`, `next/**`, `frontend/**` | WCAG 2.1 AA, semantic HTML, keyboard navigation |
| `api-design.md` | API controllers/routes | REST conventions, error formats, pagination, versioning |
| `database.md` | Migrations, schema | Safe migrations, indexing strategy, N+1 prevention |
| `error-handling.md` | All source files | Rails rescue patterns, React Native error boundaries |
| `git-workflow.md` | Git operations | Conventional commits, branch naming, PR requirements |
| `infrastructure.md` | Terraform, Docker, CI | AWS, Vercel, Docker, cost optimization |
| `monitoring.md` | Logging, health checks | Structured logging, CloudWatch, Sentry, correlation IDs |
| `i18n.md` | Locale/translation files | Key naming, pluralization, RTL support, CI validation |

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
| `/deploy` | — | Deployment with pre-flight checks, canary/blue-green |
| `/doc-generator` | — | ADRs, runbooks, specs, retrospectives, change management |
| `/i18n` | — | Rails + React Native + Vite SPA + Next.js internationalization |
| `/compliance-auditor` | — | SOC2, HIPAA, PCI-DSS, GDPR auditing |
| `/sprint-planner` | — | Sprint planning, estimation, velocity tracking |
| `/technical-rfc` | — | RFC proposals for significant changes |
| `/onboarding` | — | Developer setup guides |
| `/incident-response` | — | Production incident diagnosis, chaos engineering (Opus) |

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
mkdir -p app/          # Rails API backend
mkdir -p src/          # React Native mobile
mkdir -p web/src/      # ReactJS Vite SPA  (NOT "client/", NOT "frontend/src/")
mkdir -p next/app/     # Next.js App Router (NOT "webapp/", NOT "ssr/")
```

If you use `frontend/` instead of `web/`, the ReactJS and accessibility rules will still trigger (both paths are configured). But `next/` has no alternative — it must be `next/`.

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
/reactjs-dev            # Build a Vite SPA feature
/nextjs-dev             # Build a Next.js feature
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

6. **Directory naming is a contract** — `web/` means Vite SPA, `next/` means Next.js, `src/` means React Native. This is not arbitrary — path globs in rules, hooks, and skills depend on these exact directory names.

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
    ├── agents/          (8 agents)
    ├── skills/          (20 skills, each with SKILL.md + references/)
    ├── rules/           (16 rule files)
    └── hooks/           (9 automation scripts + test harness)
```

## Contributing

1. Follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
2. Branch naming: `feature/TICKET-ID-description`
3. PRs under 400 lines changed
4. Squash merge to main

## License

This configuration is provided as-is for teams using Claude Code with Rails + React Native + ReactJS + Next.js projects. Adapt the rules, agents, and skills to match your tech stack and standards.
