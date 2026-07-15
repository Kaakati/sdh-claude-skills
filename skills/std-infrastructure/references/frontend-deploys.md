# Frontend Deploys — Vite SPA, Next.js, and Web Pipeline Gates

Hosting targets for the web frontends: **Vite SPA → S3 + CloudFront**, **Next.js → Vercel** (ECS as
the alternative). For PR checks and OIDC setup see `ci-pipeline.md`; for the Rails deploy see
`backend-deploys.md`.

Load-bearing rules restated (they hold even if you read nothing else):
- **Every PR must pass lint + test + security scan before merge.** No direct pushes to `main`; production is behind a manual approval gate.
- **No long-lived AWS keys in CI** — GitHub Actions authenticates via OIDC role assumption.
- **Smoke tests run after every deployment.**
- **Production containers run as non-root** from a multi-stage build on a slim base.
- **Bundle budgets are enforced, not printed**: 300 KB initial JS (Vite), 200 KB client bundle (Next.js).

---

## Decision: how do I deploy the Vite SPA

Target: **S3 + CloudFront**. `npm run build` produces `web/dist/`.

Two cache classes, and getting them backwards is the classic outage: hashed assets are immutable and cached for a year; `index.html` must never be cached, or users pin to a stale bundle referencing deleted asset hashes.

SPA routing needs a CloudFront custom error response mapping 404 → `/index.html` (200), or a deep link returns the S3 404 page.

### Bad

```yaml
      - run: npm run build
      - run: aws s3 sync dist/ s3://web-prod/ --delete
        # BAD: default cache headers on everything; index.html gets cached by CloudFront
      - run: aws cloudfront create-invalidation --distribution-id $ID --paths "/*"
        # BAD: invalidating /* on every deploy throws away the entire cache and costs per path
```

### Good

```yaml
# .github/workflows/deploy-web.yml
      - run: npm ci
        working-directory: web
      - run: npm run build
        working-directory: web

      # 1. Hashed assets first, long immutable cache. Upload before index.html so
      #    the new index never points at assets that are not yet in the bucket.
      - name: Sync hashed assets
        run: |
          aws s3 sync web/dist/ s3://web-prod/ \
            --exclude "index.html" \
            --cache-control "public, max-age=31536000, immutable"

      # 2. index.html last, never cached.
      - name: Upload index.html
        run: |
          aws s3 cp web/dist/index.html s3://web-prod/index.html \
            --cache-control "no-cache" \
            --content-type "text/html"

      # 3. Invalidate only the entry point — hashed assets never need invalidating.
      - name: Invalidate
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/index.html"
```

CloudFront SPA fallback:

```hcl
resource "aws_cloudfront_distribution" "web" {
  # ...
  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 403   # S3 returns 403 for missing keys on OAC origins
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }
}
```

---

## Decision: how do I deploy Next.js

**Vercel is the primary target.** Connect the Git repository — preview deployments are created automatically for every PR (a unique URL for QA), and production deploys on `main`. Environment variables are set in the Vercel dashboard, per environment. Rollback is `vercel rollback` or the dashboard.

Custom headers, redirects, and rewrites live in `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" },
        { "key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload" }
      ]
    },
    {
      "source": "/_next/static/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ],
  "redirects": [
    { "source": "/docs", "destination": "/documentation", "permanent": true }
  ],
  "rewrites": [
    { "source": "/api/v1/:path*", "destination": "https://api.example.com/api/v1/:path*" }
  ]
}
```

### Alternative: Next.js on AWS ECS

Use when the org requires everything in one VPC/account. Set `output: 'standalone'` so the Docker image ships only the traced dependencies, and serve `_next/static/` from S3 behind CloudFront rather than from the Node server.

```ts
// next.config.ts
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  assetPrefix: process.env.NEXT_PUBLIC_ASSET_PREFIX, // https://cdn.example.com
};

export default nextConfig;
```

```dockerfile
# syntax=docker/dockerfile:1
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

# standalone output already contains a minimal node_modules
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=build --chown=nextjs:nodejs /app/public ./public

USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
```

Deploy as an ECS Fargate service behind the ALB. Environment variables come from the ECS task definition; secrets from AWS Secrets Manager via the `secrets` block (see `aws-compute-and-networking.md`). Note that `NEXT_PUBLIC_*` values are **inlined at build time** — they must be build args, not runtime task-definition env vars.

---

## Decision: what gates the web pipeline

- **PR checks**: `tsc --noEmit`, ESLint + Prettier, Vitest unit tests, build verification.
- **Staging**: auto-deploy on merge to `main`.
- **Production**: manual approval gate plus a Lighthouse CI score check.
- **Preview environments**: every PR branch gets a unique URL (Vercel preview, or an S3 subdirectory for the Vite SPA).
- **Bundle size budget**: fail CI if initial JS exceeds **300 KB (Vite)** or the client bundle exceeds **200 KB (Next.js)**.

Enforce the budget rather than printing it:

```ts
// web/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    // Vite warns above this; CI turns the warning into a failure (see below).
    chunkSizeWarningLimit: 300,
  },
});
```

```yaml
      - name: Enforce bundle budget (300KB initial JS)
        working-directory: web
        run: |
          BYTES=$(find dist/assets -name 'index-*.js' -printf '%s\n' | sort -rn | head -1)
          LIMIT=$((300 * 1024))
          echo "Initial JS: $BYTES bytes (limit $LIMIT)"
          test "$BYTES" -le "$LIMIT" || { echo "Bundle budget exceeded"; exit 1; }

      - name: Lighthouse CI
        run: npx --yes @lhci/cli@0.14.x autorun --collect.url=https://staging.example.com
```
