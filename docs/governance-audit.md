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
| 2 | Capability governance | What each **role** can do | 🟢 Good | Bash hole closed; dead `permissionMode` removed; capability enforced by `tools`, guarded by CI |
| 3 | Runtime gates | What happens **as each action fires** | 🟢 Strong | all 6 Ch. 10 gate patterns present; 3 fail-closed gates; fail-open paths visible; 103 fixture tests |
| 4 | Permission boundaries | The harness's **own** enforcement | 🟢 Guarded | 30 denies (reference); sentinel detects an **absent OR stale** floor by diffing the plugin's own reference |
| 5 | Organizational policy | What **developers** can grant | 🟠 Thin | `managed-settings.template.json` exists but is minimal/undocumented |
| 6 | Human-in-the-loop | The **person**, for the irreversible | 🟢 Good | `ask` on deploys, migrations, direct pushes to protected branches |
| 7 | External verification | Everything **outside the session** | 🟢 Good | 5 CI jobs incl. changelog-as-interface enforcement; branch protection still repo-side |

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

### Layer 1 — redundancy audit: the monoliths were NOT redundant (deletion averted) — *2026-07-15*
Iteration 3 deferred deleting the 5 `full-guide.md` monoliths pending proof. The audit ran
chunk-by-chunk (paragraphs + code blocks, normalized) against the union of `rules/*.md`:

| Skill | full-guide covered by rules/ | Verdict |
|---|---|---|
| react-best-practices | 89.8% | unique = TOC/preamble scaffolding |
| react-native-best-practices | 89.8% | unique = scaffolding |
| composition-patterns | 79.2% | unique = scaffolding |
| **atomic-design** | **32.8%** | **67% UNIQUE — real 4-platform component code** |
| **terraform** | **7.7%** | **92% UNIQUE — real HCL playbooks** |

**Safe to delete: none.** The iteration-3 hypothesis ("full-guide duplicates rules/") was **wrong**
for atomic-design and terraform — the forward heading check was misleading. Deleting blind would
have destroyed 84 unique terraform chunks (`versions.tf`/backend blocks, `terraform import` recipes,
`moved {}` blocks, env layout) and 43 atomic-design chunks.

**A regression this exposed:** iteration 3's removal of the full-guide pointer *orphaned* that
unique content — reachable by nothing. Repaired, not reverted:
- `terraform` → `repository-layout.md` (175) + `enforcement-and-tooling.md` (70); monolith deleted
- `atomic-design` → `choosing-the-atomic-level.md` (164) + `diagnosing-misplaced-components.md` (166)
  + `nextjs-server-client-boundary.md` (106); monolith deleted
All under the ~300-line budget, decision-shaped, indexed. Content preserved (verified chunk-by-chunk).

### Layer 1 — 3 contradictions caught by adversarial verify (terraform) — *2026-07-15*
The rescue inherited the *old guide's* patterns without reconciling against the rules that
superseded them — the model would have gotten **opposite answers to the same question**
(contradictory guidance is worse than none). All three reconciled toward the rule (the indexed,
authoritative source):
1. **Tags** — reference prescribed `locals.common_tags` merged per resource; `resource-required-tags`
   prescribes provider-level `default_tags` and argues *against* per-module maps → reference now
   teaches `default_tags`.
2. **`terraform.tfvars`** — reference banned it absolutely; the rule's canonical tree uses it. The
   ban was *sound but over-broad*: auto-load is only a footgun in the **single-root** variant. With
   separate root modules (our default) the auto-loaded file is by construction that env's values →
   warning now correctly scoped to the single-root pattern.
3. **Backend placement** — reference put `backend "s3"` in `versions.tf`; the rule's tree has a
   separate `backend.tf` → reference aligned (the `key` is the only per-env line; isolating it makes
   the diff obvious).

### Layer 7 — CI guard extended: references must resolve — *2026-07-15*
The tier-discipline guard now also fails when a body indexes a reference that does not exist. Built
to handle **cross-skill** references (`../other/references/x.md`, `@skills/other/references/x.md`) —
a deliberate pattern where a framework has one canonical home (storytelling-ui.md). A first naive
version produced 4 false positives on exactly those; fixed before shipping, because a guard that
cries wolf is the kind teams disable.

### Layer 3 — silent failure eliminated: dead gates can no longer look green — *2026-07-15*
Ch. 9: *"Silent failure is invisible failure. A fail-open hook that swallows its own exceptions
looks identical to one that passed"* — so a dead gate masquerades as a green one for months.

**This was a real defect in code from iteration 1.** Proven: a checker raising `RuntimeError`
exited 0 with empty stdout — literally indistinguishable from a clean pass. Every advisory checker
routes through `run_post_checker`, and the dispatcher swallowed checker exceptions with a bare
`except: continue`. A silently broken `code-quality-checker` would have enforced nothing, forever,
with every signal green.

Fixed via a single emitter, `_hooklib.hook_error(label, exc)`:
- `run_post_checker` — reports and names the failing script, still exits 0 (fail-open preserved)
- `post-edit-dispatch` — reports the failing checker instead of `continue`-ing past it; also
  reports a module that exposes no `check()`
- `audit-logger` — the sharpest case. Its `except (IOError, OSError): pass` meant a failed write
  left **invisible holes in the audit trail plus false confidence it was complete** — strictly
  worse than no trail. It also had **two unguarded paths** (`os.makedirs` and `json.load`) *outside*
  the try, which crashed with exit 1 and no message. Whole path now guarded; every gap announces.
- `vague-request-detector` — had zero exception handling; a malformed event dumped a raw traceback
  at the user. Now one actionable line.
- A **healthy** hook still emits nothing — the signal must not become noise.

6 fixture tests added (`[fail-open visibility]`), harness 77 → **83**.

### Layer 3 — fail stances decided, not defaulted (Ch. 9) — *2026-07-15*
Audited all 27 hooks. 12 advisory checkers + 5 gates now have explicit, chosen stances; the table
is documented in `hooks/README.md` with the reasoning (*"the linter's crash should cost you a lint
report, not a session"*; *"a fail-closed formatter is an outage generator"*; the availability cost
of fail-closed is the correct trade only for the small deny tier).

### Layer 3 — the three-tier command gate: the last missing Ch. 10 pattern — *2026-07-15*
**The gap was real and serious.** Terraform had tier-1 (allow, via `permissions`) and tier-2 (ask,
via `deployment-gate`) but **no deny tier** — probed and confirmed:

| command | before |
|---|---|
| `terraform destroy` | **ALLOWED — nothing stopped it** |
| `terraform state rm aws_db_instance.main` | **ALLOWED** |
| `terraform force-unlock 1234` | **ALLOWED** |
| `terraform apply -auto-approve` | only `ask` (the book says deny) |

**Lowest-effective-layer analysis first** (as promised, rather than reflexively writing a hook):
- read-only surface → already allow-listed in `permissions` (layer 4) ✅ correct, lowest ring
- deny the irreversible → **added to `permissions.deny`** (layer 4: lower, surer, cannot be coded
  wrong): `terraform destroy`, `tofu destroy`, `state rm/mv/push`, `force-unlock`
- what a tool+target pattern **cannot** express → the hook (layer 3): `-auto-approve` is a flag
  anywhere in the string, not a prefix; and the `ask` tier needs a reasoned checklist
- The overlap is deliberate: destroy/state-surgery are catastrophic, and *"the catastrophic rules
  get several"* (Ch. 20). A plugin cannot ship permissions, so if a consumer never copied the floor,
  the hook is the only thing standing there.

`hooks/terraform-command-gate.py` — **fail-closed** (*"a gate guarding `apply` that crashes must
deny"*), registered on PreToolUse:Bash, **20 fixture tests**.

**Improved on the book's template:** it regexes a bare `destroy`, which would deny
`terraform plan -destroy` — a read-only *preview*. Ours matches `destroy` only as a subcommand, so
the preview falls through. Carries the book's honest caveat: regex over shell strings is defeatable
by wrappers/aliases; this is defense in depth, not a wall — its value is catching the *model's*
ordinary mistakes cheaply and deterministically.

### Layer 3/6 — one concern, one owner: removed a double-prompt — *2026-07-15*
Registering the gate exposed that `deployment-gate` **also** decided `terraform apply`:
- `terraform apply` → **two prompts for one command** — approval fatigue is exactly how you get
  "the human who stops reading" (Ch. 20, layer 6)
- `terraform apply -auto-approve` → the two hooks **disagreed outright** (ask vs deny)

Terraform removed from `deployment-gate` entirely; the dedicated three-tier gate owns that surface.

### Layer 4 — the sentinel now detects a STALE floor, not just an absent one — *2026-07-15*
Last iteration grew the deny floor 24 → 30 and I recorded the gap it created: consumers who copied
the **old** floor are silently missing the new terraform denies, and a 4-rule hardcoded sample can
prove a floor is ABSENT but never that it is CURRENT. A floor that silently went stale is the same
invisible gap in slower motion.

Fixed by inverting the check: `_plugin_reference_floor()` reads **the plugin's own reference**
`.claude/settings.json` (located from `__file__`, so it needs no env var and works under
`--plugin-dir`, a marketplace install, or a plain clone) and **diffs** the consumer's floor against
it. The check is therefore self-maintaining — it can never drift from the floor it guards. The
hardcoded sample survives only as a fallback when the reference is unreadable.

Output distinguishes the two cases and is actionable:
> GOVERNANCE GAP: this project's permission floor is **STALE** … Missing **6 of 30**:
> `Bash(terraform destroy:*)`, `Bash(tofu destroy:*)`, `Bash(terraform state rm:*)` …

3 fixture tests added (stale detected / empty reads as absent, not stale / names the exact rules).

### Layer 7 — the changelog as an interface (Ch. 13) — *2026-07-15*
*"When a plugin bump changes what gets denied or how a gate behaves, that is a behavioural change to
every consuming repo's development process. Document it as you would an API change — because for
your teammates' agents, it is one."*

`CHANGELOG.md` (Keep a Changelog) added, written for the consuming team rather than for us: it opens
with the plugin-trap warning and marks the terraform denies **ACTION REQUIRED** with the exact rules
to paste. Behavioural gate changes (destroy/state-surgery/-auto-approve now denied; apply now asks;
`plan -destroy` still allowed) are called out as such.

**Enforced, not just written**: a new CI job fails any PR that changes the permission floor or a
gate's behaviour without updating `CHANGELOG.md`. Because a plugin cannot ship `permissions`, an
undocumented floor change is one consumers can neither see nor copy — it just silently goes stale.

### Layer 3 — hook DX: the dev loop, the capture tool, and the Ch. 25 symptom table — *2026-07-15*
The explicit half of the mandate ("enhance the DX to the utmost level"), and the last Layer-3 item.

- **`hooks/capture-event.py`** — Ch. 9's step 1 as a first-class tool. Register it temporarily,
  trigger the tool once, and a *real* event lands in `hooks/tests/fixtures/` (named
  `PreToolUse-Bash-<ts>.json`). Then develop against the fixture: a **sub-second loop** instead of
  "edit, start a session, trigger the tool, squint at the output" — a minute-long loop you run fifty
  times. Verified end-to-end: captured a real event, replayed it into the terraform gate, got the
  deny. Fixtures are gitignored (dev artifacts).
- **`docs/hook-development.md`** — the dev loop, the *observe, don't guess* first move (check
  `/hooks`; run the hook by hand — *"the single most useful diagnostic"*, separating "the hook has a
  bug" from "the hook isn't being invoked"; read the agent definition, not your memory of it), and a
  **symptom→cause table** written for THIS repo (hooks live in `hooks/hooks.json` not settings; the
  `${CLAUDE_PLUGIN_ROOT}` requirement; MSYS-path and cp1252 gotchas that have actually bitten us).
- Linked from `hooks/README.md`; refreshed stale content there (it still claimed checker crashes are
  "swallowed" — fixed in iteration 5 — and used pre-plugin `.claude/hooks/` paths).

### Layer 3 — every deny reason must name a remedy (Ch. 25) — *2026-07-15*
*"The model argues with a denial"* — root cause: the reason names **what** is forbidden but not
**what to do instead**. *"'Denied' invites retries; 'denied because X, do Y instead' invites Y."*

Audited all 9 deny reasons. One real defect: `pre-commit-check`'s force-push deny stated only the
prohibition ("Force pushing to main/master/develop/release is prohibited") — an invitation to
retry variations. Now names the remedy: `git revert <sha>` + a PR for a shared branch, or
`--force-with-lease` on your *own* feature branch. A standing test
(`[deny reasons must name a remedy]`) audits every `hooklib.deny()` call so this cannot regress.

### Layer 2 — the dead `permissionMode` removed (theater) — *2026-07-15*
`permissionMode` is **not supported** for plugin-shipped agents — it is silently ignored ("for
security reasons"). 10 agents carried it (4 with `plan`), and CLAUDE.md/README advertised
"(Opus, plan mode)" on 4 agents: **a control that does not exist**. Theater in a security control
is worse than nothing, because it changes how much you check.

- Removed the field from all 10 agents. Capability is unaffected: the 4 "plan mode" agents carry
  `tools: Read, Grep, Glob` — **read-only by capability**, which is the real control; plan-mode was
  only ever discouraging what the tool list already removes (Ch. 8).
- Corrected 11 doc claims (`plan mode` → `read-only`) across CLAUDE.md and README.
- **CI guard added** (`agent-frontmatter`): fails if any agent carries `permissionMode`, `hooks`, or
  `mcpServers` (all silently ignored for plugin agents), or ships without a `tools` list.

### Layer 7 — the CI workflow itself is now tested — *2026-07-15*
While adding the guard above I **broke `ci.yml`** (a generator turned `
` into a real newline,
splitting a Python statement). It was caught locally — but the near-miss is the lesson: **a workflow
that does not parse is simply never run.** GitHub reports nothing, every local signal stays green,
and the layer-7 backstop is *gone*. That is precisely the "dead gate masquerading as a green one"
failure, one layer up — so it gets the same treatment.

`[CI workflow — layer 7 must not vanish silently]`: asserts `ci.yml` parses, that the required jobs
(`hook-fixtures`, `plugin-manifest`, `skills-lint`, `sentinel-guard`) still exist, and that every
inline CI python block is syntactically valid. Verified by injecting a syntax error: the test failed
loudly, then the file was restored.

## OPEN — prioritized backlog

### P1 · Layer 1 — finish progressive disclosure (13 skills remain single-file)
7 of 20 `std-*` skills are now three-tier. The remaining 13 (`std-rails-conventions`,
`std-react-native`, `std-database`, `std-accessibility`, `std-i18n`, `std-clean-architecture`,
`std-monitoring`, `std-terraform-conventions`, `std-security`, `std-code-standards`,
`std-error-handling`, `std-git-workflow`, `std-agent-teams`) still carry all depth in tier 2.
Apply the same placement test. Note `std-security`/`std-code-standards` now load on *every*
source edit — their bodies must stay tight, so they are the highest-priority splits.

### P2 · Layer 1 — the 3 remaining `full-guide.md` monoliths (~90% scaffolding)
`react-best-practices` (2934), `react-native-best-practices` (2897), `composition-patterns` (946)
are ~80-90% covered by `rules/`; their unique residue is document scaffolding (the "Note: this
document is mainly for agents and LLMs" preamble, the auto-generated TOC) **plus substantive
section preambles** (e.g. "Waterfalls are the #1 performance killer..."). They are now unreferenced,
so nothing loads them — no context cost, but they will drift (this is exactly how terraform's index
broke). Fix: fold the section preambles into the body's section headings (tier-2 material — they
apply to the whole section), then delete. Do not delete before migrating the preambles.

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
