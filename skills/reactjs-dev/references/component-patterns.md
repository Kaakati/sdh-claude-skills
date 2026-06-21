# ReactJS (Vite SPA) — Component Patterns

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
