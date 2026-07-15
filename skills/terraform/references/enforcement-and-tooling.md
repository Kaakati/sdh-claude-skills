# Terraform Enforcement and Tooling

What runs automatically against your `.tf` files, what it blocks, and what it cannot catch.

Read this when a hook rejects an edit, when a `terraform apply` is refused, when your file is
reformatted under you, or when you are deciding how much to rely on automation versus review.

## Decision: what checks my Terraform, and when?

Four separate mechanisms fire at different moments. None of them replace the others.

| Mechanism | Fires | Enforces |
|-----------|-------|----------|
| `std-terraform-conventions` skill | Automatically on any `terraform/**/*.tf` edit | HCL file structure, provider constraints, resource naming, required tags, security minimums |
| `terraform-checker.py` (PostToolUse hook) | After a `.tf` file is written | Hardcoded secrets, snake_case naming, required tags, backend config, provider versions |
| `auto-format.py` (PostToolUse hook) | After a `.tf` file is saved | Runs `terraform fmt` |
| `deployment-gate.py` (PreToolUse hook) | Before `terraform apply` runs | Blocks the apply until explicitly confirmed |

The ordering matters in practice: the conventions skill is loaded *while you write*, the checker runs
*after* you write, and the deployment gate is the last line before infrastructure actually changes.
A change that passes the first three can still be stopped at the gate.

## Decision: a hook rejected my edit — now what?

Fix the code, not the hook. The checks are duplicative of the rule files on purpose — the rule tells
you the reasoning, the hook makes the failure unmissable. Map the complaint back to its rule:

| Hook complaint | Rule file with the reasoning and the fix |
|----------------|------------------------------------------|
| Hardcoded secret | `rules/sec-no-hardcoded-secrets.md` |
| Resource name not snake_case / wrong pattern | `rules/resource-naming-convention.md` |
| Missing required tags | `rules/resource-required-tags.md` |
| Missing or malformed backend config | `rules/state-remote-backend.md` |
| Unpinned provider version | `rules/sec-provider-version-constraint.md` |

Do not work around a hook by splitting a change across files or renaming to dodge a pattern match. If
a check is genuinely wrong for a case, that is a change to the hook, in its own PR, with the
justification written down.

## Decision: `terraform apply` was gated — should I confirm?

The gate is a deliberate stop, not a formality. Before confirming, verify:

1. **You ran `terraform plan` and read it.** Not "it exited 0" — read the resource list.
2. **No stateful resource shows `destroy` or `replace`.** RDS instances, ElastiCache clusters, and S3
   buckets with data must never be destroyed by a refactor. A destroy on one of these almost always
   means a missing `moved {}` block (`rules/state-move-not-destroy.md`) or a missing import
   (`rules/state-import-before-adopt.md`) — not a real intent to delete.
3. **You are in the right directory.** Each environment is its own root module. The gate cannot tell
   you that you are in `production/` when you meant `dev/`.
4. **The lock is yours.** If a lock error appears, someone else is applying. Wait — do not
   `force-unlock`, and never pass `-lock=false`.

## Decision: what does none of this catch?

The automation is a floor, not a ceiling. It is pattern matching over HCL text; it has no model of
your intent or of AWS's behavior. It cannot catch:

- **Semantically wrong values that are syntactically fine.** A `/16` CIDR that overlaps another
  environment's VPC passes every check and breaks peering later.
- **IAM policies that are scoped but still too broad.** `Resource` on a specific bucket ARN passes the
  wildcard check; whether that role should touch that bucket at all is a review question.
- **Cost.** Nothing here will tell you a `db.r6g.xlarge` in dev is wrong.
- **Missing resources.** A hook can only inspect what you wrote. A missing
  `aws_s3_bucket_public_access_block` is invisible to it.
- **Drift.** Checks run against your config, never against what is actually deployed. Only
  `terraform plan` sees reality.

Which is why infrastructure PRs still get human review, and why the plan output — not the hook
output — is the artifact that matters in that review.
