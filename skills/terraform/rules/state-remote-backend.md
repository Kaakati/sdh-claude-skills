---
title: "Always Use Remote State Backend"
id: state-remote-backend
impact: CRITICAL
tags: [terraform, state-management]
---

# Always Use Remote State Backend

Terraform state must be stored in a remote backend with encryption and versioning. Local state files risk data loss, prevent team collaboration, and cannot be locked for concurrent access.

## Incorrect

Local backend stores state on the developer's machine. No encryption, no locking, no versioning.

```hcl
# terraform/environments/dev/main.tf
# WRONG: Local state -- cannot collaborate, no locking, easy to lose

terraform {
  # No backend block = local state by default
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_ecs_service" "rails_app" {
  name            = "rails-app"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rails_app.arn
  desired_count   = 2
}
```

## Correct

S3 backend with DynamoDB locking, server-side encryption, and versioning enabled on the bucket.

```hcl
# terraform/environments/dev/backend.tf
terraform {
  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "myproject/dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "myproject-terraform-locks"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# terraform/global/state-infra/main.tf
# Bootstrap: create the state bucket and lock table first
resource "aws_s3_bucket" "terraform_state" {
  bucket = "myproject-terraform-state"

  tags = {
    Name        = "Terraform State"
    Environment = "global"
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = "myproject-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name      = "Terraform Lock Table"
    ManagedBy = "terraform"
  }
}
```

## Additional Context

- **Bootstrap problem**: The state bucket and DynamoDB table must be created before other Terraform runs. Use a separate `terraform/global/state-infra/` configuration with local state, or create them manually/via CloudFormation.
- **Key naming**: Use `{project}/{environment}/terraform.tfstate` for clear organization.
- **Bucket versioning**: Enables state recovery if a `terraform apply` corrupts state.
- **Encryption**: `encrypt = true` uses S3 server-side encryption. For compliance, specify a KMS key with `kms_key_id`.
- **Cross-account**: For multi-account setups, the state bucket lives in a shared infrastructure account with cross-account IAM roles.
