# Design Token Specification

Complete design token system for cross-platform theming. All tokens are defined as CSS custom properties at the `:root` scope and consumed by Tailwind CSS, React Native, and Phlex.

---

## CSS Custom Properties Architecture

### Naming Convention

All tokens follow the pattern `--{category}-{name}`:

| Category | Prefix | Examples |
|----------|--------|----------|
| Colors | `--color-` or direct semantic name | `--primary`, `--secondary`, `--background` |
| Typography | `--font-` | `--font-sans`, `--font-mono` |
| Spacing | `--spacing-` | `--spacing-4`, `--spacing-8` |
| Radius | `--radius-` | `--radius-sm`, `--radius-lg` |
| Shadow | `--shadow-` | `--shadow-md`, `--shadow-xl` |

### HSL Format

Colors use space-separated HSL values (without the `hsl()` wrapper) so they can be composed with opacity modifiers in Tailwind CSS:

```css
/* Definition: raw HSL values */
--primary: 222.2 47.4% 11.2%;

/* Usage with Tailwind: opacity modifier works */
/* bg-primary/50 compiles to: */
background-color: hsl(222.2 47.4% 11.2% / 0.5);
```

This pattern enables `bg-primary/80`, `text-primary-foreground/90`, and similar opacity utilities without defining extra variables.

### Root Scope

All tokens are declared in `:root` for global availability. Dark mode overrides use the `.dark` class selector:

```css
:root {
  /* Light mode tokens */
  --primary: 222.2 47.4% 11.2%;
}

.dark {
  /* Dark mode overrides */
  --primary: 210 40% 98%;
}
```

---

## Color System

### Core Palette

| Token | Purpose | Light Value (HSL) | Dark Value (HSL) |
|-------|---------|-------------------|------------------|
| `--primary` | Brand color, primary actions | `222.2 47.4% 11.2%` | `210 40% 98%` |
| `--primary-foreground` | Text on primary backgrounds | `210 40% 98%` | `222.2 47.4% 11.2%` |
| `--secondary` | Secondary actions, accents | `210 40% 96.1%` | `217.2 32.6% 17.5%` |
| `--secondary-foreground` | Text on secondary backgrounds | `222.2 47.4% 11.2%` | `210 40% 98%` |
| `--accent` | Highlights, hover states | `210 40% 96.1%` | `217.2 32.6% 17.5%` |
| `--accent-foreground` | Text on accent backgrounds | `222.2 47.4% 11.2%` | `210 40% 98%` |
| `--neutral` | Neutral UI elements | `0 0% 46.1%` | `0 0% 63.9%` |

### Semantic Colors

| Token | Purpose | Light Value (HSL) | Dark Value (HSL) |
|-------|---------|-------------------|------------------|
| `--success` | Success states, confirmations | `142.1 76.2% 28%` | `142.1 70.6% 45.3%` |
| `--success-foreground` | Text on success backgrounds | `355.7 100% 97.3%` | `144.9 80.4% 10%` |
| `--warning` | Warning states, caution | `37.7 92.1% 50.2%` | `43.3 96.4% 56.3%` |
| `--warning-foreground` | Text on warning backgrounds | `26 83.3% 14.1%` | `26 83.3% 14.1%` |
| `--error` | Error states, destructive | `0 84.2% 60.2%` | `0 62.8% 30.6%` |
| `--error-foreground` | Text on error backgrounds | `0 0% 98%` | `0 85.7% 97.3%` |
| `--info` | Informational states | `199.4 95.5% 53.8%` | `199.4 80% 46%` |
| `--info-foreground` | Text on info backgrounds | `200 100% 10%` | `200 100% 95%` |

### Background / Foreground Convention

Every color token has a `-foreground` counterpart. This ensures accessible text contrast on any background:

```css
/* The foreground color is always readable on its base color */
.btn-primary {
  background-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}
```

### Surface Colors

| Token | Purpose | Light Value (HSL) | Dark Value (HSL) |
|-------|---------|-------------------|------------------|
| `--background` | Page background | `0 0% 100%` | `222.2 84% 4.9%` |
| `--foreground` | Default text | `222.2 84% 4.9%` | `210 40% 98%` |
| `--card` | Card backgrounds | `0 0% 100%` | `222.2 84% 4.9%` |
| `--card-foreground` | Card text | `222.2 84% 4.9%` | `210 40% 98%` |
| `--popover` | Popover/dropdown backgrounds | `0 0% 100%` | `222.2 84% 4.9%` |
| `--popover-foreground` | Popover text | `222.2 84% 4.9%` | `210 40% 98%` |
| `--muted` | Muted/disabled backgrounds | `210 40% 96.1%` | `217.2 32.6% 17.5%` |
| `--muted-foreground` | Muted/disabled text | `215.4 16.3% 46.9%` | `215 20.2% 65.1%` |

### Border & Ring Colors

| Token | Purpose | Light Value (HSL) | Dark Value (HSL) |
|-------|---------|-------------------|------------------|
| `--border` | Default borders | `214.3 31.8% 91.4%` | `217.2 32.6% 17.5%` |
| `--input` | Input borders | `214.3 31.8% 91.4%` | `217.2 32.6% 17.5%` |
| `--ring` | Focus ring color | `222.2 84% 4.9%` | `212.7 26.8% 83.9%` |

### Complete Light Mode `:root` Block

```css
:root {
  /* Surface */
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;

  /* Card */
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;

  /* Popover */
  --popover: 0 0% 100%;
  --popover-foreground: 222.2 84% 4.9%;

  /* Core Palette */
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;

  --secondary: 210 40% 96.1%;
  --secondary-foreground: 222.2 47.4% 11.2%;

  --accent: 210 40% 96.1%;
  --accent-foreground: 222.2 47.4% 11.2%;

  --neutral: 0 0% 46.1%;

  /* Muted */
  --muted: 210 40% 96.1%;
  --muted-foreground: 215.4 16.3% 44%;

  /* Semantic */
  --success: 142.1 76.2% 28%;
  --success-foreground: 355.7 100% 97.3%;

  --warning: 37.7 92.1% 50.2%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 84.2% 47%;
  --error-foreground: 0 0% 98%;

  --info: 199.4 95.5% 53.8%;
  --info-foreground: 200 100% 10%;

  /* Borders & Ring */
  --border: 214.3 31.8% 91.4%;
  --input: 214.3 31.8% 91.4%;
  --ring: 222.2 84% 4.9%;

  /* Border Radius */
  --radius: 0.5rem;
}
```

### Complete Dark Mode Block

```css
.dark {
  /* Surface */
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;

  /* Card */
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;

  /* Popover */
  --popover: 222.2 84% 4.9%;
  --popover-foreground: 210 40% 98%;

  /* Core Palette */
  --primary: 210 40% 98%;
  --primary-foreground: 222.2 47.4% 11.2%;

  --secondary: 217.2 32.6% 17.5%;
  --secondary-foreground: 210 40% 98%;

  --accent: 217.2 32.6% 17.5%;
  --accent-foreground: 210 40% 98%;

  --neutral: 0 0% 63.9%;

  /* Muted */
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;

  /* Semantic */
  --success: 142.1 70.6% 45.3%;
  --success-foreground: 144.9 80.4% 10%;

  --warning: 43.3 96.4% 56.3%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 62.8% 30.6%;
  --error-foreground: 0 85.7% 97.3%;

  --info: 199.4 80% 35%;
  --info-foreground: 200 100% 95%;

  /* Borders & Ring */
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 212.7 26.8% 83.9%;
}
```

---

## Typography Scale

### Font Families

| Token | Value | Usage |
|-------|-------|-------|
| `--font-sans` | `'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif` | Body text, UI elements |
| `--font-mono` | `'JetBrains Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace` | Code, technical content |
| `--font-serif` | `'Merriweather', ui-serif, Georgia, Cambria, 'Times New Roman', Times, serif` | Optional: editorial, long-form |

```css
:root {
  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo,
    Consolas, 'Liberation Mono', monospace;
  --font-serif: 'Merriweather', ui-serif, Georgia, Cambria, 'Times New Roman',
    Times, serif;
}
```

### Size Scale

| Name | Value | Pixels (at 16px base) | Usage |
|------|-------|-----------------------|-------|
| `xs` | `0.75rem` | 12px | Captions, labels, badges |
| `sm` | `0.875rem` | 14px | Secondary text, helper text |
| `base` | `1rem` | 16px | Body text (default) |
| `lg` | `1.125rem` | 18px | Subheadings, emphasis |
| `xl` | `1.25rem` | 20px | Section headings |
| `2xl` | `1.5rem` | 24px | Page section titles |
| `3xl` | `1.875rem` | 30px | Major headings |
| `4xl` | `2.25rem` | 36px | Hero titles |
| `5xl` | `3rem` | 48px | Display text |

### Weight Scale

| Name | Value | Usage |
|------|-------|-------|
| `light` | `300` | De-emphasized, decorative text |
| `normal` | `400` | Body text (default) |
| `medium` | `500` | Slightly emphasized text, labels |
| `semibold` | `600` | Subheadings, important labels |
| `bold` | `700` | Headings, strong emphasis |

### Line Height Scale

| Name | Value | Usage |
|------|-------|-------|
| `tight` | `1.25` | Headings, compact UI |
| `snug` | `1.375` | Subheadings, dense content |
| `normal` | `1.5` | Body text (default) |
| `relaxed` | `1.625` | Long-form reading content |
| `loose` | `2` | Spacious layouts, large display text |

---

## Spacing System

Base unit: **4px**. All spacing values are multiples of 4px for consistent vertical and horizontal rhythm.

| Token | Value | Pixels | Usage |
|-------|-------|--------|-------|
| `0.5` | `0.125rem` | 2px | Hairline gaps |
| `1` | `0.25rem` | 4px | Tight inner padding |
| `1.5` | `0.375rem` | 6px | Small gaps |
| `2` | `0.5rem` | 8px | Default inner padding, icon gaps |
| `3` | `0.75rem` | 12px | Compact element spacing |
| `4` | `1rem` | 16px | Standard padding |
| `5` | `1.25rem` | 20px | Comfortable padding |
| `6` | `1.5rem` | 24px | Section inner padding |
| `8` | `2rem` | 32px | Card padding, section gaps |
| `10` | `2.5rem` | 40px | Large section spacing |
| `12` | `3rem` | 48px | Page section gaps |
| `16` | `4rem` | 64px | Major section separation |
| `20` | `5rem` | 80px | Page-level spacing |
| `24` | `6rem` | 96px | Hero section padding |

### Usage Guidelines

- **Inner padding**: Use `2` to `6` for element padding.
- **Between elements**: Use `2` to `4` for sibling elements within a group.
- **Between sections**: Use `8` to `16` for major layout sections.
- **Page margins**: Use `4` to `8` on mobile, `8` to `16` on desktop.

---

## Border Radius

| Name | Value | Usage |
|------|-------|-------|
| `none` | `0` | Sharp corners, full-width elements |
| `sm` | `0.125rem` (2px) | Subtle rounding, badges |
| `default` | `0.25rem` (4px) | Inputs, small buttons |
| `md` | `0.375rem` (6px) | Cards, dropdowns |
| `lg` | `0.5rem` (8px) | Modals, larger cards |
| `xl` | `0.75rem` (12px) | Prominent cards, panels |
| `2xl` | `1rem` (16px) | Hero sections, feature cards |
| `full` | `9999px` | Pills, avatars, circular elements |

```css
:root {
  --radius: 0.5rem; /* Base radius used by Tailwind */
}
```

Tailwind maps radius values relative to `--radius`:

```css
/* Tailwind v4 computed radius utilities */
/* rounded-sm  = calc(var(--radius) - 4px) */
/* rounded-md  = calc(var(--radius) - 2px) */
/* rounded-lg  = var(--radius) */
/* rounded-xl  = calc(var(--radius) + 4px) */
```

---

## Shadows

Elevation scale using `box-shadow` for depth hierarchy:

| Name | Value | Usage |
|------|-------|-------|
| `sm` | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Subtle lift: buttons, inputs |
| `default` | `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)` | Cards, list items |
| `md` | `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)` | Dropdowns, floating elements |
| `lg` | `0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)` | Modals, dialogs |
| `xl` | `0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)` | Popovers, elevated panels |
| `2xl` | `0 25px 50px -12px rgb(0 0 0 / 0.25)` | Top-level overlays |

### Dark Mode Shadow Adjustment

In dark mode, shadows are less visible. Increase opacity or use a colored glow instead:

```css
.dark {
  /* Shadows use higher opacity in dark mode */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.2);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.3), 0 2px 4px -2px rgb(0 0 0 / 0.2);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.3), 0 4px 6px -4px rgb(0 0 0 / 0.2);
}
```

---

## Transitions

### Duration Scale

| Name | Value | Usage |
|------|-------|-------|
| `75` | `75ms` | Instant feedback (checkbox, toggle) |
| `100` | `100ms` | Hover color changes |
| `150` | `150ms` | Default UI interactions |
| `200` | `200ms` | Button presses, focus rings |
| `300` | `300ms` | Dropdowns, tooltips |
| `500` | `500ms` | Page transitions, modals |
| `700` | `700ms` | Complex animations |
| `1000` | `1000ms` | Loading states, skeleton animations |

### Easing Functions

| Name | Value | Usage |
|------|-------|-------|
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Elements exiting the viewport |
| `ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | Elements entering the viewport |
| `ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Default for most transitions |
| `spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Playful bounce, toggle switches |

### Standard Transition Shorthand

```css
/* Default transition for interactive elements */
.interactive {
  transition: color 150ms ease-in-out,
              background-color 150ms ease-in-out,
              border-color 150ms ease-in-out,
              box-shadow 150ms ease-in-out;
}

/* Modal / overlay transitions */
.overlay {
  transition: opacity 300ms ease-out,
              transform 300ms ease-out;
}
```

---

## WCAG AA Contrast Requirements

### Minimum Contrast Ratios

| Content Type | Minimum Ratio | WCAG Criterion |
|-------------|---------------|----------------|
| Normal text (< 18px, or < 14px bold) | **4.5:1** | 1.4.3 Contrast (Minimum) |
| Large text (>= 18px, or >= 14px bold) | **3:1** | 1.4.3 Contrast (Minimum) |
| UI components and graphical objects | **3:1** | 1.4.11 Non-text Contrast |

### Measured Foreground / Background Pairs

**Computed from the `:root` and `.dark` blocks in this file** with the `contrastRatio()`
helper in `../../std-design-system/references/defining-tokens.md`, not asserted. A test
recomputes this table from those blocks and fails CI if any cell drifts or drops below AA —
because the previous version of this table was headed *"Verified"* and **9 of its 10 ratios
were wrong**, three of them claiming "Passes AA" while measuring below 4.5:1 (`--success`
was 3.00:1). The word "Verified" was the most dangerous thing on the page: the numbers had
never been computed, and these are the **default** tokens teams copy.

| Background Token | Foreground Token | Light Ratio | Dark Ratio | Status |
|-----------------|-----------------|-------------|------------|--------|
| `--primary` | `--primary-foreground` | 17.06:1 | 17.06:1 | Passes AA & AAA |
| `--secondary` | `--secondary-foreground` | 16.30:1 | 13.98:1 | Passes AA & AAA |
| `--accent` | `--accent-foreground` | 16.30:1 | 13.98:1 | Passes AA & AAA |
| `--card` | `--card-foreground` | 20.01:1 | 19.12:1 | Passes AA & AAA |
| `--muted` | `--muted-foreground` | 4.81:1 | 5.71:1 | Passes AA |
| `--success` | `--success-foreground` | 4.70:1 | 6.54:1 | Passes AA |
| `--warning` | `--warning-foreground` | 6.79:1 | 8.73:1 | Passes AA |
| `--error` | `--error-foreground` | 4.82:1 | 9.16:1 | Passes AA |
| `--info` | `--info-foreground` | 6.82:1 | 4.80:1 | Passes AA |

All pairs clear **4.5:1** (WCAG 1.4.3, normal text) in both modes. `--success`, `--error`,
`--muted-foreground` and dark `--info` were darkened to get there — fixing only the table
would have left defaults documented as failing and still shipped.

### Contrast Validation Process

Always validate contrast when:
1. Introducing a new color token or modifying an existing one
2. Changing foreground or background pairings
3. Adding colored text on non-standard backgrounds

Use these tools for validation:
- Chrome DevTools color contrast checker
- WebAIM Contrast Checker (https://webaim.org/resources/contrastchecker/)
- Figma A11y contrast plugins

### Customization Notes

When overriding token values:
- Always update both the base color and its `-foreground` counterpart together
- Re-validate contrast ratios after any color change
- Document any pairs that fall to AA-only (no AAA) compliance
- Semantic color pairs (success, warning, error, info) are especially important to validate because they convey meaning through color alone -- always pair with an icon or text label
