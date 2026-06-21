---
title: "Pin Provider Version Constraints"
id: sec-provider-version-constraint
impact: HIGH
tags: [terraform, security]
---

# Pin Provider Version Constraints

All Terraform providers must have explicit version constraints using the `~>` operator. Unpinned providers can auto-upgrade to versions with breaking changes, security vulnerabilities, or incompatible resource schemas.

## Incorrect

No version constraints on providers. Terraform downloads the latest version on every `init`, risking breaking changes.

```hcl
# terraform/environments/production/main.tf
# WRONG: No version pinning

terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      # Missing version constraint -- uses latest, which may break
    }
  }
}

provider "aws" {
  region = "us-east-1"
}
```

```hcl
# WRONG: Exact pinning is too rigid
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.31.0"  # No patch updates, must manually bump
    }
  }
}
```

## Correct

Use `~>` pessimistic constraint to allow patch updates while locking the minor version.

```hcl
# terraform/environments/production/main.tf
terraform {
  required_version = ">= 1.6.0, < 2.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"  # Allows 5.x, blocks 6.0
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"  # Allows 3.6.x, blocks 3.7
    }
  }

  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "myproject/production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "myproject-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "myproject"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

For modules, use broader constraints to allow consuming environments flexibility:

```hcl
# terraform/modules/rds/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0, < 6.0"  # Broader for module reuse
    }
  }
}
```

## Additional Context

- **Lock file**: Always commit `.terraform.lock.hcl` to version control. This pins the exact provider version and checksums, ensuring reproducible builds across team members and CI.
- **`~>` operator**: `~> 5.0` means `>= 5.0, < 6.0`. `~> 5.31` means `>= 5.31, < 5.32`. Use `~> X.0` for environments, `>= X.0, < Y.0` for modules.
- **Terraform version**: Pin with `required_version` to prevent running with incompatible Terraform CLI versions.
- **Update cadence**: Review provider updates monthly. Test updates in dev before applying to production. Use Dependabot or Renovate for automated PR generation.
- **Security patches**: The `~>` constraint allows automatic patch updates, which often include security fixes. Exact pinning (`=`) requires manual bumps for every security patch.
