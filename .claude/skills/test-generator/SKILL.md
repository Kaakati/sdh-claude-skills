---
name: test-generator
description: Generate comprehensive test suites including unit, integration, and E2E tests following AAA pattern. Use this skill whenever someone asks to write tests, generate specs, improve coverage, add test cases, or says things like "write tests for this", "add test coverage", "generate specs", "I need tests for X", "create a test suite", or "help me test this function". Also trigger when someone mentions flaky test investigation, test infrastructure setup, or mock strategy questions.
agent: test-generator
context: fork
argument-hint: "file path or module name"
model: sonnet
---

# Test Generator

Generate well-structured, maintainable test suites that provide confidence in code correctness. Follow the test pyramid approach: many unit tests, fewer integration tests, minimal E2E tests.

## Test Generation Workflow

### Step 1: Analyze the Code Under Test

1. Read the source file(s) to understand functionality.
2. Identify all public functions, methods, and exported interfaces.
3. Map code paths — branches, loops, error handlers, early returns.
4. Identify external dependencies — APIs, databases, file system, third-party services.
5. Note any existing tests to avoid duplication and maintain consistency.

### Step 2: Identify Test Cases

For each function or method, identify:

#### Happy Path Cases
- Standard inputs producing expected outputs.
- Common use cases as described in requirements or documentation.

#### Edge Cases
- **Null/undefined/empty inputs**: What happens with no data?
- **Boundary values**: Minimum, maximum, zero, negative numbers, empty strings, single-character strings.
- **Type boundaries**: Integer overflow, floating point precision, very long strings.
- **Collection edges**: Empty array, single element, very large collections.
- **Concurrent access**: Race conditions, simultaneous modifications.

#### Error Cases
- Invalid input types or formats.
- Missing required fields.
- External service failures (network errors, timeouts, 5xx responses).
- Permission/authorization failures.
- Resource not found scenarios.
- Data constraint violations (unique, foreign key, validation).

#### State Transitions
- Before/after states for mutations.
- Idempotency verification — calling twice produces the same result.
- Order-dependent behavior.

### Step 3: Write Tests Using AAA Pattern

Every test follows **Arrange, Act, Assert**:

```
// Arrange — set up test data, mocks, and preconditions
// Act — execute the function or operation under test
// Assert — verify the outcome matches expectations
```

#### Test Structure Rules

1. **One assertion concept per test** — a test should verify one behavior. Multiple `expect` calls are fine if they verify the same logical assertion.
2. **Descriptive test names**: `should [expected behavior] when [condition/context]`
3. **No test logic** — no conditionals, loops, or try/catch in tests. If you need them, the test is too complex.
4. **Independent tests** — no shared mutable state, no execution order dependencies.
5. **Fast tests** — unit tests should run in milliseconds. Mock external dependencies.

### Step 4: Apply Mocking Strategy

#### When to Mock
- External HTTP APIs and services.
- Database connections and queries.
- File system operations.
- Time-dependent operations (`Date.now()`, timers).
- Random number generation.
- Environment variables and configuration.

#### When NOT to Mock
- The code under test itself.
- Pure utility functions with no side effects.
- Value objects and data structures.
- Simple internal collaborators that are fast and deterministic.

#### Mock Quality Rules
- Mocks should match the real interface — use type-safe mocks when possible.
- Verify mock interactions only when the interaction IS the behavior (e.g., "sends an email").
- Prefer stubs (return values) over mocks (verify calls) for dependencies that provide data.
- Reset mocks between tests to prevent state leakage.

### Step 5: Generate Tests by Type

#### Unit Tests
- Test individual functions and methods in isolation.
- Mock all external dependencies.
- Focus on logic, calculations, transformations, validations.
- Target: cover all code paths including error branches.

```
describe('calculateDiscount', () => {
  it('should apply 10% discount for orders over $100', () => {
    const order = createOrder({ subtotal: 150 });
    const result = calculateDiscount(order);
    expect(result).toBe(15);
  });

  it('should return 0 discount for orders under $100', () => {
    const order = createOrder({ subtotal: 50 });
    const result = calculateDiscount(order);
    expect(result).toBe(0);
  });

  it('should throw when order subtotal is negative', () => {
    const order = createOrder({ subtotal: -10 });
    expect(() => calculateDiscount(order)).toThrow('Invalid subtotal');
  });
});
```

#### Integration Tests
- Test interactions between modules or services.
- Use real implementations for internal dependencies, mock external boundaries.
- Verify data flows correctly through the system.
- Test database queries against a test database (not mocked).

```
describe('UserService.createUser', () => {
  it('should create user and send welcome email', async () => {
    const emailService = createMockEmailService();
    const service = new UserService(testDatabase, emailService);

    const user = await service.createUser({ name: 'Jane', email: 'jane@example.com' });

    expect(user.id).toBeDefined();
    const savedUser = await testDatabase.users.findById(user.id);
    expect(savedUser.name).toBe('Jane');
    expect(emailService.sendWelcome).toHaveBeenCalledWith('jane@example.com');
  });
});
```

#### E2E Tests
- Test complete user workflows through the full stack.
- Use real services (or dedicated test instances).
- Focus on critical business paths — registration, checkout, core CRUD operations.
- Keep the number small — these are slow and expensive.

### Step 6: Coverage Guidance

| Test Type | Coverage Target | Focus |
|---|---|---|
| Unit | 80%+ line coverage | Business logic, calculations, validations |
| Integration | Critical paths covered | Service interactions, data persistence |
| E2E | Core workflows covered | User-facing flows, happy paths |

**Coverage is a guide, not a goal.** 80% meaningful coverage is better than 100% coverage with trivial assertions. Focus on:
- Code with complex logic or many branches.
- Code that handles money, permissions, or sensitive data.
- Code that has broken before (regression tests).

Skip testing:
- Simple getters/setters with no logic.
- Framework-generated boilerplate.
- Configuration objects with no behavior.

## Test File Organization

```
mobile/src/
  services/
    user-service.ts
    user-service.test.ts          # Unit tests colocated
mobile/tests/
  integration/
    user-service.integration.ts   # Integration tests separate
  e2e/
    user-registration.e2e.ts      # E2E tests separate
  fixtures/
    users.ts                      # Shared test data factories
  helpers/
    test-database.ts              # Test infrastructure utilities
```

### Web Frontend Tests (Vitest + React Testing Library)

#### Component Tests (Vite SPA + Next.js Client Components)
```tsx
// web/src/components/OrderTable.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { OrderTable } from './OrderTable';
import { createQueryWrapper } from '../../tests/utils';

describe('OrderTable', () => {
  it('should render order rows when orders are provided', () => {
    // Arrange
    const orders = [{ id: '1', status: 'pending', totalAmount: 100 }];

    // Act
    render(<OrderTable orders={orders} />, { wrapper: createQueryWrapper() });

    // Assert
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('pending')).toBeInTheDocument();
  });

  it('should show empty state when no orders exist', () => {
    render(<OrderTable orders={[]} />, { wrapper: createQueryWrapper() });
    expect(screen.getByText(/no orders/i)).toBeInTheDocument();
  });
});
```

#### Query Priority (React Testing Library)
Use this order: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`.

#### TanStack Query Hook Tests with MSW
```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../../tests/msw-server';
import { useOrders } from '../orders';
import { createQueryWrapper } from '../../tests/utils';

describe('useOrders', () => {
  it('should fetch orders from the API', async () => {
    // Arrange
    server.use(
      http.get('*/api/v1/orders', () => HttpResponse.json([{ id: '1', status: 'pending' }])),
    );

    // Act
    const { result } = renderHook(() => useOrders(), { wrapper: createQueryWrapper() });

    // Assert
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(1);
  });
});
```

#### Next.js Server Component Tests
Test Server Components as async functions — call and assert on returned JSX:

```tsx
import { describe, it, expect, vi } from 'vitest';
import OrdersPage from '@/app/orders/page';

vi.mock('@/api/client', () => ({
  railsApi: { get: vi.fn().mockResolvedValue([{ id: '1', status: 'pending' }]) },
}));

describe('OrdersPage (Server Component)', () => {
  it('should fetch and render orders', async () => {
    // Act — call as async function
    const page = await OrdersPage();

    // Assert — Server Component returns JSX
    expect(page).toBeTruthy();
  });
});
```

#### Next.js Server Action Tests
Test server actions as async functions with FormData:

```tsx
import { describe, it, expect, vi } from 'vitest';
import { createOrder } from '@/actions/orders';

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }));
vi.mock('next/navigation', () => ({ redirect: vi.fn() }));

describe('createOrder', () => {
  it('should return validation errors for invalid input', async () => {
    // Arrange
    const formData = new FormData();

    // Act
    const result = await createOrder(null, formData);

    // Assert
    expect(result?.errors?.customerName).toBeDefined();
  });
});
```

#### Test Wrapper Utility
```tsx
// tests/utils.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

export function createQueryWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{children}</BrowserRouter>
    </QueryClientProvider>
  );
}
```

## Output

When generating tests, provide:
1. The complete test file(s) with all test cases.
2. Any required test fixtures or factories.
3. A brief summary of what is covered and any known gaps.
4. Setup instructions if new test infrastructure is needed.
