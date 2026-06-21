---
title: "Atoms Must Use Design Tokens"
id: atom-theming-tokens
impact: HIGH
tags: [atomic-design, atoms, theming]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Atoms Must Use Design Tokens

Atoms must consume design tokens (CSS custom properties, Tailwind theme values, or platform theme objects) instead of hardcoding colors, sizes, spacing, fonts, or other visual values. This ensures theme consistency, dark mode support, and design system scalability.

## Incorrect

Hardcoded hex colors, pixel values, or arbitrary Tailwind values bypass the design system and break theme switching.

```tsx
// WRONG: Hardcoded color values
export function Badge({ label }: { label: string }) {
  return (
    <span style={{ backgroundColor: "#3b82f6", color: "#ffffff", padding: "4px 8px" }}>
      {label}
    </span>
  );
}
```

```tsx
// WRONG: Arbitrary Tailwind values instead of theme tokens
export function Badge({ label }: { label: string }) {
  return (
    <span className="bg-[#3b82f6] text-[#ffffff] px-[8px] py-[4px] rounded-[4px]">
      {label}
    </span>
  );
}
```

```ruby
# WRONG: Hardcoded inline styles in Phlex
class Components::Atoms::Badge < Components::Base
  def view_template
    span(style: "background-color: #3b82f6; color: #fff; padding: 4px 8px;") { @label }
  end
end
```

## Correct

Use semantic token names that map to the design system.

### Phlex (Rails)

```ruby
# backend/app/components/atoms/badge.rb
class Components::Atoms::Badge < Components::Base
  VARIANTS = {
    info: "bg-info text-info-foreground",
    success: "bg-success text-success-foreground",
    warning: "bg-warning text-warning-foreground",
    error: "bg-error text-error-foreground",
    neutral: "bg-neutral text-neutral-foreground",
  }.freeze

  def initialize(label:, variant: :neutral, size: :md)
    @label = label
    @variant = variant
    @size = size
  end

  def view_template
    span(class: badge_classes) { @label }
  end

  private

  def badge_classes
    [
      "inline-flex items-center font-medium rounded-full",
      VARIANTS.fetch(@variant),
      size_class,
    ].join(" ")
  end

  def size_class
    case @size
    when :sm then "px-2 py-0.5 text-xs"
    when :md then "px-2.5 py-1 text-sm"
    when :lg then "px-3 py-1.5 text-base"
    end
  end
end
```

### ReactJS (Vite SPA)

```tsx
// web/src/components/atoms/Badge/Badge.tsx
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type BadgeVariant = "info" | "success" | "warning" | "error" | "neutral";
type BadgeSize = "sm" | "md" | "lg";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  info: "bg-info text-info-foreground",
  success: "bg-success text-success-foreground",
  warning: "bg-warning text-warning-foreground",
  error: "bg-error text-error-foreground",
  neutral: "bg-neutral text-neutral-foreground",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-base",
};

export function Badge({
  label,
  variant = "neutral",
  size = "md",
  className,
}: BadgeProps) {
  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center font-medium rounded-full",
          variantStyles[variant],
          sizeStyles[size],
          className,
        ),
      )}
    >
      {label}
    </span>
  );
}
```

### Next.js (App Router)

```tsx
// next/src/components/atoms/Badge/Badge.tsx
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type BadgeVariant = "info" | "success" | "warning" | "error" | "neutral";
type BadgeSize = "sm" | "md" | "lg";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  info: "bg-info text-info-foreground",
  success: "bg-success text-success-foreground",
  warning: "bg-warning text-warning-foreground",
  error: "bg-error text-error-foreground",
  neutral: "bg-neutral text-neutral-foreground",
};

const sizeStyles: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
  lg: "px-3 py-1.5 text-base",
};

export function Badge({
  label,
  variant = "neutral",
  size = "md",
  className,
}: BadgeProps) {
  return (
    <span
      className={twMerge(
        clsx(
          "inline-flex items-center font-medium rounded-full",
          variantStyles[variant],
          sizeStyles[size],
          className,
        ),
      )}
    >
      {label}
    </span>
  );
}
```

### React Native

```tsx
// mobile/src/components/atoms/Badge/Badge.tsx
import { View, Text } from "react-native";
import { useTheme } from "@/theme/useTheme";

type BadgeVariant = "info" | "success" | "warning" | "error" | "neutral";
type BadgeSize = "sm" | "md" | "lg";

interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
}

export function Badge({
  label,
  variant = "neutral",
  size = "md",
}: BadgeProps) {
  const theme = useTheme();

  const variantColors = {
    info: { bg: theme.colors.info, text: theme.colors.infoForeground },
    success: { bg: theme.colors.success, text: theme.colors.successForeground },
    warning: { bg: theme.colors.warning, text: theme.colors.warningForeground },
    error: { bg: theme.colors.error, text: theme.colors.errorForeground },
    neutral: { bg: theme.colors.neutral, text: theme.colors.neutralForeground },
  };

  const sizeStyles = {
    sm: { paddingHorizontal: theme.spacing[2], paddingVertical: theme.spacing[0.5], fontSize: theme.fontSizes.xs },
    md: { paddingHorizontal: theme.spacing[2.5], paddingVertical: theme.spacing[1], fontSize: theme.fontSizes.sm },
    lg: { paddingHorizontal: theme.spacing[3], paddingVertical: theme.spacing[1.5], fontSize: theme.fontSizes.base },
  };

  const colors = variantColors[variant];
  const sizing = sizeStyles[size];

  return (
    <View
      style={{
        backgroundColor: colors.bg,
        paddingHorizontal: sizing.paddingHorizontal,
        paddingVertical: sizing.paddingVertical,
        borderRadius: theme.radii.full,
        alignSelf: "flex-start",
      }}
      accessibilityRole="text"
    >
      <Text
        style={{
          color: colors.text,
          fontSize: sizing.fontSize,
          fontWeight: theme.fontWeights.medium,
        }}
      >
        {label}
      </Text>
    </View>
  );
}
```

## Additional Context

**Design token categories that atoms must reference:**
- **Colors**: `primary`, `secondary`, `success`, `warning`, `error`, `neutral` and their foreground/background variants
- **Spacing**: Use the spacing scale (`spacing[1]`, `spacing[2]`, etc.) not raw pixel values
- **Typography**: Font sizes, weights, and line heights from the type scale
- **Radii**: Border radius values from the radii scale (`rounded-sm`, `rounded-lg`, etc.)
- **Shadows**: Elevation values from the shadow scale

**Acceptable exceptions:**
- Layout-specific values like `flex-1`, `items-center`, `justify-between` are not design tokens -- they are structural and acceptable to use directly
- Transition durations may use standard values (`transition-colors`, `duration-150`)
- Z-index values that are component-scoped

**Dark mode compliance:**
- When atoms use semantic tokens (e.g., `bg-primary` instead of `bg-blue-500`), dark mode works automatically through CSS custom properties or theme provider swaps
- Hardcoded values break dark mode and require manual overrides
