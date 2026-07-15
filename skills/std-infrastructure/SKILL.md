---
name: std-infrastructure
description: Infrastructure standards — Terraform, Docker Compose, AWS, GCP, Vercel, CI/CD. Use when changing IaC, containers, pipelines, or deployment config.
paths:
  - "**/*.tf"
  - "**/*.tfvars"
  - "**/terraform/**"
  - "**/infra/**"
  - "**/docker-compose*.yml"
  - "**/Dockerfile*"
  - "**/.github/workflows/**"
  - "**/deploy/**"
---

# Infrastructure Conventions

AWS is the primary cloud; GCP is secondary (Maps, ML, BigQuery only). Vercel is the primary
Next.js target. All infrastructure is Terraform. Local development is Docker Compose.

## Non-negotiables (apply to every infrastructure change)

- **No secrets in the repo, ever.** No credentials in `.tf`, `.tfvars`, `.env`, task definitions,
  CI YAML, or Dockerfiles. Secrets live in **AWS Secrets Manager** (single source of truth) and
  are referenced, not copied.
- **Prefer no credential at all.** CI authenticates by **federation, not keys** — OIDC to AWS,
  Workload Identity Federation to GCP. A credential that does not exist cannot leak, expire, or
  be rotated late. A static key is the fallback, not the default; when one is genuinely
  unavoidable it goes in AWS Secrets Manager like any other.
- **Pin every version.** Image tags, provider versions, `Gemfile.lock`, `package-lock.json`.
  `latest` is never allowed in a committed file; deploys use immutable git-SHA tags.
  **A GitHub Action tag is not a pin** — `uses: foo/bar@v4` is a *mutable* tag the author can
  move, so a third-party action runs code you never reviewed with your token. Pin to the full
  commit SHA and let Dependabot bump it (`references/github-actions.md`).
- **Tag every resource**: `project`, `environment`, `team`, `managed-by = "terraform"` (plus
  `cost-center` where spend is tracked). Enforce via provider `default_tags`, not copy-paste.
- **`terraform plan` before `terraform apply`.** Read the plan. Remote state with locking always
  (S3 + DynamoDB on AWS, GCS on GCP), one state file per environment.
- **Everything is an environment variable.** Maintain `.env.example` with every required key and
  empty values. Canonical names: `RAILS_ENV`, `DATABASE_URL`, `REDIS_URL`, `CENTRIFUGO_API_KEY`.
  `dotenv-rails` is development-only.
- **Production containers run as non-root** from a multi-stage build on a slim base.
- **No direct pushes to `main`.** Every PR passes lint + test + security scan.

## Layout

Terraform is organized by environment directory, not workspace:

```
terraform/
├── modules/        # networking, database (RDS+PostGIS), redis (ElastiCache), ecs, centrifugo
├── environments/   # dev, staging, production — each with its own state file
└── shared/         # ECR, IAM
```

## The AWS stack (defaults — deviate only with a reason)

| Concern | Service |
|---|---|
| Compute | ECS Fargate (Rails, Sidekiq, Centrifugo) |
| Database | RDS PostgreSQL, PostGIS extension enabled |
| Cache / Queues | ElastiCache Redis (Sidekiq needs `maxmemory-policy = noeviction`) |
| Storage / CDN | S3 (ActiveStorage) + CloudFront |
| DNS | Route 53 |
| Secrets | AWS Secrets Manager |
| Monitoring | CloudWatch logs + metrics |
| Real-time | Centrifugo on ECS behind an ALB with a raised idle timeout (WebSockets) |
| CI/CD | GitHub Actions → ECS, authenticating via **OIDC role assumption** (no static keys) |

## Local development

`docker-compose.yml` (committed) runs Rails, PostgreSQL + PostGIS, Redis, Centrifugo.
`docker-compose.override.yml` is gitignored for per-developer settings. Named volumes
(`postgres_data`, `redis_data`) for persistence. Health checks on every service, and dependents
wait with `condition: service_healthy`. `.dockerignore` must exclude `.git`, `node_modules`,
`tmp`, `log`, `.env*`.

## Deployment flow

- **PR** → lint (rubocop, eslint), test (rspec, vitest), security scan, build verification.
  Cache gems and `node_modules`. Web PRs also run `tsc --noEmit` and the bundle budget check
  (300 KB initial JS for Vite, 200 KB client bundle for Next.js).
- **Merge to `develop`** → auto-deploy to staging.
- **Merge to `main`** → production behind a **manual approval gate**.
- **Migrations run as a separate step before the deploy** — never in a container entrypoint.
- **Smoke tests run after every deployment.**
- Frontend targets: Vite SPA → S3 + CloudFront; Next.js → Vercel (ECS as the alternative).

## Deep guides (read on demand, do not preload)

- Compose stacks, multi-stage Dockerfiles, `.dockerignore`, env config → `references/docker-and-compose.md`
- Terraform layout, remote state, variable declaration, tagging, getting secrets into resources → `references/terraform-mechanics.md`
- RDS PostgreSQL + PostGIS parameter groups, ElastiCache Redis for cache/Sidekiq → `references/aws-data-services.md`
- ECS Fargate task definitions and services, autoscaling, ALB with WebSockets → `references/aws-compute-and-networking.md`
- GCP Workload Identity Federation (keyless CI), the `attribute_condition` that scopes it to your repo, when a key is unavoidable and where it lives, GCS backend, service selection → `references/gcp-secondary-cloud.md`
- GitHub Actions PR checks (rubocop/rspec/vitest/security), OIDC to AWS → `references/ci-pipeline.md`
- Workflow supply chain (pin actions to a SHA, Dependabot), `permissions` least privilege, concurrency groups for deploys, reusable workflows vs composite actions, environments, the `pull_request_target` hole → `references/github-actions.md`
- Rails → ECS deploy: immutable SHA tags, migrations as a task, wait, smoke test → `references/backend-deploys.md`
- Vite SPA → S3/CloudFront, Next.js → Vercel or ECS standalone, bundle budgets → `references/frontend-deploys.md`
- Savings Plans, right-sizing, budgets and anomaly detection, storage lifecycle, FinOps cadence → `references/cost-optimization.md`
