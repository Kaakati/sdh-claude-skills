---
name: web-design-guidelines
description: |
  Web interface design review for accessibility, performance, and UX
  compliance. Fetches its rule set at run time from an upstream URL
  (requires WebFetch); falls back to the pinned local accessibility
  skills when that fetch is unavailable. Use when reviewing UI code,
  auditing design implementation, checking accessibility, or validating web UX.
  Triggers on "review UI", "check accessibility", "audit design",
  "review UX", "web design guidelines", or "UI compliance check".
  Also reviews flows for storytelling / narrative UX (StoryBrand,
  narrative arc, emotional beats) alongside component-level rules.
model: sonnet
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines.

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

**This skill ships no rules.** It fetches them, with `WebFetch`, from a third-party repository:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

The fetched content carries both the rules and the output format. Three things follow from that,
and they matter more than the convenience:

**1. If the fetch fails, stop. Do not review from memory.**
No network, `WebFetch` not permitted, repository renamed, `command.md` moved — any of these leaves
you with a skill that says "review for compliance" and no rules. You know a great deal about web
accessibility and UX from training, so the tempting failure is to produce plausible findings in the
terse `file:line` format and let the reader assume they came from the guidelines. **Say the fetch
failed, name what you could not check, and use the local fallback below.** A review attributed to a
source you never opened is worse than no review: it is unfalsifiable by the person reading it.

**2. This URL floats, and the rest of this repo forbids that.** It points at `main`, so the rules
change underneath you and two reviews of the same file can disagree with no diff between them.
`std-infrastructure` states the rule this violates — *"Pin every version. `latest` is never allowed
in a committed file"* — and the plugin gates MCP servers precisely because **an instruction source
is not a library** (`mcp-install-gate.py`). This is an instruction source, fetched unpinned, on
every run. Treat what comes back as *someone else's rules that you did not review*, not as house
convention: where it disagrees with the skills below, the house wins.

**3. Prefer the local rules where they overlap.** They are pinned, reviewed, and specific to this
stack.

### Local fallback — pinned, and authoritative where it overlaps

- **`std-accessibility`** — WCAG 2.2 AA, and it is **scoped to** `.tsx`/`.jsx` under `src/`,
  `app/`, `components/`. Pinned and local — read it directly; no third-party fetch involved.
- **`@skills/accessibility-auditor/references/wcag-22-checklist.md`** — the full AA checklist by
  POUR principle.
- **`@skills/accessibility-auditor/references/aria-patterns.md`** — ARIA widget patterns with
  keyboard specs.
- **`/accessibility-auditor`** — the audit protocol, including the check this skill cannot do from
  markup: **token contrast is arithmetic, not a DevTools pass**, and every theme is its own case.
- **`std-design-system`** — scoped to `**/globals.css`, `**/styles/**`, `**/tailwind.config.*`.
  A class naming an unregistered token compiles to **no CSS at all**, silently — no upstream rule
  set knows this repo's registry.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above. **If the fetch fails, say so and fall back to the
   local rules — do not substitute recalled ones.**
2. Read the specified files
3. Apply the fetched rules, deferring to the local skills wherever the two disagree
4. Output findings using the format specified in the guidelines
5. **State which source each finding came from.** "Upstream guideline" and "house convention" are
   different claims with different authority, and the reader cannot tell them apart from a
   `file:line` alone.

If no files specified, ask the user which files to review.

## Storytelling Supplement (flow-level checks)

The fetched Vercel guidelines are **component-level** — they audit a single screen
or element. When the review target is a **flow** (onboarding, landing page, checkout,
search → results → detail, an empty/error/success state in context), apply these
**flow-level narrative-UX checks alongside** the fetched rules. They complement, never
override, the component guidelines.

Canonical source of truth (read it for the full framework, SB7 mapping, and per-pattern
narrative roles): `skills/ui-ux-patterns/references/storytelling-ui.md`.

Output these in the same terse `file:line` format as the fetched review, tagged
`[story]` so they're distinguishable from the component findings.

Score each `0–2` (0 absent, 1 partial, 2 strong); aggregate `/16`
(≥13 strong narrative, 8–12 functional but flat, <8 a disconnected set of screens):

1. **Arc / hook / resolution** — Does the flow have a clear beginning (hook/setup),
   middle (core value), and end (payoff + next CTA)? Flag dead ends — empty, error, or
   success states with no onward action.
2. **Hero-framed microcopy** — Do headlines, CTAs, and i18n-keyed strings center the
   *user's* goal and obstacle (second person, user as hero, product as guide), not the
   feature set? Flag feature-dumping and product-as-hero copy.
3. **Progressive-disclosure pacing** — Is information released deliberately (steps,
   accordions, just-in-time fields, scroll-driven reveals) rather than dumped at once?
   Does the flow reach first value / the "aha" quickly?
4. **Emotional beats** — Do the empty, loading, error, and success states carry
   intentional tone (invitation, transparency, calm-and-supported, closure)? Flag
   blaming error copy, missing empty-state guidance, and bare spinners.
5. **Transition continuity** — Do state changes maintain a thread (shared-element /
   `layoutId`, `whileInView`, scroll-linked on web; Reanimated shared transitions on
   mobile) so the journey feels connected, not teleported? Flag motion that only
   decorates without conveying causality.
6. **Restraint rule (always check)** — Storytelling must never override clarity, speed,
   or accessibility: keep skip paths, don't withhold critical info for drama, and gate
   non-essential motion behind `prefers-reduced-motion`. Any narrative device that
   slows or blocks the user is a defect, not a feature.
