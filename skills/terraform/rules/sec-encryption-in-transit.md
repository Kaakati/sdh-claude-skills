---
title: "Encryption in Transit"
id: sec-encryption-in-transit
impact: HIGH
tags: [terraform, security]
---

# Encryption in Transit

All data in transit must be encrypted. Enforce TLS for RDS connections, ElastiCache transit encryption, HTTPS-only on ALBs, and SSL for all service-to-service communication.

## Incorrect

Services configured without transit encryption.

```hcl
# WRONG: RDS without forced SSL
resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-production-postgres"
  engine         = "postgres"
  instance_class = "db.r6g.xlarge"
  # Missing: parameter group enforcing SSL
}

# WRONG: ElastiCache without transit encryption
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "myproject-production-redis"
  engine               = "redis"
  node_type            = "cache.r6g.large"
  # Missing: transit_encryption_enabled
}

# WRONG: ALB listener on HTTP without redirect
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.rails_app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_app.arn
    # WRONG: Forwarding HTTP traffic instead of redirecting to HTTPS
  }
}
```

## Correct

TLS enforced on all data paths.

```hcl
# terraform/modules/rds/main.tf

# Force SSL connections to PostgreSQL
resource "aws_db_parameter_group" "postgres" {
  family = "postgres15"
  name   = "myproject-${var.environment}-postgres"

  parameter {
    name  = "rds.force_ssl"
    value = "1"
  }

  tags = {
    Name        = "myproject-${var.environment}-postgres-params"
    Environment = var.environment
  }
}

resource "aws_db_instance" "postgres_db" {
  identifier     = "myproject-${var.environment}-postgres"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = var.instance_class

  parameter_group_name = aws_db_parameter_group.postgres.name

  storage_encrypted = true
  kms_key_id        = var.kms_key_arn
}

# terraform/modules/elasticache/main.tf

# Enable transit encryption for Redis
resource "aws_elasticache_replication_group" "redis_cache" {
  replication_group_id = "myproject-${var.environment}-redis"
  description          = "Redis for Rails cache and Sidekiq"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = var.node_type

  transit_encryption_enabled = true
  at_rest_encryption_enabled = true
  kms_key_id                 = var.kms_key_arn

  # auth_token sourced from var.redis_auth_token (sensitive variable)
  # Store the actual value in AWS Secrets Manager, pass via TF_VAR
}

# terraform/modules/alb/main.tf

# HTTPS listener with ACM certificate
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.rails_app.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = var.acm_certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_app.arn
  }
}

# HTTP listener redirects to HTTPS
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.rails_app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# CloudFront with TLS 1.2 minimum
resource "aws_cloudfront_distribution" "cdn" {
  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  # Force HTTPS to origin
  default_cache_behavior {
    viewer_protocol_policy = "redirect-to-https"
    # ...
  }
}
```

## Additional Context

- **SSL policy**: Use `ELBSecurityPolicy-TLS13-1-2-2021-06` or newer. Older policies allow deprecated TLS versions.
- **Redis AUTH**: When `transit_encryption_enabled = true`, Redis requires an AUTH credential. Store it in Secrets Manager and pass via a sensitive variable.
- **Rails DATABASE_URL**: With `rds.force_ssl = 1`, use `sslmode=require` in the Rails `DATABASE_URL`.
- **Centrifugo**: Configure the Centrifugo ECS service with TLS termination at the ALB. WebSocket connections use `wss://` protocol.
- **CloudFront**: Set `minimum_protocol_version = "TLSv1.2_2021"` and `viewer_protocol_policy = "redirect-to-https"` on all behaviors.
