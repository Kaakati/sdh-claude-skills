# Shaping Errors in a Rails API

Load-bearing rules restated (these hold even if you read nothing else):

- **Every** error response uses the same envelope: `error`, `code`, `status`, optional `details`, `requestId`.
- `code` is machine-readable and stable. Clients branch on `code`, never on `error` text.
- Never leak stack traces, internal paths, SQL, or class names in production error bodies.
- Validate at the API boundary (controller), never deep in business logic.
- Return **all** validation errors at once, not the first one.
- Strip unknown fields from validated input before passing it downstream — `params.require(...).permit(...)`.

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

## Testing the error contract (RSpec request spec)

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
