---
title: "Mark Sensitive Outputs"
id: state-sensitive-outputs
impact: HIGH
tags: [terraform, state-management]
---

# Mark Sensitive Outputs

All outputs containing secrets, credentials, or sensitive data must be marked with `sensitive = true`. Without this flag, Terraform displays secrets in CLI output, plan files, and state that may be logged in CI.

## Incorrect

Outputting database credentials and connection strings without the sensitive flag. These values appear in plain text in `terraform output`, plan logs, and CI artifacts.

```hcl
# terraform/modules/rds/outputs.tf
# WRONG: Secrets exposed in CLI output and CI logs

output "database_url" {
  description = "PostgreSQL connection URL"
  value       = "postgres://${aws_db_instance.postgres_db.username}:${aws_db_instance.postgres_db.password}@${aws_db_instance.postgres_db.endpoint}/${aws_db_instance.postgres_db.db_name}"
}

output "database_password" {
  description = "Database master password"
  value       = aws_db_instance.postgres_db.password
}

output "redis_auth_token" {
  description = "Redis AUTH token"
  value       = aws_elasticache_replication_group.redis_cache.auth_token
}
```

## Correct

Mark all secret-bearing outputs as sensitive. Terraform redacts these values from CLI output and marks them in plans.

```hcl
# terraform/modules/rds/outputs.tf
output "database_url" {
  description = "PostgreSQL connection URL for Rails DATABASE_URL"
  value       = "postgres://${aws_db_instance.postgres_db.username}:${aws_db_instance.postgres_db.password}@${aws_db_instance.postgres_db.endpoint}/${aws_db_instance.postgres_db.db_name}"
  sensitive   = true
}

output "database_password" {
  description = "Database master password"
  value       = aws_db_instance.postgres_db.password
  sensitive   = true
}

output "database_endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.postgres_db.endpoint
  # Not sensitive -- endpoint is not a secret
}

# terraform/modules/elasticache/outputs.tf
output "redis_auth_token" {
  description = "Redis AUTH token for Sidekiq and Rails cache"
  value       = aws_elasticache_replication_group.redis_cache.auth_token
  sensitive   = true
}

output "redis_url" {
  description = "Redis connection URL"
  value       = "rediss://:${aws_elasticache_replication_group.redis_cache.auth_token}@${aws_elasticache_replication_group.redis_cache.primary_endpoint_address}:6379"
  sensitive   = true
}

output "redis_endpoint" {
  description = "ElastiCache primary endpoint"
  value       = aws_elasticache_replication_group.redis_cache.primary_endpoint_address
  # Not sensitive -- endpoint hostname is not a secret
}
```

## Additional Context

- **State file still contains plaintext**: The `sensitive` flag only redacts CLI and plan output. State files still contain sensitive values in plaintext -- this is why state encryption (S3 SSE/KMS) is critical.
- **Propagation**: If a module output is marked sensitive, any root output consuming it must also be marked sensitive. Terraform enforces this at plan time.
- **CI logs**: Without `sensitive = true`, `terraform plan` and `terraform output` print secrets to stdout, which ends up in CI build logs. This is a common credential leak vector.
- **What to mark sensitive**: Database passwords, API keys, auth tokens, connection strings with credentials, private keys, and any value sourced from `aws_secretsmanager_secret_version` or `aws_ssm_parameter` of type `SecureString`.
- **What NOT to mark sensitive**: Endpoints, ARNs, resource IDs, and names. Over-marking outputs as sensitive makes debugging harder.
