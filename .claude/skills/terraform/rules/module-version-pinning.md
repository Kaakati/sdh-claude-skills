---
title: "Module Version Pinning"
id: module-version-pinning
impact: HIGH
tags: [terraform, modules, versioning]
---

# Module Version Pinning

Pin all module sources to a specific version or git ref. Unpinned modules can introduce breaking changes on the next `terraform init`, causing unexpected infrastructure drift or failures.

## Incorrect

```hcl
# No version constraint — pulls latest, may break at any time
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
}

# Git source without ref — always uses HEAD of default branch
module "ecs" {
  source = "git::https://github.com/our-org/terraform-ecs.git"
}

# Local module with no versioning strategy
module "database" {
  source = "../../modules/database"
  # No way to track which version of the module is deployed
}
```

## Correct

```hcl
# Registry module — pinned with pessimistic constraint
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.5.0"
}

# Git source — pinned to a tagged release
module "ecs" {
  source = "git::https://github.com/our-org/terraform-ecs.git?ref=v2.1.0"
}

# Internal registry module — pinned version
module "rails_service" {
  source  = "app.terraform.io/our-org/ecs-service/aws"
  version = "~> 1.3.0"
}
```

```hcl
# versions.tf — pin provider versions alongside modules
terraform {
  required_version = "~> 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40.0"
    }
  }
}
```

## Additional Context

Use `~>` (pessimistic constraint) to allow patch updates while preventing minor/major version jumps. For git sources, always use `?ref=vX.Y.Z` tags — never branch names. For local modules in a monorepo (our `terraform/modules/` directory), version control is handled by git itself, but tag releases when modules are shared across teams. Always run `terraform init -upgrade` explicitly when you intend to update module versions, never implicitly.
