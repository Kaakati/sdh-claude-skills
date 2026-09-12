# Next.js App Router — Client Patterns

Load-bearing rules restated (this file is read standalone):

- **Forms are shadcn `Field` + react-hook-form + zod, and the server action re-checks the same
  schema with `safeParse`.** The client check is UX; the action is a public endpoint. Never
  `shadcn add form` — it is the legacy wrapper.
- **Keep `action={formAction}` on the `<form>`.** Without JavaScript the browser posts straight to
  the action; with it, the shared schema runs first and then the same action.
- **Charts are shadcn's `chart` + Recharts**, drawn in a `'use client'` leaf that a Server
  Component feeds with plain data; the Server Component renders the caption, summary and data
  table. No other chart library. The standard → `@skills/std-shadcn-ui/references/charts.md`.
- **Errors render inline; outcomes go through `notify()`.** Never a toast for a field.
- Primitives are written for the package's base (`components.json` `style`). Nothing below
  composes a trigger, so both examples read the same on Base UI and Radix. `cn` imports from
  `@/lib/utils`.

---

## Field Form on a Server Action

One schema module, imported by both sides. Its messages are translation keys, so a client error
and a server error render through the same path.

```ts
// src/schemas/order.ts — imported by the form AND the action; no directive
import { z } from 'zod';

export const CreateOrderSchema = z.object({
  customerName: z.string().min(1, 'orders.errors.customerNameRequired'),
  email: z.string().email('orders.errors.emailInvalid'),
});
export type CreateOrderInput = z.infer<typeof CreateOrderSchema>;
```

The action that re-checks it, and returns `ActionResult` →
`@skills/nextjs-dev/references/server-patterns.md`.

```tsx
// src/components/organisms/CreateOrderForm/CreateOrderForm.tsx
'use client';

import { startTransition, useActionState, useRef, type FormEvent } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { FieldGroup } from '@/components/ui/field';
import { createOrder } from '@/actions/orders';
import { CreateOrderSchema, type CreateOrderInput } from '@/schemas/order';
import { TextField } from './TextField';

export function CreateOrderForm() {
  const t = useTranslations();
  const formRef = useRef<HTMLFormElement>(null);
  const [state, formAction, isPending] = useActionState(createOrder, null);
  const form = useForm<CreateOrderInput>({
    resolver: zodResolver(CreateOrderSchema),
    defaultValues: { customerName: '', email: '' },
  });
  const serverErrors = state?.ok === false ? state.fieldErrors : undefined;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isPending) return; // aria-disabled does not stop a submit
    void form.handleSubmit(() => {
      startTransition(() => formAction(new FormData(formRef.current!))); // the same action, schema already passed
    })(event);
  }

  return (
    <form ref={formRef} action={formAction} onSubmit={onSubmit} noValidate className="space-y-6">
      <FieldGroup>
        <TextField control={form.control} name="customerName" serverErrors={serverErrors} />
        <TextField control={form.control} name="email" type="email" serverErrors={serverErrors} />
      </FieldGroup>
      {state?.ok === false && state.formErrors?.[0] && (
        <p role="alert" className="text-sm text-error">{t(state.formErrors[0])}</p>
      )}
      <Button type="submit" aria-disabled={isPending}>{t('orders.create')}</Button>
    </form>
  );
}
```

```tsx
// src/components/organisms/CreateOrderForm/TextField.tsx
'use client';

import { Controller, type Control } from 'react-hook-form';
import { useTranslations } from 'next-intl';
import { Field, FieldError, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import type { CreateOrderInput } from '@/schemas/order';

interface TextFieldProps {
  control: Control<CreateOrderInput>;
  name: keyof CreateOrderInput;
  type?: 'text' | 'email';
  serverErrors?: Record<string, string[]>;
}

export function TextField({ control, name, type = 'text', serverErrors }: TextFieldProps) {
  const t = useTranslations();
  return (
    <Controller
      name={name}
      control={control}
      render={({ field, fieldState }) => {
        const keys = [fieldState.error?.message, ...(serverErrors?.[name] ?? [])].filter(
          (key): key is string => Boolean(key),
        );
        return (
          <Field data-invalid={keys.length > 0}>
            <FieldLabel htmlFor={name}>{t(`orders.fields.${name}`)}</FieldLabel>
            <Input {...field} id={name} type={type} aria-invalid={keys.length > 0} />
            <FieldError errors={keys.map((key) => ({ message: t(key) }))} />
          </Field>
        );
      }}
    />
  );
}
```

- **`{...field}` carries `name`**, which is what puts each value into the `FormData` the action
  receives — with or without JavaScript.
- **`startTransition` is not optional.** Calling a `useActionState` action outside a transition
  makes React warn, and `isPending` never flips.
- **`FieldError` renders `role="alert"` and dedupes its array**, so a key the client and the server
  both report shows once.
- The Field API, `FieldSet` / `FieldLegend` for grouped controls, and what `notify()` does after a
  successful submit → `@skills/std-shadcn-ui/references/forms-and-feedback.md`.

---

## Chart on a Page (shadcn chart + Recharts)

The Next.js chart standard lives in one place, with the full code:
`@skills/std-shadcn-ui/references/charts.md`. The page reads the range from `searchParams`; a
Server Component panel fetches and renders the loading, empty and error paths and the figure's
caption, summary and data table; a `'use client'` leaf composes Recharts inside `ChartContainer`.
Build from it, not from a chart block. What a feature adds on top:

- **Where the page sits.** A report is a level inside an area
  (`app/(app)/(reports)/reports/revenue/page.tsx`): its range is list state in the URL, and it has
  its own `h1` and `generateMetadata` title → `@skills/std-nextjs/references/navigation.md`.
- **Two or more series** get `ChartLegend` with `ChartLegendContent`, and the second series a
  `strokeDasharray`, so the chart survives a colour-vision deficiency and a greyscale print.
- **`ChartContainer` carries a size from the scale** (`aspect-video`, `min-h-72`), never an
  arbitrary `min-h-[…]`.
- **Every series takes `isAnimationActive={!reduceMotion}`**, from Framer Motion's
  `useReducedMotion()` — never a bare prop, never `true`.
- **Only plain data crosses into the leaf** — points and a currency code. Formatters are built in the
  leaf with `useFormatter()`; a function prop from a Server Component fails serialization.
- **Chart blocks (`chart-area-*`, `chart-bar-*`, …) exist only for the Radix styles.** A Base UI
  package composes from `chart`.

---

## Client Component with TanStack Query (Real-Time Data)

```tsx
// next/src/components/LiveOrderTracker.tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/api/client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { Order } from '@/domain/order';

interface LiveOrderTrackerProps {
  orderId: string;
  initialData: Order;
}

export function LiveOrderTracker({ orderId, initialData }: LiveOrderTrackerProps) {
  const t = useTranslations('orders');
  const { data: order } = useQuery({
    queryKey: ['orders', orderId],
    queryFn: () => apiClient.get<Order>(`/api/v1/orders/${orderId}`),
    initialData,
    refetchInterval: 10_000, // Poll every 10 seconds
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('title', { id: order.id })}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        {t(`status.${order.status}`)}
      </CardContent>
    </Card>
  );
}
```
