---
title: "NAT Gateway High Availability"
id: net-nat-gateway-ha
impact: MEDIUM
tags: [terraform, networking, nat, high-availability]
---

# NAT Gateway High Availability

Deploy one NAT Gateway per AZ in production for fault tolerance. Use a single NAT Gateway in dev/staging to save costs. A single NAT in production is a single point of failure -- if its AZ goes down, all private subnet outbound traffic stops.

## Incorrect

```hcl
# Single NAT Gateway in production -- AZ failure kills all outbound traffic
resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["us-east-1a"].id

  tags = { Name = "${var.project_name}-nat" }
}

resource "aws_eip" "nat" {
  domain = "vpc"
}

# All private subnets route through the single NAT
resource "aws_route" "private_nat" {
  for_each               = aws_subnet.private
  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}
```

## Correct

```hcl
locals {
  # One NAT per AZ in production, single NAT in dev/staging
  nat_azs = var.environment == "production" ? var.availability_zones : [var.availability_zones[0]]
}

resource "aws_eip" "nat" {
  for_each = toset(local.nat_azs)
  domain   = "vpc"

  tags = { Name = "${var.project_name}-${var.environment}-nat-${each.key}" }
}

resource "aws_nat_gateway" "main" {
  for_each = toset(local.nat_azs)

  allocation_id = aws_eip.nat[each.key].id
  subnet_id     = aws_subnet.public[each.key].id

  tags = { Name = "${var.project_name}-${var.environment}-nat-${each.key}" }

  depends_on = [aws_internet_gateway.main]
}

# Each private subnet routes to the NAT in its own AZ (prod)
# or to the single NAT (dev/staging)
resource "aws_route" "private_nat" {
  for_each = aws_subnet.private

  route_table_id         = aws_route_table.private[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id = (
    contains(keys(aws_nat_gateway.main), each.key)
    ? aws_nat_gateway.main[each.key].id
    : aws_nat_gateway.main[local.nat_azs[0]].id
  )
}
```

## Additional Context

- NAT Gateways cost ~$32/month each plus data processing charges. In dev, a single NAT saves $64+/month with 3 AZs.
- Production must have one NAT per AZ so ECS tasks (Rails, Sidekiq, Centrifugo) maintain outbound connectivity during AZ failures.
- ECS Fargate tasks in private subnets need NAT for: pulling container images from ECR, connecting to external APIs, sending emails, and accessing AWS services without VPC endpoints.
- Consider VPC endpoints for ECR, S3, CloudWatch, and Secrets Manager to reduce NAT data transfer costs and improve reliability.
- The `depends_on` for the internet gateway prevents race conditions during initial creation.
- Cross-AZ NAT traffic incurs data transfer charges ($0.01/GB), so same-AZ routing is preferred in production.
