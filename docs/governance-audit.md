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

### Ch22 — auditing this loop's own output, deliberately — *2026-07-15*

Last iteration found that **this loop had produced three defects of the class it audits for**, each
surfaced by accident while looking at something else. That is a measurable defect rate in my own
work, so this pass audited the branch itself rather than the next skill: **91 files, 5,834
insertions.** It found two more.

**4th self-inflicted defect — a gate claim narrower than the sentence around it.** I wrote in
`i18n/SKILL.md` (commit `f80c64a`): *"No user-facing literal in a component, view, or **serializer**.
`i18n-checker.py` warns on this."* But `i18n-checker.py` is
`ALLOWED_EXTENSIONS = (".tsx", ".jsx", ".erb")` — **a Panko serializer is `.rb` and is never
inspected.** The rule names three things; the hook covers two. A developer puts a literal in a
serializer, gets no warning, and concludes they are fine — and that is the copy that reaches the API
consumer rather than the page. Now states exactly where the gate ends.

**5th — I asserted a number after saying I would not.** Fixing the bundle-budget units, I told the
user *"I won't assert a conversion ratio I can't verify"* — then wrote *"differ by roughly 3-4x"*
into **three** files as bare fact. The rule of thumb is not fabricated, but it varies with bundle
content, and **it was not load-bearing**: the argument is that gzipped and uncompressed are
*different measures*, which is stronger without a number. Removed from all three; the point now
rests on *"converting between them needs that bundle's real compression ratio"* and *"the Vite build
output prints both."*

**A new finding in an already-passed skill.** `performance-benchmarks.md` has a **"Backend
(Node.js)"** table (heap, RSS, worker count, GC pause) — and this stack's backend is **Rails**, with
its own table directly below. Not wrong, **mis-titled**: the only long-running Node process here is
**Next.js self-hosted on ECS** (`output: 'standalone'` — the documented alternative in
`frontend-deploys.md`). On **Vercel**, the primary target, those numbers mean nothing — *you do not
tune an RSS ceiling on a serverless function, and reading them as budgets there sends you hunting
for a knob that does not exist.* Retitled and scoped. Worth noting the skill was already marked
done: **a pass is not a proof.**

**What checked out**, recorded so a later iteration does not re-litigate it: every API claim I added
traces to a verified owner (`contrastRatio()` → `defining-tokens.md:218`; `newSubscription()`/
`getSubscription()` → `realtime-centrifugo.md`, and gated; `JTIMatcher` → `authorization.md`;
`Sidekiq::Job` → `background-jobs.md`). Every hook claim I added is true of the hook as it stands —
including `terraform-command-gate.py` *"is a three-tier gate"* (its docstring: *"three-tier command
gate… Ch. 10 Pattern 3"*).

**The pattern in my own defects is consistent and worth naming:** all five are *scope* errors, not
fabrications — a gate that covers less than the sentence claims, a test scoped to one file, a stale
claim about a hook I myself changed, an unverified package manager, a ratio stated without its
variance. **Not "I made something up" but "I claimed more coverage than I had"** — which is exactly
the defect this sweep keeps finding in the plugin. The lens works on its author.

### Layer 3 — the plugin's own description of its hooks was wrong in three places — *2026-07-15*

`log-search` and `toolchain` were the target; the lens was *"does the skill agree with the repo's
own CI"* rather than freshness. It found something better, including **two defects I caused**.

**CLAUDE.md described three hooks as things they are not.** This is the plugin's own map of its
governance — someone asking *"what runs on every `.tsx` edit?"* got three wrong answers:

| CLAUDE.md said | Reality |
|---|---|
| *"Accessibility **agent** hook — **Haiku agent** with Read/Grep/Glob"* | `accessibility-checker.py`'s own docstring: *"deterministic command hook"* |
| *"API design **agent** hook — **Haiku agent**"* | `api-design-checker.py`: *"deterministic command hook"* |
| *"Monitoring **prompt** — request_id in logs, sensitive data"* | A command hook, and **the request_id check was removed** (by this loop, correctly) |

The Haiku claim is not cosmetic: it tells a reader that every `.tsx` edit spawns a model, with the
cost and latency that implies. It spawns nothing. Corrected against the code, including two scope
errors the prose had drifted past (`accessibility-checker` also covers `.css`/`.scss` — which
matters, because `outline: none` is a CSS declaration).

**A stale claim I created.** `std-monitoring/references/request-tracing.md:16` still said
*"`monitoring-checker.py` **warns when it doesn't**"* include `request_id` — after this loop removed
that check early on. The removal was right (the id is injected by `config.log_tags`, so it is not in
the source line; every correct app tripped it). Updating the file that *depends on* the claim was
missed. It now states the opposite, with the reason: **the id's presence is your configuration's
job, not a gate's** — which is precisely why that reference has to be right.

**A defect I introduced, found by my own lens.** `toolchain`'s headline rule is *"CI and your laptop
must run the same commands"* — and its own example block mixed **`pnpm exec`** and **`npx`** on
adjacent lines (two different managers' runners), while `ci-pipeline.md` runs **npm** throughout
(`npm ci`, `npx tsc`, `npm audit`). **CLAUDE.md pins no package manager.** I had then written
`pnpm vitest run` / `pnpm jest` into `refactor-specialist` this sweep — asserting a manager the repo
does not pin, and contradicting CI. (Tellingly, `test-generator`, which I also wrote, names the
*library* with no runner prefix. I was inconsistent with myself.)

Fixed without deciding the maintainer's question: **the lockfile tells you the runner** —
`package-lock.json` → `npx`, `pnpm-lock.yaml` → `pnpm exec`, `yarn.lock` → `yarn`. That is
deterministic, checkable, and requires no pin. *"If the lockfile and CI disagree, that is the
finding"* — say so rather than picking a side. `refactor-specialist` now says run the
`package.json` script, so you run what CI runs rather than a command you composed.

**`log-search` needed nothing** and that is recorded rather than padded: it agrees with
`std-monitoring` on `request_id`, states its precondition honestly (*"This file assumes those
exist"* / *"When it is missing, that is the finding"*), and already points at the owner.

**A gate was measured and rejected.** All 22 hooks named in docs exist on disk — so a
"named hook exists" check finds nothing, **and would pass while the real defect persists**: the
failures here were hooks that exist but do not do what the doc says. That is the
*partial-coverage-looks-like-coverage* pattern this sweep keeps finding, and shipping it would have
been committing it.

### BP pass — the mobile skills: one already right, one dated nothing — *2026-07-15*

**`mobile-signing` avoids the freshness trap by construction, and that deserves recording rather
than "improving".** It says *"Apple distribution certificate → **expires**; rebuild/reissue before
it does"* and *"put the dates in a calendar the team reads"* — it never asserts a **period**. The
actionable advice does not depend on a number that can move, so there is nothing to go stale. Its
irreversibility table is mechanism, not policy: *Play App Signing converts the only unrecoverable
failure into a recoverable one*; `.p8` downloads exactly once; the upload key is not the app signing
key. None of that expires. **Nothing to add that would not be padding.**

**What it did need was one reconciliation.** `std-infrastructure` says *"Prefer no credential at
all. CI authenticates by **federation, not keys** — OIDC to AWS"* and *"no long-lived AWS keys in
CI"* — while this skill's entire subject is long-lived secrets in CI (`.p8`, keystore,
service-account JSON). **That is a real exception, not an oversight**, and knowing which matters:
Apple's App Store Connect API key *is* a `.p8` private key and there is no OIDC path to App Store
Connect to prefer instead. So the rule cannot be satisfied and the mitigation moves to what can be
controlled — least privilege, rotation, never echoing, ephemeral keychains — and *"time spent
hunting for the OIDC option on the Apple side is time not spent rotating the key you actually
have."* Stated conservatively: if a federated path exists for a given provider, prefer it, but
confirm at that provider's docs rather than assuming the AWS answer transfers.

**`mobile-beta-release` is where the volatile numbers live** — 100 internal, 10,000 external, 90-day
expiry — and **nothing dates them.** `testflight.md` quotes Apple *verbatim*, which makes them
**sourced but not dated**, and that is a subtler trap than `platform-specs.md`'s: a quote reads as
*more* authoritative while being equally uncheckable, and it is exactly as confident the day it goes
stale as the day it was right. These numbers have moved before (external 2,000 → 10,000; internal
25 → 100).

No numbers changed — unverifiable from here, and asserting a fix would be the defect. What was added
is the **split between what expires and what does not**, which keeps the skill's value intact rather
than blanket-warning over it:
- *Stable*: internal is fast / external is reviewed; a TestFlight build has a finite life and a Play
  build does not; build numbers increase forever.
- *Expires*: the ceilings, the 90-day window, review turnaround, track names.

Check them in **App Store Connect** and the **Play Console** — the consoles show your app's real
limits, which beat any doc. And *"the planning advice survives either way"*: **use internal for the
tight loop, reserve external for the wider round** holds whether the ceiling is 10,000 or 25,000.

**A file could not be read** (`ci-signing-secrets.md`, permission denied), so no claim is made about
whether it reconciles the OIDC tension internally — the note went in the body, which was readable.
Asserting a deficiency in a file I could not open would have been this sweep's own recurring defect.

### BP pass — the fixed conversion rate, and the specs with no expiry — *2026-07-15*

**`sprint-planner` contradicted itself on the same screen.** Its Story Point Reference mapped points
to **duration** (`1` = *< 2 hours*, `5` = *1-2 days*, `13` = *3-5 days*) — eleven lines above the
first estimation guideline: ***"Compare, don't calculate."***

Two reasons the duration column had to go, and the second is the one that bites:
1. **A 5 is "1-2 days" for whom?** Seniors on a familiar codebase and a team onboarding deliver
   different hours for the same relative size. That is not noise to correct — it is why points exist
   instead of hours.
2. **It made velocity circular.** The skill measures velocity (Step 1, and a *Velocity Tracking*
   section) precisely to **discover** what a point is worth for *this* team, empirically. If the
   table already declares a 5 is 1-2 days, velocity can only measure how wrong the table is. You
   cannot fix a conversion rate a priori **and** claim to be measuring it.

This is the sweep's recurring shape with the polarity flipped: usually an assertion stands where a
measurement is *absent*; here the measurement **existed** and the assertion pre-empted it.

**The repo's own position corroborates the fix** — checked rather than asserted:
`technical-rfc:114` already says *"Estimate effort in **developer-days (not story points)**"*, and
`doc-generator/process-docs.md` treats velocity as committed/completed points. Both correct.
`sprint-planner` was the only place conflating the two tools. The table keeps its **examples as
anchors** (the genuinely useful part) and drops the conversion; estimation is explicitly the team's,
because *"an estimate produced by reading a ticket is a guess wearing a Fibonacci number."*

**`marketing-assets` ships the most volatile facts in the plugin with no expiry date.** Google 30/90,
Meta 125/40, TikTok 100, LinkedIn 150/70 — and `platform-specs.md` opened by calling itself
***"Complete"***, undated and unsourced. "Complete" belongs to the same word-class as the
*"Verified"* contrast table and the *"contrast-verified"* tokens: **a property nobody checked.**

Deliberately **no new factual claims** — the numbers were not corrected, because they cannot be
verified from here and asserting a fix would be the exact defect. What changed is the epistemic
frame: it is a **cached copy, not the source of truth**; it is undated *by construction* (nothing
here was ever checked against a platform); verify anything a campaign depends on, because a stale
limit is a truncated headline in production or an upload rejected on launch day; **do not extend the
table from memory** (asked about Pinterest you will produce a plausible unsourced number
indistinguishable from the rows above it); and *recommended* ≠ *maximum* — a table cell hides which,
and Meta's truncation point is not the uploader's hard cap.

**No gate for either.** Measured first: `sprint-planner` was the only points→time mapping, and
platform-spec freshness is not decidable without the network. Both are judgement, and the sweep's
line holds — gate the data a hook enforces; write down the judgement calls.

### Layer 2+6 — the skill that signed Claude as the Auditor — *2026-07-15*

The highest-consequence instance of the pattern this sweep keeps finding — *an assertion where a
computation or an authority belongs*. `compliance-auditor`'s output template:

```
# Compliance Audit Report — [Framework]
**Date**: YYYY-MM-DD | **Auditor**: Claude | **Scope**: [System/Component]
```

…with a quotable **Compliant** count and an *"overall compliance posture"*. **And no epistemic
limit anywhere in 212 lines** — no "not an audit", no "not legal advice", no counsel. Measured:
`security-auditor` has a capability boundary, `incident-responder` an authority boundary,
`requirements-consultant` an epistemic one. The skill producing **regulatory** documents had none,
and it was the **only** one in the repo signing Claude as an authority.

**Why it matters more than the wording.** A SOC 2 attestation is issued by a licensed CPA firm; a
PCI-DSS assessment by a QSA. That document is what gets forwarded — into a vendor questionnaire, a
customer security review, a board deck — and it reads as an attestation. The counts make it
quotable ("47 Compliant / 3 Non-Compliant") long after the context is gone.

**The decisive detail is in the skill's own control list.** It says "For each applicable control,
verify implementation in **code and infrastructure**… Mark each control as: **Compliant**" — while
SOC 2 CC1's controls are *"Background checks for personnel"*, *"Security awareness training program
in place"*, and CC3's is *"Annual risk assessment conducted"*. **None of those exist in a
repository.** The skill asked for a determination about an organization from an agent that can see
one repo, which forces a choice between inventing a pass and inventing a gap.

Fixed by changing what is claimed rather than by disclaiming it:
- **Evidence, not compliance.** *Evidence found* / *Partial* / *No evidence found* / **No evidence
  in scope** / *N/A*. "Evidence found at `file:line`" is an observation; "Compliant" is a
  determination — and they look identical in a table cell.
- **"No evidence in scope" is not a gap.** The org may do background checks perfectly; a repo read
  cannot see them, and marking them Non-Compliant manufactures a false gap that costs someone a week.
- **SOC 2 Type II is operating effectiveness over 3-12 months.** A repository read is one instant:
  it can show a control *exists*, never that it *operated*. The skill named "Type I & Type II" and
  never drew the distinction.
- **Third-party certifications are not recalled.** "AWS is SOC 2 certified" from memory is training
  data with no date or scope — cite the trust portal or record an open item.
- Retitled a **readiness self-assessment**, *prepared by* (unverified) with a **required named
  reviewer**, and "overall compliance posture" removed: the largest risks are routinely in the
  controls this review cannot see.

**No gate.** Measured first: `compliance-auditor` was the only skill signing as an authority, and
the class — *an output template that attests to what the agent cannot determine* — is judgement,
not a mechanical invariant. The other auditors correctly present "findings".

### Layer 1 — the recipe that generated the failing presets — *2026-07-15*

Traced the 13 failing preset pairs to their **source**. `brand-identity` is the generator, and its
recipe (`references/color-theory.md`) prescribed semantic-colour lightness *ranges* with **no
foreground named**:

```
Success: HSL(142, 70-76%, 36-45%)
Error:   HSL(0, 62-84%, 30-60%)
Info:    HSL(199, 80-95%, 46-54%)
```

…then, one step later: *"Create foreground pairs meeting WCAG 4.5:1 contrast."*

**Measured against the usual near-white `*-foreground`, the entire Success range and the entire
Info range fail** — best case **3.40:1** and **3.12:1**. Steps 1-5 made step 6 unsatisfiable. The
presets were built from this recipe and inherited its arithmetic: `--success: 36.3%` is the
prescribed range's *floor*. **The recipe was the bug; fixing the presets without fixing it would
just regenerate them.**

The ranges are now **foreground-aware caps**, which is the missing concept — a lightness range means
nothing until you say what sits on it. Success ≤ 29%, Error ≤ 48%, Info ≤ 35%. **Warning is the
proof the old table was malformed**: amber takes a *dark* foreground (no lightness in the usable
amber range clears 4.5:1 against white), so quoting it beside three white-foreground ranges was
comparing different things.

Two further defects in the same recipe:
- *"Output all colors… meeting WCAG AA"* asked the model for a property **it cannot compute by
  inspection** — a gamma-corrected luminance ratio. It now must emit the **measured ratio beside
  each pair**, which is what makes the claim falsifiable.
- *"Generate dark mode by **inverting lightness**"* is a plausible-looking rule that produces
  failures: flipping `success 36% → 64%` yields a light green that now needs a *dark* foreground, so
  the pair changes character rather than its numbers. The dark halves of all three presets failed on
  exactly this. Dark mode is a separate set of pairs, measured independently.

**The gate caught an error in my own caps — and that is the point of it.** I derived them with
`min(caps)` formatted `:.0f`, which **rounds to nearest**: 29.7 → "30". A cap must be **floored**.
At 76% saturation, `L=30%` measures **4.43:1** (fails) and `L=29%` measures 4.69:1. One percent,
and the gate refused it before it shipped. The published caps are now set by the **most saturated**
end of each range — higher saturation needs lower lightness — and floored.

**`figma-handoff`** feeds the same registry from the other side. Its risk is structural rather than
live (its examples map to `--primary`/`--secondary`, both registered): a Figma file names styles for
designers (`Brand/Green/500`), and transliterating them mints `--brand-green-500`, which compiles to
**no CSS at all**. It now maps onto the registry, treats an unmatched style as a **finding rather
than a naming exercise**, and states that a designer's fill is a brand decision, not a contrast
measurement — verified: `#10B981` on white is **2.54:1**.

### BP pass — `web-design-guidelines`: the 100+ rules that were never in the plugin — *2026-07-15*

Went looking for "partial coverage that looks like coverage" in a 100+-rule skill and found
something else: **the plugin ships none of them.** 81 lines, no `rules/`, no `references/` — it
fetches the rule set *and its output format* at run time from a third-party `main` branch.

CLAUDE.md, the README (twice) and the skill's own description all advertised **"100+
accessibility/UX rules"**. The plugin contains a URL. Fixed in all four places.

**Two of the repo's own rules, contradicted at once** — which is what makes this a finding rather
than a preference:
- `std-infrastructure`: *"Pin every version. `latest` is never allowed in a committed file."* The
  URL targets `main`; the skill said *"Fetch the latest"* / *"Fetch fresh guidelines before each
  review."*
- `mcp-install-gate.py` exists so **a human picks an instruction source**. This fetches
  instructions, from a third party, ungated, every run — a wider hole than the one the plugin built
  a gate for, one directory over. Measured: it is the **only** skill doing this.

**The live hazard was the missing fail-closed clause**, not the pin. *"Apply all rules from the
fetched guidelines"* with no fallback means that when `WebFetch` is denied, offline, or the repo
moves, the model has a skill saying "review for compliance", no rules, and a great deal of
training-data knowledge about web guidelines. It produces plausible findings in a terse `file:line`
format and the reader assumes they came from the source. **That is `requirements-consultant`'s
Phase 0 in a different costume** — and worse, because the format looks authoritative. It now must
say the fetch failed, fall back to the **pinned local** skills (`std-accessibility` auto-loads and
is already in context; the WCAG checklist and ARIA patterns are on disk), defer to house
conventions where upstream disagrees, and **name the source of every finding** — "upstream
guideline" and "house convention" are different claims and a `file:line` hides which.

**A gate was written, verified, and withheld.** A detector for committed floating raw URLs matches
**exactly one** file and correctly ignores the repo's 8 ordinary `github.com` doc links. It is not
shipped because the skill's *purpose* is the thing the rule forbids — pinning to a SHA makes it
reproducible **and stale**, defeating "latest guidelines". Pin / vendor / float-consciously is a
maintainer's decision (P2, with the detector ready to ship alongside it). A gate that fails on a
finding only the maintainer can resolve leaves the suite red, and that is how gates become noise.

### BP pass — the three React rules-skills, and the version nobody pinned — *2026-07-15*

`react-best-practices` (57 rules), `react-native-best-practices` (36), `composition-patterns` — all
three named **no owner**, and two named **no React version**, while their `std-*` counterparts
auto-load on the same files.

**The rules themselves are in better shape than expected, and that is worth recording** — I went
looking for React 18 rot and did not find it: **no `forwardRef`**, **no `useFormState`**, and
`rerender-memo` already carries the caveat that *React Compiler makes manual `memo()`/`useMemo()`
unnecessary*. The rules are 19-aware. Only the anchor was missing.

**The real finding is that React is pinned for one of three React platforms** — `std-nextjs` says
"React 19 minimum"; the Vite SPA and React Native say nothing. Recorded as a P3 (maintainer's call,
like ActiveJob): inventing a pin would be this loop deciding version policy for a stack it does not
own, and **RN's React lags web**, so the Next.js answer does not transfer. All three skills now say
*read `package.json` before applying a version-specific rule*, and `react-best-practices` carries
the honest table — 19 for Next, *not pinned* for the other two.

**A second axis nobody states:** `rerender-memo`'s Compiler caveat turns on whether the **build**
enables the Compiler, not on a React version. A rule that is right or wrong depending on a babel
plugin needs to say so.

**Wiring, with the reason each pointer earns its place** rather than a list: `std-reactjs` owns
*what state goes where* (a compound component whose context holds server data has invented a second
cache); `std-nextjs` owns the Server/Client boundary (*context requires a Client Component, so
reaching for a provider is a rendering decision before it is a composition one*); RN testing is
Jest, not Vitest.

**A gate was considered and declined**, for the third time in this sweep and for the same reason:
"every `React \d+` equals the pinned major" flags **correct prose** — `react19-no-forwardref` says
"React 18" legitimately, explaining what changed. Measured: 2 of 21 occurrences are that shape. The
correction contains the words the gate looks for.

### BP pass — why the auditor never caught the presets — *2026-07-15*

Follow-up to the 13 failing preset pairs: **why did the plugin's own `accessibility-auditor` not
find them?** Because it lists contrast under *"Chrome DevTools · Contrast checker · **Manual**"*.

**Token contrast is arithmetic on two static HSL values in a file.** It does not need a browser —
finding all 13 took a 20-line script. Nobody opens DevTools 36 times, so the failure survived not
because it was subtle but because **checking it by hand does not scale and therefore does not
happen**. The auditor now carries the iterating test (`describe.each` over themes × `it.each` over
pairs) and marks it *not manual*, with the two traps a page-level pass misses: a `-foreground`
token is verified against its **solid** surface (so it says nothing about `bg-success/10`), and
**presets are copies** — every theme is its own case.

**The mechanism already existed and nothing pointed at it.** `std-design-system/references/defining-tokens.md`
has a working `contrastRatio()` and Vitest wiring. But it hand-writes **two** `it()` cases
(`foreground`/`background`, `brand`) — partial coverage, which is the same shape as the failure
itself.

**A coverage edge worth naming:** `std-accessibility` owns "color contrast" and its `paths:` are
`.tsx`/`.jsx` **only** — it does **not** auto-load on `globals.css` or a token file. Contrast gets
decided where tokens are *defined*, which is `std-design-system`'s territory (`**/globals.css`,
`**/styles/**`, `**/tailwind.config.*`). Neither is wrong; auditing a colour system means opening
both, and now the auditor says so.

**A contradiction found — in the advice, against the artifact.** `defining-tokens.md` said the fix
for a low-contrast surface is *"**always** to darken the foreground, not to brighten the surface —
the surface color is the brand decision."* But `design-tokens.md`'s canonical defaults and all three
presets were repaired by darkening the **surface**. Checked before rewriting: **`--primary` was
never touched in any of them** — every adjustment was `success`/`error`/`info`, i.e. **semantic
status** tokens. So the rule is real but the "always" is overreach, and it now splits by what the
token *is*: darken the **foreground** for a brand token (you do not restyle the logo to pass a
checker); darken the **surface** for a semantic one ("green means success" is the convention,
*which* green is not — Tailwind ships `green-700` for exactly this). Left absolute, it told you to
do the opposite of what this repo's own shipped tokens do.

**`atomic-design`** needed a pointer, not a section: it owns the **hierarchy**, and its
`atom-theming-tokens.md` rule already cites the registry (fixed in an earlier pass). Added the
owner note — `std-design-system` auto-loads on the same files — and the distinction that matters:
*"uses a token" and "uses a registered token" are different claims, and only the second renders.*

### Layer 1 — the fix that never propagated: 13 preset pairs still below AA — *2026-07-15*

**The most consequential finding of the sweep, and it was this loop's own miss.** An earlier
iteration fixed `design-tokens.md`'s failing contrast tokens (`--success` 36.3% → 28%, `--error`
60.2% → 47%, …) and gated them with `test_contrast_table_matches_the_tokens`. **That test only ever
read `design-tokens.md`.** `theme-presets.md` carried the same defaults, copied — and still had
them.

Measured, not suspected: **13 pairs below WCAG AA across all 6 preset blocks** (3 presets ×
light/dark). Worst offenders `--success` at **2.54:1** (Modern) and `--info` at **2.99:1**
(Corporate dark) — against a 4.5:1 requirement.

**A preset is worse than a spec.** `theme-presets.md` says outright: *"Copy the relevant `:root`
and `.dark` blocks into your project's token stylesheet."* It exists to be taken wholesale. So a
team picks Modern, ships it, and this plugin's **own `accessibility-auditor` fails the result** —
the same shape as the original "Verified" table that was never computed.

All 13 solved by minimal lightness shifts; **36 pairs across 6 blocks now clear AA, worst 4.55:1.**

**Two lessons, both about the gate rather than the tokens:**

1. **A check scoped to one file proves nothing about the copy beside it.** The right scope is the
   *invariant* — "no shipped token pair is below AA" — not the file you happened to be fixing.
   That is now the scope.
2. **Corporate was not a preset — it was the spec under another name.** It shares
   `design-tokens.md`'s hue and saturation on every token, so my solver's minimal fixes (28.6%,
   48.6%, 45.5%) would have left *one token with two values* — recreating the drift class this
   sweep keeps finding, in the act of fixing it. Corporate now carries the canonical numbers
   verbatim, and a second check pins that agreement. It fires on a **1% divergence that still
   passes AA**, deliberately: it catches drift *before* it becomes a contrast failure. Modern and
   Minimal are genuinely different palettes and are not compared.

### BP pass — `terraform`: the tag list three sources state and nothing gated — *2026-07-15*

First skill past the user-skill ↔ `std-*` duplication surface, which is now exhausted. `terraform`
is **rules-shaped** (47 rules across 9 categories + 2 references), so it needed a different lens:
not "does the body duplicate a reference" but **"is the hook-enforced data consistent with the
prose that documents it."**

**`terraform-checker.py` enforces `REQUIRED_TAGS = ["project", "environment", "team",
"managed-by"]`.** That list is also stated by `std-terraform-conventions` (which **auto-loads on
every `**/*.tf`**) and by `terraform/rules/resource-required-tags.md`. Three sources, agreeing
today, **ungated**.

Gated now, and the justification is the distinguishing one: **a hook enforces it.** Last iteration
a third number-gate was *declined* for Sidekiq's retry default — 17 restatements, no drift, and
the anchor was upstream docs, so a gate would have added surface for a defect that does not exist.
The tag list is different in kind: add a fifth tag to the hook alone and the developer reads the
skill, writes the four it documents, is warned anyway, and concludes the hook is noise. That is not
hypothetical — it is precisely what `code-quality-checker`'s 200-line limit did, which is why
`test_limits_match_the_skill_that_documents_them` exists. This is that test's sibling, importing
the list from the hook rather than restating it. Verified to fail on a hook-only fifth tag, in
**both** skills.

**Two overlaps checked and found clean** — recorded, because a checked-and-clean overlap is a
result and stops a later iteration re-litigating it:
- `terraform/references/repository-layout.md` and
  `std-infrastructure/references/terraform-mechanics.md` answer the **same two questions** (where a
  `.tf` file goes; where tags come from). They **agree** — `default_tags` on the provider, same four
  tags — and `repository-layout.md` already cross-cites `rules/resource-required-tags.md` as
  authoritative. Correct ownership hygiene, not duplication to unwind.

**Wiring:** `terraform` named neither owner. Now points at `std-terraform-conventions` with the
distinction that matters — *it auto-loads on `.tf`, so you do not need it open while editing; open
it when **planning** infrastructure that does not exist yet, because nothing auto-loads for a file
you have not created* — plus `terraform-mechanics.md` and both hooks.

### BP pass — `rails-architect` wired; `db-migration` skipped because it was already right — *2026-07-15*

**`rails-architect`** named **no owner at all** — not `std-rails-conventions`, not `std-database`,
not `std-error-handling` — the same "names nowhere" case as `react-native-dev`. Now wired to the
six that own its sections (authorization, locking, Sidekiq, the error envelope, pagination,
tracing).

**The Sidekiq section was the gap that mattered.** It said *"Idempotent jobs — safe to retry"* and
nothing else about retries — omitting the fact that decides whether that sentence is a nicety or a
survival requirement: **Sidekiq already retries 25 times over ~20 days, by default.** Nobody
configures that; it *is* the default, so "no retry policy" means three weeks of them, and
`retry_on ..., attempts: 5` runs **30** attempts rather than 5 because ActiveJob's retries stack on
top of Sidekiq's rather than replacing them. That is now in the body, because it changes what you
write on every job, with the depth pointed at rather than copied.

**Two claims checked and found clean** — worth recording, because the absence of a defect is also a
result:
- The **PostGIS example is correctly parameterised** (`ST_DWithin(..., ?, ?)` with bound args), not
  the interpolation bug flagged as a class in `security-auditor`.
- The **Panko serializer is a proper allowlist**. No field leak.

**`backend/app/jobs/` and `backend/app/services/`** were hardcoded wrappers in *instructions* —
fixed to `app/jobs/` / `app/services/`. The Reference Architecture **tree was left alone**: it is
inside a fenced block, i.e. an illustration of shape, and flagging it would flag correct
documentation — the same call made for `phlex-developer`'s Atomic Design tree.

**`ApplicationJob` vs `Sidekiq::Job` was deliberately not touched.** `rails-architect`'s example
uses `< ApplicationJob`; the open P3 records that the repo has not decided, that
`background-jobs.md` recommends native, and that **the decision is the maintainer's, not the
loop's.** Converting it unilaterally would be this loop overriding a call it explicitly deferred.

**`db-migration` was skipped, and that is the finding.** It is already exemplary: it points at
`../std-database/references/locking-and-timeouts.md` in four places, states outright *"that
mechanism is owned by … and is not repeated here"*, and carries a *"Related, owned elsewhere — do
not duplicate"* section. An earlier iteration did this work. Per the mandate — *skip a skill rather
than pad it* — there was nothing to add that would not be filler.

**A gate was considered and declined.** The Sidekiq retry default is restated **17 times across the
repo and agrees everywhere**, with `background-jobs.md:18` quoting Sidekiq's own docs as the
anchor. A third number-gate (after page size and PR size) for a number with no drift adds test
surface for a defect that does not exist. The number-gates that shipped each had a live
contradiction behind them.

### BP pass — `react-native-dev` taught a Centrifugo hook that could not run — *2026-07-15*

The sharpest defect this sweep has found in a *code example*. `react-native-dev`'s Section 5
shipped a `useChatMessages` hook built on:

```typescript
const sub = centrifuge.subscribe(`chat:${roomId}`);
```

**That is not this client's API.** Subscriptions are *created* with `newSubscription()` and
retrieved with `getSubscription()`; `.subscribe()` is a method on the **Subscription object**, not
a channel-taking method on the client. The example could not run at all.

And the shape it taught had the exact leak its own owner
(`std-react-native/references/realtime-centrifugo.md`) exists to prevent. Measured against that
reference, the snippet was wrong **four** ways:

1. wrong creation call (`getSubscription(ch) ?? newSubscription(ch)` is the idiom — `newSubscription`
   **throws** if the channel is already registered, and a remounting screen calls it twice);
2. never called `sub.subscribe()`, so nothing started;
3. cleaned up with `sub.unsubscribe()` while leaving its own handler attached — *"every remount
   stacks another one and the cache update runs N times per message"*;
4. never called `centrifuge.removeSubscription(sub)`, so the channel stayed in the registry and the
   next `newSubscription` threw on navigation.

The one thing it got right was the headline rule — pushing publications into the Query cache via
`setQueryData` rather than a second store. That is why it looked fine.

**Gated, and the scoping is the interesting part.** The check reads **fenced code only**. That is
load-bearing rather than incidental: the fix's own prose says the words
`centrifuge.subscribe(channel)` in order to warn against them, and a naive check flags the
correction. This is the same trap that killed the market-research gate two iterations ago
(markdown emphasis defeats a negation lookbehind) — but here the defect is *always code*, so code
is all the gate reads, and the prose is free to explain itself. It also fails loudly if
`getSubscription(` disappears entirely, rather than passing vacuously.

`react-native-dev` named `std-react-native` **nowhere** — worse than `nextjs-dev`/`reactjs-dev`,
which at least named the skill. Now wired to both owner references, plus the two facts that decide
what you write: `staleTime` is per query (not one default — the thing I nearly mis-filed as a
defect last iteration), and RN testing is **Jest, not Vitest**.

**`phlex-dev`** (63 lines) needed no split — its References section named the *skill* and none of
`std-phlex-conventions`' six references. Now indexed, with the two token facts that bite at
styling time (unregistered token → **no CSS at all**; `-foreground` on a tint → invisible).

### BP pass — `nextjs-dev` + `reactjs-dev`: two budgets, two units, one stated — *2026-07-15*

**A suspicion was checked and withdrawn first.** `staleTime` looked like the page-size pattern:
five values across the repo (30s, 60s, 5min). It is not a defect — `staleTime` is deliberately
**per query**, and `std-reactjs/references/data-fetching.md:74` has the decision table
(`| Data | staleTime | Rationale |`). `users` at 5min and `orders` at 1min is that table working.
Only the *QueryClient default* must agree, and those differ per platform for a reason (React
Native is offline-first, `retry: 3`). Claiming this would have been a false finding.

**The real one is subtler than a wrong number — it is a missing unit.** The Vite initial-JS budget
is stated in three places:

| Source | Figure | Unit stated? |
|---|---|---|
| `std-reactjs/references/routing-and-code-split.md:10` (**owner**) | `< 300KB` | **no** |
| `performance-profiler/SKILL.md:231` | `< 300KB` | **no** |
| `performance-profiler/references/performance-benchmarks.md:61` | `< 150KB` | **gzipped** |

The owner's 300 is what `chunkSizeWarningLimit: 300` compares against — **minified,
uncompressed**. The benchmark table's 150 is **over the wire**. Those differ by roughly 3-4x, so
they are **not competing budgets and neither is stricter** — but a developer handed "150KB" and
"300KB" *inside the same skill*, with neither unit stated, cannot tell whether they conflict and
will pick whichever is convenient. All three now state their measure, and the benchmark table says
outright that it is a different one.

**Gated where it is mechanical.** The prose budget must equal `chunkSizeWarningLimit` — the
`test_limits_match_the_skill_that_documents_them` shape: a documented budget that disagrees with
the thing that actually warns is worse than none, because the developer writes to the doc, the
build complains anyway, and concludes the warning is noise. Units cannot be gated, so they are
stated instead. Verified to fail on a drifted config.

**`nextjs-dev` named no version.** `std-nextjs` devotes a section to *"This targets Next.js 15+ —
and 14 answers differently"* (`fetch` no longer cached, `GET` handlers no longer cached, `cookies`
and `params` now async) and says plainly: *"guidance that does not say which major it means is
guidance you cannot check."* `nextjs-dev` — the skill you open to **build** the feature — said
nothing about the version. Its code was correct for 15 (`params: Promise<{id}>` + `await params`,
verified), so this was a missing anchor rather than wrong code; it now carries the version and the
two consequences.

**Both were `test-generator`'s wiring bug.** Each named its std counterpart *skill* and none of its
**references** — `nextjs-dev` missed 4, `reactjs-dev` missed 7, while their own 3-file reference
sets duplicate those topic-for-topic. Now indexed, framed as *the three files above are worked
patterns; these answer which pattern and why*.

### BP pass — `api-designer`: the page size that was 20 in the only file anyone reads — *2026-07-15*

Chosen by **measuring the duplication surface** rather than picking a skill: for each user-invoked
skill that pairs with a `std-*` counterpart, compare body size to reference count. `api-designer`
was the outlier — **235-line body, 1 reference**, against `std-api-design`'s 120-line body and
**7 references**. That imbalance is what the last three duplications looked like, and it was again.

**A hard numeric contradiction, 3-to-1:**

| Source | Default page size |
|---|---|
| `std-api-design/SKILL.md:88` (**auto-loads** on controllers) | **25** |
| `std-api-design/references/pagination-rails.md:7` | **25** |
| `std-api-design/references/pagination-clients.md:19` | **25** |
| `api-designer/SKILL.md:162` (+ its collection example, + its `api-conventions.md`) | **20** |

The odd family out was **the one being read**. A developer opens `/api-designer` to design an API,
ships a 20-default, and `std-api-design` auto-loads on their controller saying 25. Nothing fails.

**A framing contradiction underneath the number.** `api-designer` presented *"Offset Pagination
(simple)"* first and cursor second, as if offset were the easy default. The owner's load-bearing
rule is the reverse: *"Cursor-based pagination is the default. Offset-based is acceptable only for
small, stable datasets that are not appended to in real time."* Offset is not the simple one — on
an appended-to table it silently skips and repeats rows as the offsets shift under the reader. The
skill was teaching the wrong default *and* the wrong reason.

Its "Deep guides" also pointed only at its own `api-conventions.md` — so, like `test-generator`, it
duplicated seven references and named none of them. Now all seven are indexed, Step 5 carries the
owner's actual rules (cursor default, 25/100, always clamp, `pagy` — CLAUDE.md pins it), Step 7
defers to `versioning-and-deprecation.md`, and the collection example uses the owner's **cursor**
shape (`nextCursor`/`hasMore`/`limit`) rather than an offset shape at the wrong size.

**Gated.** The number is data with an owner — same as the error envelope, same remedy, same gate.
Scoped to lines that literally say "default page size": every unqualified number in an API doc
(`limit=20` in a URL example, `"pageSize": 25` in a body) is not a statement of the default, and
asserting they all match would flag correct examples. Verified to fail on the original 20.

### Layer 1 — `test-generator` 316 → 215, and the SLA that contradicted itself — *2026-07-15*

**`test-generator` was the `deploy` pattern again.** Its "Web Frontend Tests (Vitest + RTL)"
section (~120 lines) duplicated `std-testing/references/react-components.md` (which owns Vitest
config, query priority, MSW, providers, Zustand, Framer Motion, ApexCharts) *and*
`nextjs-server.md` (Server Components, server actions) — both decision-shaped, both in a skill
that **auto-loads** on `**/*.test.*`. Its own "Deep guides" pointed at neither: it indexed only
`testing-standards.md`, so the body duplicated four references and never mentioned them.

**The drift is the same shape as the HSTS one.** The body compressed RTL's query priority to one
line — `getByRole > getByLabelText > getByText > getByTestId` — which silently drops
`getByPlaceholderText` and, worse, the reason the owner gives: *a `getByTestId` test passes even
when the "button" is a non-focusable `<div>` with no accessible name*, so it cannot detect the
accessibility regression it exists to catch. **A summary of a decision guide is not a smaller
version of it — it is the part that does not tell you why.**

### Layer 1 — `onboarding`: the number that had no owner — *2026-07-15*

`onboarding` (304) was **not split, deliberately.** It is read once, end to end, by a new
developer; Ch. 7's signal is *sections never needed together*, and linear reading is the point
here. 304 is 1% over a guideline, and the audit's own rule is not to shred files to hit a round
number. **The duplication check found something worth more than 4 lines:**

**A contradiction inside one skill.** The body said reviews land *"within **24 hours**"*; its own
`references/dev-handbook.md` said *"Review SLA: within **4 business hours**"*. Aimed squarely at
the one reader who has no way to tell which is right — a new developer, on day one, whose whole
job that week is believing the docs.

**Neither was authoritative, because the number has no owner.** `std-git-workflow` pins the PR
process (400 lines, squash merge, Conventional Commits) and says **nothing** about a review SLA;
CLAUDE.md names PR requirements and no SLA either. So it was invented twice, differently. A team's
SLA is not the plugin's to assert — and `onboarding` is a *template* (`{repository-url}`,
`{install-command}`), so it is now `{review-sla}` in both places, with the reason stated: *a number
that appears only in an onboarding doc is a number nobody agreed to.*

**The PR size limit got the opposite treatment, because it does have an owner.** `std-git-workflow`
owns 400; `onboarding` restates it and agrees today. Now gated. Scoped to lines mentioning a PR —
a bare `under (\d+) lines` also matches the **200-line file limit** in `std-react-native` and
`phlex-developer`, which is different data already covered by
`test_limits_match_the_skill_that_documents_them`, and asserting all of them agree would have
failed on correct docs.

**Bodies: done.** `deploy` 232, `doc-generator` 50, `test-generator` 215, `onboarding` 304 (kept).

### Layer 1 — `doc-generator` 334 → 50: seven templates, and a task needs one — *2026-07-15*

The cleanest Ch. 7 split in the repo, because the signal was structural rather than a line count:
`doc-generator`'s body was **seven independent templates** — ADR, API endpoint docs, runbook,
technical spec, changelog, retrospective, change management — and **a changelog task never needs
the retrospective template.** ~315 lines loaded so that ~40 could be used.

Grouped by lifecycle rather than one file per template (Ch. 7's merge signal: short and always
needed together should merge — a spec usually follows an ADR, and the three process artifacts are
one habit):

| Reference | Templates | Lines |
|---|---|---|
| `design-docs.md` | ADR + Technical Specification | 115 |
| `operational-docs.md` | API endpoint docs + Runbook | 120 |
| `process-docs.md` | Changelog + Retrospective + Change management | 181 |

**The duplication check ran first this time** (last iteration's lesson), and it found one real
case and one false lead:

- **False lead — runbooks.** `incident-response/references/runbooks.md` looked like a duplicate.
  It holds *specific* runbooks (Redis OOM, Sidekiq backup); `doc-generator`'s is the *template*
  for writing a new one. Instances vs template — not duplication. The two now point at each other.
- **Real — the ADR template**, in `architecture-advisor` *and* `doc-generator`, with CLAUDE.md
  pinning the shape a third time. **Unlike the HSTS case, neither copy was wrong** — the drift was
  cosmetic (`ADR-[NUMBER]` vs `ADR-NNN`; the advisor spells out `Alternative 1/2`). So it was
  **not** resolved by deletion: both legitimately need it inline, since the ADR is
  `architecture-advisor`'s output contract on *every* task, which is exactly where Ch. 7 puts a
  body. Deleting its copy to satisfy a principle would have made that agent worse.

**Gated instead of merged.** A test holds the two **section sets** in sync, compared at `##` level
(the contract) and allowing `###` sub-detail to differ (editorial). The reason is concrete: ADRs
get grepped — `rg '^## Status' docs/adr/` only works if every ADR has the same headings, so a
template that quietly gains or loses one breaks that silently. CLAUDE.md's four named sections must
also be a subset of both. Verified to fail on a renamed section.

The body keeps exactly one rule, because it applies to every document type: **do not document what
you did not read.** Documentation is believed — that is its function, and why invention costs more
here than in code. A wrong endpoint parameter fails loudly the first time someone calls it; a wrong
runbook step fails at 3am. Write `Unknown: <question>` and leave it: an explicit gap gets filled,
a confident guess never gets questioned, because it does not look like a gap.

**Bodies remaining:** `test-generator` 316, `onboarding` 304.

### Layer 1 — `deploy` 357 → 232, and the duplicate that had quietly lost its HSTS — *2026-07-15*

`deploy` was the worst body in the repo: **357 lines, zero references**, loading in **full** on
every deploy task — including the routine staging deploy that needs none of it. Two clean Ch. 7
split signals (*sections never needed together*), not a line count:

**1. It was duplicating a reference, and the copy had drifted.** `deploy/SKILL.md`'s "Web Frontend
Deployments" covered Vercel and S3+CloudFront — which
`std-infrastructure/references/frontend-deploys.md` already owns, decision-shaped, and which
**auto-loads** for infrastructure work. Two sources of truth, and the body's copy was the weaker
one:

| | `deploy/SKILL.md` (deleted) | `frontend-deploys.md` (owner) |
|---|---|---|
| HSTS | `max-age=63072000` | `max-age=63072000; includeSubDomains; preload` |
| Schema | — | `$schema` for editor validation |
| Referrer-Policy | — | `strict-origin-when-cross-origin` |
| `_next/static/` cache | — | `immutable`, 1 year |

**The HSTS line is the point.** Without `includeSubDomains; preload` the header **does not qualify
for the preload list at all** — so following the duplicate produced a header that looks right and
buys nothing. Nobody edited it wrong; it was written once and the owner moved on. That is what a
second copy does. The same section also carried `cd next && vercel` (a hardcoded wrapper dir, in an
executable instruction — the defect this loop keeps finding, here in a *skill*, which the
agents-only gate does not scan) and `npm i -g vercel` (a global install on a pnpm stack). All three
went with the duplicate.

**2. Canary/blue-green (~72 lines) is real, and is nobody else's.** Verified: nothing in
`std-infrastructure` covers it. So it *moved* to `deploy/references/ecs-strategies.md` (157 lines)
rather than being deleted — a routine deploy never needs it, and reaching for a canary when a
rolling update would do buys two services to reason about exactly when you want fewer. The
reference is self-contained per Ch. 7 and adds what the body's snippets never said: **the shared
database is the trap in both.** "Instant rollback" is a claim about *traffic*, not data — the
listener swap takes milliseconds, the schema does not come back with it. So expand/contract across
two deploys, and a `NOT NULL` column shipped with the code that fills it means the canary looks
fine while **primary** is what breaks.

**Gate extended, no live defect found.** CI's skills-lint validates the pointers a skill *body*
indexes; my earlier test covered *agents*. Nothing validated the pointers **one reference makes to
another** — 21 such cross-links exist, all resolving today. Now gated (79 pointers across 130
files), because a reference is where a stale pointer hides longest: nothing loads it until someone
needs it, and by then they are mid-task. Verified to fail on a dangling pointer inside a reference.

**Bodies remaining:** `doc-generator` 334, `test-generator` 316, `onboarding` 304.

### Layer 2 — the ADR that invents a price; and the wiring closes — *2026-07-15*

**Closes the P2 wiring item: 0 of 13 agents now point at nothing** (was 9). 58 pointers gated,
all resolving.

**`architecture-advisor` had the `requirements-consultant` defect, one rank more expensive.** It
holds `Read, Grep, Glob` — no web — with **no epistemic boundary at all**, and its protocol asked
for: *"Hiring market for chosen technology stack"* (step 5), *"Does a well-maintained open-source
solution exist?"*, *"total cost of ownership (maintenance, upgrades, security patches)"*, *"risk of
vendor lock-in"* (step 6). A repository does not tell you how many engineers there are — a small
team and a large one produce the same file tree.

Worse than the consultant's case, because **an ADR is a permanent record**. A scoping doc is read
once and superseded; an ADR is cited for years by people who reasonably assume the TCO in it was
checked. Same remedy, adapted: step 5's org facts are **inputs — ask**, though "this team already
runs Sidekiq" *is* readable from what is committed and should be cited. Step 6 splits cleanly —
for a domain the stack **already pins**, CLAUDE.md's *Library Preferences* is the standing answer
and citing it is real; for a domain it does not pin, emit a spike, and put any belief under
**Alternatives Considered** as an assumption to verify, never under **Decision** as a finding.

**A wrong pointer was caught before shipping.** `doc-generator/references/doc-templates.md` sounds
exactly like where an ADR template lives. It is model/table documentation — associations,
validations, scopes. Pointing there would have sent the agent to confidently irrelevant material,
which is the harm this whole item is about. The filename was not evidence.

**`refactor-specialist`** got one pointer, not five: `std-testing/references/test-strategy.md` is
decision-shaped and answers what its step 2 actually turns on (*which level of test*, *how do I
build test data*), and its *"mocking a chain vs. simplifying the code"* section is a **refactoring**
decision — if a test needs four mocks to construct, that is the design talking. It also got the
runner table, because last iteration gave it `Bash` and **a green run of the wrong suite proves
nothing** (RN is Jest, not Vitest).

**`requirements-consultant` was nearly skipped, and the honest answer was one sentence.** Its job
is asking a human questions; the depth it needs is their answers. But Phase 5 *does* sketch a
stack-framed architecture, so the layer shape it should follow has a home — one routing note to
`std-clean-architecture/references/` and to `architecture-advisor` for the real design. Four
platform mappings for a sketch would have been padding, and *"a requirements doc that hardens into
an architecture nobody agreed to is how scope arrives pre-decided."*

**Deliberately not gated: "every agent must have ≥1 pointer."** It would have forced exactly the
padding the mandate warns against — `requirements-consultant` legitimately had none until Phase 5
justified one. The gate checks that pointers **resolve**, not that they exist.

### Layer 2+3 — the agent told to lose jobs, with nothing stopping it — *2026-07-15*

`incident-responder` had **no capability boundary at all** — while holding `Bash`, running at
`model: opus, maxTurns: 30`, and carrying a protocol that explicitly instructs production
mutations: *"Rollback to previous ECS task definition"*, *"Kill long-running queries"*,
*"Restart Sidekiq workers"*, and **"Clear stuck queues only as last resort (loses jobs)"**.

`security-auditor` — **identical** tool list (`Read, Grep, Glob, Bash`) — has had an explicit
"Capability boundary (read this first)" section since an earlier pass, citing Ch. 8's Bash hole.
The repo established the pattern, and the one agent whose protocol actually tells it to break
production was the one without it.

**What was gated, measured rather than assumed:**

| Protocol step | Gate |
|---|---|
| Rollback ECS task definition | ✅ `deployment-gate.py:45` asks (`aws ecs update-service`) |
| `DROP`/`TRUNCATE`/unfiltered `DELETE` | ✅ `dangerous-command-blocker.py` denies |
| **"Kill long-running queries"** | ❌ `pg_terminate_backend` matched nothing |
| **"Clear stuck queues (loses jobs)"** | ❌ `redis-cli FLUSHALL` matched nothing |

**Why the last one is the serious one.** On this stack Redis is *both* the Rails cache backend
*and* the Sidekiq queue store (CLAUDE.md). `FLUSHALL` against production does not clear a cache —
it destroys every enqueued job, irreversibly, with no error. The protocol's own **"(loses jobs)"**
was the only thing standing in the way, and that is prose. Ch. 7's placement test: a rule that
must hold whether or not it is read is a gate.

**Scoped, not blanket.** The block requires a *remote* target (`-h`/`-u`, no localhost in the
segment): `redis-cli FLUSHALL` on a dev box is ordinary daily work, and read-only production
commands (`GET`, `INFO`, `LLEN`) must keep working or an incident responder cannot diagnose. Ten
shapes tested, all correct. It lives in `dangerous-command-blocker` rather than a new hook because
that is already the repo's home for irreversible data operations, and its denial already names the
remedy: *"requires manual execution outside Claude Code."*

**`pg_terminate_backend` was deliberately NOT gated.** Killing a runaway query is a standard,
reversible incident action — the query aborts and the app retries. Gating it would flag correct
work under exactly the pressure where a false alarm costs most. The boundary covers it in prose,
which is the right layer for a judgement call.

The new boundary section is adapted rather than copied: unlike a reviewer, an incident responder
*must* be able to mitigate. So: diagnose freely (reading is never gated); never take an
**irreversible** action on your own authority — propose the command, the blast radius, and the
cost of being wrong; know which of your own steps are gated and **do not route around one**; and
say what you could not check, because a report that omits its gaps reads as an all-clear.

### BP pass — `incident-responder` + `clean-architecture` wired — *2026-07-15*

**9 → 3** agents now point at nothing; **49** pointers gated, all resolving.

`incident-responder` got the 9 references that carry the queries and thresholds for its own
protocol — CloudWatch Insights, GCP Logging, request tracing, lock contention, the Sidekiq Dead
set, ECS rollback — because mid-incident is the worst possible time to re-derive an Insights query
from memory. Two facts were lifted into the body because they change a *diagnosis* rather than a
fix, and both were verified against the references themselves: **Sidekiq already retries 25 times
over ~20 days by default** (`background-jobs.md:5`), so "the job never ran" and "the job is still
retrying" look identical from outside; and a waiting `ALTER TABLE` **queues every query behind
it** (`locking-and-timeouts.md:26`), so a migration with no `lock_timeout` presents as a
whole-table outage, not a slow migration.

`clean-architecture` got the four platform mappings plus layer examples, one per protocol step.
"Depends inward" is one sentence, but what it *looks like* differs in all four platforms — which
is exactly where the conformance call gets made. Also given the fail-closed clause the two design
agents got: "no files matched" ≠ "no violations found".

**Remaining (3):** `architecture-advisor`, `refactor-specialist`, `requirements-consultant`.

### BP pass — `phlex-developer` + `devops-engineer`; and the gate that missed a synonym — *2026-07-15*

Continues the P2 wiring. **19 → 6** agents now point at nothing; 35 pointers gated, all resolving.

**`phlex-developer`** *had* a "Reference Files" section — naming **skills, not references**. It
knew `std-phlex-conventions` existed and none of its six reference files (1,473 lines: primitives,
composites, variants/tokens, Stimulus, Turbo, testing), nor `phlex-dev`'s two (1,577 lines). Now a
table mapping each reference to the protocol step that needs it, plus the two token facts that
bite hardest at step 7 — `destructive`/`neutral` are variant **keys**, not tokens, and a class
naming an unregistered token compiles to **no CSS at all**; a `-foreground` token is verified
against its **solid** surface, so it is invisible on a 10% tint.

**`devops-engineer`** was well-wired at the *governance* layer (it named the autoload, the
checker, `deployment-gate.py`) and pointed at **none of `std-infrastructure`'s 10 references** —
ECS Fargate, RDS+PostGIS, OIDC, Vercel, Compose — which are precisely its job. All ten mapped onto
its own numbered steps.

**My own gate had a hole, and this is how it was found.** `phlex-developer` step 3 said
*"**Search** `backend/app/components/`"* — the same hardcoded-wrapper defect I fixed in the two
design agents last iteration, sailing straight past the gate I wrote for it, because my verb list
was `Glob|Read|Grep` and "Search" is not in it. An instruction to go look somewhere is the defect
**however it is phrased**. Verb list widened (`Search|Scan|Look in|Inspect`), and fenced blocks are
now stripped first — `phlex-developer` draws its Atomic Design tree as a `backend/app/components/`
diagram, which is an illustration of *shape*; flagging it would be flagging correct documentation.
Measured: exactly one hit across 13 agents, no false positives.

**Also extended to directory pointers.** `monorepo-architect` points at
`skills/monorepo-architect/references/` as a directory rather than naming files — legitimate but
weaker, and it dangles just as silently if the skill is renamed. Worth recording *how* that was
verified: my first sabotage (`/references/` → `/nope/`) **passed**, because breaking the path made
the pointer stop looking like a pointer (35 → 34 checked) — it fell out of scope rather than
failing. The test was right and the sabotage was wrong; re-run against the realistic failure (skill
renamed, `/references/` intact) it fails correctly. A test that "passes" because its subject
vanished is not a passing test.

**Remaining (6):** `architecture-advisor`, `clean-architecture`, `incident-responder`,
`monorepo-architect` (directory-level only), `refactor-specialist`, `requirements-consultant`.

### BP pass — `code-reviewer` + `test-generator`: 116 references nobody told the agents about — *2026-07-15*

The systemic finding, measured across all 13 agents: **9 had zero pointers to any reference.**
The repo carries **116 reference files** of verified, stack-specific depth, and the agents that do
the work were never told they exist. `SubagentStart` injects tech-stack and team context — not
references — so nothing closes the loop implicitly.

This is a Ch. 7 wiring failure, not a content failure. Tier 2 was written; Tier 1 had no pointer.
And the failure mode is the quiet one: an agent that never learns a reference exists does not
error — it reviews without the material and reports as though it had it.

**`code-reviewer`** was the sharpest case. A prior iteration put every defect this loop verified
into `references/pr-review-guide.md` (325 lines: Rails red flags, N+1, migration safety, PostGIS,
React Native, Sidekiq, plus *"Checks earned from real defects"*). The **skill** indexes it at
`:112`. The **agent** — which actually performs the review — named it nowhere, and `agent:
code-reviewer` in the skill frontmatter routes the work to the agent. The material was written,
indexed, and unreachable by the thing that needed it.

Its step 11 was also "Web-Specific" in a four-platform repo: no Rails, no React Native, no Phlex.
It now covers all four, each check grounded in something already pinned — the Pundit policy
nobody called, `policy_scope` for `index`, `includes` for N+1, `pagy` on lists, the Panko
allowlist, the one error envelope — and points at the depth rather than restating it.

**`test-generator`** named **zero** of the stack's test tools — not `rspec`, not `vitest`, not
`factory_bot`, not `msw` — in a repo pinned to all of them, while four `std-testing` references
sat unreferenced. Now carries the runner table, verified against `std-rails-conventions:97`
(`rspec-rails` + `factory_bot_rails` + `shoulda-matchers`) and
`std-testing/references/react-native.md:15` (**Jest**, not Vitest — *"there is no DOM"*), plus the
rule that decides whether coverage here is real: **mock at the network boundary (MSW), not the
client** — stubbing `axios` or the query hook tests your mock instead of TanStack Query's cache
and retry behaviour.

**Gate — and a hole found by measuring rather than trusting.** CI's skills-lint validates the
references a **skill body** indexes; it globs `skills/*/SKILL.md` and never looks at `agents/*.md`.
Verified by injecting `@skills/std-database/references/DOES-NOT-EXIST.md` into an agent: **all 231
tests stayed green.** The sibling `@rules/` check is a different thing — it proves an agent does
not point into the *pre-plugin* layout, not that today's target exists. The new test accepts both
spellings CI accepts, and that mattered: scoping it to the `@skills/` form alone silently missed
the two **bare** pointers in `security-auditor` (8 pointers checked vs 15). Verified to fail on a
dangling pointer in each form.

**Remaining:** 9 agents still point at nothing. Recorded in OPEN — wiring them needs per-agent
verification that the reference is actually the right one, which is the slow part, not the typing.

### BP pass — `security-auditor`: auditing a stack it wasn't looking at — *2026-07-15*

The audit protocol was generic OWASP. It told the agent to run **`cargo audit`** — there is no
Rust in this stack — and to check LDAP injection and XXE, while the two libraries this stack
actually authenticates and authorizes with, **`pundit`** and **`devise-jwt`**, appeared nowhere.
Ch. 5: attention spent on LDAP is attention not spent on the Pundit action that never authorized.

**Everything added was verified against something the repo already commits to**, not invented:

| Addition | Where the repo already pins it |
|---|---|
| `bundle exec brakeman --no-pager --exit-on-warn` | `std-infrastructure/references/ci-pipeline.md:122` |
| `bundle exec bundler-audit check --update` | `ci-pipeline.md:123` |
| `verify_authorized` / `policy_scope` for `index` | `std-rails-conventions/references/authorization.md` |
| `devise-jwt` does not revoke by default | same reference, `:178` |
| `params.permit!`, SQL interpolation, Panko field leaks | `std-security`, CLAUDE.md stack |

The agent now runs **what CI runs**, so a finding and the merge gate agree rather than diverging
(Layer 3 ↔ Layer 7). Deep material was **pointed at, not copied** — `authorization.md` already
carries the bad/good pairs (Ch. 7).

**A claim was corrected mid-write.** The standard Sidekiq recipe is
`authenticate :user do ... end`, and I had written it — but Devise's route helper needs Warden's
**session middleware**, which an **API-only** Rails app (CLAUDE.md's shape) does not load by
default. The blog-post recipe can be present and authenticate nobody. `Sidekiq::Web.use
Rack::Auth::Basic` in an initializer is the fit here, and the guidance now says to verify the
recipe rejects an anonymous request rather than assume it.

### Layer 3 — new hook: `rails-routes-checker.py` (unauthenticated `Sidekiq::Web`) — *2026-07-15*

**`Sidekiq::Web` was covered nowhere in the repo** — not in `std-security`, not in the
security-auditor, despite CLAUDE.md committing to Sidekiq. `mount Sidekiq::Web => '/sidekiq'`
with nothing wrapping it publishes every job's **arguments** (user ids, emails, tokens ride along
routinely) and lets any visitor retry or kill jobs. Two lines, no error, looks finished.

Ch. 7's placement test made it a **hook**, not a bullet in an agent: it must hold whether or not
anybody runs an audit.

**The false-positive path is the whole design.** The idiomatic protection for an API-only app is
*not* in `routes.rb` — it is `Sidekiq::Web.use Rack::Auth::Basic` in
`config/initializers/sidekiq.rb`. A routes.rb-only check would have flagged correctly-secured
apps, i.e. this repo's own recurring failure. So the checker reads the sibling initializers from
disk before warning, and returns "guarded" on an unreadable tree — silence beats a false
accusation. Four fixtures pin it: bare mount warns; `authenticate` block silent; initializer-
protected silent; no-mount silent.

**A gap I created and closed in the same pass:** the hook named `std-security`, which auto-loads
on `**/*.rb` (so the pointer resolves) but **said nothing about Sidekiq** — a remedy naming a
document that lacks the remedy. `std-security` now carries the rule and the API-only caveat.
Worth noting: `test_file_scoped_hooks_name_a_loadable_skill` would *not* have caught this — it
proves a named skill can load, not that it covers the topic. Recorded below as a known limit.

### Layer 2 — the consultant asked to research a market it cannot see — *2026-07-15*

`requirements-consultant` holds `Read, Grep, Glob` — no WebSearch, no WebFetch — and its Phase 0
said *"Name 3+ competitors and their approach"*, *"What is the industry-standard UX pattern"*,
and *"Evaluate cost, reliability, and vendor lock-in"* for third-party services. It can read this
repository and nothing else, so every one of those answers would come from training data,
presented as research.

**This is the most expensive thing this agent could fabricate.** Market claims are confident in
tone (training data is full of competitor names), stale by construction (pricing and features
move faster than any cutoff), unverifiable without redoing the work — which is the whole cost
Phase 0 exists to save — and they land directly in **build/buy and scope decisions**.

**The skill's phase count gave it away.** `SKILL.md` claimed a *"six-phase protocol"* and
documented Phases 1-6; the agent defines Phase 0 through 6 — **seven**. The undocumented phase
was exactly the broken one: Phase 0 was bolted on later and the skill never updated. A phase the
skill does not document is a phase nobody reviews.

**The file already knew the answer.** Phase 0's own feasibility bullet said *"What are the
technical unknowns? List spike stories for each"* — spike stories were already the established
idiom two lines below the market section. Drift, not design, same signature as the design agents.

Phase 0 now emits a **research brief, not research results**: spike stories with an owner and the
decision each unblocks. The split is by what the agent can honestly do — stack fit and technical
unknowns it *can* answer from the repo (citing files); competitor names, pricing and SLAs it
cannot; timeline/team-size/budget are **inputs it does not have and must ask for**, not infer from
a repository. Compliance stays as triage → flag → named sign-off, never a ruling. Repo precedent
supports the read-only shape: only `phlex-developer` holds a web tool (WebFetch, for Phlex docs),
and no agent has WebSearch.

**A gate was prototyped and deliberately rejected.** A detector for "web-less agent told to
research the market" flagged **my own fix**: the prohibition reads *"Do \*\*not\*\* name
competitors"*, and a negation lookbehind cannot see past markdown emphasis (`** ` sits between
`not` and `name`). Contorting the prose to satisfy a brittle regex is tail-wagging-dog, and a gate
that flags the correct fix is the exact failure this suite keeps catching elsewhere. The agent's
epistemic boundary is stated in its body instead — *"You have `Read`, `Grep` and `Glob` — the
repository, and nothing else"* — which is context that applies to every Phase 0 task, i.e. exactly
where Ch. 7's placement test puts it. **What did ship is the phase-count check**: the number is
data, prose cannot be imported, so it is counted rather than restated.

### Layer 2 — the agent that could change code but not test it — *2026-07-15*

`refactor-specialist` shipped `Read, Grep, Glob, Write, Edit` — **no Bash** — while its own
protocol said *"Run the test suite to confirm it passes"*, *"Execute the relevant test suite
after every change"*, *"NEVER refactor without tests… the single most important rule"*, and
required it to report **"Test results (pass/fail count)"**. It could not run any of them.

That is the worst combination on offer: **full power to mutate, zero power to verify, and a
protocol demanding a number it cannot obtain.** The only way to comply was to invent one — and
the entire safety argument for the agent is that the tests were green before and after. Ch. 8's
removed-capability trap: taking the tool away does not remove the instruction that needs it, it
just makes it unsatisfiable, and the model still has to answer.

**Measured across all 13 agents, it was the only one that could write but not verify.**
`devops-engineer`, `phlex-developer` and `test-generator` all pair Write/Edit with Bash; the six
read-only agents correctly have neither. An outlier, not a design decision — so granting Bash
restores the repo's own pattern rather than inventing one, and Ch. 11's lowest-effective-layer is
satisfied because Bash is already governed by four PreToolUse gates
(`dangerous-command-blocker`, `pre-commit-check`, `deployment-gate`, `terraform-command-gate`).

Bash alone was not the whole fix — the protocol now forbids reporting a result it did not
observe (*"I could not run the tests" is a usable report; an invented green is worse than no
refactoring*), and treats a red baseline as a stop condition, since you cannot tell your
regression from theirs.

### Layer 2 — two design agents globbed directories the plugin swore off — *2026-07-15*

`design-system-architect` and `design-critique` globbed `web/src/components/**`,
`next/src/components/**`, `mobile/src/components/**`, `backend/app/components/**`. The plugin's
central monorepo claim is that it is **wrapper-directory agnostic**. In any repo not using those
four names — `apps/web-client`, `frontend`, a flat layout — the globs match nothing, and **an
auditing agent that finds nothing reports clean**. A fabricated clean bill is worse than an
error: nobody investigates it.

Both files were **internally inconsistent**, which is what proves drift rather than design —
`design-system-architect` already globbed `**/globals.css` and `**/styles/**` correctly two lines
above the hardcoded ones. Both now locate packages by **marker file** (`next.config.*`,
`vite.config.*`, `metro.config.js`, `Gemfile`) and search from the marker's directory, mirroring
`_hooklib.detect_framework`. The marker is not optional detail: it is the only thing separating a
React Native component from a browser React one — both are `.tsx` under `**/src/components/`, and
no directory name distinguishes them. Both agents now must report "no components found" rather
than clean.

**The gate is deliberately narrow.** A blanket ban on `backend/app/` would flag **301
occurrences across 46 files**, nearly all legitimate — an example needs a concrete path, and
`e.g. backend/app/models/user.rb` reads better than a glob. Only a hardcoded wrapper inside an
instruction the agent *executes* (Glob/Read/Grep) is the defect. Gating the prose would have been
this repo's own recurring failure: a gate that flags correct code is a gate people learn to
ignore.

### Layer 1+3 — one error envelope, three shapes, and a gate enforcing a fourth — *2026-07-15*

Four files described the same API error body, disagreeing on **every axis a client parses**:

| Source | `error` | `code` | status | `details` | id key |
|---|---|---|---|---|---|
| `std-error-handling/SKILL.md` | string | **`422` (int)** | in `code` | **object** | `request_id` |
| `std-api-design/errors-*.md` *(owner)* | string | `"VALIDATION_ERROR"` | `status` | array | `requestId` |
| `api-designer/SKILL.md` + `api-conventions.md` | **object** | string | *absent* | array | `requestId` |

A client written against one breaks on the others. `std-error-handling` auto-loads on **every**
`.rb`/`.ts`/`.tsx` file, so its copy — the most divergent — was the one most likely to be read.

The contradiction was **self-aware**: `std-error-handling/SKILL.md` said *"owned elsewhere — do
not duplicate: the API error envelope →"* about 30 lines after duplicating it. That pointer also
settled ownership, so this needed no judgement call: `std-api-design`'s two references (Rails and
TypeScript) already agreed with each other, and `SKILL.md:54` states the casing rule outright
(*"Use camelCase for JSON response keys"*). Three-to-one on ownership and internal consistency.

**The gate enforced a fourth shape — and flagged correct code.** `api-design-checker.py` grepped
the rendered block for the **substring** `request_id` and warned *"missing code/request_id"*:

- **It named a remedy that produces a violation.** It told you to add `request_id` to an API whose
  stated convention is camelCase. Ch. 25 — the denial named the bug.
- **It passed canonical code only by luck.** `errors-rails.md` writes `requestId: request.request_id`;
  the substring appears on the **value** side, via the Rails accessor. Write `requestId: rid` —
  the identical envelope, correct casing — and the gate fired. *Measured, not theorised.*
- **`code` matched anywhere**, so `status_code:` satisfied it.

Now it matches **key positions**, and separates absent from present-but-snake_case (different bug,
different remedy). One claim was **checked and withdrawn**: I expected the hook to reject the
canonical helper outright; it does not — the helper's `render json: body` never matches the
literal-hash regex at all. That blind spot is now stated in the docstring rather than hidden: the
inline literal is what gets written when someone is *not* using the helper, which is exactly the
case worth catching, and resolving the variable means parsing Ruby.

**Gate:** the envelope is data, so the test re-parses it from the owner rather than restating it,
and asserts `std-error-handling` keeps no copy at all. Verified to fail on both original defects.

### Layer 1 — the tokens that compiled to nothing, and the alert nobody could read — *2026-07-15*

**A Tailwind utility naming an unregistered token compiles to NOTHING** — no error, no warning,
no CSS. `bg-destructive` on a Delete button renders transparent with inherited text. It reads
like a token, reviews like a token, and silently is not one. That is the whole failure mode: it
survives review precisely because it looks right.

Four registries (Tailwind v4 `@theme`, Tailwind v3 `colors`, RN light, RN dark) unanimously
define `error` and `muted`. **None define `destructive` or `neutral`.** Yet the docs taught:
- `bg-destructive` in 4 files, and
- `bg-neutral text-neutral-foreground` across all four platform examples of the rule literally
  titled **"Atoms Must Use Design Tokens"**.

`std-design-system` and `std-phlex-conventions` **both auto-load for `**/app/components/**/*.rb`**
and disagreed — one said `bg-error`, the other `bg-destructive`. An agent could not comply with
both. In every case `destructive`/`neutral` was correct as the variant **key** and wrong as the
**token**; the canonical Button in `theming/references/platform-integration.md:162` already had
it right (`destructive: "bg-error ..."`), which is what made the drift invisible.

**The alert nobody could read.** `success: "bg-success/10 text-success-foreground"` measures
**1.05:1** — near-white on near-white. A `-foreground` token is contrast-verified against its
**solid** surface, never a 10% tint. The `warning` row passed at 13.52:1 by pure coincidence (its
foreground happens to be dark brown), and that symmetry is exactly what made the bug look
deliberate. The semantic token is no rescue either: `text-warning` on its own tint is **1.99:1**.
`text-foreground` measures ~17:1 — the tint and border carry the meaning, the text inherits the
page's already-verified body colour.

**Why nothing caught it:** `design-token-checker.py` has no allowlist, so it parsed
`bg-destructive` as a well-formed token class and passed. The registry is **data**, and prose
cannot be imported — so the new test recomputes it from `platform-integration.md` rather than
restating it.

**The gate's scope is the point.** A first pass over raw prose reported `to-many` (from
"many-to-many") and `gray` (from `bg-gray-100`) — 41 names, almost all English. A gate that flags
correct code is a gate people learn to ignore, so the check is confined to class strings inside
fenced code, and exempts tokens a file registers itself (`defining-tokens.md` defines `--brand`
then demos `bg-brand` — that is the file working as intended). Verified to fail on the real bug
before being trusted.

### Layer 4 — a hook naming a skill that could never load — *2026-07-15*

`error-handling-checker.py` names the `std-error-handling` skill **five times** as the remedy for
what it flags. That skill shipped with **no `paths:`** — it auto-loaded on nothing, ever. Ch. 25
says a denial must name a remedy; a remedy with no delivery mechanism is not one. Its `paths:` now
mirror the checker's own `SOURCE_EXTENSIONS`, which turn out to be exactly `std-code-standards`'
six patterns — derived, not guessed.

**`std-git-workflow` and `std-agent-teams` stay pathless, deliberately.** `pre-commit-check.py`
fires on `git commit`, where there is no file to key on. Ch. 7's placement test settles it: a rule
that must hold whether or not it is read is a hook, not context — and the hook already names the
skill when it denies. Inventing a `paths:` to satisfy a checker would be fabricating a trigger.
So the new test exempts Bash-scoped hooks by design rather than by omission.

**Autoload coverage, measured** (20 std-* skills vs. real stack paths): source code is well
covered — a Phlex component loads 7 skills, a Next page 7. **Configuration files are the blind
spot**: `.rubocop.yml`, `Fastfile`, `Matchfile`, `package.json`, `turbo.json`,
`pnpm-workspace.yaml`, `tsconfig.json` matched nothing. `tsconfig.json` is now claimed by
`std-reactjs`, which already stated a rule *about that file* (`"strict": true`, `@/`→`src/`) and
already loaded on `vite.config.*` — the other half of the same alias rule. `.mcp.json` needed
nothing: `mcp-install-gate.py` already covers it at the hook layer and names `mcp-advisor`.
`.rubocop.yml` was rejected for `std-infrastructure` — every rubocop mention there is "run it in
CI", which says nothing about writing that file.

**`paths:` cannot read a marker file.** CLAUDE.md describes framework detection as marker-based
(`next.config.*`, `metro.config.js`) and that is true of *hooks* (`_hooklib.is_react_native`) —
but skill autoload is a pure glob, and `app/` is owned by Next's App Router, Expo Router, and
Rails simultaneously. Measured off-stack false-loads, all real, none reachable from the stack
CLAUDE.md commits to (Rails API-only, `@react-navigation`, App Router):
`app/javascript/**/*.tsx` → std-nextjs; `mobile/app/(tabs)/*.tsx` → std-nextjs;
`src/pages/**/*.tsx` (Next Pages Router) → std-reactjs, never std-nextjs. Loading the *wrong*
framework skill is worse than loading none — it is confident, on-topic, and wrong. A new test
pins the six canonical stack paths to exactly one framework skill each, so a later path edit
cannot quietly undo it. Adopting any of those shapes needs a marker-aware hook, not a cleverer
glob.

### Layer 1 — 19 dangling pointers, and a "Verified" table that was fabricated — *2026-07-15*
Batch 3 from the adversarial audit. Both findings are shapes this loop already fixed once — and
both survived because the earlier sweep stopped one directory short.

**19 pointers into a layout that has not existed since the plugin conversion.** Neither
`.claude/rules/` nor `.claude/agents/` exists. The repo fixed this class **in hooks only** three
iterations ago and scoped the regression test to *hook messages* — so `agents/` and `skills/`
were never swept. The worst instance is `phlex-developer.md:59`: step **9 of 9** is *"Verify
compliance — check against `@rules/phlex-conventions.md`"*. The compliance step pointed at
nothing, so it no-opped and the agent reported a check it never performed.

Two needed a **meaning** change, not a path:
- `devops-engineer.md:118` claimed the terraform rules auto-load for `terraform/**/*.tf`. The
  skill declares `**/*.tf` — an agent trusting the old text concludes a `.tf` outside a
  `terraform/` wrapper is unguarded, contradicting this repo's wrapper-agnostic detection.
- `code-reviewer/SKILL.md:35` said **WCAG 2.1** AA; the house standard is 2.2.

The pointer test now covers `agents/`, `skills/` and every reference — not just hooks.

**The `theming` contrast table was fiction.** Headed *"Verified Foreground / Background Pairs"*,
and **9 of its 10 ratios were wrong**. Recomputed independently from the file's own `:root`
block, with the formula validated against two published values first (21.00 white/black, 4.54 for
#767676 on white):

| token | claimed | actual |
|---|---|---|
| `--success` | 4.6 "Passes AA" | **3.00** |
| `--error` | 5.1 "Passes AA" | **3.61** |
| `--muted` | 4.6 "Passes AA" | **4.34** |
| `--info` (dark) | 5.0 | **2.99** |
| `--warning` | 5.8 | 6.79 |
| `--primary` | 12.6 | 17.06 |

Errors run in **both** directions, which rules out a systematic miscalculation — the numbers were
never computed. And these are the **default** tokens, copied verbatim into `theme-presets.md`: a
team trusting the word "Verified" shipped body text that this plugin's own
`accessibility-auditor` fails at 4.5:1.

**Fixed both halves**, because fixing only the table would leave defaults *documented* as failing
and still shipped: `--success` to 28% L (4.70:1), `--error` to 47% (4.82), `--muted-foreground`
to 44% (4.81), dark `--info` to 35% (4.80) — each with headroom so downstream rounding cannot
push a "passing" token back under. The table is now **regenerated from the tokens** and headed
"Measured". `test_contrast_table_matches_the_tokens` recomputes it, validates the formula before
trusting a cell, and fails on drift **or** on any default dropping below AA — proven by reverting
`--success` in a scratch copy (2 failures, correctly). **214/214.**

### Layer 3 — a 97-agent audit found 7 broken gates in our own hooks — *2026-07-15*
Ran an adversarial audit workflow: 6 independent lenses over skills/references/hooks/agents, then
**3 refuters per finding**, each told to refute and to default to refuted when uncertain. 97
agents, 885 tool calls. That design was chosen because this loop's dominant failure has been
**false positives** — 8 caught so far. It worked: every surviving finding was reproduced
end-to-end before any edit.

**P0 — gates that fired on correct work, every session.** The repo states the principle in
`migration-validator.py:23` — *"a gate that flags correct code is a gate people learn to ignore"* —
and violated it three times:
- `api-design-checker`: `re.IGNORECASE` voided `[A-Z]`, the **only** thing separating `/getUser`
  from `/posts`. So `/posts`, `/addresses`, `/listings`, `/editions` were each told *"Use plural
  nouns for resources"* — which they are. On every API-client file in Vite and Next. Fixing it
  cost **zero** detection and *gained* `/api/deleteItem`, which the old char class missed by
  accident.
- `task-completed-checker`: `"test" in text` matches "la-test-". **Exit 2, a hard reject** —
  "Deploy the latest build" was blocked against a remedy that cannot exist.
- `teammate-idle-checker`: "add" matches "address", "fix" matches "prefix" — *review* vocabulary.
  And it told teammates to "implement the changes" while four bundled agents ship
  `tools: Read, Grep, Glob` and are placed as teammates by the Review/Design templates:
  **structurally incapable** of complying.

**P1 — gates that silently did not fire (false assurance).**
- `hooks.json` routed `migration-validator` on `"Write"` while the hook accepts `("Write",
  "Edit")` — so the canonical Rails path (`rails g migration`, then Edit) **never reached the
  gate**. Now `Edit|Write`, plus a generic test asserting every hook's matcher covers the tools
  its `check()` accepts.
- `terraform-checker`: `\w` cannot match `-`, so a kebab-named resource was invisible to the
  naming check — *and*, because the tags check derives its resource list from the same pattern,
  an all-kebab file yielded an empty list and **the tags check skipped entirely**.
- `monitoring-checker`: **removed** the request_id-per-line check. It asked source lines to
  contain a string Rails injects via `config.log_tags` — a false positive on every correctly
  configured app, and on a broken one the remedy is config, not the call site (Ch. 7 placement
  test). It was also dead: a trailing `\s` meant only paren-less Ruby matched.
- `accessibility-checker`: matched CSS `outline: none` while reading only `.tsx/.jsx`, where the
  idiom is Tailwind `outline-none` — matcher and scope **disjoint**, so it could never fire.
  Widened both, and — the part a naive fix would have broken — it now honours its own docstring
  by checking for a *replacement*, so `focus-visible:outline-none focus-visible:ring-2` (the
  repo's own recommendation) stays quiet.

**38 new fixtures**, every one a case that shipped, each asserting the false-positive **and**
true-positive direction: a fix that silences real detection is not a fix. Nothing tested the
false-positive direction before, which is exactly why all seven survived. **210/210.**

### BP pass — `/i18n` split; and the audit was measuring the wrong thing — *2026-07-15*
Two findings, and the second is about this document.

**The hypothesis was wrong, again, and measuring saved it.** `/i18n` (367 lines) and `std-i18n`
(113) share **9 of 17 headings**, which looked like duplication worth merging. Content overlap is
**10%** — 7 lines, all i18next boilerplate imports that are identical by nature. The skills
genuinely differ: `std-i18n` is the path-scoped rule set that auto-loads when you touch a locale
file; `/i18n` is the invoked workflow. Merging them would have destroyed a real distinction, the
same way the `full-guide` deletion would have.

**The audit's sizing backlog only ever measured `references/`. Bodies were never checked** — and
a body is the more expensive half: a reference loads when a task needs it, a **body loads in full
every time the skill activates** (Ch. 5, the attention economy). Sweeping them found **5 bodies
over 300 lines**, two with **zero references to peel into**: `/i18n` 367 and `/deploy` 357 load
entirely, always.

Split `/i18n` along the seam that actually exists (Ch. 7: *sections never needed together* — a
Rails task never needs the React Native half): **367 → 91** body, four references
(`rails-i18n` 142, `react-native-i18n` 142, `web-i18n` 73, `locale-workflow` 32). Verified
line-by-line that **no content was lost** — the single missing line is the intro sentence I
deliberately rewrote. The body now leads with the decisions that outlive the strings
(server-vs-client localization, key namespace, RTL, where the locale lives) instead of opening
with Rails setup, and states the API-returns-codes rule the old body never made explicit.

**Not gated, deliberately.** The *deliberate non-decisions* below say sizing is a guideline, not
a gate — a body-size check would fire on judgement calls and earn a `|| true`, which is exactly
the failure fixed one iteration ago. Recorded in the backlog instead.

Version → **2.0.1** (PATCH): consumer-visible (floating installs receive it) but no new
capability and no behaviour change — the same knowledge, reorganised. The delivery gate demands
the bump; `docs/releasing.md`'s table sets the level.

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
| `std-design-system` | 3-tier (4 refs) | done *2026-07-15* — defining-tokens.md said 'ALWAYS darken the foreground' while the repo's own canonical tokens + all 3 presets darken the SURFACE; now splits brand (foreground) vs semantic status (surface), verified --primary was never touched |
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
| `std-terraform-conventions` | single-file | done *2026-07-15* — its tag list is now gated against terraform-checker.py's REQUIRED_TAGS; 0 refs is correct at 99 lines (no depth to peel) |
| `std-testing` | 3-tier (4 refs) | todo |

#### Workflow skills — 44

| Skill | Tier state | BP pass |
|---|---|---|
| `accessibility-auditor` | 3-tier (2 refs) | done *2026-07-15* — listed contrast as a MANUAL DevTools check, which is why it never caught the 13 failing presets; now carries an iterating token-contrast test (not manual) + the tint/preset traps; wired to std-accessibility, std-design-system, theming |
| `api-designer` | 3-tier (1 refs) | done *2026-07-15* — default page size was 20 vs the owner's 25 (3-to-1), and taught offset-first when the owner defaults to cursor; wired to all 7 std-api-design refs; number now gated |
| `architecture-advisor` | single-file | todo |
| `atomic-design` | rule-per-file (10) | done *2026-07-15* — tokens verified clean by the registry gate; added the owner pointer (it owns hierarchy, std-design-system owns tokens) — 'uses a token' != 'uses a registered token' |
| `brand-identity` | 3-tier (2 refs) | done *2026-07-15* — **it generated the failing presets**: color-theory.md prescribed lightness ranges with no foreground named, and the whole Success/Info ranges fail against near-white (3.40/3.12 best). Now foreground-aware caps (<=29/48/35, floored, set by the most-saturated end) + gated; must emit the measured ratio; dark mode is measured, not inverted |
| `clean-architecture` | 3-tier (1 refs) | todo |
| `code-reviewer` | 3-tier (2 refs) | todo |
| `compliance-auditor` | single-file | done *2026-07-15* — signed Claude as **Auditor** on a SOC2/HIPAA/PCI 'Compliance Audit Report' with a Compliant count and zero epistemic limits (the only skill in the repo signing as an authority). Now a readiness self-assessment: evidence-not-compliance vocabulary, 'no evidence in scope' != a gap, Type II operating-effectiveness caveat, named human reviewer required |
| `composition-patterns` | rule-per-file (8) | done *2026-07-15* — wired to std-reactjs (state placement) + std-nextjs (Server/Client boundary); its react19 section is 19-only and the repo pins 19 for Next alone -> P3 |
| `db-migration` | 3-tier (2 refs) | done *2026-07-15* — **skipped, already exemplary**: points at std-database/references/locking-and-timeouts.md in 4 places and says outright it does not repeat it. Nothing to add that would not be filler |
| `deploy` | single-file | todo |
| `design-critique` | single-file | todo |
| `design-to-code` | 3-tier (1 refs) | todo |
| `doc-generator` | 3-tier (4 refs) | done *2026-07-15* — 334 -> 50; 7 templates split by lifecycle; ADR section set gated against architecture-advisor + CLAUDE.md |
| `figma-handoff` | 3-tier (2 refs) | done *2026-07-15* — maps Figma style names onto the registry (transliterating `Brand/Green/500` mints a token that compiles to no CSS); unmatched style = a finding, not a naming exercise; a designer's fill is unverified (#10B981 on white = 2.54:1) |
| `i18n` | 3-tier (4 refs) | done *2026-07-15* — 367→91 body, split by platform |
| `incident-response` | 3-tier (1 refs) | todo |
| `log-search` || done *2026-07-15* — **skipped, already right**: agrees with std-monitoring on `request_id`, states its precondition honestly ("this file assumes those exist"), points at the owner. Nothing to add that would not be padding |
| `mcp-advisor` | 3-tier (2 refs) | done *2026-07-15* — shipped as a BP skill |
| `toolchain` || done *2026-07-15* — its own example mixed `pnpm exec` and `npx` while its headline rule is "CI and your laptop must run the same commands" and CI runs npm. Repo pins no package manager -> the lockfile now decides the runner (deterministic, no pin needed); npm-vs-pnpm split recorded as P3 |
| `marketing-assets` | 3-tier (1 refs) | done *2026-07-15* — platform-specs.md called itself 'Complete', undated and unsourced, for the most volatile facts in the plugin. No numbers changed (unverifiable from here — asserting a fix would be the defect); now framed as a cached copy that expires, verify-before-ship, don't extend from memory, recommended != maximum |
| `monorepo-architect` | 3-tier (6 refs) | done *2026-07-15* — shipped as a BP skill |
| `mobile-beta-release` | 3-tier (3 refs) | done *2026-07-15* — shipped as a BP skill; **re-audited**: 100/10,000/90-day undated, and testflight.md's verbatim Apple quotes are sourced-but-not-dated (reads more authoritative, equally uncheckable). No numbers changed; added the expires-vs-stable split + check the consoles |
| `mobile-signing` | 3-tier (3 refs) | done *2026-07-15* — shipped as a BP skill; **re-audited**: already right on freshness by construction (states certs expire, never a period). Added the one gap — it breaks std-infrastructure's 'federation, not keys' rule *necessarily* (Apple's .p8 has no OIDC path); now a stated exception |
| `nextjs-dev` | 3-tier (3 refs) | done *2026-07-15* — named no Next version while std-nextjs pins 15+ and says 14 answers differently (code was 15-correct; anchor was missing); wired to all 4 owner refs |
| `onboarding` | 3-tier (1 refs) | done *2026-07-15* — kept at 304 (read once, end-to-end); fixed a self-contradiction: body said 24h review SLA, its own handbook said 4 business hours, and the number has no owner -> {review-sla} |
| `performance-profiler` | 3-tier (1 refs) | done *2026-07-15* — its body said 300KB and its own reference 150KB gzipped, neither stating the unit; both now say which measure, and the number is gated against the config |
| `phlex-dev` | 3-tier (2 refs) | done *2026-07-15* — References named the skill, not its 6 refs; now indexed + the two token facts (unregistered token = no CSS; -foreground on a tint = invisible) |
| `rails-architect` | 3-tier (1 refs) | done *2026-07-15* — named no owner at all; wired to 6; Sidekiq section omitted the 25-retries/~20-days default and the retry_on-stacks trap; PostGIS + Panko verified clean; ApplicationJob left alone (maintainer's call, P3) |
| `react-best-practices` | rule-per-file (57) | done *2026-07-15* — rules verified 19-aware (no forwardRef/useFormState; Compiler caveat present); added the honest version table (19 for Next, unpinned for Vite/RN) + wired to std-reactjs/std-nextjs |
| `react-native-best-practices` | rule-per-file (36) | done *2026-07-15* — wired to std-react-native (realtime, offline) + Jest-not-Vitest; repo pins no RN/React version for mobile while its rules assume Compiler/Expo-era RN -> P3 |
| `react-native-dev` | 3-tier (1 refs) | done *2026-07-15* — its Centrifugo hook called `centrifuge.subscribe(channel)`, not this client's API (could not run) + 4 leaks vs the owner; replaced with the owner's rules, gated in code fences; wired to both std-react-native refs |
| `reactjs-dev` | 3-tier (3 refs) | done *2026-07-15* — wired to all 7 std-reactjs refs (its 3 duplicate them topic-for-topic); bundle budget unit stated + gated against chunkSizeWarningLimit |
| `refactor` | single-file | todo |
| `requirements-consultant` | single-file | todo |
| `sdh-engineering-standards` | single-file | todo |
| `security-auditor` | 3-tier (1 refs) | todo |
| `sprint-planner` | single-file | done *2026-07-15* — its Story Point Reference mapped points to DURATION eleven lines above 'Compare, don't calculate', which also made its own velocity tracking circular. Duration column removed (examples kept as anchors); estimation is the team's. technical-rfc:114 already had it right ('developer-days, not story points') |
| `technical-rfc` | 3-tier (1 refs) | todo |
| `terraform` | rule-per-file (47) | done *2026-07-15* — rules-shaped, so a different lens: hook-enforced REQUIRED_TAGS stated by 3 sources, ungated -> now gated (sibling of the limits test); repository-layout vs terraform-mechanics overlap checked and clean; wired to std-terraform-conventions + both hooks |
| `test-generator` | 3-tier (1 refs) | done *2026-07-15* — 316 -> 215; web-frontend half was a drifted copy of std-testing/react-components.md + nextjs-server.md; now points at all 4 |
| `theming` | 3-tier (3 refs) | done *2026-07-15* — theme-presets.md shipped 13 pairs below AA (worst 2.54:1); the earlier design-tokens.md fix never propagated because the gate read one file. All 36 pairs now clear AA; Corporate realigned to the canonical palette + drift gated |
| `ui-ux-patterns` | 3-tier (3 refs) | todo |
| `web-design-guidelines` | single-file | done *2026-07-15* — ships NONE of the advertised 100+ rules: fetches them (and its output format) from an unpinned third-party main branch. Fail-closed clause added (was: reviews from memory when the fetch fails), house-wins, source attribution; docs corrected in 4 places; pin/vendor/float = maintainer's call (P2, detector ready) |

#### Agents — 13

| Agent | BP pass |
|---|---|
| `architecture-advisor` | done *2026-07-15* — Layer 2: asked for hiring market/TCO/vendor lock-in with no web access, and an ADR is permanent; boundary added (ask for org facts, cite Library Preferences, spike the rest); wired 6 refs |
| `clean-architecture` | done *2026-07-15* — wired the 4 platform mappings + layer-examples to its protocol steps; fail-closed clause ('no files matched' != 'no violations') |
| `code-reviewer` | done *2026-07-15* — step 11 covers all 4 platforms (was web-only); wired to pr-review-guide.md + 3 refs it never knew existed |
| `design-critique` | done *2026-07-15* — Layer 2: hardcoded wrapper globs -> marker-based; fail-closed on empty |
| `design-system-architect` | done *2026-07-15* — Layer 2: hardcoded wrapper globs -> marker-based; fail-closed on empty |
| `devops-engineer` | done *2026-07-15* — wired all 10 std-infrastructure refs to its numbered steps (was zero; governance layer was already sound) |
| `incident-responder` | done *2026-07-15* — Layer 2: NO authority boundary while holding Bash + told to 'clear stuck queues (loses jobs)'; boundary added + remote redis FLUSH now blocked; wired 9 refs |
| `monorepo-architect` | done *2026-07-15* — shipped with the skill |
| `phlex-developer` | done *2026-07-15* — Reference Files named skills not references; wired 9 refs to protocol steps; `Search backend/app/` -> marker-agnostic glob; token facts added |
| `refactor-specialist` | done *2026-07-15* — Layer 2: granted Bash (wrote code it could not test); no unobserved test results; wired test-strategy.md + runner table (RN is Jest, not Vitest) |
| `requirements-consultant` | done *2026-07-15* — Layer 2: Phase 0 emits spike stories, not invented market research; phase count fixed; refs deliberately minimal (one routing note — its depth is the human's answers, not a document) |
| `security-auditor` | done *2026-07-15* — stack-grounded: brakeman/bundler-audit (what CI runs), Pundit `verify_authorized`, devise-jwt revocation, Sidekiq::Web, Panko leaks; dropped `cargo audit` (no Rust) |
| `test-generator` | done *2026-07-15* — named none of rspec/vitest/factory_bot/msw; added the runner table (Jest for RN, not Vitest) + MSW boundary rule; wired to 5 refs |

---
## OPEN — prioritized backlog

*(The four below are **verified**, not suspected — each was measured against the files named.
They are recorded here so the specifics survive a context compaction.)*

### P3 · Layer 3 — a hook's skill pointer is checked for reachability, not for content
`test_file_scoped_hooks_name_a_loadable_skill` proves that a skill a hook names has `paths:` and
can load. It does **not** prove the skill says anything about the topic. Found the hard way:
`rails-routes-checker.py` shipped naming `std-security`, which auto-loads on `**/*.rb` — pointer
resolves, test green — while being entirely silent on Sidekiq. Fixed by hand in the same pass.
A content check is hard to do without false positives (topic ≠ keyword), so this is recorded
rather than gated; the cheap mitigation is that hook messages already carry the remedy inline,
so the pointer is depth, not the whole answer.

### P2 · Layer 1+7 — `/web-design-guidelines` fetches unpinned third-party instructions
**The plugin ships zero of the "100+ rules" it advertised.** `web-design-guidelines/SKILL.md` is 81
lines with no `rules/` and no `references/`; it fetches its rule set — *and its output format* — at
run time from
`https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`.

This contradicts two of the repo's own rules at once:

- **Pin-don't-float.** `std-infrastructure`: *"Pin every version. `latest` is never allowed in a
  committed file."* The URL targets `main`, and the skill said *"Fetch the **latest** guidelines"* /
  *"Fetch **fresh** guidelines before each review."* Two reviews of the same file can disagree with
  no diff between them.
- **An instruction source is not a library.** `mcp-install-gate.py` exists so *a human picks* an
  instruction source. This fetches rules **and output-format instructions** from a third-party repo
  on every run, ungated — a wider hole than the one the plugin built a gate for, one directory over.

**Mitigated already** (these needed no decision): the skill now **fails closed** — if the fetch
fails it must say so and use the pinned local fallback rather than reviewing from training data,
which was the live hazard (a `file:line` review attributed to a source it never opened is
unfalsifiable by the reader); house conventions **win** where upstream disagrees; every finding must
**name its source**; and CLAUDE.md, the README and the skill's own description no longer claim 100+
shipped rules.

**The decision is the maintainer's**, because the skill's *purpose* is the thing the rule forbids:
1. **Pin to a SHA** — reproducible and reviewable, but stale until someone bumps it, which defeats
   "latest guidelines".
2. **Vendor the rules** into `rules/` — fully pinned, house-reviewable, at the cost of a fork to
   maintain (and a licence check this loop cannot make).
3. **Keep floating, consciously** — accept unreviewed third-party instructions, and add a gate/notice
   so it is a decision rather than an accident.

**A gate was written and withheld.** A detector for committed floating raw URLs
(`raw.githubusercontent.com/.../{main,master,HEAD,latest}/`) matches **exactly one** file and
correctly ignores the repo's 8 ordinary `github.com` documentation links — it is precise and ready.
It is not shipped because it would fail on a defect only option 1/2/3 can resolve, and a red suite
on an unresolvable finding is how gates become noise. Ship it with the decision.

### P3 · Layer 1 — npm or pnpm? The repo runs one and documents the other
CLAUDE.md pins **no JS package manager**. The repo then splits:
`std-infrastructure/references/ci-pipeline.md` — **what CI actually runs** — uses **npm** (`npm ci`,
`npx tsc --noEmit`, `npx eslint .`, `npm audit`), while `toolchain`, `monorepo-architect` and
several references use **pnpm**. `toolchain`'s own example block mixed both on adjacent lines, under
the heading *"CI and your laptop must run the same commands."*

**Mitigated without deciding it** (the decision is the maintainer's, like the React version and
ActiveJob): the runner now follows **the lockfile** — `package-lock.json` → `npx`,
`pnpm-lock.yaml` → `pnpm exec`, `yarn.lock` → `yarn` — which is deterministic and needs no pin, and
*"if the lockfile and CI disagree, that is the finding."*

**The decision still wants making**, because the two are not equivalent: pnpm's non-flat
`node_modules` and workspace protocol are the usual reason a monorepo picks it, and this repo ships
a `monorepo-architect` skill. Whichever is chosen, `ci-pipeline.md` and `toolchain` must name the
same one — CI parity is `toolchain`'s entire thesis.

### P3 · Layer 1 — React is pinned for one of three React platforms
`std-nextjs:21` states **"React 19 minimum"**. `std-reactjs` (Vite SPA) and `std-react-native` pin
**no React version at all**, and nothing pins a React Native version either — while
`react-native-best-practices` ships `react-compiler-*` and `expo-image` rules that assume a
Compiler-era, Expo-era RN.

The cost is visible in the repo's own words. `composition-patterns/rules/react19-no-forwardref.md`
opens with *"⚠️ **React 19+ only.** Skip this if you're on React 18 or earlier"* — it hedges
because the repo does not say, and `std-nextjs`'s own principle is that *"guidance that does not
say which major it means is guidance you cannot check."* Meanwhile `rerender-memo`'s Compiler
caveat turns on a **build** decision (is the Compiler enabled) rather than a version, which is a
second axis nobody states.

**Maintainer's call, not the loop's** — same treatment as ActiveJob vs `Sidekiq::Job`. Inventing
"std-reactjs pins React 19" would be this loop deciding a version policy for a stack it does not
own, and RN's React lags web, so the Next.js answer does not transfer. The three rules-skills now
say *read `package.json`* rather than assuming.

**A gate was considered and declined.** "Every `React \d+` must equal the pinned major" flags
**correct prose**: `react19-no-forwardref` says "React 18" legitimately, explaining what changed.
Measured — 2 of 21 occurrences are that shape. Same trap as the market-research gate: the
correction contains the words the gate looks for. Not mechanically decidable; recorded instead.

### P3 · Layer 1 — the repo has not decided ActiveJob vs `Sidekiq::Job`
5 files use `< ApplicationJob`, 3 use `include Sidekiq::Job`; CLAUDE.md commits to Sidekiq but
not to an API. The two differ in retry semantics (`retry_on` **stacks** on Sidekiq's retries),
overhead (*"about 30% overhead"*), and argument serialization (GlobalID re-queries a row that may
have changed between enqueue and run). `std-error-handling/references/background-jobs.md`
documents the tradeoff and recommends native; the decision belongs in CLAUDE.md and converting
the existing examples is a mechanical follow-up — **maintainer's call, not the loop's.**

### ~~P3 · Layer 1 — oversized bodies~~ — **CLOSED** *2026-07-15*
`deploy` 357→232 · `doc-generator` 334→50 · `test-generator` 316→215 · `onboarding` 304 **kept**
(read once end-to-end; 1% over is not a signal). Two of the three splits were really
*de-duplications* — `deploy`'s frontend half and `test-generator`'s web half were drifted copies
of references that already owned them. **Check for a duplicate before splitting**: half the work
was deleting, not moving.

### P3 · Layer 1 — sizing residue: references (6 files)
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

## This loop's own defect rate (Ch. 22 — audit your own system)

Five defects traced to this loop's own output, all found by the same lens it applies to the plugin.
Recorded because the rate matters more than any one of them, and because a later iteration should
assume it is still non-zero:

| # | Defect | How it surfaced |
|---|---|---|
| 1 | `test_contrast_table_matches_the_tokens` read **one file**; `theme-presets.md` kept 13 failing pairs | Accident — auditing `theming` |
| 2 | `request-tracing.md` still claimed a hook check **I had removed** | Accident — auditing `log-search` |
| 3 | Asserted **pnpm** in `refactor-specialist`; repo pins no package manager, CI runs npm | Accident — auditing `toolchain` |
| 4 | `i18n-checker.py` *"warns on this"* named 3 targets; it covers **2** (no `.rb`) | **Deliberate self-audit** |
| 5 | Asserted *"roughly 3-4x"* gzip ratio **after saying I would not** | **Deliberate self-audit** |

**All five are scope errors, not fabrications** — "I claimed more coverage than I had", which is the
same defect the sweep keeps finding in the plugin. Three surfaced by luck; only the deliberate pass
found the last two, which is the argument for running it again.

**What did not fail:** every API claim traced to a verified owner; every hook-behaviour claim was
true of the hook as it stands. The errors cluster in *claims about coverage*, not claims about
facts — so that is where the next self-audit should look first.

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
