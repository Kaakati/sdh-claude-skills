---
name: std-api-design
description: REST API design conventions — URL nouns, response envelope, error format, pagination, versioning, status codes. Use when designing or reviewing API endpoints.
paths:
  - "**/app/controllers/**/*.rb"
  - "**/src/api/**"
  - "**/src/actions/**"
  - "**/routes/**"
  - "**/controllers/**"
  - "**/endpoints/**"
---

# API Design Standards

Rules for designing and implementing RESTful APIs.

**Enforcement**: code-reviewer skill (Step 8: Stack-Specific Checks), api-designer skill (design validation).

## RESTful URL Naming

- Use **plural nouns** for resource collections. No verbs in URLs.
- Use path hierarchy to express relationships.
- Use kebab-case for multi-word resources: `/v1/order-items`, not `/v1/orderItems`.
- Keep URLs shallow — maximum 3 levels of nesting. Use query parameters or separate endpoints beyond that.

```
# Good                          # Bad
GET    /v1/users                GET    /v1/getUser/123
GET    /v1/users/123            POST   /v1/createUser
GET    /v1/users/123/orders     GET    /v1/user/123/getOrders
POST   /v1/users                POST   /v1/deleteUser/123
PATCH  /v1/users/123
```

## HTTP Methods

| Method   | Purpose                  | Idempotent | Request Body | Success Code |
|----------|--------------------------|------------|--------------|--------------|
| `GET`    | Read resource(s)         | Yes        | No           | 200          |
| `POST`   | Create new resource      | No         | Yes          | 201          |
| `PUT`    | Full replacement update  | Yes        | Yes          | 200          |
| `PATCH`  | Partial update           | No*        | Yes          | 200          |
| `DELETE` | Remove resource          | Yes        | No           | 204          |

- Return `404` when a resource does not exist (GET, PUT, PATCH, DELETE).
- Return `409 Conflict` for duplicate creation attempts.
- Return `202 Accepted` for async operations that will complete later.

## Response Conventions

- Wrap collections in a `data` field: `{ "data": [...], "pagination": {...} }`.
- Return the created/updated resource in the response body for POST, PUT, PATCH.
- Use consistent date format: ISO 8601 (`2024-01-15T09:30:00Z`).
- Use camelCase for JSON response keys.
- Include `Location` header for POST (201) responses pointing to the new resource.

## Error Format

Every error — from every endpoint — uses this envelope. Never a bare string, never a bare array.

```json
{
  "error": "Human-readable error message",
  "code": "VALIDATION_ERROR",
  "status": 422,
  "details": [{ "field": "email", "message": "Must be a valid email address" }],
  "requestId": "req-abc-123"
}
```

- Always include a machine-readable `code` — clients branch on `code`, never on `error` text.
- Always include `requestId` for support and debugging.
- Never expose stack traces, internal paths, or implementation details in production responses.
- Status codes: `400` malformed · `401` unauthenticated · `403` unauthorized · `404` not found ·
  `409` conflict · `422` validation failure · `429` rate limited · `500` unexpected failure.

## Input Validation

- Validate **all** request inputs with a schema library (Zod on TS; strong params + model
  validations on Rails).
- Validate at the API boundary (controller / route handler), not deep in business logic.
- Return all validation errors at once, not one at a time.
- Strip unknown fields from validated input — never pass unexpected data downstream.

## Pagination

- **Cursor-based is the default.** Offset is acceptable only for small, stable datasets.
- Default page size **25**, maximum **100**, client-settable via `?limit=`.
- Always return pagination metadata — never a bare array.

```json
{ "data": [], "pagination": { "nextCursor": "eyJpZCI6MTAwfQ==", "hasMore": true, "limit": 25 } }
```

## Versioning

- Version in the URL path: `/v1/users`. Bump the major **only for breaking changes**.
- Support the previous version for a documented deprecation period, with headers on every
  response from it:
  ```
  Deprecation: true
  Sunset: Sat, 01 Mar 2025 00:00:00 GMT
  ```

## Rate Limiting and Health

- Rate-limit all public endpoints; stricter limits on auth endpoints (login, password reset).
- Return `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` headers; `429` with
  `Retry-After` when exceeded.
- Every service exposes `GET /health` returning `status`, `version`, `uptime`, and `dependencies`.

## Deep guides (read on demand, do not preload)

- Rails error concern, Zod boundaries, server-action results, typed client → `references/errors-and-validation.md`
- Keyset cursors, pagy, PostGIS proximity, `useInfiniteQuery` → `references/pagination.md`
- Is-it-breaking table, v1/v2 side by side, sunset sequence → `references/versioning-and-deprecation.md`
- rack-attack tiers, client backoff, liveness vs deep health → `references/rate-limiting-and-health.md`
