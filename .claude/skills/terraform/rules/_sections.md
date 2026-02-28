# Rule Sections

## Section Definitions

| # | Section | Prefix | Priority | Description |
|---|---------|--------|----------|-------------|
| 1 | State Management | `state-` | CRITICAL | Remote backends, state locking, environment isolation, resource imports, state moves, and sensitive output handling. Mismanaging state leads to infrastructure drift, race conditions, and data loss. |
| 2 | Security | `sec-` | CRITICAL | Secret management, IAM least privilege, encryption at rest and in transit, security group restrictions, provider pinning, and VPC isolation. Security violations are non-negotiable blockers. |
| 3 | Module Design | `module-` | HIGH | Standard module structure, single responsibility, version pinning, composition patterns, documentation, and output conventions. Well-designed modules enable reuse and reduce drift. |
| 4 | Resource Patterns | `resource-` | HIGH | Consistent naming, mandatory tagging, lifecycle protection, explicit dependencies, data source lookups, and conditional resource creation. |
| 5 | Variables & Outputs | `var-` | MEDIUM-HIGH | Type constraints, validation blocks, sensitive flags, descriptive metadata, and output grouping conventions. |
| 6 | Networking | `net-` | MEDIUM | Multi-AZ subnets, subnet tiers (public/private/data), NAT gateway HA, VPC flow logs, and private endpoints for AWS services. |
| 7 | Data Stores | `data-` | MEDIUM | RDS Multi-AZ, custom parameter groups, ElastiCache cluster mode, S3 versioning, and backup retention policies. |
| 8 | Compute | `compute-` | MEDIUM | Fargate CPU/memory sizing, task vs execution IAM roles, autoscaling policies, and health check configuration. |
| 9 | Cost Optimization | `cost-` | LOW-MEDIUM | Right-sizing audits, reserved capacity planning, and unused resource cleanup to control AWS spend. |

## Applicability

All rules apply to Terraform configurations for our AWS infrastructure:
- **Environments**: `terraform/environments/dev/`, `terraform/environments/staging/`, `terraform/environments/production/`
- **Modules**: `terraform/modules/` (reusable infrastructure components)
- **Global**: `terraform/global/` (shared resources like Route53, IAM)

## Stack Context

These rules are tailored for our specific stack:
- **Compute**: ECS Fargate (Rails API, Centrifugo)
- **Database**: RDS PostgreSQL with PostGIS extension
- **Cache/Queue**: ElastiCache Redis (Rails cache + Sidekiq)
- **Storage**: S3 (ActiveStorage attachments, assets)
- **CDN**: CloudFront (static assets, API acceleration)
- **Real-time**: Centrifugo on ECS Fargate (WebSocket channels)
- **CI/CD**: Terraform plan in CI, manual apply for production
