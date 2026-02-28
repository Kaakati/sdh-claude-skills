---
title: "Resource Required Tags"
id: resource-required-tags
impact: HIGH
tags: [terraform, resources, tagging]
---

# Resource Required Tags

Every AWS resource must carry `project`, `environment`, `team`, and `managed-by` tags. Tags enable cost allocation, ownership tracking, and automated governance policies.

## Incorrect

```hcl
# No tags at all — invisible in cost reports, no ownership
resource "aws_ecs_cluster" "rails" {
  name = "myapp-production-rails-cluster"
}

resource "aws_db_instance" "postgres" {
  identifier     = "myapp-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.large"
}
```

## Correct

```hcl
# provider block sets default tags for all resources
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project     = var.project
      environment = var.environment
      team        = var.team
      managed-by  = "terraform"
    }
  }
}

# Resources inherit default_tags automatically
resource "aws_ecs_cluster" "rails" {
  name = "${local.prefix}-rails-cluster"

  tags = {
    Name    = "${local.prefix}-rails-cluster"
    service = "rails-api"
  }
}

resource "aws_db_instance" "postgres" {
  identifier     = "${local.prefix}-postgres"
  engine         = "postgres"
  instance_class = var.db_instance_class

  tags = {
    Name    = "${local.prefix}-postgres"
    service = "database"
    backup  = "critical"
  }
}

resource "aws_s3_bucket" "active_storage" {
  bucket = "${local.prefix}-active-storage"

  tags = {
    Name    = "${local.prefix}-active-storage"
    service = "storage"
    data    = "user-uploads"
  }
}
```

## Additional Context

Use `default_tags` in the AWS provider block to apply mandatory tags to every resource without repeating them. Per-resource `tags` merge with and can override default tags. Add service-specific tags (like `backup = "critical"` on RDS and S3) at the resource level. AWS Config rules or SCPs can enforce tag compliance — `default_tags` ensures Terraform resources always pass. The `managed-by = "terraform"` tag distinguishes IaC-managed resources from manually created ones.
