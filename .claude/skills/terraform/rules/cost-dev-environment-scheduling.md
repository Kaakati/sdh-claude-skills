---
title: "Dev Environment Scheduling and Scale-to-Zero"
id: cost-dev-environment-scheduling
impact: LOW
tags: [terraform, cost, scheduling, dev]
---

# Dev Environment Scheduling and Scale-to-Zero

Dev and staging environments should not run 24/7 at full capacity. Use scheduled scaling to reduce ECS tasks off-hours and conditionally create expensive resources only in production.

## Incorrect

```hcl
# Dev environment running 24/7 at full capacity
resource "aws_ecs_service" "rails_app" {
  desired_count = 2  # Running all night and weekends in dev
}

resource "aws_elasticache_replication_group" "redis_cache" {
  num_cache_clusters = 2  # Multi-node Redis in dev
}

resource "aws_nat_gateway" "main" {
  # 3 NAT gateways in dev at $32/month each
  for_each = toset(var.availability_zones)
  # ...
}
```

## Correct

```hcl
# ECS scheduled scaling -- scale down nights and weekends in dev/staging
resource "aws_appautoscaling_target" "rails_app" {
  max_capacity       = local.ecs_config[var.environment].max_tasks
  min_capacity       = local.ecs_config[var.environment].min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.rails_app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale down to 0 on weeknights (dev only)
resource "aws_appautoscaling_scheduled_action" "scale_down_night" {
  count = var.environment == "dev" ? 1 : 0

  name               = "${var.project_name}-dev-scale-down-night"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.rails_app.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_app.scalable_dimension
  schedule           = "cron(0 20 ? * MON-FRI *)"  # 8 PM UTC weeknights

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

# Scale back up on weekday mornings (dev only)
resource "aws_appautoscaling_scheduled_action" "scale_up_morning" {
  count = var.environment == "dev" ? 1 : 0

  name               = "${var.project_name}-dev-scale-up-morning"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.rails_app.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_app.scalable_dimension
  schedule           = "cron(0 8 ? * MON-FRI *)"  # 8 AM UTC weekdays

  scalable_target_action {
    min_capacity = 1
    max_capacity = 2
  }
}

# Scale down all weekend (dev only)
resource "aws_appautoscaling_scheduled_action" "scale_down_weekend" {
  count = var.environment == "dev" ? 1 : 0

  name               = "${var.project_name}-dev-scale-down-weekend"
  service_namespace  = "ecs"
  resource_id        = aws_appautoscaling_target.rails_app.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_app.scalable_dimension
  schedule           = "cron(0 20 ? * FRI *)"  # Friday 8 PM UTC

  scalable_target_action {
    min_capacity = 0
    max_capacity = 0
  }
}

# Conditional resource creation -- skip expensive resources in dev
resource "aws_cloudfront_distribution" "cdn" {
  count = var.environment == "production" ? 1 : 0

  origin {
    domain_name = aws_s3_bucket.active_storage.bucket_regional_domain_name
    origin_id   = "s3-active-storage"
  }

  enabled = true
  # ... full CDN config for production only
}

# RDS stop/start via Lambda for dev (optional automation)
resource "aws_lambda_function" "rds_scheduler" {
  count = var.environment == "dev" ? 1 : 0

  function_name = "${var.project_name}-dev-rds-scheduler"
  runtime       = "python3.12"
  handler       = "index.handler"
  filename      = data.archive_file.rds_scheduler[0].output_path
  role          = aws_iam_role.rds_scheduler[0].arn

  environment {
    variables = {
      RDS_INSTANCE_ID = aws_db_instance.postgres_db.identifier
    }
  }
}
```

## Additional Context

- ECS Fargate charges per-second for running tasks. Scaling to 0 off-hours saves ~65% of dev compute costs (16 hours/day, 5 days/week).
- RDS instances can be stopped for up to 7 days (AWS auto-starts after 7 days). A Lambda on a CloudWatch Events schedule can automate stop/start cycles.
- CloudFront, WAF, and other production-only services should use `count = var.environment == "production" ? 1 : 0` to avoid creation in dev.
- NAT Gateway charges apply even with zero traffic ($32/month base). In dev, use a single NAT only.
- Adjust cron schedules to match your team's timezone and working hours.
- Never apply scheduled scaling to production -- production must be available 24/7.
- Estimated monthly savings for a typical dev environment: $200-500/month by scheduling off-hours and right-sizing.
