---
name: std-design-system
description: Design system / token standards — color, typography, spacing, motion tokens; component styling; cross-platform consistency. Use when styling components or defining tokens.
paths:
  - "**/styles/**"
  - "**/components/ui/**"
  - "**/src/theme/**"
  - "**/app/components/**/*.rb"
  - "**/tailwind.config.*"
  - "**/globals.css"
---

# Design System Standards

Apple-level design token conventions for cross-platform visual consistency. **All visual properties
derive from tokens — no hardcoded values.**

## The four rules that apply everywhere

1. **No hardcoded colors** in component files — no hex, no `rgb()`, no `hsl()` literals. Consume
   tokens via utility classes (`bg-primary`, `text-foreground`) or CSS custom properties.
2. **No arbitrary Tailwind values** — `p-[13px]`, `text-[17px]`, `bg-[#ff0000]` are all rejected.
   Snap to the nearest scale token. If no token fits, question the design first.
3. **Every interactive element has a visible focus indicator** — 2px ring, ≥3:1 contrast, using the
   `ring-ring` token and the `focus-visible:` prefix (never bare `focus:`).
4. **Every animation has a reduced-motion path** — `motion-safe:` on the web, `useReducedMotion()`
   in JS-driven animation.

```tsx
// The canonical component line: tokens, focus-visible, guarded motion.
className="bg-primary text-primary-foreground motion-safe:transition-colors motion-safe:duration-150
           focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
```

## Token naming

All CSS custom properties follow `--{category}-{name}`:

| Category   | Pattern                | Examples                                            |
|------------|------------------------|-----------------------------------------------------|
| Colors     | Semantic name          | `--primary`, `--secondary`, `--accent`, `--success` |
| Foreground | `{color}-foreground`   | `--primary-foreground`, `--error-foreground`        |
| Surface    | Surface role           | `--background`, `--card`, `--popover`, `--muted`    |
| Border     | Border role            | `--border`, `--input`, `--ring`                     |

Colors are declared as **space-separated HSL channels with no `hsl()` wrapper**, so Tailwind's
opacity modifier works. Every background token has a contrast-verified `-foreground` pair.

```css
--primary: 222.2 47.4% 11.2%;              /* definition */
background-color: hsl(var(--primary) / 0.5);  /* consumption — Tailwind: bg-primary/50 */
```

Tokens live in `:root`; dark mode overrides use the **`.dark` class**, not
`@media (prefers-color-scheme)`.

## Color

- **Contrast**: ≥4.5:1 for normal text; ≥3:1 for large text (18px+, or 14px+ bold) and UI components.
- **Never convey meaning through color alone** — semantic colors pair with an icon and a text label.
- Required palettes: Core (`primary`/`secondary`/`accent`), Neutral (`neutral`/`muted`/`background`/
  `foreground`), Semantic (`success`/`warning`/`error`/`info`), Surface (`card`/`popover`), Border
  (`border`/`input`/`ring`).

## Typography

Use Tailwind's built-in scale exclusively — no arbitrary font sizes.

| `text-xs` | `text-sm` | `text-base` | `text-lg` | `text-xl` | `text-2xl` | `text-3xl` | `text-4xl` | `text-5xl` |
|-----------|-----------|-------------|-----------|-----------|------------|------------|------------|------------|
| 12px      | 14px      | 16px (body) | 18px      | 20px      | 24px       | 30px       | 36px       | 48px       |

- **Maximum 2 font families** per project (sans + mono, or sans + serif).
- **Weights**: 300, 400, 500, 600, 700 only.
- **Line height**: `leading-tight` (1.25), `leading-snug` (1.375), `leading-normal` (1.5),
  `leading-relaxed` (1.625).

## Spacing

All spacing is a multiple of **4px**, from the Tailwind scale.

| Scale       | Value   | Usage                                   |
|-------------|---------|-----------------------------------------|
| `0.5`-`1.5` | 2-6px   | Tight inner padding, icon gaps           |
| `2`-`4`     | 8-16px  | Standard padding, element gaps           |
| `5`-`8`     | 20-32px | Section padding, card padding            |
| `10`-`16`   | 40-64px | Major section separation                 |
| `20`-`24`   | 80-96px | Page-level spacing, hero padding         |

Padding by atomic level: Atoms `p-1`-`p-3` · Molecules `p-2`-`p-4` · Organisms `p-4`-`p-8` ·
Templates/Pages `p-6`-`p-16`.

## Motion

Durations: `duration-75` (instant feedback) · `duration-100` (hover) · `duration-150` (default) ·
`duration-200` (press, focus) · `duration-300` (dropdowns, tooltips) · `duration-500` (page
transitions, modals). **Ceiling is 500ms** — longer feels sluggish.

Easing: `ease-out` for entering, `ease-in` for exiting, `ease-in-out` as default,
`cubic-bezier(0.34, 1.56, 0.64, 1)` spring for tactile elements (toggles, modals).

## Component styling

Multi-variant components use `class_variants` (Ruby/Phlex) or `cva` (TypeScript) — never hand-rolled
conditional string concatenation. Five standard axes: `size` (`sm`/`md`/`lg`/`xl`), `variant`
(`primary`/`secondary`/`outline`/`ghost`/`destructive`), `state` (`default`/`hover`/`active`/
`disabled`/`loading`), `radius` (`none`/`sm`/`md`/`lg`/`full`), `density` (`compact`/`default`/
`comfortable`).

## Cross-platform

| Platform            | Token source           | Consumption                         |
|---------------------|------------------------|-------------------------------------|
| Vite SPA / Next.js  | CSS custom properties  | Tailwind utility classes            |
| React Native        | Theme context          | `useTheme()` hook + `StyleSheet`    |
| Phlex (Rails)       | CSS custom properties  | Tailwind classes + `class_variants` |

Token **names**, the 4px spacing base, and type scale ratios are identical on every platform. Touch
targets: 44×44px minimum on mobile, 32×32px on web (WCAG 2.5.8).

## Deep guides (read on demand, do not preload)

- Adding a color token, Tailwind wiring, dark mode, contrast verification → `references/defining-tokens.md`
- `cva` / `class_variants` components, focus rings, arbitrary-value escape hatch → `references/component-variants.md`
- Shared token package, React Native theme, touch targets, parity tests → `references/cross-platform-parity.md`
- Framer Motion, Reanimated, `prefers-reduced-motion`, animation budgets → `references/motion.md`
