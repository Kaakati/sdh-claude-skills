# Defining Design Tokens

Read this when you are **creating or changing the token layer itself** — adding a color, wiring
Tailwind, building dark mode, or validating contrast. If you are only *consuming* existing tokens
in a component, you do not need this file.

Load-bearing rules restated (they must hold even if nothing else here is read):

1. Colors are declared as **space-separated HSL channels with no `hsl()` wrapper**, so Tailwind's
   opacity modifier (`bg-primary/50`) works.
2. **Every background color token ships with a `-foreground` counterpart** that is contrast-verified
   against it. A token without a foreground pair is an incomplete token.
3. Dark mode overrides use the **`.dark` class selector**, never `@media (prefers-color-scheme)`.
4. Normal text ≥ **4.5:1**; large text (18px+, or 14px+ bold) and UI component boundaries ≥ **3:1**.

---

## Decision: I need to add a new color token

The mistake is adding a raw value in one place and letting components reach for it directly.

### Bad — wrapped color, no foreground pair, no dark override

```css
/* app/assets/stylesheets/globals.css */
:root {
  --brand-purple: hsl(270, 60%, 45%);   /* wrapped → bg-brand-purple/50 silently breaks */
  --warning: #f59e0b;                   /* hex → opacity modifier impossible */
}
/* no .dark block: the purple stays at 45% lightness on a near-black surface */
```

```tsx
// Consumer is forced to hardcode the readable text color by eye:
<div className="bg-[hsl(var(--brand-purple))] text-white">Upgrade</div>
```

### Good — channels only, paired foreground, dark override, Tailwind-registered

```css
/* app/assets/stylesheets/globals.css */
:root {
  --brand: 270 60% 45%;
  --brand-foreground: 0 0% 100%;   /* 7.1:1 against --brand — verified */
  --warning: 38 92% 50%;
  --warning-foreground: 26 83% 14%; /* 8.4:1 — dark text on amber, not white */
}

.dark {
  --brand: 270 65% 68%;            /* lifted lightness for dark surfaces */
  --brand-foreground: 270 40% 12%;
  --warning: 38 88% 62%;
  --warning-foreground: 26 83% 10%;
}
```

```js
// tailwind.config.js — register once, and the token becomes a first-class utility
module.exports = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: 'hsl(var(--brand) / <alpha-value>)',
          foreground: 'hsl(var(--brand-foreground) / <alpha-value>)',
        },
        warning: {
          DEFAULT: 'hsl(var(--warning) / <alpha-value>)',
          foreground: 'hsl(var(--warning-foreground) / <alpha-value>)',
        },
      },
    },
  },
};
```

```tsx
// Consumer never names a color value, and dark mode is free:
<div className="bg-brand text-brand-foreground">Upgrade</div>
<div className="bg-brand/10 text-brand">Subtle variant</div>
```

`<alpha-value>` is the placeholder Tailwind substitutes when you write `bg-brand/10`. Omit it and
every opacity modifier in the codebase becomes a no-op.

---

## Decision: is my palette complete?

A palette is complete when all five groups exist. Missing groups get filled ad hoc with arbitrary
values later — that is how token drift starts.

| Palette  | Required tokens                                    | Purpose                             |
|----------|----------------------------------------------------|-------------------------------------|
| Core     | `primary`, `secondary`, `accent`                   | Brand identity and UI actions       |
| Neutral  | `neutral`, `muted`, `background`, `foreground`     | Text, backgrounds, disabled states  |
| Semantic | `success`, `warning`, `error`, `info`              | Status communication                |
| Surface  | `card`, `popover`                                  | Container backgrounds               |
| Border   | `border`, `input`, `ring`                          | Boundaries and focus indicators     |

Each of Core, Semantic, and Surface also requires its `-foreground` pair. `border` / `input` / `ring`
do not — nothing sits on top of them.

---

## Decision: dark mode — class or media query?

### Bad — media query

```css
@media (prefers-color-scheme: dark) {
  :root { --background: 222 47% 11%; }
}
```

This cannot be overridden. A user who wants light mode inside a dark OS has no path, and you cannot
render a dark-themed marketing section inside a light app.

### Good — class selector, with the OS as the initial default only

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --card: 0 0% 100%;
  --card-foreground: 222 47% 11%;
  --border: 214 32% 91%;
  --ring: 222 47% 11%;
}

.dark {
  --background: 222 47% 11%;
  --foreground: 210 40% 98%;
  --card: 222 47% 14%;      /* card lifts off background, not the reverse */
  --card-foreground: 210 40% 98%;
  --border: 217 33% 24%;
  --ring: 213 27% 84%;
}
```

```tsx
// app/providers/theme-provider.tsx — OS preference seeds the default; the user can override.
'use client';
import { useEffect } from 'react';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({ theme: 'system', setTheme: (theme) => set({ theme }) }),
    { name: 'theme' },
  ),
);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && media.matches);
      document.documentElement.classList.toggle('dark', dark);
    };
    apply();
    media.addEventListener('change', apply);
    return () => media.removeEventListener('change', apply);
  }, [theme]);

  return <>{children}</>;
}
```

One inversion rule worth stating explicitly: in dark mode, **surfaces get lighter as they get
closer to the user** (`--card` lighter than `--background`). Do not mirror the light-mode ramp,
where cards are white on a grey page.

---

## Decision: does this pair actually meet contrast?

Do not eyeball it. Compute it. Both channels are already in HSL, so the check is mechanical.

```ts
// scripts/check-contrast.ts — run in CI alongside lint
type Hsl = [number, number, number];

function hslToRgb([h, s, l]: Hsl): [number, number, number] {
  const sn = s / 100;
  const ln = l / 100;
  const c = (1 - Math.abs(2 * ln - 1)) * sn;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = ln - c / 2;
  const [r, g, b] =
    h < 60 ? [c, x, 0] :
    h < 120 ? [x, c, 0] :
    h < 180 ? [0, c, x] :
    h < 240 ? [0, x, c] :
    h < 300 ? [x, 0, c] : [c, 0, x];
  return [(r + m) * 255, (g + m) * 255, (b + m) * 255];
}

function relativeLuminance(hsl: Hsl): number {
  const [r, g, b] = hslToRgb(hsl).map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contrastRatio(a: Hsl, b: Hsl): number {
  const [hi, lo] = [relativeLuminance(a), relativeLuminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
```

```ts
// scripts/check-contrast.test.ts — Vitest; fails the build on a bad pair
import { describe, it, expect } from 'vitest';
import { contrastRatio } from './check-contrast';

const light = {
  brand: [270, 60, 45] as const,
  brandForeground: [0, 0, 100] as const,
  background: [0, 0, 100] as const,
  foreground: [222, 47, 11] as const,
};

describe('token contrast', () => {
  it('should meet 4.5:1 for body text when foreground sits on background', () => {
    expect(contrastRatio([...light.foreground], [...light.background])).toBeGreaterThanOrEqual(4.5);
  });

  it('should meet 4.5:1 for label text when brand-foreground sits on brand', () => {
    expect(contrastRatio([...light.brandForeground], [...light.brand])).toBeGreaterThanOrEqual(4.5);
  });
});
```

A frequent near-miss: a mid-tone amber or lime `success`/`warning` with white foreground lands
around 2.1:1. The fix is always to darken the *foreground*, not to brighten the surface — the
surface color is the brand decision.

---

## Decision: color is carrying meaning — is that enough?

Never. Color alone fails for ~8% of men and for anyone on a monochrome or sun-washed screen.

### Bad

```tsx
<span className={status === 'failed' ? 'text-error' : 'text-success'}>
  {status}
</span>
```

### Good — color plus icon plus text

```tsx
import { CheckCircle, XCircle } from 'lucide-react';

const config = {
  succeeded: { Icon: CheckCircle, className: 'text-success', label: 'Succeeded' },
  failed: { Icon: XCircle, className: 'text-error', label: 'Failed' },
} as const;

export function StatusBadge({ status }: { status: keyof typeof config }) {
  const { Icon, className, label } = config[status];
  return (
    <span className={`inline-flex items-center gap-1.5 ${className}`}>
      <Icon className="h-4 w-4" aria-hidden="true" />
      {label}
    </span>
  );
}
```
