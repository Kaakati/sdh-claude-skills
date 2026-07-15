# Testing React Native (RNTL + TanStack Query + Reanimated)

Load-bearing rules restated (this file stands alone):
- Test **user behavior**, not implementation details.
- Name tests `should [expected behavior] when [condition]`; structure Arrange / Act / Assert.
- Mock at the **network/native boundary** only — never mock your own hooks, stores, or components.

Applies to React Native / Expo. Browser React (Vite SPA, Next.js Client Components) uses a different
renderer and query set — see `react-components.md`.

---

## Decision: which renderer and which queries?

Jest + `@testing-library/react-native` (RNTL), **not** Vitest + jsdom — there is no DOM, and Metro's
transform pipeline is Jest-based via `jest-expo` / `react-native` presets.

Query priority mirrors the web ordering, adapted to RN's accessibility tree:

1. `getByRole` — with `{ name }`, e.g. `getByRole("button", { name: /save/i })`.
2. `getByLabelText` — maps to `accessibilityLabel`.
3. `getByPlaceholderText` — `TextInput` without a visible label.
4. `getByText` — non-interactive content.
5. `getByTestId` — last resort only.

```tsx
// BAD — testID everywhere plus fireEvent.press on a bare View. Passes even when the
// control has no accessibility role or label, so screen readers get nothing.
it("saves", () => {
  const { getByTestId } = render(<ProfileForm />);
  fireEvent.press(getByTestId("save-button"));
  expect(getByTestId("toast")).toBeTruthy();
});
```

```tsx
// GOOD — role/label queries; fails if the component stops being accessible.
import { render, screen, userEvent } from "@testing-library/react-native";

it("should show a confirmation when the profile is saved", async () => {
  // Arrange
  const user = userEvent.setup();
  render(<ProfileForm />);

  // Act
  await user.type(screen.getByLabelText(/display name/i), "Jane");
  await user.press(screen.getByRole("button", { name: /save/i }));

  // Assert
  expect(await screen.findByText(/profile updated/i)).toBeOnTheScreen();
});
```

Use `userEvent` from RNTL (v12.4+), not `fireEvent`: it fires the full press sequence with realistic
timing, so it catches `disabled` and `pointerEvents="none"` that `fireEvent.press` ignores.

---

## Decision: how do I fake the server?

MSW with the native fetch/XHR interceptor — same boundary rule as web. Never mock `axios`, never mock
`useQuery`.

```typescript
// jest.setup.ts
import "react-native-gesture-handler/jestSetup";
import { server } from "./src/test/msw-server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

```tsx
// BAD — mocks the data hook, so query keys, caching, loading and error paths are untested.
vi.mock("@/hooks/useProjects", () => ({
  useProjects: () => ({ data: [{ id: "1", name: "Apollo" }], isLoading: false }),
}));
```

```tsx
// GOOD — real hook, real QueryClient, faked HTTP; loading and error states are reachable.
import { http, HttpResponse } from "msw";
import { server } from "@/test/msw-server";

it("should render the project list when the API returns projects", async () => {
  renderWithProviders(<ProjectListScreen />);

  expect(await screen.findByText("Apollo")).toBeOnTheScreen();
});

it("should show an error state when the API returns 500", async () => {
  server.use(
    http.get("*/api/v1/projects", () => new HttpResponse(null, { status: 500 })),
  );

  renderWithProviders(<ProjectListScreen />);

  expect(await screen.findByText(/could not load projects/i)).toBeOnTheScreen();
});
```

---

## Provider wrapper

One shared utility, fresh `QueryClient` per render (a module-level client leaks cache between tests
and breaks independence).

```tsx
// src/test/render.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NavigationContainer } from "@react-navigation/native";
import { render } from "@testing-library/react-native";
import type { ReactElement, ReactNode } from "react";

export function renderWithProviders(ui: ReactElement) {
  // retry:false — the default 3 retries make error-path tests time out.
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NavigationContainer>{children}</NavigationContainer>
      </QueryClientProvider>
    );
  }

  return { queryClient, ...render(ui, { wrapper: Wrapper }) };
}
```

---

## Decision: testing navigation

Assert the **intent**, not the navigator internals.

```tsx
// BAD — asserts on the whole navigation state tree; breaks on any unrelated route change.
expect(navigationRef.getRootState().routes[1].name).toBe("ProjectDetail");
```

```tsx
// GOOD — inject a spy navigation prop; the assertion states the user-visible outcome.
it("should navigate to the project detail when a project row is pressed", async () => {
  const user = userEvent.setup();
  const navigate = jest.fn();

  render(<ProjectRow project={buildProject({ id: "42" })} navigation={{ navigate } as any} />);
  await user.press(screen.getByRole("button", { name: /apollo/i }));

  expect(navigate).toHaveBeenCalledWith("ProjectDetail", { projectId: "42" });
});
```

---

## Decision: testing a Zustand store

Client state only — server data belongs to TanStack Query, never a store. Reset between tests.

```typescript
// BAD — module singleton; a prior test's items leak in and test order decides the result.
it("adds an item", () => {
  useCartStore.getState().addItem(buildItem());
  expect(useCartStore.getState().items).toHaveLength(1);
});
```

```typescript
// GOOD
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

---

## Native modules and Reanimated

Never assert on animated style values or wait for animations to settle — assert the **end state**
with `findBy*`. Mock native modules once, in the Jest setup file, never per-test.

```typescript
// jest.setup.ts
require("react-native-reanimated").setUpTests();

jest.mock("react-native-mmkv", () => {
  const store = new Map<string, string>();
  return {
    MMKV: jest.fn().mockImplementation(() => ({
      set: (k: string, v: string) => store.set(k, v),
      getString: (k: string) => store.get(k),
      delete: (k: string) => store.delete(k),
      clearAll: () => store.clear(),
    })),
  };
});
```

An in-memory **fake** beats a `jest.fn()` mock here: real read-after-write semantics mean the code
under test exercises its actual persistence path.

---

## Centrifugo / real-time

Do not spin up a WebSocket in a unit test. Inject a fake client and drive the callback directly.

```typescript
// GOOD — the subscription handler is the unit; the transport is a fake.
it("should append the incoming message when a chat event is published", () => {
  const handlers: Record<string, (ctx: unknown) => void> = {};
  const fakeSub = {
    on: (event: string, cb: (ctx: unknown) => void) => {
      handlers[event] = cb;
    },
    subscribe: jest.fn(),
  };

  const { result } = renderHook(() => useChatChannel("room-1", fakeSub as any));

  act(() => handlers.publication({ data: { id: "m1", body: "hi" } }));

  expect(result.current.messages).toEqual([{ id: "m1", body: "hi" }]);
});
```
