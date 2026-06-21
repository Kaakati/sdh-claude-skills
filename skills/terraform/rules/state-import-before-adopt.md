---
title: "Import Existing Resources Before Managing"
id: state-import-before-adopt
impact: HIGH
tags: [terraform, state-management]
---

# Import Existing Resources Before Managing

When adopting existing infrastructure into Terraform, always import resources into state before applying. Creating a resource that already exists causes conflicts, errors, or accidental resource duplication.

## Incorrect

Writing Terraform config for an existing RDS instance without importing it. Terraform will try to create a new instance, failing or creating a duplicate.

```hcl
# terraform/environments/production/main.tf
# WRONG: This RDS instance already exists in AWS but is not in state
# Running `terraform apply` will try to CREATE a new instance

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"  # Already exists!
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"
}

# terraform apply => Error: DBInstanceAlreadyExists
```

## Correct

Import the existing resource into state first, then manage it with Terraform.

### Option 1: Import block (Terraform 1.5+, recommended)

```hcl
# terraform/environments/production/imports.tf
# Declarative import -- runs during terraform plan/apply
import {
  to = aws_db_instance.postgres_db
  id = "myproject-production-postgres"
}

import {
  to = aws_elasticache_replication_group.redis_cache
  id = "myproject-production-redis"
}

import {
  to = aws_ecs_cluster.main
  id = "myproject-production"
}

# terraform/environments/production/main.tf
resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"

  # Match ALL existing attributes to avoid drift
  allocated_storage       = 100
  storage_encrypted       = true
  multi_az                = true
  backup_retention_period = 30
  deletion_protection     = true
}
```

### Option 2: CLI import (older Terraform versions)

```bash
# Import existing resources one at a time
terraform import aws_db_instance.postgres_db myproject-production-postgres
terraform import aws_elasticache_replication_group.redis_cache myproject-production-redis
terraform import aws_ecs_cluster.main myproject-production

# After import, run plan to check for drift
terraform plan
# Review the plan -- fix any differences between config and actual state
```

## Additional Context

- **Match all attributes**: After importing, run `terraform plan` and adjust your configuration until the plan shows no changes. This ensures your config matches reality.
- **Generate config**: Use `terraform plan -generate-config-out=generated.tf` (Terraform 1.5+) to auto-generate config for imported resources, then clean it up.
- **Import blocks are idempotent**: Once the resource is in state, the import block is safely ignored on subsequent runs. Remove import blocks after successful import for cleanliness.
- **Bulk adoption**: When importing many resources (e.g., migrating an entire account to Terraform), use tools like `terraformer` or `cf2tf` to generate initial configs, then review and refine.
- **State-only operation**: `terraform import` only modifies state -- it never creates, modifies, or destroys real infrastructure.
