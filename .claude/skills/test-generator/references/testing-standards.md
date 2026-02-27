# Testing Standards

Standards and conventions for all tests in the project. Follow these to ensure consistency, reliability, and maintainability of the test suite.

---

## Test Naming Conventions

### Test Files
- Unit tests: `<module-name>.test.ts` (colocated with source)
- Integration tests: `<module-name>.integration.ts` (in `tests/integration/`)
- E2E tests: `<workflow-name>.e2e.ts` (in `tests/e2e/`)

### Test Suites (describe blocks)
- Use the class or module name: `describe('UserService', ...)`
- Nest for methods: `describe('createUser', ...)`
- Nest for context: `describe('when user already exists', ...)`

### Test Cases (it/test blocks)
- Format: `should [expected behavior] when [condition]`
- Examples:
  - `should return user when valid ID is provided`
  - `should throw NotFoundError when user does not exist`
  - `should send welcome email after successful registration`
- Do not prefix with "it should" — the `it` function provides the prefix.

---

## Test Structure: AAA Pattern

Every test follows Arrange-Act-Assert with clear visual separation:

```typescript
it('should calculate total with tax', () => {
  // Arrange
  const items = [createItem({ price: 100 }), createItem({ price: 50 })];
  const taxRate = 0.08;

  // Act
  const total = calculateTotal(items, taxRate);

  // Assert
  expect(total).toBe(162);
});
```

Rules:
- One logical assertion per test (multiple `expect` calls verifying the same concept are acceptable).
- No logic in tests: no `if`, `for`, `while`, `try/catch`, or ternary operators.
- No shared mutable state between tests.

---

## Fixture Patterns

### Test Data Factories

Use factory functions to create test data with sensible defaults and optional overrides:

```typescript
// tests/fixtures/users.ts
export function createUser(overrides: Partial<User> = {}): User {
  return {
    id: faker.string.uuid(),
    name: faker.person.fullName(),
    email: faker.internet.email(),
    role: 'member',
    createdAt: new Date('2024-01-01'),
    ...overrides,
  };
}

// Usage in tests
const admin = createUser({ role: 'admin' });
const newUser = createUser({ createdAt: new Date() });
```

### Fixture Rules
- Factories live in `tests/fixtures/` organized by entity.
- Every factory has sensible defaults — tests only override what they care about.
- Use a library like `faker` for realistic but non-PII data.
- Date values in factories should be deterministic (fixed dates, not `new Date()`).
- IDs should be generated, not hardcoded, unless the test specifically depends on a known ID.

---

## Mock / Stub / Spy Guidance

### Definitions
- **Stub**: Returns predefined data. Use when the dependency provides data to the code under test.
- **Mock**: Verifies interactions. Use when the interaction IS the behavior being tested (sending email, publishing event).
- **Spy**: Wraps real implementation, records calls. Use when you want real behavior but need to verify it was called.

### When to Use Each

| Scenario | Use | Example |
|---|---|---|
| Database returning data | Stub | `db.findUser.mockResolvedValue(user)` |
| Sending notification | Mock | `expect(notifier.send).toHaveBeenCalledWith(...)` |
| Logging behavior | Spy | `jest.spyOn(logger, 'info')` |
| Time-dependent code | Stub | `jest.useFakeTimers()` |
| External HTTP API | Stub | `nock('https://api.example.com').get('/users').reply(200, [...])` |

### Mock Quality Rules
1. Mock at the boundary, not deep inside the system.
2. Mock interfaces/contracts, not implementations.
3. Type-safe mocks — the mock should satisfy the same interface as the real dependency.
4. Reset mocks in `beforeEach` or `afterEach` to prevent test pollution.
5. Avoid mocking what you do not own — wrap third-party libs in your own adapter, then mock that.

---

## Test Data Management

### Database Tests
- Each test suite sets up and tears down its own data.
- Use transactions that roll back after each test for speed.
- Never depend on data from other test suites.
- Use a dedicated test database, never the development or production database.

### File System Tests
- Use a temporary directory created per test suite.
- Clean up after the suite completes.
- Use `os.tmpdir()` or the test framework's temp directory support.

### API Tests
- Use `nock`, `msw`, or similar to intercept HTTP requests.
- Record and replay real responses for complex integrations.
- Verify that mocked responses match the actual API schema.

---

## CI Integration Requirements

### Test Execution
- All tests run on every pull request before merge.
- Unit tests run first (fast feedback), then integration, then E2E.
- Tests must pass with a zero-failure policy — no "known failures" or skipped tests without a tracking ticket.

### Test Environment
- CI uses a dedicated test database provisioned per run.
- Environment variables for test configuration come from CI secrets, not hardcoded values.
- Test containers (Docker) used for database and service dependencies.

### Reporting
- Coverage reports generated on every CI run.
- Coverage thresholds enforced: overall 80% line coverage minimum.
- Test results published as PR comments or CI artifacts.
- Slow tests (>5s) flagged for investigation.

---

## Flaky Test Handling

A test is flaky if it passes and fails without code changes. Flaky tests erode trust in the test suite.

### Prevention
- No `sleep` or fixed timeouts — use polling with a reasonable max wait.
- No dependencies on external services in unit tests — mock everything external.
- No test order dependencies — each test sets up its own state.
- No shared mutable state — use `beforeEach` to reset.
- No reliance on system clock — use fake timers.

### When a Flaky Test is Found
1. **Immediately quarantine**: Move to a `flaky/` directory or mark with `@flaky` tag.
2. **Create a ticket**: Track it with high priority — flaky tests are bugs.
3. **Investigate root cause**: Run the test 50-100 times in isolation to reproduce.
4. **Fix or rewrite**: Fix the root cause. If the test design is fundamentally flawed, rewrite it.
5. **Verify**: Run the fixed test 100 times to confirm stability before removing quarantine.

### Common Causes
- Race conditions in async code.
- Time-sensitive assertions without tolerance.
- Port conflicts or resource contention.
- Uncontrolled randomness (use seeded random in tests).
- Network-dependent tests without mocking.
