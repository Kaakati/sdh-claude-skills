# Terraform Full Reference Guide

Complete reference for all 47 Terraform rules across 9 categories, tailored for our AWS stack: ECS Fargate (Rails + Centrifugo), RDS PostgreSQL+PostGIS, ElastiCache Redis, S3, CloudFront.

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

---

## 1. State Management (CRITICAL) -- 6 Rules

### 1.1 Always Use Remote State Backend (`state-remote-backend`)

**Impact**: CRITICAL

Terraform state must be stored in a remote backend with encryption and versioning. Local state files risk data loss, prevent team collaboration, and cannot be locked for concurrent access.

```hcl
# terraform/environments/production/versions.tf
terraform {
  required_version = ">= 1.6.0"

  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "alias/terraform-state"
    dynamodb_table = "myproject-terraform-locks"
  }
}
```

**Key points**: One S3 bucket for all environments, separate keys per environment. SSE-KMS encryption. S3 versioning enabled. DynamoDB table for state locking.

### 1.2 Configure State Locking (`state-lock-configuration`)

**Impact**: CRITICAL

State locking prevents concurrent modifications that corrupt state.

```hcl
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "myproject-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name      = "myproject-terraform-locks"
    ManagedBy = "terraform"
  }
}
```

**Never** use `-lock=false` in production.

### 1.3 Directory-Based Environment Isolation (`state-workspace-isolation`)

**Impact**: HIGH

Use separate directories per environment, not Terraform workspaces.

```
terraform/
  environments/
    dev/          # Own backend key, own state file
    staging/      # Own backend key, own state file
    production/   # Own backend key, own state file
  modules/        # Shared modules referenced by all environments
```

### 1.4 Import Before Adopt (`state-import-before-adopt`)

**Impact**: HIGH

When bringing existing AWS resources under Terraform management, always import first.

```bash
terraform import aws_db_instance.postgres_db myproject-production-postgres
terraform import aws_s3_bucket.active_storage myproject-production-active-storage
```

After import, run `terraform plan` to verify no destructive changes.

### 1.5 Use State Move for Refactoring (`state-move-not-destroy`)

**Impact**: HIGH

Use `moved` blocks (Terraform 1.1+) or `terraform state mv`. Never destroy and recreate stateful resources.

```hcl
moved {
  from = aws_db_instance.main
  to   = aws_db_instance.postgres_db
}

moved {
  from = aws_ecs_service.rails_app
  to   = module.ecs.aws_ecs_service.rails_app
}
```

### 1.6 Mark Sensitive Outputs (`state-sensitive-outputs`)

**Impact**: MEDIUM

Any output containing credentials must be marked `sensitive = true`.

```hcl
output "database_url" {
  description = "PostgreSQL connection string"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres_db.endpoint}/${var.db_name}?sslmode=require"
  sensitive   = true
}
```

---

## 2. Security (CRITICAL) -- 7 Rules

### 2.1 No Hardcoded Secrets (`sec-no-hardcoded-secrets`)

**Impact**: CRITICAL

Never hardcode passwords, API keys, tokens, or credentials in `.tf` files. Use `sensitive = true` variables, AWS Secrets Manager, or SSM Parameter Store. For ECS, use the `secrets` block with `valueFrom` ARN, never `environment` for sensitive values.

### 2.2 IAM Least Privilege (`sec-iam-least-privilege`)

**Impact**: CRITICAL

No wildcard `Action: "*"` or `Resource: "*"` in IAM policies. Always specify exact actions and resource ARNs.

```hcl
resource "aws_iam_role_policy" "rails_task" {
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource = "${aws_s3_bucket.active_storage.arn}/*"
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = "arn:aws:secretsmanager:${var.region}:${var.account_id}:secret:${var.project_name}/${var.environment}/*"
      }
    ]
  })
}
```

### 2.3 Encryption at Rest (`sec-encryption-at-rest`)

**Impact**: HIGH

All data stores must be encrypted at rest using KMS customer-managed keys: RDS `storage_encrypted = true`, S3 SSE-KMS with `bucket_key_enabled`, ElastiCache `at_rest_encryption_enabled = true`.

### 2.4 Encryption in Transit (`sec-encryption-in-transit`)

**Impact**: HIGH

Enforce TLS for all data paths: RDS `rds.force_ssl = 1`, ElastiCache `transit_encryption_enabled = true`, ALB HTTPS listener with `ELBSecurityPolicy-TLS13-1-2-2021-06`, HTTP redirect to HTTPS, CloudFront `minimum_protocol_version = "TLSv1.2_2021"`.

### 2.5 Security Group Restrictions (`sec-security-group-restrict`)

**Impact**: HIGH

Never allow `0.0.0.0/0` on non-public ports. Only ALB ports 80/443 may have public ingress. ECS ingress from ALB security group only. RDS/Redis ingress from ECS security group only.

```hcl
# Chain: Public (ALB) -> Private (ECS) -> Data (RDS/Redis)
resource "aws_security_group" "alb" {
  ingress { from_port = 443; to_port = 443; protocol = "tcp"; cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_security_group" "ecs_tasks" {
  ingress { from_port = 3000; to_port = 3000; protocol = "tcp"; security_groups = [aws_security_group.alb.id] }
}
resource "aws_security_group" "rds" {
  ingress { from_port = 5432; to_port = 5432; protocol = "tcp"; security_groups = [aws_security_group.ecs_tasks.id] }
}
```

### 2.6 Provider Version Constraints (`sec-provider-version-constraint`)

**Impact**: MEDIUM

Pin all providers with `~>` (pessimistic) constraints. Include `required_version` for Terraform itself.

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = { source = "hashicorp/aws"; version = "~> 5.30" }
  }
}
```

### 2.7 Never Use Default VPC (`sec-no-default-vpc`)

**Impact**: MEDIUM

Always create a dedicated VPC with custom CIDR, three subnet tiers (public/private/data), and proper security controls. Default VPCs have overly permissive defaults.

---

## 3. Module Design (HIGH) -- 6 Rules

### 3.1 Single Responsibility (`module-single-responsibility`)

**Impact**: HIGH

Each module manages one logical concern. Never combine unrelated resources.

```
terraform/modules/
  networking/   # VPC, subnets, NAT, route tables
  database/     # RDS, parameter groups, subnet groups
  redis/        # ElastiCache, subnet groups
  ecs/          # Cluster, services, task definitions
  s3/           # Buckets, policies, lifecycle
  centrifugo/   # Centrifugo WebSocket service
  cloudfront/   # CDN distributions
```

### 3.2 Input/Output Contract (`module-input-output-contract`)

**Impact**: HIGH

Every variable needs a type, description, and validation. Every consumer-needed value gets an output.

```hcl
variable "instance_class" {
  description = "RDS instance class for PostgreSQL"
  type        = string
  default     = "db.r6g.large"

  validation {
    condition     = can(regex("^db\.", var.instance_class))
    error_message = "Instance class must start with 'db.' prefix."
  }
}

variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}
```

### 3.3 Composition Over Monolith (`module-composition-over-monolith`)

**Impact**: MEDIUM

Compose small, focused modules. Maximum 2 levels of nesting. Root modules call child modules; child modules do not call other child modules.

```hcl
# terraform/environments/production/main.tf
module "networking" {
  source = "../../modules/networking"
  vpc_cidr            = var.vpc_cidr
  availability_zones  = var.availability_zones
  environment         = var.environment
}

module "database" {
  source     = "../../modules/database"
  vpc_id     = module.networking.vpc_id
  subnet_ids = module.networking.data_subnet_ids
  environment = var.environment
}

module "ecs" {
  source     = "../../modules/ecs"
  vpc_id     = module.networking.vpc_id
  subnet_ids = module.networking.private_subnet_ids
  db_url_secret_arn = module.database.connection_string_secret_arn
}
```

### 3.4 Module Version Pinning (`module-version-pinning`)

**Impact**: MEDIUM

Pin module sources with version constraints or git refs. Never use unversioned references for remote modules.

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.4"
}

module "custom" {
  source = "git::https://github.com/org/terraform-modules.git//networking?ref=v2.1.0"
}
```

### 3.5 Minimal Outputs (`module-output-minimal`)

**Impact**: LOW

Output only values that consumers need. Group by resource, use consistent naming.

```hcl
output "vpc_id"             { value = aws_vpc.main.id }
output "public_subnet_ids"  { value = aws_subnet.public[*].id }
output "private_subnet_ids" { value = aws_subnet.private[*].id }
output "data_subnet_ids"    { value = aws_subnet.data[*].id }
```

### 3.6 Module Documentation (`module-readme-documentation`)

**Impact**: LOW

Every module needs a README with: purpose, usage example, inputs table, outputs table, and requirements.

---

## 4. Resource Patterns (HIGH) -- 6 Rules

### 4.1 Naming Convention (`resource-naming-convention`)

**Impact**: HIGH

All resources follow: `{project}-{environment}-{service}-{resource}`.

```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-cluster"
}

resource "aws_db_instance" "postgres_db" {
  identifier = "${var.project_name}-${var.environment}-postgres"
}

resource "aws_s3_bucket" "active_storage" {
  bucket = "${var.project_name}-${var.environment}-active-storage"
}
```

### 4.2 Required Tags (`resource-required-tags`)

**Impact**: HIGH

Every taggable resource must have: `Name`, `Environment`, `Project`, `Team`, `ManagedBy`.

```hcl
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Team        = var.team
    ManagedBy   = "terraform"
  }
}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-${var.environment}-vpc"
  })
}
```

### 4.3 `for_each` Over `count` (`resource-for-each-over-count`)

**Impact**: MEDIUM

Use `for_each` for named resources to avoid index-shift problems when items are added/removed.

```hcl
# CORRECT: for_each is stable
resource "aws_subnet" "public" {
  for_each          = toset(var.availability_zones)
  availability_zone = each.value
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, index(var.availability_zones, each.value))
}
```

### 4.4 Lifecycle Rules (`resource-lifecycle-rules`)

**Impact**: HIGH

Protect stateful resources with `prevent_destroy`. Use `create_before_destroy` for zero-downtime compute updates.

```hcl
resource "aws_db_instance" "postgres_db" {
  lifecycle { prevent_destroy = true }
}

resource "aws_ecs_task_definition" "rails_app" {
  lifecycle { create_before_destroy = true }
}

resource "aws_s3_bucket" "active_storage" {
  lifecycle { prevent_destroy = true }
}
```

### 4.5 Prefer Implicit Dependencies (`resource-depends-on-sparingly`)

**Impact**: LOW

Use resource references for implicit dependencies. Only use `depends_on` when Terraform cannot infer the dependency.

### 4.6 Data Source Lookups (`resource-data-source-lookup`)

**Impact**: LOW

Use data sources for dynamic values (AMI IDs, account ID, AZs). Never hardcode them.

```hcl
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" { state = "available" }
```

---

## 5. Variables & Outputs (MEDIUM-HIGH) -- 5 Rules

### 5.1 Type Constraints (`var-type-constraints`)

Always declare explicit types on every variable. Use `object()` for complex structures.

```hcl
variable "ecs_config" {
  description = "ECS service configuration per environment"
  type = object({
    cpu          = number
    memory       = number
    min_tasks    = number
    max_tasks    = number
    health_path  = string
  })
}
```

### 5.2 Validation Blocks (`var-validation-blocks`)

Add `validation` blocks for constrained inputs: CIDRs, ports, environment names.

```hcl
variable "vpc_cidr" {
  type = string
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "Must be a valid CIDR block."
  }
}
```

### 5.3 Sensitive Marking (`var-sensitive-marking`)

Mark `sensitive = true` on all password, token, and key variables. Prevents display in `terraform plan` output and CI logs.

### 5.4 Descriptive Defaults (`var-descriptive-defaults`)

Every variable needs `description`. Only set `default` for truly optional values.

### 5.5 Per-Environment tfvars (`var-tfvars-per-environment`)

Separate `.tfvars` files per environment. Never commit credentials to `.tfvars`.

---

## 6. Networking (MEDIUM) -- 5 Rules

### 6.1 VPC CIDR Planning (`net-vpc-cidr-planning`)

- Production: `/16` (65,536 IPs)
- Dev/Staging: `/20` (4,096 IPs)
- Reserve space for VPC peering and future growth
- Never overlap CIDRs between environments

### 6.2 Multi-AZ Subnets (`net-multi-az-subnets`)

Deploy public, private, and data subnets across 2+ AZs. Production should use 3 AZs.

### 6.3 NAT Gateway HA (`net-nat-gateway-ha`)

One NAT per AZ in production for HA. Single NAT in dev ($32/month savings per gateway).

```hcl
resource "aws_nat_gateway" "main" {
  for_each      = var.environment == "production" ? toset(var.availability_zones) : toset([var.availability_zones[0]])
  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id
}
```

### 6.4 ALB Configuration (`net-alb-configuration`)

HTTPS listener with ACM cert, HTTP redirect to HTTPS, health checks with grace periods. Use `ELBSecurityPolicy-TLS13-1-2-2021-06` or newer.

### 6.5 Private Subnets for Data (`net-private-subnets-for-data`)

RDS, ElastiCache, and ECS tasks in private/data subnets. Only ALB and NAT in public subnets.

---

## 7. Data Stores (MEDIUM) -- 5 Rules

### 7.1 RDS PostgreSQL + PostGIS (`data-rds-postgresql-postgis`)

Multi-AZ for production, custom parameter group, PostGIS extension, `prevent_destroy` lifecycle.

```hcl
resource "aws_db_instance" "postgres_db" {
  identifier          = "${var.project_name}-${var.environment}-postgres"
  engine              = "postgres"
  engine_version      = "15.4"
  multi_az            = var.environment == "production"
  storage_encrypted   = true
  deletion_protection = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 30 : 7
  lifecycle { prevent_destroy = true }
}
```

### 7.2 ElastiCache Redis (`data-elasticache-redis`)

Cluster mode for production, automatic failover, transit + at-rest encryption.

### 7.3 S3 Bucket Policy (`data-s3-bucket-policy`)

Block all public access, enable versioning, SSE-KMS encryption, lifecycle rules.

```hcl
resource "aws_s3_bucket_public_access_block" "active_storage" {
  bucket                  = aws_s3_bucket.active_storage.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
```

### 7.4 Backup Retention (`data-backup-retention`)

- RDS: 7 days dev, 30 days production
- ElastiCache: daily snapshots, 7-day retention
- S3: versioning enabled, lifecycle for old versions

### 7.5 Connection Strings via Secrets Manager (`data-connection-strings-via-ssm`)

Store DATABASE_URL, REDIS_URL in AWS Secrets Manager. Reference in ECS via `secrets` block with `valueFrom` ARN.

---

## 8. Compute (MEDIUM) -- 4 Rules

### 8.1 ECS Fargate Task Definition (`compute-ecs-fargate-task-definition`)

Right-size CPU/memory, `awslogs` driver, health checks, separate task role from execution role.

```hcl
resource "aws_ecs_task_definition" "rails_app" {
  family                   = "${var.project_name}-${var.environment}-rails"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_config.cpu
  memory                   = var.ecs_config.memory
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn
}
```

### 8.2 ECS Service Autoscaling (`compute-ecs-service-autoscaling`)

Target tracking on CPU/memory at 70%. Scale-in cooldown 300s, scale-out cooldown 60s.

### 8.3 ECR Lifecycle Policy (`compute-ecr-lifecycle-policy`)

Expire untagged images after 30 days. Keep last 20 tagged images.

### 8.4 ECS Deployment Configuration (`compute-ecs-deployment-configuration`)

Zero-downtime: `minimum_healthy_percent = 100`, `maximum_percent = 200`, circuit breaker with auto-rollback.

```hcl
resource "aws_ecs_service" "rails_app" {
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 120

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}
```

---

## 9. Cost Optimization (LOW-MEDIUM) -- 3 Rules

### 9.1 Right-Sizing (`cost-right-sizing`)

Start small, scale with metrics. Review quarterly.

| Resource | Dev | Staging | Production |
|----------|-----|---------|------------|
| RDS | db.t3.medium | db.t3.large | db.r6g.xlarge |
| ElastiCache | cache.t3.micro | cache.t3.small | cache.r6g.large |
| ECS CPU/Memory | 256/512 | 512/1024 | 1024/2048 |

### 9.2 S3 Intelligent Tiering (`cost-s3-intelligent-tiering`)

- ActiveStorage: Standard (fast access via CloudFront)
- Backups: Standard > Intelligent Tiering (30d) > Glacier (90d) > Deep Archive (365d)
- Logs: Standard > Standard-IA (30d) > Glacier (90d) > Expire (365d)
- Always add `abort_incomplete_multipart_upload` rule

### 9.3 Dev Environment Scheduling (`cost-dev-environment-scheduling`)

Scale dev ECS to zero off-hours. Skip expensive resources (CloudFront, WAF) in dev. Estimated savings: $200-500/month per dev environment.

---

## Module Structure Reference

```
terraform/
  environments/
    dev/
      main.tf           # Root module composing child modules
      variables.tf      # Environment-specific variable declarations
      outputs.tf        # Environment outputs
      versions.tf       # required_providers + backend config
      dev.tfvars        # Variable values for dev
      locals.tf         # Computed values and common tags
    staging/
    production/
  modules/
    networking/         # VPC, subnets, NAT, route tables, security groups
    database/           # RDS PostgreSQL + PostGIS, parameter groups
    redis/              # ElastiCache Redis, subnet groups
    ecs/                # ECS cluster, services, task definitions
    centrifugo/         # Centrifugo WebSocket service on ECS
    s3/                 # S3 buckets (ActiveStorage, backups, logs)
    cloudfront/         # CloudFront distributions
```

## Enforcement

- **Always-on rule**: `terraform-conventions.md` auto-loads on `terraform/**/*.tf` edits
- **PostToolUse hook**: `terraform-checker.py` validates naming, tags, backend config
- **PreToolUse hook**: `deployment-gate.py` blocks `terraform apply` without confirmation
- **Auto-format**: `auto-format.py` runs `terraform fmt` on saved `.tf` files
