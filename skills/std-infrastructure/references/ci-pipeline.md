# CI Pipeline — Pull Request Checks and AWS Authentication

What GitHub Actions runs on a pull request, and how any AWS-touching workflow authenticates. For
what happens after the merge see `backend-deploys.md` (Rails → ECS) and `frontend-deploys.md`
(Vite → S3/CloudFront, Next.js → Vercel).

Load-bearing rules restated (they hold even if you read nothing else):
- **Every PR must pass lint + test + security scan before merge.** No direct pushes to `main`.
- **No long-lived AWS keys in CI** — GitHub Actions authenticates via OIDC role assumption.
- **Cache gems and `node_modules`** between runs or CI time balloons.
- Pin action and language versions; `latest` is never allowed in a committed file.

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

The web PR gates (bundle size budget, Lighthouse) are in `frontend-deploys.md`.

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
