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
| 1 | Context governance | What the agent **knows** | 🟢 Strong | 20 `std-*` + 43 workflow skills; 43 three-tier (110 refs); rule-per-file across 5 skills; CI guards tier discipline **and** the taxonomy |
| 2 | Capability governance | What each **role** can do | 🟢 Good | Bash hole closed; dead `permissionMode` removed; capability enforced by `tools`, guarded by CI |
| 3 | Runtime gates | What happens **as each action fires** | 🟢 Strong | all 6 Ch. 10 gate patterns present; 3 fail-closed gates; fail-open paths visible; protected branches configurable; every deny reason names a **reachable** remedy; MCP installs gated; enforced limits gated against their skill; every warning names a reachable skill; no unattended formatter changes semantics; blocking lists gated against their docs; 176 fixture tests |
| 4 | Permission boundaries | The harness's **own** enforcement | 🟢 Guarded | 30 denies (reference); sentinel detects an **absent OR stale** floor by diffing the plugin's own reference |
| 5 | Organizational policy | What **developers** can grant | 🟢 Good | 4 legitimate uses covered + calibrated against maximalism; `docs/org-policy.md`; CI guards the floor from going stale |
| 6 | Human-in-the-loop | The **person**, for the irreversible | 🟢 Good | `ask` on deploys, migrations, direct pushes to protected branches |
| 7 | External verification | Everything **outside the session** | 🟢 Good | 8 CI jobs incl. changelog-as-interface + release-hygiene (runs on tag push); required branch-protection posture documented in `docs/releasing.md`; **`v2.0.0` prepared — tag it on `main` after the merge to activate the delivery gate** |

---

## DONE

### Layer 7 — the release gate turned `main` red on its own first day — *2026-07-15*
Tagging v2.0.0 activated the delivery gate, and the very next commit tripped it. **`main` was
failing its own release-hygiene check**, and would have gone red in CI.

The cause was a **false positive**, not a real gap. The gate treats everything under `hooks/` as
plugin content and demands a version bump — but the commit only changed
`hooks/tests/run-all.py`. `hooks.json` never references that file, so **a consumer's session
cannot execute it**: a test-only change ships no behaviour and delivers nothing that a version
bump would carry. Verified by listing the 17 files `hooks.json` actually runs; `run-all.py` is
not among them.

This is the failure this loop keeps naming from the other side: **a gate that fires on a change
with no consumer impact is one people learn to `|| true`.** Left alone, the first red CI on a
docs PR teaches the team that release-hygiene is noise — and the *real* stale-version bug it
exists to catch goes with it.

`NOT_SHIPPED_BEHAVIOUR = ("hooks/tests/",)` now excludes the plugin's own CI, and the failure
message names the actual files rather than the top-level directory (it said *"(hooks)"* while the
file was a test — the message hid the cause). Two fixtures, both directions: a test-only change
needs no bump; a real `hooks/auto-format.py` change still fails **and names the file**, so the
exclusion cannot become a hole. **176/176.**

**Method note.** My first probe "proved" the gate no longer caught real changes — because I
edited the working tree and the gate diffs **commits** (`v2.0.0..HEAD`). Correct for CI, invalid
as a test. The scratch-git-repo fixture is the only honest way to test it, which is why the
harness builds one. Sixth measurement error of the session, caught before it became a
"simplification" that gutted the gate.

### BP pass — `std-git-workflow`: a blocking list nobody could read — *2026-07-15*
Two sweeps, both grounded in last iteration's method (verify what a hook *runs*, not what it says).

**Sweep 1 — confirmed.** Beyond `auto-format` (fixed last iteration), the only external commands
any hook executes are `git` calls in 5 hooks, and every one is **read-only**: `status`, `diff`,
`log`, `rev-list`, `rev-parse`. No hook mutates the repo behind you — the hook-level equivalent
of the Bash hole is absent. Fifth consecutive sweep that confirmed rather than found.

**Sweep 2 — found.** `pre-commit-check.py` **blocks** any commit whose type is outside its
pattern, and names `std-git-workflow` in the denial. That makes its type list a **hard
interface**, and the two had drifted: the hook accepts **11** types, the skill documented **10**,
CLAUDE.md listed **9**. `revert` was accepted by the hook and named nowhere — discoverable only
by being denied first. Checked the dangerous direction too: **nothing documented is blocked** (a
documented instruction that cannot be followed would be the worse failure), so this was a
discoverability gap, not a false block.

Fixed in both, and the skill now says the table **is** the accepted set rather than leaving it
ambiguous. `test_commit_types_match_the_skill` parses the hook's regex and the skill's table and
fails on drift **in either direction**, plus live-fire: `revert:` is accepted, `wibble:` is still
blocked. **174/174.**

This is the third instance of one pattern — a list in code and the same list in prose, drifting
silently (200-vs-300 line limits, the 37 dangling pointers, now commit types). All three are now
gated. The generalisation worth keeping: **wherever a hook's behaviour is data (a number, a list,
a path), the data and its documentation need a test, because prose cannot be imported.**

### `/toolchain` skill — and the formatter that silently rewrote semantics — *2026-07-15*
User request: skills/references for linters, checking they are installed, and compilers. Writing
it found a **live defect in this plugin's own hook**.

`auto-format.py` ran **`rubocop --autocorrect-all`**. Verified against the installed gem
(rubocop 1.87.0) rather than the docs, which 404'd:

> `-a, --autocorrect` — *"Autocorrect offenses (**only when it's safe**)."*
> `-A, --autocorrect-all` — *"Autocorrect offenses (**safe and unsafe**)."*

and its own `config/default.yml` marks **80 cops `Safe: false`, 53 `SafeAutoCorrect: false`** —
RuboCop's maintainers flagging corrections that can change behaviour. So this hook applied
semantic rewrites **unattended, on every `.rb` write, with stdout/stderr sent to DEVNULL**, to
code nobody re-read. `Lint/BinaryOperatorWithIdenticalOperands` (`Safe: false`) is the shape of
the harm: `user.role == user.role` is a real typo, and an unsafe autocorrect rewrites the
expression so the bug becomes invisible.

Now `--autocorrect` (safe only). **A formatter may reshape code; it must never change what the
code means while nobody is reading.** `-A` remains the right tool for a human who reads the diff.
`test_autoformat_never_changes_semantics` fails the build if any unattended formatter regains an
unsafe flag, and asserts `.rb` still autocorrects (the safe half is the point) and that
prettier/black/`terraform fmt` stay layout-only. **170/170.**

The skill itself (`/toolchain`, 114 + 2 refs): the four tiers and why most toolchain arguments
compare tools from different ones; **check but never install** (a global install is a
machine-level change that often makes CI parity *worse*, by shadowing the bundle's pinned
version); `bundle exec`/`pnpm exec` because a bare `rubocop` is a different program; and
`tsc --noEmit` as the highest-value command most CI omits — **Vite and Next do not typecheck**,
they strip types with esbuild/SWC, so a type error can pass dev, pass build, pass a green CI and
reach production having failed nothing.

### Layer 3 — 7 hooks warned into the void — *2026-07-15*
Generalised last iteration's finding. That one gated *one* hook's numbers against *one* skill;
the obvious question was whether other hooks drift the same way. **They do not** — a sweep found
`code-quality-checker.py` is the only hook with numeric constants, and it is already gated. The
tag list (`project`, `environment`, `team`, `managed-by`) **agrees** across
`terraform-checker.py`, `std-terraform-conventions` and `std-infrastructure`. Fourth consecutive
sweep that confirmed rather than found.

What it did find is the *other* direction. Three iterations ago I fixed 37 hook messages that
named a skill **that did not exist**. The mirror was never checked: **7 hooks name no skill at
all.** `security-scan`, `pre-commit-check`, `terraform-checker`, `terraform-command-gate`,
`atomic-design-checker`, `design-token-checker`, `dangerous-command-blocker` all warn correctly,
name a remedy correctly — and leave the reader nowhere to learn *why*. Eleven hooks point at a
skill; these seven pointed at nothing, which is an inconsistency a developer experiences as
arbitrariness.

All 7 now name the skill that carries the rule, and the gate generalises with them:
`test_hook_messages_point_somewhere_real` previously asserted *"the skill you name must exist"*
and now also asserts *"you must name one"*, with a **documented exemption list** — `auto-format`
names an install command (no skill teaches "have rubocop on your PATH"), `audit-logger` records
rather than warns. **165/165**, 44 skill pointers checked.

**Fourth regex false positive of the session, and the most instructive.** The sweep first reported
`i18n-checker.py` as naming no skill. It names `std-i18n` twice — my character class was
`[a-z-]`, which excludes the digits in `i18n`. Had I trusted it I would have "fixed" a hook that
was already correct. Every sweep in this loop is a **lead generator, never a verdict**; the
running tally is now 4 false alarms (the "Nest" verb, Rails' `request.ip`, `MAX_PARAMS`, and this)
against 8 real defects.

### BP pass — `std-code-standards`: the gate's number and the skill's number disagreed — *2026-07-15*
`code-quality-checker.py` warns at **200 lines** for Rails models and UI components and names the
`std-code-standards` skill in its message. That skill said **"Target maximum 300 lines"** and
never mentioned 200. So: developer writes a 250-line model, reads the skill it was pointed at,
sees 300, gets warned anyway, and concludes the hook is noise. A gate whose number disagrees with
the skill it names is worse than no gate — it teaches people to click through.

Notably the number **was** documented — in `CLAUDE.md` and in `sdh-engineering-standards` — but
**a plugin's `CLAUDE.md` is not shipped as consumer context** (this repo says so itself), and the
skill that *auto-loads on the file you are editing*, and that the hook *names*, is
`std-code-standards`. Right rule, wrong file. The body now carries both numbers, the wrapper-
agnostic path list, and the rationale (models and components are where responsibilities
accumulate without anyone deciding to add them — a 300-line service does one thing at length; a
300-line model is a god object), plus the fact that all four limits are **advisory, never
blocking**.

**`test_limits_match_the_skill_that_documents_them`** (new): every constant the hook enforces
(`MODEL_LIMIT`, `COMPONENT_LIMIT`, `DEFAULT_LIMIT`, `MAX_FUNCTION_LINES`, `MAX_PARAMS`,
`MAX_NESTING`) must appear in the skill its message points at, and in the always-on skill
consumers actually receive — imported from the hook module, so changing a constant without
updating the prose fails CI. Plus a live-fire case proving a model over the limit still warns.
**164/164.**

**Three false alarms caught, and worth recording** — the pull to find a defect is now the main
risk in this loop:
1. `MAX_PARAMS = 4` looked undocumented. My grep used BRE alternation (`\|`) under `-E`, so it
   searched for a literal string. The skill documents it on line 38.
2. The hook looked **dead** — silent on a 252-line model, twice. Both times my harness was wrong:
   first a path that did not exist (the checker is PostToolUse and reads from **disk**, which is
   correct), then a Git Bash `/tmp/...` path invisible to native Windows Python. Tested inside
   Python with a real file: the hook warns exactly as designed.
3. Reporting a phantom bug in a working gate would have been worse than the gap actually fixed.

### `code-reviewer` now checks what this loop found — *2026-07-15*
Closes **P2**. Ch. 23's ritual is *"every repeated review comment is a reference candidate"*;
the inverse is what this pass implements: **every defect this loop verified becomes a review
check.** The reviewer's stack checks were one line per stack and predated all of it — it could
not have caught a single bug this loop fixed.

Added to `references/pr-review-guide.md` (now reachable, since last iteration) a section grouped
by the property these share: **nothing fails, nothing raises, and the diff looks fine.** Each is
a grep, not a judgement call:
- the policy nobody called (`policy_scope` filters; `authorize` does not — and `index` using
  `authorize` returns every row to any signed-in user);
- the migration with no `lock_timeout` (default 0 = wait forever, and a waiting `ALTER TABLE`
  queues every query behind it);
- the column drop with no `ignored_columns` deploy first (AR caches the column list — live
  instances 500 on rows they never touched);
- the transaction that commits half (non-bang `create` returns `false`, so the block completes);
- the trace that dies at the async boundary.

Each cross-links to the reference that owns it rather than restating — the contradiction class
this loop has been eliminating. The body carries only the five greps (tier 2: they apply to every
Rails review); the depth stays in the guide.

**Fixed a contradiction found while editing.** The guide's *"GREEN: Idempotent job"* taught
`return if order.charged?` **as the answer**. `std-error-handling/references/background-jobs.md`
(verified against Sidekiq's wiki) says that guard is a race-prone optimisation — two workers can
both pass it — and the **server-side idempotency key** is the correctness. The GREEN example also
carried no `sidekiq_options`, so the repo's model idempotent job was silently inheriting *25
retries over ~20 days* on a payment. Both fixed.

**Sizing recorded, not churned:** `pr-review-guide.md` is now **325** lines (+8% over the ~300
guideline). It also has a genuine Ch. 7 split signal — reviewing a Rails PR never needs the React
Native red flags. Added to the sizing backlog rather than shredded mid-pass; the *deliberate
non-decisions* below say a guideline is not a gate.

### Layer 1 — 14 references existed that nothing could ever load — *2026-07-15*
Aimed the BP mandate at the **agents**, the one class still entirely `todo`. Ch. 8's Bash hole
was the obvious target: an agent claiming read-only while holding `Bash` is theater. Swept all
13 — and `security-auditor` is **already honest** (it says *"You hold `Bash`, which is write
access"* and cites Ch. 8 by name; my grep matched the lines that **deny** read-only status). A
previous pass got there first. Layer 2 confirmed 🟢; nothing to do. **Third consecutive sweep
that confirmed rather than found** — worth recording, because the pull to find something is how
you break working content.

The sweep did surface something else. `code-reviewer` has **one line** of Rails checks and zero
mention of `verify_authorized`, `lock_timeout`, `sidekiq_options`, `request_id`, `ignored_columns`
— i.e. **every defect this loop actually found is invisible to the review agent**. Chasing that
led to the real finding.

**14 reference files (2,298 lines) exist that no body — and no agent — ever names.** Written,
maintained, and unreachable: `api-designer`, `code-reviewer` (×2), `incident-response`,
`nextjs-dev` (×3), `onboarding`, `performance-profiler`, `reactjs-dev` (×3), `security-auditor`,
`test-generator`. Verified they are not indexed from the agents either, since several of these
skills route to one — they are indexed from **nowhere**.

Ch. 7 is unambiguous about why this is fatal rather than untidy: **tier 1 is the catalog.** If
the body does not name the file, the model never learns the knowledge exists, so it is never
loaded — no matter how good it is. `code-reviewer`'s `pr-review-guide.md` contains exactly the
N+1, migration-safety and Sidekiq checks the reviewer needed, and has been unreachable the whole
time.

**This is the exact mirror of the dangling hook pointers fixed three iterations ago:** there a
pointer had no destination; here a destination had no pointer. Same defect, opposite direction —
and the repo already gated one side and not the other. **The CI enforced it for `rules/` and
never for `references/`.** Now both: `skills-lint` fails when a `references/*.md` is not named by
its body ("add it to the Deep guides index, or delete the file"). Gate written first, confirmed
firing on all 14, then fixed. Every index line is drawn from the file's actual headings, not its
name.

**Both directions now hold: 0 pointers without a file, 0 files without a pointer, 110 references
reachable.**

**Newly recorded, not fixed here:** `code-reviewer`'s stack checks predate everything this loop
verified (retry stacking, `lock_timeout`, `verify_authorized`, `request_id`). Now that its
references are reachable, folding those in is a real next pass — P2 below.

### `/mcp-advisor` skill + `mcp-install-gate.py` — MCP as an instruction source — *2026-07-15*
User request: discover MCPs, suggest them, and **ask permission before adding one**. The repo
had **no MCP skill at all** — MCP appeared only in `docs/org-policy.md` (layer 5
`allowedMcpServers`) and in the CI rule rejecting `mcpServers` on plugin agents.

**The third ask is a placement-test question, and it decided the design.** "Never add an MCP
without asking" must hold whether or not anyone reads the skill → Ch. 7: that is **not context,
it is a gate**. So `mcp-install-gate.py` (PreToolUse, `ask`, fail-open) covers `claude mcp add`,
`add-json`, `add-from-claude-desktop`, **and writes to `.mcp.json`** — gating only the CLI would
be a gate with a door next to it. It stays silent on `list`/`get`/`remove` (removal *reduces*
capability; gating it would be the crying-wolf failure). `ask`, never `deny`: MCP servers are
legitimate, and a deny here just gets the plugin disabled. 12 fixtures.

**The framing the skill is built on**, verified from the docs: *"Verify you trust each server
before connecting it. Servers that fetch external content can expose you to prompt injection
risk."* A library is text you **run**; an MCP server is text the model **obeys** — its tool
descriptions are prompts, and its responses are content the model reasons over. So a Jira MCP is
only as trustworthy as whoever can file a ticket. That is not an argument against MCP; it is the
argument for a human picking each one.

Also verified and load-bearing: **local scope is the default** (`~/.claude.json`, private, this
project only) while `--scope project` writes a **committed `.mcp.json`** that loads for every
teammate as `⏸ Pending approval` — a trust decision made on their behalf. And `headersHelper`
**executes arbitrary shell commands**, so a `.mcp.json` in a PR is code, not config.

The skill's honest counsel: **prefer the CLI you already have.** `gh` runs under the permission
and hook layers that exist; an MCP adds a new instruction source and a new credential. The docs'
own trigger is the bar — *"connect a server when you find yourself copying data into chat"* —
repetition, not novelty.

### Layer 1 — WCAG 2.2: an AAA criterion sold as AA — *2026-07-15*
`std-accessibility` claimed *"WCAG 2.2 adds 7 success criteria ... All are required for AA
compliance"* and listed **2.4.13 Focus Appearance (AA)**. Both halves wrong, in the
**over-governing** direction: 2.2 adds **nine** (and removes 4.1.1 Parsing, obsolete), and W3C
states *"Understanding SC 2.4.13 Focus Appearance **(Level AAA)**"*. Six of the nine bind at AA;
2.4.12, 2.4.13 and 3.3.9 are AAA.

Holding a team to a AAA bar while calling it AA is Ch. 20's failure mode — *"teams that
experience governance as obstruction disable it"*. The requirement is worth keeping (the design
system already ships the ring), so it stays, **relabelled honestly as a house rule** stricter
than AA, in all 4 places it appeared across `std-accessibility` and `accessibility-auditor`.

**Verification cut both ways, which is the whole point.** The W3C *"What's New in WCAG 2.2"*
summary grouped **3.3.7 Redundant Entry under AAA**; the skill said Level A. The authoritative
per-criterion page settles it — *"Understanding SC 3.3.7 Redundant Entry (Level A)"* — so the
**skill was right and the summary page was wrong**. Trusting the first source would have turned a
correct label into an incorrect one. Check the per-criterion page, never the summary.

### BP pass — `std-nextjs`: verification that confirmed rather than found — *2026-07-15*
Seventh BP iteration, aimed at the highest-risk factual surface in the repo: Next.js caching,
which the book calls *"the framework's most error-prone surface"*. Next.js 15 flipped the
caching defaults, so this was the most likely place for the "written from memory, never verified"
defect that the last three passes each found.

**It isn't there. The Next.js content is already correct** — `await cookies()`,
`params: Promise<…>`, `await params` throughout, **zero** synchronous Next-14 usages. And
`caching.md` never leans on the `fetch` default at all: every call states
`next: { revalidate, tags }` explicitly, which insulates it from the 14→15 flip entirely. That is
good design that predates this loop, and the honest result of the check is *"leave it alone."*
Recording the negative matters: three consecutive passes found defects, and the pattern-matching
urge to find a fourth is exactly how you break working content.

A repo-wide sweep for six Next-14-isms (sync `cookies`/`headers`, sync `params` types,
`useFormState`, `serverComponentsExternalPackages`, `NextRequest.geo`/`.ip`) returned **one hit,
and it was a false positive**: Rails' `request.ip` in a rack-attack example, matched by a regex
that does not know Ruby from TypeScript. Same shape as the "Nest" verb false positive two
iterations ago — the sweep is a lead generator, never a verdict.

**The one real gap: no version was pinned anywhere**, in a repo whose own non-negotiable is *pin
every version*. Guidance that does not say which major it means cannot be checked — and here the
majors genuinely disagree. The body now states **Next.js 15+ / React 19** and carries a 14-vs-15
table of what changed (`fetch` and `GET` handlers no longer cached by default; Client Router
Cache no longer reuses page segments; `cookies`/`headers`/`params`/`searchParams` now async),
verified against the official upgrade guide. It also explains *why* `caching.md` is verbose:
**never rely on the `fetch` default** — 14 said cached, 15 says uncached, so any code whose
correctness depends on the default is a version bug waiting to happen.

### BP pass — `std-error-handling`: the retries nobody configured — *2026-07-15*
Sixth BP iteration. Ran the "asserted everywhere, shown nowhere" sweep from the last two passes
across 8 more concepts (health checks, feature flags, idempotency, ADRs, Result objects, rate
limiting, soft delete) — **all had a mechanism somewhere**. That sweep is now closed: it
confirmed rather than found. Sidekiq did not: `sidekiq_options retry`,
`sidekiq_retries_exhausted`, `death_handlers`, Dead set — **0 files**, while
`std-rails-conventions` asserts *"set sensible retry limits and dead-letter handling"*.

**Verifying against the Sidekiq wiki turned a doc gap into a live defect.** The repo's guidance
said *"configure `retry_on` for transient errors"* — an **ActiveJob** API under a Sidekiq
heading. Sidekiq's own wiki:

> *"ActiveJob does not provide a retry mechanism on its own, but failed ActiveJob jobs will
> retry"* ... ActiveJob retries first, then *"will kick the job back to Sidekiq, where Sidekiq's
> retries with exponential backoff will take over"* — the default being *"25 retries over
> approximately 20 days."*

So `retry_on ..., attempts: 5` is **not** 5 attempts. It is 5, then 25 more, across three weeks.
**The repo's own canonical example (`rails-architect/references/rails-patterns.md`) had exactly
this on a *payment* job** — a charge retried for ~20 days, in the pattern the repo holds up as
correct. Fixed: one policy via `sidekiq_options retry: 5` (which works on ActiveJob classes and
does not stack), plus `sidekiq_retries_exhausted` so the job cannot die into the Dead set
silently.

`references/background-jobs.md` (214) — the defaults nobody reads, `retry: 0` (to the Dead set,
kept) vs `retry: false` (**discarded** — one character apart, opposite outcomes), the stacking
trap, ActiveJob vs `include Sidekiq::Job` (*"about 30% overhead"*), the Dead set as silent
failure (10k jobs / 6 months), why rescue-and-swallow **disables the retry** while reporting
success, and timeouts (without them there is no failure to retry — just a stuck queue and a
green dashboard).

**New finding recorded, not silently decided:** the repo is **split** on the job API — 5 files
`< ApplicationJob`, 3 `include Sidekiq::Job` (two of those three were added by this loop). The
reference states the tradeoff and recommends native, rather than a rewrite nobody asked for.

### BP pass — `std-monitoring`: 11 files depended on an id nobody defined — *2026-07-15*
Fifth BP iteration. The measurement found a **dangling dependency**, not a missing topic.

`request_id` is referenced by **11 files** — `std-monitoring` requires it on every log line,
`monitoring-checker.py` and `api-design-checker.py` **warn when it is absent**, `std-api-design`
puts it in the error envelope, and the whole "trace one request" workflow in `log-search` is
built on it. The **mechanism was documented nowhere**: `ActionDispatch::RequestId`,
`TaggedLogging`, `CurrentAttributes`, `X-Request-Id`, Sidekiq propagation — **all zero files**.

So a developer hit by *"Include request_id for distributed tracing per the `std-monitoring`
skill"* opened that skill and found… the same assertion. Eleven pointers, no destination. This is
the sibling of last iteration's dangling hook messages: there the *link* was broken, here the
*content* was. Both look fine from every angle except the reader's.

`references/request-tracing.md` (209) — and the load-bearing point is the one nobody writes down:
**the trace breaks at the async boundary.** A Sidekiq job runs in another process with no
request, so `Current.request_id` is `nil` exactly where you need it — the async work is what
fails at 3am. Covers client+server middleware (including `configure_server`'s *client* middleware,
or the trace dies one hop later when a job enqueues a job), the `ensure` reset (Sidekiq reuses
threads; a leaked id mislabels the next job, which is worse than no id), `Current` over
`Thread.current` because Rails resets it between requests, and a one-`curl` end-to-end proof.

**Verified against the Rails docs, which corrected me and added a finding.** The guide documents
`ActionDispatch::Request#uuid`, not `#request_id` — the API docs confirm `uuid` is the **alias**
and both work. And the id *"is either based on the `X-Request-Id` header in the request, which
would typically be generated by a firewall, load balancer, or the web server"* — so the ALB's
trace id flows straight through, joining your logs to the LB's for free. Rails *"sanitize[s] it
to a max of 255 chars and alphanumeric and dashes only"* **because a client can send it**: the id
is outside input, now flagged in the body as never-interpolate-into-SQL.

`std-monitoring` had **zero code examples** in 67 lines — it asserted the rule and never showed
the mechanism. The body now carries the load-bearing lines; the reference carries the depth.

### `db-migration` restacked to ActiveRecord + Postgres — and the folklore was wrong — *2026-07-15*
Closes **P2**. `SKILL.md` (192→108) and `references/migration-guide.md` (287→312) were raw SQL
with MySQL branches (`ALGORITHM=INPLACE`, `pt-online-schema-change`, `gh-ost`) and **zero**
ActiveRecord, in a Rails/PostgreSQL-only stack. Now 0 MySQL references and 31 ActiveRecord ones.
`references/postgres-patterns.md` was already correct and was left alone.

**Verifying against the Postgres docs found the guide was not merely off-stack — it was wrong,
in the expensive direction.** It labelled `ADD COLUMN ... NOT NULL DEFAULT 'x'` as *"rewrites
entire table"* and prescribed a batched-backfill dance. Postgres:

> *"When a column is added with `ADD COLUMN` and a non-volatile `DEFAULT` is specified, the
> default value is evaluated at the time of the statement and the result stored in the table's
> metadata … **making the `ALTER TABLE` very fast even on large tables**. In neither case is a
> rewrite of the table required."*

So the guide made teams do a multi-step migration for something that is **free**, while never
mentioning what *does* rewrite: a **volatile** default (`clock_timestamp()`), stored generated
columns, identity columns. It also never mentioned that `SET NOT NULL` *"requires scanning the
table"* under an exclusive lock — the actual expensive half — nor the `NOT VALID` → `VALIDATE`
split that avoids it. The rewritten guide leads with a what-actually-locks table sourced from the
docs, and carries the ActiveRecord-specific traps the SQL version could not: `ignored_columns`
before a drop, passing the type to `remove_column` so `change` stays reversible,
`add_foreign_key validate: false` → `validate_foreign_key`, and `unscoped` on backfills.

**The hook contradicted the guide, and was factually wrong.** `migration-validator.py` flagged
`remove_column` in `change` as irreversible — but `remove_column :orders, :status, :string` **is**
reversible, and is exactly the form the new guide recommends. It also called `rename_column`
irreversible; ActiveRecord inverts it fine. A gate that fires on correct code is one people learn
to click through — my own lesson from the taxonomy pass, arriving from the other direction. Now:
`remove_column` only without a type, `drop_table` only without a block, and `rename_column`
warns for the **real** reason (it breaks running instances mid rolling-deploy — a deploy problem,
not a rollback one) with the real remedy. Also dropped the hard-coded `/backend/db/migrate/`
path, a leftover from the forced-layout era that contradicted wrapper-agnostic detection;
`/migrate/` already matches any wrapper, and a fixture proves `api/db/migrate` is validated.

6 new fixtures. **149/149.**

### Layer 3 — 37 hook messages pointed at files that no longer exist — *2026-07-15*
The backlog said *"audit for the same defect elsewhere before assuming it is confined to these
two."* Doing that first — instead of fixing the known instance — is what found this.

**The wrong-stack defect is NOT the pattern I claimed.** Sweeping every out-of-stack technology
across `skills/` returned almost all **false positives**: "Nest sub-resources" is the English
verb, `mysql` in `security-auditor` is a *secret-detection regex* (correctly including it),
Firebase is genuinely in the stack, and Azure/GitLab appear once each as generic examples. Only
`db-migration` is real. My *"pattern, not an incident"* was **overstated**, and the corrected
scope is recorded below rather than left to justify a rewrite it does not justify.

**What the sweep actually found is worse.** Converting `.claude/rules/*.md` into `std-*` skills
left **37 messages across 10 hooks** pointing at `accessibility.md`, `security.md`,
`database.md`, `code-standards.md`, `api-design.md`… — **none of which exist**. Every one of
those hooks fires correctly, explains itself, and sends the reader to a file they will never
find.

That is a direct hit on Ch. 13's adoption property: *"It explains its denials … the deny reasons
are your plugin's user interface, and they're the only part most users will ever read"* — and on
Ch. 25: a reason must name a remedy. **A remedy nobody can follow is not a remedy.** It is also
precisely the class this repo already fixed once (the dead `.claude/rules/security.md` path in
the managed-settings template) — fixed there, never swept for elsewhere.

- All 37 now name the skill that actually carries the rule (`per the `std-accessibility` skill`).
  All 12 referenced names mapped cleanly onto existing `std-*` skills.
- **`test_hook_messages_point_somewhere_real`** (new): every `*.md` a hook names must exist on
  disk, and every `` `std-x` `` it names must be a real skill (39 pointers checked). Proven to
  fire against an invented pointer rather than merely agreeing with today's tree. **145/145.**

**Why a test and not care:** the existing `test_deny_reasons_name_a_remedy` checked that reasons
*name* a remedy — it never checked the remedy was reachable. The conversion passed every gate the
repo had. Ch. 7's placement test settles it: this must hold whether or not anyone reads it, so it
is not context — it is a gate.

### BP pass — `std-database`: written for a stack this repo doesn't use — *2026-07-15*
Fourth BP iteration. Measuring found something worse than a missing topic.

**`std-database` had ZERO ActiveRecord content.** Every example was **`knex` / TypeScript** — a
Node query builder that appears nowhere in CLAUDE.md's stack — in a repo whose backend is Rails
on PostgreSQL. The rules were fine; the code was for somebody else's project. Restacked the three
examples to ActiveRecord, and used the rewrite to add what the Rails idiom actually gets wrong:
`create!` vs `create` inside a transaction (the non-bang form returns `false`, so the block
completes and commits half the operation), `after_commit` vs `after_save` for jobs/Centrifugo,
`includes`/`preload`/`eager_load` + `references`, and Panko serializers as where N+1 hides.

**The genuine gap: `lock_timeout` / `statement_timeout` = 0 files repo-wide** — while "Migration
Safety" is a whole section here *and* `db-migration` owns a 287-line migration guide. Both cover
*which operation* is safe; neither covered **the lock you take while doing it**, which is the
mechanism behind most migration outages:

> `ALTER TABLE` needs `ACCESS EXCLUSIVE`, which *"conflicts with locks of all modes"*, and
> *"Only an `ACCESS EXCLUSIVE` lock blocks a `SELECT`"*. A transaction *"will wait indefinitely
> for conflicting locks to be released"* — and queries arriving after it queue behind it. So a
> millisecond-fast, correctly-written migration becomes a full table outage for as long as some
> unrelated reporting query runs. **`lock_timeout` defaults to 0: wait forever.**

`references/locking-and-timeouts.md` (203) — the mechanism, the one line every migration needs,
retrying (failing is the *good* outcome), `disable_ddl_transaction!` and the invalid index it can
leave, `pg_blocking_pids()` to name the culprit, idle-in-transaction, row vs advisory locks.

**Verified against the Postgres docs, and it caught a subtlety I'd have missed:** *"if
`statement_timeout` is nonzero, it is rather pointless to set `lock_timeout` to the same or larger
value, since the statement timeout would always trigger first"* — so `lock_timeout` **must be
smaller**, or it is decoration. Also confirmed: neither should go in `postgresql.conf`.

### BP pass — `std-infrastructure`: keys nobody needed, tags that aren't pins — *2026-07-15*
Third BP iteration, on the "extend GitHub Actions / AWS / GCP alongside Terraform" ask. Measured
first; the measurement moved the work.

**Not written:** AWS OIDC and PR-check pipelines are already owned by `references/ci-pipeline.md`,
and Terraform has 47 rule files. Duplicating either would be padding.

**Two real gaps, both zero-coverage repo-wide:**

- **`workload_identity_provider` / "Workload Identity" = 0 files.** Worse, the repo was
  *internally inconsistent*: `ci-pipeline.md` teaches keyless OIDC for AWS, while
  `gcp-secondary-cloud.md` (39 lines) had exactly one auth story — **download a service-account
  key**. Google's own guidance: *"Workload Identity Federation is recommended over Service
  Account Keys as it obviates the need to export a long-lived credential"*, and JSON keys *"must
  be treated like a password."* Rewrote it (156 lines) around a keyless-first decision table,
  keeping the AWS-primary stance and the "when a key is unavoidable it lives in AWS Secrets
  Manager" rule as the documented fallback rather than the default. Includes the line that
  actually matters: **`attribute_condition` scoping the provider to your repo** — without it, the
  provider trusts *every* GitHub Actions run in existence, and "keyless" becomes world-writable.
- **`workflow_call`, composite actions, action pinning, Dependabot = 0 files.** New
  `references/github-actions.md` (234): a third-party action is code you run with your token, and
  **`@v4` is a mutable tag, not a version** — the mechanism behind the `tj-actions/changed-files`
  compromise. Plus `permissions` least privilege, `concurrency` (and why `cancel-in-progress` must
  be **false** for deploys — cancelling a half-applied migration is worse than queueing), reusable
  workflows vs composite actions, environments as the layer-6 human gate, and the
  `pull_request_target` hole.

**Body reconciled, not just extended.** Two non-negotiables now contradicted the references, so
they were fixed rather than left to rot: "pin every version" said nothing about action tags not
being pins, and the secrets rule implied GCP *always* has a credential to store. The body now
leads with **prefer no credential at all**.

**Verified against the vendor docs before writing** (mandate): the `google-github-actions/auth`
inputs, the required `id-token: write`, and Google's own key-vs-federation wording.

### BP pass — `std-react-native`: the two pillars it asserted but never showed — *2026-07-15*
Second BP iteration. Measured first again, and it redirected the work twice.

**What I did *not* write.** List/render performance looked like the obvious gap — but
`react-native-best-practices` already owns 38 rule files for it. axios token-refresh is covered
in 6 files. Both skipped; writing either would have been padding.

**What was actually missing.** `onlineManager`, `persistQueryClient`, `MutationCache`,
`setMutationDefaults` and `Centrifuge` were at **zero coverage across the whole repo** — while
`SKILL.md` asserted *"queue mutations when offline, replay on reconnect"* and *"update TanStack
Query cache on real-time events"* as if settled. Two core pillars of this stack (CLAUDE.md names
Centrifugo as the real-time layer) with the mechanism documented nowhere.

- `references/offline-and-mutations.md` (218) — the part the one-liner hides: queuing is free,
  **surviving an app kill is not**. Only mutation *state* persists (functions are not
  serializable), so a resumed mutation dies with `No mutationFn found` unless
  `setMutationDefaults` is registered at **module scope before hydration** — the failure only
  appears when the app is killed, which is why it ships. Plus NetInfo → `onlineManager`, and
  idempotency keys generated **once at the call site** (generating inside `mutationFn` defeats
  the whole mechanism).
- `references/realtime-centrifugo.md` (200) — **`newSubscription()` throws if the channel is
  already registered**, which is exactly what a remounting screen does; `unsubscribe()` does not
  remove listeners, so remounts stack handlers; the socket does not backfill on reconnect;
  `getToken` vs a static `token` (the "real-time stopped working after an hour" bug).

**Verified against the real docs before writing** (mandate): TanStack's own wording on
non-serializable functions and `No mutationFn found`; centrifuge-js v5's *"throws an exception
if the Subscription to a channel already exists"* and *"unsubscribing does not remove event
handlers"*. The throw-on-duplicate is the crux of the hook example — asserting it from memory
would have been exactly the "reference that is wrong causes visible harm" case.

**An incident became a control.** I wrote a bare cross-skill pointer
(`std-api-design/references/x.md` instead of `../std-api-design/...`) **three times in two
iterations**; the resolver reads only the trailing `references/x.md`, so it dangles. Rather than
resolve to be more careful, the CI check now **names the remedy** (Ch. 25): it finds which skill
actually owns the file and prints the exact `../owner/references/x.md` to use. Verified by
simulating the mistake.

### BP pass — `std-rails-conventions`, `std-security`: the policy nobody calls — *2026-07-15*
First iteration of the standing best-practices mandate. Two skills, one real gap.

**The gap was found by measuring, not guessing.** `N+1` already appears in 9 files and
`includes(` in 10, so the obvious "add a queries reference" would have been duplication.
`verify_authorized` and `JTIMatcher` appeared in **zero files** — while `Pundit` policies are
documented in 10. The repo taught how to *write* a policy and never how to guarantee it is
**called**.

That gap is not academic: a controller action that forgets `authorize` does not raise, does not
warn, and passes a happy-path spec. It returns `200 OK` with another user's data. It is OWASP
**#1 Broken Access Control** — which `std-security` itself lists first — and it is invisible in
review *because the policy file exists*. Pundit ships the fix (`after_action :verify_authorized`
/ `verify_policy_scoped`) and it is **off by default**.

- `std-rails-conventions/references/authorization.md` (211 lines) — `policy_scope` vs
  `authorize` (authorizing a collection does not filter it), 404-not-403 for non-owners (a 403
  confirms the record exists), deliberate `skip_authorization` for public endpoints, the
  negative-path specs that are the only ones that catch this, and `devise-jwt` revocation
  (JTIMatcher + unique `jti`) — without a strategy, sign-out leaves the token valid until expiry.
- Body gains only the load-bearing lines (Ch. 7: applies to every controller task → tier 2).
- `std-security` gains the access-control rules its JS-only example did not carry, pointing at
  the Rails mechanism.

**Ownership kept clean:** the 403 envelope and `rescue_from Pundit::NotAuthorizedError` already
belong to `std-api-design/references/errors-rails.md`; this reference points there rather than
restating it — the contradiction class that bit terraform.

**Verified against the real libraries before writing, per the mandate — and it paid.** The
Pundit README gives `include Pundit::Authorization` (plain `include Pundit` is deprecated) and
the skip methods are **`skip_authorization` / `skip_policy_scope`** — not the
`skip_verify_authorized` I was about to write. devise-jwt's JTIMatcher setup and the
`null: false` + unique `jti` index were confirmed from its README.

**The CI reference gate caught my own sloppiness:** I wrote cross-skill pointers as
`std-api-design/references/x.md`, which the resolver does not accept — the established form is
`../std-api-design/references/x.md`. Fixed the pointers rather than loosening the gate.

### Ch. 13 — the version is a delivery handle, and ours is stale — *2026-07-15*
Closes **P1 · Versioning / supply chain** and **P3 · Layer 7 repo-side controls**. The P1 entry
understated the problem: it said *"consumers cannot pin"*. Checking the actual plugin docs
turned that into something sharper and worse.

> *"Setting `version` pins the plugin. If `plugin.json` declares `"version": "1.0.0"`, pushing
> new commits without changing that string **does nothing for existing users**, because Claude
> Code sees the same version and keeps the cached copy."*

**So this is not "consumers can't pin" — it is a silent delivery failure.** `plugin.json` has
declared `1.0.0` since the plugin-conversion commit while **16 commits changed plugin content**,
including the fail-closed terraform gate and the sentinel. Merged, green, and received by
**nobody** who already installed. Same shape as a dead gate masquerading as a green one — which
is why it now has a gate rather than a doc.

Verified against the plugin-marketplace docs rather than assumed (the mechanisms are real):
version resolution is `plugin.json` → marketplace entry → commit SHA; git sources take `ref`
and `sha`, with **`sha` the effective pin when both are set**; declaring `version` in both
plugin.json and the marketplace entry means plugin.json wins **without warning**.

- **`.github/scripts/check_release_hygiene.py`** + a CI job that also runs **on tag pushes** —
  the moment a consumer's pin starts pointing at a commit is the last moment to catch the tag,
  the manifest, and the CHANGELOG disagreeing. Enforces: semver; no double-declared version;
  **plugin content changed since the newest tag ⇒ version must have moved**; on a tag push the
  tag/version/CHANGELOG agree and `[Unreleased]` was drained.
- **The gate is inert until the first tag exists — and announces that on every run.** An inert
  delivery gate that stayed quiet would be indistinguishable from a passing one (Ch. 9).
  `test_release_hygiene_checker` asserts the announcement, then proves the gate **fires** on all
  six failure shapes against a scratch git repo. **143/143.**
- **`docs/releasing.md`** — the two viable postures (explicit versions *or* omit `version` and
  deliver by SHA) and the accidental third state that looks like the first and behaves like
  nothing. Includes the SemVer table judged from the *consumer's process*: **a new deny is
  MAJOR**, because work that succeeded yesterday now stops, whatever the diff size.
- **Layer 7 repo-side posture documented** there too: required PR + status checks, review
  **not from the author** (Ch. 20 — *"if the same tired person clicks `ask` and approves the
  PR, you have one layer wearing two hats"*), up-to-date branches, and **restricted tag
  pushes** — a tag is what consumers pin, so whoever can move it can change what every pinned
  consumer runs.
- README now says plainly that the documented install **floats on `main`**, with the verified
  `ref`/`sha` pin JSON.

**The maintainer chose MAJOR: `v2.0.0` is prepared, not yet tagged.** `plugin.json` and
`marketplace.json` declare `2.0.0`, `[Unreleased]` is drained into a `## [2.0.0]` section that
leads with what breaks and how to pin, and a simulated `refs/tags/v2.0.0` push passes the gate
(a mismatched tag still fails). MAJOR is what this repo's own table demands: the terraform gate
denies work that previously succeeded, and that is breaking from the consumer's process whatever
the diff size.

**Still outstanding — the tag must point at `main`, not a feature branch**, because the tag is
what consumers pin: merge `feat/governance-layers`, then `git tag v2.0.0 && git push origin
v2.0.0` on the merge commit. Until then the delivery gate stays inert and says so.

### Ch. 13 — "a plugin others will actually use": day-one + configurable edges — *2026-07-15*
Audited the plugin against Ch. 13's four adoption properties. Two held; two did not.

| Property | State |
|---|---|
| It explains its denials | ✅ already enforced by `test_deny_reasons_name_a_remedy` |
| README leads with the permission block | ✅ |
| **It works on day one, in a repo you didn't design** | ❌ fixed below |
| **It's configurable at the edges** | ❌ fixed below |

**Works on day one.** *"A linter hook that can't find the linter should say so once and exit 0,
not crash on every write."* `auto-format.py` got the exit-0 half right and the *say so* half
wrong: it exited **silently**, so a developer without `rubocop`/`prettier` watched formatting
quietly never happen and had no way to learn why — Ch. 9's "silent failure is invisible failure"
wearing a formatter's name. It now prints one actionable line naming the binary **and its install
command**, once per session, then stays quiet. The `except Exception: pass` around the formatter
run was the same silent swallow and got the same treatment (a non-zero formatter exit is normal
and does not land there — this is the formatter failing to *run*).

**Configurable at the edges.** *"Hard-coding your team's test command, branch names, or protected
paths makes the plugin unusable elsewhere."* Nothing in `hooks/` read a single environment
variable, and `main|master|develop` was hard-coded across three hooks — so a repo whose trunk is
`trunk` got **no protection at all**, silently. Added `hooklib.protected_branches()` /
`env_list()` / `branch_alternation()`, honouring **`SDH_PROTECTED_BRANCHES`**, and wired
`pre-commit-check.py`, `deployment-gate.py`, and `session-start-check.py` to it. Defaults are
byte-identical to the previous behaviour — this is not a behavioural change for existing
consumers, and a fixture proves it per branch.

Two judgment calls, made deliberately rather than by default (Ch. 9):
- **A blank `SDH_PROTECTED_BRANCHES` falls back to the defaults** rather than protecting nothing.
  An empty value almost always means "not set here"; the unprotected reading is the dangerous one.
- **If the once-per-session marker cannot be written, the notice speaks anyway.** A repeated
  notice is visible and fixable; a silent hole is neither.
- Branch names are regex-**escaped**, so `release/v1.0` cannot corrupt the pattern.

`session-start-check.py` now imports `_hooklib` defensively: it carries the layer-4 sentinel, and
*"a plugin without this check is distributing a false sense of protection"* — it must survive the
shared lib failing to import. (Caught pre-commit: the naive edit would have made the sentinel
`NameError` on every session.)

12 new fixtures — `test_configurable_at_the_edges`, `test_missing_tool_says_so_once`. **135/135.**

### Layer 1 — the 3 `full-guide.md` monoliths deleted, and the drift they hid — *2026-07-15*
Closes the P2 backlog item. **6,777 lines** removed: `react-best-practices` (2934),
`react-native-best-practices` (2897), `composition-patterns` (946). All three were already
unreferenced, so this costs no context — it removes a drift source.

**The premise was wrong, and checking it found a live defect.** The backlog said the monoliths'
unique residue was section preambles that had to be migrated before deleting. They were not
unique: `rules/_sections.md` is the **canonical taxonomy** — it owns each section's impact level
and the filename prefix that groups its rules, and the monolith preambles were copies of its
descriptions. Nothing needed rescuing.

What *did* need fixing was found by diffing the bodies against that ground truth:
`react-native-best-practices` had **silently collapsed its 14 canonical sections into 8 invented
ones** — it dropped **Core Rendering (CRITICAL — "violations cause runtime crashes or broken
UI")** entirely and promoted List Performance into the vacant top slot, relabelled Monorepo
LOW→MEDIUM, and advertised "14 categories" in tier 1 while its table listed 8. The body is what
the model reads, so a wrong impact there mis-prioritises real work. `react-best-practices`,
`composition-patterns`, `atomic-design` and `terraform` were verified clean and left untouched.

- Bodies now carry the section **rationale** and the **rule prefix** (the load mechanism), all
  generated from `_sections.md` + the rule files on disk.
- `_sections.md` is **kept, not merged**. Ch. 7's merge signal argues for folding short
  always-relevant material into the body, but the placement test's last row decides it: this
  taxonomy *must hold whether or not anyone reads it* → that is **not context at all**, it is a
  gate. It stays as machine-checkable truth, and CI enforces the match.
- **`.github/scripts/check_rule_taxonomy.py`** (new) + CI step: every prefix claims ≥1 rule, every
  rule is claimed by exactly one section, and the body declares each section with the same impact.
  Runs locally with the same command CI uses.
- `test_rule_taxonomy_checker` proves the gate **fires** on all three real regression shapes
  rather than merely agreeing with today's tree (Ch. 9 — *a gate that has only ever passed is
  untested*). Harness **123/123**.

**Two near-misses worth recording.** A `(\w+)` impact pattern silently failed on hyphenated
levels (`MEDIUM-HIGH`), inventing two contradictions in `react-best-practices` that did not
exist — an assertion blocked the write, and the "fix" would have *downgraded correct labels*.
And the first gate enforced heading *numbering*, which would have failed `atomic-design` and
`terraform` for house style: 15 false positives on correct files. **Gate the invariant, not the
convention** — a gate that fires on legitimate variation trains people to ignore it.

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

### Layer 1 — "finish progressive disclosure (13 skills)" was mostly NOT a gap — *2026-07-15*
Audited the 13 single-file `std-*` skills against Ch. 7's **placement test** rather than assuming
"single-file = unfinished". Bodies measure **50–127 lines** — which *is* tier-2's target ("a page of
rules"). The 7 skills genuinely split earlier were 148–217.

Ch. 7's **merge signal** is explicit: *"it's short, and it applies to essentially every task the
skill triggers on. That's not a reference; that's a rule you moved out of the body for no reason,
and you've bought an extra file read for nothing."* Splitting `std-accessibility` (126, all
cross-cutting web a11y), `std-database` (121, all general DB rules), `std-monitoring` (67),
`std-error-handling` (50) etc. would therefore be an **antipattern**, not progress.

**12 of 13 are correctly sized — the item is closed as not-a-gap.** Recording the reasoning so a
later pass doesn't "complete" it and do harm.

**One real exception, found by the other signal:** `std-clean-architecture` (127 lines) is not
oversized, but it carries **four platform mappings** (Rails, React Native, Vite, Next.js) in tier 2,
and its `paths:` trigger on `**/app/**/*.rb` *and* `**/src/**/*.ts` — so a Rails task loads the
Next.js/RN/Vite mappings for nothing. That is Ch. 7's *second stack/platform* split signal ("an ECS
task should never load Kubernetes context"), and it is being split by platform.

### Layer 1 — reference sizing: the over-budget files split at the book's own signals — *2026-07-15*
Split at Ch. 7's two signals (never *by line count*): **sections never needed together**, and **a
second stack/platform** ("an ECS task should never load Kubernetes context").

| Skill | Before | After |
|---|---|---|
| std-infrastructure | terraform-aws **560** + cicd-and-deploys **492** (1052) | 7 files, max 287 — split Terraform-mechanics ↔ AWS-services, and CI/backend ↔ frontend deploys |
| std-api-design | errors-and-validation **457**, rate-limiting-and-health **380**, pagination **387** | 7 files, max 299 — split at the **Rails ↔ TypeScript** seam; rate-limiting ↔ health-checks |
| std-phlex-conventions | component-levels **430**, stimulus-and-turbo **375** | 6 files, max 313 — primitives ↔ composites; Stimulus ↔ Turbo |
| std-reactjs | forms-and-testing **399**, state-and-data **368** | 7 files, max 286 — forms ↔ testing; state-placement ↔ data-fetching |
| std-clean-architecture | body 127 carrying **4 platform mappings** | body 75 (hub) + 4 platform references — a Rails task no longer loads Next.js/RN/Vite context |

Content preserved in every case (verified file-by-file against HEAD).

**A real defect the adversarial verify caught** (`std-reactjs`, same class as iteration 4's terraform
contradictions): the split **added** a second copy of the `useOrders` hook and, worse, left **two
`orderKeys` factories both labelled `// src/api/orders.ts`** — one *with* `lists()`, one *without*,
while `data-fetching.md`'s invalidation calls `orderKeys.lists()`. A reader copying the
`state-placement` factory and following `data-fetching`'s invalidation gets
`orderKeys.lists is not a function`. The inconsistency pre-existed at HEAD but was *contained* in one
file; splitting turned it into a cross-file contradiction. Fixed: one factory (the `lists()` version
its invalidation depends on), owned by `data-fetching.md`, imported by the other.

### Layer 5 — governing the governors: the last thin layer — *2026-07-15*
I called the work "done" last pass. It wasn't: **layer 5 was the one layer still 🟠**, so the
seven-layer model was incomplete. Ch. 20: layer 5 is *"the layer teams reach for last and misuse
first"*, and its discipline is **enforce the intolerable, permit the rest**.

Audited `managed-settings.template.json` against the book's **four legitimate uses** and found real
defects, not just thinness:
1. **Its deny floor was STALE** — missing the terraform denies added in iteration 6. The org
   template had the *same staleness bug we built the sentinel to catch in consumers*.
2. `companyAnnouncements` pointed at **`.claude/rules/security.md`** — a path deleted in the plugin
   conversion.
3. **No audit-trail requirement** — the book's 4th legitimate use was absent.

Rebuilt around the four uses, each with its reasoning inline: forced auth · a non-overridable
security floor · MCP allowlist (supply-chain vetting made mandatory — *an MCP tool description is a
prompt the model obeys*) · required audit trail (with the plugin **pinned**, not floating).

**The structural insight — layer 5 is the org-scale answer to the plugin trap.** A plugin cannot
ship `permissions`, so every project must copy the floor and the sentinel exists to catch those that
didn't. Deployed at layer 5 the floor simply *exists everywhere*, non-overridably: no copying, no
drift, no sentinel needed. The sentinel remains the net for teams without managed settings.

**Calibrated against maximalism, deliberately:**
- The managed floor is the **catastrophic tier only** (secrets, privilege, remote-exec, irreversible
  infra). The build-artifact denies are **context economy, not security** — putting them in
  non-overridable policy blocks nothing dangerous and annoys everyone.
- `allowManagedPermissionRulesOnly` and `allowManagedHooksOnly` stay **false**: the deny list is a
  *floor*, not a *ceiling*. Teams must stay free to add a project-specific rule. *"An org policy that
  treats every engineer as an adversary loses them to shadow tooling — the worst outcome, since
  shadow tooling has NO layers."*

`docs/org-policy.md` — the four uses, an explicit **what does NOT belong at layer 5** table, and the
maximalism warning first, because that is the failure mode.

**CI guard `managed-floor-sync`**: the managed floor must contain every catastrophic deny from the
reference floor (it went stale once — it can't again), *and* must NOT contain context-economy denies
(guarding against overreach in both directions). Verified by simulating the exact staleness: it
caught all 6 missing terraform rules.

### Best-practices coverage — per skill / per agent

Standing mandate (loop): extend each skill/agent with best practices **where they genuinely
apply**, grounded in the stack this repo actually pins (CLAUDE.md), not generic advice. A few
per iteration — never all at once. Ch. 7 decides placement: applies to every task → body;
deep + decision-shaped + example-paired → `references/<topic>.md`; must hold whether or not it
is read → **not context at all**, so make it a hook, a permission, or a CI gate.

**`skip` is a first-class outcome and is final** — record the reason and never re-litigate
it. Padding a skill to look complete buys an extra file read for nothing (Ch. 7).

Legend: `todo` not yet passed · `done` passed (dated) · `skip` deliberately none (reason)

#### Convention skills (`std-*`) — 20

| Skill | Tier state | BP pass |
|---|---|---|
| `std-accessibility` | single-file | todo |
| `std-agent-teams` | single-file | todo |
| `std-api-design` | 3-tier (7 refs) | todo |
| `std-clean-architecture` | 3-tier (4 refs) | todo |
| `std-code-standards` | single-file | done *2026-07-15* — limits reconciled with the hook + gated |
| `std-database` | 3-tier (1 ref) | done *2026-07-15* — restacked to ActiveRecord + lock timeouts |
| `std-design-system` | 3-tier (4 refs) | todo |
| `std-error-handling` | 3-tier (1 ref) | done *2026-07-15* — Sidekiq's real retry semantics |
| `std-git-workflow` | single-file | done *2026-07-15* — commit types reconciled with the hook + gated |
| `std-i18n` | single-file | todo |
| `std-infrastructure` | 3-tier (10 refs) | done *2026-07-15* — GH Actions supply chain + GCP WIF |
| `std-monitoring` | 3-tier (1 ref) | done *2026-07-15* — where request_id actually comes from |
| `std-nextjs` | 3-tier (4 refs) | done *2026-07-15* — version target pinned; content verified current |
| `std-phlex-conventions` | 3-tier (6 refs) | todo |
| `std-rails-conventions` | 3-tier (1 ref) | done *2026-07-15* — authorization enforcement |
| `std-react-native` | 3-tier (2 refs) | done *2026-07-15* — offline mutations + Centrifugo |
| `std-reactjs` | 3-tier (7 refs) | todo |
| `std-security` | single-file | done *2026-07-15* — access-control rules + Rails pointer |
| `std-terraform-conventions` | single-file | todo |
| `std-testing` | 3-tier (4 refs) | todo |

#### Workflow skills — 44

| Skill | Tier state | BP pass |
|---|---|---|
| `accessibility-auditor` | 3-tier (2 refs) | todo |
| `api-designer` | 3-tier (1 refs) | todo |
| `architecture-advisor` | single-file | todo |
| `atomic-design` | rule-per-file (10) | todo |
| `brand-identity` | 3-tier (2 refs) | todo |
| `clean-architecture` | 3-tier (1 refs) | todo |
| `code-reviewer` | 3-tier (2 refs) | todo |
| `compliance-auditor` | single-file | todo |
| `composition-patterns` | rule-per-file (8) | todo |
| `db-migration` | 3-tier (2 refs) | todo |
| `deploy` | single-file | todo |
| `design-critique` | single-file | todo |
| `design-to-code` | 3-tier (1 refs) | todo |
| `doc-generator` | 3-tier (1 refs) | todo |
| `figma-handoff` | 3-tier (2 refs) | todo |
| `i18n` | single-file | todo |
| `incident-response` | 3-tier (1 refs) | todo |
| `log-search` | 3-tier (2 refs) | done *2026-07-15* — shipped as a BP skill |
| `mcp-advisor` | 3-tier (2 refs) | done *2026-07-15* — shipped as a BP skill |
| `toolchain` | 3-tier (2 refs) | done *2026-07-15* — shipped as a BP skill |
| `marketing-assets` | 3-tier (1 refs) | todo |
| `monorepo-architect` | 3-tier (6 refs) | done *2026-07-15* — shipped as a BP skill |
| `mobile-beta-release` | 3-tier (3 refs) | done *2026-07-15* — shipped as a BP skill |
| `mobile-signing` | 3-tier (3 refs) | done *2026-07-15* — shipped as a BP skill |
| `nextjs-dev` | 3-tier (3 refs) | todo |
| `onboarding` | 3-tier (1 refs) | todo |
| `performance-profiler` | 3-tier (1 refs) | todo |
| `phlex-dev` | 3-tier (2 refs) | todo |
| `rails-architect` | 3-tier (1 refs) | todo |
| `react-best-practices` | rule-per-file (57) | todo |
| `react-native-best-practices` | rule-per-file (36) | todo |
| `react-native-dev` | 3-tier (1 refs) | todo |
| `reactjs-dev` | 3-tier (3 refs) | todo |
| `refactor` | single-file | todo |
| `requirements-consultant` | single-file | todo |
| `sdh-engineering-standards` | single-file | todo |
| `security-auditor` | 3-tier (1 refs) | todo |
| `sprint-planner` | single-file | todo |
| `technical-rfc` | 3-tier (1 refs) | todo |
| `terraform` | rule-per-file (47) | todo |
| `test-generator` | 3-tier (1 refs) | todo |
| `theming` | 3-tier (3 refs) | todo |
| `ui-ux-patterns` | 3-tier (3 refs) | todo |
| `web-design-guidelines` | single-file | todo |

#### Agents — 13

| Agent | BP pass |
|---|---|
| `architecture-advisor` | todo |
| `clean-architecture` | todo |
| `code-reviewer` | todo |
| `design-critique` | todo |
| `design-system-architect` | todo |
| `devops-engineer` | todo |
| `incident-responder` | todo |
| `monorepo-architect` | done *2026-07-15* — shipped with the skill |
| `phlex-developer` | todo |
| `refactor-specialist` | todo |
| `requirements-consultant` | todo |
| `security-auditor` | todo |
| `test-generator` | todo |

---
## OPEN — prioritized backlog

### P3 · Layer 1 — the repo has not decided ActiveJob vs `Sidekiq::Job`
5 files use `< ApplicationJob`, 3 use `include Sidekiq::Job`; CLAUDE.md commits to Sidekiq but
not to an API. The two differ in retry semantics (`retry_on` **stacks** on Sidekiq's retries),
overhead (*"about 30% overhead"*), and argument serialization (GlobalID re-queries a row that may
have changed between enqueue and run). `std-error-handling/references/background-jobs.md`
documents the tradeoff and recommends native; the decision belongs in CLAUDE.md and converting
the existing examples is a mechanical follow-up — **maintainer's call, not the loop's.**

### P3 · Layer 1 — sizing residue (6 files)
Two have a genuine Ch. 7 **split signal** (sections never needed together), which is the real
reason to split — not the line count:
- `code-reviewer/references/pr-review-guide.md` **325** (+8%) — mixes Rails, React Native,
  security and the generic checklist. A Rails review never needs the RN red flags. Peel by stack.
- `std-nextjs/rendering.md` **386** — streaming/Suspense is the natural peel.

`std-nextjs/server-actions.md` **340** is genuinely over with no obvious seam. The remaining
three are within tolerance and **not worth churning**: `variants-and-styling.md` 313 (+4%),
`middleware-seo-deploy.md` 309, `cross-platform-parity.md` 302. Per the *deliberate
non-decisions* below, this is a guideline, not a gate — do not shred files to hit a round number.

---

## Correlated failure modes to watch (Ch. 20)

- **Plugin trap correlates 3+4** — now guarded by the sentinel. ✅
- **Widening an agent's tools correlates 2+3** — Bash reconstitutes a removed capability and
  routes around `Edit|Write` guards.
- **Human fatigue correlates 6+7** — if the same tired person clicks `ask` and approves the PR,
  that is one layer, not two.
- **Shared assumptions correlate everything** — every layer here assumes failures are *accidents*.
  Against prompt injection (Ch. 32), layers 1–2 fall together; only 3, 4, 6, 7 hold.

---

## Deliberate non-decisions

**No hard CI gate on reference line count.** The ~300-line budget is a *guideline* ("a few hundred
lines"), and Ch. 20 is pointed about the inverse error: *"over-governing the trivial. A hard deny on
a style choice that belongs in a skill teaches your team that the governance system is an obstacle,
and a team that experiences governance as obstruction disables it."* Sizing is a quality guideline,
not a catastrophic rule — *"the trivial rules get one layer; the catastrophic rules get several."*
It stays in this audit and in review, not in a build-breaking gate.

**No force-splitting of correctly-sized skills.** See the merge-signal finding above.
