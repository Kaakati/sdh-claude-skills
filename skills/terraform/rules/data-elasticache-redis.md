---
title: "ElastiCache Redis with Failover"
id: data-elasticache-redis
impact: MEDIUM
tags: [terraform, data-stores, elasticache, redis]
---

# ElastiCache Redis with Failover

ElastiCache Redis must use replication groups with automatic failover in production. Configure separate parameter groups for caching (allkeys-lru) and Sidekiq queues (noeviction).

## Incorrect

```hcl
# Single-node Redis without failover or eviction policy
resource "aws_elasticache_cluster" "redis_cache" {
  cluster_id           = "redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  # No failover, no replication, default eviction policy
}
```

## Correct

```hcl
# Parameter group for Rails cache (evicts LRU keys when full)
resource "aws_elasticache_parameter_group" "rails_cache" {
  family = "redis7"
  name   = "${var.project}-${var.environment}-cache"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = local.common_tags
}

# Parameter group for Sidekiq queues (never evicts — jobs must not be lost)
resource "aws_elasticache_parameter_group" "sidekiq_queue" {
  family = "redis7"
  name   = "${var.project}-${var.environment}-sidekiq"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }

  tags = local.common_tags
}

# Replication group for Rails cache
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "${var.project}-${var.environment}-cache"
  description          = "Redis cache for Rails"
  engine_version       = "7.0"
  node_type            = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  parameter_group_name = aws_elasticache_parameter_group.rails_cache.name

  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled           = var.environment == "production"
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  snapshot_retention_limit = var.environment == "production" ? 7 : 1

  tags = local.common_tags
}

# Replication group for Sidekiq queues
resource "aws_elasticache_replication_group" "redis_sidekiq" {
  replication_group_id = "${var.project}-${var.environment}-sidekiq"
  description          = "Redis for Sidekiq job queues"
  engine_version       = "7.0"
  node_type            = var.environment == "production" ? "cache.r6g.large" : "cache.t3.micro"
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  parameter_group_name = aws_elasticache_parameter_group.sidekiq_queue.name

  automatic_failover_enabled = var.environment == "production"
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  snapshot_retention_limit = var.environment == "production" ? 7 : 1

  tags = local.common_tags
}
```

## Additional Context

- Separate Redis instances for cache vs Sidekiq prevents eviction from dropping queued jobs.
- `allkeys-lru` is ideal for Rails cache: evicts least-recently-used keys when memory is full.
- `noeviction` for Sidekiq returns errors on writes when full rather than silently dropping data.
- Automatic failover requires at least 2 cache clusters (primary + replica).
- Enable both at-rest and in-transit encryption for security compliance.
