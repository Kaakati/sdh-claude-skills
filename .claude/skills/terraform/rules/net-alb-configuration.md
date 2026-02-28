---
title: "ALB Configuration with HTTPS and Health Checks"
id: net-alb-configuration
impact: MEDIUM
tags: [terraform, networking, alb, load-balancer]
---

# ALB Configuration with HTTPS and Health Checks

Configure the Application Load Balancer with HTTPS on port 443, HTTP-to-HTTPS redirect on port 80, proper health checks for Rails, and WebSocket support for Centrifugo.

## Incorrect

```hcl
# HTTP only -- no encryption in transit
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.rails_app.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.rails_app.arn
  }
}

# Default health check -- checks / with 30s interval, too slow for detection
resource "aws_lb_target_group" "rails_app" {
  port     = 3000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  # No health_check block -- uses defaults
}
```

## Correct

```hcl
resource "aws_lb" "rails_app" {
  name               = "${var.project_name}-${var.environment}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [for s in aws_subnet.public : s.id]

  enable_deletion_protection = var.environment == "production"

  tags = {
    Name        = "${var.project_name}-${var.environment}-alb"
    Environment = var.environment
  }
}

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

# HTTP redirect to HTTPS
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

# Rails API target group with health check
resource "aws_lb_target_group" "rails_app" {
  name        = "${var.project_name}-${var.environment}-rails"
  port        = var.rails_app_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"  # Required for ECS Fargate

  health_check {
    enabled             = true
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }

  stickiness {
    type    = "lb_cookie"
    enabled = false
  }
}

# Centrifugo WebSocket listener rule
resource "aws_lb_listener_rule" "centrifugo" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.centrifugo_service.arn
  }

  condition {
    path_pattern { values = ["/connection/websocket", "/connection/websocket/*"] }
  }
}

resource "aws_lb_target_group" "centrifugo_service" {
  name        = "${var.project_name}-${var.environment}-centrifugo"
  port        = var.centrifugo_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path    = "/health"
    matcher = "200"
  }
}
```

## Additional Context

- Use TLS 1.3 policy (`ELBSecurityPolicy-TLS13-1-2-2021-06`) for strongest encryption.
- `target_type = "ip"` is required for ECS Fargate (awsvpc network mode).
- The Rails `/health` endpoint should check database connectivity and Redis availability.
- Centrifugo WebSocket connections need path-based routing on the same ALB to avoid a second load balancer.
- Enable deletion protection on production ALBs to prevent accidental `terraform destroy`.
- Health check interval of 15s with 3 unhealthy threshold = 45s to mark unhealthy, fast enough for rolling deploys.
