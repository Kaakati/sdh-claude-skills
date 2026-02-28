---
title: "Use for_each Over count"
id: resource-for-each-over-count
impact: HIGH
tags: [terraform, resources, iteration]
---

# Use for_each Over count

Prefer `for_each` with maps or sets over `count` with lists. `count` uses numeric indices — removing an item from the middle shifts all subsequent indices, causing Terraform to destroy and recreate resources unnecessarily.

## Incorrect

```hcl
# count with a list — removing "us-east-1a" shifts indices,
# destroying subnet [1] and [2] then recreating them
variable "availability_zones" {
  default = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${local.prefix}-private-${count.index}"
  }
}
```

## Correct

```hcl
# for_each with a map — keys are stable, removing an AZ only
# destroys that specific subnet
variable "private_subnets" {
  description = "Map of AZ to CIDR for private subnets"
  type        = map(string)
  default = {
    "us-east-1a" = "10.0.1.0/24"
    "us-east-1b" = "10.0.2.0/24"
    "us-east-1c" = "10.0.3.0/24"
  }
}

resource "aws_subnet" "private" {
  for_each          = var.private_subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value
  availability_zone = each.key

  tags = {
    Name = "${local.prefix}-private-${each.key}"
  }
}

# Referencing for_each resources — use values()
resource "aws_db_subnet_group" "postgres" {
  name       = "${local.prefix}-postgres"
  subnet_ids = [for s in aws_subnet.private : s.id]
}
```

## Additional Context

`for_each` resources are keyed by map key or set element (`aws_subnet.private["us-east-1a"]`) instead of numeric index (`aws_subnet.private[0]`). This makes state addresses stable and human-readable. Use `count` only for conditional creation (`count = var.enable_feature ? 1 : 0`), never for iterating over collections. When migrating from `count` to `for_each`, use `terraform state mv` to avoid resource recreation.
