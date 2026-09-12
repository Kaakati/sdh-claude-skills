---
name: theming
description: |
  Cross-platform theming and design token system for Phlex (Rails), ReactJS Vite SPA,
  Next.js App Router, and React Native. Covers CSS custom properties holding complete hsl()
  values, Tailwind v4 @theme inline and @custom-variant dark, the shadcn/ui token aliases
  (destructive, sidebar-*, chart-1..5) mapped onto house roles, dark/light mode, WCAG AA
  contrast, and per-platform token consumption.
  Triggers on "design tokens", "theming", "dark mode", "color system",
  "theme provider", "CSS variables", "design system", "grid system",
  "design system architect", "spacing system", "token architecture", "chart colors",
  "shadcn tokens", or "globals.css".
model: sonnet
---

# Theming & Design Tokens

Cross-platform theming system providing consistent design tokens across all frontend platforms: Phlex (Rails), ReactJS (Vite SPA), Next.js (App Router), and React Native.

## When to Apply

Reference these guidelines when:
- Setting up or modifying a design token system (colors, typography, spacing)
- Implementing dark/light mode switching
- Creating new UI components that consume visual tokens
- Reviewing color contrast for WCAG AA compliance
- Integrating Tailwind CSS with custom themes
- Building a React Native ThemeProvider

## Platform Guides

| Platform | Token Consumption | Reference |
|----------|------------------|-----------|
| Tailwind CSS (Vite / Next.js) | Complete `hsl()` values in `:root`/`.dark`, `@theme inline { --color-x: var(--x) }`, `@custom-variant dark (&:is(.dark *))`, the shadcn/ui alias block, `next-themes` (Next.js) or the house provider (Vite) | `references/platform-integration.md` |
| React Native | `ThemeProvider` context, `useTheme()` hook, `StyleSheet` with tokens | `references/platform-integration.md` |
| Phlex (Rails) | Global CSS custom properties, Tailwind utility classes, `class_variants` | `references/platform-integration.md` |

## Quick Reference

### Token Categories

| Category | Examples | Reference |
|----------|----------|-----------|
| Colors | primary, secondary, accent, neutral, semantic (success/warning/error/info), foreground convention | `references/design-tokens.md` |
| Chart | `chart-1`…`chart-5`: categorical series, fixed order, measured against every preset surface | `references/design-tokens.md` |
| shadcn/ui aliases | `destructive` → error, `sidebar-*` → card/primary/accent/border/ring, as `var()` references (web only) | `references/design-tokens.md`, `references/platform-integration.md` |
| Typography | Font families, size scale (xs-5xl), weights, line heights | `references/design-tokens.md` |
| Spacing | 4px base unit, scale from 0.5 to 96 | `references/design-tokens.md` |
| Borders | Border radius scale, border widths | `references/design-tokens.md` |
| Shadows | Elevation scale (sm, md, lg, xl, 2xl) | `references/design-tokens.md` |
| Transitions | Duration scale, easing functions | `references/design-tokens.md` |
| Dark Mode | `prefers-color-scheme`, class toggle, system detection | `references/platform-integration.md` |

### Ready-to-Use Presets

| Preset | Style | Reference |
|--------|-------|-----------|
| Corporate | Professional blues, conservative typography | `references/theme-presets.md` |
| Modern | Vibrant gradients, rounded corners, Inter font | `references/theme-presets.md` |
| Minimal | Monochrome palette, tight spacing, system fonts | `references/theme-presets.md` |

## Component Libraries

shadcn/ui is the component standard for Next.js and the Vite SPA, and it consumes these tokens
through the alias block. Everything else about it is owned by the `std-shadcn-ui` skill: bases,
the CLI, forms, toasts, charts, and the edits aliasing cannot make. See
`@skills/std-shadcn-ui/references/components-and-blocks.md` and
`@skills/std-shadcn-ui/references/cli-and-registry.md`. Do not restate it here. React Native keeps
the house `ThemeProvider`, since shadcn/ui is web-only.

## Full References

- `references/design-tokens.md` -- Complete design token specification
- `references/platform-integration.md` -- Per-platform integration guides
- `references/theme-presets.md` -- Ready-to-use theme presets
