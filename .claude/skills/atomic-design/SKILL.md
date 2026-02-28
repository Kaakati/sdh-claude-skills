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

## Full Reference

For the complete guide with all rules and code examples: `references/full-guide.md`
