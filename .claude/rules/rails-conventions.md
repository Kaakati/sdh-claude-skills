---
paths:
  - "backend/app/**/*.rb"
  - "backend/lib/**/*.rb"
  - "backend/config/**/*.rb"
  - "backend/db/**/*.rb"
---

# Ruby on Rails Conventions

## Rails Way
- Follow Rails conventions over configuration — don't fight the framework
- Use standard Rails directory structure (app/models, app/controllers, app/services, etc.)
- Prefer ActiveRecord callbacks sparingly — use service objects for complex logic
- Use concerns for shared model/controller behavior, but keep them focused

## Models
- Fat models are acceptable for domain logic, but extract service objects when > 200 lines
- Use scopes for reusable queries: `scope :active, -> { where(active: true) }`
- Validate at the model level, not just the database level
- Use `has_many through:` for join tables, never `has_and_belongs_to_many`
- Always add database-level constraints (NOT NULL, foreign keys, unique indexes) alongside model validations

## Controllers
- Thin controllers — max 7 RESTful actions per controller
- Extract non-RESTful actions into dedicated controllers
- Use `before_action` for authentication and authorization checks
- Never put business logic in controllers — delegate to service objects
- Use strong parameters: `params.require(:model).permit(:field1, :field2)`

## Serialization (Panko)
- Use Panko::Serializer for all JSON responses — it's significantly faster than AMS
- Define explicit `attributes` — never serialize entire models
- Use `has_many` and `has_one` associations in serializers
- Create separate serializers for list vs detail views (e.g., `UserListSerializer`, `UserDetailSerializer`)
- Example:
  ```ruby
  class UserSerializer < Panko::Serializer
    attributes :id, :name, :email, :created_at

    has_one :profile, serializer: ProfileSerializer
  end
  ```

## Service Objects
- Place in `backend/app/services/` with clear naming: `CreateUser`, `ProcessPayment`
- Single public method: `call` or `execute`
- Return result objects, not bare values — consider using `dry-monads` or similar
- Keep services testable with dependency injection

## Background Jobs (Sidekiq + Redis)
- Use Sidekiq for all background processing
- Make jobs idempotent — safe to retry
- Set appropriate queues: `default`, `critical`, `low_priority`
- Never pass ActiveRecord objects to jobs — pass IDs and re-fetch
- Set sensible retry limits and dead-letter handling

## Database (PostgreSQL + PostGIS)
- Use migrations for ALL schema changes — never modify production DB manually
- Use `uuid` as primary key type for new tables when appropriate
- Leverage PostgreSQL-specific features: JSONB columns, array columns, CTEs, partial indexes
- Use PostGIS types for geospatial: `st_point`, `st_polygon` via `activerecord-postgis-adapter`
- Use `RGeo` for geometry operations in Ruby
- Always add indexes for foreign keys and frequently filtered columns

## Caching (Redis)
- Use Rails cache with Redis backend: `Rails.cache.fetch`
- Cache serialized responses at the controller level for list endpoints
- Use Russian Doll caching for nested views
- Set explicit TTLs — no infinite caches
- Use cache keys that include `updated_at` for automatic invalidation

## Gems — Prefer Established Libraries
- Authentication: `devise` + `devise-jwt` for API auth
- Authorization: `pundit` (policy objects) over `cancancan`
- Pagination: `pagy` (fastest) over `kaminari` or `will_paginate`
- Search: `pg_search` for PostgreSQL full-text search
- File uploads: `ActiveStorage` with S3 backend
- Geospatial: `rgeo`, `activerecord-postgis-adapter`, `geocoder`
- API documentation: `rswag` for Swagger/OpenAPI
- Testing: `rspec-rails`, `factory_bot_rails`, `shoulda-matchers`
- Background jobs: `sidekiq`, `sidekiq-cron` for scheduled jobs
- HTTP client: `faraday` with middleware
