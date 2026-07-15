# Terraform Repository Layout

Where every Terraform file lives in our AWS stack, and which file owns which concern.

The individual conventions (remote state, directory-based isolation, module single responsibility,
per-environment tfvars) each have their own rule file — `rules/state-remote-backend.md`,
`rules/state-workspace-isolation.md`, `rules/module-single-responsibility.md`,
`rules/var-tfvars-per-environment.md`. This reference answers the layout questions those rules
leave open: what the canonical tree looks like as a whole, and which file a given block belongs in.

## Decision: what is the canonical tree?

```
terraform/
  global/
    state-infra/        # State bucket + lock table (bootstrap, local state)
  environments/
    dev/
      main.tf           # Root module composing child modules
      variables.tf      # Environment-specific variable declarations
      outputs.tf        # Environment outputs
      backend.tf        # backend "s3" — this environment's state key
      versions.tf       # required_version + required_providers
      providers.tf      # provider config incl. default_tags
      locals.tf         # Computed values
      terraform.tfvars  # Variable values for this environment (auto-loads in this root)
    staging/
    production/
  modules/
    networking/         # VPC, subnets, NAT, route tables, security groups
    database/           # RDS PostgreSQL + PostGIS, parameter groups
    redis/              # ElastiCache Redis, subnet groups
    ecs/                # ECS cluster, services, task definitions
    centrifugo/         # Centrifugo WebSocket service on ECS
    s3/                 # S3 buckets (ActiveStorage, backups, logs)
    cloudfront/         # CloudFront distributions
```

Load-bearing points, restated so you do not have to open the rule files:

- **Each `environments/<env>/` directory is its own Terraform root module.** You `cd` into it and run
  `terraform init && terraform plan` there. It has its own state file and its own backend key.
- **`modules/` are never applied directly.** They have no backend block and no provider block; they
  are consumed by the environment root modules.
- **Terraform workspaces are not used.** Directories are the isolation mechanism.
- **The module inventory above is the complete set for our stack.** A new module needs a new
  infrastructure concern, not a new grouping of existing ones.

## Decision: which file does this block go in?

The environment root module always has the same file set. Splitting by file type — rather than
piling everything into `main.tf` — is what makes environments diffable against each other in review.
This layout matches the canonical tree in `rules/state-workspace-isolation.md`.

| File | Owns | Never contains |
|------|------|----------------|
| `backend.tf` | the `backend "s3"` block — this environment's state `key` | anything else |
| `versions.tf` | `terraform {}`: `required_version`, `required_providers` | the backend block, resources |
| `providers.tf` | `provider` config, incl. `default_tags` (see `rules/resource-required-tags.md`) | resources |
| `main.tf` | `module` calls only — the wiring of child modules | raw `resource` blocks, provider config |
| `variables.tf` | `variable` declarations (type, description, validation) | values |
| `terraform.tfvars` | the values for those variables | secrets, credentials |
| `locals.tf` | `locals {}` — computed values | anything a consumer needs (that is an output) |
| `outputs.tf` | `output` blocks consumed by other systems or humans | intermediate values |

The most common mistake is putting `resource` blocks directly in an environment's `main.tf`. If a
resource does not belong to any existing module, that is a signal to create a module — not to inline
it into the environment.

### `backend.tf` — the one file people get wrong

The backend lives in its own file, separate from the version pins, because the `key` is the only
line that differs between environments — isolating it makes that diff obvious in review:

```hcl
# terraform/environments/production/backend.tf
terraform {
  backend "s3" {
    bucket         = "myproject-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    kms_key_id     = "alias/terraform-state"
    dynamodb_table = "myproject-terraform-locks"
  }
}
```

```hcl
# terraform/environments/production/versions.tf — pins only, no backend
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
  }
}
```

Notes that are easy to miss:

- **One bucket for all environments; the `key` is what separates them.** Do not create a state
  bucket per environment. `key = "<env>/terraform.tfstate"` is the isolation boundary.
- **`kms_key_id` with a KMS alias**, not just `encrypt = true`. Plain `encrypt = true` gets you SSE-S3;
  our compliance baseline requires a customer-managed key. The alias (rather than a key ARN) keeps
  the block identical across accounts.
- **One DynamoDB lock table for all environments.** Each state file takes its own lock entry keyed by
  the S3 path.
- **The bucket and lock table cannot be created by the config that uses them.** They live in
  `terraform/global/state-infra/` — see `rules/state-remote-backend.md` for the bootstrap.

## Decision: separate root modules per environment, or one root with per-env tfvars?

Both patterns appear in the wild, and `rules/var-tfvars-per-environment.md` shows the single-root
variant (`terraform plan -var-file=environments/dev/dev.tfvars`). **For our stack, use separate root
modules** — the tree at the top of this file.

Use separate root modules (default) when:

- Environments differ structurally, not just in sizing — e.g. dev skips CloudFront and WAF entirely,
  production runs one NAT gateway per AZ and dev runs one total.
- Environments need to move independently — production pinned to an older provider while dev tests
  an upgrade.
- Blast radius matters. A separate root module means `terraform apply` in `dev/` physically cannot
  touch production state.

The single-root + `-var-file` variant is acceptable only for small stacks where every environment is
the same shape and differs purely by numbers. Our stack is not that. When you inherit a repo using
the single-root pattern, the migration is mechanical: create the env directories, move the backend
into each `backend.tf`, and use `moved {}` blocks (see `rules/state-move-not-destroy.md`) so nothing
is destroyed.

**Where `terraform.tfvars` is safe, and where it is not** — the auto-load behaviour cuts both ways:

- **Separate root modules (our default): use `terraform.tfvars`.** Each environment directory *is*
  its own root, so the auto-loaded file is by construction that environment's values. You cannot
  load dev values into a production apply, because you are running in a different directory against
  a different state. This is the layout `rules/state-workspace-isolation.md` shows.
- **Single-root variant: never use `terraform.tfvars` or `*.auto.tfvars`.** There, one root serves
  every environment, so an auto-loading file silently defeats the `-var-file` isolation you are
  relying on. Name them `dev.tfvars` / `production.tfvars` and pass `-var-file` explicitly.

## Decision: where do tags come from?

**Provider-level `default_tags`** — declared once in the environment's provider block. Every
resource inherits them automatically, with no per-resource `merge()` and no map threaded through
module variables. `rules/resource-required-tags.md` is the authoritative rule; read it for the
mandatory tag set and the enforcement story (AWS Config / SCPs).

```hcl
# terraform/environments/production/providers.tf
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      project    = var.project_name
      environment = var.environment
      team       = var.team
      managed-by = "terraform"
    }
  }
}
```

Per-resource `tags` **merge with** and can override the defaults — add only service-specific tags
(e.g. `backup = "critical"` on RDS/S3) at the resource level.

> Do **not** hand-roll a `locals.common_tags` map and merge it at every resource, and do not pass a
> tag map into modules as a variable. That is the pattern `resource-required-tags.md` explicitly
> argues against: it repeats itself, drifts per module, and loses the guarantee that *every*
> resource is tagged.
