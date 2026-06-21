---
title: "Encryption at Rest for All Data Stores"
id: sec-encryption-at-rest
impact: CRITICAL
tags: [terraform, security]
---

# Encryption at Rest for All Data Stores

Every data store must have encryption at rest enabled: RDS, S3, ElastiCache, EBS volumes, and Secrets Manager. Unencrypted data at rest violates compliance requirements and exposes data if storage media is compromised.

## Incorrect

Data stores created without encryption configuration.

```hcl
# WRONG: RDS without encryption
resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.r6g.xlarge"
  # Missing: storage_encrypted, kms_key_id
}

# WRONG: S3 bucket without encryption
resource "aws_s3_bucket" "uploads" {
  bucket = "myproject-production-uploads"
  # Missing: server-side encryption configuration
}

# WRONG: ElastiCache without encryption
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "myproject-production-redis"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  # Missing: at_rest_encryption_enabled
}
```

## Correct

All data stores encrypted with KMS keys.

```hcl
# terraform/modules/kms/main.tf
resource "aws_kms_key" "data_encryption" {
  description             = "KMS key for myproject data encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name        = "myproject-data-encryption"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_kms_alias" "data_encryption" {
  name          = "alias/myproject-${var.environment}-data"
  target_key_id = aws_kms_key.data_encryption.key_id
}

# terraform/modules/rds/main.tf
resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.instance_class

  storage_encrypted = true
  kms_key_id        = var.kms_key_arn

  tags = {
    Name        = "myproject-${var.environment}-postgres"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# terraform/modules/s3/main.tf
resource "aws_s3_bucket" "uploads" {
  bucket = "myproject-${var.environment}-uploads"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = true  # Reduces KMS API costs
  }
}

# terraform/modules/elasticache/main.tf
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "myproject-${var.environment}-redis"
  description          = "Redis for Rails cache and Sidekiq"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.node_type

  at_rest_encryption_enabled = true
  kms_key_id                 = var.kms_key_arn

  tags = {
    Name        = "myproject-${var.environment}-redis"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# EBS volumes (for any EC2-based workloads)
resource "aws_ebs_default_encryption" "enabled" {
  enabled    = true
  kms_key_id = var.kms_key_arn
}
```

## Additional Context

- **KMS key rotation**: Always enable automatic key rotation (`enable_key_rotation = true`). AWS rotates the key material annually while keeping the key ID stable.
- **S3 bucket key**: Enable `bucket_key_enabled = true` to reduce KMS API calls and costs for S3 encryption.
- **RDS limitation**: Encryption cannot be enabled on an existing unencrypted RDS instance. You must create an encrypted snapshot and restore from it.
- **Default EBS encryption**: Use `aws_ebs_default_encryption` to encrypt all new EBS volumes in the account by default.
- **Compliance**: SOC2, HIPAA, and PCI-DSS all require encryption at rest. This is a non-negotiable requirement for production infrastructure.
- **Cost**: KMS costs are minimal (~$1/month per key + $0.03 per 10,000 API calls). Bucket keys further reduce S3 encryption costs.
