# AWS Compute and Networking — ECS Fargate, Autoscaling, ALB WebSockets

The compute layer of the canonical AWS stack: **ECS Fargate** (Rails app + Sidekiq + Centrifugo)
behind an **ALB with WebSocket support**, logging to **CloudWatch**. For state/variables/tagging
mechanics see `terraform-mechanics.md`; for RDS/PostGIS and ElastiCache see `aws-data-services.md`.

Load-bearing rules restated (they hold even if you read nothing else):
- **Never hardcode secrets.** Credentials live in AWS Secrets Manager and are referenced by ARN from the task definition's `secrets` block — never `environment`.
- **Pin every image tag to an immutable git SHA.** `latest` is never allowed: you cannot roll back to a tag that moved.
- **Every resource is tagged** with `project`, `environment`, `team`, `managed-by = "terraform"` (add `cost-center` where the org tracks spend).
- **Always `terraform plan` and read the plan before `terraform apply`.**
- IAM grants name exact ARNs, never `*`.

---

## Decision: ECS Fargate service for the Rails app

Secrets go in the `secrets` block (resolved from Secrets Manager at task start), plain config in `environment`. Never put a credential in `environment` — it is visible in the task definition to anyone with `ecs:DescribeTaskDefinition`.

### Bad

```hcl
resource "aws_ecs_task_definition" "app" {
  family = "app"
  container_definitions = jsonencode([{
    name  = "rails"
    image = "1234.dkr.ecr.eu-west-1.amazonaws.com/app:latest"   # BAD: mutable tag, no rollback target
    environment = [
      { name = "DATABASE_URL", value = "postgres://app:hunter2@prod-db:5432/app" }  # BAD: secret in plaintext
    ]
    # BAD: no logConfiguration -> logs vanish; no healthCheck -> ALB drains blind
  }])
}
```

### Good

```hcl
# terraform/modules/ecs/main.tf
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.environment}/rails"
  retention_in_days = var.environment == "production" ? 90 : 14
  tags              = var.tags
}

resource "aws_ecs_task_definition" "app" {
  family                   = "${var.environment}-rails"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.task_cpu     # e.g. "1024"
  memory                   = var.task_memory  # e.g. "2048"
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "rails"
    image     = "${var.ecr_repository_url}:${var.image_tag}"  # immutable git SHA
    essential = true

    portMappings = [{ containerPort = 3000, protocol = "tcp" }]

    environment = [
      { name = "RAILS_ENV",           value = "production" },
      { name = "RAILS_LOG_TO_STDOUT", value = "1" },
      { name = "REDIS_URL",           value = var.redis_url },
    ]

    secrets = [
      { name = "DATABASE_URL",        valueFrom = var.database_url_secret_arn },
      { name = "CENTRIFUGO_API_KEY",  valueFrom = var.centrifugo_api_key_secret_arn },
      { name = "SECRET_KEY_BASE",     valueFrom = var.secret_key_base_arn },
    ]

    healthCheck = {
      command     = ["CMD-SHELL", "curl -fsS http://localhost:3000/up || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 30
    }

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.app.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "rails"
      }
    }
  }])

  tags = var.tags
}

resource "aws_ecs_service" "app" {
  name            = "${var.environment}-rails"
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.app.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.app_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "rails"
    container_port   = 3000
  }

  lifecycle {
    ignore_changes = [desired_count]   # autoscaling owns this
  }

  tags = var.tags
}
```

The execution role needs `secretsmanager:GetSecretValue` on exactly the referenced secret ARNs — not `*`:

```hcl
data "aws_iam_policy_document" "task_execution_secrets" {
  statement {
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [
      var.database_url_secret_arn,
      var.centrifugo_api_key_secret_arn,
      var.secret_key_base_arn,
    ]
  }
}
```

---

## Decision: auto-scaling the ECS service

Idle capacity is the most common avoidable cost. Attach a target-tracking policy rather than a fixed `desired_count`.

```hcl
resource "aws_appautoscaling_target" "app" {
  service_namespace  = "ecs"
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = var.min_capacity
  max_capacity       = var.max_capacity
}

resource "aws_appautoscaling_policy" "app_cpu" {
  name               = "${var.environment}-rails-cpu-target"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.app.service_namespace
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension

  target_tracking_scaling_policy_configuration {
    target_value       = 60
    scale_in_cooldown  = 300
    scale_out_cooldown = 60

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
```

---

## Decision: Centrifugo behind an ALB (WebSockets)

WebSocket upgrade fails on an ALB whose target group has a short idle timeout or no stickiness. Long-lived connections need an explicit idle timeout raise.

```hcl
resource "aws_lb" "main" {
  name               = "${var.environment}-alb"
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [var.alb_security_group_id]
  idle_timeout       = 3600   # WebSockets: default 60s kills live connections
  tags               = var.tags
}

resource "aws_lb_target_group" "centrifugo" {
  name        = "${var.environment}-centrifugo"
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = var.vpc_id

  health_check {
    path                = "/health"
    matcher             = "200"
    interval            = 15
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }

  tags = var.tags
}
```
