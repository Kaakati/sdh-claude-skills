---
title: "Directory-Based Environment Isolation"
id: state-workspace-isolation
impact: CRITICAL
tags: [terraform, state-management]
---

# Directory-Based Environment Isolation

Use separate directories per environment instead of Terraform workspaces. Workspaces share the same configuration, making it impossible to have different resource sizes, feature flags, or provider configurations per environment.

## Incorrect

Using Terraform workspaces for environment separation. All environments share identical configuration -- you cannot size production differently from dev.

```hcl
# terraform/main.tf
# WRONG: Single config with workspace-based switching

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-${terraform.workspace}-postgres"
  engine         = "postgres"
  engine_version = "15.4"

  # Fragile workspace-based conditionals everywhere
  instance_class    = terraform.workspace == "production" ? "db.r6g.xlarge" : "db.t3.medium"
  allocated_storage = terraform.workspace == "production" ? 100 : 20
  multi_az          = terraform.workspace == "production" ? true : false

  # What if staging needs a unique setting? More ternaries...
}
```

```bash
# WRONG: Workspace-based workflow
terraform workspace new staging
terraform workspace select staging
terraform apply
```

## Correct

Separate directory per environment with its own backend config, variables, and resource definitions. Shared logic lives in reusable modules.

```
terraform/
  modules/
    rds/
      main.tf
      variables.tf
      outputs.tf
    ecs/
      main.tf
      variables.tf
      outputs.tf
  environments/
    dev/
      backend.tf
      main.tf
      variables.tf
      terraform.tfvars
    staging/
      backend.tf
      main.tf
      variables.tf
      terraform.tfvars
    production/
      backend.tf
      main.tf
      variables.tf
      terraform.tfvars
```

```hcl
# terraform/environments/production/main.tf
module "postgres_db" {
  source = "../../modules/rds"

  identifier     = "myproject-production-postgres"
  instance_class = "db.r6g.xlarge"
  storage_gb     = 100
  multi_az       = true
  engine_version = "15.4"

  # Production-specific settings
  backup_retention_period    = 30
  deletion_protection        = true
  performance_insights       = true
  monitoring_interval        = 10
}

# terraform/environments/dev/main.tf
module "postgres_db" {
  source = "../../modules/rds"

  identifier     = "myproject-dev-postgres"
  instance_class = "db.t3.medium"
  storage_gb     = 20
  multi_az       = false
  engine_version = "15.4"

  backup_retention_period = 7
  deletion_protection     = false
  performance_insights    = false
}
```

## Additional Context

- **Why not workspaces**: Workspaces were designed for testing configuration changes, not environment isolation. They share backend config, provider versions, and module sources -- making environment-specific customization painful.
- **Module reuse**: Extract all resource definitions into `terraform/modules/`. Environments consume modules with environment-specific variables.
- **State isolation**: Each environment directory has its own `backend.tf` with a unique state key, ensuring complete state isolation.
- **Independent lifecycle**: Production can be on a different Terraform version or provider version than dev. Directories make this trivial; workspaces make it impossible.
- **CI/CD**: Each environment directory is a separate Terraform root module, applied independently in the pipeline.
