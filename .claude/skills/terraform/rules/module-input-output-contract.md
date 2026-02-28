---
title: "Module Input/Output Contract"
id: module-input-output-contract
impact: HIGH
tags: [terraform, modules, validation]
---

# Module Input/Output Contract

Every module variable must have a type constraint, description, and validation block where applicable. Untyped or undocumented inputs make modules fragile and hard to consume.

## Incorrect

```hcl
# modules/database/variables.tf — no types, no descriptions, no validation
variable "environment" {}

variable "instance_class" {
  default = "db.t3.medium"
}

variable "vpc_cidr" {}

variable "port" {
  default = 5432
}
```

## Correct

```hcl
# modules/database/variables.tf — typed, documented, validated
variable "environment" {
  description = "Deployment environment for the RDS instance"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be dev, staging, or production."
  }
}

variable "instance_class" {
  description = "RDS instance class for PostgreSQL"
  type        = string
  default     = "db.t3.medium"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC hosting the database"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid CIDR block (e.g., 10.0.0.0/16)."
  }
}

variable "port" {
  description = "Port for PostgreSQL connections"
  type        = number
  default     = 5432

  validation {
    condition     = var.port >= 1024 && var.port <= 65535
    error_message = "Port must be between 1024 and 65535."
  }
}

variable "subnet_ids" {
  description = "Private subnet IDs for the DB subnet group"
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) >= 2
    error_message = "At least 2 subnet IDs required for Multi-AZ."
  }
}
```

## Additional Context

Validation blocks catch misconfigurations at `terraform plan` time rather than during apply or, worse, at runtime. Always validate enumerations (environment names), formats (CIDR blocks, ARN patterns), and ranges (ports, instance counts). Use `can()` for format validation and `contains()` for allowed values.
