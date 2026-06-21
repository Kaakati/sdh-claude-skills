---
title: "Resource Data Source Lookup"
id: resource-data-source-lookup
impact: HIGH
tags: [terraform, resources, data-sources]
---

# Resource Data Source Lookup

Use data sources for values that vary by account, region, or time (AMI IDs, account IDs, availability zones). Hardcoded values break when deploying to different environments or regions and become silently stale.

## Incorrect

```hcl
# Hardcoded AMI — stale after next update, wrong in other regions
resource "aws_ecs_service" "rails_app" {
  # ...
}

resource "aws_launch_template" "ecs_instance" {
  image_id = "ami-0c55b159cbfafe1f0"  # What is this? When was it current?
}

# Hardcoded account ID — breaks in staging/production accounts
resource "aws_iam_policy" "s3_access" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "arn:aws:s3:::123456789012-active-storage/*"
    }]
  })
}

# Hardcoded AZs — wrong in other regions
resource "aws_subnet" "private_a" {
  availability_zone = "us-east-1a"
  cidr_block        = "10.0.1.0/24"
  vpc_id            = aws_vpc.main.id
}
```

## Correct

```hcl
# Dynamic account ID
data "aws_caller_identity" "current" {}

# Dynamic region
data "aws_region" "current" {}

# Dynamic availability zones
data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

# Dynamic AMI lookup with filters
data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

# Usage — always current, works in any account/region
resource "aws_launch_template" "ecs_instance" {
  image_id = data.aws_ami.ecs_optimized.id
}

resource "aws_iam_policy" "s3_access" {
  policy = jsonencode({
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:GetObject"]
      Resource = "arn:aws:s3:::${var.project}-${var.environment}-active-storage/*"
    }]
  })
}

resource "aws_subnet" "private" {
  for_each          = { for i, az in data.aws_availability_zones.available.names : az => cidrsubnet(var.vpc_cidr, 8, i) }
  availability_zone = each.key
  cidr_block        = each.value
  vpc_id            = aws_vpc.main.id
}
```

## Additional Context

Common data sources for our stack: `aws_caller_identity` (account ID for ARNs), `aws_region` (current region), `aws_availability_zones` (AZs for subnet distribution), `aws_ami` (ECS-optimized AMI), `aws_ssm_parameter` (stored config values), and `aws_acm_certificate` (SSL certs for CloudFront/ALB). Data sources are read at plan time, so they always reflect the current state of AWS. Use `filter` blocks to be specific — avoid overly broad lookups that could match unintended resources.
