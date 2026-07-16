---
name: atomic-design
description: |
  Atomic Design methodology for component hierarchy across Phlex (Rails),
  ReactJS Vite SPA, Next.js App Router, and React Native. Covers atoms,
  molecules, organisms, templates, and pages with composition rules.
  Triggers on "atomic design", "component hierarchy", "atom component",
  "molecule component", "organism component", "design system structure",
  or "component organization".
model: sonnet
---

# Atomic Design Methodology

Systematic component hierarchy based on Brad Frost's Atomic Design: atoms -> molecules -> organisms -> templates -> pages. Applied across all 4 frontend platforms.

## When to Apply

Reference these guidelines when:
- Creating new UI components (determine correct atomic level)
- Reviewing component composition (verify import rules)
- Organizing component directories across platforms
- Building or extending a design system / component library
- Deciding where data fetching logic belongs

## Rule Categories

| # | Category | Prefix | Priority | Description |
|---|----------|--------|----------|-------------|
| 1 | Atoms | `atom-` | HIGH | Indivisible primitive components |
| 2 | Molecules | `molecule-` | HIGH | Simple compositions of atoms |
| 3 | Organisms | `organism-` | MEDIUM | Complex UI sections |
| 4 | Templates | `template-` | MEDIUM | Page-level layout skeletons |
| 5 | Pages | `page-` | MEDIUM | Templates with real data |
| 6 | Organization | `org-` | MEDIUM | Directory structure &amp; naming |

## Quick Reference -- All Rules

### Atoms (HIGH)
- `atom-standalone-primitives` -- Atoms are indivisible, cannot compose other atoms
- `atom-theming-tokens` -- Atoms must consume design tokens, never hardcode values

### Molecules (HIGH)
- `molecule-atom-composition` -- Molecules compose only atoms
- `molecule-single-responsibility` -- Each molecule = one cohesive function

### Organisms (MEDIUM)
- `organism-section-boundary` -- Organisms = distinct interface sections
- `organism-data-awareness` -- Organisms are the lowest data-aware level

### Templates (MEDIUM)
- `template-layout-skeleton` -- Templates define layout without real content

### Pages (MEDIUM)
- `page-template-instance` -- Pages = templates + real data

### Organization (MEDIUM)
- `org-directory-structure` -- Directory trees for all 4 platforms
- `org-naming-conventions` -- Naming conventions per platform

## Composition Rules

| Level | Can Import From | Data-Aware? | Example |
|-------|----------------|-------------|---------|
| Atoms | Nothing (standalone) | No | Button, Input, Label, Icon |
| Molecules | Atoms only | No | SearchForm, FormField, NavLink |
| Organisms | Atoms + Molecules | Yes (props/hooks) | Header, ProductGrid, Sidebar |
| Templates | Atoms + Molecules + Organisms | Layout only | DashboardLayout, AuthLayout |
| Pages | Everything | Full data | Articles::Index, DashboardPage |

## Deep guides (read on demand, do not preload)

Every rule id listed above maps to a self-contained file at `rules/<rule-id>.md`, each with its
own bad/good code pair for all 4 platforms.

**Read only the rule file matching your task** — not the set:

```
rules/<rule-id>.md
```

### Owned elsewhere

This skill owns the **hierarchy** — which level a component belongs at, and what may compose what.
It does not own the tokens those components style with:

- **`std-design-system`** is scoped to the same files you will be editing (`**/components/ui/**`,
  `**/app/components/**/*.rb`, `**/styles/**`) and owns the token rules.
  `rules/atom-theming-tokens.md` is the hierarchy-side rule; the **registry of names that actually
  exist** is `@skills/theming/references/platform-integration.md`. A class naming an unregistered
  token compiles to no CSS at all — silently — so "uses a token" and "uses a *registered* token"
  are different claims, and only the second one renders.

Loading one ~60-line rule beats skimming the whole directory. Do not preload it.

The rules answer "how do I write this level correctly?". These references answer the questions that
come before and after that — read one only when the question is yours:

| Reference | Read it when |
|-----------|--------------|
| `references/choosing-the-atomic-level.md` | You don't yet know which level a component is. Decision tree, classification questions, data/state boundaries, the standard atom and molecule catalogs, and whether a level changes when you port across platforms. |
| `references/diagnosing-misplaced-components.md` | The hierarchy exists but feels wrong — an import goes the wrong way, a component won't reuse, an atom has too many props. Symptom → diagnosis → fix. |
| `references/nextjs-server-client-boundary.md` | **Next.js only.** Deciding `"use client"` placement, whether an organism should `await` or use a hook, or `layout.tsx` vs an Atomic Design template. Skip on Vite, Phlex, and React Native. |
