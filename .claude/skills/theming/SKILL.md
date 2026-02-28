---
name: theming
description: |
  Cross-platform theming and design token system for Phlex (Rails), ReactJS Vite SPA,
  Next.js App Router, and React Native. Covers CSS custom properties, Tailwind v4 @theme,
  dark/light mode, WCAG AA contrast, and per-platform token consumption.
  Triggers on "design tokens", "theming", "dark mode", "color system",
  "theme provider", "CSS variables", or "design system".
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
| Tailwind CSS (Vite / Next.js) | `@theme` (v4) or `tailwind.config.ts` (v3), CSS custom properties, `dark:` variant | `references/platform-integration.md` |
| React Native | `ThemeProvider` context, `useTheme()` hook, `StyleSheet` with tokens | `references/platform-integration.md` |
| Phlex (Rails) | Global CSS custom properties, Tailwind utility classes, `class_variants` | `references/platform-integration.md` |

## Quick Reference

### Token Categories

| Category | Examples | Reference |
|----------|----------|-----------|
| Colors | primary, secondary, accent, neutral, semantic (success/warning/error/info), foreground convention | `references/design-tokens.md` |
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

## Full References

- `references/design-tokens.md` -- Complete design token specification
- `references/platform-integration.md` -- Per-platform integration guides
- `references/theme-presets.md` -- Ready-to-use theme presets
