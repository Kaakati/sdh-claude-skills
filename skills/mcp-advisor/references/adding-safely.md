# Adding an MCP Server — the mechanics

Load-bearing rules restated (hold even if you read nothing else):

1. **Local is the default, and usually correct.** `--scope project` is a decision about your
   teammates.
2. **No secrets in `.mcp.json`** — it is committed. Reference the environment.
3. **Vet first.** `references/vetting-servers.md` is the prerequisite, not the appendix.

---

## The three transports

```bash
# stdio — a local process. `--` separates Claude's options from the server's command.
claude mcp add [options] <name> -- <command> [args...]
claude mcp add --env AIRTABLE_API_KEY=$AIRTABLE_KEY --transport stdio airtable \
  -- npx -y airtable-mcp-server@1.4.2

# http — a remote server
claude mcp add --transport http notion https://mcp.notion.com/mcp

# sse — a remote server with server-sent events
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

The `--` matters and is easy to get wrong: everything **before** it is Claude's
(`--transport`, `--env`, `--scope`); everything **after** it is the command Claude runs. Options
placed after `--` are silently passed to the server instead of to Claude.

## Scopes: where it lives, and who it affects

| Scope | Stored in | Loads for | Shared? |
|---|---|---|---|
| `local` (**default**) | `~/.claude.json` | You, in this project only | No |
| `project` | **`.mcp.json` in the repo** | Everyone who opens the repo | **Yes — committed** |
| `user` | your user config | You, in every project | No |

```bash
claude mcp add --transport http stripe https://mcp.stripe.com                    # local (default)
claude mcp add --transport http stripe --scope local https://mcp.stripe.com      # explicit
claude mcp add --transport http acme --scope project https://mcp.acme.com/mcp    # writes .mcp.json
```

> Note the naming trap: MCP **"local scope"** lives in `~/.claude.json` (your home directory) —
> it is not the same thing as `.claude/settings.local.json`. Same word, different file.

### Start local. Promote deliberately.

Local scope is the right default because it is **reversible and private**: if the server is
useless or badly behaved, you remove it and nobody else ever knew. Project scope makes it
everyone's problem — and everyone's trust decision.

## `.mcp.json` — the team-wide file

```json
{
  "mcpServers": {
    "acme": {
      "type": "http",
      "url": "https://mcp.acme.com/mcp",
      "headers": {
        "Authorization": "Bearer ${ACME_MCP_TOKEN}"
      }
    }
  }
}
```

### Bad — the credential is now in git forever

```json
{
  "mcpServers": {
    "acme": {
      "type": "http",
      "url": "https://mcp.acme.com/mcp",
      "headers": { "Authorization": "Bearer sk-live-REDACTED-EXAMPLE-DO-NOT-DO-THIS" }
    }
  }
}
```

`.mcp.json` is committed. A token here is a token in every clone, every fork, and every CI cache,
permanently — `git rm` does not unpublish it. The repo's `security-scan.py` catches the obvious
shapes; do not rely on it to catch yours.

### Good — indirection, so each teammate supplies their own

```json
{
  "mcpServers": {
    "acme": {
      "type": "http",
      "url": "https://mcp.acme.com/mcp",
      "headers": { "Authorization": "Bearer ${ACME_MCP_TOKEN}" }
    }
  }
}
```

`${VAR}` is expanded from the environment, so the file describes *which* credential is needed
without containing it — and each teammate uses a token scoped to them, which is also what makes
revocation possible.

Document the variable in `.env.example` (per `std-infrastructure`: *maintain `.env.example` with
every required key and empty values*), or the next person's server fails to start with no
explanation.

## What teammates see

A project-scoped server appears to everyone else as `⏸ Pending approval` in `claude mcp list`
until they accept it. That is Claude Code putting a human in the loop **on their side** — they
are being asked to trust your vetting. It is a courtesy to say, in the PR description, *what* the
server is and *why* you trust it, rather than leaving them to approve a name.

Approvals are also trust-scoped: `.mcp.json` approvals from settings checked into the repo do not
count until the workspace itself is trusted. A repo cannot approve its own servers on your
behalf — which is exactly the right default, and worth knowing before you debug "why is it
pending".

## Verify, then look at what you added

```bash
claude mcp list             # is it connected, or pending, or failing to start?
claude mcp get acme         # what tools did it actually bring — and what do they SAY?
/mcp                        # inside a session
```

`claude mcp get` is the step that matters: **read the tool descriptions**. They are now prompts
in your context (`references/vetting-servers.md`). A server that fails to start is a silent
capability gap — the session simply behaves as if the tool never existed.

## Removing one

```bash
claude mcp remove acme                  # local/user
# project scope: delete the entry from .mcp.json and commit
```

Removal is cheap and reversible — which is the argument for trying servers at **local** scope
first. Nothing here deserves a two-week evaluation; it deserves five minutes of vetting and an
easy exit.

## Making vetting mandatory (layer 5)

Everything above is a discipline, and a discipline is what people skip under deadline. An org
that needs it enforced uses managed settings:

```json
{
  "allowedMcpServers": [{ "serverName": "postgres-readonly" }],
  "deniedMcpServers": [{ "serverName": "*" }]
}
```

Default-deny, allow the vetted. This is the only mechanism that stops a determined engineer, and
it is deliberately outside this skill's reach — see [`docs/org-policy.md`](../../../docs/org-policy.md).
