# Charts (ApexCharts) & Animation (Framer Motion)

Load-bearing rules restated (hold even if you read nothing else):

1. **ApexCharts is the charting library** (`react-apexcharts`). **Framer Motion is the animation
   library.** No d3, no Chart.js, no CSS keyframe libraries.
2. **Both are heavy and route-specific — load them lazily.** Neither belongs in the entry chunk.
3. **Every animation must respect `prefers-reduced-motion`.** This is a WCAG obligation, not a
   nicety.
4. **Chart data comes from TanStack Query**, transformed with `useMemo` — never fetched inside
   the chart component.

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

---

## Chart accessibility

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

## Decision: animating with Framer Motion

### Reduced motion — the non-negotiable

`useReducedMotion()` returns the user's OS setting and updates live.

### Bad

```tsx
// ❌ animates regardless of user preference; can trigger vestibular disorders
<motion.div
  initial={{ opacity: 0, y: 40, scale: 0.9 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  transition={{ duration: 0.6 }}
>
  {children}
</motion.div>
```

### Good

```tsx
// src/components/motion/FadeIn.tsx  ✅
import { motion, useReducedMotion } from 'framer-motion';
import type { ReactNode } from 'react';

export function FadeIn({ children }: { children: ReactNode }) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0.15 : 0.3, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
```

Reduced motion means *reduced*, not *removed*: keep the opacity cross-fade so state changes
remain perceivable; drop the translation, scale, and parallax.

---

## Decision: what may I animate?

Only **`transform`** and **`opacity`** — they run on the compositor and never trigger layout.

### Bad — animating layout properties

```tsx
<motion.div
  animate={{ width: isOpen ? 280 : 64, height: 'auto', top: y }}  // ❌ layout thrash every frame
/>
```

### Good — transform-based, or let Framer's layout engine do it

```tsx
// Option A: transform only
<motion.div
  className="w-70"
  animate={{ x: isOpen ? 0 : -216 }}
  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
/>

// Option B: `layout` prop — Framer measures and runs it as a transform (FLIP)
<motion.aside layout className={cn('shrink-0', isOpen ? 'w-70' : 'w-16')}>
  <SidebarContent collapsed={!isOpen} />
</motion.aside>
```

---

## Decision: page transitions

Requires `AnimatePresence` + a `key` that changes per route, and `mode="wait"` so the outgoing
page finishes before the incoming one mounts.

```tsx
// src/components/layouts/AppLayout.tsx
import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';

export function AppLayout() {
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: shouldReduceMotion ? 0 : -8 }}
            transition={{ duration: 0.2 }}
          >
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
```

Without `key={location.pathname}` React reuses the same element and `AnimatePresence` never sees
an exit. Without `mode="wait"` both pages overlap mid-transition.

---

## Decision: list item enter/exit

```tsx
// Bad ❌ — no key on the motion element, or index as key: exits animate the wrong row
{orders.map((order, i) => (
  <motion.li key={i} exit={{ opacity: 0 }}>{order.reference}</motion.li>
))}

// Good ✅ — stable key, AnimatePresence wrapping, layout for reflow
<AnimatePresence initial={false}>
  {orders.map((order) => (
    <motion.li
      key={order.id}
      layout
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.18 }}
      className="overflow-hidden border-b border-slate-200 dark:border-slate-800"
    >
      <OrderRow order={order} />
    </motion.li>
  ))}
</AnimatePresence>
```

`height: 'auto'` is the documented exception to the transform-only rule — Framer measures it and
it is the only way to collapse a row cleanly. Keep it to list rows and accordions.

---

## Bundle note

`framer-motion` is ~35KB gzip; `apexcharts` + `react-apexcharts` is ~150KB gzip. If only the
dashboard charts, give both their own `manualChunks` entry (see the routing reference) and lazy
the chart component. For simple hover/press feedback, prefer a Tailwind `transition-colors`
utility over pulling `framer-motion` into a route that has no other animation.
