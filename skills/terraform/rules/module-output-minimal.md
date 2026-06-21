---
title: "Module Output Minimal"
id: module-output-minimal
impact: HIGH
tags: [terraform, modules, outputs]
---

# Module Output Minimal

Output only the specific attributes that consuming modules need. Exposing entire resource objects leaks implementation details, creates brittle cross-module dependencies, and clutters `terraform output`.

## Incorrect

```hcl
# modules/database/outputs.tf — exposes entire resource
output "rds_instance" {
  description = "The entire RDS instance"
  value       = aws_db_instance.postgres
}

output "db_subnet_group" {
  description = "The entire subnet group"
  value       = aws_db_subnet_group.postgres
}

# Consumer must know internal resource structure
# module.database.rds_instance.endpoint
# module.database.rds_instance.port
# module.database.rds_instance.db_name
```

## Correct

```hcl
# modules/database/outputs.tf — only what consumers need
output "connection_url" {
  description = "PostgreSQL connection URL for Rails DATABASE_URL"
  value       = "postgresql://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}"
  sensitive   = true
}

output "endpoint" {
  description = "RDS endpoint (host:port)"
  value       = aws_db_instance.postgres.endpoint
}

output "port" {
  description = "RDS port"
  value       = aws_db_instance.postgres.port
}

output "security_group_id" {
  description = "Security group ID for ingress rules"
  value       = aws_security_group.postgres.id
}
```

```hcl
# modules/redis/outputs.tf
output "connection_url" {
  description = "Redis connection URL for Rails REDIS_URL"
  value       = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"
}

output "primary_endpoint" {
  description = "Redis primary endpoint for Sidekiq and Rails cache"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}
```

## Additional Context

Ask: "What does the consuming module actually reference?" Output those attributes and nothing more. Mark outputs containing credentials as `sensitive = true` to prevent them from appearing in CLI output and logs. Constructed values like `connection_url` are preferred over raw parts because they reduce logic duplication in consumers — the database module knows how to build its own connection string.
