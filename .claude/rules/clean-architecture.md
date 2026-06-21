---
paths:
  - "**/app/**/*.rb"
  - "**/lib/**/*.rb"
  - "**/src/**/*.ts"
  - "**/src/**/*.tsx"
  - "**/app/**/*.ts"
  - "**/app/**/*.tsx"
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
| Entities | Models, Value Objects | `backend/app/models/`, `backend/app/values/` |
| Use Cases | Service Objects | `backend/app/services/` |
| Interface Adapters | Controllers, Serializers, Form Objects | `backend/app/controllers/`, `backend/app/serializers/`, `backend/app/forms/` |
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
| Entities | TypeScript types/interfaces, domain utils | `mobile/src/domain/`, `mobile/src/types/` |
| Use Cases | Custom hooks (business logic) | `mobile/src/hooks/` |
| Interface Adapters | Screens, API client, navigation | `mobile/src/screens/`, `mobile/src/api/`, `mobile/src/navigation/` |
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

## ReactJS (Vite SPA) Mapping

| Clean Architecture Layer | Vite SPA Component | Directory |
|--------------------------|-------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `web/src/domain/`, `web/src/types/` |
| Use Cases | Custom hooks (business logic + data fetching) | `web/src/hooks/`, `web/src/api/` |
| Interface Adapters | Pages, components, API client, router config | `web/src/pages/`, `web/src/components/`, `web/src/api/`, `web/src/router/` |
| Frameworks | React, Vite, TanStack Query, Zustand, React Router | Framework code |

### Rules for ReactJS Vite SPA
- **Domain types** are pure TypeScript — no React, no framework dependencies.
- **Hooks** encapsulate business logic and data fetching (TanStack Query). Pages call hooks, not API clients directly.
- **Pages** are thin — compose hooks and presentational components. Minimal logic in JSX.
- **API client** is an interface adapter — transforms API responses to domain types.
- **Zustand stores** hold client-only state (UI preferences, sidebar, theme). Never duplicate server state.
- **React Router** config is framework-level. Auth guards wrap routes as adapter-layer components.

## Next.js App Router Mapping

| Clean Architecture Layer | Next.js Component | Directory |
|--------------------------|-------------------|-----------|
| Entities | TypeScript types/interfaces, domain utils | `next/src/domain/`, `next/src/types/` |
| Use Cases (Server) | Server actions | `next/src/actions/` |
| Use Cases (Client) | Custom hooks | `next/src/hooks/` |
| Interface Adapters | Pages, layouts, route handlers, components | `next/app/`, `next/src/components/`, `next/src/api/` |
| Frameworks | Next.js, React Server Components, TanStack Query, Zustand | Framework code |

### Rules for Next.js App Router
- **Server actions** are use cases — they validate input (zod), call the Rails API, and trigger revalidation. No UI or framework concerns.
- **Server Components** (pages, layouts) are interface adapters — they fetch data and compose components. Keep them thin.
- **Client Components** (`'use client'`) should be leaf-level and minimal. Extract interactive parts, keep data fetching in Server Components.
- **Domain types** are pure TypeScript — shared across server and client boundaries.
- **Route handlers** (`route.ts`) are interface adapters for BFF endpoints. Thin wrappers that delegate to services.

## Web Boundary Violations to Detect

9. **Page imports API client directly (Vite SPA)** — Page should call a hook, not axios directly.
10. **Server action contains UI logic** — Server action returns JSX or imports React components. Keep actions data-only.
11. **Client Component fetches data via `useEffect`** — Use TanStack Query `useQuery` instead.
12. **Domain type imports React or Next.js modules** — Keep domain types framework-free.

## Testing by Layer

- **Entities**: Unit tests, no mocks needed (pure domain logic).
- **Use Cases**: Unit tests with mocked repositories/gateways.
- **Interface Adapters**: Integration tests (controller specs, serializer specs).
- **Frameworks**: Minimal testing — trust the framework, test your configuration.
