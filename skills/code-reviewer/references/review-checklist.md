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

## Navigation (web and mobile)

- [ ] The global sidebar renders areas only (optional static group labels) — no `SidebarMenuSub`, section tree, collapsible group, or recursive renderer over `children`; sections render in the area's own layout.
- [ ] The active area comes from `areaState(pathname, area)` — whole path segments plus the area's `match` prefixes — never a bare `pathname.startsWith(href)`.
- [ ] Nav items come from `visibleNav(NAV, ability, entitlements)`, never a hardcoded `navItems` array.
- [ ] A feature reached by URL without its permission renders the no-access page; `notFound()` is reserved for records outside the caller's scope.
- [ ] Breadcrumbs render the detail's `ancestors` — never browser history, the referrer, or URL segments.
- [ ] Filters, sort, and query live in the URL; Up is a real link, never `history.back()`; Phlex frame navigation between levels carries `data-turbo-action="advance"`.
- [ ] Charts use the stack's library: the shadcn chart component (Next.js), `react-chartjs-2` with an explicit registration module (Vite SPA), or the house Stimulus controller on `chart.js` (Rails views) — never ApexCharts.

Rules: `../ui-ux-patterns/references/drill-down-navigation.md` and `../access-control-designer/references/ui-gates.md`. Charts: `../std-shadcn-ui/references/charts.md`, `../std-reactjs/references/charts.md`, `../std-phlex-conventions/references/charts.md`.

## Drill-down APIs

- [ ] Collection routes nest one level under the resource's one canonical parent; member routes are flat by ID.
- [ ] A nested `index` loads the parent through its policy scope; a flat member lookup scopes the child itself — out of scope answers 404.
- [ ] A detail's `ancestors` pass each ancestor's read policy and load in one query, never one per parent.
- [ ] Overview counts are computed within the caller's scope; a cached counter is shown only to `org`-scoped callers.
- [ ] The query count per level is pinned in a test.
- [ ] ETags on scoped levels vary by viewer and `permissions_version`; no scoped level is cached `public`.
- [ ] A same-type tree uses the storage its ADR records; recursive queries carry a cycle guard and a depth cap.

Contract: `../std-api-design/references/drill-down-resources.md`. Tree storage: `../std-database/references/hierarchies.md`.

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
