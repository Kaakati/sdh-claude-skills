---
name: design-to-code
description: |
  Translate design specifications into production code with design token extraction,
  component decomposition, responsive implementation, and accessibility layers.
  Routes to the design-system-architect agent for comprehensive translation.
  Triggers on "design to code", "implement this design", "code this design",
  "translate design", "build from design", "design implementation",
  or "convert design to code".
model: sonnet
agent: design-system-architect
context: fork
---

# Design-to-Code Translator

Routes to the `design-system-architect` agent for comprehensive design-to-code translation.

## What It Does

The design-system-architect agent follows its 6-step protocol to:

1. **Audit current tokens** — Reads existing design token definitions
2. **Analyze component inventory** — Maps existing components across platforms
3. **Define/verify token architecture** — Ensures all required tokens exist
4. **Establish grid system** — Validates layout foundations
5. **Produce component spec matrix** — Documents 30+ components with variants, props, a11y, plus a
   navigation spec (area budget per role, an areas-only `AppSidebar`, the shared command palette
   organism) per `@skills/ui-ux-patterns/references/drill-down-navigation.md`
6. **Cross-reference quality** — Validates WCAG 2.2, motion, dark mode, touch targets (44×44 on
   touch; on web the house's 32×32, above WCAG 2.5.8's 24×24 floor)

## Translation Workflow

Reference `references/translation-workflow.md` for the detailed methodology:

1. **Input**: Design spec (Figma link, screenshots, written spec, or existing components to audit)
2. **Token extraction**: Colors, typography, spacing, shadows, transitions
3. **Component decomposition**: Break UI into atomic design levels; map designed navigation to
   areas, sections and levels — a designed global sidebar with nested sections is a finding to
   raise, not a layout to copy
4. **Code generation**: Platform-specific implementation (Phlex, React, React Native)
5. **Responsive layer**: Breakpoint-aware layouts
6. **Accessibility layer**: ARIA, keyboard, focus management
7. **Output**: Production-ready components with design tokens

## When to Use

- Translating a Figma design into code across platforms
- Building a new design system from scratch
- Auditing an existing design system for completeness
- Ensuring cross-platform visual consistency
- Generating a design system specification document

## Full References

- `references/translation-workflow.md` — Detailed translation methodology
