# Testing React Components (Vitest + RTL + MSW)

Load-bearing rules restated (this file stands alone):
- Test **user behavior**, not implementation details.
- Name tests `should [expected behavior] when [condition]`; structure Arrange / Act / Assert.
- Mock at the **network boundary** (MSW), never mock your own hooks or components.

Applies to browser React: ReactJS Vite SPA and Next.js Client Components. React Native has its own
renderer — see `react-native.md`.

---

## Setup: Vitest configuration

- Vitest for all web frontend tests (Vite SPA and Next.js) — Jest-compatible API, native Vite support.
- Environment `jsdom` or `happy-dom`.
- `@testing-library/jest-dom` matchers loaded from a setup file.
- Co-locate: `Component.tsx` → `Component.test.tsx`.

```typescript
// vitest.config.ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: { provider: "v8", reporter: ["text", "lcov"] },
  },
});
```

```typescript
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, afterAll, beforeAll } from "vitest";
import { server } from "./msw-server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
```

`onUnhandledRequest: "error"` is deliberate — an un-mocked request should fail the test loudly, not
silently hit the network.

---

## Decision: which query do I reach for?

Priority order — prefer queries that reflect how users actually find things:

1. `getByRole` — best; ARIA role (`button`, `heading`, `textbox`), usually with `{ name }`.
2. `getByLabelText` — form elements with associated labels.
3. `getByPlaceholderText` — when no visible label exists.
4. `getByText` — non-interactive content.
5. `getByTestId` — last resort, only when no semantic query applies.

```tsx
// BAD — test IDs everywhere; passes even if the button is a non-focusable <div>
// with no accessible name. The test cannot detect an accessibility regression.
it("submits", async () => {
  render(<LoginForm />);
  fireEvent.change(screen.getByTestId("email-input"), {
    target: { value: "jane@example.com" },
  });
  fireEvent.click(screen.getByTestId("submit-btn"));
  expect(screen.getByTestId("success")).toBeInTheDocument();
});
```

```tsx
// GOOD — role/label queries + userEvent. Fails if the markup stops being accessible.
import userEvent from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";

it("should show a success message when credentials are valid", async () => {
  // Arrange
  const user = userEvent.setup();
  render(<LoginForm />);

  // Act
  await user.type(screen.getByLabelText(/email/i), "jane@example.com");
  await user.type(screen.getByLabelText(/password/i), "hunter2");
  await user.click(screen.getByRole("button", { name: /sign in/i }));

  // Assert
  expect(await screen.findByRole("status")).toHaveTextContent(/welcome back/i);
});
```

`userEvent`, not `fireEvent`: `fireEvent.click` dispatches one synthetic event; `user.click` fires the
pointer/focus/mouse sequence a real browser does — it catches disabled buttons and focus traps that
`fireEvent` sails past.

### `getBy` vs `findBy` vs `queryBy`

- `getBy*` — must exist **now**; throws otherwise.
- `findBy*` — will exist **soon** (async); always `await` it.
- `queryBy*` — may not exist; the **only** correct way to assert absence.

```tsx
// BAD — getByText throws before the assertion can run, so the failure message is
// "unable to find element" instead of "expected element not to be in the document".
expect(screen.getByText(/error/i)).not.toBeInTheDocument();
```

```tsx
// GOOD
expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
```

---

## Decision: how do I fake the server?

MSW at the network boundary. Never mock `axios`, never mock `useQuery`.

```typescript
// src/test/msw-server.ts
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

export const handlers = [
  http.get("*/api/v1/projects", () =>
    HttpResponse.json({ data: [{ id: "1", name: "Apollo" }] }),
  ),
];

export const server = setupServer(...handlers);
```

```tsx
// BAD — mocks TanStack Query itself. The component's real cache/loading/error
// behavior is never exercised; the test passes even if the query key is wrong.
vi.mock("@tanstack/react-query", () => ({
  useQuery: () => ({ data: [{ id: "1", name: "Apollo" }], isLoading: false }),
}));
```

```tsx
// GOOD — real QueryClient, real hook, fake HTTP. Loading and error states are testable.
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw-server";

it("should render the project list when the API returns projects", async () => {
  renderWithProviders(<ProjectList />);

  expect(screen.getByRole("status", { name: /loading/i })).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "Apollo" })).toBeInTheDocument();
});

it("should render an error message when the API returns 500", async () => {
  server.use(
    http.get("*/api/v1/projects", () => new HttpResponse(null, { status: 500 })),
  );

  renderWithProviders(<ProjectList />);

  expect(await screen.findByRole("alert")).toHaveTextContent(/could not load projects/i);
});
```

Per-test overrides go through `server.use(...)`; `resetHandlers()` in `afterEach` undoes them.

---

## Decision: how do I render a component that needs providers?

One shared utility. Never repeat provider trees in test files.

```tsx
// src/test/render.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

export function renderWithProviders(
  ui: ReactElement,
  { route = "/", ...options }: RenderOptions & { route?: string } = {},
) {
  // retry:false is essential — the default 3 retries make error-path tests time out.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) };
}
```

A **fresh QueryClient per render** is mandatory — a module-level client leaks cached data between
tests and breaks independence.

---

## Decision: testing a Zustand store

Client state only. Reset between tests or state leaks across the file.

```typescript
// BAD — store is a module singleton; test order now decides the outcome.
it("should add an item to the cart", () => {
  useCartStore.getState().addItem(buildItem());
  expect(useCartStore.getState().items).toHaveLength(1); // fails if a prior test added one
});
```

```typescript
// GOOD — snapshot the initial state once, restore before each test.
import { useCartStore } from "@/stores/cart";

const initialState = useCartStore.getState();

beforeEach(() => {
  useCartStore.setState(initialState, true);
});

it("should add an item to the cart when addItem is called", () => {
  useCartStore.getState().addItem(buildItem({ id: "sku-1" }));

  expect(useCartStore.getState().items).toEqual([expect.objectContaining({ id: "sku-1" })]);
});
```

Test the store directly for logic; test it through a component only when the binding is the point.

---

## Framer Motion and animation

Do not assert on transform values or wait for animations. Assert on the **end state** with
`findBy*`, and disable motion globally in tests:

```tsx
// src/test/setup.ts (addition)
import { MotionGlobalConfig } from "framer-motion";
MotionGlobalConfig.skipAnimations = true;
```

---

## Charts (ApexCharts)

ApexCharts renders SVG through a non-jsdom-friendly path. Do not assert on rendered bars. Test the
**data transform** as a pure unit, and assert only that the chart region is present with an
accessible name.

```typescript
// GOOD — the logic worth testing is the transform, and it needs no DOM at all.
it("should aggregate revenue by month when given daily rows", () => {
  const rows = [
    { date: "2024-01-05", cents: 1_000 },
    { date: "2024-01-20", cents: 2_500 },
    { date: "2024-02-01", cents: 500 },
  ];

  expect(toMonthlySeries(rows)).toEqual([
    { x: "2024-01", y: 35 },
    { x: "2024-02", y: 5 },
  ]);
});
```
