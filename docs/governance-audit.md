# Seven-Layer Governance Audit — the `sdh` plugin

Audits this plugin against the **Seven Layers of AI Governance** from *The Governed Agent*
(Ch. 20), using the layer-by-layer audit method (Ch. 22). This is a **living document**: it is
the running backlog. Each improvement pass reads it first, implements the highest-value OPEN
items, then updates it. Never redo `DONE` work.

**The three questions** every incident maps to (Ch. 20):
1. What does the agent **know**? → Layer 1
2. What is it **able** to do? → Layers 2, 4, 5
3. What **checks** it? → Layers 3, 6, 7

**Lowest-effective-layer principle:** a rule belongs at the lowest ring that can enforce it;
depth (multiple layers) is reserved for the intolerable. Over-governing the trivial teaches
teams that governance is an obstacle — and teams that experience governance as obstruction
disable it.

---

## Layer scorecard

| # | Layer | What it governs | State | Notes |
|---|-------|-----------------|-------|-------|
| 1 | Context governance | What the agent **knows** | 🟢 Strong | 20 `std-*` path-scoped skills + `sdh-engineering-standards` + 37 workflow skills, wrapper-agnostic globs |
| 2 | Capability governance | What each **role** can do | 🟡 Partial | 12 agents with tool lists; **the Bash hole** unaudited |
| 3 | Runtime gates | What happens **as each action fires** | 🟢 Strong | 2 fail-closed PreToolUse gates, dispatcher, audit trail, 77 fixture tests |
| 4 | Permission boundaries | The harness's **own** enforcement | 🟢 Guarded | 24 denies (reference) + **sentinel check** now detects the plugin trap |
| 5 | Organizational policy | What **developers** can grant | 🟠 Thin | `managed-settings.template.json` exists but is minimal/undocumented |
| 6 | Human-in-the-loop | The **person**, for the irreversible | 🟢 Good | `ask` on deploys, migrations, direct pushes to protected branches |
| 7 | External verification | Everything **outside the session** | 🟡 Partial | CI now runs the plugin's own gates; branch protection is repo-side |

---

## DONE

### Layer 4 — the sentinel check (the plugin trap) — *2026-07-15*
The book calls this **non-optional**: *"A plugin without this check is distributing a false
sense of protection, which is worse than distributing none."* (Ch. 13)

A plugin **cannot ship `permissions`**. Our conversion left 24 deny rules that consumers must
copy by hand — and every visible signal (skills load, hooks fire) says "protected" while the
innermost ring is silently absent. Layers 3 and 4 correlate: our hooks were designed assuming
the permission floor existed underneath.

- `hooks/session-start-check.py` → `check_permission_sentinels()` reads the **consuming
  project's** `.claude/settings.json` and warns loudly on every session until fixed.
- Sentinels: `Read(**/.env)`, `Read(**/secrets/**)`, `Bash(sudo:*)`, `Bash(curl * | bash)` —
  a small, stable sample of the critical tiers (secrets / privilege / remote-exec).
- Handles: floor present (silent), sentinel missing, empty deny, no settings.json, unparseable.
- 6 fixture tests in `hooks/tests/run-all.py`; never blocks (exits 0).

### Layer 7 — CI on the plugin repo itself — *2026-07-15*
*"A governance repository without CI running its own gate tests is enforcing on its consumers
a discipline it does not practice on itself."* (Ch. 13)

`.github/workflows/ci.yml` — 4 jobs, on Linux (which also proves the cross-platform LF/UTF-8
contract that was previously only exercised on a Windows dev machine):
- **hook-fixtures** — the full fixture suite via `run-python.sh`
- **plugin-manifest** — plugin.json/marketplace.json validity, components at plugin root (never
  inside `.claude-plugin/`), and hook commands using `${CLAUDE_PLUGIN_ROOT}` (no stale paths)
- **skills-lint** — every `SKILL.md` + agent has valid frontmatter with name/description (70 files)
- **sentinel-guard** — the sentinel check itself cannot be silently deleted, and the reference
  deny floor it guards cannot lose a sentinel

---

## OPEN — prioritized backlog

### P1 · Layer 1 — extend skills with references (Ch. 7, progressive disclosure)
The book's **three tiers**: frontmatter description (always in context) → SKILL.md body (loaded
on trigger) → `references/*.md` (loaded only when the skill says to read them). Several skills
are single-file and carry detail in the body that belongs in tier 3; several `std-*` skills have
no `references/` at all. Audit each skill for tier placement, split oversized bodies, and add
references where depth exists. Consider the **rule-per-file** granularity variant (already used
well by `react-best-practices`, `terraform`, `atomic-design`) for the dense `std-*` skills.

### P1 · Layer 1 — the always-on regression from the plugin conversion
`std-code-standards`, `std-security`, `std-git-workflow`, `std-error-handling`, `std-agent-teams`
had **no `paths:`** as rules, so they always loaded. As plugin skills they are now model-invoked
(loaded only when judged relevant) — a real layer-1 weakening. Mitigation today: the hooks
(layer 3) still hard-enforce the critical parts. Options to evaluate: broad `paths:` globs, or
folding the non-negotiables into `sdh-engineering-standards` (which has a broad trigger).

### P2 · Layer 2 — the Bash hole (Ch. 8, Ch. 22, Ch. 25)
*"A read-only agent that has Bash is not read-only"* — `sed -i` is edit access, and content
guards matching only `Edit|Write` are bypassed. Audit all 12 agents: any agent documented as
review-only that carries `Bash` is a **read-only lie**. Fix by removing Bash or constraining it
with permission rules. Also re-ask, per Ch. 20, what gates assumed a narrower envelope.

### P2 · Layer 3 — hook DX + gate-pattern coverage (Ch. 9, Ch. 10, Ch. 25)
- Map our gates against the book's **six patterns**: completion gate ✅ (Stop), ask/human-in-loop
  ✅, **three-tier command gate** ⬜ (allow/ask/deny tiers for Bash — partially in permissions),
  context injection ✅, dispatcher ✅, audit trail ✅.
- DX: a documented hook dev workflow, a debug switch, and the Ch. 25 symptom→cause table
  (hook never fires / fires but never blocks / gate blocks everything) as a troubleshooting doc.

### P2 · Layer 7 — changelog as an interface (Ch. 13)
*"When a plugin bump changes what gets denied or how a gate behaves, that is a behavioral change
to every consuming repo's development process."* No `CHANGELOG.md` exists (and `CLAUDE.md`
mandates Keep a Changelog format). Add one, and treat gate/deny changes as interface changes.

### P3 · Layer 5 — governing the governors
`managed-settings.template.json` is minimal. Expand per Ch. 20's layer-5 section: non-overridable
org policy, MCP-server allowlists, forced authentication — calibrated, not maximal (over-coarse
policy drives shadow configurations).

### P3 · Layer 7 — repo-side controls
Branch protection + required reviews are GitHub settings, not code. Document the required posture
in the rollout guide (Ch. 23) so layer 7 is genuinely independent — *"a different person, or no
person at all."*

### P3 · Versioning / supply chain (Ch. 13)
*"Pin, don't float."* `plugin.json` pins `version: 1.0.0` ✅. Add release tagging guidance so
consumers pin a tag rather than tracking `main`.

---

## Correlated failure modes to watch (Ch. 20)

- **Plugin trap correlates 3+4** — now guarded by the sentinel. ✅
- **Widening an agent's tools correlates 2+3** — Bash reconstitutes a removed capability and
  routes around `Edit|Write` guards.
- **Human fatigue correlates 6+7** — if the same tired person clicks `ask` and approves the PR,
  that is one layer, not two.
- **Shared assumptions correlate everything** — every layer here assumes failures are *accidents*.
  Against prompt injection (Ch. 32), layers 1–2 fall together; only 3, 4, 6, 7 hold.
