---
title: "Explicit Type Constraints on Variables"
id: var-type-constraints
impact: HIGH
tags: [terraform, variables, type-safety]
---

# Explicit Type Constraints on Variables

Every Terraform variable must declare an explicit `type` constraint. Untyped variables default to `any`, which bypasses validation and makes modules error-prone and hard to understand.

## Incorrect

```hcl
# No type declared -- defaults to "any", accepts anything
variable "vpc_cidr" {
  description = "VPC CIDR block"
}

variable "ecs_cpu" {
  description = "CPU units for ECS task"
}

variable "enable_multi_az" {
  description = "Enable multi-AZ for RDS"
}

variable "subnet_ids" {
  description = "Subnet IDs for deployment"
}
```

## Correct

```hcl
variable "vpc_cidr" {
  description = "CIDR block for the VPC (e.g. 10.0.0.0/16)"
  type        = string
}

variable "ecs_cpu" {
  description = "CPU units for ECS Fargate task (256, 512, 1024, 2048, 4096)"
  type        = number
}

variable "enable_multi_az" {
  description = "Enable Multi-AZ deployment for RDS PostgreSQL"
  type        = bool
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS service placement"
  type        = list(string)
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
}

variable "rds_config" {
  description = "RDS PostgreSQL configuration"
  type = object({
    instance_class    = string
    allocated_storage = number
    engine_version    = string
    multi_az          = bool
  })
}
```

## Additional Context

- `string`, `number`, `bool` cover most scalar values.
- `list(string)` and `map(string)` for collections.
- `object({...})` for structured configuration like RDS or ECS task definitions.
- Explicit types catch misconfiguration at `terraform plan` time instead of at apply or runtime.
- For our stack, common typed variables include: VPC CIDRs (string), ECS CPU/memory (number), Multi-AZ toggles (bool), subnet IDs (list(string)), and resource tags (map(string)).
