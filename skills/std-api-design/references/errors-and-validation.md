# Shaping Errors and Validating Input

Load-bearing rules restated (these hold even if you read nothing else):

- **Every** error response uses the same envelope: `error`, `code`, `status`, optional `details`, `requestId`.
- `code` is machine-readable and stable. Clients branch on `code`, never on `error` text.
- Never leak stack traces, internal paths, SQL, or class names in production error bodies.
- Validate at the API boundary (controller / route handler / server action), never deep in business logic.
- Return **all** validation errors at once, not the first one.
- Strip unknown fields from validated input before passing it downstream.

The canonical error body:

```json
{
  "error": "Human-readable error message",
  "code": "VALIDATION_ERROR",
  "status": 422,
  "details": [
    { "field": "email", "message": "Must be a valid email address" }
  ],
  "requestId": "req-abc-123"
}
```

Status codes: `400` malformed syntax · `401` not authenticated · `403` authenticated but not
permitted · `404` not found · `409` duplicate / state conflict · `422` validation failure ·
`429` rate limited · `500` unexpected failure.

---

## Decision: how do I render an error from a Rails controller?

Do not hand-roll error JSON per action. One concern, rescued centrally.

### Bad — inconsistent shape, leaked internals, one error at a time

```ruby
class Api::V1::OrdersController < ApplicationController
  def create
    order = Order.new(order_params)
    if order.save
      render json: order
    else
      # Bare array — no code, no requestId, shape differs from every other endpoint.
      render json: { errors: order.errors.full_messages.first }, status: :bad_request
    end
  rescue ActiveRecord::RecordNotFound => e
    # Leaks the model name and the internal message to the client.
    render json: { message: e.message, backtrace: e.backtrace }, status: 500
  end
end
```

### Good — a single rendering concern, machine-readable codes, all errors at once

```ruby
# app/controllers/concerns/api_error_handling.rb
module ApiErrorHandling
  extend ActiveSupport::Concern

  included do
    rescue_from ActiveRecord::RecordNotFound,       with: :render_not_found
    rescue_from ActiveRecord::RecordInvalid,        with: :render_unprocessable
    rescue_from ActionController::ParameterMissing, with: :render_bad_request
    rescue_from Pundit::NotAuthorizedError,         with: :render_forbidden
    rescue_from ActiveRecord::RecordNotUnique,      with: :render_conflict
  end

  private

  def render_api_error(message:, code:, status:, details: nil)
    body = {
      error: message,
      code: code,
      status: Rack::Utils.status_code(status),
      requestId: request.request_id
    }
    body[:details] = details if details.present?
    render json: body, status: status
  end

  def render_not_found(_error)
    render_api_error(message: "Resource not found", code: "NOT_FOUND", status: :not_found)
  end

  def render_unprocessable(error)
    details = error.record.errors.map do |err|
      { field: err.attribute.to_s.camelize(:lower), message: err.message }
    end
    render_api_error(
      message: "Validation failed",
      code: "VALIDATION_ERROR",
      status: :unprocessable_entity,
      details: details
    )
  end

  def render_bad_request(error)
    render_api_error(message: "Missing parameter: #{error.param}",
                     code: "BAD_REQUEST", status: :bad_request)
  end

  def render_forbidden(_error)
    render_api_error(message: "You are not allowed to perform this action",
                     code: "FORBIDDEN", status: :forbidden)
  end

  def render_conflict(_error)
    render_api_error(message: "Resource already exists",
                     code: "CONFLICT", status: :conflict)
  end
end
```

```ruby
class Api::V1::OrdersController < ApplicationController
  include ApiErrorHandling

  def create
    order = Orders::Create.new(user: current_user, params: order_params).call!
    render json: OrderSerializer.new(order).to_json, status: :created,
           location: api_v1_order_url(order)
  end

  private

  def order_params
    params.require(:order).permit(:product_id, :quantity,
                                  shipping_address: %i[street city zip_code country])
  end
end
```

`create!` / `call!` raises `RecordInvalid`; the concern turns it into the canonical 422 with every
field error at once. No `rescue` in the action.

---

## Decision: the 500 handler — what does the client see?

### Bad — the exception message becomes the API contract

```ruby
rescue_from StandardError do |e|
  render json: { error: e.message }, status: 500
end
# => {"error":"PG::UndefinedColumn: ERROR: column orders.totl does not exist"}
```

### Good — opaque to the client, complete for the operator

```ruby
rescue_from StandardError, with: :render_internal_error

def render_internal_error(error)
  Sentry.capture_exception(error, extra: { request_id: request.request_id })
  Rails.logger.error(
    message: "unhandled_exception",
    request_id: request.request_id,
    error_class: error.class.name,
    error_message: error.message
  )
  render_api_error(
    message: "An unexpected error occurred. Contact support with this request ID.",
    code: "INTERNAL_ERROR",
    status: :internal_server_error
  )
end
```

The `requestId` in the body is the bridge: the client quotes it, the operator greps for it.

---

## Decision: where do I validate a TypeScript request body?

Validate at the boundary with Zod, return every issue, and never forward the raw body.

### Bad — hand-rolled checks, first error wins, extra keys forwarded

```typescript
// app/api/orders/route.ts
export async function POST(req: Request) {
  const body = await req.json();
  if (!body.productId) {
    return Response.json({ error: 'productId required' }, { status: 400 });
  }
  if (!body.quantity || body.quantity < 1) {
    return Response.json({ error: 'bad quantity' }, { status: 400 });
  }
  // `body` may carry isAdmin, price, whatever the caller invented.
  const order = await createOrder(body);
  return Response.json(order);
}
```

Three defects: the shape differs from the rest of the API, the caller fixes one field per
round-trip, and unknown keys reach the domain layer.

### Good — one schema, all issues, stripped output

```typescript
// src/api/schemas/order.ts
import { z } from 'zod';

export const CreateOrderSchema = z
  .object({
    productId: z.string().uuid(),
    quantity: z.number().int().min(1).max(100),
    shippingAddress: z.object({
      street: z.string().min(1).max(200),
      city: z.string().min(1).max(100),
      zipCode: z.string().regex(/^\d{5}(-\d{4})?$/),
      country: z.string().length(2),
    }),
  })
  .strict(); // unknown keys are an error, not silently carried

export type CreateOrderInput = z.infer<typeof CreateOrderSchema>;
```

```typescript
// src/api/http/errors.ts
import { ZodError } from 'zod';

export type ApiError = {
  error: string;
  code: string;
  status: number;
  details?: Array<{ field: string; message: string }>;
  requestId: string;
};

export function validationErrorBody(err: ZodError, requestId: string): ApiError {
  return {
    error: 'Validation failed',
    code: 'VALIDATION_ERROR',
    status: 422,
    details: err.issues.map((issue) => ({
      field: issue.path.join('.'),
      message: issue.message,
    })),
    requestId,
  };
}
```

```typescript
// app/api/orders/route.ts
import { randomUUID } from 'node:crypto';
import { CreateOrderSchema } from '@/src/api/schemas/order';
import { validationErrorBody } from '@/src/api/http/errors';

export async function POST(req: Request) {
  const requestId = req.headers.get('x-request-id') ?? randomUUID();
  const parsed = CreateOrderSchema.safeParse(await req.json());

  if (!parsed.success) {
    return Response.json(validationErrorBody(parsed.error, requestId), { status: 422 });
  }

  // parsed.data is typed AND stripped — only declared keys survive.
  const order = await createOrder(parsed.data);
  return Response.json({ data: order }, {
    status: 201,
    headers: { Location: `/v1/orders/${order.id}` },
  });
}
```

---

## Decision: how does a Next.js server action report validation failure?

Server actions cannot set a status code — they return a value. Keep the same `code` vocabulary
so client handling stays uniform.

### Bad — throwing raw errors across the RSC boundary

```typescript
'use server';
export async function createOrder(formData: FormData) {
  const quantity = Number(formData.get('quantity'));
  if (quantity < 1) throw new Error('quantity must be >= 1'); // becomes a digest, unusable in UI
  await api.post('/v1/orders', { quantity });
}
```

In production React replaces the message with an opaque digest — the user sees a generic error
boundary and the field never gets highlighted.

### Good — a discriminated result the form can render field-by-field

```typescript
'use server';

import { CreateOrderSchema } from '@/src/api/schemas/order';

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; code: string; error: string; details?: Array<{ field: string; message: string }> };

export async function createOrder(formData: FormData): Promise<ActionResult<{ id: string }>> {
  const parsed = CreateOrderSchema.safeParse({
    productId: formData.get('productId'),
    quantity: Number(formData.get('quantity')),
    shippingAddress: JSON.parse(String(formData.get('shippingAddress') ?? '{}')),
  });

  if (!parsed.success) {
    return {
      ok: false,
      code: 'VALIDATION_ERROR',
      error: 'Validation failed',
      details: parsed.error.issues.map((i) => ({
        field: i.path.join('.'),
        message: i.message,
      })),
    };
  }

  const order = await createOrderOnBackend(parsed.data);
  return { ok: true, data: { id: order.id } };
}
```

---

## Decision: how does the client consume these errors?

Branch on `code`, surface `requestId`, map `details` onto form fields.

### Bad — string-matching the human message

```typescript
if (err.response?.data?.error?.includes('email')) {
  setEmailError('bad email'); // breaks the moment copy is reworded or translated
}
```

### Good — one typed interceptor, code-driven handling

```typescript
// src/api/client.ts
import axios, { AxiosError } from 'axios';

export class ApiError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
    message: string,
    readonly details: Array<{ field: string; message: string }> = [],
    readonly requestId?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  fieldErrors(): Record<string, string> {
    return Object.fromEntries(this.details.map((d) => [d.field, d.message]));
  }
}

export const apiClient = axios.create({ baseURL: '/v1' });

apiClient.interceptors.response.use(
  (res) => res,
  (err: AxiosError<{ error?: string; code?: string; status?: number; details?: []; requestId?: string }>) => {
    const body = err.response?.data;
    throw new ApiError(
      body?.code ?? 'NETWORK_ERROR',
      err.response?.status ?? 0,
      body?.error ?? 'Request failed',
      body?.details ?? [],
      body?.requestId,
    );
  },
);
```

```typescript
// Consuming it in a react-hook-form + TanStack Query mutation.
const mutation = useMutation({
  mutationFn: (input: CreateOrderInput) => apiClient.post('/orders', input),
  onError: (err) => {
    if (err instanceof ApiError && err.code === 'VALIDATION_ERROR') {
      for (const [field, message] of Object.entries(err.fieldErrors())) {
        setError(field as keyof CreateOrderInput, { message });
      }
      return;
    }
    if (err instanceof ApiError && err.code === 'FORBIDDEN') {
      toast.error('You do not have access to this order.');
      return;
    }
    toast.error(`Something went wrong. Reference: ${(err as ApiError).requestId ?? 'n/a'}`);
  },
});
```

---

## Testing the error contract (Vitest + MSW)

```typescript
// src/api/client.test.ts
import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { apiClient, ApiError } from './client';

const server = setupServer(
  http.post('/v1/orders', () =>
    HttpResponse.json(
      {
        error: 'Validation failed',
        code: 'VALIDATION_ERROR',
        status: 422,
        details: [{ field: 'quantity', message: 'Must be at least 1' }],
        requestId: 'req-abc-123',
      },
      { status: 422 },
    ),
  ),
);

beforeAll(() => server.listen());
afterAll(() => server.close());

it('should expose field errors when the API returns VALIDATION_ERROR', async () => {
  // Arrange / Act
  const err = await apiClient.post('/orders', {}).catch((e) => e);

  // Assert
  expect(err).toBeInstanceOf(ApiError);
  expect(err.code).toBe('VALIDATION_ERROR');
  expect(err.fieldErrors()).toEqual({ quantity: 'Must be at least 1' });
  expect(err.requestId).toBe('req-abc-123');
});
```

Rails request spec asserting the same contract:

```ruby
# spec/requests/api/v1/orders_spec.rb
it "should return the canonical error envelope when validation fails" do
  post "/v1/orders", params: { order: { quantity: 0 } }, headers: auth_headers

  expect(response).to have_http_status(:unprocessable_entity)
  body = response.parsed_body
  expect(body["code"]).to eq("VALIDATION_ERROR")
  expect(body["status"]).to eq(422)
  expect(body["requestId"]).to be_present
  expect(body["details"]).to include(hash_including("field" => "quantity"))
  expect(body.keys).not_to include("backtrace")
end
```
