# CI/CD Pipelines and Deployment Targets

Load-bearing rules restated (they hold even if you read nothing else):
- **Every PR must pass lint + test + security scan before merge.** No direct pushes to `main`.
- **`develop` merges deploy to staging automatically. `main` merges deploy to production behind a manual approval gate.**
- **Migrations run as a separate step before the deploy**, never as a container entrypoint.
- **Smoke tests run after every deployment.**
- **No long-lived AWS keys in CI** — GitHub Actions authenticates via OIDC role assumption.

---

## Decision: what runs on a pull request

Lint (`rubocop`, `eslint`), test (`rspec`, `vitest`), security scan, and a build verification. Gems and `node_modules` are cached between runs or CI time balloons.

### Bad — no caching, no service health gating, secrets as long-lived keys

```yaml
# .github/workflows/ci.yml
name: CI
on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
      - run: bundle install          # BAD: no cache, ~90s every run
      - run: bundle exec rspec       # BAD: no database service; will fail or silently skip
      - run: echo "${{ secrets.AWS_SECRET_ACCESS_KEY }}"  # BAD: long-lived key, and echoing it
```

### Good — cached, health-gated services, matrix of checks

```yaml
# .github/workflows/ci.yml
name: CI

on:
  pull_request:
  push:
    branches: [main, develop]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-ruby:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3.6'
          bundler-cache: true        # caches gems keyed on Gemfile.lock
      - run: bundle exec rubocop --parallel

  test-ruby:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:16-3.4
        env:
          POSTGRES_PASSWORD: postgres
        ports: ['5432:5432']
        options: >-
          --health-cmd="pg_isready -U postgres"
          --health-interval=5s --health-timeout=3s --health-retries=10
      redis:
        image: redis:7.2-alpine
        ports: ['6379:6379']
        options: >-
          --health-cmd="redis-cli ping"
          --health-interval=5s --health-timeout=3s --health-retries=10
    env:
      RAILS_ENV: test
      DATABASE_URL: postgres://postgres:postgres@localhost:5432/app_test
      REDIS_URL: redis://localhost:6379/0
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3.6'
          bundler-cache: true
      - run: bundle exec rails db:prepare
      - run: bundle exec rspec

  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npx tsc --noEmit
      - run: npx eslint .
      - run: npx prettier --check .
      - run: npx vitest run --coverage
      - run: npm run build

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3.6'
          bundler-cache: true
      - run: bundle exec brakeman --no-pager --exit-on-warn
      - run: bundle exec bundler-audit check --update
      - run: npm audit --audit-level=high --prefix web
```

---

## Decision: how does CI authenticate to AWS

Use **OIDC role assumption**. Static `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` repo secrets are long-lived credentials with no expiry — one leaked log line is a permanent breach.

### Bad

```yaml
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}       # BAD: never rotates
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-west-1
```

### Good

```yaml
permissions:
  id-token: write     # required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-production
          aws-region: eu-west-1
```

Trust policy on the AWS side, scoped to one repo and one branch:

```hcl
data "aws_iam_policy_document" "github_actions_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:acme/platform:ref:refs/heads/main"]  # not repo:acme/platform:*
    }
  }
}
```

---

## Decision: how do I deploy Rails to ECS

Image tags are **immutable git SHAs**, never `latest` — you cannot roll back to a tag that moved. Migrations run as a standalone ECS task **before** the service update, so a failing migration aborts the deploy rather than crash-looping half the fleet.

### Bad — migrations in the entrypoint, mutable tag

```dockerfile
# BAD: every task on every scale-out event races to run migrations
CMD ["sh", "-c", "bundle exec rails db:migrate && bundle exec rails server -b 0.0.0.0"]
```

```yaml
      - run: docker build -t $ECR/app:latest . && docker push $ECR/app:latest
      - run: aws ecs update-service --cluster prod --service rails --force-new-deployment
      # BAD: no rollback target, no wait, no smoke test — the job goes green before the deploy lands
```

### Good — build once, migrate as a task, update service, wait, smoke test

```yaml
# .github/workflows/deploy-production.yml
name: Deploy production

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.build.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-production
          aws-region: eu-west-1
      - uses: aws-actions/amazon-ecr-login@v2
        id: ecr
      - name: Build and push
        id: build
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build --target production -t "$REGISTRY/app:$TAG" .
          docker push "$REGISTRY/app:$TAG"
          echo "image=$REGISTRY/app:$TAG" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production        # manual approval gate configured on this environment
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-production
          aws-region: eu-west-1

      - name: Run migrations (separate step, before deploy)
        run: |
          TASK_ARN=$(aws ecs run-task \
            --cluster production \
            --task-definition production-rails-migrate \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=DISABLED}" \
            --overrides '{"containerOverrides":[{"name":"rails","command":["bundle","exec","rails","db:migrate"]}]}' \
            --query 'tasks[0].taskArn' --output text)
          aws ecs wait tasks-stopped --cluster production --tasks "$TASK_ARN"
          EXIT=$(aws ecs describe-tasks --cluster production --tasks "$TASK_ARN" \
            --query 'tasks[0].containers[0].exitCode' --output text)
          test "$EXIT" = "0" || { echo "Migration failed with exit $EXIT"; exit 1; }
        env:
          SUBNETS: ${{ vars.PRIVATE_SUBNET_IDS }}
          SG: ${{ vars.APP_SECURITY_GROUP_ID }}

      - name: Render task definition with the new image
        id: taskdef
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: deploy/ecs/production-rails.json
          container-name: rails
          image: ${{ needs.build.outputs.image }}

      - name: Deploy and wait for stability
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.taskdef.outputs.task-definition }}
          cluster: production
          service: production-rails
          wait-for-service-stability: true

      - name: Smoke test
        run: |
          for i in $(seq 1 10); do
            if curl -fsS https://api.example.com/up; then
              curl -fsS https://api.example.com/api/v1/health | tee /dev/stderr | grep -q '"status":"ok"'
              exit 0
            fi
            sleep 10
          done
          echo "Smoke test failed after deploy"; exit 1
```

Staging is the same workflow triggered on `push: branches: [develop]`, targeting the staging cluster, with the `environment: staging` gate removed.

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

Deploy as an ECS Fargate service behind the ALB. Environment variables come from the ECS task definition; secrets from AWS Secrets Manager via the `secrets` block (see `terraform-aws.md`). Note that `NEXT_PUBLIC_*` values are **inlined at build time** — they must be build args, not runtime task-definition env vars.

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
