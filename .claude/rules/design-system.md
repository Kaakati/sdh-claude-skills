---
paths:
  - "web/src/styles/**"
  - "web/src/components/ui/**"
  - "next/src/components/ui/**"
  - "mobile/src/theme/**"
  - "backend/app/components/**"
  - "**/tailwind.config.*"
  - "**/globals.css"
---

# Design System Standards

Apple-level design token conventions for cross-platform visual consistency. All visual properties must derive from tokens — no hardcoded values.

## Token Architecture

### Naming Convention

All CSS custom properties follow `--{category}-{name}`:

| Category | Pattern | Examples |
|----------|---------|----------|
| Colors | Semantic name | `--primary`, `--secondary`, `--accent`, `--success` |
| Foreground | `{color}-foreground` | `--primary-foreground`, `--error-foreground` |
| Surface | Surface role | `--background`, `--card`, `--popover`, `--muted` |
| Border | Border role | `--border`, `--input`, `--ring` |

### HSL Format

Colors use space-separated HSL values (without `hsl()` wrapper) for Tailwind opacity modifier compatibility:

```css
/* Definition */
--primary: 222.2 47.4% 11.2%;

/* Consumption with opacity */
background-color: hsl(var(--primary) / 0.5);
/* Tailwind: bg-primary/50 */
```

### Root Scope and Dark Mode

- All tokens defined in `:root` for global availability
- Dark mode overrides use `.dark` class selector (not `@media prefers-color-scheme`)
- Every color token has a `-foreground` counterpart for guaranteed text contrast

## Color Rules

### Palette Requirements

| Palette | Required Tokens | Purpose |
|---------|----------------|---------|
| Core | `primary`, `secondary`, `accent` | Brand identity and UI actions |
| Neutral | `neutral`, `muted`, `background`, `foreground` | Text, backgrounds, disabled states |
| Semantic | `success`, `warning`, `error`, `info` | Status communication |
| Surface | `card`, `popover` | Container backgrounds |
| Border | `border`, `input`, `ring` | Boundaries and focus indicators |

### Color Constraints

- **No hardcoded hex values** in component files — use token classes (`bg-primary`, `text-foreground`)
- **No hardcoded RGB/HSL** — consume via CSS custom properties or Tailwind utilities
- **Minimum 4.5:1 contrast** for normal text against its background
- **Minimum 3:1 contrast** for large text (18px+ or 14px+ bold) and UI components
- **Foreground convention**: Every background color token has a `-foreground` pair that guarantees readable text contrast
- **Semantic colors must pair with icons**: Never convey meaning through color alone

## Typography

### Type Scale

Use Tailwind's built-in type scale tokens exclusively:

| Token | Size | Usage |
|-------|------|-------|
| `text-xs` | 12px | Captions, badges, labels |
| `text-sm` | 14px | Secondary text, helper text |
| `text-base` | 16px | Body text (default) |
| `text-lg` | 18px | Subheadings, emphasis |
| `text-xl` | 20px | Section headings |
| `text-2xl` | 24px | Page section titles |
| `text-3xl` | 30px | Major headings |
| `text-4xl` | 36px | Hero titles |
| `text-5xl` | 48px | Display text |

### Typography Constraints

- **Maximum 2 font families** per project (sans + mono, or sans + serif)
- **Weight scale**: 300 (light), 400 (normal), 500 (medium), 600 (semibold), 700 (bold)
- **No arbitrary font sizes** — use the scale tokens only
- **Line height**: Use `leading-tight` (1.25), `leading-snug` (1.375), `leading-normal` (1.5), `leading-relaxed` (1.625)

## Spacing

### 4px Base Unit

All spacing values are multiples of 4px. Use Tailwind spacing scale tokens exclusively:

| Scale | Value | Usage |
|-------|-------|-------|
| `0.5`-`1.5` | 2-6px | Tight inner padding, icon gaps |
| `2`-`4` | 8-16px | Standard padding, element gaps |
| `5`-`8` | 20-32px | Section padding, card padding |
| `10`-`16` | 40-64px | Major section separation |
| `20`-`24` | 80-96px | Page-level spacing, hero padding |

### Spacing Constraints

- **No arbitrary pixel values** (`p-[13px]`) — use the nearest scale token
- **Consistent component padding per atomic level**:
  - Atoms: `p-1` to `p-3`
  - Molecules: `p-2` to `p-4`
  - Organisms: `p-4` to `p-8`
  - Templates/Pages: `p-6` to `p-16`

## Motion

### Duration Scale

| Token | Duration | Usage |
|-------|----------|-------|
| `duration-75` | 75ms | Instant feedback (toggle, checkbox) |
| `duration-100` | 100ms | Hover color changes |
| `duration-150` | 150ms | Default UI interactions |
| `duration-200` | 200ms | Button presses, focus rings |
| `duration-300` | 300ms | Dropdowns, tooltips, slide-in |
| `duration-500` | 500ms | Page transitions, modals |

### Easing

| Easing | Curve | Usage |
|--------|-------|-------|
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Elements exiting viewport |
| `ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Elements entering viewport |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Default for most transitions |
| Spring | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Apple-feel bounce, toggle switches |

### Motion Constraints

- **Always prefix with `motion-safe:`** for accessibility — users with vestibular disorders disable motion
- **No animations without `prefers-reduced-motion` handling**
- **Duration ceiling**: UI transitions must not exceed 500ms; longer durations feel sluggish
- **Spring easing** for interactive elements (toggles, modals) — gives Apple-quality tactile feel

```tsx
// Correct: motion-safe prefix
<div className="motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-in-out">

// Framer Motion: respect reduced motion
<motion.div
  initial={{ opacity: 0, y: 10 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.2, ease: [0.34, 1.56, 0.64, 1] }}
/>
```

## Component Styling

### Variant Architecture

Use `class_variants` (Ruby/Phlex) or `cva` (TypeScript) for multi-variant components:

**5 standard variant axes:**

| Axis | Values | Purpose |
|------|--------|---------|
| `size` | `sm`, `md`, `lg`, `xl` | Component dimensions |
| `variant` | `primary`, `secondary`, `outline`, `ghost`, `destructive` | Visual treatment |
| `state` | `default`, `hover`, `active`, `disabled`, `loading` | Interaction state |
| `radius` | `none`, `sm`, `md`, `lg`, `full` | Corner rounding |
| `density` | `compact`, `default`, `comfortable` | Spacing density |

### Focus Indicators

- **Every interactive element** must have a visible focus indicator
- **Focus ring**: 2px ring with minimum 3:1 contrast against adjacent colors
- **Use `focus-visible:`** (not `focus:`) to avoid showing focus rings on mouse clicks
- **Ring color**: Use `ring-ring` token for consistent focus appearance

```tsx
// Standard focus pattern
className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
```

### Tailwind Arbitrary Values

- **Avoid Tailwind arbitrary values** (`bg-[#ff0000]`, `p-[13px]`, `text-[17px]`)
- If a token does not exist for your value, consider whether the design is correct
- Exception: one-off layout values for grid columns or specific breakpoints, documented with a comment

## Cross-Platform Consistency

### Platform-Specific Token Consumption

| Platform | Token Source | Method |
|----------|-------------|--------|
| Vite SPA / Next.js | CSS custom properties | Tailwind utility classes |
| React Native | Theme context | `useTheme()` hook, `StyleSheet` |
| Phlex (Rails) | CSS custom properties | Tailwind classes + `class_variants` |

### Shared Constraints

- Same token names across all platforms (color-primary = primary in all)
- Same spacing scale (4px base) on all platforms
- Same type scale ratios on all platforms
- Touch target minimum: 44x44px (mobile), 32x32px (web) per WCAG 2.5.8
