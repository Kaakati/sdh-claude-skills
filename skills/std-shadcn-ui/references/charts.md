# Charts in Next.js — shadcn/ui `chart` (Recharts)

The house charting standard for **Next.js packages**, written against shadcn/ui's `chart` component.
It composes Recharts v3 directly — the registry item pins `recharts@3.8.0`, and shadcn's docs say
"We do not wrap Recharts" — so the Recharts API is the API (shadcn/ui — Chart).

**Not the other stacks.** The Vite SPA charts with Chart.js through react-chartjs-2 →
@skills/std-reactjs/references/charts.md. Rails Phlex views chart with a house Stimulus controller on
Chart.js → @skills/std-phlex-conventions/references/charts.md. A chart module never moves between
those packages and this one. Where a panel, its figure and its chart leaf sit on the atomic ladder →
@skills/std-shadcn-ui/references/components-and-blocks.md.

Load-bearing rules restated (hold even if you read nothing else):

1. **shadcn/ui's `chart` component is the only charting entry point.** `ChartContainer`,
   `ChartTooltip`, `ChartTooltipContent`, `ChartLegend`, `ChartLegendContent` and
   `type ChartConfig` come from `@/components/ui/chart`, and Recharts elements go inside
   `ChartContainer`. No other chart library in a Next.js package, and no Recharts outside the
   container.
2. **`ChartConfig` colours are `var(--chart-N)`** — never `hsl(var(--chart-N))`, never a literal.
   Series read them back as `var(--color-<key>)`.
3. **The server fetches and says what the chart means; the client only draws.** A Server Component
   fetches, renders the loading, empty and error paths, and renders the figure's caption, summary
   and data table. The `'use client'` chart leaf receives plain points and never fetches.
4. **Only plain data crosses the boundary** — points and a currency code, never a formatter
   function or a class instance. Formatting the plot needs happens inside the leaf.
5. **Every chart has a text alternative** — a summary sentence, plus the data as a table whenever a
   value would otherwise live only in the tooltip. `accessibilityLayer` stays on, and it is not the
   alternative.
6. **Reduced motion turns series animation off**: `isAnimationActive={!reduceMotion}`, from Framer
   Motion's `useReducedMotion()` — the switch @skills/std-design-system/references/motion.md names.
7. **`ChartContainer` always carries a size** (`aspect-*`, `h-*` or `min-h-*`), tooltips are
   `ChartTooltipContent`, and the chart module is imported by its file path, never through a barrel.

---

## Decision: rendering a chart

### Bad — a client page that fetches, with literal colours and no size

```tsx
// app/(app)/(reports)/reports/revenue/page.tsx — BAD
'use client';

import { useEffect, useState } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip } from 'recharts';

export default function RevenuePage() {
  const [days, setDays] = useState<RevenueDay[]>([]);
  useEffect(() => {
    apiClient.get('/api/v1/revenue').then((r) => setDays(r.data.data)); // BAD: a page fetching in an effect
  }, []);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={days.map((d) => ({ day: d.date, revenue: d.totalCents / 100 }))}>
        <Tooltip />
        <Area dataKey="revenue" stroke="#3b82f6" fill="hsl(var(--chart-1))" />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

Six defects, and not one of them throws:

- **`'use client'` on a page:** no `await`, no numbers in the HTML, an empty first paint
  (`std-nextjs`: pages and layouts never take the directive).
- **No size:** `height="100%"` of a parent with no height is 0 — Recharts logs "The width(0) and
  height(0) of chart should be greater than 0" and draws nothing. `ChartContainer` ships
  `aspect-video`; keep a size whenever you override its `className`.
- **`hsl(var(--chart-1))`:** the token already holds a complete colour, so the wrapped value is
  invalid and the browser drops it without a word (shadcn/ui — Tailwind v4). **`#3b82f6`** ignores
  dark mode and the contrast measurement the token set carries.
- **A bare `<Tooltip />`** prints the raw `dataKey`; **no text alternative** leaves the numbers in
  SVG paths and a hover.

### Good — the page reads the URL, the panel fetches, the leaf draws

```tsx
// app/(app)/(reports)/reports/revenue/page.tsx — Server Component
import { Suspense } from 'react';
import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { ChartSkeleton } from '@/components/molecules/ChartSkeleton/ChartSkeleton';
import { RevenuePanel } from '@/components/organisms/RevenuePanel/RevenuePanel';
import { revenueRange } from '@/schemas/revenue-range'; // zod: the range is list state, so it lives in the URL

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('dashboard.revenue');
  return { title: t('title') };
}

export default async function RevenuePage({ searchParams }: { searchParams: SearchParams }) {
  const t = await getTranslations('dashboard.revenue');
  const parsed = revenueRange.safeParse(await searchParams);
  const range = parsed.success ? parsed.data : revenueRange.parse({}); // a stale or tampered URL falls back
  return (
    <>
      <h1 tabIndex={-1} className="text-2xl font-semibold text-foreground">{t('title')}</h1>
      <Suspense key={JSON.stringify(range)} fallback={<ChartSkeleton />}>
        <RevenuePanel range={range} />
      </Suspense>
    </>
  );
}
```

```tsx
// src/components/organisms/RevenuePanel/RevenueChart.tsx — 'use client': points in, plot out
'use client';

import { useCallback, useMemo } from 'react';
import { useFormatter, useTranslations } from 'next-intl';
import { useReducedMotion } from 'framer-motion';
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart';
import type { RevenuePoint } from '@/domain/revenue';

export function RevenueChart({ points, currency }: { points: RevenuePoint[]; currency: string }) {
  const t = useTranslations('dashboard.revenue');
  const format = useFormatter();
  const reduceMotion = useReducedMotion();

  const config = useMemo<ChartConfig>(() => ({ revenue: { label: t('series'), color: 'var(--chart-1)' } }), [t]);
  const compactMoney = useCallback(
    (value: number) => format.number(value, { style: 'currency', currency, notation: 'compact' }),
    [format, currency],
  );

  return (
    <ChartContainer config={config} className="aspect-video w-full">
      <AreaChart accessibilityLayer data={points}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="day" tickLine={false} axisLine={false} tickMargin={8} />
        <YAxis tickFormatter={compactMoney} tickLine={false} axisLine={false} width={72} />
        <ChartTooltip cursor={false} content={<ChartTooltipContent indicator="line" />} />
        <Area dataKey="revenue" type="monotone" stroke="var(--color-revenue)" fill="var(--color-revenue)"
          fillOpacity={0.4} isAnimationActive={!reduceMotion} />
      </AreaChart>
    </ChartContainer>
  );
}
```

- `ChartContainer` renders `ChartStyle`, which writes `--color-revenue: var(--chart-1)` scoped to
  this chart for light and `.dark` (shadcn/ui — Chart). The token already switches with the theme,
  so the house never needs `ChartConfig`'s `theme: { light, dark }`, which exists for literal colours.
- `config` is memoized on `t`, so labels re-translate when the locale changes and at no other
  render; `ChartTooltipContent` reads its labels and swatches from the same config.
- **`points` needs no memo in the leaf** — it arrives from the server, so its identity changes only
  when the server renders again. Anything derived from it (a rolling average) is `useMemo` on `points`.
- **The formatter is built here, not passed in.** A function prop from a Server Component fails
  serialization; the currency code crosses, and `useFormatter()` does the rest.
- `accessibilityLayer` is Recharts 3's default and is written anyway: a snippet copied from
  Recharts 2, where it defaulted to `false`, would otherwise ship without it.

---

## Decision: loading, empty, and error states

The states belong to the server, before any client code is involved:

```tsx
// src/components/organisms/RevenuePanel/RevenuePanel.tsx — Server Component: states first, chart last
import { getTranslations } from 'next-intl/server';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { fetchRevenue } from '@/api/revenue';
import { toRevenuePoints, type RevenueRange } from '@/domain/revenue';
import { RevenueChart } from './RevenueChart'; // by file path: never re-exported through a barrel
import { RevenueFigure } from './RevenueFigure';

export async function RevenuePanel({ range }: { range: RevenueRange }) {
  const t = await getTranslations('dashboard.revenue');
  const revenue = await fetchRevenue(range); // throws on failure: the segment's error.tsx renders
  const points = toRevenuePoints(revenue.days); // plain objects, safe to cross the boundary

  if (points.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{t('emptyTitle')}</EmptyTitle>
          <EmptyDescription>{t('emptyDescription')}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <RevenueFigure points={points} currency={revenue.currency}>
      <RevenueChart points={points} currency={revenue.currency} />
    </RevenueFigure>
  );
}
```

```tsx
// src/components/molecules/ChartSkeleton/ChartSkeleton.tsx — the chart's own box, so nothing jumps
import { Skeleton } from '@/components/ui/skeleton';

export function ChartSkeleton() {
  return <Skeleton aria-busy="true" className="aspect-video w-full rounded-lg" />;
}
```

- **Pending** → the `Suspense` fallback, or the segment's `loading.tsx`: a `Skeleton` the size of
  the chart. The page keys the boundary on the range, so a new range shows the skeleton again.
- **Error** → the segment's `error.tsx`: `'use client'`, `role="alert"`, a translated message, a
  reset (@skills/std-nextjs/references/rendering.md). Never an empty chart.
- **Empty** → shadcn's `Empty`, which carries no `'use client'`. A chart handed `[]` is not an empty
  state: a bare grid reads as "zero" — a false statement about the business.

---

## Decision: making the chart accessible

An `<svg>` of paths is not a sentence. `accessibilityLayer` "adds keyboard access and screen reader
support" (shadcn/ui — Chart): it makes the plot operable one data point at a time. It does not say
the total, the peak or the trend, and does nothing for a reader who never focuses the chart. The
words ship with the chart, rendered on the server:

```tsx
// src/components/organisms/RevenuePanel/RevenueFigure.tsx — Server Component: caption, summary, the numbers
import type { ReactNode } from 'react';
import { getFormatter, getTranslations } from 'next-intl/server';
import type { RevenuePoint } from '@/domain/revenue';

interface RevenueFigureProps { points: RevenuePoint[]; currency: string; children: ReactNode }

export async function RevenueFigure({ points, currency, children }: RevenueFigureProps) {
  const t = await getTranslations('dashboard.revenue');
  const format = await getFormatter();
  const money = (value: number) => format.number(value, { style: 'currency', currency });
  const total = points.reduce((sum, point) => sum + point.revenue, 0);
  const peak = points.reduce((best, point) => (point.revenue > best.revenue ? point : best));

  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-medium">{t('title')}</figcaption>
      <p className="text-sm text-muted-foreground">
        {t('summary', { total: money(total), peak: money(peak.revenue), peakDay: peak.day })}
      </p>
      {children}
      <table className="sr-only">
        <caption>{t('tableCaption')}</caption>
        <thead>
          <tr><th scope="col">{t('day')}</th><th scope="col">{t('series')}</th></tr>
        </thead>
        <tbody>
          {points.map((point) => (
            <tr key={point.day}><th scope="row">{point.day}</th><td>{money(point.revenue)}</td></tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
```

- **Caption and summary: always.** The `figcaption` names the metric and the period; one visible
  sentence, built from the data, carries what the chart is for.
- **The data as a table whenever a value would otherwise live only in the tooltip** — `sr-only`, or
  behind a visible "Show data" toggle, never `hidden`. Rendered on the server, it costs no client
  JavaScript and is in the HTML before the chart chunk arrives.
- **Never colour alone.** A second line gets `strokeDasharray`; more than one series gets
  `ChartLegend` with `ChartLegendContent`; bars and slices can take a Recharts `LabelList`. Chart
  colours are graphical objects, so they need 3:1 against their surface (WCAG 1.4.11) — which is why
  they are registered, measured tokens (@skills/theming/references/design-tokens.md).
- What the primitives around the chart guarantee, and their label props →
  @skills/std-shadcn-ui/references/accessibility-and-i18n.md.

---

## Decision: reduced motion

```tsx
const reduceMotion = useReducedMotion(); // framer-motion — the switch the page transitions use

<Bar dataKey="orders" fill="var(--color-orders)" radius={4} isAnimationActive={!reduceMotion} />
```

- Recharts 3's series default is `isAnimationActive: 'auto'`, documented in the 3.8.0 `Bar` source
  as respecting `prefers-reduced-motion` (Recharts — Bar source). The explicit prop puts charts on the
  page's `useReducedMotion()` switch and makes the obligation visible in review.
- **Never a bare `isAnimationActive` or `isAnimationActive={true}`** — both override the user. The
  CSS backstop is not the control: a Recharts series animates in JavaScript.
- Series animate only in the browser, where the hook reads the preference. Check once, with reduced
  motion on in the OS, that the chart draws without a transition and the console shows no hydration
  warning.

---

## Decision: loading the chart module

`@/components/ui/chart` starts with `'use client'` and imports Recharts itself, so importing
`ChartContainer` imports Recharts. The chart leaf is the one place that import lives.

- **Import the leaf by its file path.** A barrel (`components/index.ts`, or an atomic directory's
  `index.ts`) that re-exports it drags Recharts into every Client Component importing the barrel.
- **A chart the first view does not show** — in a tab, a disclosure, a dialog — loads when it
  renders, through `next/dynamic` in the client component that owns the tab:

```tsx
const OrdersByStatusChart = dynamic(
  () => import('@/components/organisms/OrdersPanel/OrdersByStatusChart').then((m) => m.OrdersByStatusChart),
  { loading: () => <ChartSkeleton /> },
);
```

**Measure, don't quote.** `@next/bundle-analyzer` (the `std-nextjs` skill's Performance rule) shows
which client chunk holds `recharts` and which routes load it. Read that before trusting a size
written down anywhere.

---

## Decision: testing a chart

- **The data mapping** (`toRevenuePoints`) is a pure function: test it without a DOM.
- **The words** are a Server Component: `render(await RevenueFigure({ … }))` with `next-intl/server`
  mocked at the module boundary, then assert the summary and the table cells →
  @skills/std-testing/references/nextjs-server.md.
- **The leaf** renders under RTL with `ResizeObserver` stubbed in the test setup. jsdom does no
  layout, so never assert SVG paths — that tests Recharts, not your code →
  @skills/std-testing/references/react-components.md.

---

## Where a chart starts from

- Add the primitive once per package — `chart`, through the CLI, after `--dry-run`, never with
  `--overwrite` → @skills/std-shadcn-ui/references/cli-and-registry.md. The registry item pins
  recharts 3.8.0, which declares `react-is` as a peer covering React 19, so npm installs a matching
  copy with no override (shadcn/ui — chart registry item; npm — recharts 3.8.0). Add an `overrides`
  entry only if `npm ls react-is` shows a major other than React's, and pin it to the installed
  React version — never the RC string in shadcn/ui's React 19 example (shadcn/ui — React 19). pnpm,
  bun and yarn need no flag.
- shadcn's 70 `chart-*` blocks live in the `new-york-v4` (Radix) registry; `base-nova` has none, so a
  Base UI package composes from `chart` as above (shadcn/ui — registry indexes). On a Radix package a
  block is a starting point only: its demo data, English labels and fixed pixel heights go, and its
  fetch moves into a Server Component → @skills/std-shadcn-ui/references/components-and-blocks.md.

---

## Sources

- shadcn/ui — Chart — https://ui.shadcn.com/docs/components/radix/chart
- shadcn/ui — Tailwind v4 — https://ui.shadcn.com/docs/tailwind-v4
- shadcn/ui — React 19 — https://ui.shadcn.com/docs/react-19
- shadcn/ui — chart registry item (new-york-v4) — https://ui.shadcn.com/r/styles/new-york-v4/chart.json
- npm — recharts 3.8.0 — https://registry.npmjs.org/recharts/3.8.0
- shadcn/ui — registry indexes (new-york-v4, base-nova) — https://ui.shadcn.com/r/styles/new-york-v4/registry.json, https://ui.shadcn.com/r/styles/base-nova/registry.json
- Recharts — Bar source (v3.8.0) — https://github.com/recharts/recharts/blob/v3.8.0/src/cartesian/Bar.tsx
