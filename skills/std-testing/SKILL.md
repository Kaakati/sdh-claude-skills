---
name: std-testing
description: Testing standards — AAA pattern, naming, mocking, coverage targets, Vitest + RTL, edge cases. Use when writing tests or test infrastructure.
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/tests/**"
  - "**/spec/**"
  - "**/__tests__/**"
---

# Testing Standards

Rules for writing and maintaining tests. Quality tests are as important as quality code.

## AAA Pattern

Structure every test with Arrange, Act, Assert, separated by blank lines:

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

## Test Naming

Pattern: `should [expected behavior] when [condition]`. `describe` blocks name the unit under test.

```typescript
// Good
"should throw NotFoundError when user does not exist"
"should return paginated results when page parameter is provided"

// Bad
"test user"  "works correctly"  "error case"
```

```typescript
describe("UserService", () => {
  describe("getProfile", () => {
    it("should return user profile when valid ID is provided", ...);
    it("should throw NotFoundError when user does not exist", ...);
  });
});
```

## One Assertion Concept Per Test

- Each test verifies one logical concept, not one literal assertion.
- Multiple related assertions on the same result are fine (status code + response body).
- If a test needs a second "Arrange" for a second check, it is a second test.

## Test Independence

- Every test must pass in isolation and in any order. No interdependency.
- No shared mutable state. `beforeEach` for setup, never `beforeAll` with mutation.
- Each test builds its own data — use factory functions/builders with overrides
  (`buildUser({ role: "admin" })`, `create(:customer, :member)`).

## Mocking Strategy

- **Mock external dependencies**: databases, APIs, file systems, email services, third-party SDKs.
- **Do not mock internal logic.** If you must mock internal functions to test a unit, the design
  needs refactoring — inject the dependency instead.
- Prefer stubs and fakes over complex mock chains. Painful mocking is a design signal.
- Reset mocks between tests: `beforeEach(() => vi.clearAllMocks())`.

## Coverage Targets

- **Business logic**: 80% minimum — services, domain models, validators, utilities.
- **Overall project**: 60% minimum — including infrastructure, config, glue code.
- **Critical paths**: 100% target — authentication, authorization, payments, data validation.
- Coverage is a floor, not a ceiling. Focus on **branch** coverage, not line coverage. High coverage
  with weak assertions is worse than moderate coverage with meaningful tests.

## Test Types

- **Unit**: fast, isolated, no I/O. One module. The base of the pyramid — many of these.
- **Integration**: real DB / real router across modules. Some of these.
- **E2E**: complete user flows, critical paths only. Slow and brittle by nature — few of these.
- **Contract**: validate API contracts at service boundaries (Pact or similar).

## Edge Cases

Every suite covers all five: **null/undefined**, **empty** (string/array/zero), **boundary**
(min/max, pagination and length limits), **error paths** (network failure, invalid data,
unauthorized, timeout), and **concurrency** where applicable.

## Anti-Patterns to Avoid

- **Testing implementation details** — test behavior, not internal calls or private state.
- **Snapshot overuse** — snapshots hide intent and fail on cosmetic changes. Use sparingly.
- **Flaky tests** — fix or delete immediately. A flaky test is worse than no test.
- **Commented-out tests** — delete them; version control keeps history.
- **Testing framework code** — do not test that your ORM saves or your HTTP library sends requests.

## Deep guides (read on demand, do not preload)

- Unit vs integration, mock boundaries, test data builders, edge-case matrix, Sidekiq jobs → `references/test-strategy.md`
- Vitest + RTL setup, query priority, userEvent, MSW, providers, Zustand, Framer Motion, ApexCharts → `references/react-components.md`
- Next.js Server Components, server actions, `generateMetadata`, route handlers → `references/nextjs-server.md`
- React Native: RNTL, navigation, Reanimated, MMKV, Centrifugo → `references/react-native.md`
