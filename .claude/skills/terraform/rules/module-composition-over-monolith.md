---
title: "Module Composition Over Monolith"
id: module-composition-over-monolith
impact: HIGH
tags: [terraform, modules, architecture]
---

# Module Composition Over Monolith

Limit module nesting to a maximum of 2 levels (root -> child). Deeply nested modules create opaque dependency chains, make state management difficult, and obscure the blast radius of changes.

## Incorrect

```hcl
# environments/production/main.tf — 3+ levels deep
module "platform" {
  source = "../../modules/platform"
}

# modules/platform/main.tf — level 2, calls level 3
module "compute" {
  source = "../compute"
}

# modules/compute/main.tf — level 3, calls level 4
module "ecs_service" {
  source = "../ecs-service"
}

# modules/ecs-service/main.tf — level 4
resource "aws_ecs_service" "rails_app" {
  name    = "rails-app"
  cluster = var.cluster_arn
}
```

## Correct

```hcl
# environments/production/main.tf — flat composition, max 2 levels
module "networking" {
  source      = "../../modules/networking"
  environment = var.environment
  project     = var.project
  vpc_cidr    = "10.0.0.0/16"
}

module "database" {
  source            = "../../modules/database"
  environment       = var.environment
  project           = var.project
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.db_security_group_id
  engine_version    = "15.4"
  postgis           = true
}

module "redis" {
  source            = "../../modules/redis"
  environment       = var.environment
  project           = var.project
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.redis_security_group_id
}

module "ecs" {
  source            = "../../modules/ecs"
  environment       = var.environment
  project           = var.project
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.ecs_security_group_id
  database_url      = module.database.connection_url
  redis_url         = module.redis.connection_url
}

module "centrifugo" {
  source       = "../../modules/centrifugo"
  environment  = var.environment
  project      = var.project
  cluster_arn  = module.ecs.cluster_arn
  subnet_ids   = module.networking.private_subnet_ids
}
```

## Additional Context

The root module (e.g., `environments/production/main.tf`) acts as the orchestrator, wiring child modules together via their outputs. Each child module contains only resources — no further module calls. This flat structure makes `terraform state list` readable, keeps plan output predictable, and allows targeted `terraform apply -target=module.database` when needed. If a child module grows too large, split it into sibling modules rather than nesting deeper.
