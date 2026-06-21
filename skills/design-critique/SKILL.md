---
name: design-critique
description: |
  Visual design quality review using Nielsen's heuristics, visual hierarchy analysis,
  design token compliance checking, narrative/storytelling UX evaluation, and
  cross-platform consistency evaluation.
  Triggers on "design critique", "design review", "visual review", "UI critique",
  "heuristic review", "design quality", "visual quality audit", "storytelling",
  "narrative UX", or "StoryBrand".
model: opus
agent: design-critique
context: fork
---

# Design Critique Partner

Routes to the `design-critique` agent for autonomous visual quality review.

## What It Does

The design-critique agent performs a 7-step review protocol:

1. **Scope identification** — Identifies components and screens to review
2. **Heuristic evaluation** — Scores against Nielsen's 10 heuristics (1-5 per heuristic)
3. **Visual hierarchy analysis** — Typography, spacing, color weight, alignment, grouping
4. **Design token compliance** — Greps for hardcoded values, arbitrary Tailwind classes
5. **Cross-platform consistency** — Compares implementations across web, mobile, Phlex
6. **WCAG spot check** — Color contrast, focus indicators, touch targets, semantic HTML
7. **Narrative & emotional arc** — Scores the 8-point storytelling checklist (arc, hero
   framing, pacing, first value, emotional beats, continuity, resolution, restraint) per
   `@skills/ui-ux-patterns/references/storytelling-ui.md`

## Output

A structured critique report with:
- Heuristic scores (overall X.X / 5.0)
- Narrative & emotional-arc score (storytelling checklist, X / 16)
- Findings table (severity, file:line, issue, redesign direction)
- Positive patterns (what works well)
- Prioritized recommendations

## When to Use

- After implementing a new feature or screen
- Before design review or sprint demo
- When onboarding a new design system
- During periodic design quality audits
- When cross-platform consistency is a concern
