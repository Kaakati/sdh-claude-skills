# Figma-to-Code Translation Workflow

Detailed methodology for converting Figma designs into production code.

---

## Pre-Translation Checklist

Before starting translation, verify:

- [ ] Design is using Auto Layout (not absolute positioning)
- [ ] Color styles are defined (not raw hex values)
- [ ] Text styles are defined (not one-off typography)
- [ ] Components are properly structured (variants, props)
- [ ] Responsive breakpoints are designed (mobile, tablet, desktop)
- [ ] Design tokens are documented or extractable

---

## Phase 1: Token Extraction

### Color Token Extraction

1. Open Figma's local styles panel
2. For each color style, document:

```
Figma Style Name     →  CSS Custom Property  →  Tailwind Class
────────────────────    ────────────────────    ──────────────
Primary/Default      →  --primary            →  bg-primary
Primary/Foreground   →  --primary-foreground  →  text-primary-foreground
Surface/Background   →  --background          →  bg-background
Surface/Card         →  --card                →  bg-card
```

3. Convert hex to HSL (space-separated, no `hsl()` wrapper):
   - `#0F172A` → `222.2 47.4% 11.2%`
   - Use an HSL converter or calculate: H = hue°, S = saturation%, L = lightness%

### Typography Token Extraction

Map Figma text styles to Tailwind typography:

```
Figma Text Style     →  Tailwind Classes
────────────────────    ────────────────────
Heading/H1           →  text-4xl font-bold leading-tight tracking-tight
Heading/H2           →  text-3xl font-semibold leading-tight
Body/Default         →  text-base font-normal leading-normal
Body/Small           →  text-sm font-normal leading-normal
Caption              →  text-xs font-medium leading-normal
```

### Spacing Token Extraction

Round Figma spacing values to the nearest Tailwind token:

| Figma Value | Nearest Token | Tailwind |
|-------------|---------------|----------|
| 3px | 4px | `1` (p-1, gap-1) |
| 6px | 6px | `1.5` (p-1.5) |
| 10px | 8px or 12px | `2` or `3` |
| 15px | 16px | `4` (p-4) |
| 18px | 20px | `5` (p-5) |

**Rule**: Always round to the nearest 4px-grid value. If the designer used 13px, use 12px (gap-3) or 16px (gap-4).

---

## Phase 2: Component Decomposition

### Step 1: Identify Component Boundaries

For each Figma component:

```
┌── Organism: ProductCard ──────────────────┐
│ ┌── Atom: ProductImage ─────────────────┐ │
│ │                                       │ │
│ └───────────────────────────────────────┘ │
│ ┌── Molecule: ProductInfo ──────────────┐ │
│ │ ┌── Atom: Heading ──┐ ┌── Atom: Badge │ │
│ │ └───────────────────┘ └───────────────│ │
│ │ ┌── Atom: Text (price) ──────────────┐│ │
│ │ └────────────────────────────────────┘│ │
│ └───────────────────────────────────────┘ │
│ ┌── Molecule: ProductActions ───────────┐ │
│ │ ┌─ Atom: Button ─┐ ┌─ Atom: Button ─┐│ │
│ │ └────────────────┘ └────────────────┘│ │
│ └───────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

### Step 2: Map Figma Variants to Props

| Figma Variant Property | Component Prop | Values |
|----------------------|---------------|--------|
| Size | `size` | `"sm" \| "md" \| "lg"` |
| Style | `variant` | `"primary" \| "secondary" \| "outline"` |
| State | Handled by CSS | `:hover`, `:active`, `:disabled`, `:focus-visible` |
| Has Icon | `icon?` | `ReactNode \| undefined` |
| Has Badge | `badge?` | `string \| undefined` |

### Step 3: Generate Component Code

**TypeScript/React pattern:**
```tsx
interface ButtonProps {
  label: string;
  variant?: "primary" | "secondary" | "outline" | "ghost" | "destructive";
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  disabled?: boolean;
  onClick?: () => void;
}

export function Button({
  label,
  variant = "primary",
  size = "md",
  icon,
  disabled = false,
  onClick,
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant, size }))}
      disabled={disabled}
      onClick={onClick}
    >
      {icon && <span className="mr-2" aria-hidden="true">{icon}</span>}
      {label}
    </button>
  );
}
```

**Phlex/Ruby pattern:**
```ruby
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, size: :md, icon: nil, **attrs)
    @label = label
    @variant = variant
    @size = size
    @icon = icon
    @attrs = attrs
  end

  def view_template
    button(class: VARIANTS.render(variant: @variant, size: @size), **@attrs) do
      render @icon if @icon
      plain @label
    end
  end
end
```

---

## Phase 3: Responsive Implementation

### Mobile-First Approach

Start with the mobile layout and add breakpoints:

```tsx
<div className="
  flex flex-col gap-4 p-4           /* Mobile: stacked, compact */
  md:flex-row md:gap-6 md:p-8      /* Tablet: side-by-side */
  lg:gap-8 lg:p-16                  /* Desktop: generous spacing */
">
```

### Common Responsive Patterns

| Figma Pattern | Mobile | Tablet+ | Tailwind |
|--------------|--------|---------|----------|
| Stack → Row | Column | Row | `flex-col md:flex-row` |
| Full → Half | 100% width | 50% width | `w-full md:w-1/2` |
| 1 col → 2 col → 3 col | 1 column | Grid | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3` |
| Show/Hide | Hidden | Visible | `hidden md:block` |
| Font resize | text-lg | text-2xl | `text-lg md:text-2xl` |

---

## Phase 4: Accessibility Layer

### For Every Interactive Element

1. **Button**: `<button>` element with visible label or `aria-label`
2. **Link**: `<a>` with `href`, not `div` with `onClick`
3. **Input**: Associated `<label>` via `htmlFor`/`id`
4. **Image**: `alt` attribute (descriptive or empty for decorative)
5. **Icon button**: `aria-label` describing the action
6. **Focus ring**: `focus-visible:ring-2 focus-visible:ring-ring`

### Keyboard Navigation Map

Document the expected keyboard behavior:

| Component | Keys | Action |
|-----------|------|--------|
| Button | Enter, Space | Activate |
| Link | Enter | Navigate |
| Modal | Escape | Close |
| Tabs | Arrow Left/Right | Switch tabs |
| Dropdown | Arrow Up/Down | Navigate options |
| Dropdown | Enter | Select option |
| Dropdown | Escape | Close |
