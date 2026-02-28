# Software Development House — Enterprise Development Standards

This repository follows enterprise-grade development standards for a professional software development house. All contributors and AI agents must adhere to these guidelines.

## Project Identity

We are a Software Development House building production systems for clients. Quality, maintainability, and security are non-negotiable. Every line of code represents our professional standard.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | Ruby on Rails | API-only mode, shared by all frontends |
| View Layer | Phlex | Object-oriented Ruby views (~1.4 Gbps rendering) |
| Serialization | Panko Serializer | High-performance JSON serialization |
| Database | PostgreSQL + PostGIS | Geospatial-enabled relational database |
| Mobile | React Native | Cross-platform iOS/Android |
| Web (SPA) | ReactJS + Vite | Single-page app with React Router |
| Web (SSR) | Next.js (App Router) | Server Components, server actions, ISR/SSG |
| Web Styling | Tailwind CSS | Utility-first CSS for all web frontends |
| State Management | Zustand | Client-only state, never server data |
| Data Fetching | TanStack Query (React Query) | All server state lives here |
| Real-time | Centrifugal (Centrifugo) | WebSocket channels for live updates |
| Caching / Queues | Redis | Rails cache backend + Sidekiq queues |
| Cloud (Primary) | AWS | ECS Fargate, RDS, ElastiCache, S3, CloudFront |
| Cloud (Secondary) | GCP | When specific GCP services are needed |
| Cloud (Next.js) | Vercel | Primary Next.js deployment platform |
| Infrastructure | Terraform | All infrastructure as code |
| Local Dev | Docker Compose | PostgreSQL, Redis, Centrifugo, Rails |
| Philosophy | Community libraries first | Prefer proven gems/packages over custom code |

### Library Preferences
- **Prefer community libraries over native/custom implementations.** If a well-maintained gem or npm package exists for the job, use it.
- Authentication: `devise` + `devise-jwt` | Authorization: `pundit`
- Pagination: `pagy` | Search: `pg_search` | Geospatial: `rgeo`, `geocoder`
- HTTP: `faraday` (Rails), `axios` (React Native + Web)
- Forms: `react-hook-form` + `zod` | Navigation: `@react-navigation/native`
- Storage: `react-native-mmkv` | Images: `react-native-fast-image`
- Views: `phlex-rails` + `class_variants` | Stimulus: `stimulus-rails`
- Web Routing: `react-router` (Vite SPA) | Web Styling: `tailwindcss` + `clsx` + `tailwind-merge`
- Web Animations: `framer-motion` | Web Charts: `react-apexcharts`
- Web Testing: `vitest` + `@testing-library/react` + `msw`
- Next.js Images: `next/image` | Next.js Navigation: `next/link`

## Git Workflow

- **Conventional Commits**: All commit messages must follow the format `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`
  - Example: `feat(auth): add JWT refresh token rotation`
- **Branch Naming**: `feature/TICKET-123-short-description`, `bugfix/TICKET-456-fix-desc`, `hotfix/TICKET-789-critical`, `release/v1.2.0`
- **PR Requirements**: Description with context, test plan, screenshots for UI changes, at least one approval
- **Merge Strategy**: Squash merge to main, rebase feature branches on target before merge
- **Protected Branches**: No direct pushes to `main`, `master`, or `develop`

@docs/git-instructions.md

## Code Standards

- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY**: Do not repeat yourself — extract shared logic into well-named utilities
- **KISS**: Keep it simple. Prefer clarity over cleverness
- **Clean Code**: Meaningful names, small functions, minimal comments (code should be self-documenting)
- **Functions**: Max 30 lines. If longer, decompose into smaller units
- **Files**: Target max 300 lines. Split when a file has multiple responsibilities

## Architecture

- **Rails Backend**: Service objects for business logic, Panko serializers for JSON, Phlex for views (Atomic Design), Sidekiq for background jobs
- **React Native Frontend**: Zustand stores for client state, TanStack Query for server data, Centrifugo for real-time
- **ReactJS (Vite SPA)**: Pages → Hooks → API Client, React Router (lazy-loaded), Tailwind CSS, Framer Motion, ApexCharts
- **Next.js (App Router)**: Server Components for data fetching, server actions for mutations, Client Components for interactivity
- **Clean Architecture**: Controllers → Services → Models (Rails) | Screens → Hooks → API Client (React Native) | Pages → Hooks → API Client (Vite) | Server Components → Server Actions → API Client (Next.js)
- **Dependency Injection**: Depend on abstractions, not concretions. Use DI containers where appropriate
- **Domain-Driven Design**: Use bounded contexts, aggregates, and value objects for complex business domains

@docs/architecture-guide.md

## Testing

- **Coverage Targets**: 80% for business logic, 60% overall minimum
- **Test Pyramid**: Unit tests (many) > Integration tests (some) > E2E tests (few)
- **Test Quality**: Follow AAA pattern (Arrange, Act, Assert). One concept per test
- **Naming**: `should [expected behavior] when [condition]`
- **CI Gate**: Tests must pass before merge. No skipping or disabling tests without a tracking ticket

## Security

- **Secrets**: Never commit secrets, API keys, or credentials. Use environment variables and secret managers
- **Input Validation**: Validate and sanitize all user inputs at system boundaries
- **SQL**: Parameterized queries only. No string concatenation for query building
- **Dependencies**: Audit dependencies regularly. No known critical vulnerabilities in production
- **OWASP**: All code must account for OWASP Top 10 risks

## CI/CD

- All PRs must pass CI pipeline (lint, test, build, security scan) before merge
- No direct pushes to main — all changes go through pull requests
- Automated deployments from main to staging, manual promotion to production
- Feature flags for incremental rollouts of significant changes

## Documentation Standards

- Documentation ships with the code — update docs in the same PR as the code change
- Every public API endpoint must have documented parameters, return types, and error codes
- Use ADR format (ADR-NNN: Title, Status, Context, Decision, Consequences) for architectural decisions — store in `docs/adr/`
- Maintain `CHANGELOG.md` following Keep a Changelog format (Added, Changed, Fixed, Deprecated, Removed, Security)
- Runbooks for operational procedures go in `docs/runbooks/` with: When to Use, Steps, Verification, Rollback, Contacts

## Rule Reference

Detailed domain-specific rules are maintained in `.claude/rules/`:

- `code-standards.md` — Naming, SOLID, function/file limits, error handling, logging
- `security.md` — OWASP, auth, input validation, secret management
- `testing.md` — Test patterns, mocking, coverage
- `git-workflow.md` — Commits, branches, PRs
- `api-design.md` — REST conventions, error formats, pagination
- `database.md` — Migrations, indexing, query optimization
- `rails-conventions.md` — Rails models, controllers, services, Panko, Sidekiq
- `react-native.md` — React Native, Zustand, TanStack Query, Centrifugo
- `reactjs.md` — ReactJS Vite SPA, React Router, Tailwind CSS, Framer Motion, ApexCharts
- `nextjs.md` — Next.js App Router, Server Components, server actions, Vercel deployment
- `infrastructure.md` — Terraform, Docker Compose, AWS, GCP, Vercel, CI/CD
- `error-handling.md` — Error handling across Rails, React Native, Sidekiq, API responses
- `monitoring.md` — Structured logging, health checks, CloudWatch alarms, Sentry
- `clean-architecture.md` — Layer separation, dependency direction, boundary violations
- `i18n.md` — Internationalization conventions, locale files, RTL support, key naming
- `accessibility.md` — WCAG 2.1 AA, semantic HTML, keyboard navigation, color contrast, ARIA
- `phlex-conventions.md` — Phlex component conventions, Atomic Design structure, `class_variants`, Stimulus/Turbo
- `terraform-conventions.md` — Terraform HCL file structure, provider constraints, resource naming, required tags, security minimums
- `agent-teams.md` — Agent team coordination, file ownership, task sizing, worktree isolation, dynamic spawning conventions

## Agents

Custom agents are available in `.claude/agents/` for specialized tasks:
- `requirements-consultant` — Partner consultant for clarifying vague requirements (Opus)
- `security-auditor` — Security vulnerability scanning and OWASP audit
- `code-reviewer` — Comprehensive code quality and PR review
- `test-generator` — Test generation and coverage improvement
- `architecture-advisor` — Architectural decisions and ADRs (Opus, plan mode)
- `devops-engineer` — CI/CD, Terraform, Docker, deployment
- `refactor-specialist` — Safe incremental refactoring (Opus)
- `clean-architecture` — Clean Architecture conformance, layer boundary validation, dependency direction enforcement (Opus, plan mode)
- `incident-responder` — Production incident diagnosis, mitigation, post-mortem, chaos engineering (Opus)
- `phlex-developer` — Phlex view components with Atomic Design, Tailwind tokens, Stimulus, Turbo

## Skills

On-demand skills available via slash commands:
- `/code-reviewer` — Code review and PR review with dynamic git diff injection (routes to code-reviewer agent)
- `/test-generator` — Generate tests with AAA pattern (routes to test-generator agent)
- `/security-auditor` — Security audit against OWASP Top 10, SBOM generation, license compliance (routes to security-auditor agent)
- `/api-designer` — REST API design and review
- `/rails-architect` — Rails backend architecture with Panko, PostGIS, Sidekiq
- `/react-native-dev` — React Native features with Zustand, TanStack, Centrifugo
- `/reactjs-dev` — ReactJS Vite SPA features with React Router, Tailwind, Framer Motion, ApexCharts
- `/nextjs-dev` — Next.js App Router features with Server Components, server actions, Vercel deployment
- `/db-migration` — Schema design and safe database migration creation
- `/performance-profiler` — Performance investigation and optimization
- `/deploy` — Deployment workflow with pre-flight checks, canary/blue-green strategies (routes to devops-engineer agent)
- `/onboarding` — Developer onboarding guides, setup docs, knowledge transfer
- `/doc-generator` — Technical documentation, ADRs, retrospectives, change management procedures (fork context)
- `/technical-rfc` — Technical RFC proposals for significant changes requiring team consensus
- `/incident-response` — Production incident diagnosis, chaos engineering, operations runbooks (routes to incident-responder agent, Opus)
- `/requirements-consultant` — Requirements discovery, user story generation, feasibility analysis (routes to requirements-consultant agent, Opus)
- `/i18n` — Internationalization for Rails, React Native, ReactJS Vite SPA, and Next.js (locales, RTL, CSS logical properties)
- `/compliance-auditor` — SOC2, HIPAA, PCI-DSS, GDPR compliance auditing and documentation
- `/clean-architecture` — Clean Architecture validation, layer boundary enforcement (routes to clean-architecture agent)
- `/sprint-planner` — Sprint planning, effort estimation, capacity planning, backlog grooming
- `/architecture-advisor` — Architectural decisions, ADRs, tech evaluation, system design (routes to architecture-advisor agent, Opus)
- `/refactor` — Safe incremental refactoring with Fowler's patterns, test-first methodology (routes to refactor-specialist agent, Opus)
- `/react-best-practices` — React/Next.js performance optimization (57 rules, 8 categories)
- `/composition-patterns` — React composition patterns (compound components, context, React 19)
- `/react-native-best-practices` — React Native/Expo performance best practices (35+ rules)
- `/web-design-guidelines` — Web interface design review (100+ accessibility/UX rules)
- `/atomic-design` — Atomic Design methodology for component hierarchy across all frontend platforms
- `/phlex-dev` — Phlex view components with Atomic Design, Tailwind, Stimulus, Turbo (routes to phlex-developer agent)
- `/theming` — Cross-platform design tokens, dark/light mode, WCAG AA contrast
- `/terraform` — Terraform IaC best practices (47 rules, 9 categories: state, security, modules, resources, variables, networking, data, compute, cost)

## Hooks (Deterministic Automation)

Active hooks in `.claude/settings.json` enforce quality at every lifecycle point:

**PreToolUse** (before tool executes):
- `security-scan.py` — Blocks writes to protected files, detects hardcoded secrets
- `dangerous-command-blocker.py` — Blocks destructive shell commands
- `pre-commit-check.py` — Validates conventional commit format, blocks force pushes
- `migration-validator.py` — Validates migration reversibility, SQL injection, destructive ops
- `deployment-gate.py` — Requires confirmation for deploys (git push main, terraform apply, vercel deploy)

**PostToolUse** (after tool completes):
- `auto-format.py` — Auto-formats edited files (rubocop, prettier, terraform fmt)
- `test-runner.py` — Reminds to run tests for modified code
- **Code quality prompt** — Enforces code-standards.md (30-line functions, 4-param max, 3-level nesting, domain-aware file limits: 200 lines for Rails models/.tsx components, 300 lines elsewhere)
- **Error handling prompt** — Enforces error-handling.md (empty catch blocks, rescue Exception)
- **Test coverage prompt** — Enforces testing.md (warns when source files lack corresponding test files)
- **Clean architecture prompt** — Enforces clean-architecture.md (layer boundary violations, dependency direction)
- **i18n prompt** — Enforces i18n.md (hardcoded user-facing strings in .tsx/.jsx/.erb files)
- **Accessibility agent hook** — Enforces accessibility.md (semantic HTML, alt text, label associations, focus indicators, ARIA misuse) — Haiku agent with Read/Grep/Glob tools, scoped to .tsx/.jsx under web/next/frontend
- **API design agent hook** — Enforces api-design.md (URL nouns, data wrapper, error format, HTTP status codes) — Haiku agent with Read/Grep/Glob tools, scoped to controllers and API routes
- **Monitoring prompt** — Enforces monitoring.md (request_id in logs, sensitive data logging) — scoped to .rb under backend/app/controllers and backend/app/jobs
- `atomic-design-checker.py` — Validates Atomic Design hierarchy (atom independence, molecule composition, organism boundaries, naming) across Phlex, ReactJS, Next.js, React Native
- `terraform-checker.py` — Validates Terraform .tf files (hardcoded secrets, snake_case naming, required tags, backend config, provider versions)
- `audit-logger.py` — Logs all tool executions for compliance (JSON-lines)

**SessionStart** (when session begins):
- Prompt hook validates development environment (git repo, branch, working tree status)

**Stop** (when Claude finishes):
- Prompt hook validates task completion

**UserPromptSubmit** (before processing):
- `vague-request-detector.py` — Suggests requirements-consultant for ambiguous inputs

**SubagentStart** (when subagent spawns):
- Prompt hook injects tech stack context and team context into all subagents

**TeammateIdle** (when a teammate goes idle):
- `teammate-idle-checker.py` — Validates teammate completed actual work, checks for uncommitted changes, verifies test coverage

**TaskCompleted** (when a task is marked complete):
- `task-completed-checker.py` — Validates deliverables match description, checks for linting errors, ensures PR-ready state
- `team-task-validator.py` — Validates modified files pass linting/formatting before allowing task completion

## Agent Teams

Agent teams coordinate multiple Claude Code instances for parallel work. Use them for complex tasks that benefit from simultaneous exploration, cross-layer implementation, or multi-dimensional review.

### When to Use What

| Approach | Best For | Example |
|----------|----------|---------|
| Single Session | Sequential tasks, simple features, bug fixes | "Fix the login timeout" |
| Subagents | Focused research, parallel reads, independent queries | "Search for all usages of UserService" |
| Agent Teams | Cross-layer features, parallel review, competing hypotheses | "Build user dashboard (API + web + mobile)" |

**Decision tree**: Use a team when the task involves 3+ layers, requires multi-dimensional review, or contains multiple independent deliverables that can be parallelized.

### Pre-defined Team Templates

Tell Claude to "use the [Template Name]" to spawn a coordinated team:

#### Feature Team (full-stack feature development)
- **Lead**: architecture-advisor (Opus, plan mode) — designs, coordinates, reviews
- **Teammates**: rails-architect (backend), reactjs-dev or react-native-dev (frontend), test-generator (tests), security-auditor (security review)
- **When**: New feature spanning backend + frontend + tests

#### Review Team (comprehensive code review)
- **Lead**: code-reviewer — coordinates review dimensions
- **Teammates**: security-auditor (security lens), clean-architecture (architecture lens), test-generator (coverage lens)
- **When**: Large PRs, release reviews, audit preparation

#### Incident Team (production incident response)
- **Lead**: incident-responder (Opus) — triage, coordinate, post-mortem
- **Teammates**: devops-engineer (infrastructure), rails-architect (app layer), security-auditor (if breach suspected)
- **When**: Production outages, performance degradation, security incidents

#### Refactor Team (large-scale refactoring)
- **Lead**: architecture-advisor (Opus, plan mode) — design target architecture
- **Teammates**: refactor-specialist (Opus, implementation), test-generator (safety net), code-reviewer (quality gate)
- **When**: Module extraction, pattern migration, dependency upgrades

#### Infrastructure Team (IaC and deployment)
- **Lead**: devops-engineer — infrastructure coordination
- **Teammates**: security-auditor (compliance), architecture-advisor (design review)
- **When**: Terraform module creation, CI/CD pipeline changes, cloud migrations

### Dynamic Spawning

Claude will automatically suggest creating a team when:
1. The task involves 3+ layers (backend, frontend, tests, infrastructure)
2. The user asks to "review", "audit", or "investigate" across multiple dimensions
3. The task description includes multiple independent deliverables
4. The user explicitly asks for parallel work

### Team Coordination Conventions

- **File ownership**: Each teammate owns a distinct set of files — no two teammates edit the same file
- **Task sizing**: 5-6 tasks per teammate maximum for a single team session
- **Worktree isolation**: Use worktree isolation for teammates making parallel edits to avoid conflicts
- **Quality gates**: `TeammateIdle` and `TaskCompleted` hooks enforce deliverable quality automatically
- See `.claude/rules/agent-teams.md` for full coordination conventions

## Enterprise Governance

- `managed-settings.template.json` — IT deployment template for non-overridable org policies
- `CLAUDE.local.md.template` — Developer personal override template (copy to CLAUDE.local.md)
