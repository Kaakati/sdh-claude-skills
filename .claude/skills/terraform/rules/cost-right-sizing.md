---
title: "Right-Size Resources per Environment"
id: cost-right-sizing
impact: MEDIUM
tags: [terraform, cost, right-sizing]
---

# Right-Size Resources per Environment

Start with small instance sizes and scale based on metrics. Dev and staging environments should use the smallest viable instances. Production sizing should be driven by load testing and monitoring data, not guesswork.

## Incorrect

```hcl
# Over-provisioned from day one -- same large instances everywhere
resource "aws_db_instance" "postgres_db" {
  instance_class    = "db.r5.2xlarge"  # $1,400/month in dev!
  allocated_storage = 500
  multi_az          = true
}

resource "aws_elasticache_replication_group" "redis_cache" {
  node_type          = "cache.r5.xlarge"  # 26 GiB RAM for a dev cache
  num_cache_clusters = 3
}

resource "aws_ecs_service" "rails_app" {
  desired_count = 4  # 4 tasks in dev, wasting money
}
```

## Correct

```hcl
locals {
  # Instance sizing by environment
  rds_config = {
    dev = {
      instance_class    = "db.t3.small"
      allocated_storage = 20
      multi_az          = false
    }
    staging = {
      instance_class    = "db.t3.medium"
      allocated_storage = 50
      multi_az          = false
    }
    production = {
      instance_class    = "db.r5.large"
      allocated_storage = 100
      multi_az          = true
    }
  }

  redis_config = {
    dev        = { node_type = "cache.t3.micro",  num_clusters = 1 }
    staging    = { node_type = "cache.t3.small",   num_clusters = 1 }
    production = { node_type = "cache.r5.large",   num_clusters = 2 }
  }

  ecs_config = {
    dev        = { cpu = 256,  memory = 512,  min_tasks = 1, max_tasks = 2 }
    staging    = { cpu = 512,  memory = 1024, min_tasks = 1, max_tasks = 3 }
    production = { cpu = 1024, memory = 2048, min_tasks = 2, max_tasks = 10 }
  }
}

resource "aws_db_instance" "postgres_db" {
  identifier        = "${var.project_name}-${var.environment}-postgres"
  engine            = "postgres"
  instance_class    = local.rds_config[var.environment].instance_class
  allocated_storage = local.rds_config[var.environment].allocated_storage
  multi_az          = local.rds_config[var.environment].multi_az
}

resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  node_type            = local.redis_config[var.environment].node_type
  num_cache_clusters   = local.redis_config[var.environment].num_clusters
}

resource "aws_ecs_service" "rails_app" {
  desired_count = local.ecs_config[var.environment].min_tasks
}

resource "aws_appautoscaling_target" "rails_app" {
  max_capacity       = local.ecs_config[var.environment].max_tasks
  min_capacity       = local.ecs_config[var.environment].min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.rails_app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
```

## Additional Context

- Dev environments can use burstable instances (t3 family) which are significantly cheaper than memory-optimized (r5).
- A `db.t3.small` costs ~$25/month vs `db.r5.2xlarge` at ~$1,400/month -- a 56x difference.
- Use `locals` maps keyed by environment to centralize sizing decisions in one place.
- Production sizing should be based on CloudWatch metrics: CPU utilization, memory usage, connection counts, and query latency.
- Enable auto-scaling for ECS services so production can scale up under load and back down during quiet periods.
- Review and right-size quarterly using AWS Cost Explorer and Compute Optimizer recommendations.
