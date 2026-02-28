---
title: "S3 Lifecycle Rules and Intelligent Tiering"
id: cost-s3-intelligent-tiering
impact: LOW
tags: [terraform, cost, s3, storage]
---

# S3 Lifecycle Rules and Intelligent Tiering

Configure lifecycle rules on S3 buckets to automatically transition infrequently accessed data to cheaper storage classes. Keep ActiveStorage buckets in Standard for fast access; apply tiering and archival policies to backups, logs, and exports.

## Incorrect

```hcl
# No lifecycle rules -- all data stays in Standard forever
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-${var.environment}-backups"
}

resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-${var.environment}-logs"
}

# Paying Standard pricing for years-old backup data that is never accessed
```

## Correct

```hcl
# ActiveStorage bucket -- Standard class, no tiering (fast access required)
resource "aws_s3_bucket" "active_storage" {
  bucket = "${var.project_name}-${var.environment}-active-storage"

  tags = {
    Name        = "${var.project_name}-${var.environment}-active-storage"
    Environment = var.environment
    Purpose     = "rails-active-storage"
  }
}

resource "aws_s3_bucket_versioning" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id
  versioning_configuration { status = "Enabled" }
}

# Database backups -- tier down aggressively
resource "aws_s3_bucket" "backups" {
  bucket = "${var.project_name}-${var.environment}-backups"

  tags = { Purpose = "database-backups" }
}

resource "aws_s3_bucket_lifecycle_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    id     = "transition-to-intelligent-tiering"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "INTELLIGENT_TIERING"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    expiration {
      days = 730  # Delete backups after 2 years
    }
  }
}

# Application logs -- expire after retention period
resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-${var.environment}-logs"

  tags = { Purpose = "application-logs" }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "log-retention"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365  # Comply with retention policy
    }
  }

  rule {
    id     = "cleanup-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}
```

## Additional Context

- **INTELLIGENT_TIERING** automatically moves objects between access tiers with no retrieval fees. Ideal for data with unpredictable access patterns.
- **STANDARD_IA** (Infrequent Access) is ~40% cheaper than Standard but has a per-GB retrieval fee. Good for logs accessed occasionally.
- **GLACIER** is ~80% cheaper than Standard but requires minutes-to-hours for retrieval. Good for backups older than 90 days.
- **DEEP_ARCHIVE** is the cheapest (~95% less) but requires 12+ hours for retrieval. Good for compliance archives.
- ActiveStorage buckets serve user-uploaded files (avatars, documents) and must stay in Standard for fast delivery via CloudFront.
- Always include `abort_incomplete_multipart_upload` to clean up failed uploads that silently accumulate storage costs.
- Align expiration policies with your data retention requirements (SOC2, GDPR, business policy).
