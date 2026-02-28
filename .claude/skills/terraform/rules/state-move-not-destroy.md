---
title: "Use State Move for Refactoring"
id: state-move-not-destroy
impact: HIGH
tags: [terraform, state-management]
---

# Use State Move for Refactoring

When renaming or restructuring Terraform resources, use `moved` blocks or `terraform state mv` instead of letting Terraform destroy and recreate infrastructure. A rename without a state move causes downtime and data loss on stateful resources.

## Incorrect

Renaming a resource without a moved block. Terraform sees the old name as deleted and the new name as a new resource -- it will destroy the RDS instance and create a new one.

```hcl
# terraform/environments/production/main.tf
# Before: resource was named "db"
# resource "aws_db_instance" "db" { ... }

# WRONG: Renamed to "postgres_db" without a moved block
# Terraform plan will show:
#   - aws_db_instance.db will be DESTROYED (data loss!)
#   + aws_db_instance.postgres_db will be CREATED

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.xlarge"
}
```

## Correct

### Option 1: Moved block (Terraform 1.1+, recommended)

```hcl
# terraform/environments/production/main.tf

# Declarative move -- Terraform updates state during plan/apply
moved {
  from = aws_db_instance.db
  to   = aws_db_instance.postgres_db
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.xlarge"
}

# Moving into a module
moved {
  from = aws_elasticache_replication_group.redis
  to   = module.redis_cache.aws_elasticache_replication_group.main
}

module "redis_cache" {
  source = "../../modules/elasticache"
  # ...
}
```

### Option 2: CLI state move (older Terraform versions)

```bash
# Rename a resource
terraform state mv aws_db_instance.db aws_db_instance.postgres_db

# Move a resource into a module
terraform state mv \
  aws_elasticache_replication_group.redis \
  module.redis_cache.aws_elasticache_replication_group.main

# Verify no destroy/create in plan
terraform plan
```

## Additional Context

- **Moved blocks are declarative**: They live in your config alongside the renamed resource, making refactoring reviewable in PRs. Remove them after the change is applied to all environments.
- **Zero downtime**: State moves update only the Terraform state file. No infrastructure is created, modified, or destroyed.
- **Module extraction**: When extracting resources into modules, use moved blocks to maintain state continuity. This is the most common refactoring pattern.
- **Cross-state moves**: For moving resources between state files (e.g., from one environment config to another), use `terraform state mv -state-out=other.tfstate`.
- **Always plan first**: After any state move, run `terraform plan` and verify the plan shows no unexpected changes before applying.
- **Stateful resources are critical**: RDS instances, ElastiCache clusters, ECS services, and S3 buckets with data must never be accidentally destroyed during refactoring.
