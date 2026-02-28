---
title: "IAM Least Privilege"
id: sec-iam-least-privilege
impact: CRITICAL
tags: [terraform, security]
---

# IAM Least Privilege

IAM policies must never use wildcard Actions (`*`) or Resources (`*`). Every policy should grant the minimum permissions required for the specific task. Overly permissive IAM policies are the most common AWS security vulnerability.

## Incorrect

Wildcard permissions granting full access to all AWS services and resources.

```hcl
# terraform/modules/ecs/main.tf
# WRONG: God-mode IAM policy

resource "aws_iam_role_policy" "rails_app_task" {
  name = "myproject-rails-task-policy"
  role = aws_iam_role.rails_app_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"           # NEVER: full access to everything
        Resource = "*"           # NEVER: all resources in the account
      }
    ]
  })
}

# WRONG: Overly broad S3 access
resource "aws_iam_role_policy" "s3_access" {
  name = "s3-access"
  role = aws_iam_role.rails_app_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "s3:*"        # WRONG: includes s3:DeleteBucket
        Resource = "*"           # WRONG: all buckets in the account
      }
    ]
  })
}
```

## Correct

Scoped permissions for specific actions on specific resources.

```hcl
# terraform/modules/ecs/iam.tf

# ECS task execution role -- only what ECS needs to start containers
resource "aws_iam_role" "rails_app_execution" {
  name = "myproject-production-rails-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "rails_execution_policy" {
  name = "execution-policy"
  role = aws_iam_role.rails_app_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"  # ECR auth token is account-wide by design
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.rails_app.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_password.arn,
          aws_secretsmanager_secret.secret_key_base.arn,
          "arn:aws:secretsmanager:us-east-1:*:secret:myproject/production/*"
        ]
      }
    ]
  })
}

# ECS task role -- what the Rails app needs at runtime
resource "aws_iam_role" "rails_app_task" {
  name = "myproject-production-rails-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "rails_task_s3" {
  name = "s3-activestorage"
  role = aws_iam_role.rails_app_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.uploads.arn}/*"  # Objects only
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.uploads.arn  # Bucket itself
      }
    ]
  })
}
```

## Additional Context

- **Separate execution and task roles**: The execution role is used by ECS to pull images and fetch secrets. The task role is used by your application code at runtime. Never combine them.
- **Resource ARNs**: Always scope resources to specific ARNs. Use `${resource.arn}` references instead of hardcoding ARN patterns.
- **Condition keys**: Add IAM conditions for extra security (e.g., `aws:SourceVpc`, `s3:prefix`) when possible.
- **IAM Access Analyzer**: Use `aws_accessanalyzer_analyzer` to detect overly permissive policies in your account.
- **Review cadence**: Audit IAM policies quarterly. Remove unused permissions and roles.
