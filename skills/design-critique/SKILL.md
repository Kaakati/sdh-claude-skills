---
name: design-critique
description: |
  Visual design quality review using Nielsen's heuristics, visual hierarchy analysis,
  design token compliance checking, narrative/storytelling UX evaluation,
  cross-platform consistency evaluation, a per-role lens for multi-role products,
  and a drill-down navigation check (area budget, areas-only sidebar, location cues).
  Triggers on "design critique", "design review", "visual review", "UI critique",
  "heuristic review", "design quality", "visual quality audit", "storytelling",
  "narrative UX", "StoryBrand", "what each role sees", "navigation review",
  "sidebar clutter", "drill-down", or "breadcrumbs".
model: opus
agent: design-critique
context: fork
---

# Design Critique Partner

Routes to the `design-critique` agent for autonomous visual quality review.

## What It Does

The design-critique agent performs a 9-step review protocol:

1. **Scope identification** — Identifies components and screens to review
2. **Heuristic evaluation** — Scores against Nielsen's 10 heuristics (1-5 per heuristic)
3. **Visual hierarchy analysis** — Typography, spacing, color weight, alignment, grouping
4. **Design token compliance** — Greps for hardcoded values, arbitrary Tailwind classes
5. **Cross-platform consistency** — Compares implementations across web, mobile, Phlex
6. **WCAG spot check** — Color contrast, focus indicators, touch targets (44×44 on touch; on web
   24×24 CSS px is the WCAG 2.5.8 floor and 32×32 the house target), semantic HTML
7. **Narrative & emotional arc** — Scores the 8-point storytelling checklist (arc, hero
   framing, pacing, first value, emotional beats, continuity, resolution, restraint) per
   `@skills/ui-ux-patterns/references/storytelling-ui.md`
8. **Role lens** — Only when the product has more than one role: walks the per-role table
   (landing page, sidebar order, primary actions), re-checks visibility of system status and
   recognition over recall for each role, and applies the three-state rule to every gated
   control, per `@skills/ui-ux-patterns/references/role-based-ux.md`. Each state's treatment
   (disabled with a reason, read-only, locked, 403 vs 404, empty, masked) is judged per
   `@skills/ui-ux-patterns/references/role-based-ux-states.md`, and the admin screens where access
   is granted (role catalog, matrix editor, invites, last-owner guard, audit log) per
   `@skills/ui-ux-patterns/references/role-management-ux.md`
9. **Navigation structure (drill-down)** — Per role: areas against the budget (at most 7 on
   desktop, 3–5 native tabs; exceeding it triggers a design review), a global sidebar holding
   areas only, section nav inside the area's own layout, location cues at every level,
   breadcrumbs from level 3 built from `ancestors`, search as the second way (a palette is never
   the only one), and no hidden desktop navigation, per
   `@skills/ui-ux-patterns/references/drill-down-navigation.md`. Existing screens are scored at
   full severity, exactly like new ones

## Output

A structured critique report with:
- Heuristic scores (overall X.X / 5.0)
- Narrative & emotional-arc score (storytelling checklist, X / 16)
- Role lens table (per role: landing page, sidebar order, status visibility, primary action,
  three-state violations) — or "not applicable — one role"
- Navigation structure table (per role: areas against the budget, what the global sidebar holds,
  section nav, missing location cues, breadcrumbs, second way, violations)
- Findings table (severity, file:line, issue, redesign direction)
- Positive patterns (what works well)
- Prioritized recommendations

## When to Use

- After implementing a new feature or screen
- Before design review or sprint demo
- When onboarding a new design system
- During periodic design quality audits
- When cross-platform consistency is a concern
- When menus and sidebars feel cluttered, or before migrating an existing product's navigation to
  drill-down
