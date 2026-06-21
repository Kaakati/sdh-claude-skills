---
title: "Mark Sensitive Variables"
id: var-sensitive-marking
impact: HIGH
tags: [terraform, variables, security]
---

# Mark Sensitive Variables

Variables containing secrets, passwords, tokens, or API keys must be marked `sensitive = true`. This prevents Terraform from displaying their values in plan output, logs, and state file diffs.

## Incorrect

```hcl
# Secrets exposed in plan output and CI logs
variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
}

variable "redis_auth_token" {
  description = "Redis AUTH token for ElastiCache"
  type        = string
}

variable "centrifugo_api_key" {
  description = "Centrifugo HTTP API key"
  type        = string
}

variable "rails_secret_key_base" {
  description = "Rails SECRET_KEY_BASE"
  type        = string
}
```

## Correct

```hcl
variable "db_password" {
  description = "PostgreSQL master password for RDS"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 16
    error_message = "db_password must be at least 16 characters."
  }
}

variable "redis_auth_token" {
  description = "Redis AUTH token for ElastiCache cluster"
  type        = string
  sensitive   = true
}

variable "centrifugo_api_key" {
  description = "Centrifugo HTTP API key for publishing messages"
  type        = string
  sensitive   = true
}

variable "rails_secret_key_base" {
  description = "Rails SECRET_KEY_BASE for session encryption"
  type        = string
  sensitive   = true
}

# Outputs referencing sensitive values must also be marked
output "rds_connection_string" {
  description = "PostgreSQL connection string (contains password)"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres_db.endpoint}/rails_app"
  sensitive   = true
}
```

## Additional Context

- `sensitive = true` redacts the value in `terraform plan` and `terraform apply` output, showing `(sensitive value)` instead.
- Outputs that reference sensitive variables must also be marked `sensitive = true` or Terraform will error.
- Sensitive values are still stored in state -- encrypt your state backend (S3 with SSE-KMS).
- For production, prefer AWS Secrets Manager or SSM Parameter Store over variable-based secrets. Use `data "aws_secretsmanager_secret_version"` to fetch at plan time.
- Common sensitive variables in our stack: `db_password`, `redis_auth_token`, `centrifugo_api_key`, `centrifugo_token_hmac_secret`, `rails_secret_key_base`, `devise_jwt_secret_key`.
- Never store sensitive values in `.tfvars` files committed to version control. Use environment variables (`TF_VAR_db_password`) or a secret manager.
