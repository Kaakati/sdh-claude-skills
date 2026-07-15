# Terraform Mechanics — Layout, State, Variables, Tagging, Secrets

Applies to any `.tf` change regardless of which AWS service you are declaring. For the service
modules themselves see `aws-data-services.md` (RDS/PostGIS, ElastiCache) and
`aws-compute-and-networking.md` (ECS Fargate, autoscaling, ALB).

Load-bearing rules restated (they hold even if you read nothing else):
- **Never hardcode secrets in `.tf` or `.tfvars`.** Credentials live in AWS Secrets Manager and are injected by reference.
- **Always `terraform plan` and read the plan before `terraform apply`.**
- **Every resource is tagged** with `project`, `environment`, `team`, `managed-by = "terraform"` (add `cost-center` where the org tracks spend).
- **Remote state with locking**, always — S3 + DynamoDB on AWS, GCS on GCP. One state file per environment.
- **Pin provider versions** with `~>`. An unpinned provider means a `terraform init` on a new machine can produce a different plan from the same code.

---

## Decision: where does this `.tf` file go

Environments are directories, not workspaces — a `production` blast radius must be a different state file, not a different workspace pointer.

```
terraform/
├── modules/
│   ├── networking/     # VPC, subnets, security groups
│   ├── database/       # RDS PostgreSQL with PostGIS
│   ├── redis/          # ElastiCache
│   ├── ecs/            # Rails app containers
│   └── centrifugo/     # Centrifugo service
├── environments/
│   ├── dev/
│   ├── staging/
│   └── production/
└── shared/             # Shared resources (ECR, IAM)
```

Each environment dir holds `main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`, `terraform.tfvars`. Modules are consumed by all three environments; they never contain environment names or hardcoded account IDs.

---

## Decision: how do I configure remote state

### Bad — local state, no locking

```hcl
# terraform/environments/production/backend.tf
# BAD: no backend block at all -> terraform.tfstate lands on one laptop.
# Two engineers applying at once corrupt each other's state silently.
terraform {
  required_version = ">= 1.0"
}
```

### Good — S3 backend, DynamoDB lock, per-environment key

```hcl
# terraform/environments/production/backend.tf
terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "production/terraform.tfstate"   # unique per environment
    region         = "eu-west-1"
    dynamodb_table = "acme-tfstate-locks"
    encrypt        = true
  }
}
```

Provider versions are pinned with `~>`. An unpinned provider means a `terraform init` on a new machine can produce a different plan from the same code.

---

## Decision: how do I declare variables

Every variable carries a `type` and a `description`. Constrain the domain with `validation` where a typo would otherwise reach production.

### Bad

```hcl
variable "env" {}                        # BAD: no type, no description
variable "instance" { default = "db.t3.medium" }  # BAD: untyped, undocumented
variable "db_password" {                 # BAD: secret as a plain variable, lands in state and plan output
  default = "hunter2"
}
```

### Good

```hcl
# terraform/modules/database/variables.tf
variable "environment" {
  type        = string
  description = "Deployment environment; drives sizing and retention defaults."

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production."
  }
}

variable "instance_class" {
  type        = string
  description = "RDS instance class for the PostgreSQL primary."
  default     = "db.t3.medium"
}

variable "allocated_storage_gb" {
  type        = number
  description = "Initial allocated storage in GB. Autoscales up to max_allocated_storage_gb."
  default     = 50
}

variable "tags" {
  type        = map(string)
  description = "Tags merged onto every resource created by this module."
}
```

---

## Decision: how do I tag every resource without repeating myself

### Bad — tags copy-pasted, drifting, incomplete

```hcl
resource "aws_ecs_cluster" "main" {
  name = "app-cluster"
  tags = { environment = "production" }        # BAD: missing project/team/managed-by
}

resource "aws_db_instance" "main" {
  identifier = "app-db"
  tags       = { Environment = "prod", team = "platform" }  # BAD: inconsistent casing and value
}
```

### Good — `default_tags` on the provider, merged locals for the rest

```hcl
# terraform/environments/production/main.tf
locals {
  common_tags = {
    project    = "acme-platform"
    environment = "production"
    team       = "platform"
    cost-center = "eng-core"
    managed-by = "terraform"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags   # applied to every taggable resource this provider creates
  }
}

module "database" {
  source = "../../modules/database"

  environment    = "production"
  instance_class = "db.r6g.large"
  tags           = local.common_tags
}
```

Inside a module, merge rather than overwrite:

```hcl
resource "aws_db_instance" "main" {
  identifier = "${var.environment}-app-db"
  # ...
  tags = merge(var.tags, { Name = "${var.environment}-app-db" })
}
```

---

## Decision: how do I get a secret into a resource

Secrets are **created and rotated in AWS Secrets Manager**, and Terraform references them. Terraform state is not a secret store — anything you pass as a variable value is stored in plaintext in the state file.

### Bad — password in tfvars, plaintext into state

```hcl
# terraform.tfvars   (committed — BAD)
db_password = "S3cretP@ssw0rd"

# main.tf
resource "aws_db_instance" "main" {
  identifier = "prod-app-db"
  username   = "app"
  password   = var.db_password    # BAD: plaintext in state, plan output, and CI logs
}
```

### Good — RDS-managed master password in Secrets Manager, referenced by ARN

```hcl
# terraform/modules/database/main.tf
resource "aws_db_instance" "main" {
  identifier = "${var.environment}-app-db"
  engine     = "postgres"
  engine_version = "16.3"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_encrypted     = true

  username = "app"

  # AWS creates and rotates the master password; Terraform never sees it.
  manage_master_user_password = true

  parameter_group_name    = aws_db_parameter_group.postgis.name
  backup_retention_period = var.environment == "production" ? 30 : 7
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"
  multi_az                = var.environment == "production"

  tags = merge(var.tags, { Name = "${var.environment}-app-db" })
}

output "master_secret_arn" {
  description = "Secrets Manager ARN holding the RDS master credentials."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}
```

For application secrets you own (e.g. `CENTRIFUGO_API_KEY`), create the secret container in Terraform and set the value out of band:

```hcl
resource "aws_secretsmanager_secret" "centrifugo_api_key" {
  name = "${var.environment}/centrifugo/api_key"
  tags = var.tags
}
# The value is set via `aws secretsmanager put-secret-value` or the console —
# deliberately NOT an aws_secretsmanager_secret_version resource, which would
# require the plaintext to pass through Terraform state.
```

Consuming the secret in a container is the `secrets` block of the ECS task definition, never
`environment` — see `aws-compute-and-networking.md`.
