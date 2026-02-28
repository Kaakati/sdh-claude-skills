# Platform Integration Guide

Per-platform guides for consuming design tokens across Tailwind CSS (Vite SPA and Next.js), React Native, and Phlex (Rails).

---

## Tailwind CSS (Vite SPA & Next.js)

### Tailwind v4 -- `@theme` Directive

Tailwind v4 uses CSS-native configuration via the `@theme` directive. Define tokens directly in your CSS entry point:

```css
/* app.css (Vite) or globals.css (Next.js) */
@import "tailwindcss";

@theme {
  /* Colors - reference CSS custom properties */
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));

  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));

  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));

  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));

  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));

  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));

  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));

  --color-success: hsl(var(--success));
  --color-success-foreground: hsl(var(--success-foreground));

  --color-warning: hsl(var(--warning));
  --color-warning-foreground: hsl(var(--warning-foreground));

  --color-error: hsl(var(--error));
  --color-error-foreground: hsl(var(--error-foreground));

  --color-info: hsl(var(--info));
  --color-info-foreground: hsl(var(--info-foreground));

  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));

  /* Typography */
  --font-sans: var(--font-sans);
  --font-mono: var(--font-mono);

  /* Border Radius */
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}
```

This generates utility classes like `bg-primary`, `text-primary-foreground`, `border-border`, and `rounded-lg` that automatically resolve to your design tokens.

### Tailwind v3 Fallback -- `tailwind.config.ts`

For projects still on Tailwind v3, extend the theme in the config file:

```typescript
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/**/*.{ts,tsx}",        // Vite SPA
    "./app/**/*.{ts,tsx}",        // Next.js App Router
    "./components/**/*.{ts,tsx}", // Shared components
  ],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        error: {
          DEFAULT: "hsl(var(--error))",
          foreground: "hsl(var(--error-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        mono: ["var(--font-mono)"],
      },
    },
  },
  plugins: [],
};

export default config;
```

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
      text-sm font-medium transition-colors focus-visible:outline-none
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
// theme/tokens.ts
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
    mutedForeground: "hsl(215.4, 16.3%, 46.9%)",

    card: "hsl(0, 0%, 100%)",
    cardForeground: "hsl(222.2, 84%, 4.9%)",

    success: "hsl(142.1, 76.2%, 36.3%)",
    successForeground: "hsl(355.7, 100%, 97.3%)",

    warning: "hsl(37.7, 92.1%, 50.2%)",
    warningForeground: "hsl(26, 83.3%, 14.1%)",

    error: "hsl(0, 84.2%, 60.2%)",
    errorForeground: "hsl(0, 0%, 98%)",

    info: "hsl(199.4, 95.5%, 53.8%)",
    infoForeground: "hsl(200, 100%, 10%)",

    border: "hsl(214.3, 31.8%, 91.4%)",
    input: "hsl(214.3, 31.8%, 91.4%)",
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

    success: "hsl(142.1, 70.6%, 45.3%)",
    successForeground: "hsl(144.9, 80.4%, 10%)",

    warning: "hsl(43.3, 96.4%, 56.3%)",
    warningForeground: "hsl(26, 83.3%, 14.1%)",

    error: "hsl(0, 62.8%, 30.6%)",
    errorForeground: "hsl(0, 85.7%, 97.3%)",

    info: "hsl(199.4, 80%, 46%)",
    infoForeground: "hsl(200, 100%, 95%)",

    border: "hsl(217.2, 32.6%, 17.5%)",
    input: "hsl(217.2, 32.6%, 17.5%)",
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

Include the design token CSS in the Rails layout. Create a dedicated stylesheet for tokens:

```css
/* app/assets/stylesheets/tokens.css */
:root {
  /* All tokens from design-tokens.md :root block */
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;
  /* ... (all other tokens) */
  --radius: 0.5rem;
}

.dark {
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  --primary: 210 40% 98%;
  --primary-foreground: 222.2 47.4% 11.2%;
  /* ... (all other dark overrides) */
}
```

Import this in the application stylesheet or the Rails layout `<head>`.

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

### CSS `prefers-color-scheme` (Automatic)

For systems that follow the OS preference without user toggle:

```css
@media (prefers-color-scheme: dark) {
  :root {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    /* ... all dark overrides */
  }
}
```

### Class Toggle (Tailwind `darkMode: 'class'`)

For user-controllable theme switching, use a `.dark` class on `<html>`:

```html
<!-- Light mode -->
<html lang="en">

<!-- Dark mode -->
<html lang="en" class="dark">
```

```typescript
// Theme toggle utility (Vite SPA)
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.contains("dark");

  if (isDark) {
    html.classList.remove("dark");
    localStorage.setItem("theme", "light");
  } else {
    html.classList.add("dark");
    localStorage.setItem("theme", "dark");
  }
}

// Initialize on page load
function initializeTheme() {
  const stored = localStorage.getItem("theme");
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;

  if (stored === "dark" || (!stored && prefersDark)) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
}
```

### System Detection with `window.matchMedia`

Listen for OS-level theme changes in real time:

```typescript
// Watch for system theme changes
const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

mediaQuery.addEventListener("change", (event) => {
  const stored = localStorage.getItem("theme");
  // Only auto-switch if user hasn't explicitly chosen a theme
  if (!stored) {
    if (event.matches) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }
});
```

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

### Next.js with `next-themes`

For Next.js App Router, use `next-themes` for SSR-safe theme management:

```typescript
// app/providers.tsx
"use client";

import { ThemeProvider } from "next-themes";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </ThemeProvider>
  );
}

// app/layout.tsx
import { Providers } from "./providers";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

Theme toggle component for Next.js:

```typescript
// components/theme-toggle.tsx
"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Avoid hydration mismatch
  useEffect(() => setMounted(true), []);
  if (!mounted) return null;

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="rounded-md p-2 hover:bg-accent"
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}
```

### Dark Token Override Block

Complete dark mode CSS variable overrides -- place in the same stylesheet as `:root` tokens:

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

  /* Core Palette (inverted for dark) */
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

  --info: 199.4 80% 46%;
  --info-foreground: 200 100% 95%;

  /* Borders & Ring */
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 212.7 26.8% 83.9%;
}
```

### Theme Persistence Summary

| Platform | Storage | Key |
|----------|---------|-----|
| Vite SPA | `localStorage` | `"theme"` |
| Next.js | `next-themes` (uses `localStorage` internally) | `"theme"` (configurable) |
| React Native | `react-native-mmkv` | `"theme-mode"` |
| Rails/Phlex | `localStorage` (via Stimulus or inline JS) | `"theme"` |
