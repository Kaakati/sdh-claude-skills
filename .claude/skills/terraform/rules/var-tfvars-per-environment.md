---
title: "Separate tfvars per Environment"
id: var-tfvars-per-environment
impact: MEDIUM
tags: [terraform, variables, environments]
---

# Separate tfvars per Environment

Use dedicated `.tfvars` files for each environment. A single shared `terraform.tfvars` leads to accidental production changes and makes it impossible to review environment-specific configuration at a glance.

## Incorrect

```hcl
# Single terraform.tfvars for all environments -- dangerous
# terraform.tfvars
project_name       = "rails_app"
environment        = "production"
vpc_cidr           = "10.0.0.0/16"
ecs_cpu            = 1024
ecs_memory         = 2048
rds_instance_class = "db.r5.large"
redis_node_type    = "cache.r5.large"
enable_multi_az    = true

# Developer manually edits values before switching environments
# Risk: forgetting to change environment = "production" back to "dev"
```

## Correct

```
# Directory structure
infrastructure/
  environments/
    dev/
      dev.tfvars
      backend.hcl
    staging/
      staging.tfvars
      backend.hcl
    production/
      production.tfvars
      backend.hcl
  modules/
    ecs/
    rds/
    vpc/
  main.tf
  variables.tf
  outputs.tf
```

```hcl
# environments/dev/dev.tfvars
project_name       = "rails_app"
environment        = "dev"
vpc_cidr           = "10.1.0.0/20"
ecs_cpu            = 256
ecs_memory         = 512
rds_instance_class = "db.t3.small"
redis_node_type    = "cache.t3.micro"
enable_multi_az    = false
min_ecs_tasks      = 1
max_ecs_tasks      = 2
```

```hcl
# environments/production/production.tfvars
project_name       = "rails_app"
environment        = "production"
vpc_cidr           = "10.0.0.0/16"
ecs_cpu            = 1024
ecs_memory         = 2048
rds_instance_class = "db.r5.large"
redis_node_type    = "cache.r5.large"
enable_multi_az    = true
min_ecs_tasks      = 2
max_ecs_tasks      = 10
```

```bash
# Apply with explicit var-file -- no ambiguity about which environment
terraform plan -var-file=environments/dev/dev.tfvars
terraform apply -var-file=environments/production/production.tfvars

# Combined with backend config for state isolation
terraform init -backend-config=environments/dev/backend.hcl
```

## Additional Context

- Never name a file `terraform.tfvars` or `*.auto.tfvars` -- these are loaded automatically and bypass the explicit `-var-file` flag, which defeats environment isolation.
- Each environment should have its own remote state backend (separate S3 keys or DynamoDB tables) configured in `backend.hcl`.
- Secrets (db_password, API keys) should not appear in `.tfvars` files. Use `TF_VAR_db_password` environment variables or a secret manager.
- CI pipelines select the correct `.tfvars` based on the deployment target branch or environment variable.
- This pattern works well with Terraform workspaces, but separate directories give clearer isolation for our stack where dev, staging, and production differ significantly in sizing.
