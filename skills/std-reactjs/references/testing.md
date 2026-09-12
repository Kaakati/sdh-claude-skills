# Testing (Vitest + React Testing Library + MSW)

Load-bearing rules restated (hold even if you read nothing else):

1. **Test behaviour, not implementation.** Query priority: `getByRole` > `getByLabelText` >
   `getByText` > `getByTestId`.
2. **MSW mocks the network.** Never `vi.mock('axios')`, never mock your own query hooks.
3. **A fresh `QueryClient` per test**, retries off. Zustand stores reset between tests.
4. **Co-locate**: `Component.tsx` → `Component.test.tsx`. Coverage: **80% on business logic**
   (hooks, stores, schema transforms), **60% overall minimum**.

---

## Decision: what does the test render?

Anything using Query, Router, or i18n needs providers. Build one wrapper, use it everywhere.

```tsx
// tests/utils.tsx  ✅
import { render, type RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import type { ReactElement, ReactNode } from 'react';

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      // Retries turn a 500-path test into a 30-second timeout. Off in tests.
      queries: { retry: false, gcTime: Infinity, staleTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  { route = '/', ...options }: RenderOptions & { route?: string } = {},
) {
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) };
}

export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
```

**A fresh `QueryClient` per test is mandatory.** A shared one leaks cache between tests and you
get order-dependent failures that only reproduce in CI.

---

## Decision: how do I mock the API?

### Bad — mocking the module

```tsx
// ❌ tests the mock, not the app. Refactor axios→fetch and every test still passes while prod burns.
vi.mock('@/api/client', () => ({
  api: { get: vi.fn().mockResolvedValue({ data: { data: [{ id: '1' }] } }) },
}));

// ❌ worse: mocking your own hook. Now nothing verifies the query key, the params, or the parsing.
vi.mock('@/api/orders', () => ({ useOrders: () => ({ data: [{ id: '1' }], isPending: false }) }));
```

### Good — MSW at the network boundary

```ts
// tests/msw/handlers.ts  ✅
import { http, HttpResponse } from 'msw';

const API = import.meta.env.VITE_API_URL;

export const handlers = [
  http.get(`${API}/orders`, ({ request }) => {
    const status = new URL(request.url).searchParams.get('status');
    const orders = [
      { id: '1', reference: 'ORD-001', status: 'pending', quantity: 2 },
      { id: '2', reference: 'ORD-002', status: 'shipped', quantity: 5 },
    ];
    return HttpResponse.json({
      data: status && status !== 'all' ? orders.filter((o) => o.status === status) : orders,
    });
  }),

  http.post(`${API}/orders`, async ({ request }) => {
    const body = (await request.json()) as { reference: string };
    if (!body.reference) {
      // The std-api-design envelope — the same one the ApiError interceptor parses.
      return HttpResponse.json(
        {
          error: 'Validation failed',
          code: 'VALIDATION_ERROR',
          status: 422,
          details: [{ field: 'reference', message: 'is required' }],
          requestId: 'req-test-1',
        },
        { status: 422 },
      );
    }
    return HttpResponse.json({ data: { id: '3', ...body, status: 'pending' } }, { status: 201 });
  }),
];
```

```ts
// tests/setup.ts  ✅
import '@testing-library/jest-dom/vitest';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { handlers } from './msw/handlers';

export const server = setupServer(...handlers);

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  server.resetHandlers();   // per-test overrides never leak
  cleanup();
});
afterAll(() => server.close());
```

`onUnhandledRequest: 'error'` is deliberate: an unmocked call should fail loudly, not silently
hang.

```ts
// vite.config.ts (test block)
export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: false,
    coverage: { provider: 'v8', reporter: ['text', 'lcov'], thresholds: { lines: 60 } },
  },
});
```

---

## Decision: writing the assertion

### Bad — implementation details and container queries

```tsx
it('renders orders', async () => {
  const { container } = render(<Orders />);
  await new Promise((r) => setTimeout(r, 100));                       // ❌ arbitrary sleep
  expect(container.querySelector('.order-row')).toBeTruthy();         // ❌ couples to a class name
  expect(wrapper.find('OrderTable').props().orders).toHaveLength(2);  // ❌ inspects props
});
```

### Good — role queries, `findBy` for async, AAA structure

```tsx
// src/pages/Orders.test.tsx  ✅
import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { renderWithProviders, screen, userEvent } from '../../tests/utils';
import { server } from '../../tests/setup';
import Orders from './Orders';

describe('Orders page', () => {
  it('should list every order when the API returns results', async () => {
    // Arrange + Act
    renderWithProviders(<Orders />);

    // Assert — findBy* waits for the query to settle; no sleeps, no act() wrangling
    expect(await screen.findByRole('row', { name: /ORD-001/ })).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /ORD-002/ })).toBeInTheDocument();
  });

  it('should show an empty state when the API returns no orders', async () => {
    // Arrange — override just this test's handler
    server.use(http.get('*/orders', () => HttpResponse.json({ data: [] })));

    // Act
    renderWithProviders(<Orders />);

    // Assert
    expect(await screen.findByText(/no orders yet/i)).toBeInTheDocument();
  });

  it('should show an error state when the API fails', async () => {
    server.use(http.get('*/orders', () => new HttpResponse(null, { status: 500 })));

    renderWithProviders(<Orders />);

    expect(await screen.findByRole('alert')).toHaveTextContent(/couldn't load orders/i);
  });
});
```

Primitives portal their popups — dialogs, menus, selects, popovers — to `document.body`. `screen`
queries find them; `within(container)` never does.

---

## Decision: testing a form

Forms are `react-hook-form` + `zod` rendered with shadcn's `Field`, submitting through a
`useMutation` (see `references/forms.md`). Two things are worth testing and nothing else: that
zod's client-side validation blocks submission, and that the API's `VALIDATION_ERROR` details
surface on the right field.

Both assert on copy, so the harness has to render copy. Schema messages are translation keys:
load the app's i18n instance in setup with the English resources bundled (not fetched over HTTP),
or every assertion below reads a key.

```ts
// tests/setup.ts — append
import i18n from '@/i18n';

beforeAll(async () => {
  await i18n.changeLanguage('en');
});
```

```tsx
// src/components/organisms/CreateOrderForm/CreateOrderForm.test.tsx  ✅
it('should surface the API field error when the server rejects the reference', async () => {
  // Arrange — the std-api-design envelope, as the ApiError interceptor expects it
  server.use(
    http.post('*/orders', () =>
      HttpResponse.json(
        {
          error: 'Validation failed',
          code: 'VALIDATION_ERROR',
          status: 422,
          details: [{ field: 'reference', message: 'has already been taken' }],
          requestId: 'req-test-2',
        },
        { status: 422 },
      ),
    ),
  );
  const user = userEvent.setup();
  renderWithProviders(<CreateOrderForm onCreated={vi.fn()} />);

  // Act
  await user.type(screen.getByLabelText(/reference/i), 'ORD-001');
  await user.click(screen.getByRole('button', { name: /create order/i }));

  // Assert
  expect(await screen.findByRole('alert')).toHaveTextContent(/already been taken/i);
  expect(screen.getByLabelText(/reference/i)).toHaveAccessibleDescription(/already been taken/i);
});

it('should block submission when the reference is empty', async () => {
  const onCreated = vi.fn();
  const user = userEvent.setup();
  renderWithProviders(<CreateOrderForm onCreated={onCreated} />);

  await user.click(screen.getByRole('button', { name: /create order/i }));

  expect(await screen.findByText(/reference is required/i)).toBeInTheDocument();
  expect(onCreated).not.toHaveBeenCalled();
});
```

Note `userEvent.setup()` before render, and `await` on every interaction — `userEvent` v14 is
async and unawaited clicks are the #1 source of flaky RTL suites.

`getByLabelText(/reference/i)` only works because `FieldLabel` and `Input` pair `htmlFor`/`id`,
and `toHaveAccessibleDescription` only passes because the input's `aria-describedby` points at
the `FieldError`. When either fails, the bug is in the component's accessibility, not in the test.

---

## Decision: testing a chart

A chart is asserted through its text alternative and its data mapping — never its pixels. jsdom
gives a canvas no 2D context and no `ResizeObserver`, so `tests/setup.ts` imports
`vitest-canvas-mock` and stubs the observer. Skip the mock and Chart.js only logs "Failed to
create chart" — the test passes having asserted nothing. The text alternative is specified in
`references/charts.md`; the setup and the bad/good pairs are in
`@skills/std-testing/references/react-components.md`.

---

## Decision: testing navigation

A permission-filtered nav cannot be tested by reading `nav.ts`: the config lists every area, and a
role sees its subset only at runtime. Render the real `routes` in a memory router for each role's
`/me` fixture and assert the structure — areas only in the main nav, within the budget; the section
nav inside its area; `aria-current` on the current link. `renderWithProviders` above wraps a
`MemoryRouter`, which cannot hold a data router, so routed tests use their own harness →
`@skills/std-testing/references/react-components.md`. The role fixtures →
`@skills/access-control-designer/references/ui-gates.md`.

---

## Decision: testing a Zustand store's consumers

Zustand state is module-level and **persists across tests**. Reset it.

```ts
// tests/setup.ts — append
import { useUiStore } from '@/stores/ui-store';
import { useOrderFilterStore } from '@/stores/order-filter-store';

const initialUi = useUiStore.getState();
const initialFilters = useOrderFilterStore.getState();

afterEach(() => {
  useUiStore.setState(initialUi, true);
  useOrderFilterStore.setState(initialFilters, true);
});
```

Without this, a test that collapses the sidebar leaves it collapsed for every test after it.

---

## What to test, and what not to

| Test it | Skip it |
|---|---|
| Page renders API data (via MSW) | That `useQuery` caches (that's TanStack's test suite) |
| Form validation + submission + error mapping | That zod validates (that's zod's test suite) |
| Conditional UI (empty / error / loading states) | Exact Tailwind class strings |
| Store actions changing rendered output | Store internals in isolation |
| Accessible names and roles are present | Snapshot of the whole DOM |
| A chart's text alternative and its data mapping | Canvas pixels, draw calls, tick positions, animation frames |
| Navigation per role: areas only, sections inside their area, `aria-current` | The sidebar's pixel layout |
| Your composition of a primitive — labels, wiring, states | The primitive's own focus trap and keyboard handling (Base UI's or Radix's test suite) |

Coverage targets from the org standard: **80% on business logic** (hooks, stores, schema
transforms), **60% overall minimum**.
