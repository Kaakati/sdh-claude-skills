---
title: "Module README Documentation"
id: module-readme-documentation
impact: HIGH
tags: [terraform, modules, documentation]
---

# Module README Documentation

Every module directory must contain a README.md with a description, usage example, inputs table, and outputs table. Undocumented modules become tribal knowledge that slows onboarding and increases risk of misconfiguration.

## Incorrect

```
terraform/modules/database/
  main.tf
  variables.tf
  outputs.tf
  # No README.md — consumers must read HCL to understand usage
```

## Correct

```
terraform/modules/database/
  README.md
  main.tf
  variables.tf
  outputs.tf
```

````markdown
# Database Module

Provisions an RDS PostgreSQL instance with PostGIS extension, Multi-AZ
failover, automated backups, and encryption at rest. Designed for the
Rails API backend.

## Usage

```hcl
module "database" {
  source            = "../../modules/database"
  project           = "myapp"
  environment       = "production"
  engine_version    = "15.4"
  instance_class    = "db.r6g.large"
  allocated_storage = 100
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.networking.db_security_group_id
  postgis           = true
}
```

## Inputs

| Name | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| project | string | — | yes | Project name for resource naming |
| environment | string | — | yes | dev, staging, or production |
| engine_version | string | "15.4" | no | PostgreSQL engine version |
| instance_class | string | "db.t3.medium" | no | RDS instance class |
| subnet_ids | list(string) | — | yes | Private subnet IDs (min 2) |
| security_group_id | string | — | yes | Security group for DB access |
| postgis | bool | false | no | Enable PostGIS extension |

## Outputs

| Name | Description |
|------|-------------|
| connection_url | PostgreSQL connection URL (sensitive) |
| endpoint | RDS endpoint (host:port) |
| port | RDS port number |
| security_group_id | DB security group ID |
````

## Additional Context

Use `terraform-docs` to auto-generate input/output tables from HCL and keep documentation in sync with code. Run `terraform-docs markdown table ./modules/database > ./modules/database/README.md` in CI to catch drift. Always include a realistic usage example referencing our module structure so new team members can copy-paste and adapt.
