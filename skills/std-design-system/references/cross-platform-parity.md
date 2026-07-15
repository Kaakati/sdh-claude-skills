# Cross-Platform Token Parity

Read this when a token has to exist on **more than one platform** — React Native alongside web, or
Phlex alongside a React SPA — or when you are building the React Native theme layer. Web-only work
does not need this file.

Load-bearing rules restated (assume nothing else here has been read):

1. **Token names are identical across platforms.** `primary` on web is `primary` in React Native.
   A renamed token is a broken token.
2. **Same 4px spacing base and same type scale ratios everywhere.**
3. React Native has no CSS custom properties and no `.dark` class — it consumes tokens through a
   **theme context**, not a stylesheet.
4. Touch targets: **44×44px minimum on mobile**, 32×32px on web (WCAG 2.5.8).

| Platform            | Token source           | Consumption method                    |
|---------------------|------------------------|---------------------------------------|
| Vite SPA / Next.js  | CSS custom properties  | Tailwind utility classes              |
| React Native        | Theme context          | `useTheme()` hook + `StyleSheet`      |
| Phlex (Rails)       | CSS custom properties  | Tailwind classes + `class_variants`   |

---

## Decision: how do I get web tokens into React Native?

React Native cannot read `globals.css`. The failure mode is a parallel palette that silently drifts
from web until the two products no longer look related.

### Bad — a second, unrelated palette invented in the mobile app

```ts
// src/theme/colors.ts  (React Native)
export const colors = {
  blue: '#1e293b',        // "close enough" to web's --primary
  lightGray: '#f1f5f9',
  danger: '#dc2626',      // web calls this `error`
};
```

```tsx
<View style={{ backgroundColor: colors.blue, padding: 13 }}>
```

Names do not match web (`blue` vs `primary`, `danger` vs `error`), values were eyeballed, spacing is
off-grid, and there is no dark mode path at all.

### Good — one source of truth, exported to both platforms

```ts
// packages/tokens/src/tokens.ts — shared package consumed by web and mobile
export const palette = {
  light: {
    background: '0 0% 100%',
    foreground: '222 47% 11%',
    primary: '222 47% 11%',
    primaryForeground: '210 40% 98%',
    muted: '210 40% 96%',
    mutedForeground: '215 16% 47%',
    error: '0 84% 60%',
    errorForeground: '0 0% 100%',
    border: '214 32% 91%',
    ring: '222 47% 11%',
  },
  dark: {
    background: '222 47% 11%',
    foreground: '210 40% 98%',
    primary: '210 40% 98%',
    primaryForeground: '222 47% 11%',
    muted: '217 33% 17%',
    mutedForeground: '215 20% 65%',
    error: '0 63% 51%',
    errorForeground: '0 0% 100%',
    border: '217 33% 24%',
    ring: '213 27% 84%',
  },
} as const;

export const spacing = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40, 12: 48, 16: 64 } as const;

export const fontSize = { xs: 12, sm: 14, base: 16, lg: 18, xl: 20, '2xl': 24, '3xl': 30, '4xl': 36 } as const;

export const radius = { none: 0, sm: 2, md: 6, lg: 8, full: 9999 } as const;

export const duration = { instant: 75, fast: 150, normal: 200, slow: 300, slower: 500 } as const;

/** RN needs literal color strings; web needs bare channels for `hsl(var(--x) / <alpha>)`. */
export function hsl(channels: string, alpha = 1): string {
  const [h, s, l] = channels.split(' ');
  return alpha === 1 ? `hsl(${h}, ${s}, ${l})` : `hsla(${h}, ${s}, ${l}, ${alpha})`;
}
```

```ts
// apps/web/tailwind.config.js — web reads the same file
const { spacing, fontSize } = require('@acme/tokens');
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: 'hsl(var(--primary) / <alpha-value>)',
          foreground: 'hsl(var(--primary-foreground) / <alpha-value>)',
        },
      },
    },
  },
};
```

```tsx
// apps/mobile/src/theme/ThemeProvider.tsx — mobile reads the same file
import { createContext, useContext, useMemo, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';
import { palette, spacing, fontSize, radius, duration, hsl } from '@acme/tokens';

type Mode = keyof typeof palette;
export type Theme = {
  colors: Record<keyof typeof palette.light, string>;
  spacing: typeof spacing;
  fontSize: typeof fontSize;
  radius: typeof radius;
  duration: typeof duration;
};

const ThemeContext = createContext<Theme | null>(null);

export function ThemeProvider({ children, mode }: { children: ReactNode; mode?: Mode }) {
  const system = useColorScheme();
  const active: Mode = mode ?? (system === 'dark' ? 'dark' : 'light');

  const theme = useMemo<Theme>(() => {
    const raw = palette[active];
    const colors = Object.fromEntries(
      Object.entries(raw).map(([key, channels]) => [key, hsl(channels)]),
    ) as Theme['colors'];
    return { colors, spacing, fontSize, radius, duration };
  }, [active]);

  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>;
}

export function useTheme(): Theme {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error('useTheme must be used within ThemeProvider');
  return theme;
}
```

---

## Decision: styling a React Native component with tokens

### Bad — literals baked into a module-scope StyleSheet

```tsx
import { StyleSheet, Pressable, Text } from 'react-native';

const styles = StyleSheet.create({
  button: { backgroundColor: '#1e293b', paddingHorizontal: 15, height: 36, borderRadius: 5 },
  label: { color: '#fff', fontSize: 15 },
});

export function Button({ onPress, children }) {
  return (
    <Pressable style={styles.button} onPress={onPress}>
      <Text style={styles.label}>{children}</Text>
    </Pressable>
  );
}
```

A module-scope `StyleSheet.create` is evaluated once at import — it physically cannot react to a
theme change. Plus: literal colors, off-grid padding, a 36px target below the 44px minimum.

### Good — theme-derived styles, 44px target, name parity with web

```tsx
// src/components/ui/Button.tsx
import { useMemo } from 'react';
import { Pressable, StyleSheet, Text, type PressableProps } from 'react-native';
import { useTheme } from '../../theme/ThemeProvider';

type Variant = 'primary' | 'secondary' | 'destructive';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends PressableProps {
  variant?: Variant;
  size?: Size;
  label: string;
}

export function Button({ variant = 'primary', size = 'md', label, ...props }: ButtonProps) {
  const theme = useTheme();

  const styles = useMemo(() => {
    const surface: Record<Variant, string> = {
      primary: theme.colors.primary,
      secondary: theme.colors.muted,
      destructive: theme.colors.error,
    };
    const text: Record<Variant, string> = {
      primary: theme.colors.primaryForeground,
      secondary: theme.colors.foreground,
      destructive: theme.colors.errorForeground,
    };
    const height: Record<Size, number> = { sm: 44, md: 48, lg: 52 }; // never below 44
    const padding: Record<Size, number> = { sm: theme.spacing[3], md: theme.spacing[4], lg: theme.spacing[6] };

    return StyleSheet.create({
      button: {
        backgroundColor: surface[variant],
        paddingHorizontal: padding[size],
        minHeight: height[size],
        borderRadius: theme.radius.md,
        alignItems: 'center',
        justifyContent: 'center',
      },
      pressed: { opacity: 0.9 },
      label: { color: text[variant], fontSize: theme.fontSize.base, fontWeight: '500' },
    });
  }, [theme, variant, size]);

  return (
    <Pressable
      accessibilityRole="button"
      hitSlop={8}
      style={({ pressed }) => [styles.button, pressed && styles.pressed]}
      {...props}
    >
      <Text style={styles.label}>{label}</Text>
    </Pressable>
  );
}
```

Note the deliberate divergence: mobile's `sm` is 44px tall while web's `sm` is 32px (`h-8`). Token
*names* stay identical across platforms; token *values* may differ where the platform's ergonomics
differ. Fingers are not cursors. Do not "fix" this by making mobile match web.

---

## Decision: touch targets

### Bad — a 24px icon button

```tsx
<Pressable onPress={onClose} style={{ width: 24, height: 24 }}>
  <Icon name="close" size={24} />
</Pressable>
```

### Good — visual size stays 24px, the target reaches 44px

```tsx
<Pressable
  onPress={onClose}
  accessibilityRole="button"
  accessibilityLabel="Close"
  hitSlop={10}                                    // 24 + 10 + 10 = 44
  style={{ width: 24, height: 24, alignItems: 'center', justifyContent: 'center' }}
>
  <Icon name="close" size={24} />
</Pressable>
```

Web equivalent — pad the target rather than growing the glyph:

```tsx
<button
  aria-label="Close"
  className="grid h-8 w-8 place-items-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
>
  <X className="h-4 w-4" aria-hidden="true" />
</button>
```

---

## Decision: verifying parity does not rot

Names drift silently. Assert them.

```ts
// packages/tokens/src/parity.test.ts — Vitest, runs in CI
import { describe, it, expect } from 'vitest';
import { palette } from './tokens';

describe('token parity', () => {
  it('should expose identical token names in light and dark modes', () => {
    expect(Object.keys(palette.dark).sort()).toEqual(Object.keys(palette.light).sort());
  });

  it('should pair every foreground token with a matching surface token', () => {
    const names = Object.keys(palette.light);
    const foregrounds = names.filter((n) => n.endsWith('Foreground'));
    for (const fg of foregrounds) {
      expect(names).toContain(fg.replace('Foreground', ''));
    }
  });
});
```
