# Accessibility and i18n — What the Primitives Guarantee, and What They Don't

Load-bearing rules restated (hold even if you read nothing else):

1. **The base library owns focus management, keyboard support and ARIA state.** The copied styles
   and strings are ours to fix — never re-implement the behaviour.
2. **Focus rings at full opacity, at least 2px, at least 3:1.** Drop the `/50` unless the house pair
   measures ≥ 3:1.
3. **Recompute contrast on house values for every pair a primitive renders** — `muted-foreground` on
   `muted`, input borders, the destructive tint, the chart colors.
4. **Pointer targets at least 32×32 CSS px on web** — the house minimum (`std-design-system`);
   WCAG 2.5.8's floor is 24×24. Stock sidebar actions are 20px wide.
5. **No English in a primitive:** required label props, filled from `t()` at the call site.
6. **RTL is decided before the first `add`:** `rtl: true`, `DirectionProvider`, `dir` on portal
   content, three components migrated by hand.
7. **The global reduced-motion backstop is mandatory.** It cannot reach JavaScript animation:
   a Recharts series takes `isAnimationActive={!reduceMotion}`, and Framer Motion transitions check
   the same `useReducedMotion()`.
8. **Every chart has a text alternative.** `accessibilityLayer` is not one.
9. **The breadcrumb's current page is plain text with `aria-current="page"`**, and its trail's
   `aria-label` comes from `t()` — both registries ship otherwise.

---

## What the primitives guarantee

- **Dialog, alert dialog, sheet, drawer:** focus is trapped while open and returned on close;
  Escape closes; title and description are wired to the panel.
- **Menus, tabs, radio and toggle groups, select, command:** the keyboard model, roving focus, and
  `aria-expanded` / `aria-selected` / `aria-checked` state. `command` is cmdk in both registries:
  combobox, listbox and option roles with `aria-activedescendant`, and its input is named by the
  `label` prop on `Command` (cmdk — README, https://github.com/dip/cmdk).
- **Field:** `Field` renders `role="group"`, `FieldError` `role="alert"`, and `FieldSet` with
  `FieldLegend` groups related controls for assistive tech.
- **Chart:** `accessibilityLayer` adds keyboard access and screen reader support for data points.
- **Sidebar:** Cmd/Ctrl+B toggles it; the trigger has a screen-reader label; on mobile it renders a
  titled `Sheet`.
- **Toasts:** Base UI's viewport is a landmark reachable with F6, and `priority` maps to polite or
  urgent; `sonner` announces through one polite region, reachable with Alt+T.
- **Data table guide:** the selection checkboxes carry `aria-label`.

Do not add a second focus trap, extra `role`s, or `tabIndex` juggling on top of a primitive — two
focus managers fight, and the keyboard user loses.

---

## Measured gaps, and the house fix

The figures are shadcn's **neutral defaults**, computed from its theming docs. House token values
differ — the figures are the reason to recompute, not results to copy. The contrast table the
`theming` skill verifies is @skills/theming/references/design-tokens.md.

| Gap | Measured on shadcn defaults | House fix |
|---|---|---|
| Focus ring `ring-ring/50` | ≈ 1.54:1 light, ≈ 1.87:1 dark (`ring` at full opacity: 2.59:1 light) | Full-opacity `ring-ring` at the width the style ships (never under 2px); keep `/50` only if the house pair measures ≥ 3:1. The destructive variant's `ring-destructive/20` (`/40` dark) likewise |
| `muted-foreground` on `muted` | 4.34:1 light — below 4.5 | Recompute on house values; small text sits on a `muted` surface only if the pair passes 4.5:1 |
| `border` / `input` on `background` | 1.26:1 | Adopted: the house `--input` and `--border` measure ≥ 3:1 (1.4.11 Non-text Contrast) on `background` and `card` in every preset (@skills/theming/references/design-tokens.md). A field on `muted`, `secondary` or `accent` still measures below 3:1 (2.92:1 and 2.40:1 in that table) — give it its own `bg-background` fill and a visible label |
| Destructive tint (base-nova: `text-destructive` on `bg-destructive/10`) | Not measured upstream | Measure the text on the tint over `background` and over `card`, in both modes |
| `dark:` opacity on a solid (new-york-v4 `dark:bg-destructive/60`) | Changes the surface its foreground was verified against | Recompute the pair in dark mode; drop the override if it fails |
| `chart-1` … `chart-5` | — | ≥ 3:1 against the chart surface, plus a non-color cue per series |
| Sidebar group and menu actions | `w-5` (20px); the `after:-inset-2` hit area is hidden from `md:` up | 32×32 on web — the house minimum (`std-design-system`), above WCAG 2.5.8's 24×24 floor: drop the `md:after:hidden`, so the stock `after:-inset-2` keeps a 36×36 hit area at every width. Never size the action down to 24px |
| Motion | No `motion-safe:` or `motion-reduce:` in any primitive; no reduced-motion rule in `tw-animate-css` 1.4.0; `shadcn/tailwind.css` stops only `.shimmer` | The backstop, below |
| Accessible names | Hardcoded English | Label props, below |
| Record-state blocks | A `disabled` control leaves the tab order, so its reason is never reached | Stays focusable (`std-accessibility`): Base UI `disabled` + `focusableWhenDisabled`, which renders `aria-disabled="true"` instead of the `disabled` attribute (read from Base UI's `useFocusableWhenDisabled` source — the Button docs page lists only `data-disabled`); Radix `aria-disabled` + a no-op handler. Neither renders `disabled`, so the stock `disabled:` classes stop dimming it — add `aria-disabled:` at the call site |
| Block demo markup | `href="#"`, placeholder emails, login inputs without `autoComplete` | Real routes; translated placeholders; `autoComplete="email"` and `"current-password"`, paste never blocked (3.3.8 Accessible Authentication) |
| Breadcrumb current page | `BreadcrumbPage` renders `<span role="link" aria-disabled="true" aria-current="page">` in both registries (read from the installed source) — announced as a dimmed link, not as the page you are on | Drop `role` and `aria-disabled`: plain text with `aria-current="page"`, the house breadcrumb rule (@skills/ui-ux-patterns/references/drill-down-navigation.md). The trail's own `aria-label` → the label table below |

The ring fix is a one-token edit, not a restyle:

```tsx
// components/ui/button.tsx, cva base (base-nova shown; new-york-v4 ships a 3px ring width)
// stock: focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50
"focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring"
```

A stock `outline-none` on a dialog or popover **panel** is not a gap: the panel is a container, not
a control, and the controls inside it carry rings. Do not add a ring to the panel.

### WCAG 2.2 criteria that shadcn layouts trip

- **2.4.11 Focus Not Obscured:** `dashboard-01`'s sticky `site-header` covers focused rows while
  tabbing up — give scroll targets a `scroll-mt-*` equal to the header height.
- **2.5.7 Dragging Movements:** the `dashboard-01` table's drag-to-reorder needs Move up / Move down.
- **2.5.8 Target Size:** the sidebar actions above, and any `xs` / `icon-xs` button — measure it
  against the house 32×32 on web, which sits above 2.5.8's 24×24.
- **Tooltips** never hold the only copy of anything essential: touch has no hover, and a disabled
  reason is visible beside its control, never tooltip-only
  (@skills/ui-ux-patterns/references/role-based-ux.md).

---

## Label props for hardcoded strings

| Primitive | Ships (installed source) | House prop | Filled with |
|---|---|---|---|
| `dialog`, `sheet` | `Close` — screen-reader text on the close button | `closeLabel` on `DialogContent`, `SheetContent` | `t('common.close')` |
| `sidebar` | `Toggle Sidebar` on the trigger and the rail; `Sidebar` and `Displays the mobile sidebar.` as the mobile sheet's title and description | `toggleLabel` on `SidebarTrigger`, `SidebarRail`; `mobileTitle`, `mobileDescription` on `Sidebar` | `t('nav.toggle')`, `t('nav.title')`, `t('nav.description')` |
| `pagination` | `Go to previous page`, `Go to next page`, `Previous`, `Next`, `More pages` | `label` (accessible name) and `text` (visible) on `PaginationPrevious`, `PaginationNext`; `label` on `PaginationEllipsis` | `t('pagination.previous')`, … |
| `breadcrumb` | `More`; `aria-label="breadcrumb"` on the `Breadcrumb` nav (both registries) | `label` on `BreadcrumbEllipsis`; `aria-label` on `Breadcrumb`, made required (the caller's value wins today only because props spread after the default) | `t('breadcrumb.more')`, `t('breadcrumb.label')` |
| `command` | `CommandDialog`'s visually hidden `Command Palette` title and `Search for a command to run...` description (both registries); it renders `DialogContent` | `title` and `description` on `CommandDialog`, made required; `closeLabel` threaded through to `DialogContent`; cmdk's `label` on `Command` names the input | `t('palette.title')`, `t('palette.description')`, `t('common.close')`, `t('palette.label')` |
| `carousel` | `Previous slide`, `Next slide` | `label` on `CarouselPrevious`, `CarouselNext` | `t('carousel.previous')`, … |
| `spinner` | `Loading` | `label` | `t('common.loading')` |
| `toast` (Base UI) | `Close toast` on each toast's close button | `closeLabel` on `Toaster` | `t('notifications.close')` |
| `sonner` (Radix) | The library's `Notifications` region name | Pass `containerAriaLabel` and `toastOptions.closeButtonAriaLabel` through the vendored `Toaster` | `t('notifications.region')`, `t('notifications.close')` |
| Data table (guide code) | `Select all`, `Select row` | At the call site | `t('table.selectAll')`, `t('table.selectRow')` |

**Make every label prop required.** The compiler then lists each call site that still needs a
translation — including vendored primitives that render another one (`command` renders
`DialogContent`), which thread the prop through. An English default hides exactly the call sites you
are looking for.

```tsx
// components/ui/dialog.tsx — the local edit: the close button's name comes from the caller.
// `ContentProps` stands for the props type the installed file already declares.
function DialogContent({ closeLabel, showCloseButton = true, className, children, ...props }: ContentProps & { closeLabel: string }) {
  // …stock JSX unchanged, except inside the close button:
  //   <span className="sr-only">Close</span>  →  <span className="sr-only">{closeLabel}</span>
}

// call site
<DialogContent closeLabel={t('common.close')}>…</DialogContent>
```

Block copy never ships literally: `login-01`'s title, links, button text and placeholders move to
message files under the feature's namespace (`auth.login.*`). Key naming, pluralization and
interpolation are the `std-i18n` skill's.

---

## RTL

Decide before the first `add` for any client that ships an RTL locale.

1. **`"rtl": true` in `components.json`** (or `init --rtl`). Installs then rewrite `ml-*` → `ms-*`,
   `text-left` → `text-start`, `slide-in-from-left` → `slide-in-from-start`, and add
   `rtl:rotate-180` to supported directional icons. Only the new styles (`base-nova`, `radix-nova`,
   …) get this; `new-york` and `default` do not. Files already installed:
   `npx shadcn migrate rtl [path]`.
2. **`npx shadcn add direction`** and provide the direction at the root — `DirectionProvider` with
   `direction` (Base UI's prop; the Radix wrapper accepts it too).
3. **Migrate `Calendar`, `Pagination` and `Sidebar` by hand** — the CLI does not. `Sidebar` takes a
   `dir` prop, and the trigger's icon gets `rtl:rotate-180`.
4. **Pass `dir` to portal content** — `PopoverContent`, `TooltipContent`, menu content — because of
   a known `tw-animate-css` issue with its logical slide utilities.

```tsx
// src/components/providers/Providers.tsx — Next.js. The root layout renders
// <html lang={locale} dir={dir} suppressHydrationWarning> and passes strings translated on the server.
'use client';

import type { ReactNode } from 'react';
import { ThemeProvider } from 'next-themes';
import { DirectionProvider } from '@/components/ui/direction';
import { Toaster } from '@/components/ui/toast'; // Radix packages: '@/components/ui/sonner'

interface ProvidersProps { dir: 'ltr' | 'rtl'; toastCloseLabel: string; children: ReactNode }

export function Providers({ dir, toastCloseLabel, children }: ProvidersProps) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <DirectionProvider direction={dir}>
        {children}
        <Toaster closeLabel={toastCloseLabel} />
      </DirectionProvider>
    </ThemeProvider>
  );
}
```

```tsx
// src/App.tsx — Vite SPA; <html dir> follows the language
i18n.on('languageChanged', (lng) => {
  document.documentElement.lang = lng;
  document.documentElement.dir = i18n.dir(lng);
});

export function App() {
  const { t, i18n } = useTranslation(); // re-renders on language change
  return (
    <ThemeProvider /* the house theming provider — the theming skill */>
      <DirectionProvider direction={i18n.dir()}>
        <RouterProvider router={router} />
        <Toaster closeLabel={t('notifications.close')} />
      </DirectionProvider>
    </ThemeProvider>
  );
}
```

Logical properties, the `rtl:` variant, and locale detection → the `std-i18n` skill and
@skills/i18n/references/web-i18n.md.

---

## Reduced motion

- **`tw-animate-css` drives the primitives' enter and exit animations** (`animate-in`, `fade-in-0`,
  `zoom-in-95`). It ships no reduced-motion rule, and no primitive uses `motion-safe:`.
- **The global backstop is mandatory** — the `@media (prefers-reduced-motion: reduce)` block from
  @skills/std-design-system/references/motion.md, verbatim, in the file `components.json` names as
  `tailwind.css`. For vendored primitives at `aliases.ui` it **is** the reduced-motion path: do not
  prefix every copied class with `motion-safe:`, which would bloat every future `add --diff`.
  Components the house writes still use `motion-safe:` (`std-design-system` rule 4).
- **The backstop cannot reach JavaScript.** Recharts animates in JS, so every series takes
  `isAnimationActive={!reduceMotion}` from Framer Motion's `useReducedMotion()` — the switch house
  page and list transitions use (@skills/std-design-system/references/motion.md). Never a bare prop,
  never `true`. Recharts 3's own `"auto"` default already follows the preference; the explicit prop
  keeps charts on the house switch and visible in review.

```css
/* the tailwind.css file — keep what init wrote, then add the backstop last */
@import "tailwindcss";
@import "shadcn/tailwind.css"; /* manual installs also import "tw-animate-css" */
@custom-variant dark (&:is(.dark *));
/* @theme inline { … } and the :root / .dark token blocks → the theming skill */
/* @media (prefers-reduced-motion: reduce) { … } → the block in std-design-system's motion.md */
```

---

## Chart text alternatives

`accessibilityLayer` makes the data points reachable by keyboard and screen reader; it does not say
what the chart means. Every chart also ships:

- **A `<figure>` whose `<figcaption>` names the metric and the period.**
- **A one-sentence summary of the takeaway**, visible.
- **The data as a table** — `sr-only`, or behind a visible "Show data" toggle.
- **Series distinguishable without color:** legend text plus `strokeDasharray` or distinct markers.
- **No value that exists only in the tooltip.**

```tsx
<figure>
  <figcaption>{t('dashboard.revenue.title', { period })}</figcaption>
  <p className="text-sm text-muted-foreground">{summary}</p>
  <ChartContainer config={chartConfig} className="min-h-64 w-full">
    <AreaChart accessibilityLayer data={points}>{/* series, axes, ChartTooltip */}</AreaChart>
  </ChartContainer>
  <RevenueTable points={points} className="sr-only" />
</figure>
```

The Next.js chart itself — `ChartConfig`, colors, the server-rendered figure, reduced motion, lazy
chart modules → @skills/std-shadcn-ui/references/charts.md. The Vite SPA's charts are Chart.js, with
their own text alternative → @skills/std-reactjs/references/charts.md.

---

## Testing

**No hook checks the house edits on a vendored primitive.** The i18n hook (`i18n-checker.py`) skips
every file under `aliases.ui`, and the accessibility hook (`accessibility-checker.py`) keeps only
its clickable-`div` and hidden-interactive checks there. Translated label props, ring opacity and
contrast, and target size on vendored primitives therefore rely on review and on the tests below.

- **axe in Vitest** on every composition that renders a primitive, plus a keyboard pass: Tab order,
  Escape, focus return, and focus after a destructive action →
  @skills/std-testing/references/react-components.md.
- **Assert the house edits so an upstream merge cannot undo them:** the close button's accessible
  name comes from the label prop, the ring class has no `/50`, and a blocked control is focusable
  and described by its reason.
- **Run the RTL locale once per screen** that renders a sidebar, pagination, calendar or popover.
