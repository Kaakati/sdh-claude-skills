# Cost Optimization (FinOps) on AWS

Load-bearing rules restated (they hold even if you read nothing else):
- **Every resource is tagged** with `project`, `environment`, `team`, `cost-center` — untagged spend is unattributable spend, and no right-sizing conversation is possible without it.
- **Nothing here justifies weakening reliability**: production keeps Multi-AZ, backups, and deletion protection regardless of cost pressure.

---

## Decision: should I commit to a Savings Plan or Reserved Instance

Commit only to **steady-state, predictable** capacity. Committing to a workload that shrinks next quarter is worse than on-demand.

- **Compute Savings Plans** (1-year or 3-year) for predictable ECS Fargate workloads — up to **50% savings**. Fargate is covered by Compute Savings Plans; there is no Fargate-specific RI.
- **RDS Reserved Instances** for production databases with steady-state usage.
- Review **Savings Plan utilization monthly**. Under-utilization means you are paying for commitment you do not consume; adjust coverage when workloads change.

Rule of thumb: cover the **trough**, not the peak. Commit to the floor of the last 90 days of usage and let auto-scaling burst on-demand above it.

---

## Decision: is this resource the right size

Right-sizing is a scheduled activity, not a reaction to a bill.

- **ECS tasks**: review CPU/memory allocation **quarterly**; downsize over-provisioned tasks. A task pinned at 8% CPU with 4 vCPU reserved is pure waste.
- **AWS Compute Optimizer**: take its recommendations for RDS instance class and ECS task sizing as the starting point.
- **ElastiCache**: start at `cache.t3.medium`. Scale up only when memory usage exceeds **65%**.
- **Idle resources**: never pay for them. ECS services get auto-scaling policies (see the auto-scaling section of `terraform-aws.md`), not fixed counts.

### Bad — over-provisioned, fixed capacity, sized by superstition

```hcl
# terraform/environments/production/main.tf
module "app" {
  source = "../../modules/ecs"

  task_cpu      = "4096"   # BAD: chosen "to be safe"; observed p99 CPU is 12%
  task_memory   = "8192"
  desired_count = 10       # BAD: fixed at peak; pays peak price at 3am
}

module "redis" {
  source    = "../../modules/redis"
  node_type = "cache.r6g.xlarge"   # BAD: 26GB for a 900MB working set
}
```

### Good — sized to observed load, scales to demand, non-prod scaled down

```hcl
locals {
  # Non-production does not need production capacity.
  sizing = {
    dev = {
      task_cpu = "512",  task_memory = "1024", min_capacity = 1, max_capacity = 2
      db_instance_class = "db.t3.micro"
      redis_node_type   = "cache.t3.micro"
    }
    staging = {
      task_cpu = "512",  task_memory = "1024", min_capacity = 1, max_capacity = 4
      db_instance_class = "db.t3.small"
      redis_node_type   = "cache.t3.micro"
    }
    production = {
      # Compute Optimizer recommendation; p99 CPU 55% at 1 vCPU.
      task_cpu = "1024", task_memory = "2048", min_capacity = 3, max_capacity = 20
      db_instance_class = "db.r6g.large"
      redis_node_type   = "cache.t3.medium"   # scale up past 65% memory utilization
    }
  }

  size = local.sizing[var.environment]
}

module "app" {
  source = "../../modules/ecs"

  task_cpu     = local.size.task_cpu
  task_memory  = local.size.task_memory
  min_capacity = local.size.min_capacity   # target-tracking autoscaling owns desired_count
  max_capacity = local.size.max_capacity
  tags         = local.common_tags
}
```

---

## Decision: how do I make cost visible before the bill arrives

- Tag every resource with `project`, `environment`, `team`, `cost-center` (provider `default_tags` is the enforcement point — see `terraform-aws.md`).
- Enable **AWS Cost Explorer** and set **monthly budget alerts**.
- Enable **Cost Anomaly Detection** to catch unexpected spend spikes.
- Review the **per-service cost breakdown monthly in team standup**.

### Bad — discovering the spike on the invoice

```hcl
# No budget, no anomaly detector. The NAT Gateway misconfiguration that
# quadrupled data-processing charges is found 34 days later by Finance.
```

### Good — budget alert plus anomaly detection, in code

```hcl
resource "aws_budgets_budget" "monthly" {
  name         = "${var.environment}-monthly"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_usd
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "TagKeyValue"
    values = ["user:environment$${var.environment}"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.finops_alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"   # warns before you land there
    subscriber_email_addresses = var.finops_alert_emails
  }
}

resource "aws_ce_anomaly_monitor" "services" {
  name              = "${var.environment}-service-monitor"
  monitor_type      = "DIMENSIONAL"
  monitor_dimension = "SERVICE"
}

resource "aws_ce_anomaly_subscription" "services" {
  name             = "${var.environment}-anomaly-alerts"
  frequency        = "DAILY"
  monitor_arn_list = [aws_ce_anomaly_monitor.services.arn]

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      match_options = ["GREATER_THAN_OR_EQUAL"]
      values        = ["100"]   # USD
    }
  }

  subscriber {
    type    = "EMAIL"
    address = var.finops_alert_emails[0]
  }
}
```

---

## Decision: storage is growing — what do I do about it

- **S3**: use **Intelligent-Tiering** for infrequently accessed objects. Set lifecycle policies to archive or delete old objects.
- **RDS**: delete old **manual** snapshots — they bill separately and forever. Automated snapshots consume included storage first.
- **ECR**: set lifecycle policies to expire **untagged images older than 30 days**. Every CI build pushes a layer set; without expiry, ECR grows without bound.

### Bad — no lifecycle rules anywhere

```hcl
resource "aws_s3_bucket" "uploads" {
  bucket = "acme-uploads-prod"
  # BAD: every ActiveStorage variant, every old attachment, sits in Standard forever
}

resource "aws_ecr_repository" "app" {
  name = "app"
  # BAD: 4 builds/day x 400MB, kept indefinitely
}
```

### Good — Intelligent-Tiering, expiry, ECR pruning

```hcl
resource "aws_s3_bucket" "uploads" {
  bucket = "acme-uploads-${var.environment}"
  tags   = var.tags
}

resource "aws_s3_bucket_lifecycle_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    id     = "intelligent-tiering"
    status = "Enabled"

    filter {}

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7   # failed uploads bill as storage
    }
  }

  rule {
    id     = "expire-temp-exports"
    status = "Enabled"

    filter {
      prefix = "exports/"
    }

    expiration {
      days = 14
    }
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 30 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the last 50 tagged images (rollback window)"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "sha-"]
          countType     = "imageCountMoreThan"
          countNumber   = 50
        }
        action = { type = "expire" }
      }
    ]
  })
}
```

---

## The FinOps review cadence

| Cadence | Activity |
|---|---|
| **Weekly** | Check Cost Anomaly Detection alerts. |
| **Monthly** | Review the Cost Explorer dashboard; compare against budget. Review Savings Plan utilization. Review per-service cost breakdown in team standup. |
| **Quarterly** | Right-sizing review (ECS task CPU/memory, RDS instance class). Savings Plan coverage evaluation. Unused resource cleanup (orphaned EBS volumes, idle NAT Gateways, old manual RDS snapshots, unattached Elastic IPs). |
