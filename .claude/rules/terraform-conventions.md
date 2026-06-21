---
paths:
  - "**/*.tf"
  - "**/*.tfvars"
---

# Terraform Conventions

## File Structure

Every Terraform module (root or child) must contain:
- `main.tf` — Resources and data sources
- `variables.tf` — All input variables with `type`, `description`, and optional `validation` blocks
- `outputs.tf` — All outputs with `description`
- `versions.tf` — `required_version` and `required_providers` with `~>` version constraints

Root modules (environment directories) additionally require:
- `backend.tf` or backend config in `versions.tf` — Remote state (S3 + DynamoDB)
- `locals.tf` — Computed values and tag maps
- `{env}.tfvars` — Environment-specific variable values

## Provider Constraints

- Pin providers with pessimistic constraints: `version = "~> 5.0"` (allows 5.x, blocks 6.0)
- Never omit version constraints — unversioned providers cause drift across environments
- Lock file (`terraform.lock.hcl`) must be committed to version control

## Resource Naming

- All resource names use `snake_case`: `aws_ecs_service.rails_app`, not `aws_ecs_service.RailsApp`
- Logical names follow: `{service}_{purpose}` — e.g., `main`, `rails_app`, `redis_cache`
- Use `this` only for single-resource modules: `aws_s3_bucket.this`

## Resource Tagging

All taggable resources must include these tags (via `default_tags` or explicit `tags`):
- `project` — Project identifier
- `environment` — `dev`, `staging`, `production`
- `team` — Owning team name
- `managed-by` — `terraform`

Use `default_tags` in the provider block. Merge additional tags per-resource when needed.

## Backend Configuration

- Remote state in S3 with DynamoDB locking for all environments
- Each environment has its own state file — never share state across environments
- State bucket: encryption enabled, versioning enabled, public access blocked
- Key pattern: `{project}/{environment}/terraform.tfstate`

## Variables

- Every variable must have `type` and `description`
- Sensitive values (passwords, tokens, keys) must set `sensitive = true`
- Use `validation` blocks for constrained values (CIDR ranges, port numbers, environment names)
- Never set defaults for required secrets — force explicit assignment via `.tfvars` or `-var`
- Group related variables: prefix with domain (`vpc_cidr`, `rds_instance_class`, `ecs_cpu`)

## Outputs

- Output only values consumed by other modules or needed for debugging
- Mark secrets with `sensitive = true`
- Include `description` on every output
- Name pattern: `{resource}_{attribute}` — e.g., `rds_endpoint`, `vpc_id`

## Security Minimums

- No hardcoded secrets (AWS keys, passwords, database credentials) in `.tf` files
- No `0.0.0.0/0` ingress on non-public ports (only ALB 80/443)
- No `Action: "*"` or `Resource: "*"` in IAM policies — least privilege only
- Encryption at rest for all data stores (RDS, S3, ElastiCache, EBS)
- Encryption in transit (TLS/SSL) for all connections
- No default VPC — always create dedicated VPCs
- Security groups: deny by default, allow specific ports and CIDRs

## State Operations

- Import existing resources before managing: `terraform import`
- Refactor with `terraform state mv`, never destroy-and-recreate
- Mark stateful resources with `prevent_destroy` lifecycle rule (RDS, S3)
- Use `create_before_destroy` for compute resources (ECS, EC2)

## Module Design

- One module, one concern (networking, database, compute)
- Maximum 2 levels of module nesting
- Pin module sources with version constraints
- Use `for_each` over `count` to avoid index-shift problems
- Prefer implicit dependencies — use `depends_on` sparingly
- Use data sources for AMI IDs, account IDs, availability zones

## Environment Isolation

- Directory-based isolation: `terraform/environments/{dev,staging,production}/`
- Shared modules in `terraform/modules/`
- Never use Terraform workspaces for environment separation
- Each environment has independent state, variables, and backend config
