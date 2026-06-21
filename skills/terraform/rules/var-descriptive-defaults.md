---
title: "Descriptive Variables with Intentional Defaults"
id: var-descriptive-defaults
impact: MEDIUM
tags: [terraform, variables, documentation]
---

# Descriptive Variables with Intentional Defaults

Every variable must have a `description`. Use `default` only for truly optional values where a sensible fallback exists. Required values (secrets, project-specific names) must never have defaults.

## Incorrect

```hcl
# No descriptions, defaults on values that should be required
variable "project_name" {
  type    = string
  default = "myapp"
}

variable "db_password" {
  type    = string
  default = "changeme"
}

variable "ecs_cpu" {
  type = number
}

variable "enable_deletion_protection" {
  type = bool
}
```

## Correct

```hcl
# Required variables -- no default, forces explicit input
variable "project_name" {
  description = "Project name used for resource naming and tagging (e.g. rails_app)"
  type        = string
}

variable "db_password" {
  description = "Master password for RDS PostgreSQL instance"
  type        = string
  sensitive   = true
}

# Optional variables -- sensible defaults provided
variable "ecs_cpu" {
  description = "CPU units for ECS Fargate Rails task (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "ecs_memory" {
  description = "Memory (MiB) for ECS Fargate Rails task"
  type        = number
  default     = 1024
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection on RDS and ALB (disable only in dev)"
  type        = bool
  default     = true
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "rails_app_port" {
  description = "Port the Rails API listens on inside the container"
  type        = number
  default     = 3000
}

variable "centrifugo_port" {
  description = "Port Centrifugo WebSocket server listens on"
  type        = number
  default     = 8000
}
```

## Additional Context

- Descriptions serve as inline documentation for anyone running `terraform plan` or reading the module.
- Variables without defaults are required -- Terraform prompts or errors if they are missing, which is the correct behavior for project-specific or secret values.
- Default values signal "this works out of the box for most cases" -- use them for ports, instance sizes, feature flags, and other infrastructure parameters that have well-known starting points.
- Never default secrets, passwords, or project-specific identifiers. These must be explicitly provided per environment.
- Good descriptions include: what the value is, valid formats or ranges, and an example where helpful.
