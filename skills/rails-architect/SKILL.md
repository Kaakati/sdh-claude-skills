---
name: rails-architect
description: Design and implement Rails backend features with Panko serializers, PostgreSQL/PostGIS, Redis caching, Sidekiq jobs, and Centrifugo real-time channels. Use this skill whenever someone asks to build a backend feature, design a Rails model, create an API endpoint, architect a service, or says things like "build the backend for X", "design the model layer", "add a Sidekiq job", "implement caching for X", "create the controller", or "how should we structure this service". Also trigger when someone mentions Panko serializer design, PostGIS spatial queries, Redis cache strategy, or Centrifugo channel topology.
model: sonnet
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Rails Architect

## Purpose
Design and implement backend features following Rails conventions with our specific stack: Rails + Panko + PostgreSQL/PostGIS + Redis + Sidekiq + Centrifugo.

## Design Protocol

### 1. Data Model First
- Start with the PostgreSQL schema — tables, columns, types, constraints
- Use PostGIS types (`st_point`, `geography`) for any location data
- Design indexes upfront: foreign keys, unique constraints, partial indexes, GiST for spatial
- Plan JSONB columns for flexible/polymorphic data
- Write reversible migrations with `change` method

### 2. Model Layer
- Define associations, validations, scopes
- Use `has_many through:` for join tables
- Extract complex queries to scopes or query objects
- Use `ActiveRecord::Enum` for status fields
- Add database-level constraints alongside model validations

### 3. API Design
- RESTful controllers with standard 7 actions
- Panko serializers for every response — never render raw models
- Separate list and detail serializers for performance
- Use `pagy` for pagination with cursor support
- Consistent error responses: `{ error: String, code: Integer, details: Object? }`

### 4. Service Layer
- Extract business logic to `app/services/` (any wrapper directory — the tree below illustrates
  shape, not a path to hardcode)
- Single responsibility: `CreateOrder`, `ProcessPayment`, `GeofenceCheck`
- Return result objects for success/failure handling
- Inject dependencies for testability

### 5. Background Processing
- Jobs live in `app/jobs/` (any wrapper directory — `backend/` is one team's naming, not a contract)
- Anything over ~100ms of work belongs in a job, not the request
- Separate queues: `default`, `critical`, `mailers`, `low_priority`
- **Pass IDs, not objects.** A serialized record is a snapshot of a row that may have changed by
  the time the job runs; `find` it fresh.
- **Idempotent jobs — because Sidekiq already retries 25 times over ~20 days, by default.** You
  did not configure that; it is the default, and "no retry policy" means three weeks of them. Set
  `sidekiq_options retry:` deliberately on every job. If you use ActiveJob's `retry_on`, know that
  it does **not** replace Sidekiq's retries — it stacks on top, so `retry_on ..., attempts: 5` runs
  30 attempts, not 5. A job that dies lands in the Dead set silently: alert on it.
  Depth → `@skills/std-error-handling/references/background-jobs.md`

### 6. Caching Strategy
- Redis-backed `Rails.cache.fetch` with explicit TTLs
- Cache Panko-serialized responses at controller level
- Fragment caching for repeated computations
- Cache invalidation on model callbacks

### 7. Real-time (Centrifugo)
- Design channel topology: `chat:room_123`, `user:456`, `location:fleet`
- Publish from Rails via Centrifugo HTTP API
- Use Redis pub/sub for internal event distribution
- JWT-based channel authorization

## Reference Architecture

```
backend/app/
├── controllers/
│   └── api/v1/           # Versioned API controllers
├── models/               # ActiveRecord models with validations
├── serializers/          # Panko::Serializer classes
├── services/             # Business logic service objects
├── jobs/                 # Sidekiq background jobs
├── policies/             # Pundit authorization policies
├── queries/              # Complex query objects
└── channels/             # Centrifugo channel helpers
```

## Common Patterns

### PostGIS Spatial Query
```ruby
# Find locations within radius
Location.where(
  "ST_DWithin(coordinates, ST_MakePoint(?, ?)::geography, ?)",
  longitude, latitude, radius_meters
)
```

### Panko Serializer with Association
```ruby
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :total_cents, :created_at
  has_one :customer, serializer: CustomerListSerializer
  has_many :items, serializer: OrderItemSerializer
end
```

### Sidekiq Job with Redis Cache
```ruby
class GeofenceCheckJob < ApplicationJob
  queue_as :default

  def perform(vehicle_id, lat, lng)
    vehicle = Vehicle.find(vehicle_id)
    geofences = Rails.cache.fetch("active_geofences", expires_in: 5.minutes) do
      Geofence.active.to_a
    end
    # Check and notify...
  end
end
```

See references/rails-patterns.md for comprehensive patterns library.

## Owned elsewhere — do not duplicate

This skill designs the shape. These own the rules, auto-load on Rails work, and carry the
bad/good pairs:

- **Authorization** — a policy that is never called is not authorization; `index` needs
  `policy_scope`, not `authorize`; `devise-jwt` does not revoke by default →
  `@skills/std-rails-conventions/references/authorization.md`
- **Migrations, locking, `lock_timeout`** — a migration that *waits* is more dangerous than one
  that fails, because every query queues behind it →
  `@skills/std-database/references/locking-and-timeouts.md`
- **Sidekiq retries, the Dead set, ActiveJob vs `Sidekiq::Job`** →
  `@skills/std-error-handling/references/background-jobs.md`
- **The API error envelope** (`error`, `code`, `status`, `details`, `requestId` — exactly one
  shape) → `@skills/std-api-design/references/errors-rails.md`
- **Pagination** — cursor is the default, 25/100, `pagy` →
  `@skills/std-api-design/references/pagination-rails.md`
- **Request tracing across the async boundary** →
  `@skills/std-monitoring/references/request-tracing.md`
