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
   `ring-ring` token and the `focus-visible:` prefix (never bare `focus:`). No opacity modifier on
   the ring (`ring-ring/50`) unless the active preset measures ≥3:1 with it — it does not in every
   preset.
4. **Every animation has a reduced-motion path** — `motion-safe:` on the web, `useReducedMotion()`
   in JS-driven animation, and the global `prefers-reduced-motion` backstop in every web token
   stylesheet (the only path vendored shadcn/ui primitives have).

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

Colors are declared as **complete `hsl()` values** and registered with Tailwind v4 through
**`@theme inline`**, so each utility reads the variable on the element it styles and a nested
`.dark` section re-resolves. Opacity modifiers still work (`bg-primary/50` compiles to
`color-mix()`). The numbers stay HSL because they are what the contrast table measures. Every
background token has a contrast-verified `-foreground` pair.

```css
:root { --primary: hsl(222.2 47.4% 11.2%); }        /* definition: a complete color */
@theme inline { --color-primary: var(--primary); }  /* registration: bg-primary, bg-primary/50 */
.divider { border-color: var(--primary); }          /* arbitrary CSS: var(), never hsl(var()) */
```

`hsl(var(--primary))` now wraps a color in a color. That is invalid at computed-value time, and
the property silently falls back to `unset`. Bare channels (`--primary: 222.2 47.4% 11.2%`) fail
the same way from the other side.

Tokens live in `:root`; dark mode overrides use the **`.dark` class**, not
`@media (prefers-color-scheme)`. Tailwind v4's `dark:` variant follows the media query unless the
stylesheet overrides it, so the stylesheet declares `@custom-variant dark (&:is(.dark *));`.
Without that line every `dark:` utility ignores the toggle.

## Color

- **Contrast**: ≥4.5:1 for normal text; ≥3:1 for large text (18px+, or 14px+ bold) and UI components.
- **Never convey meaning through color alone** — semantic colors pair with an icon and a text label.
- Required palettes: Core (`primary`/`secondary`/`accent`), Neutral (`neutral`/`muted`/`background`/
  `foreground`), Semantic (`success`/`warning`/`error`/`info`), Surface (`card`/`popover`), Border
  (`border`/`input`/`ring`, each ≥3:1 against `background` and `card` in both modes), Chart
  (`chart-1`…`chart-5`: categorical series, non-text, no `-foreground`, used in fixed order).
- **shadcn/ui aliases** are registered in shadcn packages (Next.js, Vite SPA). `destructive` and
  `destructive-foreground` point to `error`. `sidebar` and `sidebar-foreground` point to `card`.
  `sidebar-primary` points to `primary`, `sidebar-accent` to `accent` (each with its `-foreground`),
  `sidebar-border` to `border`, and `sidebar-ring` to `ring`. They are `var()` references, never
  copied values, so they cannot drift from the role. Code the house writes names the role
  (`bg-error`). The aliases exist so vendored shadcn source compiles unmodified. For the wiring,
  see `@skills/theming/references/platform-integration.md`; for measured pairs, see
  `@skills/theming/references/design-tokens.md`.

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

`framer-motion` drives house page and list transitions. `tw-animate-css` is allowed only as the
CSS-only enter/exit animation dependency of shadcn/ui primitives. It ships no reduced-motion rule
of its own, which is why the stylesheet backstop is mandatory.

## Component styling

Multi-variant components use `class_variants` (Ruby/Phlex) or `cva` (TypeScript) — never hand-rolled
conditional string concatenation. Five standard axes: `size` (`sm`/`md`/`lg`/`xl`), `variant`
(`primary`/`secondary`/`outline`/`ghost`/`destructive`), `state` (`default`/`hover`/`active`/
`disabled`/`loading`), `radius` (`none`/`sm`/`md`/`lg`/`full`), `density` (`compact`/`default`/
`comfortable`). Merge classes with `cn` imported from `@/lib/utils`.

Vendored shadcn/ui primitives arrive with their own variant keys and base-specific APIs. Adopting,
remapping, and keeping them mergeable is owned by the `std-shadcn-ui` skill
(`@skills/std-shadcn-ui/references/components-and-blocks.md`). Do not restate it here.

## Navigation chrome

- **Salience ladder**: global nav > section nav > breadcrumb. Local navigation never outweighs the
  global nav in size, weight or surface.
- **Selected state takes two cues**: an indicator bar or border plus weight, never color alone.
- **The desktop sidebar ships open.** Collapsing it is the person's choice, never the default.
- What the global sidebar holds, where section nav lives, drill-down levels and breadcrumbs are
  owned by `@skills/ui-ux-patterns/references/drill-down-navigation.md`. Do not restate them here.

## Cross-platform

| Platform            | Token source           | Consumption                         |
|---------------------|------------------------|-------------------------------------|
| Vite SPA / Next.js  | CSS custom properties  | Tailwind utility classes            |
| React Native        | Theme context          | `useTheme()` hook + `StyleSheet`    |
| Phlex (Rails)       | CSS custom properties  | Tailwind classes + `class_variants` |

Token **names**, the 4px spacing base, and type scale ratios are identical on every platform. The
exception is the shadcn/ui aliases: they are web wiring, and React Native reads the roles they
point to. Touch targets: 44×44px minimum on mobile and 32×32px on web are **house minimums**, set
above the 24×24 CSS px that WCAG 2.5.8 (AA) requires. Never cite them as WCAG numbers.

## What the hook enforces

`design-token-checker.py` warns, never blocks, after an edit to a component, style or token file.
Besides hex colors and arbitrary values, three checks decide what it accepts:

- **Unregistered tokens.** A color utility built on a role name (`primary`, `muted`, `error`,
  `sidebar`, … and the usual strays `danger` and `neutral`) must name a registered token, or it
  compiles to no CSS and warns: `bg-primary-600`, `bg-neutral`, `bg-danger`, `bg-sidebar-background`.
  Accepted: a registered role, with or without an opacity modifier (`bg-primary/90`); the 15
  shadcn/ui alias names (`destructive`, `destructive-foreground`, the `sidebar-*` set, …); and a
  token the same file defines (`--success-subtle: …;` then `bg-success-subtle`). The aliases are
  accepted in every package, so `bg-destructive` in a Phlex component, where no alias block exists,
  is review's catch. Palette classes (`bg-red-500`) are outside this check, not allowed by it. It is
  the only check that still runs on vendored primitives under `aliases.ui`.
- **Reduced motion** (`.tsx`, `.jsx`, `.css`, `.scss`). Movement — `animate-*`, `@keyframes`, `animation:`, transitions of transform,
  size or position, `transition` paired with a transform variant (`hover:scale-105`), smooth
  scrolling, `<motion.*>`, React Native `Animated.timing`-style calls and `LayoutAnimation`,
  Reanimated `withTiming` / `withSpring` — needs one of `motion-safe:`, `motion-reduce:`,
  `prefers-reduced-motion`, `useReducedMotion`, `reducedMotion` (Framer Motion's `MotionConfig`),
  `AccessibilityInfo.isReduceMotionEnabled` or `reduceMotionChanged`, or Reanimated's
  `ReduceMotion`. One anywhere in the file satisfies it, so review still checks each animation.
  `transition-colors` and opacity fades are not movement.
- **Focus** (`.tsx`, `.jsx`). A styled host control — `<button>`, `<a>`, `<input>`, `<select>`, `<textarea>` or
  `<Link>` whose class string is written at the call site — needs `focus-visible:`; bare `focus:`
  does not satisfy it. A control with no class keeps the browser ring, a pass-through
  `className={className}` is judged where the string is written, and `<Button>` or a class built
  from `buttonVariants(…)`, `cva(…)` or `tv(…)` inherits the atom's ring. Tests, stories and React
  Native are out.

## Deep guides (read on demand, do not preload)

- Adding a color token or alias, Tailwind v4 wiring (`@theme inline`, `@custom-variant dark`), dark mode, contrast verification → `references/defining-tokens.md`
- `cva` / `class_variants` components, `cn` from `@/lib/utils`, focus rings and ring opacity, arbitrary-value escape hatch → `references/component-variants.md`
- Shared token package, React Native theme, web-only aliases, touch targets, parity tests → `references/cross-platform-parity.md`
- Framer Motion, `tw-animate-css` in shadcn primitives, Reanimated, the mandatory `prefers-reduced-motion` backstop, animation budgets → `references/motion.md`
