# AWS Data Services — RDS with PostGIS, ElastiCache Redis

The data layer of the canonical AWS stack: **RDS PostgreSQL with PostGIS** (primary database) and
**ElastiCache Redis** (Rails cache + Sidekiq queues). For the `aws_db_instance` resource itself and
how its master password is handled, see `terraform-mechanics.md`; for ECS/ALB see
`aws-compute-and-networking.md`.

Load-bearing rules restated (they hold even if you read nothing else):
- **Never hardcode secrets in `.tf` or `.tfvars`.** Credentials live in AWS Secrets Manager and are injected by reference — the RDS master password is created and rotated by AWS via `manage_master_user_password = true`, so Terraform never sees it.
- **Every resource is tagged** with `project`, `environment`, `team`, `managed-by = "terraform"` (add `cost-center` where the org tracks spend). Inside a module, `merge(var.tags, ...)` rather than overwrite.
- **Always `terraform plan` and read the plan before `terraform apply`.**
- Encryption at rest is on for both services; production gets multi-AZ / automatic failover.

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

The parameter group is attached to the primary via `parameter_group_name = aws_db_parameter_group.postgis.name`.

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
