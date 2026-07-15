# Forms (react-hook-form + zod)

Load-bearing rules restated (hold even if you read nothing else):

1. **Every form is `react-hook-form` + `zod`.** No Formik, no hand-rolled `useState` forms, no
   uncontrolled forms.
2. **The zod schema is the single source of truth** — infer the TypeScript type from it with
   `z.infer`, never declare both.
3. **Components never call axios directly.** A form submits through a TanStack Query
   `useMutation` hook, never `api.post` inline.
4. **Validation errors are programmatically associated** with their field via `aria-describedby`,
   and the submit button is disabled while `isSubmitting`.

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

### Good — schema first, type inferred, mutation wired

```ts
// src/domain/order-schema.ts  ✅ one source of truth
import { z } from 'zod';

export const createOrderSchema = z.object({
  reference: z.string().min(1, 'Reference is required').max(32),
  quantity: z.coerce.number().int().positive('Quantity must be at least 1'),
  notes: z.string().max(500).optional(),
});

export type CreateOrderInput = z.infer<typeof createOrderSchema>;
```

```tsx
// src/components/forms/CreateOrderForm.tsx  ✅
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { createOrderSchema, type CreateOrderInput } from '@/domain/order-schema';
import { useCreateOrder } from '@/api/orders';
import { cn } from '@/lib/cn';

export function CreateOrderForm({ onCreated }: { onCreated: (id: string) => void }) {
  const createOrder = useCreateOrder();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<CreateOrderInput>({
    resolver: zodResolver(createOrderSchema),
    defaultValues: { reference: '', quantity: 1 },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      const order = await createOrder.mutateAsync(values);
      onCreated(order.id);
    } catch (error) {
      // Map the Rails API's field errors back onto the form.
      if (isAxiosError(error) && error.response?.status === 422) {
        const fieldErrors = error.response.data.errors as Record<string, string[]>;
        for (const [field, messages] of Object.entries(fieldErrors)) {
          setError(field as keyof CreateOrderInput, { message: messages[0] });
        }
        return;
      }
      setError('root', { message: 'Something went wrong. Please try again.' });
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      <div>
        <label htmlFor="reference" className="block text-sm font-medium">
          Reference
        </label>
        <input
          id="reference"
          {...register('reference')}
          aria-invalid={!!errors.reference}
          aria-describedby={errors.reference ? 'reference-error' : undefined}
          className={cn(
            'mt-1 w-full rounded border px-3 py-2',
            errors.reference ? 'border-red-500' : 'border-slate-300 dark:border-slate-700',
          )}
        />
        {errors.reference && (
          <p id="reference-error" role="alert" className="mt-1 text-sm text-red-600">
            {errors.reference.message}
          </p>
        )}
      </div>

      {errors.root && (
        <p role="alert" className="text-sm text-red-600">{errors.root.message}</p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {isSubmitting ? 'Creating…' : 'Create order'}
      </button>
    </form>
  );
}
```

Details that matter and are routinely missed:
- `htmlFor` / `id` pairing — without it `getByLabelText` fails **and** so does every screen reader.
- `aria-invalid` + `aria-describedby` — the error text must be programmatically associated.
- `role="alert"` on the error — announces on appearance.
- `noValidate` — you own validation; the browser's native bubbles fight zod's messages.
- `disabled={isSubmitting}` — the only thing standing between you and duplicate orders.
- `z.coerce.number()` — an `<input>` always yields a string; coerce at the schema boundary.

---

## Decision: mapping API errors back onto the form

The Rails API returns `422` with `{ errors: { field: ["message"] } }`. Two failure modes to avoid:

- Swallowing the error and leaving the user staring at a form that "did nothing".
- Dumping a generic toast when the server told you exactly which field is wrong.

The `onSubmit` above shows the pattern. The rules behind it:

- **Field-level errors** (`422` with an `errors` object) → `setError(field, { message })` so the
  message lands under the offending input, associated by `aria-describedby`.
- **Everything else** (500, network failure, timeout) → `setError('root', …)` and render
  `errors.root` as a `role="alert"` above the submit button.
- Take `messages[0]` — the API may return several per field; show the first, don't concatenate.
- Never re-run zod against the server response. zod validates *input*; the server owns rules zod
  cannot know (uniqueness, authorization, stock levels).

For testing this mapping end-to-end with MSW, see `references/testing.md`.
