# Forms (react-hook-form + zod, rendered with shadcn/ui Field)

Load-bearing rules restated (hold even if you read nothing else):

1. **Every form is `react-hook-form` + `zod`, rendered with shadcn/ui's `Field` family**
   (`Field`, `FieldLabel`, `FieldError`, `FieldGroup`) through RHF's `Controller`. No Formik, no
   hand-rolled `useState` forms, and never `npx shadcn add form` — that item is the legacy
   wrapper, with no docs page.
2. **The zod schema is the single source of truth** — infer the TypeScript type from it with
   `z.infer`, never declare both. Its messages are translation keys.
3. **Components never call axios directly.** A form submits through a TanStack Query
   `useMutation` hook, never `api.post` inline.
4. **Errors are programmatically associated with their field** — `aria-invalid` on the control,
   `aria-describedby` pointing at the `FieldError` — and the submit button is disabled while
   `isSubmitting`.
5. **Never a toast for a field error, and never a toast as the only place a blocking error
   appears.** Toasts and the house `notify()` helper →
   `@skills/std-shadcn-ui/references/forms-and-feedback.md`.

---

## Decision: building a form

### Bad — useState soup, duplicated types, manual validation

```tsx
// ❌
export function CreateOrderForm() {
  const [reference, setReference] = useState('');
  const [quantity, setQuantity] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const next: Record<string, string> = {};
    if (!reference) next.reference = 'Required';                    // ❌ validation drifts from the API
    if (Number(quantity) < 1) next.quantity = 'Must be positive';
    setErrors(next);
    if (Object.keys(next).length) return;
    await api.post('/orders', { reference, quantity: Number(quantity) });  // ❌ raw axios, no isPending
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={reference} onChange={(e) => setReference(e.target.value)} />  {/* ❌ no label */}
      {errors.reference && <span>{errors.reference}</span>}
      <button type="submit">Create</button>                          {/* ❌ double-submittable */}
    </form>
  );
}
```

### Good — schema first, `Field` components, mutation wired

```ts
// src/domain/order-schema.ts  ✅ one source of truth; messages are translation keys
import { z } from 'zod';

export const createOrderSchema = z.object({
  reference: z.string().min(1, 'orders.form.referenceRequired').max(32, 'orders.form.referenceTooLong'),
  quantity: z.coerce.number().int().positive('orders.form.quantityPositive'),
  notes: z.string().max(500, 'orders.form.notesTooLong').optional(),
});

export type CreateOrderInput = z.infer<typeof createOrderSchema>;
```

```tsx
// src/components/organisms/CreateOrderForm/CreateOrderForm.tsx  ✅
import { Controller, useForm, type Control, type UseFormReturn } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { ApiError } from '@/api/client';
import { useCreateOrder } from '@/api/orders';
import { createOrderSchema, type CreateOrderInput } from '@/domain/order-schema';
import { errorText } from '@/lib/form-errors';

type OrderForm = UseFormReturn<CreateOrderInput>;

function applyServerErrors(form: OrderForm, error: unknown, t: TFunction) {
  if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
    for (const [field, message] of Object.entries(error.fieldErrors())) {
      form.setError(field as keyof CreateOrderInput, { type: 'server', message });
    }
    return;
  }
  const requestId = error instanceof ApiError ? error.requestId : undefined;
  form.setError('root', { type: 'server', message: t('errors.generic', { requestId }) });
}

function ReferenceField({ control }: { control: Control<CreateOrderInput> }) {
  const { t } = useTranslation();
  return (
    <Controller
      name="reference"
      control={control}
      render={({ field, fieldState }) => (
        <Field data-invalid={fieldState.invalid}>
          <FieldLabel htmlFor="reference">{t('orders.form.reference')}</FieldLabel>
          <Input
            {...field}
            id="reference"
            aria-invalid={fieldState.invalid}
            aria-describedby={fieldState.invalid ? 'reference-error' : undefined}
          />
          {fieldState.invalid && <FieldError id="reference-error">{errorText(t, fieldState.error)}</FieldError>}
        </Field>
      )}
    />
  );
}

export function CreateOrderForm({ onCreated }: { onCreated: (id: string) => void }) {
  const { t } = useTranslation();
  const createOrder = useCreateOrder();
  const form = useForm<CreateOrderInput>({
    resolver: zodResolver(createOrderSchema),
    defaultValues: { reference: '', quantity: 1 },
  });

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const order = await createOrder.mutateAsync(values);
      onCreated(order.id);
    } catch (error) {
      applyServerErrors(form, error, t);
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate>
      <FieldGroup>
        <ReferenceField control={form.control} />
        {form.formState.errors.root && <FieldError>{form.formState.errors.root.message}</FieldError>}
        <Button type="submit" disabled={form.formState.isSubmitting}>
          {t(form.formState.isSubmitting ? 'orders.form.creating' : 'orders.form.create')}
        </Button>
      </FieldGroup>
    </form>
  );
}
```

A form with several text inputs uses the house `TextField` molecule instead of repeating
`ReferenceField`; it and `errorText` (`@/lib/form-errors`) are defined in
`@skills/std-shadcn-ui/references/forms-and-feedback.md`.

Details that matter and are routinely missed:
- `htmlFor` / `id` pairing on `FieldLabel` and `Input` — `FieldLabel` does not wire it for you, and
  without it `getByLabelText` fails **and** so does every screen reader.
- `data-invalid` on `Field` and `aria-invalid` on the control — the pair shadcn's React Hook Form
  guide wires. The first is a styling hook for the field's parts; the second is what assistive
  technology reads.
- `aria-describedby` → the `FieldError` `id`. shadcn's guide stops at `aria-invalid`; `FieldError`
  renders `role="alert"` and spreads its props, so the `id` goes straight on it. `role="alert"`
  announces the error once; `aria-describedby` ties it to the field for every later visit.
- `errorText` translates client messages, which are keys, and shows server messages as sent —
  Rails localizes them from `Accept-Language`, and running a sentence through `t()` looks it up as
  a key.
- `noValidate` — you own validation; the browser's native bubbles fight zod's messages.
- `disabled={isSubmitting}` — the only thing standing between you and duplicate orders.
- `z.coerce.number()` — an `<input>` always yields a string; coerce at the schema boundary.
- Selects, checkboxes, radio groups and switches wire `field.onChange` through the control's own
  change prop (`onValueChange`, `onCheckedChange`) →
  `@skills/std-shadcn-ui/references/forms-and-feedback.md`.

---

## Decision: mapping API errors back onto the form

The error envelope is owned by `std-api-design`: a validation failure carries
`code: "VALIDATION_ERROR"` and a `details` array of `{ field, message }`, and the shared axios
interceptor turns every error response into an `ApiError` whose `fieldErrors()` flattens that
array → `@skills/std-api-design/references/errors-typescript.md`. Read the contract there; this
file only consumes it.

Two failure modes to avoid:

- Swallowing the error and leaving the user staring at a form that "did nothing".
- Dumping a generic toast when the server told you exactly which field is wrong.

`applyServerErrors` above shows the pattern. The rules behind it:

- **Branch on `code`, never on message text** — copy gets reworded and translated.
- **`VALIDATION_ERROR`** → `setError(field, { type: 'server', message })` for each entry of
  `fieldErrors()`, so the message lands under the offending input, associated by
  `aria-describedby`.
- **Everything else** (other codes, network failure, timeout) → `setError('root', …)`, rendered as
  a `FieldError` above the submit button, carrying `requestId` so support can find the request. A
  `notify()` error toast may add to it; it never replaces it — the failure has to appear where it
  happened.
- `type: 'server'` marks text the API already wrote; client messages are keys and go through `t()`.
- Never re-run zod against the server response. zod validates *input*; the server owns rules zod
  cannot know (uniqueness, authorization, stock levels).

For testing this mapping end-to-end with MSW, see `references/testing.md`.
