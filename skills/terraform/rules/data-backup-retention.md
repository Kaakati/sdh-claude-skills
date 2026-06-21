---
title: "Backup Retention Policies"
id: data-backup-retention
impact: MEDIUM
tags: [terraform, data-stores, backup, disaster-recovery]
---

# Backup Retention Policies

All data stores must have environment-appropriate backup retention: 7 days for dev/staging, 30 days for production. Never disable backups.

## Incorrect

```hcl
# No backups — data loss is unrecoverable
resource "aws_db_instance" "postgres_db" {
  identifier              = "rails-postgres"
  engine                  = "postgres"
  instance_class          = "db.t3.medium"
  backup_retention_period = 0  # Backups disabled!
  skip_final_snapshot     = true
}

resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id    = "rails-redis"
  node_type               = "cache.t3.micro"
  num_cache_clusters      = 1
  snapshot_retention_limit = 0  # No snapshots!
}
```

## Correct

```hcl
locals {
  backup_retention = {
    development = 7
    staging     = 7
    production  = 30
  }
  redis_snapshot_retention = {
    development = 1
    staging     = 3
    production  = 7
  }
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "${var.project}-${var.environment}-postgres"
  engine         = "postgres"
  instance_class = var.environment == "production" ? "db.r6g.large" : "db.t3.medium"

  backup_retention_period   = local.backup_retention[var.environment]
  backup_window             = "03:00-04:00"
  maintenance_window        = "Mon:04:00-Mon:05:00"
  copy_tags_to_snapshot     = true
  delete_automated_backups  = var.environment != "production"
  skip_final_snapshot       = var.environment != "production"
  final_snapshot_identifier = "${var.project}-${var.environment}-final-${formatdate("YYYYMMDD", timestamp())}"

  tags = local.common_tags
}

resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "${var.project}-${var.environment}-cache"
  node_type            = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_clusters   = var.environment == "production" ? 2 : 1

  snapshot_retention_limit = local.redis_snapshot_retention[var.environment]
  snapshot_window          = "04:00-05:00"

  tags = local.common_tags
}
```

## Additional Context

- `backup_retention_period = 0` disables RDS automated backups entirely -- never do this.
- Stagger `backup_window` and `maintenance_window` to avoid overlapping I/O contention.
- `copy_tags_to_snapshot = true` ensures snapshots inherit cost-allocation and environment tags.
- Production final snapshots use timestamped identifiers to prevent naming collisions.
- ElastiCache snapshots are essential for Sidekiq queue recovery after failures.
- Backup windows should be during low-traffic hours (typically 03:00-05:00 UTC).
