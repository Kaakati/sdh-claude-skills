# Claude Code Skills, Rules, Agents, and Hooks for the enterprise

Claude Code's extensibility rests on **four interlocking systems** — Skills for domain knowledge, Rules for governance, Agents for delegation, and Hooks for deterministic automation — that together give enterprise teams fine-grained control over AI-assisted development at scale. This guide synthesizes official Anthropic documentation and production-tested patterns into a comprehensive reference for organizations deploying Claude Code to 50+ developers across monorepos and complex toolchains. Each pillar addresses a distinct need: Skills teach Claude *what* to do, Rules tell it *how* to behave, Agents let it *delegate* work, and Hooks guarantee *when* specific actions execute.

---

## 1. Skills: modular, on-demand domain expertise

Skills are **filesystem-based capability modules** that extend Claude Code with organized instructions, scripts, and reference material. Unlike CLAUDE.md files (which load at every session start), skills use **progressive disclosure**: only ~100 tokens of frontmatter metadata load at startup, the full SKILL.md body (~2,000–5,000 tokens) loads on activation, and supporting files load only when referenced. This makes skills dramatically more context-efficient than stuffing everything into CLAUDE.md.

### How skills are structured

Every skill lives in a directory containing a required `SKILL.md` file with YAML frontmatter:

```markdown
---
name: api-reviewer
description: Review API endpoints for REST conventions, input validation, and security. Use when reviewing or creating API routes.
---

# API Reviewer

## Instructions
1. Check all endpoints follow RESTful naming conventions
2. Verify input validation on all request parameters
3. Ensure consistent error response formats
4. Flag any missing authentication checks

## Reference
See references/api-standards.md for the complete API style guide.
```

The `name` field (max 64 characters, lowercase with hyphens) becomes the `/api-reviewer` slash command. The `description` field is **the single most important element** — Claude uses it to decide when to auto-invoke the skill. Anthropic's guidance is to make descriptions slightly "pushy" with explicit trigger terms: *"Extract text and tables from PDF files. Use when working with PDFs, forms, or document extraction"* beats *"Helps with documents."*

Skills support several powerful optional frontmatter fields for enterprise use:

| Field | Purpose | Enterprise use case |
|-------|---------|-------------------|
| `disable-model-invocation: true` | Only user can invoke via `/name` | Deployment, commit, and message-sending skills |
| `allowed-tools` | Restricts and pre-approves specific tools | Read-only code review (`Read, Grep, Glob`) |
| `context: fork` | Runs in isolated subagent context | Self-contained workflows that shouldn't pollute main context |
| `agent` | Specifies which subagent to use | Route to specialized agents like `Explore` or custom agents |
| `model` | Override the model for this skill | Use Haiku for cheap exploration skills, Opus for critical ones |
| `hooks` | Define lifecycle hooks scoped to this skill | Pre/post validation specific to a workflow |

The directory structure supports progressive complexity:

```
.claude/skills/
├── code-reviewer/
│   ├── SKILL.md              # Core instructions
│   ├── scripts/
│   │   └── complexity-check.py
│   └── references/
│       └── style-guide.md
├── deploy/
│   └── SKILL.md              # User-invoked only
└── api-conventions/
    └── SKILL.md              # Background knowledge
```

Skills also support **dynamic context injection** using `!` backtick syntax — commands like `` !`gh pr diff` `` are preprocessed before Claude sees the content, enabling skills that automatically pull in PR diffs, test results, or environment data.

### Enterprise skill management at scale

For organizations with 50+ developers, skills distribute through multiple channels. **Git-committed project skills** in `.claude/skills/` propagate automatically when teammates pull. **Personal skills** in `~/.claude/skills/` let individual developers maintain private workflows. **Plugins** bundle skills for marketplace distribution across teams. On Team and Enterprise plans, organization Owners can **provision skills org-wide** through the admin console, setting them as enabled-by-default or opt-in.

Skill descriptions share a **context budget of 2% of the context window** (~16,000 characters). With many skills installed, some may be excluded from Claude's awareness. Running `/context` reveals whether skills are being dropped, and the `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable overrides the budget.

Key best practices for enterprise skill libraries: keep each skill focused on one capability (split "document processing" into separate PDF, Excel, and Word skills), keep SKILL.md under **500 lines**, move detailed reference material to supporting files, and always test with representative queries before org-wide provisioning. The open **Agent Skills standard** at agentskills.io (published December 2025) ensures portability across Claude Code, OpenAI Codex, GitHub Copilot, and 26+ other platforms.

---

## 2. Rules: hierarchical governance from CLAUDE.md to managed policies

Rules in Claude Code operate through a layered system of markdown files and JSON settings that together form the agent's "constitution." The cornerstone is `CLAUDE.md` — a markdown file automatically loaded into Claude's system prompt at every session start, providing authoritative project context that Claude treats as system-level instructions.

### The CLAUDE.md hierarchy

Claude Code implements a **four-tier memory hierarchy** evaluated from highest to lowest precedence:

| Tier | Location | Scope | Shared with |
|------|----------|-------|-------------|
| Enterprise policy | `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS), `/etc/claude-code/CLAUDE.md` (Linux) | Organization-wide | All users via IT deployment |
| User memory | `~/.claude/CLAUDE.md` | All your projects | Just you |
| Project memory | `./CLAUDE.md` or `./.claude/CLAUDE.md` | Current project | Team via source control |
| Local memory | `./CLAUDE.local.md` | Current project | Just you (gitignored) |

All tiers load simultaneously at session start — they are **additive**, not overriding. When instructions conflict, Claude applies judgment, with more specific instructions generally prevailing. The enterprise tier deployed via MDM or configuration management gives IT teams an unbypassable layer for security policies.

A critical behavior for monorepos: Claude Code walks **upward** from the current working directory, loading every CLAUDE.md found along the path. Running Claude in `packages/frontend/` loads both root `CLAUDE.md` and `packages/frontend/CLAUDE.md`. Subdirectory CLAUDE.md files below the working directory use **lazy loading** — they activate only when Claude reads or writes files in those directories. This prevents a 50-package monorepo from consuming the entire context window at startup.

CLAUDE.md files support `@path/to/import` syntax for modular organization:

```markdown
See @README for project overview and @package.json for available commands.
# Git workflow
@docs/git-instructions.md
```

Imports resolve recursively up to 5 levels deep and support both relative and absolute paths.

### Modular rules with path scoping

The `.claude/rules/` directory provides **granular, file-pattern-scoped rules** that activate conditionally:

```yaml
---
paths:
  - "src/api/**/*.ts"
---
# API development standards
- All endpoints must include input validation using Zod schemas
- Return consistent error format: { error: string, code: number, details?: object }
- Include OpenAPI JSDoc comments on every route handler
```

Rules **without** a `paths:` frontmatter load unconditionally at every session. Rules **with** `paths:` only activate when Claude works on matching files, keeping context focused. The directory supports recursive organization — `rules/frontend/react.md`, `rules/backend/database.md` — enabling teams to maintain domain-specific guidance without a monolithic CLAUDE.md.

**Important clarification**: The `.mdc` file format is **Cursor-specific, not Claude Code**. Claude Code uses standard `.md` files in `.claude/rules/` with a `paths:` frontmatter field. Teams using both tools can write rules in either format — each tool ignores the other's proprietary frontmatter fields.

### Enterprise governance through managed settings

The **`managed-settings.json`** file sits at the top of the settings hierarchy and **cannot be overridden** by any user or project configuration:

```json
{
  "forceLoginMethod": "console",
  "forceLoginOrgUUID": "a1b2c3d4-e5f6-...",
  "disableBypassPermissionsMode": "disable",
  "allowManagedHooksOnly": true,
  "allowManagedPermissionRulesOnly": true,
  "permissions": {
    "deny": [
      "Read(**/.env)", "Read(**/secrets/**)",
      "Bash(sudo:*)", "Bash(curl:*)", "Bash(wget:*)"
    ]
  },
  "allowedMcpServers": [{"serverName": "approved-db-server"}],
  "deniedMcpServers": [{"serverName": "untrusted-server"}],
  "companyAnnouncements": ["Review security guidelines at docs.internal/claude-policy"]
}
```

This enables enterprise security teams to enforce non-negotiable policies: blocking access to `.env` files, preventing dangerous shell commands, restricting MCP server connections, forcing specific authentication methods, and disabling the `--dangerously-skip-permissions` flag entirely. The permission evaluation order is **deny → ask → allow**, with unmatched operations defaulting to requiring approval (fail-closed).

### Monorepo rule architecture

For large monorepos, the recommended pattern layers rules at three levels:

```
/monorepo/
├── CLAUDE.md                          # Universal: commit format, CI, coding standards
├── .claude/
│   ├── settings.json                  # Shared: tool permissions, MCP config
│   ├── rules/
│   │   ├── security.md                # Global: security requirements (no paths:)
│   │   ├── api-design.md              # Scoped to src/api/**
│   │   └── frontend/
│   │       └── react-patterns.md      # Scoped to src/frontend/**/*.tsx
│   └── skills/
│       └── deploy/SKILL.md
├── packages/
│   ├── frontend/CLAUDE.md             # Frontend-specific (lazy loaded)
│   ├── backend/CLAUDE.md              # Backend-specific (lazy loaded)
│   └── shared/CLAUDE.md
└── CLAUDE.local.md                    # Personal overrides (gitignored)
```

Version-controlled files (`.claude/settings.json`, `.claude/rules/`, `CLAUDE.md`) propagate team standards automatically through Git. Personal files (`.claude/settings.local.json`, `CLAUDE.local.md`) stay gitignored. Enterprise policies deploy via MDM or Ansible to system-level paths.

---

## 3. Agents: subagents, teams, and multi-agent orchestration

Claude Code provides three tiers of agent delegation: **subagents** for focused task delegation within a session, **Agent Teams** for coordinated parallel work across multiple Claude instances, and the **Claude Agent SDK** for programmatic orchestration in CI/CD and custom tooling.

### Subagents and the Task tool

Subagents are pre-configured AI agents that Claude delegates to via the **Task tool**. Each subagent operates in its own context window with a specific purpose, tools, and system prompt. Claude Code ships with three built-in subagents:

- **Explore** — Uses Haiku for fast, read-only codebase search (tools: Glob, Grep, Read, Bash read-only)
- **General-purpose** — Uses Sonnet for complex multi-step tasks with full tool access
- **Plan** — Uses Sonnet in plan mode for codebase research without modifications

Custom subagents are defined as markdown files with YAML frontmatter in `.claude/agents/` (project-level, shared via Git) or `~/.claude/agents/` (personal):

```yaml
---
name: security-auditor
description: Security audit specialist. Use when reviewing code for vulnerabilities, checking authentication flows, or analyzing access control.
tools: Read, Grep, Glob, Bash
model: sonnet
permissionMode: default
---

You are a senior security engineer conducting thorough code audits.

## Audit protocol
1. Run `git diff HEAD~1` to identify recent changes
2. Scan for hardcoded secrets using grep patterns
3. Check authentication middleware for bypass vulnerabilities
4. Verify input sanitization on all user-facing endpoints
5. Review dependency versions against known CVE databases

## Output format
Provide findings as: CRITICAL / HIGH / MEDIUM / LOW with file paths and line numbers.
```

A critical architectural constraint: **subagents cannot spawn other subagents** — the delegation tree is one level deep. This prevents runaway agent chains but means complex multi-step workflows must be coordinated by the main agent.

### Agent Teams for parallel coordination

**Agent Teams** (experimental, launched February 2026 alongside Claude Opus 4.6) enable multiple full Claude Code instances to work together with peer-to-peer communication:

```json
// Enable in ~/.claude/settings.json
{ "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" } }
```

The architecture consists of a **Lead Agent** that spawns **Teammates**, each operating in independent context windows with access to a **shared task list** (`~/.claude/tasks/{team-name}/`) and **inbox system** (`~/.claude/teams/{team-name}/inboxes/`) for direct messaging.

The key difference from subagents is that teammates can **message each other directly** — not just report to the parent. This enables patterns like:

- Frontend, backend, and test teammates coordinating on a feature
- Multiple security reviewers with different specializations cross-referencing findings
- Competing debugging hypotheses explored in parallel

Anthropic's own multi-agent research (published June 2025) found that **Opus as lead + Sonnet subagents outperformed single-agent Opus by 90.2%**, with token usage explaining 80% of performance variance. However, agents use ~15× more tokens than single chat sessions, and **3 teammates typically outperform 6** due to diminishing returns and coordination overhead.

Current limitations include: no nested teams (teammates can't spawn their own teams), one team per session, requires tmux or iTerm2 for split-pane execution, and known issues with session resumption and shutdown timing.

### The Claude Agent SDK for programmatic control

The SDK (Python and TypeScript) exposes Claude Code's full agentic harness for custom tooling:

```python
from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

async for message in query(
    prompt="Review authentication module for security issues",
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Task"],
        agents={
            "security-reviewer": AgentDefinition(
                description="Security code review specialist",
                prompt="You are a security reviewer focused on auth...",
                tools=["Read", "Grep", "Glob"],
                model="sonnet",
            ),
        },
        permission_mode="acceptEdits",
    ),
):
    if hasattr(message, "result"):
        process_result(message.result)
```

The SDK supports headless execution (`claude -p "prompt"` on CLI), structured JSON output, session management with resume capability, MCP integration, and multi-turn conversations. For CI/CD, the official `anthropics/claude-code-action@v1` GitHub Action integrates directly with pull request workflows, triggering on `@claude` mentions in PRs and issues.

### Enterprise agent patterns

**Automated code review pipeline**: Configure a `code-reviewer` agent with read-only tools that auto-triggers on PR creation via GitHub Actions. The agent reads the diff, applies project-specific rules from CLAUDE.md, and posts findings as PR comments.

**Multi-perspective security audit**: Spawn an Agent Team with specialized teammates — a vulnerability scanner, a dependency auditor, and an architecture reviewer — each examining the same changeset from different angles and cross-referencing through the shared inbox.

**Parallel monorepo refactoring**: Use headless mode in bash loops to process files in parallel:
```bash
for file in src/**/*.js; do
  claude -p "Convert to TypeScript with strict types: @$file" \
    --allowedTools "Read,Write" --max-turns 5 &
done
wait
```

Cost control across these patterns relies on **model selection per agent role**: Haiku for read-only exploration (~$0.25/M input tokens), Sonnet for general work (~$3/M), and Opus only for the lead agent on critical decisions (~$5/M). Setting `--max-turns` prevents runaway iterations.

---

## 4. Hooks: deterministic automation at every lifecycle point

Hooks are **user-defined commands that execute at specific points in Claude Code's lifecycle**, providing guaranteed deterministic behavior that CLAUDE.md instructions cannot. Where rules are advisory (Claude may not follow them perfectly), hooks are **application-level code that fires every time conditions are met**. This makes hooks the enterprise enforcement layer for formatting, security scanning, logging, and compliance.

### The three hook handler types

**Command hooks** run shell commands that receive JSON via stdin and control behavior through exit codes:
```json
{
  "type": "command",
  "command": "python3 scripts/security-check.py",
  "timeout": 300
}
```

**Prompt hooks** send a question to a fast Haiku model for single-turn judgment calls without shell scripting:
```json
{
  "type": "prompt",
  "prompt": "Evaluate if this task is truly complete: $ARGUMENTS",
  "timeout": 30
}
```

**Agent hooks** spawn a subagent with tools like Read, Grep, and Glob for deep codebase analysis — up to 50 tool-use turns. These are the most powerful type, enabling hooks that inspect actual code state before making decisions.

### Lifecycle events and matchers

Claude Code exposes **14+ hook events** spanning the full session lifecycle:

| Event | When it fires | Can block? |
|-------|--------------|-----------|
| `Setup` | Via `--init` or `--maintenance` flags | No |
| `SessionStart` | New or resumed session | No |
| `UserPromptSubmit` | User submits prompt, before processing | Yes (exit 2) |
| `PreToolUse` | Before any tool executes | Yes (allow/deny/ask) |
| `PermissionRequest` | When permission dialog shown | Yes |
| `PostToolUse` | After tool completes | No (tool already ran) |
| `SubagentStart` | When subagent spawns | No (can inject context) |
| `SubagentStop` | When subagent finishes | Yes (exit 2) |
| `Stop` | When main agent finishes responding | Yes (exit 2 continues work) |
| `Notification` | When notifications sent | No |
| `SessionEnd` | Session terminates | No |
| `TeammateIdle` | Agent Team member about to go idle | Yes |
| `TaskCompleted` | Task marked complete | Yes |

Matchers use string matching or regex against tool names: `"Edit|Write"` matches both tools, `"Bash"` matches only Bash, `"mcp__myserver__.*"` matches MCP tools. All matching hooks for an event **run in parallel** with a default **10-minute timeout**.

### Hook configuration and placement

Hooks configure through JSON in settings files at every tier:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | xargs prettier --write"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 .claude/hooks/block-protected-files.py"
          }
        ]
      }
    ]
  }
}
```

Configuration locations follow the same hierarchy as settings: `managed-settings.json` (enterprise, non-overridable) → `.claude/settings.json` (project, Git-tracked) → `.claude/settings.local.json` (personal) → `~/.claude/settings.json` (user-global). Skills and agents can also define hooks in their YAML frontmatter.

The enterprise-critical setting `allowManagedHooksOnly: true` in managed settings **disables all user- and project-defined hooks**, ensuring only IT-approved hooks execute.

### PreToolUse hooks as enterprise gatekeepers

PreToolUse hooks are the most powerful enforcement mechanism. They can **block operations, modify tool inputs transparently, or escalate to manual approval**:

```python
#!/usr/bin/env python3
# .claude/hooks/enterprise-gatekeeper.py
import json, sys, re

data = json.load(sys.stdin)
tool = data.get("tool_name", "")
tool_input = data.get("tool_input", {})

# Block writes to protected paths
if tool in ("Edit", "Write"):
    path = tool_input.get("file_path", "")
    protected = [".env", "secrets/", "production.config", ".github/workflows/"]
    if any(p in path for p in protected):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"Protected file: {path}"
            }
        }))
        sys.exit(0)

# Block destructive commands
if tool == "Bash":
    cmd = tool_input.get("command", "")
    if re.search(r"rm\s+-rf|DROP\s+TABLE|truncate", cmd, re.IGNORECASE):
        sys.exit(2)  # Block with error

sys.exit(0)  # Allow
```

Since v2.0.10, PreToolUse hooks can also **modify tool inputs** via `updatedInput` — enabling transparent sandboxing, path rewriting, and convention enforcement invisible to Claude.

### Enterprise hook deployment patterns

For compliance-critical environments, deploy a layered hook strategy:

**Managed hooks (IT-controlled, non-overridable)**: Audit logging of all Bash commands, secret detection in file writes, network request monitoring. Deployed via `managed-settings.json` with `allowManagedHooksOnly: true`.

**Project hooks (team-controlled, Git-tracked)**: Auto-formatting with Prettier/gofmt on file edits, test execution after code changes, linting enforcement. Configured in `.claude/settings.json`.

**Personal hooks (developer preference)**: Desktop notifications when Claude needs input, custom commit message formatting. Set in `~/.claude/settings.json`.

Integration with existing toolchains works through the shell command interface — hooks can call Semgrep for SAST scanning, Snyk for dependency checks, or post to Slack/Jira APIs. The GitButler integration provides a production-grade pattern for automatic branch and commit management through Pre/PostToolUse and Stop hooks.

A known security consideration: **CVE-2025-59536** demonstrated that malicious `.claude/settings.json` files in cloned repositories could execute arbitrary code via hooks. Anthropic responded with enhanced warning dialogs for untrusted project configurations. Enterprise deployments should audit project-level hook configurations in code review and consider `allowManagedHooksOnly` for high-security environments.

---

## 5. Enterprise deployment architecture and governance

### Configuration management at scale

The complete enterprise configuration stack deploys through three channels:

**System-level (IT-managed)**: `managed-settings.json`, `managed-mcp.json`, and enterprise `CLAUDE.md` files deployed via MDM, Group Policy, or Ansible to platform-specific paths. These cannot be overridden and establish the security baseline.

**Repository-level (team-managed)**: `.claude/settings.json`, `.claude/rules/`, `.claude/skills/`, `.claude/agents/`, and root `CLAUDE.md` checked into version control. These propagate team standards through normal Git workflows.

**Developer-level (personal)**: `.claude/settings.local.json`, `CLAUDE.local.md`, `~/.claude/CLAUDE.md`, and `~/.claude/skills/` for individual preferences. These are gitignored and never leave the developer's machine.

### Authentication, access control, and audit

Enterprise plans support **SAML 2.0 and OIDC SSO** with Okta, Azure AD, and Ping Identity, plus **SCIM provisioning** for automated user lifecycle management. The `forceLoginMethod` and `forceLoginOrgUUID` managed settings ensure developers authenticate through the correct identity provider.

The permission system provides fine-grained tool access control with **deny → ask → allow** evaluation. Tool patterns include `Bash(npm run test:*)` for command allowlisting, `Read(./.env)` for file access restriction, and `WebFetch(domain:internal.api.com)` for network control.

The **Compliance API** (Enterprise-only, NDA required) provides real-time programmatic access to usage data, conversation logs, and activity history — filterable by user and time range. **Audit logs** retain 180 days of user actions, system events, and data access in exportable JSON/CSV format, integrable with SIEM platforms like Splunk and Datadog. OpenTelemetry integration enables custom metrics export for per-user cost tracking and usage dashboards.

### Multi-cloud deployment options

Claude Code supports **Anthropic's direct API**, **AWS Bedrock** (VPC-scoped with CloudTrail and IAM), **Google Vertex AI** (Private Service Connect for zero-egress), and **Microsoft Azure Foundry**. Each backend configures through environment variables (`CLAUDE_CODE_USE_BEDROCK=1`, `CLAUDE_CODE_USE_VERTEX=1`, `CLAUDE_CODE_USE_FOUNDRY=1`). For air-gapped environments, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` disables the auto-updater, bug reporting, and all telemetry in a single toggle.

### Phased enterprise rollout

Production deployments follow a proven three-phase pattern:

1. **Pilot (2 weeks)**: 5–8 senior developers establish CLAUDE.md conventions, build initial skills library, configure managed settings, validate security policies against the permission system
2. **Department (1 month)**: 50 developers with full CI/CD integration via GitHub Actions, team-specific skills and agents deployed via Git, hook-based formatting and compliance enforcement
3. **Organization-wide (3 months)**: 200+ developers with SSO/SCIM provisioning, Compliance API integration with existing governance tooling, Agent Teams for cross-team coordination, and continuous iteration on skill libraries based on usage analytics

### Version pinning and update control

Enterprise administrators control Claude Code updates through `autoUpdatesChannel` — set to `"stable"` (typically one week behind latest) for predictable rollouts or disable entirely with `DISABLE_AUTOUPDATER: "1"`. The managed settings file pins these organization-wide, ensuring all developers run consistent versions during security reviews or compliance audits.

---

## Conclusion: four pillars working together

The four pillars are most powerful when composed. **Rules** in CLAUDE.md and `.claude/rules/` establish the behavioral baseline — coding standards, architecture patterns, security requirements. **Skills** package domain expertise as on-demand, context-efficient modules that Claude auto-invokes when relevant. **Agents** extend Claude's reach through specialized subagents for focused tasks and Agent Teams for coordinated parallel work. **Hooks** provide the deterministic enforcement layer that guarantees critical actions — formatting, scanning, logging, blocking — happen every time, regardless of whether Claude "remembers" a rule.

For enterprise teams, the key insight is that **managed settings and enterprise CLAUDE.md files create an unbypassable governance layer** that sits above all developer and project configuration. Combined with the Compliance API, audit logs, and SIEM integration, this gives security and compliance teams the visibility and control they need while preserving developer autonomy within safe boundaries. The system's layered architecture — enterprise → user → project → local — maps naturally to organizational hierarchies, and Git-based distribution of project-level configuration means standards propagate through existing workflows without additional tooling overhead.

The ecosystem is maturing rapidly — Agent Teams reached experimental status in February 2026, hooks have expanded to 14+ lifecycle events with three handler types, and the Agent Skills open standard enables cross-platform portability. Organizations investing in these four pillars now are building institutional knowledge that compounds as Claude Code's capabilities expand.