---
title: "ECS Fargate Task Definition"
id: compute-ecs-fargate-task-definition
impact: MEDIUM
tags: [terraform, compute, ecs, fargate]
---

# ECS Fargate Task Definition

Task definitions must use Fargate compatibility, environment-appropriate CPU/memory, CloudWatch log configuration, and secrets from Secrets Manager.

## Incorrect

```hcl
# Hardcoded secrets, no logging, no health check
resource "aws_ecs_task_definition" "rails_app" {
  family = "rails"

  container_definitions = jsonencode([{
    name  = "rails"
    image = "123456789.dkr.ecr.us-east-1.amazonaws.com/rails:latest"
    cpu   = 256
    memory = 512
    environment = [
      { name = "DATABASE_URL", value = "postgres://user:pass@host/db" },
      { name = "RAILS_MASTER_KEY", value = "abc123secret" }
    ]
    # No logConfiguration — logs are lost
    # No healthCheck — ECS cannot detect unhealthy containers
  }])
}
```

## Correct

```hcl
resource "aws_ecs_task_definition" "rails_app" {
  family                   = "${var.project}-${var.environment}-rails"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.environment == "production" ? 1024 : 256
  memory                   = var.environment == "production" ? 2048 : 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name      = "rails_app"
    image     = "${aws_ecr_repository.rails_app.repository_url}:${var.image_tag}"
    essential = true

    portMappings = [{
      containerPort = 3000
      protocol      = "tcp"
    }]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:3000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }

    secrets = [
      { name = "DATABASE_URL",       valueFrom = aws_secretsmanager_secret.database_url.arn },
      { name = "REDIS_URL",          valueFrom = aws_secretsmanager_secret.redis_url.arn },
      { name = "RAILS_MASTER_KEY",   valueFrom = aws_secretsmanager_secret.rails_master_key.arn },
      { name = "CENTRIFUGO_API_KEY", valueFrom = aws_secretsmanager_secret.centrifugo_api_key.arn }
    ]

    environment = [
      { name = "RAILS_ENV",      value = var.environment == "production" ? "production" : "staging" },
      { name = "RAILS_LOG_TO_STDOUT", value = "true" },
      { name = "PORT",           value = "3000" }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.rails_app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "rails"
      }
    }
  }])

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "rails_app" {
  name              = "/ecs/${var.project}/${var.environment}/rails"
  retention_in_days = var.environment == "production" ? 90 : 14

  tags = local.common_tags
}
```

## Additional Context

- Fargate requires `network_mode = "awsvpc"` and explicit `cpu`/`memory` at the task level.
- Valid Fargate CPU/memory combinations: 256/512, 512/1024, 1024/2048, 2048/4096, 4096/8192.
- Use `secrets` block for sensitive values; `environment` for non-sensitive configuration.
- `RAILS_LOG_TO_STDOUT = true` ensures logs flow to CloudWatch via the awslogs driver.
- Container health checks let ECS detect and replace unhealthy tasks automatically.
- `startPeriod` gives Rails time to boot before health checks begin failing.
- Set log retention to control CloudWatch costs: 90 days for prod, 14 days for dev.
