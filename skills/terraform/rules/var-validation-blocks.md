---
title: "Validation Blocks on Variables"
id: var-validation-blocks
impact: HIGH
tags: [terraform, variables, validation]
---

# Validation Blocks on Variables

Use `validation` blocks to catch invalid input at plan time. Validate CIDRs, port ranges, environment names, and any constrained value before Terraform attempts to create resources.

## Incorrect

```hcl
# No validation -- any string accepted, errors only at apply time
variable "environment" {
  description = "Deployment environment"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
}

variable "rails_app_port" {
  description = "Port for Rails application"
  type        = number
}
```

## Correct

```hcl
variable "environment" {
  description = "Deployment environment (dev, staging, production)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC (e.g. 10.0.0.0/16)"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid CIDR notation (e.g. 10.0.0.0/16)."
  }
}

variable "rails_app_port" {
  description = "Port for the Rails API container"
  type        = number

  validation {
    condition     = var.rails_app_port >= 1024 && var.rails_app_port <= 65535
    error_message = "rails_app_port must be between 1024 and 65535."
  }
}

variable "rds_instance_class" {
  description = "RDS instance class for PostgreSQL"
  type        = string

  validation {
    condition     = can(regex("^db\\.", var.rds_instance_class))
    error_message = "rds_instance_class must start with 'db.' (e.g. db.t3.medium)."
  }
}

variable "ecs_cpu" {
  description = "CPU units for ECS Fargate task"
  type        = number

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.ecs_cpu)
    error_message = "ecs_cpu must be a valid Fargate CPU value: 256, 512, 1024, 2048, or 4096."
  }
}
```

## Additional Context

- `can()` wraps expressions that might fail -- returns `false` instead of an error.
- `cidrhost(cidr, 0)` validates CIDR notation without needing a regex.
- `contains()` is ideal for enum-like values (environments, instance families).
- `regex()` inside `can()` validates string patterns like instance class prefixes.
- Multiple validation blocks can be added to a single variable for layered checks.
- Validation runs at `terraform plan`, giving fast feedback before any resources are touched.
