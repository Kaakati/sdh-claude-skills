# API Conventions

Comprehensive conventions for designing and implementing REST APIs. All new endpoints must follow these standards.

---

## URL Structure

### Base URL
```
https://api.{domain}.com/v{version}/{resource}
```

### Path Rules
- Lowercase only with hyphens for word separation: `/order-items`
- Plural nouns for collections: `/users`, `/invoices`
- Singular resource via ID: `/users/{userId}`
- Sub-resources nested one level: `/users/{userId}/orders`
- Actions as POST to a sub-path: `/orders/{orderId}/cancel`
- No trailing slashes: `/users` not `/users/`
- No file extensions: `/users` not `/users.json`

### Examples
```
GET    /api/v1/users                    # List users
POST   /api/v1/users                    # Create user
GET    /api/v1/users/{userId}           # Get user
PUT    /api/v1/users/{userId}           # Update user
DELETE /api/v1/users/{userId}           # Delete user
GET    /api/v1/users/{userId}/orders    # List user's orders
POST   /api/v1/orders/{orderId}/cancel  # Cancel order (action)
```

---

## Status Codes

### Success Codes

| Code | Name | Use |
|---|---|---|
| 200 | OK | Successful read, update, or action |
| 201 | Created | Resource created — include `Location` header |
| 202 | Accepted | Async operation accepted for processing |
| 204 | No Content | Successful delete or update with no response body |

### Client Error Codes

| Code | Name | Use |
|---|---|---|
| 400 | Bad Request | Malformed syntax, missing required field |
| 401 | Unauthorized | No valid authentication credentials |
| 403 | Forbidden | Valid credentials but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 405 | Method Not Allowed | HTTP method not supported on this endpoint |
| 409 | Conflict | Resource state conflict (duplicate, version mismatch) |
| 413 | Payload Too Large | Request body exceeds size limit |
| 422 | Unprocessable Entity | Valid syntax but semantically invalid |
| 429 | Too Many Requests | Rate limit exceeded — include `Retry-After` header |

### Server Error Codes

| Code | Name | Use |
|---|---|---|
| 500 | Internal Server Error | Unexpected server failure |
| 502 | Bad Gateway | Upstream service failure |
| 503 | Service Unavailable | Temporary overload or maintenance |
| 504 | Gateway Timeout | Upstream service timeout |

---

## Error Format

### Standard Error Response

The envelope is owned by `std-api-design` → `references/errors-rails.md` /
`references/errors-typescript.md`, which auto-load on controller and route work. Match them
exactly — a client cannot parse two shapes:

```json
{
  "error": "Human-readable description of what went wrong.",
  "code": "VALIDATION_ERROR",
  "status": 422,
  "details": [
    { "field": "email", "message": "Must be a valid email address." },
    { "field": "age", "message": "Must be between 0 and 150." }
  ],
  "requestId": "req-550e8400-e29b"
}
```

`error` is flat, not nested. A nested `error: { message: ... }` reads well but forces every
consumer — the fetch wrapper, the Sentry hook, the RN toast — to reach through a level for the
one field they all need, and it makes `error` mean two different things depending on the
endpoint that failed.

### Error Code Naming
- Uppercase with underscores: `RESOURCE_NOT_FOUND`
- Scoped to domain: `PAYMENT_INSUFFICIENT_FUNDS`, `AUTH_TOKEN_EXPIRED`
- Stable once published — never change the meaning of an existing code

### Common Error Codes
```
VALIDATION_ERROR          — One or more fields failed validation
RESOURCE_NOT_FOUND        — The requested resource does not exist
RESOURCE_ALREADY_EXISTS   — Conflict with existing resource
UNAUTHORIZED              — Authentication required
FORBIDDEN                 — Insufficient permissions
RATE_LIMIT_EXCEEDED       — Too many requests
INTERNAL_ERROR            — Unexpected server error
SERVICE_UNAVAILABLE       — Dependent service is down
```

---

## Pagination Patterns

Owned by `std-api-design`. Do not restate the shape here — this file already carried a third copy
of it, and the copies disagreed: the example below used `pageSize=20` while the owner pins
**default 25, maximum 100**. Three sources said 25, one said 20, and the odd one out was the
family a designer actually reads.

- **Cursor is the default**; offset only for small, stable, non-appended datasets.
- Default **25**, max **100**, via `?limit=` — always clamped server-side.
- Wrapped: `{ "data": [...], "pagination": {...} }`, never a bare array.

Server → `@skills/std-api-design/references/pagination-rails.md` (uses `pagy`; hand-rolled offset
arithmetic reintroduces the N+1 count `pagy` exists to avoid).
Client → `@skills/std-api-design/references/pagination-clients.md`.

## Filtering and Sorting

### Filtering
```
GET /products?category=electronics&priceMin=10&priceMax=500
GET /orders?status=shipped&createdAfter=2024-01-01
GET /users?search=john                  # Full-text search
GET /users?ids=abc,def,ghi              # Batch lookup
```

- Use query parameters for all filters.
- Range filters use `Min`/`Max` or `Before`/`After` suffixes.
- Search uses a `search` parameter for full-text queries.
- Batch lookups use comma-separated IDs.

### Sorting
```
GET /products?sort=price:asc
GET /products?sort=price:asc,name:desc
```

- Format: `field:direction`
- Multiple fields: comma-separated
- Default direction: ascending if unspecified
- Only allow sorting on indexed fields

---

## HATEOAS (Hypermedia Links)

Include links for discoverability in resource responses:

```json
{
  "data": {
    "id": "order-123",
    "status": "pending",
    "total": 4999
  },
  "links": {
    "self": "/api/v1/orders/order-123",
    "cancel": "/api/v1/orders/order-123/cancel",
    "items": "/api/v1/orders/order-123/items",
    "customer": "/api/v1/customers/cust-456"
  }
}
```

Include links when:
- Related resources exist.
- Actions are available based on current state.
- Navigation between collection pages.

---

## Rate Limiting

### Response Headers
```
X-RateLimit-Limit: 1000          # Requests allowed per window
X-RateLimit-Remaining: 950       # Requests remaining
X-RateLimit-Reset: 1705312800    # Unix timestamp when the window resets
Retry-After: 30                  # Seconds to wait (only on 429 responses)
```

### Default Limits
| Tier | Rate | Window |
|---|---|---|
| Unauthenticated | 60 requests | per hour |
| Authenticated | 1000 requests | per hour |
| API Key (service) | 5000 requests | per hour |

### Rate Limit Response
```json
HTTP/1.1 429 Too Many Requests
Retry-After: 30

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "retryAfter": 30
  }
}
```

---

## OpenAPI Specification Template

Minimal template for new endpoints:

```yaml
openapi: 3.1.0
info:
  title: Service Name API
  version: 1.0.0
  description: Brief service description.
  contact:
    name: API Support
    email: api-support@example.com

servers:
  - url: https://api.example.com/v1
    description: Production
  - url: https://api.staging.example.com/v1
    description: Staging

paths:
  /resources:
    get:
      summary: List resources
      operationId: listResources
      tags: [Resources]
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: pageSize
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceList'
    post:
      summary: Create resource
      operationId: createResource
      tags: [Resources]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateResourceRequest'
      responses:
        '201':
          description: Resource created
          headers:
            Location:
              schema:
                type: string
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ResourceResponse'
        '422':
          description: Validation error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

components:
  schemas:
    ResourceResponse:
      type: object
      properties:
        data:
          $ref: '#/components/schemas/Resource'
    Resource:
      type: object
      properties:
        id:
          type: string
          format: uuid
        name:
          type: string
        createdAt:
          type: string
          format: date-time
    ErrorResponse:
      type: object
      properties:
        error:
          type: object
          properties:
            code:
              type: string
            message:
              type: string
            details:
              type: array
              items:
                type: object
                properties:
                  field:
                    type: string
                  code:
                    type: string
                  message:
                    type: string
            requestId:
              type: string
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - bearerAuth: []
```
