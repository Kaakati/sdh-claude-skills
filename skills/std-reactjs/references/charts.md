# Charts (ApexCharts)

Load-bearing rules restated (hold even if you read nothing else):

1. **ApexCharts is the charting library** (`react-apexcharts`). No d3, no Chart.js, no Recharts.
2. **It is heavy (~150KB gzip) and route-specific — load it lazily.** It never belongs in the
   entry chunk.
3. **Chart data comes from TanStack Query**, transformed with `useMemo` — never fetched inside
   the chart component.
4. **`series` and `options` must be memoized.** ApexCharts diffs them by reference.
5. **Colours come from design tokens, never literal hex**, and a chart is never encoded by colour
   alone.

---

## Decision: rendering a chart

### Bad — options rebuilt every render, data fetched inside, no memo

```tsx
// src/components/RevenueChart.tsx  ❌
import Chart from 'react-apexcharts';
import { useEffect, useState } from 'react';

export function RevenueChart() {
  const [data, setData] = useState<Point[]>([]);
  useEffect(() => {                                     // ❌ useEffect fetching
    axios.get('/api/revenue').then((r) => setData(r.data.data));
  }, []);

  return (
    <Chart
      type="area"
      height={320}
      series={[{ name: 'Revenue', data: data.map((d) => d.amount) }]}  // ❌ new array identity every render
      options={{                                                        // ❌ new object every render →
        chart: { id: 'revenue' },                                       //    ApexCharts tears down and
        xaxis: { categories: data.map((d) => d.date) },                 //    rebuilds the SVG each time
        colors: ['#3b82f6'],                                            // ❌ hardcoded hex, ignores theme
      }}
    />
  );
}
```

ApexCharts diffs `options` by reference. A fresh object each render forces a full chart
re-initialisation — visible flicker, lost tooltip state, and dropped frames on every parent
update.

### Good

```tsx
// src/components/charts/RevenueChart.tsx  ✅
import { lazy, Suspense, useMemo } from 'react';
import type { ApexOptions } from 'apexcharts';
import { useUiStore } from '@/stores/ui-store';
import type { RevenuePoint } from '@/domain/revenue';

const Chart = lazy(() => import('react-apexcharts'));

interface RevenueChartProps {
  points: RevenuePoint[];
  currency: string;
}

export function RevenueChart({ points, currency }: RevenueChartProps) {
  const theme = useUiStore((s) => s.theme);

  const series = useMemo<ApexAxisChartSeries>(
    () => [{ name: 'Revenue', data: points.map((p) => ({ x: p.date, y: p.amount })) }],
    [points],
  );

  const options = useMemo<ApexOptions>(
    () => ({
      chart: {
        id: 'revenue',
        type: 'area',
        toolbar: { show: false },
        animations: { enabled: !window.matchMedia('(prefers-reduced-motion: reduce)').matches },
        fontFamily: 'inherit',
        background: 'transparent',
      },
      theme: { mode: theme },
      colors: ['rgb(var(--color-primary))'],   // ✅ design token, not a literal
      dataLabels: { enabled: false },
      stroke: { curve: 'smooth', width: 2 },
      xaxis: { type: 'datetime' },
      yaxis: {
        labels: {
          formatter: (v: number) =>
            new Intl.NumberFormat(undefined, { style: 'currency', currency, notation: 'compact' }).format(v),
        },
      },
      tooltip: { theme },
      grid: { borderColor: theme === 'dark' ? '#334155' : '#e2e8f0' },
    }),
    [theme, currency],
  );

  return (
    <Suspense fallback={<div className="h-80 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />}>
      <Chart type="area" series={series} options={options} height={320} />
    </Suspense>
  );
}
```

```tsx
// src/pages/Dashboard.tsx  ✅ data comes from Query, chart is presentational
export default function Dashboard() {
  const { data, isPending } = useRevenue({ range: '30d' });
  if (isPending) return <PageSkeleton />;
  return <RevenueChart points={data.points} currency={data.currency} />;
}
```

**Rule:** chart components take data as props. They never call `useQuery` themselves — that makes
them unusable in Storybook, in tests, and in any page with a different query shape.

Note the chart's own `animations.enabled` is gated on `prefers-reduced-motion`. ApexCharts is not
Framer Motion and has no `useReducedMotion` hook — you must read the media query yourself.

---

## Decision: making the chart accessible

An `<svg>` full of paths is invisible to a screen reader. ApexCharts will not fix that for you.

```tsx
<figure role="group" aria-labelledby="revenue-chart-title">
  <figcaption id="revenue-chart-title" className="text-sm font-medium">
    Revenue, last 30 days
  </figcaption>

  <Chart type="area" series={series} options={options} height={320} />

  {/* The chart's data, available to assistive tech and to anyone who can't read the plot. */}
  <table className="sr-only">
    <caption>Revenue by day</caption>
    <thead>
      <tr><th scope="col">Date</th><th scope="col">Revenue</th></tr>
    </thead>
    <tbody>
      {points.map((p) => (
        <tr key={p.date}>
          <th scope="row">{p.date}</th>
          <td>{formatCurrency(p.amount, currency)}</td>
        </tr>
      ))}
    </tbody>
  </table>
</figure>
```

Also: never encode a series by colour alone. Use `stroke.dashArray` or `markers.shape` so the
chart survives a colour-vision deficiency and a greyscale print.

---

## Bundle note

`apexcharts` + `react-apexcharts` is ~150KB gzip — half the SPA's entire 300KB initial-JS budget.
If only the dashboard charts, give it its own `manualChunks` entry (see
`references/routing-and-code-split.md`) and lazy the chart component itself, as above.
