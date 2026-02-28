---
title: "Never Use Default VPC"
id: sec-no-default-vpc
impact: MEDIUM
tags: [terraform, security]
---

# Never Use Default VPC

Always create a dedicated VPC with custom CIDR blocks, subnet tiers, and security controls. The default VPC has overly permissive security groups, public subnets by default, and a non-standard network layout that does not meet production requirements.

## Incorrect

Using the default VPC for production resources.

```hcl
# terraform/environments/production/main.tf
# WRONG: Referencing the default VPC

data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.xlarge"

  # WRONG: Default VPC subnets are all public
  db_subnet_group_name = aws_db_subnet_group.default.name
}

resource "aws_db_subnet_group" "default" {
  name       = "default"
  subnet_ids = data.aws_subnets.default.ids
  # All subnets in default VPC have public IPs -- DB is internet-routable!
}
```

## Correct

Create a dedicated VPC with proper subnet tiers: public (ALB), private (ECS, app), and data (RDS, Redis).

```hcl
# terraform/modules/vpc/main.tf
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr  # e.g., "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "myproject-${var.environment}"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Public subnets -- ALB only
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = var.availability_zones[count.index]

  map_public_ip_on_launch = true  # Only for public subnet

  tags = {
    Name        = "myproject-${var.environment}-public-${var.availability_zones[count.index]}"
    Environment = var.environment
    Tier        = "public"
  }
}

# Private subnets -- ECS Fargate tasks, Centrifugo
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "myproject-${var.environment}-private-${var.availability_zones[count.index]}"
    Environment = var.environment
    Tier        = "private"
  }
}

# Data subnets -- RDS, ElastiCache (most restricted)
resource "aws_subnet" "data" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 20)
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name        = "myproject-${var.environment}-data-${var.availability_zones[count.index]}"
    Environment = var.environment
    Tier        = "data"
  }
}

# Internet gateway for public subnets
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "myproject-${var.environment}-igw"
    Environment = var.environment
  }
}

# Place RDS in data subnets only
resource "aws_db_subnet_group" "postgres" {
  name       = "myproject-${var.environment}-postgres"
  subnet_ids = aws_subnet.data[*].id

  tags = {
    Name        = "myproject-${var.environment}-postgres"
    Environment = var.environment
  }
}

# Place ElastiCache in data subnets only
resource "aws_elasticache_subnet_group" "redis" {
  name       = "myproject-${var.environment}-redis"
  subnet_ids = aws_subnet.data[*].id
}
```

## Additional Context

- **Three subnet tiers**: Public (ALB, NAT Gateway), Private (ECS tasks, application), Data (RDS, ElastiCache). Each tier has its own route table and security profile.
- **No public IPs on private/data subnets**: Only public subnets should have `map_public_ip_on_launch = true`. Private and data subnets reach the internet via NAT gateways.
- **Default VPC risks**: All subnets are public, the default security group allows all outbound traffic, and the default NACL allows all traffic. This is inappropriate for production workloads.
- **CIDR planning**: Use a `/16` VPC (65,536 IPs) with `/24` subnets (256 IPs each). Reserve CIDR space for VPC peering and future growth.
- **Delete the default VPC**: As a security hardening step, consider deleting the default VPC in production accounts to prevent accidental use.
