---
name: terraform
description: |
  Terraform infrastructure-as-code best practices with 47 rules across 9 categories.
  Covers state management, security, module design, resource patterns, variables,
  networking, data stores, compute, and cost optimization for AWS deployments.
  Triggers on "terraform", "infrastructure as code", "IaC", "HCL",
  "terraform module", "terraform state", or "terraform plan".
model: sonnet
---

# Terraform Infrastructure-as-Code

Enterprise Terraform standards for our AWS stack: ECS Fargate, RDS PostgreSQL+PostGIS, ElastiCache Redis, S3, CloudFront, Centrifugo, with directory-based environment isolation and remote state.

## When to Apply

Reference these guidelines when:
- Writing or reviewing Terraform configurations
- Creating or updating infrastructure modules
- Managing Terraform state (remote backends, imports, moves)
- Designing networking, security groups, or IAM policies
- Provisioning data stores (RDS, ElastiCache, S3)
- Setting up compute resources (ECS Fargate, Lambda)
- Reviewing infrastructure PRs for security and cost

## Quick Decision Matrix

| Decision | Rule | Action |
|----------|------|--------|
| Where to store state? | `state-remote-backend` | S3 + DynamoDB, always |
| Multiple environments? | `state-workspace-isolation` | Directory-based, never workspaces |
| Existing AWS resource? | `state-import-before-adopt` | `terraform import` first |
| Renaming a module? | `state-move-not-destroy` | `moved` block or `state mv` |
| Secrets in HCL? | `sec-no-hardcoded-secrets` | Never. Use Secrets Manager + sensitive vars |
| IAM policy scope? | `sec-iam-least-privilege` | Specific actions + resources, never `*` |
| Security group ingress? | `sec-security-group-restrict` | No `0.0.0.0/0` except ALB 80/443 |
| Provider versions? | `sec-provider-version-constraint` | Pin with `~>` constraints |
| Module structure? | `module-single-responsibility` | One concern per module |
| Resource naming? | `resource-naming-convention` | `{project}-{env}-{service}-{resource}` |
| Tags? | `resource-required-tags` | project, environment, team, managed-by |
| `count` vs `for_each`? | `resource-for-each-over-count` | Always `for_each` for named resources |
| Variable types? | `var-type-constraints` | Explicit type on every variable |
| Subnet design? | `net-multi-az-subnets` | Public/private/data across 2+ AZs |
| RDS configuration? | `data-rds-postgresql-postgis` | Multi-AZ prod, PostGIS, custom params |
| ECS task sizing? | `compute-ecs-fargate-task-definition` | Right-size CPU/memory, use secrets block |
| Dev cost savings? | `cost-dev-environment-scheduling` | Scale to zero off-hours |

## Rule Categories

| # | Category | Prefix | Priority | Rules | Description |
|---|----------|--------|----------|-------|-------------|
| 1 | State Management | `state-` | CRITICAL | 6 | Remote backends, locking, workspace isolation, imports, moves, sensitive outputs |
| 2 | Security | `sec-` | CRITICAL | 7 | Secrets, IAM, encryption, security groups, provider pinning, VPC isolation |
| 3 | Module Design | `module-` | HIGH | 6 | Module structure, inputs/outputs, versioning, composition, documentation |
| 4 | Resource Patterns | `resource-` | HIGH | 6 | Naming, tagging, lifecycle, dependencies, data sources, conditional creation |
| 5 | Variables & Outputs | `var-` | MEDIUM-HIGH | 5 | Typing, validation, defaults, descriptions, output structure |
| 6 | Networking | `net-` | MEDIUM | 5 | VPC design, subnet tiers, NAT, DNS, transit gateway |
| 7 | Data Stores | `data-` | MEDIUM | 5 | RDS, ElastiCache, S3, backups, parameter groups |
| 8 | Compute | `compute-` | MEDIUM | 4 | ECS Fargate, task definitions, autoscaling, health checks |
| 9 | Cost Optimization | `cost-` | LOW-MEDIUM | 3 | Right-sizing, reserved capacity, unused resource cleanup |

## Quick Reference -- All 47 Rules

### State Management (CRITICAL)

- `state-import-before-adopt` -- Import Existing Resources Before Managing
- `state-lock-configuration` -- Configure State Locking
- `state-move-not-destroy` -- Use State Move for Refactoring
- `state-remote-backend` -- Always Use Remote State Backend
- `state-sensitive-outputs` -- Mark Sensitive Outputs
- `state-workspace-isolation` -- Directory-Based Environment Isolation

### Security (CRITICAL)

- `sec-encryption-at-rest` -- Encryption at Rest for All Data Stores
- `sec-encryption-in-transit` -- Encryption in Transit
- `sec-iam-least-privilege` -- IAM Least Privilege
- `sec-no-default-vpc` -- Never Use Default VPC
- `sec-no-hardcoded-secrets` -- No Hardcoded Secrets
- `sec-provider-version-constraint` -- Pin Provider Version Constraints
- `sec-security-group-restrict` -- Restrict Security Group Ingress

### Module Design (HIGH)

- `module-composition-over-monolith` -- Module Composition Over Monolith
- `module-input-output-contract` -- Module Input/Output Contract
- `module-output-minimal` -- Module Output Minimal
- `module-readme-documentation` -- Module README Documentation
- `module-single-responsibility` -- Module Single Responsibility
- `module-version-pinning` -- Module Version Pinning

### Resource Patterns (HIGH)

- `resource-data-source-lookup` -- Resource Data Source Lookup
- `resource-depends-on-sparingly` -- Use depends_on Sparingly
- `resource-for-each-over-count` -- Use for_each Over count
- `resource-lifecycle-rules` -- Resource Lifecycle Rules
- `resource-naming-convention` -- Resource Naming Convention
- `resource-required-tags` -- Resource Required Tags

### Variables & Outputs (MEDIUM-HIGH)

- `var-descriptive-defaults` -- Descriptive Variables with Intentional Defaults
- `var-sensitive-marking` -- Mark Sensitive Variables
- `var-tfvars-per-environment` -- Separate tfvars per Environment
- `var-type-constraints` -- Explicit Type Constraints on Variables
- `var-validation-blocks` -- Validation Blocks on Variables

### Networking (MEDIUM)

- `net-alb-configuration` -- ALB Configuration with HTTPS and Health Checks
- `net-multi-az-subnets` -- Multi-AZ Subnet Tiers
- `net-nat-gateway-ha` -- NAT Gateway High Availability
- `net-private-subnets-for-data` -- Private Subnets for Data Services
- `net-vpc-cidr-planning` -- VPC CIDR Block Planning

### Data Stores (MEDIUM)

- `data-backup-retention` -- Backup Retention Policies
- `data-connection-strings-via-ssm` -- Connection Strings via Secrets Manager
- `data-elasticache-redis` -- ElastiCache Redis with Failover
- `data-rds-postgresql-postgis` -- RDS PostgreSQL with PostGIS Extension
- `data-s3-bucket-policy` -- S3 Bucket Security and Lifecycle

### Compute (MEDIUM)

- `compute-ecr-lifecycle-policy` -- ECR Lifecycle Policy
- `compute-ecs-deployment-configuration` -- ECS Deployment Configuration
- `compute-ecs-fargate-task-definition` -- ECS Fargate Task Definition
- `compute-ecs-service-autoscaling` -- ECS Service Auto Scaling

### Cost Optimization (LOW-MEDIUM)

- `cost-dev-environment-scheduling` -- Dev Environment Scheduling and Scale-to-Zero
- `cost-right-sizing` -- Right-Size Resources per Environment
- `cost-s3-intelligent-tiering` -- S3 Lifecycle Rules and Intelligent Tiering

## Deep guides (read on demand, do not preload)

Every rule id listed above maps to a self-contained file at `rules/<rule-id>.md`, each with its
own bad/good code pair.

**Read only the rule file matching your task** — not the set:

```
rules/<rule-id>.md
```

Loading one ~60-line rule beats skimming a compiled monolith. Do not preload the directory.

Two references cover what spans rules rather than living inside any one of them. Read either only
when the task calls for it:

| Reference | Read it when |
|-----------|--------------|
| `references/repository-layout.md` | Laying out a new Terraform repo, deciding which file a block belongs in, writing `versions.tf`/`locals.tf`, or choosing between per-environment root modules and a single root with `-var-file` |
| `references/enforcement-and-tooling.md` | A hook rejected your edit, a `terraform apply` was gated, or you need to know what the automated checks do not catch |

### Owned elsewhere

- **`std-terraform-conventions`** is the Terraform rule set: it is **scoped to every `**/*.tf` and
  `**/*.tfvars`**, any wrapper directory. File structure, provider constraints, resource naming,
  - **`std-terraform-conventions`** is the house rule set, **path-scoped to `**/*.tf` and
  `**/*.tfvars`**, any wrapper directory. File structure, provider constraints, resource naming,
  the required tag set, backend config, security minimums. Read it before you write `.tf` — the
  scoping gates when it *may* load, it does not put it in front of you. What does fire regardless
  is `terraform-checker.py` on every `.tf` edit, and `terraform-command-gate.py` on the commands.
  Read it too when you are *planning* infrastructure that does not exist yet, since no glob matches
  a file you have not created.
- **`@skills/std-infrastructure/references/terraform-mechanics.md`** — state, variables, tagging and
  secrets as decisions rather than rules. It overlaps `references/repository-layout.md` on two
  questions (where a `.tf` file goes; where tags come from) and **agrees** with it; read either.
  `rules/resource-required-tags.md` is authoritative for the tag set itself.
- **`terraform-checker.py`** warns on `.tf` edits (hardcoded secrets, snake_case naming, the four
  required tags, backend config, provider versions); **`terraform-command-gate.py`** is a three-tier
  gate on the commands. The tag list the hook enforces and the tag list these skills document are
  held in sync by a test — if they ever disagree, that is a bug in the plugin, not in your code.
