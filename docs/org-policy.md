# Layer 5 — Organizational Policy (governing the governors)

Managed settings: deployed centrally, **non-overridable** by any user or project. This is the layer
that governs *the humans configuring the agents*, not the agents' actions — the rules that must hold
**regardless of what any individual engineer configures**, because they protect against **the
engineer's mistake**, not the agent's.

Template: [`.claude/managed-settings.template.json`](../.claude/managed-settings.template.json)
Deploy to `/etc/claude-code/managed-settings.json` (Linux/macOS) or
`C:\ProgramData\ClaudeCode\managed-settings.json` (Windows).

---

## Read this before you deploy anything

> Layer 5 is **the layer teams reach for last and misuse first.**

**The discipline is: enforce the intolerable, permit the rest.**

The misuse is **maximalism** — locking down so hard that real teams can't do real work, which drives
them to shadow tooling *outside* the governed environment. That is the **worst** outcome available to
you, because shadow tooling has **no layers at all**. An org policy that blocks the genuinely
dangerous and trusts teams with the merely serious keeps people inside the system, where the other
six layers can protect them. An org policy that treats every engineer as an adversary loses them.

If you take one thing from this page: **a gap is recoverable; shadow tooling is not.**

---

## The four legitimate uses

Narrow, and real. Everything else belongs in the project's own `.claude/settings.json`.

### 1. Force authentication
So nobody runs against production with personal credentials.
```json
{ "forceLoginMethod": "console", "forceLoginOrgUUID": "YOUR-ORG-UUID" }
```

### 2. Pin a security floor no local override can weaken
```json
{ "disableBypassPermissionsMode": "disable",
  "allowManagedPermissionRulesOnly": false,
  "permissions": { "deny": ["Read(**/.env)", "Bash(sudo:*)", "Bash(terraform destroy:*)", "…"] } }
```

**This is the org-scale answer to the plugin trap.** A plugin *cannot* ship `permissions`, so every
consuming project must copy the deny floor by hand — and this plugin's SessionStart **sentinel**
exists only to catch the projects that didn't (and the ones whose copy went stale). Deployed at layer
5, the floor simply **exists everywhere**, non-overridably: no copying, no drift, no sentinel needed.
The sentinel remains the safety net for teams *without* managed settings.

> **Keep this list to the catastrophic tier only** — secrets, privilege escalation, remote code
> execution, irreversible infrastructure. The plugin's fuller floor (`dist/`, `build/`, `coverage/`
> Read denies) is a **context-economy** concern, not a security one. Putting it in non-overridable
> org policy is exactly the maximalism above: it blocks nothing dangerous and annoys everyone.

**`allowManagedPermissionRulesOnly: false` is deliberate.** The deny list is a *floor*, not a
*ceiling* — projects must stay free to add their own rules. Setting it `true` says "only the org may
define permissions", which is how you lose the teams that need one project-specific rule.

### 3. Restrict which MCP servers may be connected
Supply-chain control at org scale — server vetting made **mandatory** rather than advisory.
```json
{ "allowedMcpServers": [{ "serverName": "postgres-readonly" }],
  "deniedMcpServers": [{ "serverName": "*" }] }
```
An MCP tool description is a **prompt the model obeys**. An unvetted server is an unvetted
instruction source, so this is a genuine supply-chain boundary, not bureaucracy.

### 4. Require the audit trail
The artifact you reconstruct an incident from must not be optional.
```json
{ "enabledPlugins": { "sdh@sdh-claude-skills": true } }
```
This keeps `audit-logger.py` registered on every session — and it **announces any gap** rather than
failing silently, so a broken trail is visible instead of quietly incomplete. **Pin a version**
rather than tracking a moving target: an unpinned governance plugin means a standards change (or a
hook bug) reaches every engineer the moment it is pushed, with no review gate between commit and
production behaviour.

---

## What does NOT belong at layer 5

| Tempting | Why not | Where it belongs |
|---|---|---|
| Build-artifact `Read` denies (`dist/`, `coverage/`) | Context economy, not security. Blocks nothing dangerous. | Project `.claude/settings.json` |
| Style/convention rules | A hard deny on a style choice teaches the team that governance is an obstacle | A skill (layer 1) |
| `allowManagedPermissionRulesOnly: true` | Removes a team's ability to add one project-specific rule | — (don't) |
| `allowManagedHooksOnly: true` | Blocks project-specific gates a team genuinely needs | — (don't) |
| Blanket Bash denial | Real work stops; shadow tooling starts | The three-tier command gate (layer 3) |

---

## How layer 5 relates to the others

- **It does not replace layers 1–4** — it guarantees a *minimum* under them.
- **It is distinct from layer 4** because it governs *the humans configuring the agents*, not the
  agents' actions. Layer 4 is what an agent may do; layer 5 is what an engineer may *permit* an agent
  to do.
- **Its failure mode is being too coarse to fit real teams**, which drives shadow configurations.
  Calibrate it — do not maximize it.

## Rollout

Deploy the floor **before** a wide rollout, not after. During a multi-team rollout is exactly when
the copy-the-permissions step gets skipped — layer 5 removes the step entirely, and the sentinel
covers whoever isn't under managed settings yet.
