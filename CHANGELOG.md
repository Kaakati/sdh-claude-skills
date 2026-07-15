# Changelog

All notable changes to the `sdh` plugin are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

> **This changelog is an interface.** When a release changes what gets **denied**, how a **gate**
> behaves, or what the **permission floor** contains, that is a behavioural change to every
> consuming repo's development process — read it as you would an API changelog.
>
> **⚠️ A plugin cannot ship `permissions`.** Any change under **Permission floor** below must be
> **copied by hand** into your project's `.claude/settings.json`. The SessionStart sentinel will
> tell you, by name, exactly which rules you are missing — including when a floor you copied
> earlier has gone **stale**.

## [Unreleased]

### Added
- **Layer 4 · Permission floor (ACTION REQUIRED)** — 6 new deny rules for irreversible Terraform.
  Copy these into your project's `.claude/settings.json` `permissions.deny`:
  ```
  Bash(terraform destroy:*)      Bash(terraform state mv:*)
  Bash(tofu destroy:*)           Bash(terraform state push:*)
  Bash(terraform state rm:*)     Bash(terraform force-unlock:*)
  ```
  Floor size: **24 → 30**. Previously `terraform destroy`, `state rm` and `force-unlock` were
  **completely ungated**.
- **Layer 3 · `terraform-command-gate.py`** — new PreToolUse three-tier gate (Ch. 10 Pattern 3).
  **Behavioural change:** `terraform destroy`, `state rm/mv/push`, `force-unlock` and
  `apply -auto-approve` are now **denied**; `terraform apply` now **asks** with a review checklist;
  the read-only surface (`plan`, `validate`, `fmt`, `output`, `state list|show`) is unaffected.
  `terraform plan -destroy` is explicitly **allowed** — it only previews. Fail-closed.
- **Layer 4 · Sentinel staleness detection** — the SessionStart sentinel now diffs your floor
  against the plugin's own reference floor, so it reports a **stale** floor (copied from an older
  version) and names the exact missing rules — not just an absent one.
- **Layer 7 · CI** (`.github/workflows/ci.yml`) — the plugin now runs its own gates: hook fixture
  suite, manifest/structure validation, skill+agent frontmatter lint, tier discipline (every rule
  indexed, no monolith pointers, all references resolve), and a sentinel-presence guard.
- **Layer 1 · Progressive disclosure** — 7 dense `std-*` skills split into a tight body + 28
  decision-shaped, example-paired references (~9.3k lines of tier-3 that cost nothing until needed).
- **Storytelling UI framework** — `skills/ui-ux-patterns/references/storytelling-ui.md`, applied
  across the UI/UX skills.

### Changed
- **Layer 3 · `deployment-gate.py` no longer decides Terraform** — `terraform-command-gate.py` owns
  that surface. Previously both fired: two prompts for one `terraform apply` (approval fatigue), and
  contradictory decisions on `-auto-approve` (ask vs deny).
- **Layer 3 · Hook dispatch consolidated** — 12 advisory checkers now run in one process via
  `post-edit-dispatch.py` (13 PostToolUse entries → 2). Same warnings, ~12 fewer Python cold-starts
  per edit.
- **Layer 1 · Rule-per-file granularity restored** — 5 skills pointed at compiled `full-guide.md`
  monoliths (up to 2934 lines); their bodies now index `rules/<id>.md`, so a task loads one ~60-line
  rule instead of skimming a monolith.
- **Layer 1 · Wrapper-agnostic detection** — conventions load by canonical structure + marker files
  (`Gemfile`, `next.config.*`, `vite.config.*`, `metro.config.js`), **not** by a forced directory
  name. Rails works under `backend/`, `api/`, or the repo root. Directory names are no longer a
  contract.

### Fixed
- **Layer 3 · Silent failure eliminated (important)** — advisory hooks failed **open and silently**,
  so a crashed checker was indistinguishable from a passing one and could enforce nothing, forever,
  with every signal green. All fail-open paths now emit `HOOK ERROR: <checker> failed …`.
  `audit-logger` was the sharpest case: a failed write left **invisible holes in the audit trail**
  plus false confidence it was complete.
- **Layer 2 · The Bash hole** — `clean-architecture` carried `Bash` (write access via `sed -i`) but
  never used it → removed; it is now read-only by capability. `security-auditor` keeps Bash (it
  needs `git diff`/`npm audit`) but no longer implies read-only.
- **Layer 1 · terraform index drift** — the body named **26 rules that had no file** while **26 real
  rule files were invisible**. Regenerated from the real files; CI now guards it.
- **Cross-platform** — hooks emit valid UTF-8 on Windows (`PYTHONUTF8=1`); `.gitattributes` pins
  `*.sh` to LF so `run-python.sh` works under Git Bash/MSYS2.

### Removed
- **`permissionMode` from all 10 agents that carried it** — the field is silently ignored for
  plugin-shipped agents, so advertising it was theater. **No capability change:** the 4 former
  "plan mode" agents carry `tools: Read, Grep, Glob` and are read-only by capability, which is the
  real control. Docs corrected (`plan mode` → `read-only`); CI now rejects `permissionMode`,
  `hooks`, and `mcpServers` on agents, and any agent without a `tools` list.

### Known gaps
- 13 `std-*` skills are still single-file; several references exceed the ~300-line budget.

---

## [1.0.0] — 2026-07-15

### Added
- Initial release as a Claude Code plugin: 58 skills (37 workflow + 20 `std-*` convention +
  `sdh-engineering-standards`), 12 agents, and quality-gate hooks.
- SessionStart **sentinel check** — detects the "plugin trap" (a plugin cannot ship `permissions`,
  so an uncopied deny floor is invisible while every other signal says "protected").
- Fail-closed security gates: `security-scan`, `dangerous-command-blocker`.
