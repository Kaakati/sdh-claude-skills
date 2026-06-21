---
title: "Resource Lifecycle Rules"
id: resource-lifecycle-rules
impact: HIGH
tags: [terraform, resources, lifecycle]
---

# Resource Lifecycle Rules

Use `prevent_destroy` on stateful resources (databases, storage) and `create_before_destroy` on compute resources to avoid data loss and downtime during infrastructure changes.

## Incorrect

```hcl
# RDS instance with no lifecycle protection — a terraform destroy
# or accidental removal from config deletes the database
resource "aws_db_instance" "postgres" {
  identifier     = "${local.prefix}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.large"
}

# S3 bucket with no protection — can be destroyed with all data
resource "aws_s3_bucket" "active_storage" {
  bucket = "${local.prefix}-active-storage"
}

# ECS task definition — updating forces replacement,
# causes downtime without create_before_destroy
resource "aws_ecs_task_definition" "rails_app" {
  family                = "${local.prefix}-rails"
  container_definitions = jsonencode([...])
}
```

## Correct

```hcl
# Stateful resources: prevent accidental destruction
resource "aws_db_instance" "postgres" {
  identifier              = "${local.prefix}-postgres"
  engine                  = "postgres"
  engine_version          = "15.4"
  instance_class          = "db.r6g.large"
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "${local.prefix}-postgres-final"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket" "active_storage" {
  bucket = "${local.prefix}-active-storage"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.prefix}-redis"
  description          = "Redis for Sidekiq queues and Rails cache"

  lifecycle {
    prevent_destroy = true
  }
}

# Compute resources: create new before destroying old
resource "aws_ecs_task_definition" "rails_app" {
  family                = "${local.prefix}-rails"
  container_definitions = jsonencode([...])

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_ecs_service" "rails_app" {
  name            = "${local.prefix}-rails-service"
  task_definition = aws_ecs_task_definition.rails_app.arn

  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
}
```

## Additional Context

`prevent_destroy` causes `terraform apply` to error if a plan includes destroying the protected resource — this is a guardrail, not a guarantee (it can be removed from config). Pair it with AWS-level protections like RDS `deletion_protection` and S3 bucket policies. `create_before_destroy` ensures zero-downtime deployments by provisioning the replacement before tearing down the original. Use `ignore_changes` sparingly for attributes managed outside Terraform (e.g., autoscaling group desired count).
