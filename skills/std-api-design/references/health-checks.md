# Health Checks

Load-bearing rules restated (these hold even if you read nothing else):

- **Every service exposes `GET /health`** reporting `status`, `version`, `uptime`, and per-
  dependency health.
- `/health` is unauthenticated and safelisted from the rate limiter — a throttle must never be
  able to fail a load balancer check.
- Liveness must **not** depend on downstream services. Deep dependency checking is opt-in via
  `?deep=true`.
- Every dependency check is **time-bounded**. A health check must never hang.

---

## Decision: what goes in the health check?

`/health` has two distinct audiences and they need different answers.

| Consumer | Needs | Endpoint |
|----------|-------|----------|
| ALB / ECS target group | "Can this container serve traffic?" — fast, no dependencies | `/health` (liveness) |
| On-call, dashboards | "Is the system whole?" — checks dependencies | `/health?deep=true` |

If the load balancer's check fails because Redis is down, ECS kills **every** container and the
degradation becomes a total outage. Liveness must not depend on downstream services.

### Bad — one endpoint, dependency-coupled, unbounded

```ruby
class HealthController < ApplicationController
  def show
    # Any hiccup in Redis => 500 => ALB drains every task => full outage from a partial one.
    # And no timeout: a hung DB connection holds a Puma thread until it dies.
    ActiveRecord::Base.connection.execute("SELECT 1")
    Redis.new.ping
    render json: { status: "ok" }
  end
end
```

### Good — cheap liveness by default, deep check on request, per-dependency timeouts

```ruby
# app/controllers/health_controller.rb
class HealthController < ApplicationController
  skip_before_action :authenticate_user!, raise: false

  BOOTED_AT = Process.clock_gettime(Process::CLOCK_MONOTONIC)

  def show
    return render(json: liveness_body) unless params[:deep] == "true"

    deps   = Health::DependencyCheck.new.call
    status = deps.values.include?("unhealthy") ? :service_unavailable : :ok

    render json: liveness_body.merge(
      status: overall_status(deps),
      dependencies: deps
    ), status: status
  end

  private

  def liveness_body
    {
      status: "healthy",
      version: ENV.fetch("APP_VERSION", "unknown"),
      uptime: (Process.clock_gettime(Process::CLOCK_MONOTONIC) - BOOTED_AT).round
    }
  end

  def overall_status(deps)
    return "unhealthy" if deps.values.include?("unhealthy")
    return "degraded"  if deps.values.include?("degraded")

    "healthy"
  end
end
```

```ruby
# app/services/health/dependency_check.rb
module Health
  class DependencyCheck
    TIMEOUT = 2 # seconds — a health check must never hang

    def call
      {
        database: check { ActiveRecord::Base.connection.execute("SELECT 1") && "healthy" },
        cache: check { Rails.cache.redis.then { |r| r.ping == "PONG" ? "healthy" : "degraded" } },
        queue: check { Sidekiq::Queue.new.latency < 60 ? "healthy" : "degraded" }
      }
    end

    private

    def check
      Timeout.timeout(TIMEOUT) { yield }
    rescue Timeout::Error
      "degraded"
    rescue StandardError => e
      Rails.logger.error(message: "health_check_failed", error_class: e.class.name)
      "unhealthy"
    end
  end
end
```

Response:

```json
{
  "status": "degraded",
  "version": "1.2.0",
  "uptime": 86400,
  "dependencies": { "database": "healthy", "cache": "healthy", "queue": "degraded" }
}
```

`degraded` is deliberate: a backed-up Sidekiq queue should page someone without taking the API
out of the load balancer.

Route it, and keep it out of the rate limiter and the auth chain:

```ruby
# config/routes.rb
get "/health", to: "health#show"
```

---

## Decision: what does the ALB target group point at?

The shallow check — always.

```hcl
resource "aws_lb_target_group" "api" {
  name        = "${var.project}-${var.environment}-api"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health" # NOT /health?deep=true — never couple the LB to Redis
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = var.common_tags
}
```

---

## Testing health

```ruby
# spec/requests/health_spec.rb
it "should stay healthy for the load balancer even when a dependency is down" do
  allow(Rails.cache).to receive(:redis).and_raise(Redis::CannotConnectError)

  get "/health"

  expect(response).to have_http_status(:ok)
  expect(response.parsed_body["status"]).to eq("healthy")
end

it "should report the failing dependency on a deep check" do
  allow(Rails.cache).to receive(:redis).and_raise(Redis::CannotConnectError)

  get "/health", params: { deep: "true" }

  expect(response).to have_http_status(:service_unavailable)
  expect(response.parsed_body["dependencies"]["cache"]).to eq("unhealthy")
end
```
