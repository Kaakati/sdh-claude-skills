---
title: "ECS Deployment Configuration"
id: compute-ecs-deployment-configuration
impact: MEDIUM
tags: [terraform, compute, ecs, deployment, zero-downtime]
---

# ECS Deployment Configuration

ECS services must use `minimum_healthy_percent = 100` and `maximum_percent = 200` for zero-downtime rolling deployments with circuit breaker rollback enabled.

## Incorrect

```hcl
# minimum_healthy_percent = 0 causes downtime during deploys
resource "aws_ecs_service" "rails_app" {
  name            = "rails-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rails_app.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 0    # All tasks can be killed — full outage
  deployment_maximum_percent         = 100  # No room for new tasks during deploy
  # No circuit breaker — failed deploys run forever
  # No health_check_grace_period — tasks killed before Rails boots
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

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 120

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

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

  ordered_placement_strategy {
    type  = "spread"
    field = "attribute:ecs.availability-zone"
  }

  propagate_tags = "SERVICE"

  lifecycle {
    ignore_changes = [desired_count]
  }

  tags = local.common_tags
}
```

## Additional Context

- `minimum_healthy_percent = 100` ensures all existing tasks stay running during deployment.
- `maximum_percent = 200` allows ECS to launch new tasks before draining old ones (rolling deploy).
- `health_check_grace_period_seconds = 120` gives Rails time to boot and pass ALB health checks.
- Circuit breaker with `rollback = true` automatically reverts failed deployments.
- `spread` placement across AZs ensures high availability if one AZ has issues.
- Without circuit breaker, a bad deploy creates a loop of failing tasks that never stabilizes.
- `propagate_tags = "SERVICE"` ensures tasks inherit service-level tags for cost tracking.
- `ignore_changes = [desired_count]` prevents Terraform from overriding auto scaler decisions.
