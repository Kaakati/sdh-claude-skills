---
name: web-design-guidelines
description: |
  Web interface design guidelines with 100+ rules for accessibility,
  performance, and UX compliance. Use when reviewing UI code, auditing
  design implementation, checking accessibility, or validating web UX.
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

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

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
