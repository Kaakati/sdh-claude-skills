# Versioning a Breaking Change

Load-bearing rules restated (these hold even if you read nothing else):

- Version lives **in the URL path**: `/v1/users`, `/v2/users`.
- Increment the **major version only for breaking changes**. Additive changes never bump.
- Support the previous version for a **documented deprecation period**.
- While the old version is still served, every response from it carries the RFC 8594 headers
  `Deprecation: true` and `Sunset: Sat, 01 Mar 2025 00:00:00 GMT`.

## Decision: is this change breaking?

| Change | Breaking? | Action |
|--------|-----------|--------|
| Add a new optional response field | No | Ship on `/v1` |
| Add a new optional request param | No | Ship on `/v1` |
| Add a new endpoint | No | Ship on `/v1` |
| Add a new enum value the client must handle | **Yes** | New version, or gate behind a param |
| Remove or rename a response field | **Yes** | New version |
| Change a field's type (`"5"` → `5`, string → object) | **Yes** | New version |
| Make an optional request param required | **Yes** | New version |
| Tighten validation (max 100 → max 10) | **Yes** | New version |
| Change the meaning of an existing field | **Yes** | New version |
| Change a success status code (200 → 202) | **Yes** | New version |
| Fix a bug where the response contradicted documented behavior | No | Ship on `/v1`, changelog it |

Rule of thumb: if a well-behaved existing client, unchanged, would start producing wrong results or crashing, it is breaking.

## Decision: how do I add a field without breaking v1?

Additive is free. Do it in place. Do **not** mint `/v2` for a new field.

### Bad — a version bump for an additive change

```ruby
# Two controller trees, two serializer trees, two spec suites — for one nullable field.
namespace :v2 do
  resources :orders # identical to v1 plus `estimated_delivery_at`
end
```

### Good — add the field to v1

```ruby
# app/serializers/order_serializer.rb
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :total_cents, :created_at, :estimated_delivery_at
end
```

Clients that ignore unknown keys — which every client must — are unaffected. Note it in `CHANGELOG.md` under **Added**.

## Decision: how do I structure v1 and v2 side by side in Rails?

Share the domain, fork only the serialization boundary.

### Bad — copy the whole controller and let the two drift

```ruby
class Api::V2::OrdersController < ApplicationController
  def index
    # 60 lines copy-pasted from V1, including the authorization and the scoping.
    # A bug fixed in V1 is now silently unfixed in V2.
  end
end
```

### Good — v2 controller inherits behaviour, overrides only the serializer

```ruby
# config/routes.rb
Rails.application.routes.draw do
  scope path: "v1", module: "api/v1", as: "api_v1" do
    resources :orders, only: %i[index show create]
  end

  scope path: "v2", module: "api/v2", as: "api_v2" do
    resources :orders, only: %i[index show create]
  end
end
```

```ruby
# app/controllers/api/v1/orders_controller.rb
module Api
  module V1
    class OrdersController < ApplicationController
      include ApiErrorHandling
      include CursorPaginable

      def index
        orders, pagination = paginate_by_cursor(
          policy_scope(Order).order(created_at: :desc, id: :desc)
        )
        render json: {
          data: serializer_class.new(orders, each_serializer: true).to_a,
          pagination: pagination
        }
      end

      def show
        order = policy_scope(Order).find(params[:id])
        authorize order
        render json: { data: serializer_class.new(order).to_h }
      end

      private

      # The single seam between versions.
      def serializer_class
        Api::V1::OrderSerializer
      end
    end
  end
end
```

```ruby
# app/controllers/api/v2/orders_controller.rb
module Api
  module V2
    class OrdersController < Api::V1::OrdersController
      private

      def serializer_class
        Api::V2::OrderSerializer
      end
    end
  end
end
```

```ruby
# app/serializers/api/v1/order_serializer.rb  — frozen, do not touch during the v2 build
module Api
  module V1
    class OrderSerializer < Panko::Serializer
      attributes :id, :status, :total, :created_at

      # v1 shipped `total` as a float in dollars. Kept exactly as-is.
      def total
        object.total_cents / 100.0
      end
    end
  end
end
```

```ruby
# app/serializers/api/v2/order_serializer.rb
module Api
  module V2
    class OrderSerializer < Panko::Serializer
      # v2 fixes the float-money mistake: integer minor units + explicit currency.
      attributes :id, :status, :amount, :created_at

      def amount
        { cents: object.total_cents, currency: object.currency, formatted: object.formatted_total }
      end
    end
  end
end
```

Fork the **serializers**, not the business logic. Business logic lives in service objects that neither version copies.

## Decision: how do I signal deprecation on the old version?

Announce it in the response, on every call, from the moment v2 ships.

### Bad — a blog post and an email

```ruby
# Nothing in the response. The client integration written 18 months ago by a
# contractor who has left will break on sunset day with no warning at all.
```

### Good — RFC 8594 headers, plus a log line naming the caller

```ruby
# app/controllers/concerns/deprecatable.rb
module Deprecatable
  extend ActiveSupport::Concern

  class_methods do
    # sunset_on: the date the version stops being served.
    def deprecate_version!(sunset_on:, successor_path:)
      before_action do
        response.set_header("Deprecation", "true")
        response.set_header("Sunset", sunset_on.to_datetime.httpdate)
        response.set_header("Link", %(<#{successor_path}>; rel="successor-version"))

        Rails.logger.warn(
          message: "deprecated_api_called",
          request_id: request.request_id,
          path: request.path,
          sunset_on: sunset_on.iso8601,
          client_id: current_client_id,
          user_agent: request.user_agent
        )
      end
    end
  end
end
```

```ruby
module Api
  module V1
    class OrdersController < ApplicationController
      include Deprecatable

      deprecate_version!(sunset_on: Date.new(2025, 3, 1), successor_path: "/v2/orders")
    end
  end
end
```

The log line is the point: it tells you **who** still calls v1, so sunset day is a decision backed by data rather than a hope. Query it before removing anything.

Client-side, surface the header instead of swallowing it:

```typescript
apiClient.interceptors.response.use((res) => {
  if (res.headers['deprecation'] === 'true') {
    console.warn(
      `[api] ${res.config.url} is deprecated; sunset ${res.headers['sunset']}. ` +
        `Successor: ${res.headers['link']}`,
    );
  }
  return res;
});
```

## Decision: retiring the old version

The sequence, in order:

1. **Ship v2.** v1 keeps working, untouched.
2. **Mark v1 deprecated** with `Deprecation` / `Sunset` headers and the warn log. Sunset date is at minimum one full release cycle out, documented in `CHANGELOG.md` under **Deprecated**.
3. **Migrate first-party clients** (web, mobile) to v2. Mobile is the constraint — old app binaries live in the wild for months; the sunset date must be later than your minimum supported app version's retirement.
4. **Watch the `deprecated_api_called` logs** until traffic is zero or only from clients you have explicitly written off.
5. **Brown-out** — return `410 Gone` from v1 for short scheduled windows before the real sunset, so remaining integrations fail loudly while someone is at a desk to answer the phone.
6. **Remove v1.** Delete the controllers, serializers, and specs. `CHANGELOG.md` under **Removed**.

The `410 Gone` response after sunset — still the canonical error envelope:

```ruby
# config/routes.rb
scope path: "v1" do
  match "*path", to: "api/gone#show", via: :all
end
```

```ruby
class Api::GoneController < ApplicationController
  def show
    render json: {
      error: "API v1 was retired on 2025-03-01. Use /v2.",
      code: "API_VERSION_GONE",
      status: 410,
      requestId: request.request_id
    }, status: :gone
  end
end
```

## Testing the version contract

The v1 spec is a **contract test**. Its job is to fail if anyone reshapes v1.

```ruby
# spec/requests/api/v1/orders_spec.rb
it "should keep the frozen v1 field set" do
  create(:order, user: user)
  get "/v1/orders", headers: auth_headers

  expect(response.parsed_body["data"].first.keys)
    .to match_array(%w[id status total created_at])
end

it "should advertise deprecation and sunset on v1" do
  get "/v1/orders", headers: auth_headers

  expect(response.headers["Deprecation"]).to eq("true")
  expect(response.headers["Sunset"]).to be_present
end
```

```ruby
# spec/requests/api/v2/orders_spec.rb
it "should return money as an object with integer minor units" do
  create(:order, user: user, total_cents: 1_999, currency: "USD")
  get "/v2/orders", headers: auth_headers

  expect(response.parsed_body["data"].first["amount"])
    .to include("cents" => 1_999, "currency" => "USD")
end
```
