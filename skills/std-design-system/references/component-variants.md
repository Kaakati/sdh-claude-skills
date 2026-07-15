# Consuming Tokens: Component Variants and Styling

Read this when you are **building or restyling a component** — choosing variant axes, wiring
`cva`/`class_variants`, adding focus rings, or deciding whether an arbitrary value is justified.
If you are changing the token layer itself, that is a different job.

Load-bearing rules restated (assume nothing else here has been read):

1. **No hardcoded hex/rgb/hsl values in component files.** Consume tokens through utility classes
   (`bg-primary`, `text-foreground`) or CSS custom properties.
2. **No arbitrary Tailwind values** (`p-[13px]`, `text-[17px]`, `bg-[#ff0000]`) — snap to the scale.
3. **Every interactive element needs a visible `focus-visible:` ring**, 2px, ≥3:1 contrast, using
   the `ring-ring` token.
4. Multi-variant components go through `cva` (TypeScript) or `class_variants` (Ruby/Phlex) —
   never through hand-rolled conditional string concatenation.

---

## Decision: which variant axes does this component need?

Five standard axes exist. Use only the ones the component actually varies on; do not invent a
sixth axis with a novel name.

| Axis      | Values                                                    | Purpose                |
|-----------|-----------------------------------------------------------|------------------------|
| `size`    | `sm`, `md`, `lg`, `xl`                                     | Component dimensions   |
| `variant` | `primary`, `secondary`, `outline`, `ghost`, `destructive`  | Visual treatment       |
| `state`   | `default`, `hover`, `active`, `disabled`, `loading`        | Interaction state      |
| `radius`  | `none`, `sm`, `md`, `lg`, `full`                           | Corner rounding        |
| `density` | `compact`, `default`, `comfortable`                        | Spacing density        |

Prefer expressing `hover`/`active`/`disabled` as Tailwind pseudo-variants in the base classes.
Reserve the `state` axis for states the DOM cannot express on its own, such as `loading`.

Padding scale by atomic level — an atom that pads like an organism is a design bug:

- Atoms: `p-1` to `p-3` · Molecules: `p-2` to `p-4` · Organisms: `p-4` to `p-8` · Templates/Pages: `p-6` to `p-16`

---

## Decision: building a variant component in React (Vite SPA or Next.js)

### Bad — conditional string soup, raw colors, `focus:` instead of `focus-visible:`

```tsx
// src/components/ui/button.tsx
export function Button({ variant = 'primary', size = 'md', className, ...props }) {
  let classes = 'rounded font-medium ';
  if (variant === 'primary') classes += 'bg-[#1e293b] text-white hover:bg-[#334155] ';
  if (variant === 'destructive') classes += 'bg-red-600 text-white ';
  if (size === 'sm') classes += 'px-[9px] py-[5px] text-[13px] ';
  if (size === 'md') classes += 'px-4 py-2 text-base ';
  classes += 'focus:ring-2 focus:ring-blue-500 ';
  return <button className={classes + className} {...props} />;
}
```

Four failures: hex literals bypass dark mode entirely; `p-[9px]`/`text-[13px]` are off-scale;
`focus:` flashes a ring on every mouse click; and `className` concatenation cannot override a base
class, so callers resort to `!important`.

### Good — `cva` + `tailwind-merge`, tokens only, `focus-visible:`

```tsx
// src/components/ui/button.tsx
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { forwardRef } from 'react';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 font-medium',
    'motion-safe:transition-colors motion-safe:duration-150 motion-safe:ease-in-out',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:opacity-50',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-primary text-primary-foreground hover:bg-primary/90',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        outline: 'border border-input bg-background hover:bg-muted hover:text-foreground',
        ghost: 'hover:bg-muted hover:text-foreground',
        destructive: 'bg-error text-error-foreground hover:bg-error/90',
      },
      size: {
        sm: 'h-8 px-3 text-sm',
        md: 'h-10 px-4 text-base',
        lg: 'h-11 px-6 text-lg',
        xl: 'h-12 px-8 text-lg',
      },
      radius: { none: 'rounded-none', sm: 'rounded-sm', md: 'rounded-md', lg: 'rounded-lg', full: 'rounded-full' },
    },
    defaultVariants: { variant: 'primary', size: 'md', radius: 'md' },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, radius, loading, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size, radius }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <Spinner className="h-4 w-4" aria-hidden="true" />}
      {children}
    </button>
  ),
);
Button.displayName = 'Button';
```

`twMerge` is what makes `className` a real override: `<Button className="bg-accent" />` replaces
`bg-primary` rather than producing two competing classes whose winner depends on stylesheet order.

### Testing a variant component (Vitest + RTL)

```tsx
// src/components/ui/button.test.tsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Button } from './button';

describe('Button', () => {
  it('should render destructive token classes when variant is destructive', () => {
    render(<Button variant="destructive">Delete</Button>);
    expect(screen.getByRole('button')).toHaveClass('bg-error', 'text-error-foreground');
  });

  it('should let className override the variant background when both set a background', () => {
    render(<Button className="bg-accent">Save</Button>);
    const button = screen.getByRole('button');
    expect(button).toHaveClass('bg-accent');
    expect(button).not.toHaveClass('bg-primary');
  });

  it('should disable and mark busy when loading is true', () => {
    render(<Button loading>Save</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveAttribute('aria-busy', 'true');
  });
});
```

---

## Decision: building a variant component in Phlex (Rails)

### Bad — string interpolation and inline styles

```ruby
# app/components/button_component.rb
class ButtonComponent < Phlex::HTML
  def initialize(variant: :primary, size: :md)
    @variant = variant
    @size = size
  end

  def view_template(&block)
    css = "rounded font-medium "
    css += @variant == :primary ? "bg-slate-900 text-white " : "bg-slate-100 text-slate-900 "
    css += @size == :sm ? "px-3 py-1 text-sm " : "px-4 py-2 "
    button(class: css, style: "outline-color: #3b82f6", &block)
  end
end
```

### Good — `class_variants`, token classes, focus ring

```ruby
# app/components/button_component.rb
class ButtonComponent < ApplicationComponent
  STYLE = ClassVariants.build(
    base: <<~CSS.squish,
      inline-flex items-center justify-center gap-2 font-medium
      motion-safe:transition-colors motion-safe:duration-150
      focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
      disabled:pointer-events-none disabled:opacity-50
    CSS
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "border border-input bg-background hover:bg-muted",
        ghost: "hover:bg-muted",
        destructive: "bg-error text-error-foreground hover:bg-error/90"
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-base",
        lg: "h-11 px-6 text-lg",
        xl: "h-12 px-8 text-lg"
      },
      radius: { none: "rounded-none", sm: "rounded-sm", md: "rounded-md", lg: "rounded-lg", full: "rounded-full" }
    },
    defaults: { variant: :primary, size: :md, radius: :md }
  )

  def initialize(variant: :primary, size: :md, radius: :md, **attrs)
    @variant = variant
    @size = size
    @radius = radius
    @attrs = attrs
  end

  def view_template(&block)
    button(class: STYLE.render(variant: @variant, size: @size, radius: @radius), **@attrs, &block)
  end
end
```

The Phlex and React buttons must resolve to the **same token names** (`bg-primary`,
`text-primary-foreground`) and the **same size ramp** (`h-8`/`h-10`/`h-11`/`h-12`). That parity is
the whole point of a shared token layer.

---

## Decision: focus indicators

`focus:` fires on mouse click too, so designers ask to remove it, and then keyboard users lose the
ring entirely. `focus-visible:` fires only for keyboard and programmatic focus — it never needs
removing.

### Bad

```tsx
<a href="/settings" className="focus:outline-none">Settings</a>  {/* ring removed, nothing replaces it */}
<button className="focus:ring-2 focus:ring-blue-500">Save</button>  {/* raw color, fires on click */}
```

### Good

```tsx
<a
  href="/settings"
  className="rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
>
  Settings
</a>
```

`ring-offset-background` matters: without it the 2px offset gap is painted with the default white,
which appears as a white halo in dark mode.

---

## Decision: I genuinely need a value the scale does not have

First ask whether the design is right. A `p-[13px]` almost always means someone measured a mockup
that itself drifted off-grid; `p-3` (12px) is the answer.

Legitimate exceptions are structural, not stylistic — grid tracks, a specific breakpoint, a fixed
third-party embed size. Document them.

### Bad

```tsx
<div className="grid gap-[13px] p-[17px] text-[15px]">   {/* three off-scale guesses */}
```

### Good

```tsx
{/* 280px sidebar is fixed by the design spec's collapsed-nav width; no spacing token maps to it. */}
<div className="grid grid-cols-[280px_1fr] gap-4 p-4 text-sm">
```

If a one-off value appears three times, it is not a one-off — promote it to a token in
`tailwind.config.js` and delete the arbitrary values.
