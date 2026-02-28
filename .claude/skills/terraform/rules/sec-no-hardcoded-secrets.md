---
title: "No Hardcoded Secrets"
id: sec-no-hardcoded-secrets
impact: CRITICAL
tags: [terraform, security]
---

# No Hardcoded Secrets

Never hardcode passwords, API keys, tokens, or credentials in Terraform files. Use variables marked `sensitive = true`, AWS Secrets Manager, SSM Parameter Store, or environment variables. Secrets in `.tf` files end up in state files and version control.

## Incorrect

Secrets embedded directly in HCL code.

```hcl
# WRONG: Password hardcoded in resource
resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.xlarge"
  username       = "postgres_admin"
  password       = "SuperSecret123!"  # Stored in state AND version control
}

# WRONG: API key in ECS task definition
resource "aws_ecs_task_definition" "rails_app" {
  container_definitions = jsonencode([{
    name = "rails"
    environment = [
      {
        name  = "SENDGRID_API_KEY"
        value = "SG.xxxxxxxxxxxxxxxxxxxx"  # Exposed in task definition
      }
    ]
  }])
}

# WRONG: AWS credentials in provider
provider "aws" {
  region     = "us-east-1"
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

## Correct

Secrets managed through secure channels.

```hcl
# terraform/modules/database/variables.tf

variable "db_password" {
  description = "Master password for RDS PostgreSQL instance"
  type        = string
  sensitive   = true  # Prevents display in plan/apply output

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "Database password must be at least 16 characters."
  }
}

# terraform/modules/database/main.tf

# Reference password from Secrets Manager
data "aws_secretsmanager_secret_version" "db_password" {
  secret_id = "130{var.project_name}/130{var.environment}/db-password"
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "130{var.project_name}-130{var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.instance_class
  username       = "postgres_admin"
  password       = data.aws_secretsmanager_secret_version.db_password.secret_string

  tags = {
    Name        = "130{var.project_name}-130{var.environment}-postgres"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# terraform/modules/ecs/main.tf

# ECS task with secrets from Secrets Manager (never environment variables)
resource "aws_ecs_task_definition" "rails_app" {
  family                   = "130{var.project_name}-130{var.environment}-rails"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([{
    name  = "rails"
    image = "130{var.ecr_repository_url}:130{var.image_tag}"

    # Secrets injected at runtime from Secrets Manager
    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = "arn:aws:secretsmanager:130{var.region}:130{var.account_id}:secret:130{var.project_name}/130{var.environment}/database-url"
      },
      {
        name      = "REDIS_URL"
        valueFrom = "arn:aws:secretsmanager:130{var.region}:130{var.account_id}:secret:130{var.project_name}/130{var.environment}/redis-url"
      },
      {
        name      = "RAILS_MASTER_KEY"
        valueFrom = "arn:aws:secretsmanager:130{var.region}:130{var.account_id}:secret:130{var.project_name}/130{var.environment}/rails-master-key"
      }
    ]

    # Only non-sensitive values in environment
    environment = [
      { name = "RAILS_ENV", value = var.environment },
      { name = "RAILS_LOG_TO_STDOUT", value = "true" }
    ]
  }])
}

# Provider uses IAM roles, never static credentials
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

## Additional Context

- **State file exposure**: Even with `sensitive = true`, secrets are stored in plaintext in the Terraform state file. Always encrypt state at rest (S3 SSE-KMS) and restrict access.
- **AWS provider auth**: Use IAM roles (instance profiles, OIDC for CI/CD) instead of static credentials. Never set `access_key`/`secret_key` in provider blocks.
- **ECS secrets vs environment**: Use the `secrets` block with `valueFrom` ARN for sensitive values. The `environment` block is visible in the AWS Console and API.
- **Secrets Manager rotation**: Enable automatic rotation for database credentials. Terraform manages the secret resource; the rotation Lambda updates the value.
- **CI/CD**: Pass secrets via `TF_VAR_` environment variables in CI pipelines. Never store them in `.tfvars` files committed to version control.
- **Git hooks**: The `terraform-checker.py` PostToolUse hook scans for patterns like `AKIA`, hardcoded passwords, and API keys in `.tf` files.
