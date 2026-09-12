# Caching, ISR, and revalidation

Load-bearing rules restated (this file is read standalone):

- A route is **static by default** unless something in it reads request-time data.
- **ISR** = `export const revalidate = N` (seconds) on a page/layout, or `next: { revalidate: N }`
  on a `fetch`.
- **Every mutation must invalidate what it changed** — `revalidatePath()`, or its tags: `updateTag()`
  in a server action on Next.js 16, `revalidateTag()` on 15 — or users see stale data.
- Cache tags are the preferred invalidation handle; paths are the blunt instrument.

---

## Decision: should this route be static, ISR, or dynamic?

| Situation | Directive | Result |
|-----------|-----------|--------|
| Marketing page, no per-user data | (nothing) or `export const dynamic = 'force-static'` | Rendered at build |
| Catalog/list that may lag a minute | `export const revalidate = 60` | ISR: served from cache, regenerated in the background |
| Per-user dashboard, auth-dependent | `export const dynamic = 'force-dynamic'` | Rendered per request |
| Content changed by an admin action | `revalidate = false` + a tag invalidation from the action (`updateTag()` on 16, `revalidateTag()` on 15) | Cached indefinitely, invalidated on write |

Reading `cookies()`, `headers()`, `searchParams`, or `draftMode()` opts the route into dynamic
rendering automatically — a route with a session check is dynamic whether you declare it or not.
Declare it anyway; the explicit export documents the intent and prevents build-time surprises.

---

## Decision: how do I cache a Rails API call?

`fetch` is patched by Next and participates in the Data Cache. **axios is not.** This is the most
common caching bug in this stack: a page marked `revalidate = 60` whose axios call runs on every
render because it was never cacheable in the first place.

### Bad — axios in a page that expects ISR

```tsx
// app/products/page.tsx
import { railsServer } from '@/api/rails-server'; // axios instance

export const revalidate = 60; // has no effect on the axios call below

export default async function ProductsPage() {
  const { data } = await railsServer.get('/api/v1/products');
  return <ProductGrid products={data.data} />;
}
```

The *page* may be cached by the full-route cache, but the fetch itself is uncacheable and
untaggable — `revalidateTag('products')` can never invalidate it.

### Good — `fetch` with tags for server-side reads

```ts
// src/api/products.ts
import 'server-only';
import type { Product } from '@/types/product';

export async function fetchProducts(): Promise<Product[]> {
  const response = await fetch(`${process.env.RAILS_INTERNAL_URL}/api/v1/products`, {
    headers: { 'X-Api-Key': process.env.RAILS_API_KEY! },
    next: { revalidate: 60, tags: ['products'] },
  });

  if (!response.ok) throw new Error(`Rails returned ${response.status} for /products`);

  const body: { data: Product[] } = await response.json();
  return body.data;
}
```

```tsx
// app/products/page.tsx
import { fetchProducts } from '@/api/products';

export default async function ProductsPage() {
  const products = await fetchProducts();
  return <ProductGrid products={products} />;
}
```

Rule of thumb for this stack: **`fetch` for server-side reads that should be cached; axios for
Client Components and for server actions** (mutations, which are never cached anyway).

---

## Decision: `revalidatePath` or `revalidateTag`?

Tag the data, not the URL. A tag invalidates every route that read that data; a path only fixes
the one route you remembered.

### Bad — path-guessing after a mutation

```ts
'use server';

export async function updateProduct(id: string, formData: FormData) {
  await railsServer.patch(`/api/v1/products/${id}`, parse(formData));

  revalidatePath('/products');
  // Forgot /products/[id], /categories/[slug], the homepage carousel, and the sitemap.
  // Every new page that lists products silently starts serving stale data.
}
```

### Good — tag at the read, invalidate at the write

```ts
// src/api/products.ts — reads declare their tags
export async function fetchProducts() {
  const res = await fetch(url('/api/v1/products'), {
    next: { tags: ['products'] },
  });
  return (await res.json()).data;
}

export async function fetchProduct(id: string) {
  const res = await fetch(url(`/api/v1/products/${id}`), {
    next: { tags: ['products', `product:${id}`] }, // collection tag + entity tag
  });
  return (await res.json()).data;
}
```

```ts
// src/actions/products.ts — the write invalidates by tag (Next.js 15)
'use server';

import { revalidateTag } from 'next/cache';

export async function updateProduct(id: string, formData: FormData) {
  const parsed = UpdateProductSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { ok: false as const, fieldErrors: parsed.error.flatten().fieldErrors };

  await railsServer.patch(`/api/v1/products/${id}`, parsed.data);

  revalidateTag(`product:${id}`); // every page showing this product
  revalidateTag('products');      // every page listing products
  return { ok: true as const };
}
```

```ts
// Next.js 16 — the same action; the one-argument revalidateTag is deprecated there
import { updateTag } from 'next/cache';

updateTag(`product:${id}`); // expired now: the editor's next request waits for fresh data
updateTag('products');
```

Use `revalidatePath` only when the thing that changed genuinely *is* a route — e.g.
`revalidatePath('/sitemap.xml')`, or `revalidatePath('/orders/[id]', 'page')` for a dynamic
segment shape.

---

## Decision: invalidating from Rails, not from Next

When a Sidekiq job or a Rails admin action changes content, Next has no idea. Expose a Route
Handler with a shared secret and have Rails call it.

```ts
// app/api/revalidate/route.ts
import { randomUUID } from 'node:crypto';
import { revalidateTag } from 'next/cache';
import { NextResponse, type NextRequest } from 'next/server';
import { z } from 'zod';
import { validationErrorBody } from '@/api/http/errors'; // the house envelope helper

const Body = z.object({ tags: z.array(z.string().min(1)).max(20) });

export async function POST(request: NextRequest) {
  const requestId = request.headers.get('x-request-id') ?? randomUUID();
  if (request.headers.get('x-revalidate-secret') !== process.env.REVALIDATE_SECRET) {
    return NextResponse.json(
      { error: 'Not authenticated', code: 'UNAUTHENTICATED', status: 401, requestId },
      { status: 401 },
    );
  }

  const parsed = Body.safeParse(await request.json());
  if (!parsed.success) {
    return NextResponse.json(validationErrorBody(parsed.error, requestId), { status: 422 });
  }

  // Next.js 16: (tag) => revalidateTag(tag, { expire: 0 }). Never forEach(revalidateTag): 16 reads the index as the profile
  parsed.data.tags.forEach((tag) => revalidateTag(tag));
  return NextResponse.json({ revalidated: parsed.data.tags });
}
```

```ruby
# app/jobs/next_revalidation_job.rb
class NextRevalidationJob < ApplicationJob
  queue_as :default

  def perform(tags)
    Faraday.post("#{ENV.fetch('NEXT_BASE_URL')}/api/revalidate") do |req|
      req.headers['Content-Type'] = 'application/json'
      req.headers['x-revalidate-secret'] = ENV.fetch('REVALIDATE_SECRET')
      req.body = { tags: Array(tags) }.to_json
    end
  end
end
```

Never leave this endpoint unauthenticated — it is a free cache-stampede lever for anyone who
finds it. Its refusals are an endpoint's errors, so they carry the house envelope (`error`, `code`,
`status`, `requestId`), and `validationErrorBody` lists every issue in a bad payload →
`@skills/std-api-design/references/errors-typescript.md`.

---

## Decision: deduping repeated reads within one request

Identical `fetch` calls in the same render pass are deduped automatically. Non-`fetch` work
(axios, a DB call) is not — wrap it in `cache()`.

### Bad — the session is fetched five times per page

```ts
// called by the layout, the page, and three child components
export async function getSession() {
  const token = (await cookies()).get('session')?.value;
  return railsServer.get('/api/v1/me', { headers: { Authorization: `Bearer ${token}` } });
}
```

### Good — memoized per request

```ts
// src/lib/auth.ts
import 'server-only';
import { cache } from 'react';
import { cookies } from 'next/headers';
import { redirect } from 'next/navigation';
import { railsServer } from '@/api/rails-server';
import type { Session } from '@/types/session';

export const getSession = cache(async (): Promise<Session | null> => {
  const token = (await cookies()).get('session')?.value;
  if (!token) return null;

  try {
    const { data } = await railsServer.get<{ data: Session }>('/api/v1/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return { ...data.data, token };
  } catch {
    return null;
  }
});

export async function requireSession(): Promise<Session> {
  const session = await getSession();
  if (!session) redirect('/login');
  return session;
}
```

`cache()` scopes to a single request — it is a dedupe, not a cross-user cache. Never use
`unstable_cache` for per-user data; you will serve one user's session to another.

`Session` also carries the user's permission rules from `/me`, so the layout's CASL ability and
every gate below it read this one memoized call rather than refetching. The payload contract is
owned by `@skills/access-control-designer/references/ui-gates.md`.

---

## Decision: pre-rendering dynamic segments

```tsx
// app/products/[slug]/page.tsx
import { notFound } from 'next/navigation';
import { fetchProduct, fetchTopProductSlugs } from '@/api/products';

export const revalidate = 3600;
export const dynamicParams = true; // slugs not listed below render on-demand, then cache

export async function generateStaticParams() {
  const slugs = await fetchTopProductSlugs(); // build the top N, not all 50k
  return slugs.map((slug) => ({ slug }));
}

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await fetchProduct(slug);
  if (!product) notFound();

  return <ProductDetail product={product} />;
}
```

`params` and `searchParams` are Promises in current Next.js — `await` them. Set
`dynamicParams = false` only when the full set is known at build and unknown slugs should 404.

---

## Decision: revalidating a drill-down level

A write to one record changes the lists and overview counts above it, not just its own page.

- **Tag a shared level with its own entity and its ancestors** — `tags: ['asset:9', 'site:42',
  'region:7']` on the `fetch`, or `cacheTag(...)` under `cacheComponents`. Invalidating an
  ancestor's tag then clears every level cached beneath it; the IDs come from the `ancestorIds` the
  change event carries. One `cacheTag` call takes at most 128 tags of at most 256 characters, and
  anything beyond is dropped with only a console warning (Next.js docs — cacheTag).
- **A permission-scoped level is per-user data** — it never enters a shared cache or carries a tag.
  It renders dynamically, or under `'use cache: private'` (Next.js docs — Caching).
- **A subtree by path** is `revalidatePath(path, 'layout')`: that layout, every nested layout and
  every page beneath. A `'page'` revalidation of `/orders/[id]` does not reach
  `/orders/[id]/shipments` (Next.js docs — revalidatePath).
- **Check the pinned major before copying a call.** On Next.js 16 the one-argument
  `revalidateTag(tag)` used on 15 is deprecated: it behaves like `{ expire: 0 }` and fails
  type-checking. A server action whose user must see their own write calls `updateTag(tag)` — it
  works only inside Server Actions. A Route Handler, like the Rails webhook above, calls
  `revalidateTag(tag, { expire: 0 })` when the data must go at once, or `revalidateTag(tag, 'max')`
  where serving stale content while it refreshes is acceptable. Either way the revalidation runs on
  the next request for the data, not at the call (Next.js docs — revalidateTag; Next.js docs —
  updateTag).

Which levels are per-user, the event payload, and per-level ETags →
`@skills/std-api-design/references/drill-down-resources.md`.

---

## Debugging: "why is my page dynamic?"

```ts
// next.config.ts
const nextConfig = {
  logging: { fetches: { fullUrl: true } }, // logs every server fetch + cache hit/miss in dev
};
export default nextConfig;
```

Then `next build` prints a per-route legend: `○ (Static)`, `● (SSG)`, `ƒ (Dynamic)`. If a route
you expect to be static is `ƒ`, something in its tree read `cookies()`/`headers()` — often a
shared analytics or session helper imported by a layout.

---

## Sources

- Next.js docs — cacheTag — https://nextjs.org/docs/app/api-reference/functions/cacheTag
- Next.js docs — Caching — https://nextjs.org/docs/app/getting-started/caching
- Next.js docs — revalidatePath — https://nextjs.org/docs/app/api-reference/functions/revalidatePath
- Next.js docs — revalidateTag — https://nextjs.org/docs/app/api-reference/functions/revalidateTag
- Next.js docs — updateTag — https://nextjs.org/docs/app/api-reference/functions/updateTag
