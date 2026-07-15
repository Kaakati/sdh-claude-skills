# Server actions: writing mutations

Load-bearing rules restated (this file is read standalone):

- **A server action is a public HTTP endpoint.** The `'use server'` directive creates a callable
  POST route. Anyone can invoke it with any payload. Validate and authorize *inside* the action.
- **Always validate input with zod.**
- **Always `revalidatePath` / `revalidateTag` after a successful mutation**, or the UI shows stale
  cached data.
- **Return serializable data only** — plain objects, arrays, primitives. No class instances,
  no `Error` objects, no functions, no `Date`-bearing domain models with methods.
- **Never return a raw error.** Catch, log server-side, return a user-safe message.

Server actions live in `src/actions/` and are the use-case layer: they validate, authorize, call
the Rails API client, revalidate, and return a result shape. They contain no business rules of
their own — those live in Rails.

---

## Decision: what does an action return?

Use one discriminated result shape across the whole app so forms can be written mechanically.

```ts
// src/actions/result.ts
export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; formErrors?: string[]; fieldErrors?: Record<string, string[]> };
```

---

## Decision: validating and authorizing an action

### Bad — trusts the client

```ts
'use server';

import { railsServer } from '@/api/rails-server';

export async function createOrder(formData: FormData) {
  // No auth check: any unauthenticated caller can POST to this endpoint.
  // No validation: quantity could be "-5" or an object.
  // userId comes from the form: trivially forged.
  return railsServer.post('/api/v1/orders', {
    userId: formData.get('userId'),
    productId: formData.get('productId'),
    quantity: formData.get('quantity'),
  });
}
```

Three defects: no authentication, no validation, and identity taken from user-controlled input.
It also returns an axios response — not serializable, and it leaks response headers.

### Good

```ts
// src/actions/orders.ts
'use server';

import { revalidateTag } from 'next/cache';
import { z } from 'zod';
import { requireSession } from '@/lib/auth';
import { railsServer } from '@/api/rails-server';
import type { ActionResult } from './result';
import type { Order } from '@/types/order';

const CreateOrderSchema = z.object({
  productId: z.string().uuid(),
  quantity: z.coerce.number().int().positive().max(100),
  paymentMethod: z.enum(['card', 'invoice']),
});

export async function createOrder(
  _prev: ActionResult<Order> | null,
  formData: FormData,
): Promise<ActionResult<Order>> {
  const session = await requireSession(); // throws/redirects if not signed in

  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) {
    const { formErrors, fieldErrors } = parsed.error.flatten();
    return { ok: false, formErrors, fieldErrors };
  }

  try {
    const response = await railsServer.post<{ data: Order }>('/api/v1/orders', parsed.data, {
      headers: { Authorization: `Bearer ${session.token}` }, // identity from the session, not the form
    });

    revalidateTag('orders');
    return { ok: true, data: response.data.data };
  } catch (error) {
    console.error('createOrder failed', { userId: session.userId, error });
    return { ok: false, formErrors: ['Could not create the order. Please try again.'] };
  }
}
```

`z.coerce.number()` matters: every `FormData` value is a string, so a plain `z.number()` rejects
valid input.

---

## Decision: wiring the action into a form

Use `useActionState` + `useFormStatus`. The form works without JavaScript because the `action`
attribute posts to the server directly.

### Bad — client-side fetch defeats progressive enhancement

```tsx
'use client';

export function NewOrderForm() {
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); // form is dead without JS
    setLoading(true);
    await fetch('/api/orders', { method: 'POST', body: new FormData(e.currentTarget) });
    setLoading(false);
    router.refresh(); // manual, and refetches the whole route
  }

  return <form onSubmit={handleSubmit}>{/* ... */}</form>;
}
```

### Good

```tsx
// src/components/orders/NewOrderForm.tsx
'use client';

import { useActionState } from 'react';
import { useFormStatus } from 'react-dom';
import { createOrder } from '@/actions/orders';

function SubmitButton() {
  const { pending } = useFormStatus(); // must be a child of <form>
  return (
    <button type="submit" disabled={pending} className="rounded bg-primary px-4 py-2">
      {pending ? 'Creating…' : 'Create order'}
    </button>
  );
}

export function NewOrderForm({ productId }: { productId: string }) {
  const [state, formAction] = useActionState(createOrder, null);

  return (
    <form action={formAction} className="space-y-4">
      <input type="hidden" name="productId" value={productId} />

      <label htmlFor="quantity">Quantity</label>
      <input id="quantity" name="quantity" type="number" defaultValue={1} required />
      {state?.ok === false && state.fieldErrors?.quantity && (
        <p role="alert" className="text-sm text-destructive">
          {state.fieldErrors.quantity[0]}
        </p>
      )}

      <select name="paymentMethod" defaultValue="card" aria-label="Payment method">
        <option value="card">Card</option>
        <option value="invoice">Invoice</option>
      </select>

      {state?.ok === false && state.formErrors?.length ? (
        <p role="alert" className="text-sm text-destructive">{state.formErrors[0]}</p>
      ) : null}

      <SubmitButton />
    </form>
  );
}
```

`useFormStatus` reads the status of the **nearest parent form**, so it only works in a child
component — calling it inside `NewOrderForm` itself always returns `pending: false`.

---

## Decision: react-hook-form + zod, or plain `useActionState`?

- Plain `useActionState` — the default. Progressive enhancement for free.
- `react-hook-form` + `zodResolver` — when the form needs live per-field validation, dependent
  fields, or a field array. Share the zod schema with the action so client and server agree.

```ts
// src/domain/orders/schema.ts — one schema, imported by both sides
import { z } from 'zod';

export const CreateOrderSchema = z.object({
  productId: z.string().uuid(),
  quantity: z.coerce.number().int().positive().max(100),
  paymentMethod: z.enum(['card', 'invoice']),
});

export type CreateOrderInput = z.infer<typeof CreateOrderSchema>;
```

The action still re-validates. Client validation is UX; server validation is the control.

---

## Decision: optimistic UI

```tsx
'use client';

import { useOptimistic, startTransition } from 'react';
import { toggleFavorite } from '@/actions/favorites';
import type { Order } from '@/types/order';

export function FavoriteButton({ order }: { order: Order }) {
  const [optimisticFav, setOptimisticFav] = useOptimistic(order.favorited);

  return (
    <button
      aria-pressed={optimisticFav}
      onClick={() => {
        startTransition(async () => {
          setOptimisticFav(!optimisticFav); // reverts automatically if the action throws
          await toggleFavorite(order.id);
        });
      }}
    >
      {optimisticFav ? '★' : '☆'}
    </button>
  );
}
```

`useOptimistic` reverts when the surrounding transition settles with fresh server state, so the
action **must** `revalidateTag`/`revalidatePath` — otherwise the optimistic value snaps back to
the stale cached value.

---

## Decision: redirect after a mutation

`redirect()` works by throwing a special error. Never call it inside a `try` block that catches
everything, and call it *after* the `try/catch`.

### Bad — the redirect is swallowed and reported as a failure

```ts
try {
  const order = await railsServer.post('/api/v1/orders', parsed.data);
  redirect(`/orders/${order.data.data.id}`); // throws NEXT_REDIRECT…
} catch (error) {
  return { ok: false, formErrors: ['Could not create the order.'] }; // …caught here
}
```

### Good

```ts
let orderId: string;
try {
  const response = await railsServer.post<{ data: Order }>('/api/v1/orders', parsed.data);
  orderId = response.data.data.id;
} catch (error) {
  console.error('createOrder failed', error);
  return { ok: false, formErrors: ['Could not create the order. Please try again.'] };
}

revalidateTag('orders');
redirect(`/orders/${orderId}`); // outside the try — nothing catches it
```

---

## Decision: server action vs Route Handler

| Need | Use |
|------|-----|
| Form submission / mutation from your own UI | Server action |
| Webhook receiver (Stripe, Centrifugo, GitHub) | Route Handler (`app/api/*/route.ts`) |
| Health check / readiness probe | Route Handler |
| Endpoint consumed by a third party or the React Native app | **Rails**, not Next.js |
| Reading data for a page | Server Component `await`, not either |

Route Handlers in this stack are BFF-only. Do not rebuild the Rails API inside `app/api`.

---

## Testing server actions (Vitest)

```ts
// tests/actions/orders.test.ts
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createOrder } from '@/actions/orders';

vi.mock('next/cache', () => ({ revalidateTag: vi.fn() }));
vi.mock('@/lib/auth', () => ({
  requireSession: vi.fn().mockResolvedValue({ userId: 'u1', token: 't' }),
}));
vi.mock('@/api/rails-server', () => ({ railsServer: { post: vi.fn() } }));

import { revalidateTag } from 'next/cache';
import { railsServer } from '@/api/rails-server';

function form(fields: Record<string, string>) {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  return fd;
}

describe('createOrder', () => {
  beforeEach(() => vi.clearAllMocks());

  it('should return field errors when quantity is not positive', async () => {
    const result = await createOrder(null, form({
      productId: '3f2a1c9e-0000-4000-8000-000000000000',
      quantity: '-1',
      paymentMethod: 'card',
    }));

    expect(result.ok).toBe(false);
    expect(railsServer.post).not.toHaveBeenCalled();
  });

  it('should revalidate the orders tag when the mutation succeeds', async () => {
    vi.mocked(railsServer.post).mockResolvedValue({ data: { data: { id: 'o1' } } } as never);

    const result = await createOrder(null, form({
      productId: '3f2a1c9e-0000-4000-8000-000000000000',
      quantity: '2',
      paymentMethod: 'card',
    }));

    expect(result).toEqual({ ok: true, data: { id: 'o1' } });
    expect(revalidateTag).toHaveBeenCalledWith('orders');
  });
});
```
