# Scans and tools

The hooks are an early-warning layer; any developer can switch hooks off for a run. The scans are
the complete picture, and the same commands are the CI gate: an architectural fitness function run
on every pull request.

## Running a script from Claude

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/<script>.py <flags> --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

- **Keep this spelling.** In a plugin skill, `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` are
  substituted both in the skill body and in its `allowed-tools` Bash rule. Using the same text in
  both places lets the script run without a permission prompt. The grant clears at the next user
  message.
- **The launcher picks the interpreter.** It tries `python`, `py -3`, then `python3`, so `python3`
  is never assumed.
- **`--cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality`** points the script at the same per-project
  index the hooks keep. Without it, a shell with no `CLAUDE_PLUGIN_DATA` falls back to the temp directory.
- **A plugin path containing a space** does not match the unquoted rule, so the command asks for
  permission instead. It still runs.

## Common flags (every script unless noted)

| Flag | Default | Meaning |
|---|---|---|
| `--project PATH` | cwd, then `git rev-parse --show-toplevel` | project or worktree root |
| `--cache-dir DIR` | the cache resolution below | where the index lives |
| `--config FILE` | `<project>/.claude/orthogonality.json` when it exists | declarations |
| `--format json\|markdown\|brief\|sarif-lite` | `markdown` on a TTY, else `json` | `brief` prints at most 15 lines, for `!` injection; `sarif-lite` is a minimal SARIF 2.1.0 run for CI annotations |
| `--output FILE` | stdout | — |
| `--paths P [P …]` / `--changed-since REF` | whole index | scope; `--changed-since` uses `git diff --name-only REF...HEAD` plus untracked files |
| `--new-only` | off | hide baseline findings |
| `--fail-on warn\|info\|never` | `never` | exit-1 threshold; CI passes `warn` |
| `--budget SECONDS` | `120` | stop and mark the result `complete: false`; it bounds the detectors inside their loops and the `--changed-since` base pass, and a detector it stops is listed in `stats.not_run` and never stamped into a baseline |
| `--no-refresh` | off | do not refresh the index first |
| `--strict` | off | an incomplete scan or a tool error becomes exit `3` |
| `--write-report` | off | also write `<project>/.claude/orthogonality/last-scan.json`, creating that directory's `.gitignore` containing `*` |

## Scripts

- **`arch_index.py`** — the index.
  - `--refresh` (default), `--rebuild`, `--status [--require-complete]`
  - `--show models|tables|contexts|mechanisms|graph|coverage`
  - `--name NAME` — concept lookup: exact, near-name and synonym matches with context, table,
    columns and `path:line`. Run it **before** creating a model or table.
- **`find_duplicates.py`** — duplicated knowledge.
  - `--detectors DK1,DK2,DK3,DK4,DK5,DK6,MF3,MF4,MF5` (default all)
  - `--min-jaccard 0.6 --min-shared 4 --min-tokens 70 --include-tests`
- **`check_boundaries.py`** — contexts and cycles.
  - `--detectors BC1,BC2,BC3,BC4,MF1,FC1` (FC1: files importing each other in a cycle inside one context, `info`)
  - `--contexts-source auto|packwerk|importlinter|tach|config|nx|inferred`
  - `--cycles context|file`
  - `--graph dot|json` — writes the context graph
- **`check_mechanisms.py`** — competing mechanisms.
  - `--detectors CM1,CM2,CM3,CM4,CM5,MF2`
  - `--emit-lint-config eslint|ruff` — **prints**, never writes, an example `no-restricted-imports`
    block or a `[tool.ruff.lint.flake8-tidy-imports.banned-api]` table built from the registry
- **`run_community_tools.py`** — installed tools only.
  - `--list` — the detection matrix: found, absent and why, and the install command it will **not** run
  - `--tools auto|<comma list>`, `--base REF`, `--with-db`, `--update-seen`
- **`arch_scan.py`** — the orchestrator. It refreshes, runs the four detector scripts' logic
  in-process, then runs tools when `--tools` is given.
  - `--update-baseline --reason TEXT` — re-stamps the baseline and appends to its history; the
    reason goes into the report
  - `--baseline-report` — frozen counts per detector and their trend

## Exit codes (all scripts)

| Code | Meaning |
|---|---|
| `0` | success, and no finding at or above `--fail-on` |
| `1` | at least one finding at or above `--fail-on`, or `--status --require-complete` on an incomplete index |
| `2` | usage or configuration error: an unknown detector, an invalid `.claude/orthogonality.json` (the message names the JSON path and key), a database-connected tool requested without `--with-db` |
| `3` | internal error; with `--strict`, also an incomplete scan (budget exceeded, a tool error or timeout). Without `--strict`, an incomplete scan exits `0` or `1` and reports `index.complete: false` and `tools[].status` |

## Output

`markdown` groups findings by class and severity, and ends with the frozen-baseline table. `brief`
prints one line per finding, at most 15, plus a count. `json` follows `sdh.orthogonality/v1`:

```json
{
  "schema": "sdh.orthogonality/v1",
  "script": "arch_scan",
  "plugin_version": "4.x.y",
  "project_root": "C:/src/acme",
  "generated_at": "2026-09-11T10:12:00Z",
  "index": {"fingerprint": "sha1…", "complete": true, "files": 8412, "truncated": false,
            "clones_truncated": false, "age_seconds": 14, "coverage": {"config_unparsed": [], "unsupported": []}},
  "contexts": {"source": "packwerk", "items": [{"name": "billing", "paths": ["packs/billing/**"], "may_depend_on": ["accounts"]}]},
  "findings": [
    {"id": "DK1", "slug": "duplicate-concept", "class": "duplicated-knowledge",
     "severity": "warn", "confidence": "high", "new": true, "fingerprint": "3f9c…",
     "subject": {"path": "packs/accounts/db/migrate/20260911_create_clients.rb", "line": 3, "symbol": "clients", "context": "accounts"},
     "related": [{"path": "db/schema.rb", "line": 88, "symbol": "customers", "context": "accounts"}],
     "evidence": {"name_match": "synonym", "jaccard": 0.71, "shared": ["email:text", "phone:text", "first_name:text", "last_name:text"]},
     "owner_skill": "std-database", "policy_skill": "orthogonality",
     "message": "ORTHOGONALITY [DK1 duplicate-concept] packs/accounts/db/migrate/20260911_create_clients.rb:3 declares clients; …",
     "remedy": "Extend customers, or declare clients in intentional_duplicates with an ADR.",
     "suppress": {"config": "intentional_duplicates", "inline": "sdh:orthogonal-ok DK1 <reason>"},
     "source": "sdh"}
  ],
  "tools": [{"name": "packwerk", "status": "ran", "exit_code": 1, "seconds": 7.4,
             "violations": [{"rule": "dependency", "path": "packs/billing/app/services/charge.rb", "line": 12,
                             "symbol": "Accounts::Customer", "message": "Dependency violation: ::Accounts::Customer belongs to 'packs/accounts', but 'packs/billing' does not specify a dependency on 'packs/accounts'."}],
             "new_violations": 1}],
  "baseline": {"taken_at": "2026-09-01T08:00:00Z", "frozen": {"BC2": 3, "DK6": 41}},
  "stats": {"seconds": 3.1, "by_severity": {"warn": 2, "info": 9}}
}
```

- `severity` is one of `warn`, `info`, `note`; `confidence` one of `high`, `medium`, `low`.
- `tools[].status` is one of `ran`, `absent`, `skipped`, `timeout`, `error`, `needs-db`.
- A finding from a community tool carries `"source": "<tool>"`.
- Every `related[]` entry carries the subject's four keys; `context` is `null` when the detector has no
  context for the counterpart.
- Every `tools[]` entry carries every key shown. A tool that did not run has `exit_code: null`,
  `seconds: 0`, an empty `violations` list and `new_violations: 0`. `run_community_tools.py --list`
  prints detection rows instead: `name`, `found`, `status`, `why` and `not_run_install_hint`.

### Handing results to agents

Scans always print inline. `--write-report` also leaves `.claude/orthogonality/last-scan.json`,
which agents without Bash (`clean-architecture`, `architecture-advisor`, `monorepo-architect`) read
when it exists. Agent-routed skills can also inject a scan into the prompt with a `!` line:

```markdown
!`bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_scan.py --changed-since origin/main --new-only --format brief --no-refresh 2>/dev/null || echo "orthogonality scan unavailable"`
```

`!` lines do not run for skills synced from claude.ai, and their output is not re-scanned; that is
why the report file exists as well.

## The index

- **Location.** `${CLAUDE_PLUGIN_DATA}/orthogonality/<key>/index.sqlite`. The key is derived from the
  project root's real path, its folder name and the parser generation, so client codebases on one
  machine never mix, and two installed plugin versions whose parsers differ never share or wipe one
  index. A linked worktree gets its own key, seeded from the main checkout's index.
- **Fallbacks.** With `CLAUDE_PLUGIN_DATA` unset, the temp directory (`sdh-orthogonality/<key>/`).
  `SDH_ORTHOGONALITY_DIR` overrides both.
- **Lifetime.** It survives plugin updates and is deleted when the plugin is uninstalled. It is a
  rebuildable cache, never a record: declarations live in the committed config file, and the CI
  baseline comes from the base commit (below).
- **Scope.** `git ls-files --cached --others --exclude-standard`, so `.gitignore` is honoured and
  untracked files count. Build output, `node_modules`, `.venv`, `__pycache__` and config `ignore` are
  skipped. Caps: 50,000 in-scope files, 1 MB per file. The hooks build no index for a session started
  outside a project: the home directory, a filesystem root, or a folder with no `.git`, package
  manifest or `.claude/orthogonality.json` at its top level.
- **Freshness.** Changed files are re-parsed by size and modification time, with a content hash when
  timestamps are unreliable. A branch switch triggers a full stat pass; a config change recomputes
  contexts without re-parsing; a plugin upgrade that changes the parsers starts a new index under a
  new key.
- **One writer at a time.** Refreshes take `refresh.lock`. A lock whose holder process on this machine
  has exited (a closed session, a killed hook) is broken at once, and any lock older than 10 minutes
  is. A pass that was killed resumes from the files it had committed. While another refresh holds the
  lock, `arch_index.py` says so and exits `0` (`1` with `--require-complete`).
- `arch_index.py --status` shows age, completeness and coverage; `--rebuild` starts over.

## Environment switches

| Variable | Effect |
|---|---|
| `SDH_ORTHOGONALITY=off` | disables the edit-time checker, the session-start refresh and the watcher |
| `SDH_ORTHOGONALITY_DIR=<dir>` | sets the cache directory |
| `SDH_ORTHOGONALITY_CLONES=0` | skips DK6 clone detection |
| `SDH_ORTHOGONALITY_TOOLS` | whether the background watcher may run installed community tools; off by default in this release |
| `SDH_HOOK_MAX_WARNINGS=0` | removes the hook output cap for a standalone run |

## Community tools — detected, never installed

A tool runs only when it is already in the project (`node_modules/.bin`, `.venv/bin` or
`.venv/Scripts`, `bin/`), or on PATH for standalone binaries (`squawk`, `jscpd`, `pks`). Nothing is
launched through `npx`, `pnpm dlx`, `yarn dlx`, `bunx`, `uvx`, `uv run` or `pipx run`, any of which
can fetch a package that is not installed. No script opens a network connection.

| Tool | Detected when (all hold) | Invocation | Baseline respected | Notes |
|---|---|---|---|---|
| packwerk | `packwerk.yml`; `Gemfile.lock` lists `packwerk`; `bin/packwerk` is executable | `bin/packwerk check [dirs]` | `package_todo.yml` | MIT. Constant-based: method calls and runtime dependencies are not seen. Accepts folders for a shorter run |
| pks | `packwerk.yml`; `pks` on PATH | `pks check` | `package_todo.yml` | MIT. Reads the same config with documented differences, so it never runs together with packwerk |
| import-linter | a contract in `.importlinter`, `setup.cfg` or `pyproject.toml`; `lint-imports` in the project `.venv` | `lint-imports` | the seen-set | BSD-2-Clause. No changed-file mode; its cache is not concurrency-safe, so runs are serialized |
| tach | `tach.toml`; `tach` in the project `.venv` | `tach check` | the seen-set | MIT. Maintenance lapsed in 2025, then resumed under tach-org |
| dependency-cruiser | `.dependency-cruiser.{js,cjs,mjs,json,ts}`; `node_modules/.bin/depcruise` | `depcruise --config <cfg> --cache --affected <base> --output-type json <src>` | `--ignore-known` + `.dependency-cruiser-known-violations.json` | MIT. Full runs can take over a minute, hence `--cache` and `--affected`. Its `--baseline` flag is not used until the release that ships it (18.3.0); the latest release is v18.2.0 |
| jscpd | `.jscpd.json`, `.config/jscpd.json` or `package.json#jscpd`; `node_modules/.bin/jscpd` or `jscpd` on PATH | `jscpd --reporters json --baseline-from-ref <base> <paths>` | its own baseline | MIT. v5 is a fast-moving rewrite: pin its version in CI |
| squawk | changed `.sql` migrations; `squawk` on PATH or in `node_modules/.bin` | `squawk <files>` | `squawk-ignore` comments | Apache-2.0/MIT. Migration safety, not orthogonality; run because it is static and fast. Pin its version in CI |
| database_consistency (`--with-db`) | `Gemfile.lock` lists it; `bundle` on PATH | `bundle exec database_consistency` | its TODO file | MIT. The house schema-consistency tool. Needs a booted app and a database. Its exit-code behaviour is not documented, so output is parsed, not the exit code. Pin its version in CI |
| active_record_doctor (`--with-db`) | `Gemfile.lock` lists it | `bundle exec rake active_record_doctor` | its ignore lists | MIT. Never beside `database_consistency`; CM1 reports the pair |
| Django checks (`--with-db`) | `manage.py`; the project `.venv` Python | `python manage.py check --fail-level WARNING [--database default]`; `python manage.py makemigrations --check` | — | needs importable settings |
| Alembic drift (`--with-db`) | `alembic.ini`; `alembic` in `.venv` | `alembic check` | — | compares models with a configured, migrated database |
| flay (optional) | `Gemfile.lock` lists `flay` | `bundle exec flay --mass <n> <changed .rb>` | — | MIT. AST clones for Ruby; no baseline mode |
| pylint R0801 (optional) | `pylint` in `.venv`, enabled in project config | `pylint --disable=all --enable=duplicate-code <pkg>` | — | GPL-2.0: run, never vendored |

**`--with-db` runs only when the user asks.** Those tools boot the application and connect to a
database, a side effect a background job or a routine scan must never trigger.

**The background watcher** does not run community tools in this release unless
`SDH_ORTHOGONALITY_TOOLS` enables it. When enabled, tools run serialized: packwerk, import-linter
and dependency-cruiser within 60 s each, tach and jscpd within 30 s, squawk within 10 s, and a
120 s cap per pass. It reports only violations absent from both the tool's own baseline and the
seen-set.

**Deliberately not integrated:**

- **Atlas** — `migrate lint` needs Atlas Pro, a proprietary dependency.
- **Nx Conformance** — needs an Nx Enterprise licence.
- **schemalint** — needs a live database; CI exit behaviour unstated.
- **SchemaSpy** — a documentation generator with no pass/fail result.
- **PgHero** — advice depends on production workload statistics.
- **SQLFluff** — a style linter with no orthogonality rules.
- **madge** — no rule language.
- **ArchUnit** — JVM only.
- **PMD CPD** — needs a JVM and has no baseline mode.
- **`import/no-cycle`** — stays in the project's own ESLint when a team wants it; it is expensive.

## CI: the fitness function

Hard enforcement belongs to the project's CI, running the same scripts. In CI the index is a fresh
cache, so the baseline must come from the **base commit**: scan the base first with
`--update-baseline`, then scan the pull request against it with `--new-only`. The cache sits in the
runner's temp directory, and the plugin checkout is excluded from the scanned tree.

```yaml
# .github/workflows/orthogonality.yml
name: orthogonality
on: pull_request
permissions:
  contents: read
jobs:
  orthogonality:
    runs-on: ubuntu-latest
    env:
      BASE_REF: ${{ github.base_ref }}
      ORTH_CACHE: ${{ runner.temp }}/orthogonality
    steps:
      - uses: actions/checkout@<full-length-sha>  # v4
        with:
          fetch-depth: 0                          # --changed-since needs the base history
      - uses: actions/checkout@<full-length-sha>  # v4
        with:
          repository: Kaakati/sdh-claude-skills
          ref: <plugin-commit-sha>                # the plugin release the team runs locally
          path: .sdh-plugin
      - uses: actions/setup-python@<full-length-sha>  # v5
        with:
          python-version: "3.12"
      - name: Keep the plugin out of the scanned tree
        run: echo ".sdh-plugin/" >> .git/info/exclude
      - name: Stamp the baseline on the base commit
        run: |
          HEAD_SHA="$(git rev-parse HEAD)"
          git checkout --quiet --detach "origin/$BASE_REF"
          python .sdh-plugin/skills/orthogonality/scripts/arch_scan.py --cache-dir "$ORTH_CACHE" \
            --update-baseline --reason "base origin/$BASE_REF" --format brief
          git checkout --quiet --detach "$HEAD_SHA"
      - name: Fail on new warnings in the changed files
        run: |
          python .sdh-plugin/skills/orthogonality/scripts/arch_scan.py --cache-dir "$ORTH_CACHE" \
            --changed-since "origin/$BASE_REF" --new-only --fail-on warn --format markdown
```

- **Pin every action by commit SHA**, per `@skills/std-infrastructure/references/github-actions.md`,
  and pin the plugin to a commit.
- **Pin tool versions** for any community tool the job runs (`squawk`, `jscpd`,
  `database_consistency`): each ships rule and parser changes every few weeks.
- **Add `--strict`** once the scan fits its budget, so an incomplete scan fails instead of passing.
- **Add `--tools auto`** to the second step to include installed boundary tools. Add `--with-db` only
  in a job that already provisions a migrated database.
- **Start report-only** (`--fail-on never`) on an eroded codebase; the move to failing is covered in
  `@skills/orthogonality/references/adoption.md`. Where the job belongs among the project's other
  pull-request checks → `@skills/std-infrastructure/references/ci-pipeline.md`.

## Performance targets

Design targets, measured on the plugin's synthetic trees:

| Operation | Target |
|---|---|
| `arch_index.py --refresh`, no changes, 10k in-scope files | ≤ 1.5 s |
| full build, 10k files | ≤ 20 s |
| full build, 50k files | ≤ 90 s |
| `find_duplicates.py`, whole index, 10k files | ≤ 10 s |
| `check_boundaries.py`, cycle search on 100k edges | ≤ 3 s |
| `arch_scan.py --changed-since origin/main --new-only`, tools excluded | ≤ 5 s |
| peak memory, any script | ≤ 300 MB |
| edit-time checker, warm index | 150 ms on 10k files; self-limited at 1.5 s |

## Sources

- Thoughtworks — Architectural fitness function | Technology Radar — https://www.thoughtworks.com/radar/techniques/architectural-fitness-function
- Thoughtworks (Paula Paul, Rosemary Wang) — Fitness function-driven development — https://www.thoughtworks.com/en-us/insights/articles/fitness-function-driven-development
- Anthropic — Claude Code docs, Skills: string substitutions, supporting files, allowed-tools, dynamic context — https://code.claude.com/docs/en/skills#available-string-substitutions
- Anthropic — Claude Code docs, Plugins reference: persistent data directory — https://code.claude.com/docs/en/plugins-reference#persistent-data-directory
- Anthropic — Claude Code docs, Hooks reference: run hooks in the background — https://code.claude.com/docs/en/hooks#run-hooks-in-the-background
- Anthropic — Claude Code docs, Hooks reference: hook locations, allowManagedHooksOnly, disableAllHooks — https://code.claude.com/docs/en/hooks#hook-locations
- Shopify — Shopify/packwerk — https://github.com/Shopify/packwerk
- David Seddon — Import Linter documentation — https://import-linter.readthedocs.io/en/stable/
- tach-org — tach-org/tach — https://github.com/tach-org/tach
- Sander Verweij — dependency-cruiser command line interface — https://github.com/sverweij/dependency-cruiser/blob/main/doc/cli.md
- Andrey Kucherenko — kucherenko/jscpd — https://github.com/kucherenko/jscpd
- GitHub sbdchd/squawk — https://github.com/sbdchd/squawk
- GitHub sbdchd/squawk — Releases — https://github.com/sbdchd/squawk/releases
- GitHub djezzzl/database_consistency — README — https://raw.githubusercontent.com/djezzzl/database_consistency/master/README.md
- GitHub gregnavis/active_record_doctor — README — https://raw.githubusercontent.com/gregnavis/active_record_doctor/master/README.md
- Django Software Foundation — django-admin and manage.py — https://docs.djangoproject.com/en/stable/ref/django-admin/
- SQLAlchemy / Alembic — Auto Generating Migrations — https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- seattlerb — seattlerb/flay — https://github.com/seattlerb/flay
- pylint-dev — pylint/checkers/symilar.py — https://raw.githubusercontent.com/pylint-dev/pylint/main/pylint/checkers/symilar.py
- Ariga — Migration Analyzers | Atlas — https://atlasgo.io/lint/analyzers
- Ariga — Atlas Community Edition — https://atlasgo.io/community-edition
- Nx — Enforce Module Boundaries — https://nx.dev/docs/features/enforce-module-boundaries
- Kristian Dupont — kristiandupont/schemalint — https://github.com/kristiandupont/schemalint
- SchemaSpy — schemaspy/schemaspy — https://github.com/schemaspy/schemaspy
- Andrew Kane — ankane/pghero — https://github.com/ankane/pghero
- SQLFluff — Rules Reference — https://docs.sqlfluff.com/en/stable/reference/rules.html
- pahen — pahen/madge — https://github.com/pahen/madge
- TNG Technology Consulting — ArchUnit User Guide — https://www.archunit.org/userguide/html/000_Index.html
- PMD — Copy/Paste Detector (CPD) — https://docs.pmd-code.org/latest/pmd_userdocs_cpd.html
- import-js — import/no-cycle — https://github.com/import-js/eslint-plugin-import/blob/main/docs/rules/no-cycle.md
