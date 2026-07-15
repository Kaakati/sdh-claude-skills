---
name: api-designer
description: Design and review REST APIs for consistency, standards compliance, and developer experience. Use this skill whenever someone asks to design an API, create endpoints, review API contracts, generate OpenAPI specs, or says things like "design the API for X", "review this endpoint", "what should the API look like", "create a REST interface", "write the OpenAPI spec", or "check my API design". Also trigger when someone mentions pagination strategy, error response format, API versioning, or rate limiting design.
model: sonnet
---

# API Designer

Design, review, and document APIs that are consistent, intuitive, and maintainable. Follow REST conventions for resource-oriented APIs and GraphQL best practices for query-based APIs.

## API Design Workflow

### Step 1: Identify Resources and Operations

1. List the primary resources (nouns) the API exposes.
2. Map CRUD and business operations to HTTP methods.
3. Define relationships between resources (one-to-many, many-to-many).
4. Identify sub-resources vs. top-level resources.
5. Determine which operations are idempotent.

### Step 2: Define URL Structure

#### Conventions
- Use lowercase with hyphens for multi-word paths: `/user-profiles`, not `/userProfiles`.
- Use plural nouns for collections: `/users`, `/orders`, `/products`.
- Use resource IDs for specific items: `/users/{userId}`.
- Nest sub-resources only one level deep: `/users/{userId}/orders`.
- For deeper relationships, use query parameters or top-level resources.

#### HTTP Method Mapping

| Operation | Method | URL | Idempotent | Example |
|---|---|---|---|---|
| List | GET | `/resources` | Yes | GET /users |
| Read | GET | `/resources/{id}` | Yes | GET /users/123 |
| Create | POST | `/resources` | No | POST /users |
| Full Update | PUT | `/resources/{id}` | Yes | PUT /users/123 |
| Partial Update | PATCH | `/resources/{id}` | No* | PATCH /users/123 |
| Delete | DELETE | `/resources/{id}` | Yes | DELETE /users/123 |
| Action | POST | `/resources/{id}/{action}` | Varies | POST /orders/123/cancel |

*PATCH is not inherently idempotent, but implementations should aim for idempotency where possible.

#### URL Anti-Patterns to Avoid
- Verbs in URLs: `/getUsers`, `/createOrder` — use HTTP methods instead.
- Deeply nested resources: `/users/1/orders/2/items/3/reviews` — flatten to `/items/3/reviews`.
- Query parameters for resource identification: `/users?id=123` — use path parameters.
- Inconsistent pluralization: `/user/123` vs `/orders/456`.

### Step 3: Design Request and Response Schemas

#### Request Bodies
- Use JSON as the default content type.
- Include only fields the client should set — no server-generated fields (id, timestamps).
- Validate all fields with clear type constraints.
- Use enums for fields with a fixed set of values.
- Provide `example` values in the schema.

#### Response Bodies

Standard success response:
```json
{
  "data": {
    "id": "abc-123",
    "name": "Example",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

Collection response:
```json
{
  "data": [
    { "id": "abc-123", "name": "First" },
    { "id": "def-456", "name": "Second" }
  ],
  "pagination": { "nextCursor": "eyJpZCI6MTAwfQ==", "hasMore": true, "limit": 25 }
}
```

That is the **cursor** shape, which is the default (see Step 5). The offset shape —
`{ "page": 2, "pageSize": 25, "totalItems": 150, "totalPages": 6 }` — is for small, stable
datasets only. Both are pinned in `@skills/std-api-design/references/pagination-rails.md`.

#### Field Conventions
- Use `camelCase` for JSON field names.
- Dates and times in ISO 8601 format with timezone: `2024-01-15T10:30:00Z`.
- IDs are strings (UUIDs preferred) — not sequential integers exposed externally.
- Boolean fields prefixed with `is`, `has`, `can`: `isActive`, `hasAccess`.
- Monetary values include currency: `{ "amount": 1999, "currency": "USD" }` (minor units).
- Null fields may be omitted from responses unless the client needs to distinguish between null and absent.

### Step 4: Error Handling

#### Standard Error Format

Owned by `std-api-design` → `references/errors-rails.md` (Rails) and `references/errors-typescript.md`
(Next route handlers / Express). Both auto-load on controller and route work; this skill does not,
so **they are the contract and this is the summary**:

```json
{
  "error": "One or more fields failed validation.",
  "code": "VALIDATION_ERROR",
  "status": 422,
  "details": [
    { "field": "email", "message": "Must be a valid email address." }
  ],
  "requestId": "req-abc-123"
}
```

`error` is the human-readable string, `code` the stable machine-readable string a client
switches on, `status` the HTTP status repeated in the body, `details` an array (a validation
failure has an ordered list of them, and an object keyed by field cannot express two errors on
one field), `requestId` the value the client quotes and the operator greps for.

`api-design-checker.py` warns on a rendered error body missing `code` or `requestId`.

#### HTTP Status Code Usage

| Code | Meaning | When to Use |
|---|---|---|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST that creates a resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation errors, malformed request |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate resource, version conflict |
| 422 | Unprocessable Entity | Semantically invalid request |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server failure |

#### Error Code Registry
Maintain a registry of application error codes. Codes should be:
- Uppercase with underscores: `RESOURCE_NOT_FOUND`, `INSUFFICIENT_BALANCE`.
- Documented with description and resolution steps.
- Stable — do not change codes once published.

### Step 5: Pagination

Owned by `std-api-design`, which auto-loads on controller work. The load-bearing rules, restated
here because they change the *design* — not just the implementation:

- **Cursor-based pagination is the default.** Offset is acceptable only for small, stable datasets
  that are not appended to in real time. Offset is not "the simple one" — on an appended-to table
  it silently skips and repeats rows as the offsets shift under the reader.
- **Default page size 25, maximum 100**, client-settable via `?limit=`. **Always clamp** — an
  unbounded `limit` is a denial-of-service you shipped yourself.
- Collections are wrapped: `{ "data": [...], "pagination": {...} }` — **never a bare array**.
- Rails uses `pagy` (CLAUDE.md pins it). Do not hand-roll offset arithmetic; `pagy` avoids the
  N+1 count that hand-rolled pagination reintroduces.

Depth, with the bad/good pairs → `@skills/std-api-design/references/pagination-rails.md` (server)
and `@skills/std-api-design/references/pagination-clients.md` (consuming it).

### Step 6: Filtering and Sorting

#### Filtering
```
GET /users?status=active&role=admin
GET /orders?createdAfter=2024-01-01&createdBefore=2024-02-01
GET /products?priceMin=10&priceMax=100
```

- Use query parameters for filtering.
- Support common filter patterns: exact match, range (min/max, before/after), partial match (search).
- Document all supported filter parameters.

#### Sorting
```
GET /users?sort=createdAt:desc
GET /products?sort=price:asc,name:asc
```

- Format: `field:direction` (asc/desc).
- Support multiple sort fields separated by commas.
- Define a default sort order for each endpoint.

### Step 7: Versioning

URL path versioning (`/api/v1/users`). Increment the major only for breaking changes; adding a
field or an endpoint is not one. Support the current and previous version simultaneously.

The part that decides whether a version bump is even needed — what actually counts as breaking for
*your* clients, how to deprecate without stranding a mobile app you cannot force-update, and the
`Sunset`/`Deprecation` headers — is owned by
`@skills/std-api-design/references/versioning-and-deprecation.md`. Read it before promising a
timeline: a deprecation window is a commitment to people who have already shipped.

### Step 8: Authentication

- Use Bearer tokens in the `Authorization` header: `Authorization: Bearer <token>`.
- API keys for machine-to-machine auth in a custom header: `X-API-Key: <key>`.
- Do not pass authentication in query parameters — they are logged in many places.
- Include rate limit headers in responses:
  ```
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 95
  X-RateLimit-Reset: 1705312800
  ```

### Step 9: Documentation

For every API, generate or maintain:

1. **OpenAPI 3.x specification** — the source of truth.
2. **Quick start guide** — authentication, first API call, common workflows.
3. **Changelog** — dated list of additions, changes, deprecations.
4. **Error code reference** — all error codes with descriptions and resolutions.

## Output

When designing or reviewing an API, provide:
1. Resource and endpoint listing.
2. Request/response schemas with examples.
3. Error scenarios and codes.
4. Pagination and filtering parameters.
5. OpenAPI specification (if generating from scratch).

## Deep guides (read on demand, do not preload)

- URL structure, status codes, filtering/sorting, HATEOAS links, the OpenAPI template →
  `references/api-conventions.md`

The rest is owned by `std-api-design`, which **auto-loads** on controller and route work. Read the
one matching the decision — these carry the bad/good pairs, and this skill deliberately does not
restate them:

- **The error envelope, and rendering it in Rails** → `@skills/std-api-design/references/errors-rails.md`
- **Validating input and consuming errors in TypeScript** → `@skills/std-api-design/references/errors-typescript.md`
- **Paginating in Rails (`pagy`)** → `@skills/std-api-design/references/pagination-rails.md`
- **Consuming a paginated API** → `@skills/std-api-design/references/pagination-clients.md`
- **Versioning a breaking change, deprecation windows** → `@skills/std-api-design/references/versioning-and-deprecation.md`
- **Rate limiting** → `@skills/std-api-design/references/rate-limiting.md`
- **Health checks** → `@skills/std-api-design/references/health-checks.md`
