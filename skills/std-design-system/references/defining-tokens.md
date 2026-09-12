# Defining Design Tokens

Read this when you are **creating or changing the token layer itself** — adding a color, wiring
Tailwind, building dark mode, or validating contrast. If you are only *consuming* existing tokens
in a component, you do not need this file.

Load-bearing rules restated (they must hold even if nothing else here is read):

1. Colors are declared as **complete `hsl()` values** (`--brand: hsl(270 60% 45%)`) and registered
   with Tailwind v4 through **`@theme inline { --color-brand: var(--brand) }`**. Tailwind applies
   opacity modifiers (`bg-brand/50`) to a complete color with `color-mix()`. Arbitrary CSS reads
   `var(--brand)`, never `hsl(var(--brand))`.
2. **Every background color token ships with a `-foreground` counterpart** that is contrast-verified
   against it. A token without a foreground pair is an incomplete token.
3. Dark mode overrides use the **`.dark` class selector**, never `@media (prefers-color-scheme)`, and
   the stylesheet declares `@custom-variant dark (&:is(.dark *));` so `dark:` utilities follow the
   class.
4. Normal text ≥ **4.5:1**; large text (18px+, or 14px+ bold) and UI component boundaries ≥ **3:1**.
5. A shadcn/ui name for a house role is an **alias**: `var(--role)` declared on `:root, .dark`,
   never a copied value.

---

## Decision: I need to add a new color token

The mistake is adding a raw value in one place and letting components reach for it directly.

### Bad — bare channels, hex, no `inline`, no foreground pair, no dark override

```css
/* globals.css */
:root {
  --brand: 270 60% 45%;          /* bare channels: var(--brand) is not a color, utilities fall to unset */
  --warning: #f59e0b;            /* hex: escapes the HSL contrast measurement this repo gates on */
}
/* no .dark block: the purple stays at 45% lightness on a near-black surface */

@theme {
  --color-brand: var(--brand);   /* no `inline`: resolved once on :root, so a nested .dark section never flips */
}
```

```tsx
// The consumer patches the broken token locally and picks the text color by eye. The day someone
// fixes the token to a complete color, this becomes hsl(hsl(...)) and renders nothing.
<div className="bg-[hsl(var(--brand))] text-white">Upgrade</div>
```

### Good — complete values, paired foreground, dark override, registered `inline`

```css
/* globals.css */
:root {
  --brand: hsl(270 60% 45%);
  --brand-foreground: hsl(0 0% 100%);    /* 7.47:1 against --brand, measured */
  --warning: hsl(38 92% 50%);
  --warning-foreground: hsl(26 83% 14%); /* 6.87:1: dark text on amber, not white */
}

.dark {
  --brand: hsl(270 65% 68%);             /* lifted lightness for dark surfaces */
  --brand-foreground: hsl(270 40% 12%);  /* 5.56:1 */
  --warning: hsl(38 88% 62%);
  --warning-foreground: hsl(26 83% 10%); /* 9.25:1 */
}

@theme inline {
  --color-brand: var(--brand);
  --color-brand-foreground: var(--brand-foreground);
  --color-warning: var(--warning);
  --color-warning-foreground: var(--warning-foreground);
}
```

```tsx
// Consumer never names a color value, and dark mode is free:
<div className="bg-brand text-brand-foreground">Upgrade</div>
<div className="bg-brand/10 text-brand">Subtle variant</div>
```

`inline` makes `bg-brand` emit `var(--brand)` itself, not a `--color-brand` that was resolved
once on `:root`. The utility then resolves on the element it styles, so a nested `.dark` section
flips and a per-component override lands. Tailwind's docs require `inline` whenever a theme
variable references another variable.

A Tailwind v3 package cannot apply an opacity modifier to a complete color; that is what
`hsl(var(--x) / <alpha-value>)` channel wiring was for. It keeps that wiring until it migrates
(`npx @tailwindcss/upgrade`), and it never mixes the two forms in one stylesheet. shadcn/ui and the
`cn` package are v4-only, so a v3 package adopts neither.

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
| Chart    | `chart-1` … `chart-5`                              | Categorical data series, fixed order |

Each of Core, Semantic, and Surface also requires its `-foreground` pair. `border` / `input` / `ring`
do not — nothing sits on top of them. Each is measured against the surfaces it sits on instead:
≥3:1 against `background` and `card` in both modes (WCAG 1.4.11). A border lighter than that is a
field with no visible edge. `chart-1`…`chart-5` take no pair either. A series is a non-text mark,
measured against the surface it sits on (≥3:1, WCAG 1.4.11), and its labels and legend text wear
`foreground`, never the series color.

---

## Decision: shadcn/ui source names a token the house calls something else

shadcn/ui primitives and blocks use `destructive`, `sidebar-*` and `chart-*`. The house roles are
`error`, `card`, `primary`, `accent`, `border` and `ring`. Minting a second value under the shadcn
name gives one role two numbers. Renaming the classes after every `add` makes every upstream diff
unmergeable. So the registry declares the shadcn names as **aliases**.

### Bad — a copied value, or a reference declared on `:root` only

```css
:root {
  --error: hsl(0 84.2% 47%);
  --destructive: hsl(0 84.2% 47%);   /* one role, two numbers: edit --error and this one stays */
  --sidebar: var(--card);            /* resolved once on :root: a nested .dark section keeps the light card */
}
```

A custom property that holds `var()` is substituted on the element that declares it, and
descendants inherit the *result*. Declared only on `:root`, the alias is frozen at the light value
for every nested `.dark` scope.

### Good — a `var()` reference, declared on both scopes, registered `inline`

```css
:root,
.dark {
  --destructive: var(--error);
  --destructive-foreground: var(--error-foreground);
  --sidebar: var(--card);
  --sidebar-foreground: var(--card-foreground);
}

@theme inline {
  --color-destructive: var(--destructive);
  --color-destructive-foreground: var(--destructive-foreground);
  --color-sidebar: var(--sidebar);
  --color-sidebar-foreground: var(--sidebar-foreground);
}
```

The full alias map, the pairs measured through it, and the `chart-1`…`chart-5` values are in
`@skills/theming/references/design-tokens.md`. Aliasing does **not** fix raw palette classes in
shadcn source (`text-white`, `bg-black/50`) or `dark:` opacity overrides on solids. Those are
edits, and they are owned by the `std-shadcn-ui` skill
(`@skills/std-shadcn-ui/references/components-and-blocks.md`).

---

## Decision: dark mode — class or media query?

### Bad — media query

```css
@media (prefers-color-scheme: dark) {
  :root { --background: hsl(222 47% 11%); }
}
```

This cannot be overridden. A user who wants light mode inside a dark OS has no path, and you cannot
render a dark-themed marketing section inside a light app.

### Good — class selector, with the OS as the initial default only

```css
/* Tailwind v4's dark: follows the media query unless this line says otherwise */
@custom-variant dark (&:is(.dark *));

:root {
  --background: hsl(0 0% 100%);
  --foreground: hsl(222 47% 11%);
  --card: hsl(0 0% 100%);
  --card-foreground: hsl(222 47% 11%);
  --border: hsl(214 32% 59%);    /* 3.20:1 against --background and --card, measured */
  --ring: hsl(222 47% 11%);
}

.dark {
  --background: hsl(222 47% 11%);
  --foreground: hsl(210 40% 98%);
  --card: hsl(222 47% 14%);      /* card lifts off background, not the reverse */
  --card-foreground: hsl(210 40% 98%);
  --border: hsl(217 33% 47%);    /* 3.28:1 against --card, 3.50:1 against --background */
  --ring: hsl(213 27% 84%);
}
```

The provider below is the house provider for the **Vite SPA**. Next.js uses `next-themes` for the
same `.dark` class, because it has to be SSR-safe. Both setups, plus the pre-paint script that
stops a flash of the wrong theme, are in `@skills/theming/references/platform-integration.md`.

```tsx
// src/providers/theme-provider.tsx (Vite SPA) — OS preference seeds the default; the user can override.
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

Do not eyeball it. Compute it. Every value is `hsl(H S% L%)`, so the check is mechanical: take the
three numbers.

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
around 2.1:1. **Never brighten the surface** — with a near-white foreground that makes it worse.
Which of the two remaining fixes you reach for depends on what the token *is*:

| Token | Fix | Why |
|---|---|---|
| **Brand** — `primary`, `brand` | Darken the **foreground** | The surface is the brand decision. You do not get to restyle the logo colour to pass a checker. |
| **Semantic status** — `success`, `error`, `warning`, `info` | Darken the **surface**, same hue | "Green means success" is the convention; *which* green is not. Every design system ships a darker step for exactly this (Tailwind's `green-600` → `green-700`), and it keeps the near-white foreground a `-foreground` token is meant to be. |

This is not theoretical. The defaults in `@skills/theming/references/design-tokens.md` and all three
presets in `@skills/theming/references/theme-presets.md` were repaired by darkening the **surface**
on `success`/`error`/`info` — semantic tokens, every one — and `primary` was never touched in any
of them. A blanket "always darken the foreground" would have told you to do the opposite of what
this repo's own shipped tokens do.

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
