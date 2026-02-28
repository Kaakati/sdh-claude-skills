# ReactJS (Vite SPA) — UI Patterns

## Framer Motion Page Transitions

```tsx
// web/src/components/PageTransition.tsx
import { motion } from 'framer-motion';

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -12 },
};

export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
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
import { motion } from 'framer-motion';

const itemVariants = {
  hidden: { opacity: 0, x: -20 },
  visible: (i: number) => ({
    opacity: 1,
    x: 0,
    transition: { delay: i * 0.05, duration: 0.2 },
  }),
};

export function AnimatedList<T extends { id: string }>({
  items,
  renderItem,
}: {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <motion.div
          key={item.id}
          custom={i}
          variants={itemVariants}
          initial="hidden"
          animate="visible"
        >
          {renderItem(item)}
        </motion.div>
      ))}
    </div>
  );
}
```

## ApexCharts Revenue Chart

```tsx
// web/src/components/charts/RevenueChart.tsx
import Chart from 'react-apexcharts';
import type { ApexOptions } from 'apexcharts';

interface RevenueChartProps {
  data: { month: string; revenue: number }[];
}

export function RevenueChart({ data }: RevenueChartProps) {
  const options: ApexOptions = {
    chart: { id: 'revenue-chart', toolbar: { show: false } },
    xaxis: { categories: data.map((d) => d.month) },
    stroke: { curve: 'smooth', width: 2 },
    colors: ['#3b82f6'],
    fill: { type: 'gradient', gradient: { opacityFrom: 0.4, opacityTo: 0.05 } },
    tooltip: { y: { formatter: (val: number) => `$${val.toLocaleString()}` } },
  };

  const series = [{ name: 'Revenue', data: data.map((d) => d.revenue) }];

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm dark:bg-gray-900">
      <h3 className="mb-4 text-lg font-semibold">Revenue Overview</h3>
      <Chart type="area" height={300} options={options} series={series} />
    </div>
  );
}
```

## ApexCharts Donut Chart

```tsx
// web/src/components/charts/OrderStatusChart.tsx
import Chart from 'react-apexcharts';
import type { ApexOptions } from 'apexcharts';

interface OrderStatusChartProps {
  counts: Record<string, number>;
}

export function OrderStatusChart({ counts }: OrderStatusChartProps) {
  const labels = Object.keys(counts);
  const series = Object.values(counts);

  const options: ApexOptions = {
    labels,
    colors: ['#f59e0b', '#3b82f6', '#8b5cf6', '#10b981', '#ef4444'],
    legend: { position: 'bottom' },
    plotOptions: { pie: { donut: { size: '60%' } } },
  };

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm dark:bg-gray-900">
      <h3 className="mb-4 text-lg font-semibold">Order Status</h3>
      <Chart type="donut" height={300} options={options} series={series} />
    </div>
  );
}
```
