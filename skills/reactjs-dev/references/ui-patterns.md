# ReactJS (Vite SPA) — UI Patterns

Worked patterns. The rules behind them — reduced motion, the transform-only rule, chart tokens,
text alternatives, lazy chart modules — are owned by `@skills/std-reactjs/references/animation.md`
and `@skills/std-reactjs/references/charts.md`.

## Framer Motion Page Transitions

```tsx
// web/src/components/PageTransition.tsx
import { motion, useReducedMotion } from 'framer-motion';

export function PageTransition({ children }: { children: React.ReactNode }) {
  const reduceMotion = useReducedMotion();
  const offset = reduceMotion ? 0 : 12;   // reduced motion keeps the fade, drops the travel

  return (
    <motion.div
      initial={{ opacity: 0, y: offset }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -offset }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
```

## Animated List Items

```tsx
// web/src/components/AnimatedList.tsx
import { motion, useReducedMotion } from 'framer-motion';

interface AnimatedListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}

export function AnimatedList<T extends { id: string }>({ items, renderItem }: AnimatedListProps<T>) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <motion.div
          key={item.id}
          initial={{ opacity: 0, x: reduceMotion ? 0 : -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: reduceMotion ? 0 : i * 0.05, duration: 0.2 }}
        >
          {renderItem(item)}
        </motion.div>
      ))}
    </div>
  );
}
```

## Revenue Line Chart

Worked end to end — the registration module, the tokens hook, the chart module, its panel with
loading, empty and error states, and the figure that carries its summary and data table — in
`@skills/std-reactjs/references/charts.md`. It is not repeated here, so the two cannot drift.

## Order Status Doughnut Chart (Chart.js)

```tsx
// web/src/components/organisms/OrderStatusCard/OrderStatusChart.tsx
import '@/lib/charts/register';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useReducedMotion } from 'framer-motion';
import { Doughnut } from 'react-chartjs-2';
import type { ChartData, ChartOptions } from 'chart.js';
import { useChartTokens } from '@/lib/charts/useChartTokens';
import type { OrderStatus } from '@/domain/order';

const STATUSES: OrderStatus[] = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled'];

export function OrderStatusChart({ counts }: { counts: Record<OrderStatus, number> }) {
  const { t, i18n } = useTranslation();
  const reduceMotion = useReducedMotion();
  const tokens = useChartTokens();

  const data = useMemo<ChartData<'doughnut'>>(() => ({
    labels: STATUSES.map((status) => t(`orders.status.${status}`)),
    datasets: [{
      label: t('orders.chart.orders'),
      data: STATUSES.map((status) => counts[status]),
      backgroundColor: tokens.series,       // one chart token per status, in STATUSES order
      hoverBackgroundColor: tokens.series,
      borderColor: tokens.surface,          // the seams between slices match the card in both themes
    }],
  }), [counts, t, tokens]);

  const options = useMemo<ChartOptions<'doughnut'>>(() => ({
    maintainAspectRatio: false,
    cutout: '60%',
    animation: reduceMotion ? false : { duration: 400 },
    locale: i18n.language,                  // doughnut tooltips format their counts with it
    plugins: { legend: { position: 'bottom', labels: { color: tokens.text } } },
  }), [reduceMotion, i18n.language, tokens]);

  return (
    <div className="relative mx-auto h-64 w-full max-w-xs">
      <Doughnut data={data} options={options} aria-label={t('orders.chart.title')} />
    </div>
  );
}
```

```tsx
// web/src/components/organisms/OrderStatusCard/OrderStatusCard.tsx
import { lazy, Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import type { OrderStatus } from '@/domain/order';

const OrderStatusChart = lazy(() =>
  import('@/components/organisms/OrderStatusCard/OrderStatusChart').then((m) => ({ default: m.OrderStatusChart })),
);

export function OrderStatusCard({ counts }: { counts: Record<OrderStatus, number> }) {
  const { t } = useTranslation();
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('orders.chart.title')}</CardTitle>
        {/* The text alternative: every count, as a sentence everyone can read. */}
        <CardDescription>{t('orders.chart.summary', { total, ...counts })}</CardDescription>
      </CardHeader>
      <CardContent>
        <Suspense fallback={<Skeleton className="mx-auto h-64 w-full max-w-xs" />}>
          <OrderStatusChart counts={counts} />
        </Suspense>
      </CardContent>
    </Card>
  );
}
```

- One chart token per status, read through `useChartTokens`, so the slice and its legend swatch
  share one source and re-theme together when `.dark` toggles. `ArcElement`, `Tooltip` and
  `Legend` come from the shared `register.ts`.
- The labels are translated, so the legend and tooltip read "Pending", not `pending`; `locale`
  formats the tooltip's counts.
- The legend is the non-colour encoding; the card description carries every count as text, which
  is also why the canvas label is only the chart's name.
- Five statuses, five chart tokens. A sixth series needs a registered, measured token, not a literal.
- The card renders only when `counts` has loaded; its caller owns the loading, empty and error
  states (`charts.md`).
