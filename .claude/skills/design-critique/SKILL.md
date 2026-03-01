---
name: design-critique
description: |
  Visual design quality review using Nielsen's heuristics, visual hierarchy analysis,
  design token compliance checking, and cross-platform consistency evaluation.
  Triggers on "design critique", "design review", "visual review", "UI critique",
  "heuristic review", "design quality", or "visual quality audit".
model: opus
agent: design-critique
---

# Design Critique Partner

Routes to the `design-critique` agent for autonomous visual quality review.

## What It Does

The design-critique agent performs a 6-step review protocol:

1. **Scope identification** — Identifies components and screens to review
2. **Heuristic evaluation** — Scores against Nielsen's 10 heuristics (1-5 per heuristic)
3. **Visual hierarchy analysis** — Typography, spacing, color weight, alignment, grouping
4. **Design token compliance** — Greps for hardcoded values, arbitrary Tailwind classes
5. **Cross-platform consistency** — Compares implementations across web, mobile, Phlex
6. **WCAG spot check** — Color contrast, focus indicators, touch targets, semantic HTML

## Output

A structured critique report with:
- Heuristic scores (overall X.X / 5.0)
- Findings table (severity, file:line, issue, redesign direction)
- Positive patterns (what works well)
- Prioritized recommendations

## When to Use

- After implementing a new feature or screen
- Before design review or sprint demo
- When onboarding a new design system
- During periodic design quality audits
- When cross-platform consistency is a concern
