# Testing Next.js Server Components and Server Actions

Load-bearing rules restated (this file stands alone):
- Test **behavior**, not implementation. Name tests `should [expected behavior] when [condition]`.
- Mock at the **process boundary** — the Rails API client / `fetch`, and Next's own framework modules
  (`next/cache`, `next/navigation`). Never mock your own validation or domain logic.

Applies to the Next.js App Router only. Client Components are ordinary React — see
`react-components.md`.

---

## Decision: Server Component or Client Component?

| The file | How to test |
|---|---|
| No `"use client"`, `async function` | Call it as a function, assert on returned JSX. Mock the data source at module level. |
| `"use client"` | Render with RTL + MSW. See `react-components.md`. |
| `"use server"` action | Call it as an async function with `FormData`. Mock `next/cache` + `next/navigation`. |
| `generateMetadata` | Plain async function. Test separately for SEO. |

---

## Testing a Server Component

A Server Component is just an async function returning JSX. You do not need a browser to test it —
render its output.

```tsx
// app/projects/page.tsx
import { getProjects } from "@/lib/api/projects";

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams: Promise<{ page?: string }>;
}) {
  const { page = "1" } = await searchParams;
  const projects = await getProjects({ page: Number(page) });

  if (projects.length === 0) {
    return <p role="status">No projects yet.</p>;
  }

  return (
    <ul>
      {projects.map((p) => (
        <li key={p.id}>{p.name}</li>
      ))}
    </ul>
  );
}
```

```tsx
// BAD — MSW + render() on a Server Component. RTL cannot render an async component;
// this either throws "Objects are not valid as a React child (promise)" or silently
// asserts on nothing.
it("renders projects", async () => {
  render(<ProjectsPage searchParams={Promise.resolve({})} />);
  expect(await screen.findByText("Apollo")).toBeInTheDocument();
});
```

```tsx
// GOOD — mock the API module, await the component, render the resolved element.
import { render, screen } from "@testing-library/react";
import ProjectsPage from "@/app/projects/page";
import { getProjects } from "@/lib/api/projects";

vi.mock("@/lib/api/projects");
const mockedGetProjects = vi.mocked(getProjects);

beforeEach(() => vi.clearAllMocks());

it("should render each project name when the API returns projects", async () => {
  // Arrange
  mockedGetProjects.mockResolvedValue([{ id: "1", name: "Apollo" }]);

  // Act — a Server Component is an async function; await it, then render the element.
  render(await ProjectsPage({ searchParams: Promise.resolve({}) }));

  // Assert
  expect(screen.getByText("Apollo")).toBeInTheDocument();
});

it("should request the page from searchParams when a page param is present", async () => {
  mockedGetProjects.mockResolvedValue([]);

  await ProjectsPage({ searchParams: Promise.resolve({ page: "3" }) });

  expect(mockedGetProjects).toHaveBeenCalledWith({ page: 3 });
});

it("should render an empty state when the API returns no projects", async () => {
  mockedGetProjects.mockResolvedValue([]);

  render(await ProjectsPage({ searchParams: Promise.resolve({}) }));

  expect(screen.getByRole("status")).toHaveTextContent(/no projects yet/i);
});
```

Note the `searchParams`/`params` props are **Promises** in the App Router — pass
`Promise.resolve({...})`, not a bare object, or the `await` inside the component hangs the test.

---

## Testing `generateMetadata`

```tsx
// GOOD — a pure async function; no rendering involved.
import { generateMetadata } from "@/app/projects/[id]/page";
import { getProject } from "@/lib/api/projects";

vi.mock("@/lib/api/projects");

it("should use the project name as the page title when the project exists", async () => {
  vi.mocked(getProject).mockResolvedValue({ id: "1", name: "Apollo", summary: "Moon shot" });

  const metadata = await generateMetadata({ params: Promise.resolve({ id: "1" }) });

  expect(metadata.title).toBe("Apollo");
  expect(metadata.description).toBe("Moon shot");
});
```

---

## Testing a Server Action

Server actions take `FormData` and return a result shape (or throw/redirect). Test both.

```typescript
// app/projects/actions.ts
"use server";

import { z } from "zod";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createProject } from "@/lib/api/projects";

const schema = z.object({ name: z.string().min(3) });

export type ActionState = { errors?: Record<string, string[]> };

export async function createProjectAction(
  _prev: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const parsed = schema.safeParse({ name: formData.get("name") });

  if (!parsed.success) {
    return { errors: parsed.error.flatten().fieldErrors };
  }

  const project = await createProject(parsed.data);
  revalidatePath("/projects");
  redirect(`/projects/${project.id}`);
}
```

```typescript
// BAD — mocks the zod schema so the validation branch is never really exercised,
// and never mocks next/cache, so revalidatePath throws
// "static generation store missing" outside a request scope.
vi.mock("zod");
it("validates", async () => {
  const result = await createProjectAction({}, new FormData());
  expect(result).toBeDefined();
});
```

```typescript
// GOOD — real validation, framework modules faked at the boundary.
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createProject } from "@/lib/api/projects";
import { createProjectAction } from "@/app/projects/actions";

vi.mock("next/cache", () => ({ revalidatePath: vi.fn(), revalidateTag: vi.fn() }));
vi.mock("next/navigation", () => ({ redirect: vi.fn() }));
vi.mock("@/lib/api/projects");

beforeEach(() => vi.clearAllMocks());

function formDataOf(fields: Record<string, string>): FormData {
  const fd = new FormData();
  Object.entries(fields).forEach(([k, v]) => fd.append(k, v));
  return fd;
}

it("should return field errors when the name is too short", async () => {
  // Arrange
  const formData = formDataOf({ name: "ab" });

  // Act
  const result = await createProjectAction({}, formData);

  // Assert
  expect(result.errors?.name).toBeDefined();
  expect(createProject).not.toHaveBeenCalled();
  expect(revalidatePath).not.toHaveBeenCalled();
});

it("should create the project and revalidate when the input is valid", async () => {
  vi.mocked(createProject).mockResolvedValue({ id: "42", name: "Apollo" });

  await createProjectAction({}, formDataOf({ name: "Apollo" }));

  expect(createProject).toHaveBeenCalledWith({ name: "Apollo" });
  expect(revalidatePath).toHaveBeenCalledWith("/projects");
  expect(redirect).toHaveBeenCalledWith("/projects/42");
});
```

Assert three things on every action: the **return shape** on invalid input, the **side effects**
(API call + revalidation) on valid input, and that side effects **do not fire** on invalid input —
that last one is the security-relevant assertion and is the one most often missing.

### Redirect gotcha

The real `redirect()` throws a `NEXT_REDIRECT` control-flow error. When you mock `next/navigation`
(as above), it does not throw, so code after the `redirect` call still runs. If you test against the
real implementation instead, wrap in `expect(...).rejects.toThrow("NEXT_REDIRECT")`. Mocking is
preferred — it keeps the assertion about intent, not about Next's internals.

---

## Route Handlers (`app/api/**/route.ts`)

```typescript
// GOOD — construct a real Request, call the exported handler, assert on the Response.
import { POST } from "@/app/api/webhooks/stripe/route";

it("should return 400 when the signature header is missing", async () => {
  const request = new Request("http://localhost/api/webhooks/stripe", {
    method: "POST",
    body: JSON.stringify({ type: "charge.succeeded" }),
  });

  const response = await POST(request);

  expect(response.status).toBe(400);
  await expect(response.json()).resolves.toMatchObject({
    error: { code: "missing_signature" },
  });
});
```

No test server, no supertest. Route handlers are `(Request) => Response` — call them directly.
