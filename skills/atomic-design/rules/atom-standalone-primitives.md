---
title: "Atoms Are Standalone Primitives"
id: atom-standalone-primitives
impact: HIGH
tags: [atomic-design, atoms]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Atoms Are Standalone Primitives

Atoms are the smallest, indivisible UI elements. They cannot compose other atoms -- they are the fundamental building blocks from which everything else is constructed. An atom maps to a single HTML element or native component with styling and props.

## Incorrect

An atom importing another atom -- this violates the indivisibility principle. If a component composes other atoms, it is a molecule.

```tsx
// web/src/components/atoms/IconButton/IconButton.tsx
// WRONG: This is a molecule disguised as an atom
import { Icon } from "@/components/atoms/Icon";
import { Button } from "@/components/atoms/Button";

export function IconButton({ icon, label }: IconButtonProps) {
  return (
    <Button>
      <Icon name={icon} />
      {label}
    </Button>
  );
}
```

```ruby
# backend/app/components/atoms/icon_button.rb
# WRONG: Atom composing other atoms
class Components::Atoms::IconButton < Components::Base
  def view_template
    render Components::Atoms::Button.new(variant: :primary) do
      render Components::Atoms::Icon.new(name: @icon)
      text @label
    end
  end
end
```

## Correct

Atoms are self-contained primitives with no component dependencies.

### Phlex (Rails)

```ruby
# backend/app/components/atoms/button.rb
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, size: :md, type: :button, disabled: false, **attrs)
    @label = label
    @variant = variant
    @size = size
    @type = type
    @disabled = disabled
    @attrs = attrs
  end

  def view_template
    button(
      type: @type,
      class: button_classes,
      disabled: @disabled,
      **@attrs
    ) { @label }
  end

  private

  def button_classes
    base = "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
    variant = case @variant
              when :primary then "bg-primary text-white hover:bg-primary-dark focus:ring-primary"
              when :secondary then "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary"
              when :ghost then "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300"
              end
    size = case @size
           when :sm then "px-3 py-1.5 text-sm"
           when :md then "px-4 py-2 text-base"
           when :lg then "px-6 py-3 text-lg"
           end
    [base, variant, size].join(" ")
  end
end
```

```ruby
# backend/app/components/atoms/input.rb
class Components::Atoms::Input < Components::Base
  def initialize(name:, type: :text, placeholder: nil, value: nil, disabled: false, **attrs)
    @name = name
    @type = type
    @placeholder = placeholder
    @value = value
    @disabled = disabled
    @attrs = attrs
  end

  def view_template
    input(
      name: @name,
      type: @type,
      placeholder: @placeholder,
      value: @value,
      disabled: @disabled,
      class: "w-full rounded-lg border border-gray-300 px-4 py-2 text-base text-gray-900 placeholder-gray-400 focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-gray-50 disabled:text-gray-400",
      **@attrs
    )
  end
end
```

### ReactJS (Vite SPA)

```tsx
// web/src/components/atoms/Button/Button.tsx
import { type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark focus:ring-primary",
  secondary: "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export function Button({
  label,
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
          variantStyles[variant],
          sizeStyles[size],
          className,
        ),
      )}
      {...props}
    >
      {label}
    </button>
  );
}
```

### Next.js (App Router)

```tsx
// next/src/components/atoms/Button/Button.tsx
import { type ButtonHTMLAttributes } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark focus:ring-primary",
  secondary: "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export function Button({
  label,
  variant = "primary",
  size = "md",
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={twMerge(
        clsx(
          "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
          variantStyles[variant],
          sizeStyles[size],
          className,
        ),
      )}
      {...props}
    >
      {label}
    </button>
  );
}
```

### React Native

```tsx
// mobile/src/components/atoms/Button/Button.tsx
import { Pressable, Text, type PressableProps } from "react-native";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends Omit<PressableProps, "children"> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles = {
  primary: { container: "bg-primary", text: "text-white" },
  secondary: { container: "bg-secondary", text: "text-gray-900" },
  ghost: { container: "bg-transparent", text: "text-gray-700" },
} as const;

const sizeStyles = {
  sm: { container: "px-3 py-1.5", text: "text-sm" },
  md: { container: "px-4 py-2", text: "text-base" },
  lg: { container: "px-6 py-3", text: "text-lg" },
} as const;

export function Button({
  label,
  variant = "primary",
  size = "md",
  disabled,
  ...props
}: ButtonProps) {
  const vStyle = variantStyles[variant];
  const sStyle = sizeStyles[size];

  return (
    <Pressable
      className={`items-center justify-center rounded-lg ${vStyle.container} ${sStyle.container} ${disabled ? "opacity-50" : ""}`}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      {...props}
    >
      <Text className={`font-medium ${vStyle.text} ${sStyle.text}`}>
        {label}
      </Text>
    </Pressable>
  );
}
```

## Additional Context

**How to tell if something is an atom:**
- It renders a single semantic HTML element (or native equivalent)
- It has no imports from the component library
- It accepts styling/behavior props but no children components
- Examples: Button, Input, Label, Heading, Icon, Avatar, Badge, Divider, Spinner

**When to promote to molecule:**
- If your "atom" imports another atom, it is a molecule
- If it combines two distinct UI elements (icon + text, input + label), it is a molecule
- Move it to `molecules/` and update imports

**Atoms CAN:**
- Accept `children` for text content (e.g., `<Heading>Title</Heading>`)
- Use design tokens and theme values
- Handle their own internal state (e.g., hover, focus)
- Forward refs and spread HTML attributes

**Atoms CANNOT:**
- Import or render other components from the design system
- Fetch data or use data-fetching hooks
- Contain business logic or domain-specific behavior
