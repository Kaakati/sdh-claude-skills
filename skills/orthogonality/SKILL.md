---
name: orthogonality
description: Detect and resolve non-orthogonal architecture and database elements before they erode the design — a second model or table for an existing concept, one fact stored in two places, a second library or pattern for a concern already covered (HTTP client, state, auth, pagination, error envelope, charts), imports across bounded contexts, new dependency cycles, a service writing another context's tables, and code in the wrong context. Use before adding a model, table, column, library, API client wrapper, error handler, or cross-module import; when someone asks "do we already have a customer model", "is this a duplicate", "which library do we use for X", "why are there two clients", "check for architecture erosion", "bounded context violation", "dependency cycle", "declare a read model", or "one mechanism per concern"; and whenever a hook reports an ORTHOGONALITY finding.
model: sonnet
argument-hint: "a concept name, a path, or --changed-since <ref>"
allowed-tools: Read, Grep, Glob, Bash(bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/*)
---

# Orthogonality

Each piece of knowledge has one authoritative home, and each property has one way to change it.
This skill finds where a codebase has grown a second one, and sends the fix to the skill that owns it.

| Policy | What erodes it |
|---|---|
| **One concept → one owner** | a second model or table for a concept that exists; one fact stored in two places |
| **One concern → one mechanism**, per deployable | a second HTTP client, state store, job system, error-envelope builder or pagination style |
| **Dependencies follow the declared context map** | imports or writes across bounded contexts; new cycles; code in the wrong context |

## 1. What this skill owns, and what it does not

It owns **detection**, the declaration file for intentional exceptions, and the scans. Every **fix**
stays with its owner — read that skill rather than restating it. House library choices come from
"Library preferences" in `sdh-engineering-standards` (machine-readable copy: `hooks/_mechanisms.json`).

| Finding family | Fix owned by |
|---|---|
| layers inside a context | `std-clean-architecture` |
| cross-package imports, the one-version policy | `monorepo-architect` |
| relationships, indexes, polymorphic and JSONB rules | `std-database` |
| migration operations, locks, backfills | `db-migration` |
| the error envelope, the pagination contract | `std-api-design` |
| the DRY principle | `std-code-standards` |
| library conventions per stack | `std-rails-conventions`, `std-phlex-conventions`, `std-reactjs`, `std-nextjs`, `std-react-native`, `std-fastapi`, `std-django`, `std-shadcn-ui` |
| the ADR for an exception that is kept | `architecture-advisor` |

## 2. What already runs, without asking

- **After each edit**, an advisory checker compares the edited file with the architecture index and
  adds at most 3 `ORTHOGONALITY [<ID> <slug>]` lines: new `warn` findings, each once per session.
- **At session start**, the index refreshes in the background: a per-project cache under
  `${CLAUDE_PLUGIN_DATA}`, never written into the repo.
- **After a Bash install or generator** (`npm install ky`, `rails g model Client`), a background
  watcher refreshes the index and wakes Claude only when something new turned up — at most 5 lines.
- Nothing asks or denies; `SDH_ORTHOGONALITY=off` switches it all off. Cross-file clones (DK6),
  whole-codebase detectors and community tools run only in scans.

## 3. Look before you add

Before creating a model or table, look the concept up:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_index.py --name Client --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

It lists exact, near-name and synonym matches with context, table, columns and `path:line`. A match
in the **same** context: extend it, or declare the second one (§5). A match in another **declared**
context is legitimate — bounded contexts may model one concept differently.

Before adding a dependency, an API client wrapper, an error handler or pagination:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/check_mechanisms.py --paths <manifest-or-directory> --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

Reuse the house choice or the existing wrapper it reports. Keep the spelling exactly as shown: the
`allowed-tools` rule above matches it, so it runs without a prompt (a plugin path with a space prompts).

## 4. Reading a finding

A finding states facts: detector ID and slug, the subject and its existing counterpart as
`path:line`, the measured signal (match kind, Jaccard value and shared columns, cycle members,
owning context and where it was declared), the owner skill, and the suppression route.

- **Severity.** `warn` shows at edit time and in scans; `info` only in scans; `note` is operational
  (a cold index, an invalid config). Hooks show `warn` at high or medium confidence only.
- **Frozen legacy.** Findings present at the first index build are frozen: hooks stay quiet, scans list them.
- **Then decide:** fix it through the owner skill, or declare it when the duplicate is deliberate (§5).

| IDs | Family | Detail | Fix owner |
|---|---|---|---|
| DK1–DK5, MF3–MF5 | a duplicate concept or copied fact in the schema, EAV, STI bloat, a JSONB key used as a column | `references/database-duplication.md` | `std-database` |
| DK6 | copy-paste blocks across files (scans and CI only) | `references/detectors.md` | `std-code-standards` |
| CM1–CM5, MF2 | a second library, client wrapper, error envelope, pagination style, auth mechanism or first-of-kind pattern | `references/competing-mechanisms.md` | the owner named in the finding |
| BC1–BC4, MF1 | a cross-context dependency, new cycle, cross-context write, multi-context transaction, wrong-context file | `references/context-maps.md` | this skill (the context map) |
| TF1–TF3 | Terraform duplication (scans only) | `references/detectors.md` | `std-terraform-conventions`, `monorepo-architect` |
| CFG-ADR, CFG-READMODEL, CFG-MARKER | a declaration or marker below the bar | `references/declaring-intent.md` | this skill |

## 5. When the second representation is intentional

A read model, a denormalized column, a client-mandated library, a migration between libraries, a
sanctioned cross-context write: keep it, and make it visible.

1. Write an ADR in `docs/adr/` with the `architecture-advisor` skill: the source of truth, how the
   copy stays in sync, who may write it, the staleness tolerated.
2. Declare it in `.claude/orthogonality.json` (committed), naming that ADR. A library migration
   carries an `until` date; once it passes, the finding returns.
3. For one obvious local case, a comment on the declaring line or the line above:
   `sdh:orthogonal-ok <ID> <reason>`. A marker without a reason is itself a finding.

A second model in another **declared** context needs no ADR: the context map is the record. Keys,
validation, markers and the ADR checklist → `references/declaring-intent.md`.

## 6. Scans and CI

`arch_scan.py` refreshes the index, runs every detector (scan-only ones included), and prints inline:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_scan.py --changed-since origin/main --new-only --format markdown --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

- `--changed-since REF` or `--paths P …` scopes it; `--new-only` hides frozen legacy;
  `--fail-on warn` exits 1 on a warning; `--format brief` prints at most 15 lines.
- `--write-report` also writes `.claude/orthogonality/last-scan.json` in a self-gitignoring
  directory — nothing else lands in the project. Pass it when an agent without Bash reviews the result.
- Exit codes: `0` clean, `1` a finding at or above `--fail-on`, `2` usage or configuration error,
  `3` internal error (with `--strict`, also an incomplete scan).

The authoritative gate is the project's CI, since anyone can switch hooks off for a run. Scripts,
flags, the JSON schema and a GitHub Actions job → `references/scans-and-tools.md`.

## 7. Community tools — run when installed, never installed

packwerk or pks, import-linter, tach, dependency-cruiser, jscpd and squawk run only when the project
already has them; `run_community_tools.py --list` shows what was found, and the install command it
will **not** run. Nothing is fetched through `npx`, `dlx`, `uvx`, `uv run` or `pipx run`. Tools that
boot the app and connect to a database (`database_consistency`, Django checks, `alembic check`) need
`--with-db`, and run only when the user asks. The house Rails schema-consistency tool is
`database_consistency`; it never runs beside `active_record_doctor`.

## 8. Adopting on an eroded codebase

The first complete index build stamps a **baseline**. Baselines lock erosion in when nobody burns
them down, so `arch_scan.py --baseline-report` prints frozen counts per detector and their trend;
re-stamp only with `--update-baseline --reason`. First baseline, burn-down, expiring declarations,
and when CI moves from reporting to failing → `references/adoption.md`.

## Deep guides (read on demand, do not preload)

- Finding contract, edit-time vs scan-only detectors, fire and quiet cases per stack, thresholds,
  blind spots, checks owned elsewhere → `references/detectors.md`
- Schema duplication: normalization, synonyms, overlap, exclusions, read models vs copies,
  snapshot columns, the composite-FK tenant key → `references/database-duplication.md`
- The mechanism registry per deployable, companions, overrides and migrations, ESLint and Ruff
  bans, one tool per meta-concern → `references/competing-mechanisms.md`
- Bounded contexts in packwerk, import-linter, tach, Nx tags or the config file; precedence,
  vocabulary, inferred defaults, cycles and writes → `references/context-maps.md`
- `.claude/orthogonality.json` keys and validation, inline markers, the ADR checklist → `references/declaring-intent.md`
- Scripts, flags, `sdh.orthogonality/v1` JSON, exit codes, tool matrix, CI job, performance → `references/scans-and-tools.md`
- Baselines, `--baseline-report`, burn-down, `until`, report-only to failing CI → `references/adoption.md`
