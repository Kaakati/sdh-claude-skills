---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/tests/**"
  - "web/src/**"
  - "next/src/**"
  - "next/app/**"
---

# Testing Standards

Rules for writing and maintaining tests. Quality tests are as important as quality code.

## AAA Pattern

Structure every test with Arrange, Act, Assert:

```typescript
it("should return user profile when valid ID is provided", async () => {
  // Arrange
  const userId = "user-123";
  const expectedUser = { id: userId, name: "Jane Doe", email: "jane@example.com" };
  mockUserRepo.findById.mockResolvedValue(expectedUser);

  // Act
  const result = await userService.getProfile(userId);

  // Assert
  expect(result).toEqual(expectedUser);
  expect(mockUserRepo.findById).toHaveBeenCalledWith(userId);
});
```

Separate the three sections with blank lines for readability.

## One Assertion Concept Per Test

- Each test should verify one logical concept, not one literal assertion.
- Multiple related assertions on the same result are fine (e.g., checking status code and response body).
- If a test needs a separate "Arrange" for a second check, it should be a separate test.

## Test Naming

Use the pattern: `should [expected behavior] when [condition]`

```typescript
// Good
"should throw NotFoundError when user does not exist"
"should return paginated results when page parameter is provided"
"should send welcome email when user registration succeeds"

// Bad
"test user"
"works correctly"
"error case"
```

For `describe` blocks, use the unit under test:

```typescript
describe("UserService", () => {
  describe("getProfile", () => {
    it("should return user profile when valid ID is provided", ...);
    it("should throw NotFoundError when user does not exist", ...);
  });
});
```

## Mocking Strategy

- **Mock external dependencies**: databases, APIs, file systems, email services, third-party SDKs.
- **Do not mock internal logic**: If you need to mock internal functions to test a unit, the design may need refactoring.
- **Use dependency injection** to make mocking straightforward.
- **Reset mocks** between tests to prevent state leakage:
  ```typescript
  beforeEach(() => {
    jest.clearAllMocks();
  });
  ```
- Prefer test doubles (stubs, fakes) over complex mock chains. If mocking becomes painful, simplify the code under test.

## Edge Cases

Every test suite must cover these categories:

- **Null/undefined inputs**: What happens when optional values are missing?
- **Empty values**: Empty strings, empty arrays, zero values.
- **Boundary values**: Min/max of ranges, pagination limits, string length limits.
- **Error paths**: Network failures, invalid data, unauthorized access, timeout scenarios.
- **Concurrent operations**: Race conditions where applicable.

```typescript
describe("validateAge", () => {
  it("should accept minimum valid age of 0", ...);
  it("should accept maximum valid age of 150", ...);
  it("should reject negative age", ...);
  it("should reject age above 150", ...);
  it("should reject null input", ...);
  it("should reject non-numeric input", ...);
});
```

## Test Independence

- **No test interdependency**. Each test must pass when run in isolation and in any order.
- Do not share mutable state between tests. Use `beforeEach` for setup, not `beforeAll` with mutation.
- Avoid relying on test execution order.
- Each test should create its own test data. Use factory functions or builders for complex objects:
  ```typescript
  function buildUser(overrides?: Partial<User>): User {
    return {
      id: "user-123",
      name: "Test User",
      email: "test@example.com",
      role: "user",
      ...overrides,
    };
  }
  ```

## Coverage Targets

- **Business logic**: 80% minimum — services, domain models, validators, utilities.
- **Overall project**: 60% minimum — includes infrastructure, config, and glue code.
- **Critical paths**: 100% target — authentication, authorization, payment processing, data validation.
- Coverage is a floor, not a ceiling. High coverage with weak assertions is worse than moderate coverage with meaningful tests.
- Focus on branch coverage, not just line coverage.

## Test Types

- **Unit tests**: Fast, isolated, no I/O. Test one module at a time. These form the base of the pyramid.
- **Integration tests**: Test interactions between modules or with real databases/APIs. Use test containers or in-memory databases.
- **E2E tests**: Test complete user flows. Keep these minimal and focused on critical paths. They are slow and brittle by nature.
- **Contract tests**: Validate API contracts between services. Use Pact or similar tools for service boundaries.

## Web Frontend Testing (Vitest + React Testing Library)

### Vitest Configuration
- Use Vitest for all web frontend tests (Vite SPA and Next.js) — Jest-compatible API with native Vite support.
- Configure in `vitest.config.ts` with `@testing-library/jest-dom` matchers.
- Use `jsdom` or `happy-dom` environment for component tests.
- Co-locate test files: `Component.tsx` → `Component.test.tsx`.

### React Testing Library Query Priority
Follow this priority order — prefer accessible queries that reflect how users interact:
1. `getByRole` — best; queries by ARIA role (button, heading, textbox)
2. `getByLabelText` — for form elements with associated labels
3. `getByPlaceholderText` — when labels are not visible
4. `getByText` — for non-interactive elements
5. `getByTestId` — last resort; use only when no semantic query applies

### Testing React Components
- Test user behavior, not implementation details.
- Use `userEvent` (not `fireEvent`) for realistic user interactions.
- Mock API calls with MSW (Mock Service Worker), not manual mocks.
- Wrap components with test providers (QueryClient, Router, i18n) via a shared `renderWithProviders` utility.

### Next.js Server Component Testing
- Test Server Components as async functions — call the component, assert on the returned JSX.
- Mock `fetch` or the Rails API client at the module level.
- Test `generateMetadata` functions separately for SEO validation.

### Next.js Server Action Testing
- Test server actions as async functions with `FormData` input.
- Mock `revalidatePath`, `revalidateTag`, and `redirect` from `next/cache` and `next/navigation`.
- Assert on validation error return shape for invalid inputs.
- Assert on side effects (API calls, revalidation) for valid inputs.

## Anti-Patterns to Avoid

- **Testing implementation details**: Test behavior, not internal method calls or state.
- **Snapshot overuse**: Use snapshots sparingly. They hide intent and fail on cosmetic changes.
- **Flaky tests**: Fix or delete flaky tests immediately. A flaky test is worse than no test.
- **Commented-out tests**: Delete them. Version control keeps history.
- **Testing framework code**: Do not test that your ORM saves data or your HTTP library sends requests.
