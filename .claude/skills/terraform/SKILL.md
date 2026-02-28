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
- `state-remote-backend` -- Always use S3 + DynamoDB remote backend with encryption
- `state-lock-configuration` -- Configure DynamoDB state locking for all environments
- `state-workspace-isolation` -- Use directory-based isolation, not Terraform workspaces
- `state-import-before-adopt` -- Import existing resources before managing them
- `state-move-not-destroy` -- Use state mv/moved blocks for refactoring, never destroy-recreate
- `state-sensitive-outputs` -- Mark all secret-bearing outputs as sensitive

### Security (CRITICAL)
- `sec-no-hardcoded-secrets` -- Never hardcode secrets in HCL; use variables + secret managers
- `sec-iam-least-privilege` -- No wildcard Actions or Resources in IAM policies
- `sec-encryption-at-rest` -- Encrypt all data stores: RDS, S3, ElastiCache, EBS
- `sec-encryption-in-transit` -- Enforce HTTPS/TLS for all data in transit
- `sec-security-group-restrict` -- No 0.0.0.0/0 on non-public ports
- `sec-provider-version-constraint` -- Pin all providers with ~> version constraints
- `sec-no-default-vpc` -- Always create dedicated VPCs, never use default

### Module Design (HIGH)
- `module-standard-structure` -- Follow standard module layout (main.tf, variables.tf, outputs.tf)
- `module-single-responsibility` -- One module = one logical resource group
- `module-version-pinning` -- Pin module sources with version/ref constraints
- `module-composition-over-inheritance` -- Compose small modules, don't build monoliths
- `module-readme-and-examples` -- Every module needs README.md and examples/
- `module-output-all-ids` -- Expose all resource IDs and ARNs as outputs

### Resource Patterns (HIGH)
- `resource-consistent-naming` -- Use project-env-resource naming convention
- `resource-mandatory-tags` -- Tag all resources with project, environment, team, managed-by
- `resource-lifecycle-prevent-destroy` -- Protect stateful resources with prevent_destroy
- `resource-explicit-dependencies` -- Use depends_on only when implicit deps are insufficient
- `resource-data-source-over-hardcode` -- Look up IDs via data sources, never hardcode
- `resource-conditional-creation` -- Use count/for_each for optional resources

### Variables & Outputs (MEDIUM-HIGH)
- `var-type-constraints` -- Always declare variable types explicitly
- `var-validation-blocks` -- Add validation blocks for constrained inputs
- `var-sensitive-flag` -- Mark sensitive variables and outputs
- `var-descriptive-metadata` -- Every variable needs a description
- `var-output-grouping` -- Group outputs by resource with consistent naming

### Networking (MEDIUM)
- `net-multi-az-subnets` -- Deploy across 3+ AZs for high availability
- `net-subnet-tiers` -- Separate public, private, and data subnets
- `net-nat-gateway-ha` -- One NAT gateway per AZ for production
- `net-flow-logs` -- Enable VPC flow logs for security auditing
- `net-private-endpoints` -- Use VPC endpoints for AWS service access

### Data Stores (MEDIUM)
- `data-rds-multi-az` -- Enable Multi-AZ for production RDS instances
- `data-rds-parameter-group` -- Use custom parameter groups, never default
- `data-elasticache-cluster-mode` -- Use cluster mode for production Redis
- `data-s3-versioning` -- Enable versioning on all S3 buckets
- `data-backup-retention` -- Configure automated backups with adequate retention

### Compute (MEDIUM)
- `compute-fargate-sizing` -- Right-size Fargate CPU/memory for workload
- `compute-task-iam-role` -- Separate task role from execution role
- `compute-autoscaling-policy` -- Configure target tracking autoscaling
- `compute-health-check` -- Configure meaningful health checks with grace periods

### Cost Optimization (LOW-MEDIUM)
- `cost-right-sizing` -- Audit and right-size instances quarterly
- `cost-reserved-capacity` -- Use reserved instances/savings plans for steady-state
- `cost-unused-resource-cleanup` -- Remove unattached EIPs, volumes, old snapshots

## Full Reference

For the complete guide with all rules and detailed code examples: `references/full-guide.md`
