---
name: clean-architecture
description: Validate and implement Clean Architecture patterns including entity/use-case/adapter/framework layer separation, dependency direction enforcement, and architectural conformance checking. Use this skill whenever someone asks about architecture validation, layer boundaries, dependency direction, or says things like "check architecture", "validate clean architecture", "are my layers correct", "dependency direction", "refactor to clean architecture", "layer violation", or "architectural conformance". Also trigger for discussions about service object patterns, controller responsibilities, or domain model isolation.
agent: clean-architecture
context: fork
model: sonnet
---

# Clean Architecture Skill

Validate, implement, and maintain Clean Architecture patterns across the full stack. This skill covers architectural conformance checking, layer boundary enforcement, and guided refactoring.

See `references/layer-examples.md` for full code examples across all frameworks.

## Architecture Layers

### Layer 1: Entities (Domain Core)
The innermost layer. Pure business logic with zero framework dependencies.
- **Rails**: Models with domain logic only (`backend/app/models/`), value objects (`backend/app/values/`)
- **React Native**: Pure TypeScript interfaces and domain functions (`mobile/src/domain/`)
- **Vite SPA**: Pure TypeScript types (`web/src/domain/`)
- **Next.js**: Shared TypeScript types (`next/src/domain/`)

### Layer 2: Use Cases (Application Logic)
Orchestrate business workflows. Depend on entities, return Result objects.
- **Rails**: Service objects with single `call` method (`backend/app/services/`)
- **React Native**: Custom hooks wrapping TanStack Query (`mobile/src/hooks/`)
- **Vite SPA**: TanStack Query hooks (`web/src/hooks/`, `web/src/api/`)
- **Next.js (Server)**: Server actions with zod validation (`next/src/actions/`)
- **Next.js (Client)**: Custom hooks (`next/src/hooks/`)

### Layer 3: Interface Adapters
Translate between application core and external concerns.
- **Rails**: Thin controllers (authorize → service → serialize), Panko serializers
- **React Native**: Thin screens composing hooks + components (`mobile/src/screens/`)
- **Vite SPA**: Thin pages composing hooks + components (`web/src/pages/`)
- **Next.js**: Server Component pages, layouts (`next/app/`), client components (`next/src/components/`)

### Layer 4: Frameworks & Drivers
External tools configured, not coded against: Rails, React Native, React, Next.js, PostgreSQL, Redis, Centrifugo, AWS, Sidekiq, TanStack Query, Zustand.

## Conformance Validation Checklist

### Dependency Direction
- [ ] Models do NOT import controllers, serializers, or jobs
- [ ] Services do NOT return HTTP status codes or render responses
- [ ] Services do NOT import controllers or serializers
- [ ] Controllers only contain: authorize, call service, serialize response
- [ ] Serializers do NOT query the database or contain business logic
- [ ] Sidekiq jobs delegate to service objects (no inline business logic)
- [ ] React Native screens delegate to hooks (no inline API calls or business logic)
- [ ] Hooks do NOT import React Native UI components
- [ ] Domain types are pure TypeScript (no React or framework imports)
- [ ] Zustand stores contain ONLY client state (no server data)

### Structural Health
- [ ] Each service object has a single public `call` method
- [ ] Controllers have max 5 public actions (index, show, create, update, destroy)
- [ ] Value objects are immutable
- [ ] No circular dependencies between services
- [ ] API client transforms responses to domain types at the boundary

### Vite SPA
- [ ] Pages call hooks, not API clients directly
- [ ] Domain types have no React or framework imports
- [ ] Zustand stores contain ONLY client state (no API responses)
- [ ] All routes are lazy-loaded

### Next.js App Router
- [ ] Server actions validate input with zod (they are public endpoints)
- [ ] Server actions do NOT import React components or return JSX
- [ ] Pages use Server Components for data fetching (no `'use client'` on page files)
- [ ] Client Components are leaf-level — interactive parts only
- [ ] Domain types are shared across server/client boundaries without framework imports

## Common Refactoring Patterns

1. **Extract Service from Controller** — Move inline business logic from controller to a service object returning Result.
2. **Extract Hook from Screen** — Move useEffect/API calls/state management from screen to a custom hook.
3. **Extract Hook from Page (Vite SPA)** — Move inline API calls from page component to TanStack Query hook.
4. **Extract Client Component from Server Component (Next.js)** — Move interactive widget to a separate `'use client'` component.
5. **Extract Value Object from Model** — Group related attributes and domain behavior into an immutable value object.
6. **Extract Adapter for External Service** — Wrap external API with adapter interface; service depends on abstraction.
