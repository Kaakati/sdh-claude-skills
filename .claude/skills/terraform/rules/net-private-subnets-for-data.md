---
title: "Private Subnets for Data Services"
id: net-private-subnets-for-data
impact: MEDIUM
tags: [terraform, networking, security, subnets]
---

# Private Subnets for Data Services

RDS, ElastiCache, and ECS tasks must be placed in private subnets only. Never expose databases or application containers to the public internet. The ALB is the only entry point from the internet.

## Incorrect

```hcl
# RDS publicly accessible -- database exposed to the internet
resource "aws_db_instance" "postgres_db" {
  identifier     = "${var.project_name}-${var.environment}-postgres"
  engine         = "postgres"
  instance_class = var.rds_instance_class

  publicly_accessible    = true  # NEVER do this
  db_subnet_group_name   = aws_db_subnet_group.public.name  # Wrong subnet tier

  skip_final_snapshot = true
}

# ElastiCache in public subnet
resource "aws_elasticache_cluster" "redis_cache" {
  cluster_id         = "${var.project_name}-${var.environment}-redis"
  engine             = "redis"
  subnet_group_name  = aws_elasticache_subnet_group.public.name  # Wrong tier
}

# ECS task in public subnet with public IP
resource "aws_ecs_service" "rails_app" {
  network_configuration {
    subnets          = [for s in aws_subnet.public : s.id]  # Wrong tier
    assign_public_ip = true  # Exposes container directly
  }
}
```

## Correct

```hcl
# RDS in database subnets, private only
resource "aws_db_instance" "postgres_db" {
  identifier     = "${var.project_name}-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = var.postgres_version
  instance_class = var.rds_instance_class

  publicly_accessible  = false
  db_subnet_group_name = aws_db_subnet_group.postgres_db.name

  vpc_security_group_ids = [aws_security_group.rds_postgres.id]

  tags = { Name = "${var.project_name}-${var.environment}-postgres" }
}

# ElastiCache in database subnets
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "${var.project_name}-${var.environment}-redis"
  description          = "Redis for Rails cache and Sidekiq"
  engine               = "redis"
  node_type            = var.redis_node_type
  num_cache_clusters   = var.environment == "production" ? 2 : 1
  subnet_group_name    = aws_elasticache_subnet_group.redis_cache.name
  security_group_ids   = [aws_security_group.redis_cache.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}

# ECS tasks in private subnets, no public IP
resource "aws_ecs_service" "rails_app" {
  name            = "${var.project_name}-${var.environment}-rails"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.rails_app.arn
  desired_count   = var.min_ecs_tasks

  network_configuration {
    subnets          = [for s in aws_subnet.private : s.id]
    security_groups  = [aws_security_group.ecs_rails.id]
    assign_public_ip = false  # Always false for private subnets
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.rails_app.arn
    container_name   = "rails_app"
    container_port   = var.rails_app_port
  }
}

# Security group: only ALB can reach ECS tasks
resource "aws_security_group" "ecs_rails" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-rails-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = var.rails_app_port
    to_port         = var.rails_app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security group: only ECS tasks can reach RDS
resource "aws_security_group" "rds_postgres" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_rails.id]
  }
}
```

## Additional Context

- Traffic flow: Internet -> ALB (public subnet) -> ECS (private subnet) -> RDS/Redis (database subnet).
- ECS tasks reach the internet via NAT Gateway for ECR image pulls, external API calls, and email delivery.
- Security groups form a chain: ALB -> ECS -> RDS/Redis. Each layer only accepts traffic from the previous one.
- `publicly_accessible = false` on RDS is a hard requirement. Even with security groups, public accessibility opens the door to misconfiguration.
- Enable encryption at rest and in transit for both RDS and ElastiCache in all environments.
- For database access during development, use SSM Session Manager or a bastion host in a private subnet -- never expose the database publicly.
