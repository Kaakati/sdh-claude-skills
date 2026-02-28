---
title: "Restrict Security Group Ingress"
id: sec-security-group-restrict
impact: HIGH
tags: [terraform, security]
---

# Restrict Security Group Ingress

Never allow `0.0.0.0/0` (all IPs) ingress on non-public ports. Only ALB listeners on ports 80/443 may accept traffic from the internet. Database, cache, and application ports must be restricted to VPC CIDR blocks or specific security groups.

## Incorrect

Database and Redis ports open to the internet.

```hcl
# WRONG: PostgreSQL open to the world
resource "aws_security_group" "postgres_db" {
  name   = "myproject-postgres"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # NEVER: DB exposed to internet
  }
}

# WRONG: Redis open to the world
resource "aws_security_group" "redis_cache" {
  name   = "myproject-redis"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # NEVER: Redis exposed to internet
  }
}

# WRONG: SSH open to the world
resource "aws_security_group" "bastion" {
  name   = "myproject-bastion"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # NEVER: SSH from anywhere
  }
}
```

## Correct

Security groups reference other security groups or VPC CIDRs. Only the ALB accepts public traffic.

```hcl
# terraform/modules/security-groups/main.tf

# ALB -- only resource accepting public traffic
resource "aws_security_group" "alb" {
  name        = "myproject-${var.environment}-alb"
  description = "ALB accepts HTTP/HTTPS from internet"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP from internet (redirects to HTTPS)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # OK: public ALB
  }

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # OK: public ALB
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "myproject-${var.environment}-alb"
    Environment = var.environment
  }
}

# ECS tasks -- only accept traffic from ALB
resource "aws_security_group" "ecs_tasks" {
  name        = "myproject-${var.environment}-ecs"
  description = "ECS Fargate tasks -- traffic from ALB only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # ALB SG only
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# PostgreSQL -- only accept traffic from ECS tasks
resource "aws_security_group" "postgres_db" {
  name        = "myproject-${var.environment}-postgres"
  description = "RDS PostgreSQL -- traffic from ECS tasks only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]  # ECS SG only
  }
}

# Redis -- only accept traffic from ECS tasks
resource "aws_security_group" "redis_cache" {
  name        = "myproject-${var.environment}-redis"
  description = "ElastiCache Redis -- traffic from ECS tasks only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]  # ECS SG only
  }
}
```

## Additional Context

- **Security group chaining**: ALB -> ECS -> RDS/Redis. Each layer only accepts traffic from the layer above it.
- **No CIDR for internal traffic**: Use security group references (`security_groups = [sg.id]`) instead of VPC CIDR blocks when possible. SG references survive VPC CIDR changes and are more precise.
- **Egress**: ECS tasks need outbound internet access for pulling ECR images and reaching AWS APIs. Use NAT gateways in private subnets.
- **Centrifugo**: The Centrifugo WebSocket service gets its own security group, accepting traffic from the ALB on its configured port.
- **Bastion/SSH**: Prefer AWS Systems Manager Session Manager over SSH bastions. If SSH is required, restrict to VPN CIDR or specific office IPs, never `0.0.0.0/0`.
