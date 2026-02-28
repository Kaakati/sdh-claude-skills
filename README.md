# SDH Claude Skills

**Enterprise-grade Claude Code configuration for a professional Software Development House.**

A complete, audited system of rules, agents, skills, and hooks that transforms Claude Code into a full SDLC partner — from requirements gathering through production incident response.

## What This Is

This repository contains a production-ready `.claude/` configuration that enforces enterprise development standards across the entire software development lifecycle. It is designed for teams building **Rails API + React Native mobile** applications deployed on **AWS**.

Instead of relying on ad-hoc prompting, this system provides:

- **13 rules** that are automatically loaded based on file paths being edited
- **8 specialized agents** that handle complex tasks with constrained tool access
- **17 slash-command skills** that provide repeatable, templated workflows
- **7 hook scripts + 3 prompt hooks** that enforce quality gates on every action

## Why This Exists

Most Claude Code setups use a single `CLAUDE.md` file with general instructions. This doesn't scale for professional teams that need:

- **Consistency** — Every developer (human or AI) follows the same standards
- **Enforcement** — Rules are checked automatically, not just documented
- **Specialization** — Different tasks need different expertise and constraints
- **Auditability** — Every tool execution is logged for compliance
- **Coverage** — All SDLC phases are addressed, not just code generation

This configuration achieves **93.75% SDLC coverage** across 64 audit cells (8 phases x 8 capability dimensions), with 0 gaps.

## Technology Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Backend | Ruby on Rails (API-only) | Server-side logic, REST APIs |
| Serialization | Panko Serializer | High-performance JSON serialization |
| Database | PostgreSQL + PostGIS | Relational + geospatial data |
| Mobile | React Native | Cross-platform iOS/Android |
| State Management | Zustand | Client-only state (never server data) |
| Data Fetching | TanStack Query | All server state and caching |
| Real-time | Centrifugo | WebSocket channels for live updates |
| Cache / Queues | Redis | Rails cache + Sidekiq background jobs |
| Cloud (Primary) | AWS | ECS Fargate, RDS, ElastiCache, S3, CloudFront |
| Cloud (Secondary) | GCP | Specific services (Maps, ML, BigQuery) |
| Infrastructure | Terraform | All infrastructure as code |
| Local Dev | Docker Compose | PostgreSQL, Redis, Centrifugo, Rails |

**Philosophy**: Community libraries first — prefer proven gems and npm packages over custom implementations.

## How It Works

### Architecture Overview

```
CLAUDE.md                          ← Master configuration (loaded every session)
├── .claude/rules/                 ← 13 auto-loaded rules (path-scoped)
│   ├── code-standards.md
│   ├── security.md
│   ├── testing.md
│   ├── clean-architecture.md
│   ├── rails-conventions.md
│   ├── react-native.md
│   ├── api-design.md
│   ├── database.md
│   ├── error-handling.md
│   ├── git-workflow.md
│   ├── infrastructure.md
│   ├── monitoring.md
│   └── i18n.md
├── .claude/agents/                ← 8 specialized agents
│   ├── requirements-consultant.md    (Opus, discovery)
│   ├── architecture-advisor.md       (Sonnet, plan mode)
│   ├── clean-architecture.md         (Sonnet, plan mode)
│   ├── code-reviewer.md              (Sonnet, review)
│   ├── security-auditor.md           (Sonnet, audit)
│   ├── test-engineer.md              (Sonnet, testing)
│   ├── devops-engineer.md            (Sonnet, infra)
│   └── refactor-specialist.md        (Sonnet, refactoring)
├── .claude/skills/                ← 17 slash-command skills
│   ├── api-designer/
│   ├── clean-architecture/
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
│   ├── security-auditor/
│   ├── sprint-planner/
│   ├── technical-rfc/
│   └── test-generator/
├── .claude/hooks/                 ← 7 automation scripts
│   ├── security-scan.py              (PreToolUse: blocks secrets)
│   ├── dangerous-command-blocker.py  (PreToolUse: blocks destructive cmds)
│   ├── pre-commit-check.py           (PreToolUse: validates commits)
│   ├── auto-format.sh                (PostToolUse: formats code)
│   ├── test-runner.sh                (PostToolUse: reminds to test)
│   ├── audit-logger.py               (PostToolUse: compliance logging)
│   └── vague-request-detector.py     (UserPromptSubmit: catches ambiguity)
└── .claude/settings.json          ← Permissions, hooks, deny/allow lists
```

### Lifecycle Hooks

Every action Claude takes passes through deterministic quality gates:

| Event | Hook | What It Does |
|-------|------|-------------|
| **Before editing files** | `security-scan.py` | Blocks writes to protected files, detects hardcoded secrets |
| **Before running commands** | `dangerous-command-blocker.py` | Blocks `rm -rf`, `DROP TABLE`, force pushes |
| **Before git commits** | `pre-commit-check.py` | Validates conventional commit format |
| **After editing files** | `auto-format.sh` | Runs rubocop, prettier, terraform fmt |
| **After editing files** | `test-runner.sh` | Reminds to run corresponding tests |
| **After editing files** | Prompt hook | Checks function length (30 lines), file length (200-300 lines), parameter count (4 max), nesting depth (3 max), empty catch blocks, missing test files |
| **After any tool use** | `audit-logger.py` | Logs execution to JSON-lines for compliance |
| **Before processing input** | `vague-request-detector.py` | Suggests requirements-consultant for ambiguous requests |
| **When subagent starts** | Prompt hook | Injects tech stack context into all subagents |
| **When session ends** | Prompt hook | Validates task completion |

### Rules (Auto-Loaded by File Path)

Rules are loaded automatically when you edit files matching their `paths` globs:

| Rule | Triggers On | Key Standards |
|------|------------|---------------|
| `code-standards.md` | All source files | SOLID, 30-line functions, 4-param max, naming conventions |
| `security.md` | All source files | OWASP Top 10, input validation, parameterized queries |
| `testing.md` | Test/spec files | AAA pattern, 80% coverage target, no test interdependencies |
| `clean-architecture.md` | `app/**`, `src/**` | Dependency direction, layer boundaries, violation detection |
| `rails-conventions.md` | `app/**/*.rb` | Models, controllers, services, Panko, Sidekiq patterns |
| `react-native.md` | `src/**/*.{ts,tsx}` | Zustand, TanStack Query, Centrifugo, component patterns |
| `api-design.md` | API controllers/routes | REST conventions, error formats, pagination, versioning |
| `database.md` | Migrations, schema | Safe migrations, indexing strategy, N+1 prevention |
| `error-handling.md` | All source files | Rails rescue patterns, React Native error boundaries |
| `git-workflow.md` | Git operations | Conventional commits, branch naming, PR requirements |
| `infrastructure.md` | Terraform, Docker, CI | AWS services, Docker best practices, cost optimization |
| `monitoring.md` | Logging, health checks | Structured logging, CloudWatch, Sentry, correlation IDs |
| `i18n.md` | Locale/translation files | Key naming, pluralization, RTL support, CI validation |

### Agents

Agents are specialized Claude instances with constrained tools and focused expertise:

| Agent | Model | Mode | Specialization |
|-------|-------|------|---------------|
| `requirements-consultant` | Opus | Interactive | Discovery, feasibility, compliance, user stories, spike scoping |
| `architecture-advisor` | Sonnet | Plan | ADRs, quality attributes, build-vs-buy, architectural decisions |
| `clean-architecture` | Sonnet | Plan | Layer boundary validation, dependency direction, conformance |
| `code-reviewer` | Sonnet | Interactive | SOLID review, complexity analysis, security scan, PR review |
| `security-auditor` | Sonnet | Interactive | OWASP audit, secret scanning, SBOM, supply chain security |
| `test-engineer` | Sonnet | Interactive | Test generation, AAA pattern, coverage analysis, mocking |
| `devops-engineer` | Sonnet | Interactive | CI/CD, Terraform, Docker, deployment automation, GitOps |
| `refactor-specialist` | Sonnet | Interactive | Code smells, Fowler's patterns, incremental refactoring |

### Skills (Slash Commands)

Invoke with `/skill-name` for templated, repeatable workflows:

| Command | Routes To Agent | Description |
|---------|----------------|-------------|
| `/code-reviewer` | code-reviewer | PR review with auto-injected git diff |
| `/security-auditor` | security-auditor | OWASP audit, SBOM generation, license compliance |
| `/clean-architecture` | clean-architecture | Architecture conformance validation |
| `/test-generator` | test-engineer | Generate tests with AAA pattern |
| `/api-designer` | — | REST API design and review |
| `/rails-architect` | — | Rails backend architecture |
| `/react-native-dev` | — | React Native feature implementation |
| `/db-migration` | — | Schema design and safe migrations |
| `/performance-profiler` | — | Performance investigation and optimization |
| `/deploy` | — | Deployment with pre-flight checks, canary/blue-green |
| `/doc-generator` | — | ADRs, runbooks, specs, retrospectives, change management |
| `/i18n` | — | Rails + React Native internationalization |
| `/compliance-auditor` | — | SOC2, HIPAA, PCI-DSS, GDPR auditing |
| `/sprint-planner` | — | Sprint planning, estimation, velocity tracking |
| `/technical-rfc` | — | RFC proposals for significant changes |
| `/onboarding` | — | Developer setup guides |
| `/incident-response` | — | Production incident diagnosis, chaos engineering |

## SDLC Coverage

This configuration was audited against a Big 4-style SDLC matrix (8 phases x 8 dimensions = 64 cells):

```
                    Skills  Agents  Rules   Hooks   Templates Security Testing  Docs
                    ------  ------  ------  ------  --------- -------- -------  ----
Phase 0: Discovery   [X]     [X]     [X]     [X]      [X]      [X]     [~]     [X]
Phase 1: Planning    [X]     [X]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 2: Design      [X]     [X]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 3: Implement   [X]     [~]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 4: QA          [X]     [X]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 5: DevOps      [X]     [X]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 6: Operations  [X]     [~]     [X]     [X]      [X]      [X]     [X]     [X]
Phase 7: Governance  [X]     [~]     [X]     [X]      [X]      [X]     [X]     [X]

[X] = Covered    [~] = Partial    60/64 COVERED (93.75%)
```

## Getting Started

### 1. Clone into your project

```bash
# Clone this repo
git clone git@github.com:Kaakati/sdh-claude-skills.git

# Copy .claude/ directory and CLAUDE.md into your project
cp -r sdh-claude-skills/.claude/ your-project/.claude/
cp sdh-claude-skills/CLAUDE.md your-project/CLAUDE.md
```

### 2. Customize for your project

```bash
# Create your personal overrides (gitignored)
cp CLAUDE.local.md.template CLAUDE.local.md
```

Edit `CLAUDE.local.md` to set your preferences:
- Explanation style (concise vs verbose)
- Primary work area (backend, mobile, full-stack)
- Development environment (ports, platforms)
- Current focus area

### 3. Verify hooks work

The hooks require Python 3 and Bash. Ensure they're available in your environment:

```bash
python3 --version  # Required for security-scan, audit-logger, etc.
bash --version     # Required for auto-format, test-runner
```

### 4. Use slash commands

```
/code-reviewer          # Review your latest changes
/security-auditor       # Run OWASP security audit
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

1. **Rules over instructions** — Rules are scoped to file paths and auto-loaded. This means Rails conventions only apply when editing Ruby files, React Native patterns only apply for TypeScript.

2. **Agents over prompts** — Complex tasks use agents with constrained tool access and specialized system prompts. A security auditor agent can't edit files. A code reviewer has read-only access.

3. **Hooks over trust** — Quality gates are deterministic scripts, not AI judgment calls. The security scanner blocks secrets before they're written, not after review.

4. **Skills over repetition** — Common workflows are templated. A deployment always follows the same pre-flight checklist. An ADR always uses the same format.

5. **Community libraries over custom code** — The entire configuration assumes and enforces the use of established gems and npm packages (devise, pundit, pagy, react-hook-form, zod, etc.).

## Repository Structure

```
.
├── CLAUDE.md                          # Master configuration
├── CLAUDE.local.md.template           # Personal override template
├── .gitignore
└── .claude/
    ├── settings.json                  # Permissions + hooks
    ├── managed-settings.template.json # IT admin template
    ├── agents/          (8 agents)
    ├── skills/          (17 skills, each with SKILL.md + references/)
    ├── rules/           (13 rule files)
    └── hooks/           (7 automation scripts)
```

## Contributing

1. Follow [Conventional Commits](https://www.conventionalcommits.org/): `type(scope): description`
2. Branch naming: `feature/TICKET-ID-description`
3. PRs under 400 lines changed
4. Squash merge to main

## License

This configuration is provided as-is for teams using Claude Code with Rails + React Native projects. Adapt the rules, agents, and skills to match your tech stack and standards.
