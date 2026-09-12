# Platform Integration Guide

Per-platform guides for consuming design tokens across Tailwind CSS (Vite SPA and Next.js), React Native, and Phlex (Rails).

---

## Tailwind CSS (Vite SPA & Next.js)

### Tailwind v4 — the token stylesheet

One stylesheet carries the whole token layer. In a shadcn/ui package it is the file
`components.json` names as `tailwind.css`: `globals.css` in Next.js, the entry stylesheet in the Vite
SPA. Three rules make it work:

1. **Variables hold complete colors**: `--primary: hsl(222.2 47.4% 11.2%)`. The numbers are the HSL
   triples `design-tokens.md` measures; only the delivery wraps them.
2. **`@theme inline` registers them**: `--color-primary: var(--primary)`. With `inline`, the utility
   emits `var(--primary)` itself, so it resolves on the element it styles and a nested `.dark`
   section flips. Opacity modifiers (`bg-primary/90`) compile to `color-mix()` over the complete
   color.
3. **`@custom-variant dark (&:is(.dark *))`** points `dark:` at the class. Without it, Tailwind v4's
   `dark:` follows `prefers-color-scheme` and ignores the toggle.

Arbitrary CSS reads the variable directly: `var(--primary)`. Never write `hsl(var(--primary))`,
which wraps a color in a color and resolves to `unset`.

```css
/* globals.css (Next.js) or the Vite entry stylesheet */
@import "tailwindcss";
@import "tw-animate-css"; /* shadcn/ui packages only: the primitives' CSS enter/exit animations */

@custom-variant dark (&:is(.dark *));

:root {
  --background: hsl(0 0% 100%);
  --foreground: hsl(222.2 84% 4.9%);
  --card: hsl(0 0% 100%);
  --card-foreground: hsl(222.2 84% 4.9%);
  --popover: hsl(0 0% 100%);
  --popover-foreground: hsl(222.2 84% 4.9%);
  --primary: hsl(222.2 47.4% 11.2%);
  --primary-foreground: hsl(210 40% 98%);
  --secondary: hsl(210 40% 96.1%);
  --secondary-foreground: hsl(222.2 47.4% 11.2%);
  --accent: hsl(210 40% 96.1%);
  --accent-foreground: hsl(222.2 47.4% 11.2%);
  --neutral: hsl(0 0% 46.1%);
  --muted: hsl(210 40% 96.1%);
  --muted-foreground: hsl(215.4 16.3% 44%);
  --success: hsl(142.1 76.2% 28%);
  --success-foreground: hsl(355.7 100% 97.3%);
  --warning: hsl(37.7 92.1% 50.2%);
  --warning-foreground: hsl(26 83.3% 14.1%);
  --error: hsl(0 84.2% 47%);
  --error-foreground: hsl(0 0% 98%);
  --info: hsl(199.4 95.5% 53.8%);
  --info-foreground: hsl(200 100% 10%);
  --border: hsl(214.3 31.8% 59%);
  --input: hsl(214.3 31.8% 59%);
  --ring: hsl(222.2 84% 4.9%);
  --chart-1: hsl(217.2 91.2% 50%);
  --chart-2: hsl(316 75% 42%);
  --chart-3: hsl(21 90% 42%);
  --chart-4: hsl(262.1 83.3% 57.8%);
  --chart-5: hsl(167 80% 28%);
  --radius: 0.5rem;
}

.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  --card: hsl(222.2 84% 4.9%);
  --card-foreground: hsl(210 40% 98%);
  --popover: hsl(222.2 84% 4.9%);
  --popover-foreground: hsl(210 40% 98%);
  --primary: hsl(210 40% 98%);
  --primary-foreground: hsl(222.2 47.4% 11.2%);
  --secondary: hsl(217.2 32.6% 17.5%);
  --secondary-foreground: hsl(210 40% 98%);
  --accent: hsl(217.2 32.6% 17.5%);
  --accent-foreground: hsl(210 40% 98%);
  --neutral: hsl(0 0% 63.9%);
  --muted: hsl(217.2 32.6% 17.5%);
  --muted-foreground: hsl(215 20.2% 65.1%);
  --success: hsl(142.1 70.6% 45.3%);
  --success-foreground: hsl(144.9 80.4% 10%);
  --warning: hsl(43.3 96.4% 56.3%);
  --warning-foreground: hsl(26 83.3% 14.1%);
  --error: hsl(0 62.8% 30.6%);
  --error-foreground: hsl(0 85.7% 97.3%);
  --info: hsl(199.4 80% 35%);
  --info-foreground: hsl(200 100% 95%);
  --border: hsl(217.2 32.6% 42%);
  --input: hsl(217.2 32.6% 42%);
  --ring: hsl(212.7 26.8% 83.9%);
  --chart-1: hsl(213 94% 62%);
  --chart-2: hsl(322 81% 58%);
  --chart-3: hsl(20.5 90.2% 48.2%);
  --chart-4: hsl(258.3 89.5% 66.3%);
  --chart-5: hsl(180 80% 36%);
}

/* shadcn/ui aliases (Next.js and Vite SPA shadcn packages only): var() references to house roles.
   Declared on both scopes so a nested .dark section re-resolves them. Never a copied value. */
:root,
.dark {
  --destructive: var(--error);
  --destructive-foreground: var(--error-foreground);
  --sidebar: var(--card);
  --sidebar-foreground: var(--card-foreground);
  --sidebar-primary: var(--primary);
  --sidebar-primary-foreground: var(--primary-foreground);
  --sidebar-accent: var(--accent);
  --sidebar-accent-foreground: var(--accent-foreground);
  --sidebar-border: var(--border);
  --sidebar-ring: var(--ring);
}

@theme {
  --font-sans: "Inter", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-card: var(--card);
  --color-card-foreground: var(--card-foreground);
  --color-popover: var(--popover);
  --color-popover-foreground: var(--popover-foreground);
  --color-primary: var(--primary);
  --color-primary-foreground: var(--primary-foreground);
  --color-secondary: var(--secondary);
  --color-secondary-foreground: var(--secondary-foreground);
  --color-accent: var(--accent);
  --color-accent-foreground: var(--accent-foreground);
  --color-muted: var(--muted);
  --color-muted-foreground: var(--muted-foreground);
  --color-success: var(--success);
  --color-success-foreground: var(--success-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
  --color-error: var(--error);
  --color-error-foreground: var(--error-foreground);
  --color-info: var(--info);
  --color-info-foreground: var(--info-foreground);
  --color-border: var(--border);
  --color-input: var(--input);
  --color-ring: var(--ring);

  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
  --color-sidebar-primary: var(--sidebar-primary);
  --color-sidebar-primary-foreground: var(--sidebar-primary-foreground);
  --color-sidebar-accent: var(--sidebar-accent);
  --color-sidebar-accent-foreground: var(--sidebar-accent-foreground);
  --color-sidebar-border: var(--sidebar-border);
  --color-sidebar-ring: var(--sidebar-ring);

  --color-chart-1: var(--chart-1);
  --color-chart-2: var(--chart-2);
  --color-chart-3: var(--chart-3);
  --color-chart-4: var(--chart-4);
  --color-chart-5: var(--chart-5);

  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}

/* Mandatory: tw-animate-css ships no reduced-motion rule (std-design-system motion.md) */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

This generates utility classes like `bg-primary`, `text-primary-foreground`, `border-border`,
`bg-sidebar-accent` and `rounded-lg` that resolve to the design tokens. Font families are literal
values, so they sit in a plain `@theme`. A `next/font` variable is a reference, so it goes through
`@theme inline { --font-sans: var(--font-inter), ui-sans-serif, system-ui, sans-serif; }`.

Packages without shadcn/ui drop the `tw-animate-css` import and the alias block. Nothing else changes.

### shadcn/ui token aliases

shadcn/ui source names ten tokens after its own roles. The registry declares them as aliases, so
every `add` compiles unmodified and `add --diff` merges stay small:

| Alias | Resolves to | Rendered by |
|---|---|---|
| `destructive` / `destructive-foreground` | `error` / `error-foreground` | Button, Badge and Alert destructive variants, invalid form controls |
| `sidebar` / `sidebar-foreground` | `card` / `card-foreground` | The Sidebar primitive and sidebar blocks |
| `sidebar-primary` / `sidebar-primary-foreground` | `primary` / `primary-foreground` | Sidebar blocks; the primitive itself does not use them |
| `sidebar-accent` / `sidebar-accent-foreground` | `accent` / `accent-foreground` | Hovered and active sidebar items |
| `sidebar-border` | `border` | Sidebar edges and rail |
| `sidebar-ring` | `ring` | Sidebar focus |

- **An alias is a `var()` reference, never a value.** A copied value is one role with two numbers,
  and it cannot follow a preset swap. The pairs an alias renders are measured through its role in
  `design-tokens.md`.
- **Declared on `:root, .dark`.** A custom property holding `var()` is substituted where it is
  declared. Declared on `:root` alone, a nested `.dark` section inherits the light result.
- **Code the house writes names the role** (`bg-error`, `bg-card`). The aliases are for vendored
  shadcn source, not new vocabulary.
- **Aliasing fixes names, not values.** shadcn source still carries raw `text-white`, `bg-black/50`
  and `bg-white`, plus `dark:` opacity overrides tuned to its own palette. Those are edits, owned by
  the `std-shadcn-ui` skill (`@skills/std-shadcn-ui/references/components-and-blocks.md`).
- Phlex and React Native packages carry no alias block.

### Chart colors

Every stack's charts draw from the same `chart-1`…`chart-5` tokens, each through its house library:
Next.js through shadcn/ui's `chart` component (below), the Vite SPA through Chart.js with
`useChartTokens` (`@skills/std-reactjs/references/charts.md`), and Rails Phlex views through the house
`chart` Stimulus controller on Chart.js (`@skills/std-phlex-conventions/references/charts.md`). The
series rules after the example hold on all three.

In Next.js, shadcn/ui's chart component composes Recharts. It reads colors from `ChartConfig` and
injects each one as `--color-<key>` under the chart's `data-chart` scope. Point every entry at a
series token:

```tsx
// inside the component, after const t = useTranslations("dashboard")
const chartConfig = {
  revenue: { label: t("revenue"), color: "var(--chart-1)" },
  refunds: { label: t("refunds"), color: "var(--chart-2)" },
} satisfies ChartConfig;
```

- Write `var(--chart-1)`, never `hsl(var(--chart-1))`: the variable already holds a complete color.
- **Series take slots in order and never cycle.** Color follows the entity, so a filter that drops a
  series must not repaint the survivors. A sixth series folds into "Other" or becomes small
  multiples.
- **Scatter, bubble and small-multiple charts carry at most three series.** Only `chart-1`…`chart-3`
  stay apart pairwise under simulated protanopia and deuteranopia; the measurements are in
  `design-tokens.md`.
- **Never color alone.** Use a legend for two or more series, direct labels where there is room, and
  a text alternative (a summary or a data table). `accessibilityLayer` adds keyboard access and
  screen-reader support, not a text alternative.
- **A series never shares a chart with status colors.** A series that *means* good or bad wears
  `success`/`error` with an icon and a label, and then it is not a `chart-N`.
- Charts animate in JS, which the CSS backstop cannot stop. Pass `isAnimationActive={!reduce}` to
  each Recharts series; Chart.js takes `animation: false` under reduced motion.

The chart component itself (install, tooltip and legend composition, the text alternative's
markup) is owned by the `std-shadcn-ui` skill (`@skills/std-shadcn-ui/references/charts.md`); the
Vite SPA's and Rails views' Chart.js charts by `@skills/std-reactjs/references/charts.md` and
`@skills/std-phlex-conventions/references/charts.md`.

### What the shadcn CLI does to this file

- `shadcn init` writes its own palette over this stylesheet, as oklch values. Never run it on an
  existing app without asking.
- `add` can append CSS variables. The new-york-v4 `sidebar` item still ships legacy
  `--sidebar-background`-style variables as bare HSL channels. Read the stylesheet back after every
  `add` and delete anything appended beside the alias block.
- `init` writes `* { @apply border-border outline-ring/50; }` into the base layer. `ring` at 50%
  measures 3.76:1 on the default light background, but 2.26:1 in Modern light and 1.66:1 in Modern
  dark. The house base layer above drops the `/50`.

The CLI protocol (reuse, `add`, `--dry-run`/`--diff`, what needs a human) is owned by
`@skills/std-shadcn-ui/references/cli-and-registry.md`.

### Tailwind v3 packages (legacy)

Tailwind v3 cannot apply an opacity modifier to a complete color, so the stylesheet above does not
work there. v3 needs channel variables and `hsl(var(--x) / <alpha-value>)` in `tailwind.config.ts`.
A v3 package keeps that wiring until it migrates (`npx @tailwindcss/upgrade`), and never mixes the
two forms in one package. shadcn/ui and the `cn` package are v4-only, so a v3 package adopts
neither.

### Tailwind Usage Examples

```tsx
// Button component
function Button({ children, variant = "primary" }: ButtonProps) {
  const variants = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    accent: "bg-accent text-accent-foreground hover:bg-accent/80",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    ghost: "hover:bg-accent hover:text-accent-foreground",
    destructive: "bg-error text-error-foreground hover:bg-error/90",
  };

  return (
    <button className={`inline-flex items-center justify-center rounded-md px-4 py-2
      text-sm font-medium motion-safe:transition-colors focus-visible:outline-none
      focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2
      disabled:pointer-events-none disabled:opacity-50
      ${variants[variant]}`}>
      {children}
    </button>
  );
}

// Card component
function Card({ title, children }: CardProps) {
  return (
    <div className="rounded-lg border border-border bg-card text-card-foreground shadow-sm">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <p className="mt-2 text-sm text-muted-foreground">{children}</p>
      </div>
    </div>
  );
}
```

---

## React Native

### Token Object

Define tokens as a JavaScript object mirroring the CSS custom property structure. Use camelCase naming:

```typescript
// theme/tokens.ts — values mirror the measured spec in design-tokens.md.
// The shadcn/ui aliases (destructive, sidebar-*) are web wiring and never appear here.
export const lightTokens = {
  colors: {
    background: "hsl(0, 0%, 100%)",
    foreground: "hsl(222.2, 84%, 4.9%)",

    primary: "hsl(222.2, 47.4%, 11.2%)",
    primaryForeground: "hsl(210, 40%, 98%)",

    secondary: "hsl(210, 40%, 96.1%)",
    secondaryForeground: "hsl(222.2, 47.4%, 11.2%)",

    accent: "hsl(210, 40%, 96.1%)",
    accentForeground: "hsl(222.2, 47.4%, 11.2%)",

    muted: "hsl(210, 40%, 96.1%)",
    mutedForeground: "hsl(215.4, 16.3%, 44%)",

    card: "hsl(0, 0%, 100%)",
    cardForeground: "hsl(222.2, 84%, 4.9%)",

    popover: "hsl(0, 0%, 100%)",
    popoverForeground: "hsl(222.2, 84%, 4.9%)",

    success: "hsl(142.1, 76.2%, 28%)",
    successForeground: "hsl(355.7, 100%, 97.3%)",

    warning: "hsl(37.7, 92.1%, 50.2%)",
    warningForeground: "hsl(26, 83.3%, 14.1%)",

    error: "hsl(0, 84.2%, 47%)",
    errorForeground: "hsl(0, 0%, 98%)",

    info: "hsl(199.4, 95.5%, 53.8%)",
    infoForeground: "hsl(200, 100%, 10%)",

    border: "hsl(214.3, 31.8%, 59%)",
    input: "hsl(214.3, 31.8%, 59%)",
    ring: "hsl(222.2, 84%, 4.9%)",
  },

  typography: {
    fontFamily: {
      sans: "Inter",
      mono: "JetBrainsMono",
    },
    fontSize: {
      xs: 12,
      sm: 14,
      base: 16,
      lg: 18,
      xl: 20,
      "2xl": 24,
      "3xl": 30,
      "4xl": 36,
      "5xl": 48,
    },
    fontWeight: {
      light: "300" as const,
      normal: "400" as const,
      medium: "500" as const,
      semibold: "600" as const,
      bold: "700" as const,
    },
    lineHeight: {
      tight: 1.25,
      snug: 1.375,
      normal: 1.5,
      relaxed: 1.625,
      loose: 2,
    },
  },

  spacing: {
    0.5: 2,
    1: 4,
    1.5: 6,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
    6: 24,
    8: 32,
    10: 40,
    12: 48,
    16: 64,
    20: 80,
    24: 96,
  },

  borderRadius: {
    none: 0,
    sm: 2,
    default: 4,
    md: 6,
    lg: 8,
    xl: 12,
    "2xl": 16,
    full: 9999,
  },
} as const;

export const darkTokens: typeof lightTokens = {
  ...lightTokens,
  colors: {
    background: "hsl(222.2, 84%, 4.9%)",
    foreground: "hsl(210, 40%, 98%)",

    primary: "hsl(210, 40%, 98%)",
    primaryForeground: "hsl(222.2, 47.4%, 11.2%)",

    secondary: "hsl(217.2, 32.6%, 17.5%)",
    secondaryForeground: "hsl(210, 40%, 98%)",

    accent: "hsl(217.2, 32.6%, 17.5%)",
    accentForeground: "hsl(210, 40%, 98%)",

    muted: "hsl(217.2, 32.6%, 17.5%)",
    mutedForeground: "hsl(215, 20.2%, 65.1%)",

    card: "hsl(222.2, 84%, 4.9%)",
    cardForeground: "hsl(210, 40%, 98%)",

    popover: "hsl(222.2, 84%, 4.9%)",
    popoverForeground: "hsl(210, 40%, 98%)",

    success: "hsl(142.1, 70.6%, 45.3%)",
    successForeground: "hsl(144.9, 80.4%, 10%)",

    warning: "hsl(43.3, 96.4%, 56.3%)",
    warningForeground: "hsl(26, 83.3%, 14.1%)",

    error: "hsl(0, 62.8%, 30.6%)",
    errorForeground: "hsl(0, 85.7%, 97.3%)",

    info: "hsl(199.4, 80%, 35%)",
    infoForeground: "hsl(200, 100%, 95%)",

    border: "hsl(217.2, 32.6%, 42%)",
    input: "hsl(217.2, 32.6%, 42%)",
    ring: "hsl(212.7, 26.8%, 83.9%)",
  },
};

export type Theme = typeof lightTokens;
```

### ThemeProvider

```typescript
// theme/ThemeProvider.tsx
import React, { createContext, useContext, useMemo } from "react";
import { useColorScheme } from "react-native";
import { useMMKVString } from "react-native-mmkv";

import { lightTokens, darkTokens, type Theme } from "./tokens";

type ThemeMode = "light" | "dark" | "system";

interface ThemeContextValue {
  theme: Theme;
  mode: ThemeMode;
  isDark: boolean;
  setMode: (mode: ThemeMode) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

interface ThemeProviderProps {
  children: React.ReactNode;
  defaultMode?: ThemeMode;
}

export function ThemeProvider({ children, defaultMode = "system" }: ThemeProviderProps) {
  const systemScheme = useColorScheme();
  const [storedMode, setStoredMode] = useMMKVString("theme-mode");

  const mode = (storedMode as ThemeMode) ?? defaultMode;

  const isDark = useMemo(() => {
    if (mode === "system") {
      return systemScheme === "dark";
    }
    return mode === "dark";
  }, [mode, systemScheme]);

  const theme = isDark ? darkTokens : lightTokens;

  const value = useMemo<ThemeContextValue>(
    () => ({
      theme,
      mode,
      isDark,
      setMode: (newMode: ThemeMode) => setStoredMode(newMode),
    }),
    [theme, mode, isDark, setStoredMode],
  );

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
}
```

### Themed Component Example

```typescript
// components/ThemedCard.tsx
import { View, Text, StyleSheet } from "react-native";
import { useTheme } from "../theme/ThemeProvider";

interface ThemedCardProps {
  title: string;
  description: string;
}

export function ThemedCard({ title, description }: ThemedCardProps) {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  return (
    <View style={styles.card}>
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.description}>{description}</Text>
    </View>
  );
}

function createStyles(theme: Theme) {
  return StyleSheet.create({
    card: {
      backgroundColor: theme.colors.card,
      borderRadius: theme.borderRadius.lg,
      borderWidth: 1,
      borderColor: theme.colors.border,
      padding: theme.spacing[6],
      shadowColor: "#000",
      shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05,
      shadowRadius: 2,
      elevation: 1,
    },
    title: {
      fontFamily: theme.typography.fontFamily.sans,
      fontSize: theme.typography.fontSize.lg,
      fontWeight: theme.typography.fontWeight.semibold,
      color: theme.colors.cardForeground,
      lineHeight: theme.typography.fontSize.lg * theme.typography.lineHeight.tight,
    },
    description: {
      fontFamily: theme.typography.fontFamily.sans,
      fontSize: theme.typography.fontSize.sm,
      fontWeight: theme.typography.fontWeight.normal,
      color: theme.colors.mutedForeground,
      lineHeight: theme.typography.fontSize.sm * theme.typography.lineHeight.normal,
      marginTop: theme.spacing[2],
    },
  });
}
```

### App Entry Point

```typescript
// App.tsx
import { ThemeProvider } from "./theme/ThemeProvider";
import { NavigationContainer } from "@react-navigation/native";

export default function App() {
  return (
    <ThemeProvider defaultMode="system">
      <NavigationContainer>
        {/* App screens */}
      </NavigationContainer>
    </ThemeProvider>
  );
}
```

---

## Phlex (Rails)

### Global CSS Custom Properties

Phlex takes the same Tailwind v4 token stylesheet as the web apps, so a class in a Phlex component
resolves to the same value as in React:

```css
/* the Tailwind entry stylesheet (tailwindcss-rails) */
@import "tailwindcss";

@custom-variant dark (&:is(.dark *));

:root {
  /* every value from design-tokens.md, written as hsl() */
  --background: hsl(0 0% 100%);
  --foreground: hsl(222.2 84% 4.9%);
  --primary: hsl(222.2 47.4% 11.2%);
  --primary-foreground: hsl(210 40% 98%);
  /* ... */
  --radius: 0.5rem;
}

.dark {
  --background: hsl(222.2 84% 4.9%);
  --foreground: hsl(210 40% 98%);
  --primary: hsl(210 40% 98%);
  --primary-foreground: hsl(222.2 47.4% 11.2%);
  /* ... */
}

/* The @theme inline registry and the reduced-motion backstop are identical to the Tailwind v4
   section above. There is no shadcn/ui alias block, because Phlex is not a shadcn package. */
```

### Phlex Components with Tailwind

Phlex components use Tailwind utility classes that resolve to the CSS custom properties:

```ruby
# app/views/components/button.rb
class Components::Button < Phlex::HTML
  VARIANTS = {
    primary: "bg-primary text-primary-foreground hover:bg-primary/90",
    secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    ghost: "hover:bg-accent hover:text-accent-foreground",
    destructive: "bg-error text-error-foreground hover:bg-error/90",
  }.freeze

  SIZES = {
    sm: "h-9 px-3 text-sm rounded-md",
    md: "h-10 px-4 py-2 text-sm rounded-md",
    lg: "h-11 px-8 text-base rounded-md",
  }.freeze

  def initialize(variant: :primary, size: :md, **attributes)
    @variant = variant
    @size = size
    @attributes = attributes
  end

  def view_template(&block)
    button(
      class: tokens(
        "inline-flex items-center justify-center font-medium",
        "transition-colors focus-visible:outline-none",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        VARIANTS[@variant],
        SIZES[@size],
      ),
      **@attributes,
      &block
    )
  end
end
```

### `class_variants` Gem Integration

For more structured variant management, use the `class_variants` gem:

```ruby
# app/views/components/badge.rb
class Components::Badge < Phlex::HTML
  include ClassVariants

  BADGE_VARIANTS = class_variants(
    base: "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary: "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        outline: "text-foreground",
        success: "border-transparent bg-success text-success-foreground",
        warning: "border-transparent bg-warning text-warning-foreground",
        error: "border-transparent bg-error text-error-foreground",
      },
    },
    defaults: {
      variant: :default,
    },
  )

  def initialize(variant: :default, **attributes)
    @variant = variant
    @attributes = attributes
  end

  def view_template(&block)
    div(class: BADGE_VARIANTS.render(variant: @variant), **@attributes, &block)
  end
end
```

### Phlex Card Component

```ruby
# app/views/components/card.rb
class Components::Card < Phlex::HTML
  def initialize(title: nil, description: nil, **attributes)
    @title = title
    @description = description
    @attributes = attributes
  end

  def view_template(&block)
    div(
      class: "rounded-lg border border-border bg-card text-card-foreground shadow-sm",
      **@attributes,
    ) do
      if @title || @description
        div(class: "p-6") do
          h3(class: "text-lg font-semibold text-foreground") { @title } if @title
          p(class: "mt-2 text-sm text-muted-foreground") { @description } if @description
        end
      end
      block&.call
    end
  end
end
```

---

## Dark / Light Mode

### Class, not media query

The `.dark` class is the only dark-mode switch. A `@media (prefers-color-scheme: dark)` token
block cannot be overridden, so a user on a dark OS has no path to light mode. The OS preference is
the **default** (`system`), never the mechanism. Tailwind v4's `dark:` variant follows the media
query unless the stylesheet declares `@custom-variant dark (&:is(.dark *));`.

```html
<!-- Light mode -->
<html lang="en">

<!-- Dark mode -->
<html lang="en" class="dark">
```

### Vite SPA — the house provider

The house `ThemeProvider` is in `@skills/std-design-system/references/defining-tokens.md`. It is a
persisted `light | dark | system` store that toggles `.dark` on `<html>` and follows the OS while
set to `system`. It applies the class in an effect, which runs after first paint. So pair it with a
pre-paint script, or a dark-OS user sees a white flash on every load:

```html
<!-- index.html, inside <head>, before the stylesheet -->
<script>
  (function () {
    var root = document.documentElement;
    try {
      var stored = JSON.parse(localStorage.getItem("theme") || "null");
      var theme = (stored && stored.state && stored.state.theme) || "system";
      var dark = theme === "dark" ||
        (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      root.classList.toggle("dark", dark);
    } catch (e) {
      root.classList.remove("dark"); // storage blocked: start light, the provider corrects it
    }
  })();
</script>
```

The key is `"theme"`, and the shape is what zustand's `persist` writes (`{"state":{"theme":…}}`).
The script and the provider must read the same record.

### React Native `useColorScheme()`

React Native provides the `useColorScheme()` hook for system theme detection. This is already integrated in the `ThemeProvider` shown above:

```typescript
import { useColorScheme } from "react-native";

function MyComponent() {
  const systemScheme = useColorScheme(); // "light" | "dark" | null
  // Use the ThemeProvider's useTheme() hook instead of this directly
}
```

For theme persistence in React Native, use `react-native-mmkv`:

```typescript
import { MMKV } from "react-native-mmkv";

const storage = new MMKV();

// Save preference
storage.set("theme-mode", "dark"); // "light" | "dark" | "system"

// Read preference
const mode = storage.getString("theme-mode") ?? "system";
```

### Next.js — `next-themes`

Next.js uses `next-themes` because the class has to be right before hydration. This is the shape
shadcn/ui documents, and sonner's `Toaster` reads this same provider.

```tsx
// components/theme-provider.tsx
"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

export function ThemeProvider(props: ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props} />;
}
```

```tsx
// app/layout.tsx
import { ThemeProvider } from "@/components/theme-provider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

`suppressHydrationWarning` belongs on `<html>` only. next-themes writes the class there before
hydration, so that one element legitimately differs, and spreading the attribute further hides
real mismatches. `disableTransitionOnChange` stops every `transition-colors` from animating the
swap.

```tsx
// components/theme-toggle.tsx
"use client";

import { useTheme } from "next-themes";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("theme");
  const [mounted, setMounted] = useState(false);

  // resolvedTheme is unknown on the server: render nothing until mounted
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  const next = resolvedTheme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className="rounded-md p-2 hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      aria-label={t(next === "dark" ? "switchToDark" : "switchToLight")}
    >
      {t(next)}
    </button>
  );
}
```

Read `resolvedTheme`, not `theme`. With `defaultTheme="system"`, `theme` is `"system"`, so
`theme === "dark"` is false for every dark-OS user, and their first click sets the mode they
already have.

### Dark token values

The `.dark` block belongs to the token stylesheet above, and its measured values are in
`design-tokens.md`. This file used to carry a second copy, and it drifted: it still had `--info` at
46% lightness after the spec darkened it to 35% to clear AA. So there is no second copy.

### Theme Persistence Summary

| Platform | Storage | Key |
|----------|---------|-----|
| Vite SPA | `localStorage` | `"theme"` |
| Next.js | `next-themes` (uses `localStorage` internally) | `"theme"` (configurable) |
| React Native | `react-native-mmkv` | `"theme-mode"` |
| Rails/Phlex | `localStorage` (via Stimulus or inline JS) | `"theme"` |
