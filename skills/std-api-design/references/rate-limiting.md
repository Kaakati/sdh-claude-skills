# Rate Limiting an API

Load-bearing rules restated (these hold even if you read nothing else):

- Rate-limit **all public endpoints**. Apply **stricter limits to authentication endpoints**
  (login, password reset, signup, token refresh).
- Every rate-limited response carries:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1672531200
  ```
- On exceeding a limit return **`429 Too Many Requests`** with a **`Retry-After`** header, in the
  canonical error envelope (`error`, `code`, `status`, `requestId`).
- Health endpoints are **safelisted** — a rate limiter must never be able to fail a load balancer
  check.

---

## Decision: how do I rate-limit a Rails API?

Community libraries first — `rack-attack` is the house choice. It runs as middleware, before
Rails routing, so a flood never touches a controller or a database connection.

### Bad — counting in the controller

```ruby
class Api::V1::SessionsController < ApplicationController
  def create
    count = Rails.cache.increment("login:#{request.ip}")
    # By the time this runs, Rails has already routed, allocated a controller, and
    # parsed params. The abuser still consumes a Puma thread per request.
    return render json: { error: "slow down" }, status: 429 if count > 5
    # ...and the response has no envelope, no code, no Retry-After.
  end
end
```

### Good — rack-attack middleware, tiered limits, canonical 429 envelope

```ruby
# config/initializers/rack_attack.rb
class Rack::Attack
  Rack::Attack.cache.store = ActiveSupport::Cache::RedisCacheStore.new(
    url: ENV.fetch("REDIS_URL")
  )

  ### Allow-lists ###
  safelist("health-checks") { |req| req.path == "/health" }

  ### General API limit — per authenticated client, falling back to IP ###
  throttle("api/general", limit: 100, period: 1.minute) do |req|
    next unless req.path.start_with?("/v1", "/v2")

    req.env["api.client_id"] || req.ip
  end

  ### Authentication endpoints — an order of magnitude stricter ###
  throttle("auth/ip", limit: 5, period: 20.seconds) do |req|
    req.ip if req.post? && req.path.match?(%r{\A/v\d/(sessions|passwords|users)\z})
  end

  # Credential stuffing rotates IPs but reuses the email. Throttle the identity too.
  throttle("auth/email", limit: 5, period: 1.hour) do |req|
    if req.post? && req.path.match?(%r{\A/v\d/(sessions|passwords)\z})
      body = begin
        JSON.parse(req.body.string)
      rescue JSON::ParserError
        {}
      ensure
        req.body.rewind
      end
      body.dig("email").to_s.downcase.presence
    end
  end

  ### Exponential backoff for sustained abuse ###
  (1..3).each do |level|
    throttle("api/exponential/#{level}", limit: 200 * level, period: (10**level).seconds) do |req|
      req.ip if req.path.start_with?("/v1", "/v2")
    end
  end

  ### The 429 response — same envelope as every other error ###
  self.throttled_responder = lambda do |req|
    match  = req.env["rack.attack.match_data"] || {}
    now    = Time.now.to_i
    period = match[:period].to_i
    reset  = period.positive? ? (now + (period - (now % period))) : now

    headers = {
      "Content-Type"          => "application/json",
      "X-RateLimit-Limit"     => match[:limit].to_s,
      "X-RateLimit-Remaining" => "0",
      "X-RateLimit-Reset"     => reset.to_s,
      "Retry-After"           => (reset - now).to_s
    }

    body = {
      error: "Rate limit exceeded. Retry after #{reset - now} seconds.",
      code: "RATE_LIMIT_EXCEEDED",
      status: 429,
      requestId: req.env["action_dispatch.request_id"]
    }.to_json

    [429, headers, [body]]
  end
end
```

Successful responses must advertise the budget too, or clients can only discover the limit by
hitting it:

```ruby
# app/controllers/concerns/rate_limit_headers.rb
module RateLimitHeaders
  extend ActiveSupport::Concern

  included do
    after_action :set_rate_limit_headers
  end

  private

  def set_rate_limit_headers
    data = request.env["rack.attack.throttle_data"]&.dig("api/general")
    return if data.blank?

    response.set_header("X-RateLimit-Limit", data[:limit].to_s)
    response.set_header("X-RateLimit-Remaining", [data[:limit] - data[:count], 0].max.to_s)
    response.set_header("X-RateLimit-Reset", (data[:epoch_time] + data[:period]).to_s)
  end
end
```

---

## Decision: how should the client react to a 429?

### Bad — retry immediately, forever

```typescript
// Retries with no delay, ignores Retry-After, and hammers a server that is already
// telling you to stop. This turns a throttle into an outage.
const mutation = useMutation({ mutationFn: createOrder, retry: true, retryDelay: 0 });
```

### Good — honour Retry-After, back off exponentially, never retry non-idempotent writes blindly

```typescript
// src/api/queryClient.ts
import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './client';

function retryDelay(attempt: number, error: unknown): number {
  if (error instanceof ApiError && error.status === 429 && error.retryAfterSeconds) {
    return error.retryAfterSeconds * 1000; // the server told us exactly when
  }
  const backoff = Math.min(1000 * 2 ** attempt, 30_000);
  return backoff + Math.random() * 250; // jitter: stops a thundering herd on recovery
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError) {
          // 4xx are the client's fault — retrying cannot help. 429 is the exception.
          if (error.status === 429) return failureCount < 3;
          if (error.status >= 400 && error.status < 500) return false;
        }
        return failureCount < 3;
      },
      retryDelay,
    },
    mutations: {
      // Writes are not automatically idempotent — retry only on explicit 429.
      retry: (failureCount, error) =>
        error instanceof ApiError && error.status === 429 && failureCount < 2,
      retryDelay,
    },
  },
});
```

Parse `Retry-After` in the interceptor so the above has something to read:

```typescript
apiClient.interceptors.response.use(undefined, (err: AxiosError) => {
  const retryAfter = err.response?.headers['retry-after'];
  const apiError = new ApiError(/* code, status, message, details, requestId */);
  apiError.retryAfterSeconds = retryAfter ? Number(retryAfter) : undefined;
  throw apiError;
});
```

---

## Testing rate limits

```ruby
# spec/requests/rate_limiting_spec.rb
before { Rack::Attack.enabled = true; Rack::Attack.reset! }
after  { Rack::Attack.enabled = false }

it "should return 429 with Retry-After when the auth limit is exceeded" do
  6.times { post "/v1/sessions", params: { email: "a@b.com", password: "wrong" } }

  expect(response).to have_http_status(:too_many_requests)
  expect(response.headers["Retry-After"]).to be_present
  expect(response.headers["X-RateLimit-Remaining"]).to eq("0")
  expect(response.parsed_body["code"]).to eq("RATE_LIMIT_EXCEEDED")
end

it "should not throttle the health endpoint" do
  200.times { get "/health" }
  expect(response).to have_http_status(:ok)
end
```
