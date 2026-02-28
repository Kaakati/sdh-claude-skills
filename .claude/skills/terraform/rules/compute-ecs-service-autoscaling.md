---
title: "ECS Service Auto Scaling"
id: compute-ecs-service-autoscaling
impact: MEDIUM
tags: [terraform, compute, ecs, autoscaling]
---

# ECS Service Auto Scaling

ECS services must use auto scaling with target tracking policies instead of fixed `desired_count`. Scale on CPU and memory utilization with environment-appropriate min/max bounds.

## Incorrect

```hcl
# Fixed desired_count, no auto-scaling — cannot handle traffic spikes
resource "aws_ecs_service" "rails_app" {
  name            = "rails-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rails_app.arn
  desired_count   = 2
  launch_type     = "FARGATE"
  # No scaling policy — manually adjust during incidents
}
```

## Correct

```hcl
resource "aws_ecs_service" "rails_app" {
  name            = "${var.project}-${var.environment}-rails"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rails_app.arn
  desired_count   = var.environment == "production" ? 2 : 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.ecs_rails.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.rails_app.arn
    container_name   = "rails_app"
    container_port   = 3000
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = local.common_tags
}

# Auto scaling target
resource "aws_appautoscaling_target" "rails_app" {
  max_capacity       = var.environment == "production" ? 10 : 2
  min_capacity       = var.environment == "production" ? 2 : 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.rails_app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Scale on CPU utilization
resource "aws_appautoscaling_policy" "rails_cpu" {
  name               = "${var.project}-${var.environment}-rails-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.rails_app.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.rails_app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

# Scale on memory utilization
resource "aws_appautoscaling_policy" "rails_memory" {
  name               = "${var.project}-${var.environment}-rails-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.rails_app.resource_id
  scalable_dimension = aws_appautoscaling_target.rails_app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.rails_app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value       = 80
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}
```

## Additional Context

- `ignore_changes = [desired_count]` prevents Terraform from fighting the auto scaler.
- Target tracking at 70% CPU leaves headroom for traffic bursts before scaling triggers.
- Memory target at 80% accounts for Ruby/Rails memory growth under load.
- `scale_out_cooldown = 60` allows fast scale-out; `scale_in_cooldown = 300` prevents flapping.
- Production min_capacity of 2 ensures high availability across AZs even during low traffic.
- Both CPU and memory policies work together -- whichever triggers first scales the service.
