---
paths:
  - "terraform/**"
  - "infra/**"
  - "docker-compose*.yml"
  - "Dockerfile*"
  - ".github/workflows/**"
  - "deploy/**"
---

# Infrastructure Conventions

## Docker Compose (Local Development)
- `docker-compose.yml` for core services: Rails app, PostgreSQL + PostGIS, Redis, Centrifugo
- `docker-compose.override.yml` for developer-specific settings (gitignored)
- Use named volumes for data persistence (postgres_data, redis_data)
- Pin image versions — never use `latest` in committed files
- Health checks for all services
- Use `.env.development` for local config, never commit real secrets

## Terraform (Infrastructure as Code)
- Organize by environment: `terraform/environments/{dev,staging,production}/`
- Shared modules in `terraform/modules/`
- Remote state in S3 (AWS) or GCS (GCP) with state locking (DynamoDB/GCS)
- Always run `terraform plan` before `terraform apply`
- Tag all resources: `project`, `environment`, `team`, `managed-by: terraform`
- Use variables with type constraints and descriptions
- Never hardcode secrets — use AWS Secrets Manager or GCP Secret Manager
- Module structure:
  ```
  terraform/
  ├── modules/
  │   ├── networking/
  │   ├── database/      # RDS PostgreSQL with PostGIS
  │   ├── redis/          # ElastiCache
  │   ├── ecs/            # Rails app containers
  │   └── centrifugo/     # Centrifugo service
  ├── environments/
  │   ├── dev/
  │   ├── staging/
  │   └── production/
  └── shared/             # Shared resources (ECR, IAM)
  ```

## AWS Services (Primary Cloud)
- **Compute**: ECS Fargate for Rails app (containerized)
- **Database**: RDS PostgreSQL with PostGIS extension enabled
- **Cache**: ElastiCache Redis for caching and Sidekiq
- **Storage**: S3 for file uploads (ActiveStorage backend)
- **CDN**: CloudFront for static assets and API caching
- **DNS**: Route 53 for domain management
- **Secrets**: AWS Secrets Manager for all credentials
- **Monitoring**: CloudWatch for logs and metrics
- **CI/CD**: GitHub Actions deploying to ECS
- **Real-time**: ECS or EC2 for Centrifugo, ALB with WebSocket support

## GCP Services (Secondary)
- Use when specific GCP services are needed (Maps, ML, BigQuery)
- Authenticate via service accounts with minimal permissions
- Store GCP credentials in AWS Secrets Manager (single source of truth)

## Docker Best Practices
- Multi-stage builds for Rails:
  - Stage 1: Build (install gems, precompile assets)
  - Stage 2: Runtime (copy built artifacts, minimal base image)
- Use `ruby:x.y-slim` as base image
- `.dockerignore` must exclude: `.git`, `node_modules`, `tmp`, `log`, `.env*`
- Run as non-root user in production
- Pin gem versions with `Gemfile.lock`

## CI/CD (GitHub Actions)
- Run on PR: lint (rubocop, eslint), test (rspec, jest), security scan
- Deploy to staging on merge to `develop`
- Deploy to production on merge to `main` (with manual approval)
- Cache gems and node_modules between runs
- Run database migrations as a separate step before deploy
- Smoke tests after deployment

## Environment Configuration
- Use environment variables for all configuration
- Never commit `.env` files with real values
- Maintain `.env.example` with all required variables (empty values)
- Environment variable naming: `RAILS_ENV`, `DATABASE_URL`, `REDIS_URL`, `CENTRIFUGO_API_KEY`
- Use `dotenv-rails` for local development only

## Cost Optimization

### Reserved Instances and Savings Plans
- Use **Compute Savings Plans** (1-year or 3-year) for predictable ECS Fargate workloads — up to 50% savings.
- Use **RDS Reserved Instances** for production databases with steady-state usage.
- Review Savings Plan utilization monthly — adjust coverage if workloads change.

### Right-Sizing
- Review ECS task CPU/memory allocation quarterly. Downsize over-provisioned tasks.
- Use **AWS Compute Optimizer** recommendations for RDS instance class and ECS task sizing.
- ElastiCache: Start with `cache.t3.medium`, scale up only when memory usage exceeds 65%.
- Avoid paying for idle resources — use auto-scaling policies for ECS services.

### Cost Allocation and Visibility
- Tag all resources with: `project`, `environment`, `team`, `cost-center`.
- Enable **AWS Cost Explorer** and set up monthly budget alerts.
- Use **Cost Anomaly Detection** to catch unexpected spend spikes.
- Review per-service cost breakdown monthly in team standup.

### Storage Optimization
- S3: Use **Intelligent-Tiering** for infrequently accessed objects. Set lifecycle policies to archive or delete old objects.
- RDS: Delete old manual snapshots. Automated snapshots use included storage first.
- ECR: Set lifecycle policies to expire untagged images older than 30 days.

### FinOps Review Cadence
- **Weekly**: Check Cost Anomaly Detection alerts.
- **Monthly**: Review Cost Explorer dashboard, compare against budget.
- **Quarterly**: Right-sizing review, Savings Plan coverage evaluation, unused resource cleanup.
