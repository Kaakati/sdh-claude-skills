---
title: "RDS PostgreSQL with PostGIS Extension"
id: data-rds-postgresql-postgis
impact: MEDIUM
tags: [terraform, data-stores, rds, postgresql, postgis]
---

# RDS PostgreSQL with PostGIS Extension

RDS instances must enable PostGIS via a custom parameter group, enforce automated backups, and use multi-AZ in production for high availability.

## Incorrect

```hcl
# No PostGIS parameter group, no backups, single AZ in production
resource "aws_db_instance" "postgres_db" {
  engine               = "postgres"
  engine_version       = "15"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  db_name              = "rails_production"
  username             = "postgres"
  password             = var.db_password
  skip_final_snapshot  = true
  # No backup_retention_period — defaults to 0 (disabled)
  # No multi_az — defaults to false
  # No parameter_group_name — PostGIS unavailable
}
```

## Correct

```hcl
resource "aws_db_parameter_group" "postgis" {
  family = "postgres15"
  name   = "${var.project}-${var.environment}-postgis"

  parameter {
    name  = "shared_preload_libraries"
    value = "postgis"
  }

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = local.common_tags
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "${var.project}-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"

  allocated_storage     = 50
  max_allocated_storage = var.environment == "production" ? 500 : 100
  storage_encrypted     = true

  db_name  = "rails_${var.environment}"
  username = "postgres"
  password = var.db_password

  parameter_group_name = aws_db_parameter_group.postgis.name

  multi_az                  = var.environment == "production"
  backup_retention_period   = var.environment == "production" ? 30 : 7
  copy_tags_to_snapshot     = true
  deletion_protection       = var.environment == "production"
  skip_final_snapshot       = var.environment != "production"
  final_snapshot_identifier = "${var.project}-${var.environment}-final"

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  tags = local.common_tags
}
```

## Additional Context

- PostGIS requires `shared_preload_libraries` in a parameter group; the default group is immutable.
- `rds.force_ssl = 1` ensures all connections use TLS, meeting security standards.
- Multi-AZ provides automatic failover in production; single AZ is acceptable for dev/staging.
- `max_allocated_storage` enables storage autoscaling to prevent disk-full outages.
- Always enable `storage_encrypted` and `deletion_protection` for production databases.
