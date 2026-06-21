---
title: "VPC CIDR Block Planning"
id: net-vpc-cidr-planning
impact: MEDIUM
tags: [terraform, networking, vpc]
---

# VPC CIDR Block Planning

Plan VPC CIDRs before provisioning. Use /16 for production, /20+ for dev, and reserve non-overlapping ranges for VPC peering, transit gateways, and future expansion.

## Incorrect

```hcl
# Overlapping CIDRs -- blocks VPC peering between environments
resource "aws_vpc" "production" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_vpc" "staging" {
  cidr_block = "10.0.0.0/16"  # Overlaps with production!
}

# Too small for production workloads
resource "aws_vpc" "prod_small" {
  cidr_block = "10.0.0.0/24"  # Only 256 IPs -- will run out
}
```

## Correct

```hcl
# Documented CIDR plan with no overlaps
# 10.0.0.0/16  = production   (65,536 IPs)
# 10.1.0.0/20  = staging      (4,096 IPs)
# 10.2.0.0/20  = dev          (4,096 IPs)
# 10.10.0.0/16 = reserved for VPC peering / shared services

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-vpc"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid CIDR block."
  }
}

# Subnet CIDRs derived from VPC CIDR
locals {
  # Production /16 splits into /20 subnets (4,096 IPs each)
  # Dev/staging /20 splits into /24 subnets (256 IPs each)
  subnet_newbits = var.environment == "production" ? 4 : 4
  az_count       = length(var.availability_zones)
}

resource "aws_subnet" "public" {
  count             = local.az_count
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, local.subnet_newbits, count.index)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.project_name}-${var.environment}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  }
}
```

## Additional Context

- Document the full CIDR allocation plan in a `docs/network-plan.md` or as comments in the VPC module.
- Use `cidrsubnet()` to derive subnet CIDRs from the VPC CIDR -- avoids manual math and errors.
- Always enable `enable_dns_support` and `enable_dns_hostnames` for ECS service discovery and RDS DNS endpoints.
- Reserve at least one /16 block for future VPC peering or shared services (monitoring, CI runners).
- For our stack: production needs room for ECS tasks (dynamic IPs), RDS multi-AZ (multiple ENIs), ElastiCache nodes, and NAT gateway ENIs.
- AWS reserves 5 IPs per subnet (first 4 + last 1), so a /24 gives 251 usable IPs, not 256.
