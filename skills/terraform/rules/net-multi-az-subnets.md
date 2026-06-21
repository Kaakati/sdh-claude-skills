---
title: "Multi-AZ Subnet Tiers"
id: net-multi-az-subnets
impact: MEDIUM
tags: [terraform, networking, subnets, high-availability]
---

# Multi-AZ Subnet Tiers

Deploy public, private, and database subnets across at least 2 availability zones. Single-AZ deployments are a single point of failure for all services in our stack.

## Incorrect

```hcl
# Single AZ -- entire stack goes down if the AZ has issues
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "us-east-1a"
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1a"
}

# No separation between application and database tiers
resource "aws_db_instance" "postgres_db" {
  db_subnet_group_name = aws_db_subnet_group.main.name
  # Placed in same subnet as ECS tasks
}
```

## Correct

```hcl
variable "availability_zones" {
  description = "AZs for multi-AZ deployment"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

# Public subnets -- ALB, NAT Gateways
resource "aws_subnet" "public" {
  for_each = { for idx, az in var.availability_zones : az => idx }

  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 4, each.value)
  availability_zone       = each.key
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.environment}-public-${each.key}"
    Tier = "public"
  }
}

# Private subnets -- ECS Fargate tasks (Rails, Centrifugo, Sidekiq)
resource "aws_subnet" "private" {
  for_each = { for idx, az in var.availability_zones : az => idx }

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, each.value + length(var.availability_zones))
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-${var.environment}-private-${each.key}"
    Tier = "private"
  }
}

# Database subnets -- RDS PostgreSQL, ElastiCache Redis
resource "aws_subnet" "database" {
  for_each = { for idx, az in var.availability_zones : az => idx }

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, each.value + 2 * length(var.availability_zones))
  availability_zone = each.key

  tags = {
    Name = "${var.project_name}-${var.environment}-database-${each.key}"
    Tier = "database"
  }
}

# Subnet groups for data services
resource "aws_db_subnet_group" "postgres_db" {
  name       = "${var.project_name}-${var.environment}-db"
  subnet_ids = [for s in aws_subnet.database : s.id]

  tags = { Name = "${var.project_name}-${var.environment}-db-subnet-group" }
}

resource "aws_elasticache_subnet_group" "redis_cache" {
  name       = "${var.project_name}-${var.environment}-redis"
  subnet_ids = [for s in aws_subnet.database : s.id]
}
```

## Additional Context

- **Public subnets**: ALB and NAT Gateways only. Never place application containers or databases here.
- **Private subnets**: ECS Fargate tasks (Rails API, Centrifugo, Sidekiq workers). Outbound via NAT Gateway.
- **Database subnets**: RDS PostgreSQL+PostGIS and ElastiCache Redis. No internet access, no NAT route.
- Use `for_each` over AZs instead of `count` for stable resource addressing when AZs change.
- RDS Multi-AZ and ElastiCache replicas require subnets in at least 2 AZs.
- Minimum 2 AZs for all environments; production should use 3 AZs where available.
