# Code Review Checklist

Use this checklist during every code review. Not every item applies to every PR — focus on items relevant to the change.

---

## Correctness

- [ ] Code implements the specified requirements accurately.
- [ ] Edge cases are handled: null values, empty collections, boundary conditions.
- [ ] Off-by-one errors checked in loops and array indexing.
- [ ] Race conditions considered in concurrent or async code.
- [ ] State mutations are intentional and controlled — no accidental side effects.
- [ ] Return values and error codes are checked and handled.
- [ ] Type conversions are explicit and safe — no implicit coercions that could lose data.
- [ ] Backwards compatibility maintained unless a breaking change is intentional and documented.

## Security

- [ ] No hardcoded secrets, tokens, API keys, or passwords in code or config files.
- [ ] User input is validated on the server side, not only on the client.
- [ ] SQL queries use parameterized statements or an ORM — no string concatenation.
- [ ] Authentication is enforced on all protected endpoints.
- [ ] Authorization checks verify the user has permission for the specific resource.
- [ ] Sensitive data (PII, credentials) is not logged or included in error responses.
- [ ] File uploads validate type, size, and content — not just the file extension.
- [ ] CORS configuration is restrictive — not using wildcard origins in production.

## Performance

- [ ] No N+1 query patterns — use eager loading, batch fetching, or data loaders.
- [ ] Database queries use appropriate indexes for the access patterns.
- [ ] Expensive computations are not repeated unnecessarily — use caching or memoization.
- [ ] Large data sets use pagination, cursors, or streaming — not loading everything into memory.
- [ ] No blocking operations on the main thread or event loop.
- [ ] API responses return only necessary fields — no over-fetching.
- [ ] Assets (images, scripts, styles) are optimized and properly cached.

## Maintainability

- [ ] Functions and methods have a single clear responsibility.
- [ ] Cyclomatic complexity is below 10 per function.
- [ ] Nesting depth does not exceed 3 levels.
- [ ] No code duplication — shared logic is extracted into reusable functions.
- [ ] Magic numbers and strings are replaced with named constants.
- [ ] Dependencies between modules are explicit and minimal.
- [ ] Code follows established project patterns — not introducing new patterns without discussion.
- [ ] No dead code, unreachable branches, or commented-out blocks.

## Testing

- [ ] New code has corresponding unit tests.
- [ ] Tests cover both the happy path and error/edge cases.
- [ ] Test names clearly describe the scenario: `should [expected behavior] when [condition]`.
- [ ] Tests are independent — no shared mutable state or execution order dependencies.
- [ ] Mocks and stubs are used for external dependencies (APIs, databases, file system).
- [ ] Integration tests exist for critical workflows and service boundaries.
- [ ] Test data is realistic but does not use production data or PII.

## Documentation

- [ ] Public APIs (functions, classes, endpoints) have documentation.
- [ ] Complex business logic or algorithms have explanatory comments.
- [ ] README or setup docs updated if development workflow changes.
- [ ] API documentation (OpenAPI, GraphQL schema) updated for endpoint changes.
- [ ] Breaking changes documented with migration instructions.
- [ ] Environment variables and configuration options documented with defaults.
