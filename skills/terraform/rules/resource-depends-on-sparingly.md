---
title: "Use depends_on Sparingly"
id: resource-depends-on-sparingly
impact: HIGH
tags: [terraform, resources, dependencies]
---

# Use depends_on Sparingly

Prefer implicit dependencies through attribute references over explicit `depends_on`. Terraform automatically infers dependency order from resource references — `depends_on` should only be used for hidden dependencies that cannot be expressed through references.

## Incorrect

```hcl
# Unnecessary depends_on — Terraform already knows the dependency
# from the security_group_ids reference
resource "aws_security_group" "postgres" {
  name   = "${local.prefix}-postgres-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rails_app.id]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${local.prefix}-postgres"
  engine                 = "postgres"
  vpc_security_group_ids = [aws_security_group.postgres.id]

  # This depends_on is redundant — the security group reference
  # already creates an implicit dependency
  depends_on = [aws_security_group.postgres]
}
```

## Correct

```hcl
# Implicit dependency through attribute reference — no depends_on needed
resource "aws_security_group" "postgres" {
  name   = "${local.prefix}-postgres-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rails_app.id]
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${local.prefix}-postgres"
  engine                 = "postgres"
  vpc_security_group_ids = [aws_security_group.postgres.id]
  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  # Terraform knows: create SG and subnet group first, then RDS
}

# Valid use of depends_on — IAM policy attachment has no attribute
# referenced by the ECS service, but the service needs the policy
resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_service" "rails_app" {
  name            = "${local.prefix}-rails-service"
  cluster         = aws_ecs_cluster.rails.arn
  task_definition = aws_ecs_task_definition.rails_app.arn

  # Necessary: the service needs the policy attached before starting,
  # but no attribute reference creates this link
  depends_on = [aws_iam_role_policy_attachment.ecs_task_execution]
}
```

## Additional Context

Redundant `depends_on` blocks add noise and can mask the actual dependency graph. They also prevent Terraform from parallelizing resource creation when dependencies are overspecified. Legitimate uses of `depends_on` include IAM policy attachments (where the consuming resource does not reference the attachment directly), CloudWatch log groups that must exist before an ECS task starts logging, and `aws_internet_gateway` before NAT gateways when the reference path is indirect.
