# ReactJS (Vite SPA) — Component Patterns

House components are composed from the shadcn/ui primitives in `components/ui/`, which are the
atom tier. Read `components.json` first: its `style` names the base (`base-*` → Base UI;
`radix-*`, `new-york` or `default` → Radix), and the dialog below marks the one line where the two
APIs differ. Reuse before `add`, and the rest of the CLI protocol →
`@skills/std-shadcn-ui/references/cli-and-registry.md`.

## Page Component Pattern

```tsx
// web/src/pages/Orders.tsx
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useOrders } from '@/api/orders';
import { OrderTable } from '@/components/organisms/OrderTable/OrderTable';
import { OrderFilters } from '@/components/molecules/OrderFilters/OrderFilters';
import { PageHeader } from '@/components/molecules/PageHeader/PageHeader';

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

`PageHeader` is a house composition, so it lives on the atomic ladder — `components/ui/` belongs
to the CLI.

## Auth Guard Component

```tsx
// web/src/components/templates/AuthGuard/AuthGuard.tsx
import { Navigate, useLocation } from 'react-router';
import { useAuthStore } from '@/stores/auth';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

## Form: react-hook-form + zod + shadcn `Field`

```tsx
// web/src/components/organisms/CreateCustomerForm/CreateCustomerForm.tsx
import { Controller, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslation } from 'react-i18next';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { useCreateCustomer } from '@/api/customers';
import { errorText } from '@/lib/form-errors';

const schema = z.object({
  name: z.string().min(1, 'customers.form.nameRequired'),
  email: z.string().email('customers.form.emailInvalid'),
});

type CreateCustomerFormData = z.infer<typeof schema>;

export function CreateCustomerForm({ onSuccess }: { onSuccess: () => void }) {
  const { t } = useTranslation();
  const createCustomer = useCreateCustomer();
  const form = useForm<CreateCustomerFormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', email: '' },
  });

  const onSubmit = form.handleSubmit((data) => createCustomer.mutate(data, { onSuccess }));

  return (
    <form onSubmit={onSubmit} noValidate>
      <FieldGroup>
        <Controller
          name="name"
          control={form.control}
          render={({ field, fieldState }) => (
            <Field data-invalid={fieldState.invalid}>
              <FieldLabel htmlFor="name">{t('customers.form.name')}</FieldLabel>
              <Input {...field} id="name" aria-invalid={fieldState.invalid}
                aria-describedby={fieldState.invalid ? 'name-error' : undefined} />
              {fieldState.invalid && <FieldError id="name-error">{errorText(t, fieldState.error)}</FieldError>}
            </Field>
          )}
        />
        <Button type="submit" disabled={createCustomer.isPending}>
          {t(createCustomer.isPending ? 'customers.form.creating' : 'customers.form.create')}
        </Button>
      </FieldGroup>
    </form>
  );
}
```

The `email` field is the same `Controller` block; more than one text input is the house
`TextField` molecule, and `errorText` shows a server message as sent instead of looking it up as a
key → `@skills/std-shadcn-ui/references/forms-and-feedback.md`. Mapping the API's
`VALIDATION_ERROR` details onto fields and rendering the root error →
`@skills/std-reactjs/references/forms.md`.

## Composing a Primitive: Base-Correct APIs

```tsx
// web/src/components/organisms/OrderDetailsDialog/OrderDetailsDialog.tsx — a Base UI package (style "base-nova")
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { OrderSummary } from '@/components/molecules/OrderSummary/OrderSummary';
import type { Order } from '@/domain/order';

export function OrderDetailsDialog({ order }: { order: Order }) {
  const { t } = useTranslation();

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="outline" />}>{t('orders.details.open')}</DialogTrigger>
      <DialogContent closeLabel={t('common.close')}>
        <DialogHeader>
          <DialogTitle>{t('orders.details.title', { reference: order.reference })}</DialogTitle>
          <DialogDescription>{t('orders.details.description')}</DialogDescription>
        </DialogHeader>
        <OrderSummary order={order} />
      </DialogContent>
    </Dialog>
  );
}
```

On a Radix package (`new-york`, `radix-*`) the trigger is the one line that changes:

```tsx
<DialogTrigger asChild>
  <Button variant="outline">{t('orders.details.open')}</Button>
</DialogTrigger>
```

- Write the API of the base the package is on. `asChild` is not a Base UI prop and `render` is not
  a Radix one — an example copied from the other base's docs stops composing with your `Button`.
  One base per package.
- `closeLabel` is the label prop the house adds to the vendored `DialogContent` in place of its
  hardcoded "Close" → `@skills/std-shadcn-ui/references/accessibility-and-i18n.md`.
- An irreversible action is an `AlertDialog` that closes on success, not on click — and the two
  bases differ there as well → `@skills/std-shadcn-ui/references/forms-and-feedback.md`. The full
  Base UI vs Radix API table → `@skills/std-shadcn-ui/references/components-and-blocks.md`.

## cn() Utility

```ts
// web/src/lib/utils.ts — a shadcn/ui package (written by the CLI; registry components import cn from "cn")
export { cn } from 'cn';
```

```ts
// web/src/lib/utils.ts — a package without shadcn/ui, or one still on Tailwind v3
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Call sites import `cn` from `@/lib/utils` either way. The `cn` package supports Tailwind v4 only;
shadcn's own migration note keeps Tailwind v3 projects on `tailwind-merge` v2.
