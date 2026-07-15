---
name: std-clean-architecture
description: Clean Architecture conventions — layer separation, dependency direction, boundary violations across Rails and frontends. Use when structuring services or reviewing architecture.
paths:
  - "**/app/**/*.rb"
  - "**/lib/**/*.rb"
  - "**/src/**/*.ts"
  - "**/src/**/*.tsx"
  - "**/app/**/*.ts"
  - "**/app/**/*.tsx"
---

# Clean Architecture

Enforce Clean Architecture principles across all application code. The core rule: dependencies
point inward. Outer layers depend on inner layers, never the reverse.

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

## Testing by Layer

- **Entities**: Unit tests, no mocks needed (pure domain logic).
- **Use Cases**: Unit tests with mocked repositories/gateways.
- **Interface Adapters**: Integration tests (controller specs, serializer specs).
- **Frameworks**: Minimal testing — trust the framework, test your configuration.

## The Universal Violations

Every platform expresses the same four mistakes. The per-platform guides below name each one
concretely, with the file paths and code it appears in:

1. **An entity depends on an adapter or framework** — a model that serializes itself, a domain
   type that imports React.
2. **A use case knows about delivery** — a service returning HTTP status codes, a server action
   returning JSX, a hook importing UI components.
3. **An adapter carries business logic** — a controller computing totals, a serializer querying
   the database, a route handler applying discounts.
4. **A layer is skipped** — a screen or page calling the API client directly instead of going
   through a hook.

## Deep guides (read on demand, do not preload)

Read **only the guide for the platform you are working in**. Each is self-contained: it restates
the dependency rule, gives the full layer→directory mapping, the rules per component, the boundary
violations to detect with bad/good code, and how to test each layer. A Rails task must not load
the frontend guides; a frontend task must not load the Rails guide.

| Working in… | Read |
|-------------|------|
| Rails backend — models, services, controllers, Panko serializers, Sidekiq jobs (`app/**/*.rb`, `lib/**/*.rb`) | `references/rails-mapping.md` |
| React Native mobile app — screens, hooks, domain types, Zustand stores (`mobile/src/**`) | `references/react-native-mapping.md` |
| ReactJS Vite SPA — pages, hooks, router config, Zustand stores (`web/src/**`) | `references/reactjs-vite-mapping.md` |
| Next.js App Router — Server Components, server actions, route handlers (`next/app/**`, `next/src/**`) | `references/nextjs-app-router-mapping.md` |

If a change spans platforms (for example, a feature touching both Rails and Next.js), read the two
relevant guides and no others.
