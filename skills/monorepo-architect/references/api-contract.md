# The API Contract — one Rails API, three TypeScript consumers

Load-bearing rules restated (hold even if you read nothing else):

1. **The Rails API schema is the source of truth.** Types are *generated* from it, never
   hand-written twice.
2. **Being in one repo does not replace an API contract.** Internal packages still need stable
   interfaces and tests at the boundary.
3. **Drift must become a compile error**, not a production bug.

---

## Why this is the highest-value move for this stack

The shape — one Rails API, consumed by Next.js, a Vite SPA, and React Native — has one dominant
failure: **the consumers drift from the API and from each other.** A field is renamed in Rails;
web is updated because someone noticed; mobile ships the old name and 500s in the field, weeks
later, on a release you cannot hot-fix.

A monorepo makes this *fixable* and does not fix it. Co-location gives you the ability to
change both sides atomically; only a generated contract gives you the *obligation*. Hand-written
types in `packages/types` are a second source of truth — they drift exactly like a separate repo
would, but with a comforting sense that they can't.

> **Treating the monorepo as an excuse to skip API contracts is a top failure mode.** One repo
> is not one program.

## The pipeline

```
apps/rails-api  --(rswag / rspec-openapi)-->  openapi.json
                                                  |
                                    (openapi-typescript)
                                                  v
                                       packages/types/src/schema.d.ts
                                                  |
                                                  v
                                       packages/api-client  (hand-written thin layer)
                                             /          \
                                    apps/web          apps/mobile
```

Two packages, deliberately:

- **`packages/types`** — 100% generated. Never hand-edited. Regenerating overwrites it.
- **`packages/api-client`** — hand-written, thin, imports the generated types. Owns retries,
  auth headers, and error mapping. This is where judgment lives, so it must not be clobbered by
  a generator.

## Decision: where does the schema come from?

| Approach | Use when | Cost |
|---|---|---|
| **rswag** (request specs → OpenAPI) | You want the schema *proven* by tests | Specs must describe responses |
| **rspec-openapi** (records real responses) | Retrofitting an existing API | Schema is only as good as coverage |
| Hand-written `openapi.yaml` | Contract-first, API not built yet | Drifts unless CI diffs it against reality |

**Prefer a schema derived from passing tests.** A schema that no test proves is documentation,
and documentation drifts.

## Bad — two sources of truth

```ruby
# apps/rails-api/app/serializers/order_serializer.rb
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :total_cents, :placed_at
end
```

```ts
// packages/types/src/order.ts  ❌ hand-written, and already wrong
export interface Order {
  id: string;
  status: 'pending' | 'shipped';   // Rails added 'cancelled' last week
  totalCents: number;              // Rails sends total_cents
  placedAt: string;
}
```

Nothing here fails. `status === 'cancelled'` silently falls through every `switch`, and
`totalCents` is `undefined` — rendering `$NaN` in web and crashing the RN screen. The type
system reports full confidence because it is describing a fiction.

## Good — generated, and CI proves it is current

```ruby
# apps/rails-api/spec/requests/orders_spec.rb  ✅ the spec IS the schema
require 'swagger_helper'

RSpec.describe 'Orders', type: :request do
  path '/api/v1/orders/{id}' do
    get 'Fetch an order' do
      produces 'application/json'
      parameter name: :id, in: :path, type: :string

      response '200', 'order found' do
        schema type: :object, properties: {
          data: {
            type: :object,
            required: %w[id status total_cents placed_at],
            properties: {
              id: { type: :string },
              status: { type: :string, enum: %w[pending shipped cancelled] },
              total_cents: { type: :integer },
              placed_at: { type: :string, format: 'date-time' }
            }
          }
        }
        run_test!   # the schema is asserted against a real response
      end
    end
  end
end
```

```json
// packages/types/package.json  ✅
{
  "name": "@acme/types",
  "scripts": {
    "generate": "openapi-typescript ../../apps/rails-api/openapi.json -o src/schema.d.ts"
  }
}
```

```ts
// packages/api-client/src/orders.ts  ✅ thin, hand-written, generated types underneath
import type { paths } from '@acme/types';
import { http } from './http';

// Derived from the schema: if Rails renames a field, THIS LINE stops compiling.
export type Order =
  paths['/api/v1/orders/{id}']['get']['responses']['200']['content']['application/json']['data'];

export async function getOrder(id: string, signal?: AbortSignal): Promise<Order> {
  const { data } = await http.get<{ data: Order }>(`/api/v1/orders/${id}`, { signal });
  return data.data;
}
```

```tsx
// apps/web + apps/mobile  ✅ both consume ONE definition
import { getOrder, type Order } from '@acme/api-client';

// Rails adds 'cancelled' -> this switch fails to compile in BOTH apps, at once.
function label(order: Order) {
  switch (order.status) {
    case 'pending': return 'Pending';
    case 'shipped': return 'Shipped';
    default: {
      const _exhaustive: never = order.status;   // the drift alarm
      return _exhaustive;
    }
  }
}
```

The `never` assignment is the whole mechanism: an added enum value becomes a **compile error in
every consumer simultaneously**, in the same PR that changed Rails. That is the monorepo payoff
made real.

## Commit the generated output — and prove it is fresh

Mobile CI should not need a booted Rails to typecheck, so **commit `schema.d.ts`**. That makes
staleness possible, so make staleness fail:

```yaml
# .github/workflows/ci.yml  ✅
  api-contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bundle exec rake rswag:specs:swaggerize   # regenerate openapi.json from specs
      - run: pnpm --filter @acme/types generate
      - name: The committed contract must match the API
        run: |
          if ! git diff --exit-code -- apps/rails-api/openapi.json packages/types/src/schema.d.ts; then
            echo "FAIL: the API changed but the generated contract was not regenerated."
            echo "Run: bundle exec rake rswag:specs:swaggerize && pnpm --filter @acme/types generate"
            echo "Then commit the result. Consumers are compiling against a stale schema."
            exit 1
          fi
```

This is the general rule from `references/versioning-and-release.md` applied: *commit generated
code only when consumers cannot generate it themselves* — and when you do commit it, let CI own
the freshness rather than a human remembering.

## Boundary tests still required

The generated types prove the *shape*. They do not prove the *behaviour* — that a 422 comes back
with the error envelope the client parses, or that pagination cursors round-trip. Keep contract
tests at the boundary:

```ts
// packages/api-client/src/orders.test.ts  ✅ MSW handlers built from the same schema
it('should surface a field error when the API returns 422', async () => {
  server.use(http.post('*/api/v1/orders', () => HttpResponse.json(
    { errors: [{ field: 'quantity', message: 'must be positive' }] }, { status: 422 },
  )));
  await expect(createOrder({ quantity: -1 })).rejects.toMatchObject({
    fieldErrors: { quantity: 'must be positive' },
  });
});
```

Rails owns the envelope's shape (`std-api-design`); `api-client` owns translating it into
something the UI can render. Both sides review this package — see the CODEOWNERS entry in
`references/ci-at-scale.md`.
