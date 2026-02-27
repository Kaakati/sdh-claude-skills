---
paths:
  - "app/**"
  - "src/**"
  - "lib/**"
---

# Clean Architecture

Enforce Clean Architecture principles across all application code. The core rule: dependencies point inward. Outer layers depend on inner layers, never the reverse.

## Layer Model

```
┌──────────────────────────────────────┐
│  Frameworks & Drivers (outermost)    │  Rails, React Native, PostgreSQL, Redis
├──────────────────────────────────────┤
│  Interface Adapters                  │  Controllers, Serializers, Presenters, Gateways
├──────────────────────────────────────┤
│  Use Cases (Application Logic)       │  Service objects, Interactors, Commands
├──────────────────────────────────────┤
│  Entities (Domain Logic) (innermost) │  Models, Value Objects, Domain Rules
└──────────────────────────────────────┘
```

## The Dependency Rule

- **Entities** know nothing about use cases, controllers, or frameworks.
- **Use Cases** know about entities but not about controllers, serializers, or databases.
- **Interface Adapters** translate between use cases and external concerns.
- **Frameworks** are implementation details — pluggable and replaceable.

## Rails Mapping

| Clean Architecture Layer | Rails Component | Directory |
|--------------------------|-----------------|-----------|
| Entities | Models, Value Objects | `app/models/`, `app/values/` |
| Use Cases | Service Objects | `app/services/` |
| Interface Adapters | Controllers, Serializers, Form Objects | `app/controllers/`, `app/serializers/`, `app/forms/` |
| Frameworks | Rails itself, ActiveRecord, Sidekiq | Framework code |

### Rules for Rails
- **Models** contain domain logic (validations, associations, scopes, domain methods). No HTTP or serialization concerns.
- **Service objects** orchestrate business workflows. They call models and return Result objects. No direct HTTP response handling.
- **Controllers** are thin — authorize, call a service, serialize the response. Max 5 public actions per controller.
- **Serializers** (Panko) handle JSON representation only. No business logic in serializers.
- **Jobs** (Sidekiq) are thin wrappers that delegate to service objects. Jobs contain retry/error config, not business logic.

## React Native Mapping

| Clean Architecture Layer | React Native Component | Directory |
|--------------------------|------------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `src/domain/`, `src/types/` |
| Use Cases | Custom hooks (business logic) | `src/hooks/` |
| Interface Adapters | Screens, API client, navigation | `src/screens/`, `src/api/`, `src/navigation/` |
| Frameworks | React Native, TanStack Query, Zustand | Framework code |

### Rules for React Native
- **Domain types** are pure TypeScript — no React, no framework dependencies.
- **Hooks** encapsulate business logic and data fetching (TanStack Query). Screens call hooks, not API clients directly.
- **Screens** are thin — compose hooks and presentational components. Minimal logic in JSX.
- **API client** is an interface adapter — transforms API responses to domain types.
- **Zustand stores** hold client-only state (UI preferences, offline queue). Never duplicate server state.

## Boundary Violations to Detect

1. **Model imports controller/serializer** — Entity depends on adapter. Move logic to a service.
2. **Service returns HTTP status codes** — Use case knows about HTTP. Return Result objects instead.
3. **Controller contains business logic** — Extract to a service object.
4. **Serializer queries the database** — Adapter bypasses use case layer. Pre-load data in the service.
5. **Sidekiq job contains business logic** — Job should delegate to a service.
6. **Screen calls API client directly** — Use a hook as the intermediary.
7. **Hook imports React Native components** — Use case depends on framework. Keep hooks logic-only.
8. **Domain type imports framework modules** — Entity depends on framework. Keep types pure.

## Testing by Layer

- **Entities**: Unit tests, no mocks needed (pure domain logic).
- **Use Cases**: Unit tests with mocked repositories/gateways.
- **Interface Adapters**: Integration tests (controller specs, serializer specs).
- **Frameworks**: Minimal testing — trust the framework, test your configuration.
