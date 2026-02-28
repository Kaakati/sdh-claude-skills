---
title: "Module Single Responsibility"
id: module-single-responsibility
impact: HIGH
tags: [terraform, modules, architecture]
---

# Module Single Responsibility

Each Terraform module must own exactly one infrastructure concern. Mixing concerns (networking + database + compute) creates tight coupling, makes modules harder to test, and forces unnecessary changes when only one concern evolves.

## Incorrect

```hcl
# modules/infrastructure/main.tf — monolithic module
resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr
}

resource "aws_db_instance" "postgres" {
  engine         = "postgres"
  instance_class = var.db_instance_class
  vpc_security_group_ids = [aws_security_group.db.id]
}

resource "aws_ecs_cluster" "rails" {
  name = "rails-cluster"
}

resource "aws_elasticache_replication_group" "redis" {
  description          = "Redis for Sidekiq"
  replication_group_id = "redis-cache"
}
```

## Correct

```hcl
# terraform/modules/ directory structure:
#   networking/    — VPC, subnets, NAT, security groups
#   database/      — RDS PostgreSQL+PostGIS
#   redis/         — ElastiCache Redis (cache + Sidekiq)
#   ecs/           — ECS Fargate cluster, services, task definitions
#   centrifugo/    — Centrifugo WebSocket service on ECS
#   s3/            — S3 buckets (ActiveStorage, assets)
#   cloudfront/    — CloudFront distributions

# environments/production/main.tf — root composition
module "networking" {
  source      = "../../modules/networking"
  environment = "production"
  vpc_cidr    = "10.0.0.0/16"
}

module "database" {
  source            = "../../modules/database"
  environment       = "production"
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.db_security_group_id
}

module "ecs" {
  source            = "../../modules/ecs"
  environment       = "production"
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.ecs_security_group_id
  database_url      = module.database.connection_url
  redis_url         = module.redis.connection_url
}
```

## Additional Context

A module has a single responsibility when you can describe it without using "and." If you say "this module creates the VPC **and** the database," split it. Each module in `terraform/modules/` maps to one bounded infrastructure domain matching our stack: networking, database (RDS PostgreSQL+PostGIS), redis (ElastiCache), ecs (Fargate for Rails API), centrifugo, s3 (ActiveStorage), and cloudfront.
