---
title: "ECR Lifecycle Policy"
id: compute-ecr-lifecycle-policy
impact: MEDIUM
tags: [terraform, compute, ecr, cost-optimization]
---

# ECR Lifecycle Policy

ECR repositories must have lifecycle policies to expire untagged images after 30 days and retain only the last 10 tagged images. Without policies, images accumulate indefinitely.

## Incorrect

```hcl
# No lifecycle policy — images accumulate, storage costs grow unbounded
resource "aws_ecr_repository" "rails_app" {
  name = "rails-app"
}
```

## Correct

```hcl
resource "aws_ecr_repository" "rails_app" {
  name                 = "${var.project}/${var.environment}/rails-app"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = local.common_tags
}

resource "aws_ecr_lifecycle_policy" "rails_app" {
  repository = aws_ecr_repository.rails_app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images after 30 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Keep only the last 10 tagged images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v", "release", "deploy"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

## Additional Context

- `image_tag_mutability = "IMMUTABLE"` prevents tag overwriting, ensuring deploy reproducibility.
- `scan_on_push = true` runs vulnerability scans on every pushed image automatically.
- Untagged images are typically intermediate build layers; 30-day expiry is safe for debugging.
- The `tagPrefixList` targets release/deploy tags; adjust prefixes to match your CI tagging scheme.
- Keeping 10 tagged images allows rollback to recent deployments while controlling storage costs.
- Rule priority determines evaluation order; lower numbers are evaluated first.
- Without lifecycle policies, a busy CI pipeline can accumulate thousands of images per month.
