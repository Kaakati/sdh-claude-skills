---
paths:
  - "src/api/**"
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

```
# Good
GET    /v1/users
GET    /v1/users/123
GET    /v1/users/123/orders
POST   /v1/users
PATCH  /v1/users/123

# Bad
GET    /v1/getUser/123
POST   /v1/createUser
GET    /v1/user/123/getOrders
POST   /v1/deleteUser/123
```

- Use kebab-case for multi-word resources: `/v1/order-items`, not `/v1/orderItems`.
- Keep URLs shallow — maximum 3 levels of nesting. Use query parameters or separate endpoints beyond that.

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

## API Versioning

- Version in the URL path: `/v1/users`, `/v2/users`.
- Increment the major version only for breaking changes.
- Support the previous version for a documented deprecation period.
- Include a deprecation header when the old version is still active:
  ```
  Sunset: Sat, 01 Mar 2025 00:00:00 GMT
  Deprecation: true
  ```

## Error Response Format

All errors must follow a consistent structure:

```json
{
  "error": "Human-readable error message",
  "code": "VALIDATION_ERROR",
  "status": 422,
  "details": [
    {
      "field": "email",
      "message": "Must be a valid email address"
    }
  ],
  "requestId": "req-abc-123"
}
```

- Always include a machine-readable `code` for client-side error handling.
- Include `requestId` for support and debugging.
- Never expose stack traces, internal paths, or implementation details in production error responses.
- Use appropriate HTTP status codes:
  - `400` — Bad request (malformed syntax)
  - `401` — Unauthorized (not authenticated)
  - `403` — Forbidden (authenticated but not authorized)
  - `404` — Not found
  - `409` — Conflict (duplicate, state conflict)
  - `422` — Unprocessable entity (validation failure)
  - `429` — Too many requests (rate limited)
  - `500` — Internal server error (unexpected failure)

## Input Validation

- Validate **all** request inputs using a schema validation library (Zod, Joi, Yup):
  ```typescript
  const CreateOrderSchema = z.object({
    productId: z.string().uuid(),
    quantity: z.number().int().min(1).max(100),
    shippingAddress: z.object({
      street: z.string().min(1).max(200),
      city: z.string().min(1).max(100),
      zipCode: z.string().regex(/^\d{5}(-\d{4})?$/),
      country: z.string().length(2),
    }),
  });
  ```
- Validate at the API boundary (controller/route handler), not deep in business logic.
- Return all validation errors at once, not one at a time.
- Strip unknown fields from validated input — do not pass unexpected data downstream.

## Pagination

### Cursor-Based (Preferred)

Use cursor-based pagination for large or real-time datasets:

```json
{
  "data": [...],
  "pagination": {
    "nextCursor": "eyJpZCI6MTAwfQ==",
    "hasMore": true,
    "limit": 25
  }
}
```

### Offset-Based (Simple Cases)

Acceptable for small, stable datasets:

```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "pageSize": 25,
    "totalItems": 150,
    "totalPages": 6
  }
}
```

- Default page size: 25. Maximum: 100. Allow clients to specify via `?limit=` parameter.
- Always return pagination metadata in the response.

## Rate Limiting

- Apply rate limits to all public endpoints.
- Stricter limits on authentication endpoints (login, password reset).
- Return rate limit information in response headers:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1672531200
  ```
- Return `429 Too Many Requests` with a `Retry-After` header when limits are exceeded.

## Response Conventions

- Wrap collections in a `data` field: `{ "data": [...], "pagination": {...} }`.
- Return the created/updated resource in the response body for POST, PUT, PATCH.
- Use consistent date format: ISO 8601 (`2024-01-15T09:30:00Z`).
- Use camelCase for JSON response keys.
- Include `Location` header for POST (201) responses pointing to the new resource.

## Health Check Endpoint

Every service must expose:

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.2.0",
  "uptime": 86400,
  "dependencies": {
    "database": "healthy",
    "cache": "healthy",
    "queue": "degraded"
  }
}
```
