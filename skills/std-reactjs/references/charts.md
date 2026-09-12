# Charts (Chart.js via react-chartjs-2)

The house charting standard for the **Vite SPA**: Chart.js 4.5.1 drawn through react-chartjs-2
5.3.1, both MIT (npm — chart.js; npm — react-chartjs-2). It replaced ApexCharts (`react-apexcharts`)
here in 4.0.0, over its licence; the other stacks start elsewhere:

- **Next.js** → shadcn/ui's `chart` component (Recharts) →
  `@skills/std-shadcn-ui/references/charts.md`. A Vite package never adds Recharts.
- **Rails Phlex views** → Chart.js through the house Stimulus controller →
  `@skills/std-phlex-conventions/references/charts.md`.

Where a panel, its figure and its chart module sit on the atomic ladder →
`@skills/std-shadcn-ui/references/components-and-blocks.md`.

Load-bearing rules restated (hold even if you read nothing else):

1. **Typed react-chartjs-2 components on registered parts.** `Line`, `Bar`, `Doughnut` — and one
   module, `src/lib/charts/register.ts`, registering the elements, scales and plugins in use.
   Never `chart.js/auto`.
2. **Chart modules are heavy leaf dependencies: `React.lazy` them by file path**, never through a
   barrel. Read the chunk's size off the build output.
3. **`data` and `options` are memoised on their real inputs.** Every dataset has a stable, unique
   `label` (or the chart sets `datasetIdKey`), a live stream passes `updateMode="none"`, and a
   chart module never calls `useQuery`.
4. **Colours are the CSS tokens, read at runtime through `useChartTokens`** — complete
   `hsl()`/`rgb()`/hex values, trimmed, re-read when the `.dark` class changes. Never a literal,
   never `var()`, and hover colours are set explicitly.
5. **Reduced motion sets `animation: false`.**
6. **The container is `relative`, carries a height, and holds only the canvas**;
   `maintainAspectRatio: false`.
7. **Every chart ships a text alternative outside the canvas** — caption, summary sentence, and
   the data as a table — and the canvas carries an `aria-label`. Loading, empty and error states
   render before any chart does.
8. **Tests load `vitest-canvas-mock` and stub `ResizeObserver`**, then assert the data mapping and
   the text alternative — never pixels or draw calls.

---

## Decision: registering Chart.js

Chart.js is tree-shakeable: a bundled app registers the controllers, elements, scales and plugins
it draws, and `chart.js/auto` is the quick start "if you don't care about the bundle size"
(Chart.js — Integration). react-chartjs-2's typed components register their own controller, so the
module lists everything else (react-chartjs-2 — Migration to v4).

```ts
// src/lib/charts/register.ts — imported by chart modules only, never by main.tsx or a layout
import {
  ArcElement, BarElement, CategoryScale, Chart as ChartJS, Filler, Legend,
  LinearScale, LineElement, PointElement, Tooltip,
} from 'chart.js';

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);
```

| Typed component | Register (its controller comes with it) |
|---|---|
| `Bar` | `BarElement`, `CategoryScale`, `LinearScale` |
| `Line` | `LineElement`, `PointElement`, `CategoryScale`, `LinearScale` — plus `Filler` for `fill` |
| `Doughnut`, `Pie` | `ArcElement` |
| Any chart with tooltips or a legend | `Tooltip`, `Legend` |

- **A missing element or scale throws** (`"arc" is not a registered element`); **a missing
  `Filler` does not** — Chart.js 4.5.1 draws no fill and logs `Tried to use the 'fill' option without
  the 'Filler' plugin enabled` (react-chartjs-2 — FAQ; Chart.js 4.5.1 `DatasetController`), so a
  component test can fail on that console warning.
- **Bad:** `import 'chart.js/auto'` in `main.tsx` — everything registered, all of it in the entry
  chunk.
- **Registration trims; it does not make Chart.js small.** esbuild 0.28.2, gzip: `chart.js/auto`
  70,366 bytes; a tree-shaken line chart with tooltip, legend and filler 59,577; the same through
  react-chartjs-2 60,157, its unused typed components shaken out (house lab — esbuild bundle
  measurement). Vite's numbers are the ones you check; the `lazy` boundary, not registration, keeps
  Chart.js off the first load.
- **A time axis needs a date adapter**, or it throws "This method is not implemented: Check that a
  complete date adapter is provided." Add `chartjs-adapter-date-fns` and `date-fns` only for a real
  time axis (about 6 KB more gzip in the same measurement), pass the date-fns locale as
  `scales.x.adapters.date.locale`, and know that importing the adapter replaces the default one
  (Chart.js — Time Cartesian Axis).

---

## Decision: rendering a chart

### Bad — fetched inside, new objects every render, a literal colour, no sized box

```tsx
// src/components/RevenueChart.tsx  ❌
import 'chart.js/auto';
import { Line } from 'react-chartjs-2';

export function RevenueChart() {
  const { data } = useRevenue({ range: '30d' });                        // ❌ the chart fetches
  const days = data?.days ?? [];
  return (
    <Line
      data={{
        labels: days.map((d) => d.date),
        datasets: [{ data: days.map((d) => d.totalCents / 100), borderColor: '#3b82f6' }],  // ❌
      }}
      options={{ plugins: { legend: { display: false } } }}              // ❌ a new object per render
    />
  );
}
```

Beyond the registration and the fetch, four defects — and not one of them throws:

- **New `data` and `options` every render.** react-chartjs-2 runs `chart.update()` whenever
  `options`, `data.labels` or `data.datasets` changes identity (react-chartjs-2 — Chart component
  source), so a keystroke in a filter re-animates an unchanged chart.
- **No dataset `label`.** Datasets are matched by `datasetIdKey`, `label` by default; with neither,
  a re-render can copy the first dataset over the others (react-chartjs-2 — Working with datasets).
- **`#3b82f6`** ignores dark mode and skips the contrast measurement the token set carries.
- **No sized box.** The parent must be "relatively positioned and dedicated to the chart canvas
  only", and a height set through it needs `maintainAspectRatio: false` (Chart.js — Responsive
  Charts); a canvas sized in CSS blurs or keeps shrinking.

### Good — tokens read per theme, data and options memoised

```ts
// src/lib/charts/useChartTokens.ts
import { useMemo, useSyncExternalStore } from 'react';

const root = () => document.documentElement;
const read = (name: string) => getComputedStyle(root()).getPropertyValue(name).trim();

function subscribe(onChange: () => void) {
  const observer = new MutationObserver(onChange);
  observer.observe(root(), { attributes: true, attributeFilter: ['class'] }); // the theming provider toggles `.dark`
  return () => observer.disconnect();
}

export function useChartTokens() {
  const theme = useSyncExternalStore(subscribe, () => root().className);
  return useMemo(() => ({
    theme, // in the value, so every memo that depends on the tokens re-runs on a theme change
    text: read('--muted-foreground'),
    grid: read('--border'),
    surface: read('--card'),
    series: ['--chart-1', '--chart-2', '--chart-3', '--chart-4', '--chart-5'].map(read),
  }), [theme]);
}
```

```tsx
// src/components/organisms/RevenuePanel/RevenueChart.tsx  ✅ presentational: points in, chart out
import '@/lib/charts/register';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useReducedMotion } from 'framer-motion';
import { Line } from 'react-chartjs-2';
import { color } from 'chart.js/helpers';
import type { ChartData, ChartOptions } from 'chart.js';
import { useChartTokens } from '@/lib/charts/useChartTokens';
import type { RevenuePoint } from '@/domain/revenue';

interface RevenueChartProps {
  points: RevenuePoint[];   // shaped and memoised by the caller
  currency: string;
}

export function RevenueChart({ points, currency }: RevenueChartProps) {
  const { t, i18n } = useTranslation();
  const reduceMotion = useReducedMotion();
  const tokens = useChartTokens();

  const data = useMemo<ChartData<'line'>>(() => {
    const line = tokens.series[0];
    return {
      labels: points.map((p) => p.day),
      datasets: [{
        label: t('dashboard.revenue.series'),
        data: points.map((p) => p.revenue),
        borderColor: line,
        backgroundColor: color(line).alpha(0.2).rgbString(),   // `fill` needs Filler in register.ts
        pointBackgroundColor: line,
        pointHoverBackgroundColor: line,
        fill: true,
      }],
    };
  }, [points, t, tokens]);

  const options = useMemo<ChartOptions<'line'>>(() => ({
    maintainAspectRatio: false,
    animation: reduceMotion ? false : { duration: 400 },
    locale: i18n.language,
    scales: {
      x: { ticks: { color: tokens.text }, grid: { color: tokens.grid } },
      y: {
        ticks: { color: tokens.text, format: { style: 'currency', currency, notation: 'compact' } },
        grid: { color: tokens.grid },
      },
    },
    plugins: { legend: { display: false } },
  }), [reduceMotion, i18n.language, currency, tokens]);

  return (
    <div className="relative h-64 w-full">
      <Line data={data} options={options} aria-label={t('dashboard.revenue.title')} />
    </div>
  );
}
```

- **Tokens are read, never referenced.** A canvas ignores `var(--chart-1)` and keeps its previous
  colour; Chart.js's colour parser (`@kurkle/color`) rejects it too, so hover colours come back
  `undefined` (house lab — Chrome 152, @kurkle/color 0.3.4). Trim the value: a leading space also
  fails the parser.
- **Chart tokens are complete colours without slash alpha** — the house stylesheet declares
  `--chart-1: hsl(217.2 91.2% 50%)` (`@skills/theming/references/platform-integration.md`).
  `hsl(… / 0.5)`, `oklch()`, `color-mix()` and bare channels (`217.2 91.2% 50%`, the Tailwind v3
  preset form) all fail. Derive translucency with `color(token).alpha(0.2).rgbString()` from
  `chart.js/helpers`.
- **Re-theme through options, never `Chart.defaults`.** A runtime `Chart.defaults.color` change
  leaves a mounted chart's ticks as they were (house lab — Chart.js 4.5.1); new memoised options
  restyle it, which is why `tokens` sits in both dependency lists.
- **Numbers follow the app locale.** `options.locale` takes a BCP 47 string (the platform's
  otherwise); linear ticks take `ticks.format` as `Intl.NumberFormat` options, and doughnut tooltips
  format with `options.locale` (Chart.js — Locale; Chart.js — Linear Axis).
- **The instance** is `useRef<ChartJS<'line'>>(null)` passed as `ref` (react-chartjs-2 — FAQ) —
  never kept in Zustand. **Never mutate `points` in place:** a new array is how the chart learns
  the data changed.

---

## Decision: live and large data

- **Streams:** when Centrifugo events invalidate the query and new points arrive, pass
  `updateMode="none"` — react-chartjs-2 hands it to `chart.update(mode)`, and `'none'` skips that
  update's animation (Chart.js — API). The subscription lives in a hook, never in the chart module.
- **`redraw` is not a refresh:** it destroys and rebuilds the chart, as a changed `type` does
  (react-chartjs-2 — Chart component source). New memoised props update in place.
- **Thousands of points:** `{ x, y }` data with `parsing: false` and `normalized: true`,
  `animation: false`, and server-side aggregation where the question allows (Chart.js —
  Performance). Decimation silently does nothing unless every requirement holds — line datasets,
  `indexAxis: 'x'`, a linear or time x axis, `parsing: false`, more points than its threshold
  (Chart.js — Data Decimation).

---

## Decision: loading the chart module

```tsx
const RevenueChart = lazy(() =>
  import('@/components/organisms/RevenuePanel/RevenueChart').then((m) => ({ default: m.RevenueChart })),
);
```

- **The chart module imports `@/lib/charts/register`, which imports Chart.js** — so Chart.js,
  `@kurkle/color` (its one runtime dependency) and react-chartjs-2 land in the lazy chunk only. The
  `.then` maps the named export onto the `default` that `React.lazy` requires; only pages are
  default exports.
- **By file path, never through a barrel** — not `components/index.ts`, not its atomic directory's
  `index.ts`. A barrel drags Chart.js into everything that imports it.
- **Measure, don't quote:** read the `chart.js` chunk in the build output against the initial-JS
  budget `references/routing-and-code-split.md` owns — which also names the vendor chunk and the
  `modulepreload` check.

---

## Decision: loading, empty, and error states

```tsx
// src/components/organisms/RevenuePanel/RevenuePanel.tsx  ✅ states first, chart last
import { lazy, Suspense, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { ChartSkeleton } from '@/components/molecules/ChartSkeleton/ChartSkeleton';
import { useRevenue } from '@/api/revenue';
import { toRevenuePoints, type RevenueRange } from '@/domain/revenue';
import { RevenueFigure } from './RevenueFigure';

const RevenueChart = lazy(() =>
  import('@/components/organisms/RevenuePanel/RevenueChart').then((m) => ({ default: m.RevenueChart })),
);

export function RevenuePanel({ range }: { range: RevenueRange }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useRevenue({ range });
  const points = useMemo(() => toRevenuePoints(data?.days ?? []), [data]);

  if (isPending) return <ChartSkeleton />;
  if (isError) return <p role="alert" className="text-sm text-error">{t('dashboard.revenue.loadFailed')}</p>;
  if (points.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>{t('dashboard.revenue.emptyTitle')}</EmptyTitle>
          <EmptyDescription>{t('dashboard.revenue.emptyDescription')}</EmptyDescription>
        </EmptyHeader>
      </Empty>
    );
  }

  return (
    <RevenueFigure points={points} currency={data.currency}>
      <Suspense fallback={<ChartSkeleton />}>
        <RevenueChart points={points} currency={data.currency} />
      </Suspense>
    </RevenueFigure>
  );
}
```

- **Pending** → `ChartSkeleton`: a shadcn `Skeleton` with `aria-busy` and the chart box's own size
  (`h-64 w-full`). It is also the `Suspense` fallback, so the box keeps its shape across both waits.
- **Error** → a `role="alert"` message from the translation file. Never an empty chart.
- **Empty** → shadcn's `Empty`. A chart handed `[]` draws bare axes that read as "zero" — a false
  statement about the business.

The panel owns the query and the chart stays presentational — which is what lets the chart render
in a test or a story from a literal array.

---

## Decision: making the chart accessible

Canvas content "will not be accessible to screen readers"; accessibility comes from ARIA on the
canvas or from content outside it (Chart.js — Accessibility). The words ship with the chart:

```tsx
// src/components/organisms/RevenuePanel/RevenueFigure.tsx  ✅ caption, summary, and the numbers as a table
import { useMemo, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import type { RevenuePoint } from '@/domain/revenue';

interface RevenueFigureProps {
  points: RevenuePoint[];   // non-empty: the panel renders its empty state first
  currency: string;
  children: ReactNode;      // the lazy chart
}

export function RevenueFigure({ points, currency, children }: RevenueFigureProps) {
  const { t, i18n } = useTranslation();
  const money = useMemo(
    () => new Intl.NumberFormat(i18n.language, { style: 'currency', currency }),
    [i18n.language, currency],
  );
  const total = points.reduce((sum, p) => sum + p.revenue, 0);
  const peak = points.reduce((best, p) => (p.revenue > best.revenue ? p : best));

  return (
    <figure className="space-y-2">
      <figcaption className="text-sm font-medium">{t('dashboard.revenue.title')}</figcaption>
      <p className="text-sm text-muted-foreground">
        {t('dashboard.revenue.summary', { total: money.format(total), peak: money.format(peak.revenue), peakDay: peak.day })}
      </p>
      {children}
      <RevenueTable points={points} format={money.format} />
    </figure>
  );
}

function RevenueTable({ points, format }: { points: RevenuePoint[]; format: (n: number) => string }) {
  const { t } = useTranslation();
  return (
    <table className="sr-only">
      <caption>{t('dashboard.revenue.tableCaption')}</caption>
      <thead>
        <tr>
          <th scope="col">{t('dashboard.revenue.day')}</th>
          <th scope="col">{t('dashboard.revenue.series')}</th>
        </tr>
      </thead>
      <tbody>
        {points.map((p) => (
          <tr key={p.day}>
            <th scope="row">{p.day}</th>
            <td>{format(p.revenue)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- **The canvas is a named image:** react-chartjs-2 renders `<canvas role="img">` and passes
  `aria-label` through (react-chartjs-2 — Chart component source), and an `img` must be labelled
  (W3C — WAI-ARIA 1.2). The label is the chart's name; the numbers belong to the table.
- **The table sits outside the canvas** — `img` children are presentational, so a table in
  `fallbackContent` is never exposed as one (W3C — WAI-ARIA 1.2). Caption and summary always; the
  table whenever a value would otherwise live only in the tooltip — `sr-only` or behind a visible
  "Show data" toggle, never `hidden`.
- **Never colour alone.** A second line gets `borderDash`; several series get the legend, labelled
  in `tokens.text`. Series colours need 3:1 against their surface (WCAG 1.4.11), which is why they
  are registered, measured tokens (`@skills/theming/references/design-tokens.md`).
- **Tooltips stay on the canvas.** The docs' external-tooltip example concatenates labels into
  `innerHTML` — an injection sink once a label carries user data (Chart.js — Tooltip). An HTML
  tooltip, if ever required, renders through React.
- **Accessibility plugins are extras, never the alternative.** `chartjs-plugin-a11y-legend` 0.2.2
  calls itself beta, tested on one browser and one screen reader; `chartjs-plugin-chart2music` adds
  keyboard navigation and sonification. Both depend on `chart.js` directly, so run `npm ls chart.js`
  after adding either — a second copy has its own registry.
- Label props of the primitives around the chart →
  `@skills/std-shadcn-ui/references/accessibility-and-i18n.md`.

---

## Decision: reduced motion

```tsx
const reduceMotion = useReducedMotion();                      // framer-motion — the switch page transitions use
const animation = reduceMotion ? false : { duration: 400 };   // goes into the memoised options
```

- Chart.js animates by default — 1000 ms, `easeOutQuart` — with no `prefers-reduced-motion`
  handling of its own; `animation: false` turns every animation off, tooltips included (Chart.js —
  Animations). Never leave `animation` unset on a house chart.
- The global CSS backstop cannot reach canvas animation, which is JavaScript
  (`references/animation.md`).

---

## Decision: StrictMode and the chart's lifecycle

- react-chartjs-2 builds the instance in a mount effect and destroys it in the cleanup
  (react-chartjs-2 — Chart component source). Under React 19.3's StrictMode double mount the house
  lab saw no errors and one live instance, with `ref.current` equal to `Chart.getChart(canvas)`
  (house lab — React 19.3.0, react-chartjs-2 5.3.1). React 19 joined the peer range in 5.3.0.
- **"Canvas is already in use. Chart with ID … must be destroyed…"** means a chart was built on a
  canvas that still had one (Chart.js — core controller source): in app code, Chart.js built by hand
  in an effect; in a test, usually the missing `ResizeObserver` in disguise.
- **A canvas removed without `destroy()` stays in `Chart.instances`** (house lab — Chart.js 4.5.1).
  The typed component's cleanup is the guarantee — never `new Chart()` inside a React tree.

---

## Decision: testing a chart

- **jsdom has no 2D context:** without a canvas mock, Chart.js logs "Failed to create chart: can't
  acquire context from the given item" and a test passes having asserted nothing. **Nor a
  `ResizeObserver`:** a responsive chart throws `ReferenceError`, and under StrictMode RTL reports an
  `AggregateError` that also carries "Canvas is already in use" (house lab — jsdom 30.0.1).
- **The mock is `vitest-canvas-mock` 1.2.0** — MIT, a `jest-canvas-mock` fork peering Vitest 3, 4
  and 5, published 2026-09-05, and loaded by importing it from a `setupFiles` entry (npm —
  vitest-canvas-mock). A Jest package uses `jest-canvas-mock` 2.5.8 (MIT). The native `canvas`
  addon draws real pixels — a heavier CI image for assertions no house test makes.
- **Assert** the mapping as a pure function, `Chart.getChart(canvas)` when the wiring is the point,
  and the caption, summary and table through RTL. **Never** pixels, draw-call snapshots, ticks or
  animation frames. The setup file and the bad/good pairs →
  `@skills/std-testing/references/react-components.md`.

---

## Where a chart starts from

```bash
npm install chart.js@4.5.1 react-chartjs-2@5.3.1
```

- react-chartjs-2 peers `chart.js ^4.1.1` and React 16.8 through 19 (npm — react-chartjs-2).
- One registration module and one tokens hook per package, then a chart module per panel. There is
  no shadcn primitive to add — shadcn's `chart` is Recharts, and it belongs to Next.js
  (`@skills/std-shadcn-ui/references/charts.md`). Rails views draw the same Chart.js version
  through Stimulus (`@skills/std-phlex-conventions/references/charts.md`).

---

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| A chart test is green, and the chart never existed | No canvas mock | `vitest-canvas-mock` in setup; assert `Chart.getChart(canvas)` is defined |
| `ResizeObserver is not defined`, or "Canvas is already in use" in a StrictMode test | jsdom has no `ResizeObserver` | Stub it in setup, beside the canvas mock |
| The chart re-animates on every keystroke | New `data` or `options` identity each render | `useMemo` on real inputs; `updateMode="none"` for streams |
| One series shows another's values after a re-render | Datasets without a unique `label` | Unique labels, or `datasetIdKey` |
| Hover colours missing; a stale series colour | A `var()`, bare-channel, slash-alpha, `oklch()` or untrimmed token | A complete `hsl()` token, trimmed; explicit hover colours |
| Dark mode leaves the ticks light | `Chart.defaults` changed at runtime | Tokens into memoised options |
| The chart blurs or keeps shrinking | Canvas sized in CSS, or a shared container | A `relative`, sized container holding only the canvas; `maintainAspectRatio: false` |
| `fill: true` draws nothing; `"arc" is not a registered element` | `Filler` or `ArcElement` not registered | Add it to `register.ts` |

---

## Sources

- Chart.js — Integration — https://www.chartjs.org/docs/latest/getting-started/integration.html
- Chart.js — Accessibility — https://www.chartjs.org/docs/latest/general/accessibility.html
- Chart.js — Animations — https://www.chartjs.org/docs/latest/configuration/animations.html
- Chart.js — Responsive Charts — https://www.chartjs.org/docs/latest/configuration/responsive.html
- Chart.js — API (update modes, destroy, getChart) — https://www.chartjs.org/docs/latest/developers/api.html
- Chart.js — Performance — https://www.chartjs.org/docs/latest/general/performance.html
- Chart.js — Data Decimation — https://www.chartjs.org/docs/latest/configuration/decimation.html
- Chart.js — Locale — https://www.chartjs.org/docs/latest/configuration/locale.html
- Chart.js — Linear Axis — https://www.chartjs.org/docs/latest/axes/cartesian/linear.html
- Chart.js — Tooltip — https://www.chartjs.org/docs/latest/configuration/tooltip.html
- Chart.js — Time Cartesian Axis — https://www.chartjs.org/docs/latest/axes/cartesian/time.html
- Chart.js — core controller source (v4.5.1) — https://github.com/chartjs/Chart.js/blob/v4.5.1/src/core/core.controller.js
- react-chartjs-2 — Migration to v4 (tree-shaking) — https://react-chartjs-2.js.org/docs/migration-to-v4#tree-shaking
- react-chartjs-2 — Working with datasets — https://react-chartjs-2.js.org/docs/working-with-datasets
- react-chartjs-2 — FAQ — https://react-chartjs-2.js.org/faq/registered-element ; https://react-chartjs-2.js.org/faq/fill-property ; https://react-chartjs-2.js.org/faq/chartjs-instance
- react-chartjs-2 — Chart component source (v5.3.1) — https://github.com/reactchartjs/react-chartjs-2/blob/v5.3.1/src/chart.tsx
- W3C — WAI-ARIA 1.2, the `img` role — https://www.w3.org/TR/wai-aria-1.2/#img
- npm — chart.js — https://registry.npmjs.org/chart.js
- npm — react-chartjs-2 — https://registry.npmjs.org/react-chartjs-2
- npm — vitest-canvas-mock — https://registry.npmjs.org/vitest-canvas-mock
- house lab — the round-3 Chart.js research run (2026-09-11): esbuild 0.28.2 bundle measurements;
  Chrome 152 canvas and colour-parser checks; React 19.3.0, jsdom 30.0.1 and Vitest 5.0.0
  lifecycle and test-harness runs
