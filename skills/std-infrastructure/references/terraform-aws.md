# Terraform on AWS — Layout, State, and the Core Services

Load-bearing rules restated (they hold even if you read nothing else):
- **Never hardcode secrets in `.tf` or `.tfvars`.** Credentials live in AWS Secrets Manager and are injected by reference.
- **Always `terraform plan` and read the plan before `terraform apply`.**
- **Every resource is tagged** with `project`, `environment`, `team`, `managed-by = "terraform"` (add `cost-center` where the org tracks spend).
- **Remote state with locking**, always — S3 + DynamoDB on AWS, GCS on GCP.

AWS is the primary cloud. The canonical stack: **ECS Fargate** (Rails app + Sidekiq + Centrifugo), **RDS PostgreSQL with PostGIS**, **ElastiCache Redis** (cache + Sidekiq queues), **S3** (ActiveStorage), **CloudFront** (static assets, API caching), **Route 53** (DNS), **Secrets Manager** (all credentials), **CloudWatch** (logs + metrics), **ALB with WebSocket support** in front of Centrifugo.

---

## Decision: where does this `.tf` file go

Environments are directories, not workspaces — a `production` blast radius must be a different state file, not a different workspace pointer.

```
terraform/
├── modules/
│   ├── networking/     # VPC, subnets, security groups
│   ├── database/       # RDS PostgreSQL with PostGIS
│   ├── redis/          # ElastiCache
│   ├── ecs/            # Rails app containers
│   └── centrifugo/     # Centrifugo service
├── environments/
│   ├── dev/
│   ├── staging/
│   └── production/
└── shared/             # Shared resources (ECR, IAM)
```

Each environment dir holds `main.tf`, `variables.tf`, `outputs.tf`, `backend.tf`, `terraform.tfvars`. Modules are consumed by all three environments; they never contain environment names or hardcoded account IDs.

---

## Decision: how do I configure remote state

### Bad — local state, no locking

```hcl
# terraform/environments/production/backend.tf
# BAD: no backend block at all -> terraform.tfstate lands on one laptop.
# Two engineers applying at once corrupt each other's state silently.
terraform {
  required_version = ">= 1.0"
}
```

### Good — S3 backend, DynamoDB lock, per-environment key

```hcl
# terraform/environments/production/backend.tf
terraform {
  required_version = "~> 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }

  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "production/terraform.tfstate"   # unique per environment
    region         = "eu-west-1"
    dynamodb_table = "acme-tfstate-locks"
    encrypt        = true
  }
}
```

Provider versions are pinned with `~>`. An unpinned provider means a `terraform init` on a new machine can produce a different plan from the same code.

---

## Decision: how do I declare variables

Every variable carries a `type` and a `description`. Constrain the domain with `validation` where a typo would otherwise reach production.

### Bad

```hcl
variable "env" {}                        # BAD: no type, no description
variable "instance" { default = "db.t3.medium" }  # BAD: untyped, undocumented
variable "db_password" {                 # BAD: secret as a plain variable, lands in state and plan output
  default = "hunter2"
}
```

### Good

```hcl
# terraform/modules/database/variables.tf
variable "environment" {
  type        = string
  description = "Deployment environment; drives sizing and retention defaults."

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "environment must be one of: dev, staging, production."
  }
}

variable "instance_class" {
  type        = string
  description = "RDS instance class for the PostgreSQL primary."
  default     = "db.t3.medium"
}

variable "allocated_storage_gb" {
  type        = number
  description = "Initial allocated storage in GB. Autoscales up to max_allocated_storage_gb."
  default     = 50
}

variable "tags" {
  type        = map(string)
  description = "Tags merged onto every resource created by this module."
}
```

---

## Decision: how do I tag every resource without repeating myself

### Bad — tags copy-pasted, drifting, incomplete

```hcl
resource "aws_ecs_cluster" "main" {
  name = "app-cluster"
  tags = { environment = "production" }        # BAD: missing project/team/managed-by
}

resource "aws_db_instance" "main" {
  identifier = "app-db"
  tags       = { Environment = "prod", team = "platform" }  # BAD: inconsistent casing and value
}
```

### Good — `default_tags` on the provider, merged locals for the rest

```hcl
# terraform/environments/production/main.tf
locals {
  common_tags = {
    project    = "acme-platform"
    environment = "production"
    team       = "platform"
    cost-center = "eng-core"
    managed-by = "terraform"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags   # applied to every taggable resource this provider creates
  }
}

module "database" {
  source = "../../modules/database"

  environment    = "production"
  instance_class = "db.r6g.large"
  tags           = local.common_tags
}
```

Inside a module, merge rather than overwrite:

```hcl
resource "aws_db_instance" "main" {
  identifier = "${var.environment}-app-db"
  # ...
  tags = merge(var.tags, { Name = "${var.environment}-app-db" })
}
```

---

## Decision: how do I get a secret into a resource

Secrets are **created and rotated in AWS Secrets Manager**, and Terraform references them. Terraform state is not a secret store — anything you pass as a variable value is stored in plaintext in the state file.

### Bad — password in tfvars, plaintext into state

```hcl
# terraform.tfvars   (committed — BAD)
db_password = "S3cretP@ssw0rd"

# main.tf
resource "aws_db_instance" "main" {
  identifier = "prod-app-db"
  username   = "app"
  password   = var.db_password    # BAD: plaintext in state, plan output, and CI logs
}
```

### Good — RDS-managed master password in Secrets Manager, referenced by ARN

```hcl
# terraform/modules/database/main.tf
resource "aws_db_instance" "main" {
  identifier = "${var.environment}-app-db"
  engine     = "postgres"
  engine_version = "16.3"
  instance_class = var.instance_class

  allocated_storage     = var.allocated_storage_gb
  max_allocated_storage = var.max_allocated_storage_gb
  storage_encrypted     = true

  username = "app"

  # AWS creates and rotates the master password; Terraform never sees it.
  manage_master_user_password = true

  parameter_group_name    = aws_db_parameter_group.postgis.name
  backup_retention_period = var.environment == "production" ? 30 : 7
  deletion_protection     = var.environment == "production"
  skip_final_snapshot     = var.environment != "production"
  multi_az                = var.environment == "production"

  tags = merge(var.tags, { Name = "${var.environment}-app-db" })
}

output "master_secret_arn" {
  description = "Secrets Manager ARN holding the RDS master credentials."
  value       = aws_db_instance.main.master_user_secret[0].secret_arn
}
```

For application secrets you own (e.g. `CENTRIFUGO_API_KEY`), create the secret container in Terraform and set the value out of band:

```hcl
resource "aws_secretsmanager_secret" "centrifugo_api_key" {
  name = "${var.environment}/centrifugo/api_key"
  tags = var.tags
}
# The value is set via `aws secretsmanager put-secret-value` or the console —
# deliberately NOT an aws_secretsmanager_secret_version resource, which would
# require the plaintext to pass through Terraform state.
```

---

## Decision: PostGIS on RDS

PostGIS is not on by default. The extension must be created in the database, and the parameter group must allow it.

```hcl
# terraform/modules/database/main.tf
resource "aws_db_parameter_group" "postgis" {
  name   = "${var.environment}-postgres16-postgis"
  family = "postgres16"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements"
  }

  parameter {
    name         = "log_min_duration_statement"
    value        = "500"   # log slow queries (ms)
    apply_method = "immediate"
  }

  tags = var.tags
}
```

Then, in a Rails migration (not Terraform — extension enablement belongs with the schema):

```ruby
class EnablePostgis < ActiveRecord::Migration[7.2]
  def up
    enable_extension "postgis"
  end

  def down
    disable_extension "postgis"
  end
end
```

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

## Decision: ElastiCache Redis for cache + Sidekiq

Sidekiq queues are not a cache — an eviction policy that drops keys will drop jobs. Sidekiq's Redis must use `noeviction`. If you also use Redis as a Rails cache, use a separate replication group (or at minimum a separate database index with `noeviction` still set).

```hcl
resource "aws_elasticache_parameter_group" "sidekiq" {
  name   = "${var.environment}-redis7-sidekiq"
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"   # Sidekiq jobs must never be evicted
  }

  tags = var.tags
}

resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${var.environment}-redis"
  description          = "Rails cache and Sidekiq queues"
  engine               = "redis"
  engine_version       = "7.1"
  node_type            = var.node_type            # start at cache.t3.medium
  parameter_group_name = aws_elasticache_parameter_group.sidekiq.name

  num_cache_clusters         = var.environment == "production" ? 2 : 1
  automatic_failover_enabled = var.environment == "production"
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true

  subnet_group_name  = var.subnet_group_name
  security_group_ids = [var.redis_security_group_id]

  tags = var.tags
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

---

## Decision: I need something from GCP

GCP is the **secondary** cloud — reach for it only when a specific service requires it (Maps, ML/Vertex, BigQuery). Do not split the primary stack across clouds.

- Authenticate with a **service account holding the minimum roles** for the one job. No `roles/editor`.
- **GCP credentials are stored in AWS Secrets Manager**, so credentials have a single source of truth. Do not introduce GCP Secret Manager for an AWS-primary system.
- GCP-only stacks use a **GCS backend with state locking**, mirroring the S3/DynamoDB arrangement.

```hcl
# terraform/environments/production/gcp.tf
resource "google_service_account" "maps_geocoder" {
  account_id   = "maps-geocoder-prod"
  display_name = "Geocoding calls from the Rails app"
}

resource "google_project_iam_member" "maps_geocoder" {
  project = var.gcp_project_id
  role    = "roles/serviceusage.serviceUsageConsumer"   # narrow, not roles/editor
  member  = "serviceAccount:${google_service_account.maps_geocoder.email}"
}

# The generated key is placed in AWS Secrets Manager out of band:
#   aws secretsmanager put-secret-value --secret-id production/gcp/maps-geocoder \
#     --secret-string file://key.json
resource "aws_secretsmanager_secret" "gcp_maps_key" {
  name = "production/gcp/maps-geocoder"
  tags = local.common_tags
}
```
