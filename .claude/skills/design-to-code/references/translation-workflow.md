# Design-to-Code Translation Workflow

Detailed methodology for translating design specifications into production code across all platforms.

---

## Overview

The translation workflow converts design intent into production code that is:
- **Token-based**: All visual properties derive from design tokens
- **Cross-platform**: Same design renders consistently on web, mobile, and Rails views
- **Accessible**: WCAG 2.2 AA compliant from the start
- **Responsive**: Mobile-first with progressive enhancement

---

## Step 1: Design Input Analysis

### Accepted Input Types

| Input | What to Extract | How |
|-------|----------------|-----|
| Figma link | Frames, styles, components, variants | Inspect panel, dev mode |
| Screenshots | Layout structure, visual hierarchy, spacing | Visual analysis |
| Written spec | Requirements, constraints, acceptance criteria | Text parsing |
| Existing code | Current implementation gaps, token usage | Read/Grep tools |
| Brand book | Colors, typography, voice, personality | Reference material |

### Analysis Checklist

- [ ] Identify all unique screens/pages
- [ ] List all unique components
- [ ] Note color palette (primary, secondary, accent, semantic)
- [ ] Note typography (font families, size scale, weight usage)
- [ ] Note spacing patterns (padding, gaps, margins)
- [ ] Note interactive behaviors (hover, focus, active, disabled)
- [ ] Note responsive breakpoints
- [ ] Note animations/transitions

---

## Step 2: Token Mapping

### Color Tokens

For each color in the design:

```
Design Color     →  Token Name           →  HSL Value            →  Tailwind
─────────────      ───────────────────      ────────────────────    ────────
Brand Blue       →  --primary             →  222.2 47.4% 11.2%   →  bg-primary
White on Blue    →  --primary-foreground   →  210 40% 98%         →  text-primary-foreground
Page BG          →  --background           →  0 0% 100%           →  bg-background
Body Text        →  --foreground           →  222.2 84% 4.9%     →  text-foreground
```

### Typography Tokens

```
Design Style     →  Tailwind Classes
─────────────      ────────────────────
Display          →  text-5xl font-bold leading-tight tracking-tight
H1               →  text-4xl font-bold leading-tight tracking-tight
H2               →  text-3xl font-semibold leading-tight
H3               →  text-2xl font-semibold leading-snug
H4               →  text-xl font-medium leading-snug
Body             →  text-base font-normal leading-normal
Small            →  text-sm font-normal leading-normal
Caption          →  text-xs font-medium leading-normal tracking-wide uppercase
```

### Spacing Tokens

Round all spacing to the 4px grid:

```
Design Value     →  Nearest 4px          →  Tailwind Token
─────────────      ────────────────────    ──────────────
3px              →  4px                   →  1
7px              →  8px                   →  2
11px             →  12px                  →  3
15px             →  16px                  →  4
22px             →  24px                  →  6
30px             →  32px                  →  8
```

---

## Step 3: Component Decomposition

### Atomic Level Assignment

```
Component               →  Level      →  Directory
───────────────────────    ──────────    ──────────────────────
Button                  →  Atom       →  components/atoms/
Input                   →  Atom       →  components/atoms/
Badge                   →  Atom       →  components/atoms/
Search Form             →  Molecule   →  components/molecules/
Nav Link Group          →  Molecule   →  components/molecules/
Product Card            →  Organism   →  components/organisms/
Header                  →  Organism   →  components/organisms/
Dashboard Layout        →  Template   →  components/templates/
Product Listing Page    →  Page       →  views/ or pages/
```

### Variant Extraction

For each component, extract all visual variants:

| Prop | Values | Visual Difference |
|------|--------|------------------|
| `size` | sm, md, lg | Height, padding, font size |
| `variant` | primary, secondary, outline, ghost, destructive | Background, text color, border |
| `state` | default, hover, active, disabled, loading | Opacity, cursor, animation |

---

## Step 4: Platform-Specific Code Generation

### TypeScript/React (Vite SPA or Next.js)

```tsx
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
  {
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-error text-error-foreground hover:bg-error/90",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-lg",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);
```

### Phlex/Ruby

```ruby
class Components::Atoms::Button < Components::Base
  VARIANTS = class_variants(
    base: "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        destructive: "bg-error text-error-foreground hover:bg-error/90"
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-lg"
      }
    },
    defaults: { variant: :primary, size: :md }
  )
end
```

### React Native

```tsx
const buttonStyles = StyleSheet.create({
  base: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: theme.radius.md,
  },
  primary: {
    backgroundColor: theme.colors.primary,
  },
  sm: { height: 32, paddingHorizontal: 12 },
  md: { height: 40, paddingHorizontal: 16 },
  lg: { height: 48, paddingHorizontal: 24 },
});
```

---

## Step 5: Responsive Implementation

### Breakpoint Strategy

Always mobile-first. Add complexity as viewport grows:

```tsx
// Mobile: single column, compact
// md: two columns, moderate spacing
// lg: three columns, generous spacing
<div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 md:gap-6 md:p-8 lg:grid-cols-3 lg:gap-8 lg:p-16">
```

---

## Step 6: Accessibility Layer

### Every Component Must Have

| Requirement | Implementation |
|-------------|---------------|
| Semantic HTML | Use `<button>`, `<a>`, `<input>` — never `<div onClick>` |
| Focus indicator | `focus-visible:ring-2 focus-visible:ring-ring` |
| Color contrast | 4.5:1 for text, 3:1 for UI components |
| Touch target | `min-h-[44px] min-w-[44px]` on mobile |
| Motion respect | `motion-safe:` prefix on all transitions |
| Screen reader | `aria-label` on icon-only buttons, `aria-live` for dynamic content |

---

## Quality Checklist

Before marking a design-to-code translation complete:

- [ ] All colors use design tokens (no hardcoded hex)
- [ ] All spacing uses scale tokens (no arbitrary px)
- [ ] All typography uses scale tokens
- [ ] All interactive elements have focus-visible states
- [ ] All components follow Atomic Design hierarchy
- [ ] Responsive behavior documented and implemented
- [ ] Dark mode tokens defined and tested
- [ ] WCAG 2.2 AA contrast ratios verified
- [ ] Touch targets meet minimum sizes
- [ ] Animations respect prefers-reduced-motion
