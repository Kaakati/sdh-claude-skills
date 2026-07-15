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

### Fixed
- **The release-hygiene gate cried wolf on test-only changes**, turning `main` red the day after
  v2.0.0. It treated everything under `hooks/` as shipped behaviour, but `hooks.json` never
  references `hooks/tests/` — a consumer's session cannot execute it, so a test change delivers
  nothing a version bump would carry. The gate now excludes the plugin's own CI and names the
  offending files instead of their top-level directory. A real hook change still requires a bump.
  *(Repo-internal: no effect on consumers.)*


## [2.0.0] — 2026-07-15

**MAJOR — this release denies work that previously succeeded.** The version is what you pin, and
`1.0.0` had gone stale: it was declared once at the plugin conversion and never moved while the
deny floor, the gates, and the skills all changed underneath it. Per the plugin's resolution
rules, that meant installed users received **none** of it. This release is the first that can
actually be delivered.

**Two things to do when you take it:**

1. **Copy the 6 new Terraform denies** into your project's `.claude/settings.json` (see
   *Permission floor* below). A plugin cannot ship `permissions`. The SessionStart sentinel will
   name the missing rules on every session until you do.
2. **Expect `terraform apply` to ask, and `terraform destroy` / `state rm|mv|push` /
   `force-unlock` / `apply -auto-approve` to be **denied**. If that breaks a workflow, that is
   the intended change, not a bug — read the reason, which names the remedy.

**Pin it** (the `/plugin marketplace add` form floats on `main`):

```json
{ "name": "sdh",
  "source": { "source": "github", "repo": "Kaakati/sdh-claude-skills", "ref": "v2.0.0" } }
```

### Fixed
- **The commit gate blocked on a list you couldn't read in full.** `pre-commit-check.py` accepts
  **11** conventional-commit types and denies everything else, pointing you at
  `std-git-workflow` — which documented **10** (and CLAUDE.md, 9). `revert:` worked but was named
  nowhere, so the only way to discover it was to be denied first. Both are now complete, the
  skill states that its table **is** the accepted set, and a test parses the hook's regex against
  that table and fails on drift **in either direction** — including the worse one, a documented
  type the hook would reject. (Verified: nothing documented was ever blocked.)
- **The auto-format hook silently applied *unsafe* RuboCop corrections (BEHAVIOURAL).** It ran
  `rubocop --autocorrect-all`, which RuboCop's own CLI documents as *"Autocorrect offenses (safe
  and unsafe)"* — against a default config marking **53 cops `SafeAutoCorrect: false`**, i.e.
  corrections its maintainers flag as able to change behaviour. The hook runs unattended on every
  `.rb` write with its output discarded, so those rewrites landed on code nobody re-read. It now
  runs `--autocorrect` (**safe only**); `-A` stays a deliberate human action where you read the
  diff. **If you relied on unsafe autocorrections happening automatically, they no longer do** —
  run `bundle exec rubocop -A` yourself. A new test fails the build if any unattended formatter
  regains an unsafe flag.
- **7 hooks warned you without saying where the rule lives.** `security-scan`, `pre-commit-check`,
  `terraform-checker`, `terraform-command-gate`, `atomic-design-checker`, `design-token-checker`
  and `dangerous-command-blocker` all named a remedy but no skill — so a developer hit by the
  design-token checker had nowhere to learn *why*. Eleven other hooks pointed at a skill; these
  seven pointed at nothing, which reads as arbitrariness. All 7 now name the skill that carries
  the rule, and the test that guaranteed *"a named skill must exist"* now also guarantees *"a skill
  must be named"* (with `auto-format` exempt — it names an install command, which is the real
  remedy).
- **The code-quality hook warned at a number its own skill never stated.** It warns at **200
  lines** for Rails models and UI components (300 elsewhere) and points you at
  `std-code-standards` — which said only *"Target maximum 300 lines"*. Write a 250-line model,
  read the skill you were sent to, get warned anyway, conclude the hook is noise. The number was
  documented in `CLAUDE.md` and the always-on skill, but **a plugin's `CLAUDE.md` is not shipped
  to consumers**, and the skill the hook *names* is the one that must carry it. `std-code-standards`
  now states both limits, the wrapper-agnostic paths they apply to, why models/components get the
  tighter one, and that all four limits are **advisory, never blocking**. A new test imports the
  hook's constants and fails CI if any of them stops appearing in the skills that document them.
- **`code-reviewer` could not catch a single bug this release fixed.** Its stack checks were one
  line each and predated every verified defect. It now greps for the five that fail *silently* —
  a policy that exists but is never called (`policy_scope` filters, `authorize` does not), a
  migration with no `lock_timeout`, a `remove_column` with no prior `ignored_columns` deploy, a
  non-bang `create` inside a transaction (commits half), and a money job with no explicit
  `sidekiq_options retry:`. Also fixed a contradiction in its own guide: the model *"idempotent
  job"* taught `return if order.charged?` as the answer (a race-prone guard, not the correctness)
  and carried no retry policy — so the repo's exemplar job silently inherited 25 retries over ~20
  days on a payment.
- **14 reference files (2,298 lines) that nothing could ever load.** `api-designer`,
  `code-reviewer`, `incident-response`, `nextjs-dev`, `onboarding`, `performance-profiler`,
  `reactjs-dev`, `security-auditor` and `test-generator` all shipped `references/*.md` that their
  SKILL.md never named — and no agent named them either. Tier 1 is the catalog: if the body does
  not name the file, the model never learns it exists, so it is never loaded however good it is.
  `code-reviewer`'s `pr-review-guide.md` held exactly the N+1, migration-safety and Sidekiq checks
  the reviewer needed, unreachable the whole time. All 14 are now indexed with descriptions drawn
  from their real contents, and **`skills-lint` now fails when a reference is not named by its
  body** — the mirror of the existing check that a named reference must exist. Both directions
  now hold: 0 pointers without a file, 0 files without a pointer.
- **An AAA accessibility criterion was sold as AA.** `std-accessibility` said *"WCAG 2.2 adds 7
  success criteria … All are required for AA compliance"* and listed **2.4.13 Focus Appearance**
  as AA. WCAG 2.2 adds **nine** (and removes 4.1.1 Parsing), and W3C states 2.4.13 is
  **Level AAA**. Holding a team to a stricter bar than the standard, while telling them it *is*
  the standard, is how governance gets disabled. The requirement stays — the design system already
  ships the focus ring — relabelled honestly as a **house rule** above AA, in all 4 places across
  `std-accessibility` and `accessibility-auditor`.
- **A payment job that retried for ~20 days.** The repo advised *"configure `retry_on` for
  transient errors"* — an ActiveJob API — and its canonical Rails pattern used
  `retry_on ..., attempts: 5` on a **payment** job. Per Sidekiq's own wiki, `retry_on` caps
  nothing: ActiveJob retries first, then *"kick[s] the job back to Sidekiq, where Sidekiq's
  retries with exponential backoff will take over"* — the default being *"25 retries over
  approximately 20 days."* That job charged 30 times across three weeks. Both are fixed to a
  single `sidekiq_options retry: 5` (which works on ActiveJob classes and does not stack), plus
  `sidekiq_retries_exhausted` so a dead job is not silent.
- **`db-migration` taught a table rewrite that does not happen — and the migration hook flagged
  correct code.** The guide was raw SQL with MySQL branches (`pt-online-schema-change`, `gh-ost`)
  in a Rails/PostgreSQL-only stack, and it labelled `ADD COLUMN ... NOT NULL DEFAULT 'x'` as
  *"rewrites entire table"*, prescribing a batched-backfill dance for it. Postgres is explicit
  that a **non-volatile default requires no rewrite** and is *"very fast even on large tables"* —
  so the guidance cost teams a multi-step migration for free work, while never mentioning what
  does rewrite (**volatile** defaults, stored generated columns, identity columns) or that
  `SET NOT NULL` *"requires scanning the table"* under an exclusive lock. Both files are now
  ActiveRecord against PostgreSQL, led by a what-actually-locks table sourced from the docs, and
  carry the Rails traps the SQL version could not (`ignored_columns` before a drop,
  `add_foreign_key validate: false` → `validate_foreign_key`, `unscoped` backfills).
  **`migration-validator.py` is corrected too:** it called `remove_column` in `change`
  irreversible — but `remove_column :orders, :status, :string` **is** reversible and is the
  recommended form, and `rename_column` is reversible as well. It now flags only the genuinely
  irreversible forms, warns about `rename_column` for the real reason (it breaks running
  instances mid-deploy), and drops a hard-coded `backend/` path that contradicted
  wrapper-agnostic detection.
- **37 hook messages sent you to files that do not exist.** Converting `.claude/rules/*.md` into
  `std-*` skills left every hook still saying *"per `accessibility.md`"*, *"per `security.md`"*,
  *"per `database.md`"* — 37 pointers across 10 hooks, none of which resolved. The hooks fired
  correctly and then sent the reader nowhere, which is the one thing a deny reason must never do:
  it is *"your plugin's user interface, and the only part most users will ever read."* Every
  message now names the skill that actually carries the rule (e.g. *"per the `std-accessibility`
  skill"*), and a new test fails the build if any hook names a `.md` file or a `std-*` skill that
  does not exist.
- **`std-database` was written for a stack this repo does not use.** Every example was `knex` /
  TypeScript — a Node query builder absent from the stack — in a Rails + PostgreSQL repo, with
  **zero** ActiveRecord content. Restacked to ActiveRecord, and the rewrite adds what the Rails
  idiom actually gets wrong: `create!` vs `create` inside a transaction (the non-bang form returns
  `false`, so the block completes and commits half the operation), `after_commit` vs `after_save`
  for Sidekiq/Centrifugo, `includes`/`preload`/`eager_load` + `references`, and Panko serializers
  as where N+1 hides. *(`db-migration` has the same defect — raw SQL with MySQL branches — and is
  recorded as a P2 backlog item rather than rushed into the same pass.)*
- **The README's agent table advertised a "Plan" mode that does not exist.** `permissionMode` is
  silently ignored for plugin-shipped agents and was removed from the agents themselves, but the
  table still listed 4 agents as "Plan". The column is now **Capability**, generated from each
  agent's actual `tools` list — and it counts `Bash` as write access (Ch. 8, the Bash hole), so
  `security-auditor` and `incident-responder` read **Read-write**, not the reassuring label their
  "audit" framing invites. `plugin.json` also under-counted the plugin's own contents.
- **A missing formatter is no longer silent.** `auto-format.py` already exited 0 when `rubocop` /
  `prettier` / `black` / `terraform` was absent — correct, but silent, so you watched formatting
  never happen with no way to learn why. It now prints one line naming the binary and its install
  command, **once per session**, then stays quiet. A formatter that fails to *run* is reported the
  same way instead of being swallowed. Nothing is blocked either way.
- **`react-native-best-practices` was advertising the wrong priorities.** Its body had collapsed
  the skill's 14 canonical sections (`rules/_sections.md`) into 8 invented ones: **Core Rendering
  — CRITICAL, "violations cause runtime crashes or broken UI" — was missing entirely**, List
  Performance was promoted HIGH→CRITICAL in its place, and Monorepo was relabelled LOW→MEDIUM.
  The body is what the model reads, so guidance drawn from this skill was mis-prioritised. All 14
  sections are now restored with their canonical impacts, each carrying its rationale and rule
  prefix. `react-best-practices`, `composition-patterns`, `atomic-design` and `terraform` were
  checked and were already correct — no change.

### Added
- **`/toolchain` skill** — linters, formatters, type-checkers and compilers: the four tiers
  (format / lint / typecheck / build) and why most toolchain arguments compare tools from
  different ones; **safe vs unsafe autocorrect**; **checking a tool is installed without
  installing it** (a global install is a machine-level change that often makes CI parity *worse*
  by shadowing the pinned version); `bundle exec` / `pnpm exec` because a bare `rubocop` is a
  different program; and `tsc --noEmit` as the check most CI omits — **Vite and Next do not
  typecheck**, so a type error can pass dev, build, and a green CI. 2 references: a doctor script
  that reports rather than fixes, and per-stack lint/typecheck/build with the prettier-vs-eslint
  boundary.
- **`/mcp-advisor` skill + `mcp-install-gate.py` hook (ACTION: expect a new prompt).** Adding an
  MCP server now **asks first** — on `claude mcp add`, `add-json`, `add-from-claude-desktop`, and
  any write to `.mcp.json`. It stays silent on `list`/`get`/`remove`. The reason: an MCP server is
  not a library. A library is text you *run*; an MCP server is text the model *obeys* — its tool
  descriptions are prompts, and the docs warn that *"servers that fetch external content can
  expose you to prompt injection risk."* The skill covers discovery (start with the reviewed
  Anthropic Directory), the vetting bar (named publisher, **pinned** not `@latest`, least
  credential, scope matching blast radius), and why `--scope project` is a decision about your
  teammates — it writes a committed `.mcp.json` they see as `Pending approval`. Also flags that
  `headersHelper` executes arbitrary shell commands, so a `.mcp.json` in a PR is code, not config.
  Its honest counsel: **prefer the CLI you already have** — `gh` runs under the gates that exist.
- **`std-nextjs` now states its version target: Next.js 15+ / React 19**, with a 14-vs-15 table of
  what changed (`fetch` and `GET` Route Handlers no longer cached by default; the Client Router
  Cache no longer reuses page segments on `<Link>` navigation; `cookies`/`headers`/`params`/
  `searchParams` are now **async**). The skill's code was already 15-correct — this pins the
  contract, per the repo's own *pin every version* rule, and explains why `references/caching.md`
  always states `next: { revalidate, tags }` explicitly rather than relying on a default that
  reversed between majors.
- **`std-error-handling/references/background-jobs.md`** — Sidekiq's real semantics, previously at
  zero coverage: the **25 retries over ~20 days you never configured**, `retry: 0` (to the Dead
  set, kept and retryable) vs `retry: false` (**discarded**, no record), the Dead set as silent
  failure (10k jobs / 6 months), ActiveJob vs `include Sidekiq::Job` (*"about 30% overhead"*), why
  rescuing inside a job **disables the retry** while reporting success, and why timeouts are what
  make retries meaningful at all.
- **`std-monitoring/references/request-tracing.md`** — `request_id` was referenced by **11 files**
  (two hooks *warn* when it is missing; `log-search` builds its whole trace workflow on it) and the
  mechanism was documented in **none**. Now: Rails already generates it
  (`ActionDispatch::RequestId` adopts the load balancer's `X-Request-Id` or makes a uuid, and
  returns it to the client), `config.log_tags = [:request_id]` tags every line — and the part
  everyone misses, **the trace breaks at the async boundary**: a Sidekiq job has no request, so the
  id is `nil` exactly where you need it. Includes the client/server middleware, the `ensure` reset
  (Sidekiq reuses threads — a leaked id mislabels the *next* job), and a one-`curl` end-to-end
  proof. Note the id is **outside input** (Rails sanitizes it because clients can send it) — never
  interpolate it into SQL.
- **`std-database/references/locking-and-timeouts.md`** + `lock_timeout` in the body — the
  mechanism behind most migration outages, previously at **zero coverage**: `ALTER TABLE` needs
  `ACCESS EXCLUSIVE` (which *"conflicts with locks of all modes"*, and *"only an ACCESS EXCLUSIVE
  lock blocks a SELECT"*), a transaction *"will wait indefinitely for conflicting locks"*, and
  queries arriving after it queue behind it — so a millisecond-fast migration becomes a full table
  outage for as long as an unrelated slow query runs. **`lock_timeout` defaults to 0: wait
  forever.** Covers the retry loop, `disable_ddl_transaction!` and its invalid index,
  `pg_blocking_pids()`, and advisory locks — plus the Postgres subtlety that `lock_timeout` must
  be *smaller* than `statement_timeout` or it never fires.
- **`/log-search` skill** — reading production logs, which the repo could emit but never query:
  `Logs Insights`, `aws logs tail`, `gcloud logging read` and `Cloud Logging` were all at **zero
  coverage** while `std-monitoring` covered structured logging and alarms. Both clouds bill by
  **data scanned**, so the skill leads with narrowing (AWS's own guidance: *"Always specify the
  narrowest possible time range"*), then the four questions that answer most incidents. 2
  references: CloudWatch Insights QL (discovered `@`-fields, `bin()` histograms, `parse` as a
  workaround not a destination, the async `start-query` → `get-query-results` dance, retention as
  an explicit decision) and GCP Cloud Logging (LQL is a **boolean filter, not SQL** — there is no
  `stats`, aggregation is a log-based metric; `:` means *contains* and `=` means *equals*; and the
  sink whose writer identity was never granted permission, which looks configured and exports
  nothing).
- **`std-infrastructure/references/github-actions.md`** — workflows as supply chain. A
  third-party action is code you run with your `GITHUB_TOKEN`, and **`@v4` is a mutable tag, not
  a version** (the mechanism behind the `tj-actions/changed-files` compromise) — pin to a full
  SHA and let Dependabot bump it. Also `permissions` least privilege, `concurrency` (with
  `cancel-in-progress: false` for deploys — cancelling a half-applied migration is worse than
  queueing), reusable workflows vs composite actions, environments as the human gate, and the
  `pull_request_target` hole.
- **`std-infrastructure/references/gcp-secondary-cloud.md` rewritten** (39 → 156 lines) around
  **Workload Identity Federation**. The repo was internally inconsistent: keyless OIDC for AWS,
  but a downloaded service-account key for GCP. Google: *"Workload Identity Federation is
  recommended over Service Account Keys as it obviates the need to export a long-lived
  credential."* Includes the `attribute_condition` that scopes the provider to your repo —
  without it, **every GitHub Actions run on the internet** can assume your service account. The
  AWS-primary stance and the "unavoidable key → AWS Secrets Manager" rule remain, as the
  documented fallback rather than the default.
- **`/mobile-signing` skill** — iOS/Android signing identity management, ordered by blast radius
  rather than workflow, because one failure here is permanent: losing an Android **app signing
  key** while not enrolled in Play App Signing means *"you will not be able to release new
  versions of your app to users as updates"* and *"you cannot regenerate a previously generated
  key."* 3 references: Apple certificates/App IDs/profiles/`.p8` keys/fastlane match (including
  why **revoking a certificate to troubleshoot** invalidates every profile built on it), Android
  upload key vs app signing key + Play App Signing enrolment and upload-key reset, and holding
  these secrets in CI (base64 → `RUNNER_TEMP`, ephemeral keychains, `match(readonly: true)`, and
  the `pull_request_target` hole).
- **`/mobile-beta-release` skill** — shipping betas to testers. Leads with the asymmetry that
  breaks release plans: TestFlight **external** requires Beta App Review (*"have your first build
  already approved by App Review for TestFlight"*) while Play **internal testing** has no review
  gate, so the two platforms do not land together. Also covers the **90-day TestFlight build
  expiry**, internal (≤100 role-holders) vs external (≤10,000), Play track API names
  (`alpha` = closed, `beta` = open), promoting the *same artifact* rather than rebuilding, staged
  rollout and how to halt one — and that there is no rollback, only a higher `versionCode`.
  3 references incl. ready-to-use fastlane lanes.
- **`std-react-native` gains two references** for pillars it previously asserted without a
  mechanism. `references/offline-and-mutations.md`: queuing offline mutations is free, but
  surviving an app kill is not — only mutation *state* is persisted, so a resumed mutation dies
  with `No mutationFn found` unless `queryClient.setMutationDefaults` is registered at module
  scope before hydration; plus NetInfo → `onlineManager` and idempotency keys generated once at
  the call site. `references/realtime-centrifugo.md`: `newSubscription()` **throws** if the
  channel is already registered (what every remounting screen does — use
  `getSubscription() ?? newSubscription()`), `unsubscribe()` does not remove listeners, the
  socket does not backfill on reconnect, and `getToken` beats a static `token`.
- **`std-rails-conventions/references/authorization.md`** + access-control rules in
  `std-security` — the repo documented Pundit *policies* in 10 files but never how to guarantee
  one is **called**. A controller action that forgets `authorize` raises nothing and returns
  `200 OK` with another user's data (OWASP #1, Broken Access Control). Both skills now carry
  Pundit's own enforcement (`after_action :verify_authorized` / `verify_policy_scoped`, off by
  default), `policy_scope` vs `authorize` for collections, 404-not-403 for non-owners, and
  `devise-jwt` revocation (`JTIMatcher` + unique `jti`) — without a strategy, sign-out leaves the
  token valid until it expires.
- **`release-hygiene` CI job + [`docs/releasing.md`](docs/releasing.md)** — the plugin's `version`
  is the delivery handle, and the plugin docs are blunt about it: *"pushing new commits without
  changing that string does nothing for existing users."* CI now fails when plugin content has
  changed since the newest release tag without a version bump, and verifies on a tag push that the
  tag, `plugin.json`, and the CHANGELOG agree and `[Unreleased]` was drained. The doc covers
  pinning (`ref`/`sha`), release channels, and the required branch-protection posture.
  **How to pin:** point a marketplace entry at a tag —
  `{"source":"github","repo":"Kaakati/sdh-claude-skills","ref":"vX.Y.Z"}`. The README's
  `/plugin marketplace add` form floats on `main`.
- **`/monorepo-architect` skill + `monorepo-architect` agent** (Opus, read-only) — monorepo
  architecture and management: workspace layout by deployable unit (`apps/`/`packages/`/`tooling/`),
  dependency boundary enforcement (ESLint `no-restricted-imports`, Nx tags, packwerk), task
  orchestration and caching (Turborepo/Nx/Bazel selection, with Bazel called out as rarely worth
  its cost below ~50 engineers), affected-only CI with remote cache and merge queue, one-version
  policy (and the deliberate React Native pin exception), per-app release tagging with Changesets,
  and generating a shared `api-client`/`types` package from the Rails schema so web and mobile
  cannot drift. 6 references, loaded on demand.
  **This is distinct from [`docs/monorepo-setup.md`](docs/monorepo-setup.md)**, which covers Claude
  Code *configuration* for a large repo (CLAUDE.md layering, excludes, worktrees). The `apps/`
  layout keeps `std-*` auto-loading intact — detection is wrapper-agnostic — though shared
  `packages/` match no framework structure and need a per-package `CLAUDE.md`.
- **`SDH_PROTECTED_BRANCHES`** — the branch names the direct-push and force-push gates protect are
  now configurable (default `main,master,develop`, unchanged). Previously hard-coded, so a repo
  whose trunk is named anything else was **silently ungated**. Set it in your environment:
  `export SDH_PROTECTED_BRANCHES="trunk,staging"`. A blank value falls back to the defaults rather
  than unprotecting everything; branch names are regex-escaped, so `release/v1.0` is safe.
- **`.github/scripts/check_rule_taxonomy.py`** + a `skills-lint` CI step — fails the build when a
  skill body drifts from its `rules/_sections.md`, when a section's prefix matches no rule file,
  or when a rule file on disk is claimed by no section. Run it locally with
  `python3 .github/scripts/check_rule_taxonomy.py`. Contributor-facing: **edit `_sections.md`, not
  the body's table.** Heading numbering is not enforced — both `### 1. Atoms (HIGH)` and
  `### Atoms (HIGH)` are accepted.
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
- **The last 3 compiled `full-guide.md` monoliths (6,777 lines)** — `react-best-practices` (2934),
  `react-native-best-practices` (2897), `composition-patterns` (946). **No content lost and no
  behaviour change:** all three were already unreferenced by their bodies (nothing loaded them),
  and their section preambles were copies of `rules/_sections.md`, which remains. Every rule keeps
  its own `rules/<rule-id>.md` with its bad/good pair. This removes a drift source — the same one
  that had already rotted `react-native-best-practices`' section table.
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
