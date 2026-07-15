# Middleware, SEO metadata, and deployment

Load-bearing rules restated (this file is read standalone):

- Middleware runs on the **Edge Runtime** for every matched request: no Node APIs, no DB, no
  heavy work, no data fetching.
- **Every page must export `metadata` or `generateMetadata`.**
- Vercel is the primary deployment target; ECS Fargate with `output: 'standalone'` is the
  alternative.

---

# Part 1 — Middleware: work that must happen before the route

## Decision: does this belong in middleware?

| Task | Middleware? |
|------|-------------|
| Redirect signed-out users away from `/(dashboard)` | Yes — cheap cookie presence check |
| Locale detection + rewrite | Yes |
| A/B bucketing via cookie | Yes |
| Coarse rate limiting / bot blocking | Yes |
| Verifying a JWT signature against Rails | **No** — network call on every request |
| Loading the user record for the page | **No** — do it in the Server Component |
| Authorization ("can this user edit order 42?") | **No** — Rails decides, per request |

Middleware is a **coarse gate**, never the security boundary. The real authorization check lives
in Rails (Pundit); the page's own `requireSession()` is the second line. Middleware only avoids
rendering a page the user obviously cannot see.

### Bad — a network round-trip on every asset request

```ts
// middleware.ts
import { NextResponse, type NextRequest } from 'next/server';

export async function middleware(request: NextRequest) {
  const token = request.cookies.get('session')?.value;

  // Runs for images, fonts, RSC payloads, prefetches — a Rails call per request.
  const res = await fetch(`${process.env.RAILS_INTERNAL_URL}/api/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) return NextResponse.redirect(new URL('/login', request.url));
  return NextResponse.next();
}
// No matcher: this runs on literally everything.
```

### Good — presence check plus a narrow matcher

```ts
// middleware.ts
import { NextResponse, type NextRequest } from 'next/server';

const PROTECTED = ['/dashboard', '/orders', '/settings'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get('session')?.value);

  if (PROTECTED.some((p) => pathname.startsWith(p)) && !hasSession) {
    const login = new URL('/login', request.url);
    login.searchParams.set('next', pathname); // preserve intent
    return NextResponse.redirect(login);
  }

  if (pathname === '/login' && hasSession) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  const response = NextResponse.next();
  response.headers.set('x-request-id', crypto.randomUUID()); // correlate with Rails logs
  return response;
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|webp)$).*)'],
};
```

The page still calls `requireSession()`. A forged-but-present cookie passes middleware and is
rejected by Rails — that is the intended layering.

Edge Runtime constraints worth remembering: no `fs`, no `crypto` Node module (use Web Crypto),
no `process.env` values that were not inlined at build, and a small code-size budget. Importing a
JWT library that pulls in Node built-ins is the usual cause of a middleware build failure.

---

# Part 2 — SEO metadata

## Decision: static `metadata` or `generateMetadata`?

Static object when the title/description are known at author time. `generateMetadata` when they
depend on fetched data.

### Bad — a dynamic page with a generic title and no canonical

```tsx
// app/products/[slug]/page.tsx
export const metadata = { title: 'Product | MyApp' };
// Every one of 50,000 products shares one title and description.
// Filter params (?sort=price) create duplicate-content URLs with no canonical.
```

### Good

```tsx
// app/products/[slug]/page.tsx
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { fetchProduct } from '@/api/products';

type Props = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const product = await fetchProduct(slug); // deduped with the page's own fetch

  if (!product) return { title: 'Product not found | MyApp' };

  return {
    title: `${product.name} | MyApp`,
    description: product.summary.slice(0, 155),
    alternates: { canonical: `/products/${slug}` },
    openGraph: {
      title: product.name,
      description: product.summary,
      images: [{ url: product.imageUrl, width: 1200, height: 630, alt: product.name }],
      type: 'website',
    },
    twitter: { card: 'summary_large_image' },
    robots: product.published ? undefined : { index: false, follow: false },
  };
}

export default async function ProductPage({ params }: Props) {
  const { slug } = await params;
  const product = await fetchProduct(slug);
  if (!product) notFound();
  return <ProductDetail product={product} />;
}
```

`generateMetadata` and the page both call `fetchProduct` — with `fetch` this is deduped into one
request, which is another reason to prefer `fetch` over axios for server reads.

Set `metadataBase` once in the root layout so relative OG image URLs resolve:

```tsx
// app/layout.tsx
export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL!),
  title: { default: 'MyApp', template: '%s | MyApp' }, // children set only their own segment
};
```

With a `template`, child pages should export `title: 'Orders'`, not `'Orders | MyApp'` — otherwise
you get `Orders | MyApp | MyApp`.

## Sitemap and robots

```ts
// app/sitemap.ts
import type { MetadataRoute } from 'next';
import { fetchProductSlugs } from '@/api/products';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = process.env.NEXT_PUBLIC_SITE_URL!;
  const slugs = await fetchProductSlugs();

  return [
    { url: base, changeFrequency: 'daily', priority: 1 },
    ...slugs.map((slug) => ({
      url: `${base}/products/${slug}`,
      changeFrequency: 'weekly' as const,
      priority: 0.7,
    })),
  ];
}
```

```ts
// app/robots.ts
import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/', disallow: ['/api/', '/dashboard/'] },
    sitemap: `${process.env.NEXT_PUBLIC_SITE_URL}/sitemap.xml`,
  };
}
```

---

# Part 3 — Deployment

## Decision: Vercel or ECS Fargate?

Vercel is the default: preview deployments per PR, ISR and the Data Cache work with no setup,
Image Optimization included. Choose ECS only when a hard requirement forces it — VPC-private
access to RDS/ElastiCache without a tunnel, a compliance boundary that mandates one AWS account,
or co-location with the Rails cluster.

## Vercel

- Connect the Git repo: pushes to `main` → production, PRs → preview URLs.
- Environment variables per environment in the dashboard. Only `NEXT_PUBLIC_*` reaches the
  browser — never prefix a secret.
- `vercel.json` for redirects, headers, and rewrites.

```json
{
  "redirects": [
    { "source": "/shop/:path*", "destination": "/products/:path*", "permanent": true }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload" }
      ]
    }
  ]
}
```

### Bad — a secret shipped to every visitor

```bash
NEXT_PUBLIC_RAILS_API_KEY=sk_live_abc123   # inlined into the client bundle, forever
```

### Good

```bash
RAILS_API_KEY=sk_live_abc123               # server-only; read in Server Components/actions
NEXT_PUBLIC_SITE_URL=https://myapp.com     # genuinely public
```

## AWS ECS Fargate

```ts
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone', // emits .next/standalone with a minimal server.js + traced deps
  images: {
    remotePatterns: [{ protocol: 'https', hostname: 'cdn.myapp.com' }],
  },
};

export default nextConfig;
```

```dockerfile
# Dockerfile
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

`NEXT_PUBLIC_*` values are inlined **at build time** — they must be `ARG`s in the build stage, not
runtime task-definition variables. Server-only secrets go the other way: inject them at runtime
from Secrets Manager via the ECS task definition, never bake them into the image.

Serve `_next/static` through CloudFront (immutable, hashed filenames — cache forever) and pass
everything else to the ALB. ISR on ECS writes to the container filesystem, so it is per-task and
lost on redeploy; if ISR correctness matters across tasks, use a shared cache handler or stay on
Vercel.

Health check for the ALB target group:

```ts
// app/api/health/route.ts
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic'; // never cache a health check

export async function GET() {
  return NextResponse.json({ status: 'ok', uptime: process.uptime() });
}
```
