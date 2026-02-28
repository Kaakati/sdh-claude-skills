---
title: "Configure State Locking"
id: state-lock-configuration
impact: CRITICAL
tags: [terraform, state-management]
---

# Configure State Locking

Every remote backend must have state locking configured to prevent concurrent modifications. Without locking, simultaneous `terraform apply` runs can corrupt state and cause infrastructure drift.

## Incorrect

S3 backend without DynamoDB locking. Two developers or CI pipelines can run apply simultaneously and corrupt state.

```hcl
# terraform/environments/staging/backend.tf
# WRONG: No DynamoDB table for locking

terraform {
  backend "s3" {
    bucket  = "myproject-terraform-state"
    key     = "myproject/staging/terraform.tfstate"
    region  = "us-east-1"
    encrypt = true
    # Missing: dynamodb_table -- no state locking!
  }
}
```

## Correct

S3 backend with DynamoDB table for state locking. Terraform acquires a lock before any state-modifying operation and releases it when done.

```hcl
# terraform/environments/staging/backend.tf
terraform {
  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "myproject/staging/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "myproject-terraform-locks"
  }
}
```

The DynamoDB table is shared across all environments -- each state file gets its own lock entry keyed by the S3 path.

```hcl
# terraform/global/state-infra/main.tf
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "myproject-terraform-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "Terraform Lock Table"
    Environment = "global"
    Project     = "myproject"
    ManagedBy   = "terraform"
  }
}
```

## Additional Context

- **PAY_PER_REQUEST billing**: Lock operations are infrequent; on-demand pricing is more cost-effective than provisioned capacity.
- **Shared table**: A single DynamoDB table can serve all environments and projects. Each lock entry is keyed by the full S3 state path.
- **Lock timeout**: If a `terraform apply` crashes mid-run, the lock persists. Use `terraform force-unlock <LOCK_ID>` only after confirming no other operation is running.
- **CI/CD safety**: In CI pipelines, always use `-lock-timeout=5m` to wait for an existing lock rather than failing immediately:
  ```bash
  terraform apply -lock-timeout=5m -auto-approve
  ```
- **Never disable locking**: The `-lock=false` flag exists for debugging only. Never use it in CI or production workflows.
