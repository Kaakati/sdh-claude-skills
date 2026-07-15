# Next.js: The Server/Client Boundary Across Atomic Levels

**Next.js App Router only.** Ignore this file on Vite, Phlex, or React Native tasks — none of them
have a server/client component split.

In the App Router every component is a Server Component unless it (or an ancestor in the render
tree) declares `"use client"`. Atomic Design and the server/client split are orthogonal axes: the
atomic level tells you what a component may *compose* and whether it may be *data-aware*; the
directive tells you where it *runs*. A component's atomic level never changes because of where it
runs.

---

## Decision: does this component need `"use client"`?

Add the directive only when the component uses `useState`, `useEffect` (or any hook), event
handlers, refs to DOM nodes, or browser APIs. Nothing else forces it.

| Level | Default | Add `"use client"` when |
|-------|---------|-------------------------|
| Atoms | Server Component | It owns interaction state (a controlled input, a hover-driven tooltip) |
| Molecules | Server Component | It handles events — `onSubmit`, `onChange`, `onPress` |
| Organisms | Server Component when it fetches server-side | It uses hooks (`useQuery`, `useState`) instead of an `await` |
| Templates | Server Component | Essentially never — templates are structural slots |
| Pages | Server Component (`page.tsx`) | Essentially never — fetch in the page, push interactivity down |

The direction that matters: **push `"use client"` as far down the tree as you can.** The directive
is inherited by everything a client component renders, so a `"use client"` on a template or page
drags the entire subtree onto the client and forfeits server rendering for atoms that never needed
it.

```tsx
// BAD: the directive sits on the page, so the template, every organism,
// and every atom below it all become client components.
"use client";

import { useState } from "react";

export default function DashboardPage() {
  const [query, setQuery] = useState("");
  const { data } = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });

  return (
    <DashboardLayout header={<Header onSearch={setQuery} />}>
      <MetricsGrid metrics={data} />
    </DashboardLayout>
  );
}
```

```tsx
// GOOD: the page stays a Server Component and awaits its data.
// Only SearchForm — the molecule that actually owns state — is a client component.
import { Suspense } from "react";

export const metadata = {
  title: "Dashboard",
  description: "Overview of key metrics and recent activity",
};

export default async function DashboardPage() {
  const currentUser = await getCurrentUser();

  return (
    <DashboardLayout header={<Header currentUser={currentUser} />}>
      <Heading level={1}>Dashboard</Heading>
      <Suspense fallback={<Spinner />}>
        <MetricsGrid />
      </Suspense>
    </DashboardLayout>
  );
}
```

`Heading`, `Spinner`, and `DashboardLayout` carry no directive and render on the server.
`SearchForm`, nested inside `Header`, declares `"use client"` in its own file — see
`molecule-atom-composition` for that molecule's code.

---

## Decision: should this organism `await` or use a hook?

Organisms are the lowest data-aware level on every platform, and in Next.js you get two ways to
honor that. Pick by whether the section needs client interactivity after its first paint.

| Situation | Shape |
|-----------|-------|
| Section renders fetched data and is then static | `async function` Server Component that `await`s its data |
| Section needs refetch, mutation, polling, or optimistic updates | `"use client"` + TanStack Query |

Prefer the Server Component. Wrap it in `<Suspense>` at the page so its fetch streams instead of
blocking the whole route, which is what the `Suspense` boundaries above are doing.
`organism-data-awareness` has the Server Component organism code.

---

## Decision: `layout.tsx` or an Atomic Design template?

They are different things and can be used together:

- `app/**/layout.tsx` is a Next.js routing primitive — a persistent shell that survives navigation
  between the route segments beneath it.
- An Atomic Design template is a reusable layout *component* with slots, used inside a page.

A `layout.tsx` may render an Atomic Design template internally. Do not collapse the two: a template
must stay reusable outside the route it happens to serve. See `template-layout-skeleton`.
