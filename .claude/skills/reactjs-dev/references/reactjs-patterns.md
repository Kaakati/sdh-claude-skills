# ReactJS (Vite SPA) Code Patterns

Reference patterns for building ReactJS web SPA features with Vite.

## Page Component Pattern

```tsx
// web/src/pages/Orders.tsx
import { useState } from 'react';
import { useOrders } from '../api/orders';
import { OrderTable } from '../components/OrderTable';
import { OrderFilters } from '../components/OrderFilters';
import { PageHeader } from '../components/ui/PageHeader';
import { useTranslation } from 'react-i18next';

export default function OrdersPage() {
  const { t } = useTranslation();
  const [filters, setFilters] = useState({ status: '', page: 1 });
  const { data: orders, isLoading, error } = useOrders(filters);

  return (
    <div className="space-y-6">
      <PageHeader title={t('orders.title')} />
      <OrderFilters value={filters} onChange={setFilters} />
      <OrderTable orders={orders ?? []} isLoading={isLoading} error={error} />
    </div>
  );
}
```

## Zustand Store with localStorage Persistence

```typescript
// web/src/stores/ui-preferences.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface UIPreferencesState {
  sidebarCollapsed: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

export const useUIPreferences = create<UIPreferencesState>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      theme: 'system',
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setTheme: (theme) => set({ theme }),
    }),
    { name: 'ui-preferences' },
  ),
);
```

## React Router Configuration

```tsx
// web/src/router/index.tsx
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AppLayout } from '../components/AppLayout';
import { AuthGuard } from '../components/AuthGuard';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

const Dashboard = lazy(() => import('../pages/Dashboard'));
const Orders = lazy(() => import('../pages/Orders'));
const OrderDetail = lazy(() => import('../pages/OrderDetail'));
const Login = lazy(() => import('../pages/Login'));
const NotFound = lazy(() => import('../pages/NotFound'));

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<LoadingSpinner />}>{children}</Suspense>;
}

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <SuspenseWrapper><Login /></SuspenseWrapper>,
  },
  {
    path: '/',
    element: <AuthGuard><AppLayout /></AuthGuard>,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: 'dashboard', element: <SuspenseWrapper><Dashboard /></SuspenseWrapper> },
      { path: 'orders', element: <SuspenseWrapper><Orders /></SuspenseWrapper> },
      { path: 'orders/:id', element: <SuspenseWrapper><OrderDetail /></SuspenseWrapper> },
    ],
  },
  { path: '*', element: <SuspenseWrapper><NotFound /></SuspenseWrapper> },
]);
```

## Auth Guard Component

```tsx
// web/src/components/AuthGuard.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/auth';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

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

## ApexCharts Dashboard Widget

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

## Donut Chart Widget

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

## react-hook-form + zod + Tailwind Form

```tsx
// web/src/components/forms/CreateOrderForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useCreateOrder } from '../../api/orders';
import { cn } from '../../lib/cn';

const schema = z.object({
  customerName: z.string().min(1, 'Customer name is required'),
  email: z.string().email('Invalid email address'),
  items: z.array(z.object({
    productId: z.string().min(1),
    quantity: z.number().positive('Quantity must be positive'),
  })).min(1, 'At least one item is required'),
});

type CreateOrderFormData = z.infer<typeof schema>;

export function CreateOrderForm({ onSuccess }: { onSuccess: () => void }) {
  const createOrder = useCreateOrder();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<CreateOrderFormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: CreateOrderFormData) => {
    await createOrder.mutateAsync(data);
    onSuccess();
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label htmlFor="customerName" className="block text-sm font-medium">
          Customer Name
        </label>
        <input
          id="customerName"
          {...register('customerName')}
          className={cn(
            'mt-1 block w-full rounded-md border px-3 py-2 shadow-sm focus:outline-none focus:ring-2',
            errors.customerName
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-300 focus:ring-blue-500',
          )}
        />
        {errors.customerName && (
          <p className="mt-1 text-sm text-red-600">{errors.customerName.message}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Creating...' : 'Create Order'}
      </button>
    </form>
  );
}
```

## cn() Utility (clsx + tailwind-merge)

```typescript
// web/src/lib/cn.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

## API Client with Interceptors

```typescript
// web/src/api/client.ts
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);
```

## Vitest Component Test

```tsx
// web/src/components/OrderTable.test.tsx
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { OrderTable } from './OrderTable';
import { createTestOrder } from '../../tests/factories';

describe('OrderTable', () => {
  it('should render order rows when orders are provided', () => {
    const orders = [createTestOrder({ id: '1', status: 'pending' })];

    render(<OrderTable orders={orders} isLoading={false} error={null} />);

    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('should show loading skeleton when isLoading is true', () => {
    render(<OrderTable orders={[]} isLoading={true} error={null} />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('should show empty state when no orders exist', () => {
    render(<OrderTable orders={[]} isLoading={false} error={null} />);

    expect(screen.getByText(/no orders/i)).toBeInTheDocument();
  });
});
```

## TanStack Query Hook with MSW

```typescript
// web/src/api/__tests__/orders.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/msw-server';
import { useOrders } from '../orders';
import { createQueryWrapper } from '../../tests/utils';

describe('useOrders', () => {
  it('should fetch orders from the API', async () => {
    server.use(
      http.get('*/api/v1/orders', () => {
        return HttpResponse.json([
          { id: '1', status: 'pending', totalAmount: 100 },
        ]);
      }),
    );

    const { result } = renderHook(() => useOrders(), { wrapper: createQueryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0].status).toBe('pending');
  });
});
```
