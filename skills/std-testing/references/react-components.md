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
import { AbilityProvider } from "@/components/providers/AbilityProvider";
import type { AppRule } from "@/lib/ability";

export function renderWithProviders(
  ui: ReactElement,
  { route = "/", rules, ...options }: RenderOptions & { route?: string; rules?: AppRule[] } = {},
) {
  // retry:false is essential — the default 3 retries make error-path tests time out.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    // @casl/react 7: a gated leaf (useAppAbility, Can) throws outside an AbilityProvider.
    const gated = rules ? <AbilityProvider rules={rules}>{children}</AbilityProvider> : children;
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{gated}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper, ...options }) };
}
```

A **fresh QueryClient per render** is mandatory — a module-level client leaks cached data between
tests and breaks independence. Layouts rendered through the app's route tree use the routed harness
in *Navigation rendered per role* below instead.

**Pass `rules` for a gated leaf.** Under @casl/react 7, a component that calls `useAppAbility()` or
renders `<Can>` throws outside an `AbilityProvider` ("AbilityContext is not provided"), so its test
passes the role's rules — `renderWithProviders(<CancelOrderButton order={order} />, { rules })` —
rather than building a provider tree in the test file. A layout that renders the provider itself
(`AppLayout`) needs none (`@skills/access-control-designer/references/ui-gates.md`).

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

## Charts (Chart.js via react-chartjs-2)

A Vite SPA chart draws on a `<canvas>`, and jsdom gives a canvas neither a 2D context nor a
`ResizeObserver` to size it by. Both gaps fail quietly, or loudly with the wrong message (house
lab — Chart.js 4.5.1, jsdom 30.0.1):

- **No canvas mock** → `getContext()` returns nothing, Chart.js logs "Failed to create chart: can't
  acquire context from the given item" without throwing, and a test that never checks the chart
  exists passes.
- **No `ResizeObserver`** → a responsive chart throws `ReferenceError: ResizeObserver is not
  defined`. Under `StrictMode` RTL reports an `AggregateError` that also contains "Canvas is
  already in use", because the first instance was never destroyed — a message that points at the
  wrong bug.

```typescript
// src/test/setup.ts (addition)
import "vitest-canvas-mock";
import { vi } from "vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);
```

`vitest-canvas-mock` (MIT, peers Vitest 3 to 5) works by being imported from a setup file. Why this
mock, and its alternatives → `@skills/std-reactjs/references/charts.md`. Three things are yours to
assert:

1. **The data mapping** — a pure function from API data to the chart's points. It needs no DOM.
2. **The wiring** — that the chart exists and holds those values: `Chart.getChart(canvas)`.
3. **The text alternative** every house chart ships with — the summary sentence and the visually
   hidden data table. If a test can read the numbers there, so can a screen reader.

```tsx
// BAD — snapshots the mock's recorded draw calls. It pins Chart.js's drawing internals, breaks on a
// patch release that changes nothing a user sees, and says nothing about the numbers anyone reads.
it("renders the revenue chart", () => {
  const { container } = renderWithProviders(<RevenueChart points={points} currency="USD" />);
  const ctx = container.querySelector("canvas")!.getContext("2d");
  expect(ctx.__getDrawCalls()).toMatchSnapshot();
});
```

```typescript
// GOOD — the mapping is logic; test it without a DOM.
it("should convert cents to whole units in date order when days arrive unsorted", () => {
  const days = [
    { date: "2026-01-06", totalCents: 500 },
    { date: "2026-01-05", totalCents: 3_500 },
  ];

  expect(toRevenuePoints(days)).toEqual([
    { day: "2026-01-05", revenue: 35 },
    { day: "2026-01-06", revenue: 5 },
  ]);
});
```

```tsx
// GOOD — the chart exists and holds the mapped values. Without the canvas mock getChart returns
// undefined, so this fails loudly instead of passing having checked nothing.
import { Chart } from "chart.js";

it("should plot one revenue value per day when given points", () => {
  // Arrange
  const points = [
    { day: "2026-01-05", revenue: 35 },
    { day: "2026-01-06", revenue: 5 },
  ];

  // Act
  const { container } = renderWithProviders(<RevenueChart points={points} currency="USD" />);

  // Assert
  const chart = Chart.getChart(container.querySelector("canvas")!);
  expect(chart?.data.datasets[0].data).toEqual([35, 5]);
});
```

```tsx
// GOOD — the text alternative is the contract a screen reader relies on; assert that.
import { within } from "@testing-library/react";

it("should expose one table row per day when given revenue points", () => {
  // Arrange
  const points = [
    { day: "2026-01-05", revenue: 35 },
    { day: "2026-01-06", revenue: 5 },
  ];

  // Act
  renderWithProviders(
    <RevenueFigure points={points} currency="USD">
      <RevenueChart points={points} currency="USD" />
    </RevenueFigure>,
  );

  // Assert
  const rows = within(screen.getByRole("table")).getAllByRole("row");
  expect(rows).toHaveLength(3); // header + one per day
  expect(rows[1]).toHaveTextContent(/2026-01-05.*35/);
});
```

No waiting on animation: the table never animates, and `Chart.getChart` holds the data from the
first render. Assert the numbers with a pattern rather than exact currency formatting unless the
test pins the locale — `Intl.NumberFormat` output follows it.

### Next.js Client Components (shadcn `chart`, Recharts)

Same contract, different renderer. Recharts draws SVG, so there is no canvas to mock: assert the
mapping and the text alternative, and never SVG paths or a `recharts-*` class name — jsdom does no
layout, so the geometry is not what a browser draws. Keep the `ResizeObserver` stub. The chart
itself → `@skills/std-shadcn-ui/references/charts.md`.

---

## Navigation rendered per role (Vite SPA)

The per-role table — exactly the permitted areas in order, nothing nested under the main nav, the
recorded area budget, the one-area and feature-gate cases — and its fixtures are
`@skills/access-control-designer/references/ui-gates.md`'s; the rules they pin are
`@skills/ui-ux-patterns/references/drill-down-navigation.md`'s. A navigation test has to render
what a role actually gets, because the config lists every area and a role sees its subset only at
runtime. This section adds the Vite harness that rendering needs.

`renderWithProviders` wraps a `MemoryRouter`, a declarative router. Loaders, and
`ScrollRestoration` — a framework- and data-mode API (React Router docs — ScrollRestoration) — need
a data router, which cannot render inside another router. So in a Vite app the per-role table, and
any test of `AppLayout` or an `AreaLayout`, renders the exported `routes` in a memory router. The
loaders warm the app's own `queryClient`, so the harness renders with that instance and setup
clears it after every test — the isolation of a fresh client, kept by clearing instead of
replacing.

```tsx
// src/test/render-route.tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { render } from "@testing-library/react";
import { queryClient } from "@/api/query-client";   // the client the loaders warm
import { routes } from "@/router";

queryClient.setDefaultOptions({ queries: { retry: false } });

export function renderRoute(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  return {
    router,
    ...render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    ),
  };
}

// src/test/setup.ts (addition): afterEach(() => queryClient.clear()) — or one role's /me answers the next test
```

What only a routed render can show — the section nav living in the area's layout, not the sidebar:

```tsx
// src/components/templates/AreaLayout/AreaLayout.test.tsx
import { http, HttpResponse } from "msw";
import { screen, within } from "@testing-library/react";
import { server } from "@/test/msw-server";
import { renderRoute } from "@/test/render-route";
import { useAuthStore } from "@/stores/auth-store";
import meByRole from "@/test/fixtures/me-by-role.json"; // exported by the Rails /me request spec

it("should render Organization's sections in the page, not the sidebar, when an owner opens Members", async () => {
  // Arrange
  useAuthStore.setState({ accessToken: "test-token" });
  server.use(http.get("*/api/v1/me", () => HttpResponse.json({ data: meByRole.owner })));

  // Act
  renderRoute("/members");

  // Assert
  const sections = await screen.findByRole("navigation", { name: /organization sections/i });
  expect(screen.getByRole("navigation", { name: /main/i })).not.toContainElement(sections);
  expect(within(sections).getByRole("link", { name: /members/i })).toHaveAttribute("aria-current", "page");
});
```

- **The per-role table swaps its render, not its assertions:** `renderRoute("/")` in place of
  `renderWithProviders(<AppLayout />)`, so the landing loader and the layout's gates run.
- **Names come from translations** — load the English resources in setup, as the form tests do, or
  every `name:` matcher reads a key.
- **Back, once the structure passes:** `await router.navigate(-1)` after a drill-in returns to the
  list with its search params; where focus lands is `drill-down-navigation.md`'s.

---

## Sources

- React Router docs — ScrollRestoration — https://reactrouter.com/api/components/ScrollRestoration
- npm — vitest-canvas-mock — https://registry.npmjs.org/vitest-canvas-mock
- house lab — the round-3 Chart.js research run (2026-09-11): Chart.js 4.5.1 under React 19.3.0,
  jsdom 30.0.1 and Vitest 5.0.0
