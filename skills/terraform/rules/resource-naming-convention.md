---
title: "Resource Naming Convention"
id: resource-naming-convention
impact: HIGH
tags: [terraform, resources, naming]
---

# Resource Naming Convention

All AWS resources must follow the `{project}-{env}-{service}-{resource}` naming pattern. Consistent naming enables filtering in the AWS console, cost attribution, and automated cleanup of orphaned resources.

## Incorrect

```hcl
resource "aws_ecs_service" "rails" {
  name    = "my-service"
  cluster = aws_ecs_cluster.main.arn
}

resource "aws_db_instance" "db" {
  identifier = "postgres"
  engine     = "postgres"
}

resource "aws_s3_bucket" "uploads" {
  bucket = "uploads-bucket"
}
```

## Correct

```hcl
locals {
  prefix = "${var.project}-${var.environment}"
}

resource "aws_ecs_cluster" "rails" {
  name = "${local.prefix}-rails-cluster"

  tags = {
    Name = "${local.prefix}-rails-cluster"
  }
}

resource "aws_ecs_service" "rails_app" {
  name    = "${local.prefix}-rails-service"
  cluster = aws_ecs_cluster.rails.arn

  tags = {
    Name = "${local.prefix}-rails-service"
  }
}

resource "aws_db_instance" "postgres" {
  identifier = "${local.prefix}-postgres"
  engine     = "postgres"

  tags = {
    Name = "${local.prefix}-postgres"
  }
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id = "${local.prefix}-redis"
  description          = "${local.prefix} Redis for Sidekiq and cache"

  tags = {
    Name = "${local.prefix}-redis"
  }
}

resource "aws_s3_bucket" "active_storage" {
  bucket = "${local.prefix}-active-storage"

  tags = {
    Name = "${local.prefix}-active-storage"
  }
}
```

## Additional Context

Use a `local.prefix` value of `{project}-{environment}` to DRY up naming across all resources. The `Name` tag should match the resource name/identifier for consistency in the AWS console. Some AWS resources have character limits on names (e.g., ElastiCache replication group IDs max 40 characters) — keep project and environment names short. Avoid underscores in resource names as some AWS services do not allow them.
