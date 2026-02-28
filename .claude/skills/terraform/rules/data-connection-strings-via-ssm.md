---
title: "Connection Strings via Secrets Manager"
id: data-connection-strings-via-ssm
impact: MEDIUM
tags: [terraform, data-stores, secrets, security]
---

# Connection Strings via Secrets Manager

Database and Redis connection strings must be stored in AWS Secrets Manager, never as plaintext environment variables. ECS tasks reference secrets by ARN.

## Incorrect

```hcl
# Hardcoded connection strings as plaintext environment variables
resource "aws_ecs_task_definition" "rails_app" {
  family = "rails-app"

  container_definitions = jsonencode([{
    name  = "rails"
    image = "${var.ecr_repo_url}:latest"
    environment = [
      {
        name  = "DATABASE_URL"
        value = "postgres://postgres:SuperSecret123@mydb.abc.rds.amazonaws.com:5432/rails_prod"
      },
      {
        name  = "REDIS_URL"
        value = "redis://redis.abc.cache.amazonaws.com:6379/0"
      }
    ]
  }])
}
```

## Correct

```hcl
# Step 1: Create secrets in Secrets Manager
resource "aws_secretsmanager_secret" "database_url" {
  name        = "${var.project}/${var.environment}/DATABASE_URL"
  description = "PostgreSQL connection string for Rails"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "database_url" {
  secret_id = aws_secretsmanager_secret.database_url.id
  secret_string = "postgres://${aws_db_instance.postgres_db.username}:${var.db_password}@${aws_db_instance.postgres_db.endpoint}/${aws_db_instance.postgres_db.db_name}"
}

resource "aws_secretsmanager_secret" "redis_url" {
  name        = "${var.project}/${var.environment}/REDIS_URL"
  description = "Redis connection string for Rails cache"

  tags = local.common_tags
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id     = aws_secretsmanager_secret.redis_url.id
  secret_string = "redis://${aws_elasticache_replication_group.redis_cache.primary_endpoint_address}:6379/0"
}

# Step 2: Grant ECS task role access to secrets
data "aws_iam_policy_document" "ecs_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [
      aws_secretsmanager_secret.database_url.arn,
      aws_secretsmanager_secret.redis_url.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecs_secrets" {
  name   = "${var.project}-${var.environment}-ecs-secrets"
  role   = aws_iam_role.ecs_execution_role.id
  policy = data.aws_iam_policy_document.ecs_secrets.json
}

# Step 3: Reference secrets in ECS task definition
resource "aws_ecs_task_definition" "rails_app" {
  family                   = "${var.project}-${var.environment}-rails"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.environment == "production" ? 1024 : 256
  memory                   = var.environment == "production" ? 2048 : 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([{
    name  = "rails_app"
    image = "${var.ecr_repo_url}:${var.image_tag}"
    secrets = [
      {
        name      = "DATABASE_URL"
        valueFrom = aws_secretsmanager_secret.database_url.arn
      },
      {
        name      = "REDIS_URL"
        valueFrom = aws_secretsmanager_secret.redis_url.arn
      }
    ]
  }])
}
```

## Additional Context

- The `secrets` block in container definitions injects values at runtime from Secrets Manager.
- ECS execution role (not task role) needs `secretsmanager:GetSecretValue` permission.
- Connection strings are constructed from Terraform outputs to avoid manual coordination.
- Use hierarchical naming (`project/environment/SECRET_NAME`) for organized secret management.
- Secrets Manager supports automatic rotation -- configure for database passwords.
- Never store `var.db_password` in Terraform state in plaintext; use `sensitive = true`.
