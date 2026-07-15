---
name: mcp-advisor
description: Discover, evaluate, and safely connect MCP servers. Use when a task keeps requiring data pasted in from another tool (Jira, Sentry, Figma, Postgres, Notion, Slack), when someone asks "is there an MCP for this", "should we add an MCP server", "find an MCP", "connect Claude to X", or when choosing a scope (local/project/user), vetting a third-party server, or deciding whether an MCP is worth its supply-chain cost. Also use before running `claude mcp add` or editing `.mcp.json`.
model: sonnet
---

# MCP Advisor — an instruction source, not a dependency

An MCP server gives Claude Code real access to your tools. It is also the least examined thing
in your stack, because it does not look like code you own. Claude Code's docs say it plainly:

> *"Verify you trust each server before connecting it. Servers that fetch external content can
> expose you to **prompt injection risk**."*

The distinction that governs everything below: **a library is text you run; an MCP server is text
the model obeys.** Its tool descriptions are prompts. A server that reads issue titles, web
pages, or customer emails is piping attacker-influenced text into a session that can write files
and run commands. That is not a reason to avoid MCP — it is the reason a **human** picks each one.

## I never add one without asking

Suggesting an MCP is my job. Installing one is yours. `mcp-install-gate.py` enforces this on
`claude mcp add`, `add-json`, `add-from-claude-desktop`, and any write to `.mcp.json` — so the
rule holds even if nobody read this file. When I propose a server I will tell you: who publishes
it, what it can read, what credential it needs, and which scope I am proposing — and then wait.

## Decision: is an MCP server even the right answer?

The docs give the honest trigger:

> *"Connect a server when you find yourself copying data into chat from another tool, like an
> issue tracker or a monitoring dashboard."*

That is the bar. Repetition of a manual paste — not novelty.

| Situation | Answer |
|---|---|
| Pasting the same dashboard/ticket/query output repeatedly | **An MCP earns its place** |
| One-off lookup | Just paste it. A permanent instruction source for a five-minute task is a bad trade |
| A CLI already does it (`gh`, `aws`, `psql`) | **Use the CLI** — it is already governed by the command gates and needs no new trust |
| Reading our own database | Prefer a **read-only** server and a read-only credential |
| It would need broad write access to production | Almost certainly no. Ask what specifically must be automated |

**`gh` beats a GitHub MCP for most tasks.** A CLI runs under the permission and hook layers you
already have; a server adds a new instruction source and a new credential. Reach for MCP when the
tool has no usable CLI, or when structured tool-calling genuinely beats parsing CLI output.

## Discovery — start with the reviewed list

- **[Anthropic Directory](https://claude.ai/directory)** — reviewed connectors, same MCP
  infrastructure. Start here; "reviewed by someone" is the cheapest trust you will ever get.
- **Vendor-published servers** (Notion, Sentry, Stripe, Figma) — the vendor is accountable and
  identifiable. Second best.
- **Community/random GitHub servers** — treat exactly like adding an unvetted dependency that can
  also talk to the model. Read the source, or don't add it.
- `claude mcp list` / `claude mcp get <name>` / `/mcp` — what is already connected. **Check this
  first**: the answer is often "we already have it."

## The vetting bar (all four, before I suggest it)

1. **Who publishes it, and would you name them in an incident review?** Anonymous server, no.
2. **Pinned, not floating.** `npx -y some-server@latest` re-downloads whatever was published this
   morning — the plugin's own *pin, don't float* rule applies here at least as hard, because this
   dependency also writes prompts.
3. **Least credential.** A read-only DB user, a scoped token. An MCP server with your admin key
   has your admin key.
4. **Blast radius matches scope.** See below.

→ `references/vetting-servers.md`

## Decision: which scope?

| Scope | Lives in | Loads | Use when |
|---|---|---|---|
| **local** (default) | `~/.claude.json` | Only this project, only you | Trying it out; anything personal |
| **project** | **`.mcp.json`, checked in** | Everyone who opens the repo | The whole team genuinely needs it |
| **user** | user config | All your projects | Your own tooling across repos |

**`--scope project` is a decision about other people.** It ships to every teammate, who each see
it as `⏸ Pending approval` until they accept — they are being asked to trust *your* vetting. Do
not use project scope to save yourself one command.

→ `references/adding-safely.md`

## Secrets never go in `.mcp.json`

`.mcp.json` is committed. Reference the environment (`${VAR}`), never a literal key — the repo's
`security-scan.py` will block the obvious cases, and the non-obvious ones are the ones that hurt.
Note that `headersHelper` **executes arbitrary shell commands**: a `.mcp.json` from an untrusted
repo is code, not config.

## After connecting

- `/mcp` shows status; a server that fails to start is a silent capability gap.
- **Re-read what changed.** New tools mean new instructions in your context; the model's
  behaviour can shift for reasons that have nothing to do with your prompt.
- An org can make vetting mandatory rather than advisory with `allowedMcpServers` /
  `deniedMcpServers` in managed settings — that is layer 5, and it is the only way to stop a
  determined engineer. See [`docs/org-policy.md`](../../docs/org-policy.md).

## Deep guides (read on demand, do not preload)

- Judging a server before it earns your trust: publisher, pinning, credential scope, the
  prompt-injection surface, reading a server's tool descriptions as the prompts they are, and
  the questions to ask about one you did not write → `references/vetting-servers.md`
- The mechanics: `claude mcp add` for stdio/HTTP/SSE, scopes and where each lives, `.mcp.json`
  and the approval flow teammates see, env-var indirection for tokens, and removing a server
  → `references/adding-safely.md`
