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
| 1 | Context governance | What the agent **knows** | 🟢 Strong | 20 `std-*` + 37 workflow skills; 7 now three-tier (28 refs); rule-per-file granularity restored across 5 skills; CI guards tier discipline |
| 2 | Capability governance | What each **role** can do | 🟢 Good | Bash hole audited + closed; capability enforced by tool lists (not the dead `permissionMode`) |
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

### Layer 1 — Ch. 7 progressive disclosure: 7 skills split into three tiers — *2026-07-15*
All 20 `std-*` skills were single-file (tier-2 bodies carrying tier-3 depth). Applied the Ch. 7
**placement test** to the 7 densest and split them:

| Skill | Body (before → after) | References |
|---|---|---|
| std-nextjs | 217 → 114 | 4 (1324 lines) |
| std-design-system | 208 → 126 | 4 (1108) |
| std-api-design | 194 → 117 | 4 (1549) |
| std-testing | 177 → 113 | 4 (982) |
| std-phlex-conventions | 167 → 119 | 4 (1407) |
| std-reactjs | 154 → 135 | 4 (1365) |
| std-infrastructure | 148 → 86 | 4 (1606) |

**28 references, ~9.3k lines of tier-3** that cost nothing until the task arrives. Each body now
ends with the index hinge (`## Deep guides (read on demand, do not preload)`); each reference is
self-contained (zero back-references), decision-shaped (`## Decision: …`), and example-paired
(bad/good compilable pairs). Frontmatter/triggers byte-identical on all 7 (verified vs HEAD).
`std-nextjs` **net-gained** rules (authorize inside the server action, `import 'server-only'`, no
secrets behind `NEXT_PUBLIC_`, don't rebuild the Rails API in `app/api`).

Adversarial verification caught and we fixed **2 real content losses**: `std-testing` lost "test
containers / in-memory databases" (restored to `test-strategy.md`); `std-reactjs` lost
`"strict": true` and the `@/`→`src/` path alias (restored to the body).

### Layer 1 — the always-on regression, resolved by the placement test — *2026-07-15*
The 5 rules that had no `paths:` became model-invoked in the plugin conversion. Resolved per Ch. 7:
- `std-code-standards`, `std-security` — *apply to most source tasks* → broad source globs
  (`**/*.{rb,py,ts,tsx,js,jsx}`), restoring layer-1 teaching at the moment of relevance.
- `std-error-handling` — *subset-scoped* → correctly model-invoked.
- `std-git-workflow`, `std-agent-teams` — **action-scoped, not file-scoped**; no glob can express
  them → correctly model-invoked.
- Their *must-hold* parts sit at layers 3/4 (security-scan, code-quality-checker,
  error-handling-checker, pre-commit-check) — exactly where the placement test's last row says
  they belong: *"must hold even if never read → not context at all."* So this was a **teaching**
  gap, not an enforcement gap.

### Layer 2 — the Bash hole, audited and closed — *2026-07-15*
Ch. 8's example of "an agent definition that looks governed and is not" is **literally our
`security-auditor`** (same name, same `tools: Read, Grep, Glob, Bash`).
- `clean-architecture` — carried `Bash` but **never used it** (pure unused write access:
  `sed -i`, `echo > file`). **Removed** → read-only by *capability*, per Ch. 8's "tool lists
  remove abilities rather than discourage them."
- `security-auditor` — genuinely needs Bash (`git diff`, `npm audit`). **Kept, theater ended**:
  an explicit capability-boundary section states it is NOT read-only and is findings-only.
- Builders (`devops-engineer`, `phlex-developer`, `test-generator`) hold Bash + Write/Edit
  honestly. `incident-responder` keeps Bash for diagnostics.

### Layer 1 — rule-per-file granularity restored (Ch. 7) — *2026-07-15*
All 5 rule-per-file skills indexed their rule ids in the body but then pointed the model at a
**compiled monolith** (`references/full-guide.md`), defeating the granularity the `rules/` dir
buys. Ch. 7: *"a list task loads only the list file — the whole of it signal"* and *"past a few
hundred lines the model's mid-task read starts skimming."*

| Skill | Body pointed at | Now loads |
|---|---|---|
| react-best-practices | 2934-line monolith | ~52-line rule file (1 of 57) |
| react-native-best-practices | 2897-line monolith | 1 of 36 |
| atomic-design | 1218-line monolith | 1 of 10 |
| composition-patterns | 946-line monolith | 1 of 8 |
| terraform | 679-line monolith | ~102-line rule file (1 of 47) |

The `full-guide.md` files are **content duplicates** of `rules/` (rule headings appear verbatim).
All 5 bodies now index `rules/<id>.md` and no body advertises a monolith.

### Layer 1 — index drift: terraform was 26/47 broken (Ch. 6 maintenance problem) — *2026-07-15*
The new CI guard immediately caught a **pre-existing** defect: `terraform`'s body named **26 rules
that had no file** (broken pointers — the model told to read files that don't exist) while **26
real rule files were invisible** (never indexed, so the model never knew they existed). The rule
files had been renamed and the index never followed; nothing caught it because no guard existed.
Index regenerated from the 47 real files (titles from their frontmatter) → 0 broken, 0 invisible.
Also indexed 3 orphaned React Native rules (`state-ground-truth`, `scroll-position-no-state`,
`design-system-compound-components`).

### Layer 7 — CI tier-discipline guard (Ch. 22 standing audit) — *2026-07-15*
`.github/workflows/ci.yml` now fails the build when (a) a `rules/<id>.md` exists that its SKILL.md
never indexes, or (b) a body points at a compiled monolith. This is the drift that produced the
terraform defect; it can no longer regress silently.

## OPEN — prioritized backlog

### P1 · Layer 1 — finish progressive disclosure (13 skills remain single-file)
7 of 20 `std-*` skills are now three-tier. The remaining 13 (`std-rails-conventions`,
`std-react-native`, `std-database`, `std-accessibility`, `std-i18n`, `std-clean-architecture`,
`std-monitoring`, `std-terraform-conventions`, `std-security`, `std-code-standards`,
`std-error-handling`, `std-git-workflow`, `std-agent-teams`) still carry all depth in tier 2.
Apply the same placement test. Note `std-security`/`std-code-standards` now load on *every*
source edit — their bodies must stay tight, so they are the highest-priority splits.

### P1 · Layer 1 — delete the duplicate `full-guide.md` monoliths (pending redundancy audit)
The 5 monoliths (2934/2897/1218/946/679 lines) are now **unreferenced** — no body points at them,
so nothing loads them. But they remain on disk as content duplicates of `rules/`, which is Ch. 6's
maintenance problem: two copies drift (exactly how terraform's index broke). Before deleting, run
a proper redundancy audit — the forward check showed rule headings appear verbatim in the guides,
but heading *shape* differs, so prove content coverage rule-by-rule first. Do not delete blind.

### P1 · Layer 1 — reference sizing overruns (Ch. 7: "under a few hundred lines")
From the Ch. 7 split; the book's split signals apply (sections never needed together / a second
stack):
- `std-infrastructure/terraform-aws.md` **560** (1.9x) — split Terraform-mechanics ↔ AWS-modules
- `std-infrastructure/cicd-and-deploys.md` **492** — split CI/OIDC/ECS ↔ frontend deploys
- `std-api-design/errors-and-validation.md` **457** — split at the Rails ↔ TS seam
- `std-phlex-conventions/component-levels.md` **430** — primitives ↔ composites
- `std-reactjs/forms-and-testing.md` **399** — forms ↔ testing
- Also >300: pagination 387, rendering 386, rate-limiting-and-health 380 (two concerns),
  state-and-data 368, stimulus-and-turbo 375, server-actions 340, versioning 325,
  variants-and-styling 313, charts-and-animation 312, middleware-seo-deploy 309
- Pre-existing, also >300: `theming/platform-integration.md` 854, `phlex-dev/component-examples.md`
  802, `phlex-dev/phlex-patterns.md` 775, `theming/design-tokens.md` 458, `theming/theme-presets.md` 445

### P1 · Layer 1 — finish progressive disclosure (13 skills remain single-file)
`std-rails-conventions`, `std-react-native`, `std-database`, `std-accessibility`, `std-i18n`,
`std-clean-architecture`, `std-monitoring`, `std-terraform-conventions`, `std-security`,
`std-code-standards`, `std-error-handling`, `std-git-workflow`, `std-agent-teams`. Apply the
placement test — but honour Ch. 7's **merge signal**: a body of ~100 lines that applies to every
task the skill triggers on is already correct as "a page of rules". Do not force-split.

### P2 · Layer 2 — `permissionMode` is DEAD in plugin agents (docs claim otherwise)
Plugin-shipped agents do **not** support `permissionMode` — it is silently ignored ("for security
reasons", per the plugins reference). 4 agents carry `permissionMode: plan`
(`architecture-advisor`, `clean-architecture`, `design-critique`, `design-system-architect`) and
CLAUDE.md/README advertise "(Opus, plan mode)" — **now a false claim**. It was only load-bearing
for `clean-architecture` (the only plan agent with Bash), and removing Bash fixed that properly.
The other 3 are read-only by tool list anyway, so the field is redundant, not dangerous. Action:
strip the dead field (silently-ignored controls are theater) and correct the "plan mode" claims.

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
