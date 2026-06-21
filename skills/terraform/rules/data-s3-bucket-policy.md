---
title: "S3 Bucket Security and Lifecycle"
id: data-s3-bucket-policy
impact: MEDIUM
tags: [terraform, data-stores, s3, security]
---

# S3 Bucket Security and Lifecycle

S3 buckets must block all public access, enable versioning and encryption, and define lifecycle rules. ActiveStorage buckets require specific CORS configuration.

## Incorrect

```hcl
# No public access block, no versioning, no encryption
resource "aws_s3_bucket" "uploads" {
  bucket = "myapp-uploads"
  # Missing: public access block, versioning, encryption, lifecycle
}
```

## Correct

```hcl
resource "aws_s3_bucket" "active_storage" {
  bucket = "${var.project}-${var.environment}-active-storage"

  tags = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id

  rule {
    id     = "expire-incomplete-uploads"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "transition-old-versions"
    status = "Enabled"

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "active_storage" {
  bucket = aws_s3_bucket.active_storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT", "POST"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3600
  }
}
```

## Additional Context

- All four `block_public_*` flags must be `true` to fully prevent public access.
- Versioning protects against accidental deletions and overwrites of user uploads.
- `AES256` (SSE-S3) is sufficient for most workloads; use `aws:kms` for regulated data.
- Abort incomplete multipart uploads after 7 days to avoid orphaned storage costs.
- Transition noncurrent versions to IA after 30 days, delete after 90 to control costs.
- CORS must be configured for direct browser uploads via ActiveStorage direct upload.
- Use `var.allowed_origins` instead of `["*"]` to restrict upload origins to your domains.
