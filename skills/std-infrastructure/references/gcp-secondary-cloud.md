# GCP — the Secondary Cloud

Read this **only** when a task genuinely requires a GCP service. An AWS task never needs this file.

Load-bearing rules restated (they hold even if you read nothing else):
- **AWS is the primary cloud.** GCP is reached for only when a specific service requires it (Maps, ML/Vertex, BigQuery). Do not split the primary stack across clouds.
- **Prefer Workload Identity Federation over a service-account key.** Google: *"Workload Identity Federation is recommended over Service Account Keys as it obviates the need to export a long-lived credential."* A credential that does not exist cannot leak, expire, or be rotated late.
- **When a key is genuinely unavoidable, it lives in AWS Secrets Manager** — one source of truth for credentials. Do not introduce GCP Secret Manager for an AWS-primary system.
- **Never hardcode a credential in `.tf` or `.tfvars`** — Terraform state stores variable values in plaintext.
- **Every resource is tagged/labelled** with `project`, `environment`, `team`, `managed-by = "terraform"`.

---

## Decision: how does this workload authenticate to GCP?

| The caller | Use | Key on disk? |
|---|---|---|
| **GitHub Actions** | Workload Identity Federation via `google-github-actions/auth` | **None** |
| Rails on ECS, calling a GCP API | WIF with AWS as the identity provider | **None** |
| A local developer | `gcloud auth application-default login` | None (their own identity) |
| Something that genuinely cannot federate | Service-account key → **AWS Secrets Manager** | Yes — and it is now a password you own forever |

Google on the last row: *"Service Account Key JSON credentials are long-lived credentials and
must be treated like a password."* Reach for it last, and write down why.

## Bad — CI downloads a key

```yaml
# .github/workflows/deploy.yml  ❌
- uses: google-github-actions/auth@v3
  with:
    # A permanent credential, pasted into a CI secret. It does not expire, so it survives
    # the person who created it, the project it was for, and the repo being forked. Rotating
    # it means finding every consumer. Leaking it means a Google-side incident.
    credentials_json: ${{ secrets.GCP_SA_KEY }}
```

Nothing about this fails. It is simply a permanent secret you now have to defend forever, in
exchange for saving twenty minutes once.

## Good — CI federates, holds nothing

```yaml
# .github/workflows/deploy.yml  ✅
permissions:
  contents: read
  id-token: write        # ONLY on the job that authenticates — see references/github-actions.md

steps:
  - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683   # v4.2.2
  - uses: google-github-actions/auth@v3
    with:
      project_id: acme-prod
      # GitHub mints a short-lived OIDC token; GCP trades it for a short-lived access
      # token. Nothing long-lived exists at any point — there is no secret to rotate.
      workload_identity_provider: projects/123456789/locations/global/workloadIdentityPools/github/providers/github
      service_account: deployer@acme-prod.iam.gserviceaccount.com
```

The trust is declared once, in Terraform, and **scoped to your repo** — this is the line that
matters:

```hcl
# terraform/environments/production/gcp-oidc.tf  ✅
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  # THE security boundary. Without a condition, ANY GitHub repository on the internet can
  # exchange a token for your service account — this is the documented misconfiguration
  # that turns "keyless" into "world-writable".
  attribute_condition = "assertion.repository == 'Kaakati/acme-app'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member = join("", [
    "principalSet://iam.googleapis.com/",
    google_iam_workload_identity_pool.github.name,
    "/attribute.repository/Kaakati/acme-app",
  ])
}
```

> **`attribute_condition` is not optional.** A provider that trusts
> `token.actions.githubusercontent.com` with no repository condition trusts *every* GitHub
> Actions run in existence. The keyless setup is only safer than a key if this line is right.

## When the key is unavoidable

Some workloads genuinely cannot federate. Then the existing rule stands — the key lives in AWS
Secrets Manager, never in Terraform state, never in the repo:

```hcl
# terraform/environments/production/gcp.tf
resource "google_service_account" "maps_geocoder" {
  account_id   = "maps-geocoder-prod"
  display_name = "Geocoding calls from the Rails app"
}

resource "google_project_iam_member" "maps_geocoder" {
  project = var.gcp_project_id
  role    = "roles/serviceusage.serviceUsageConsumer"   # narrow, not roles/editor
  member  = "serviceAccount:${google_service_account.maps_geocoder.email}"
}

# Terraform creates the SECRET, never its value: `google_service_account_key` would put the
# private key in state, in plaintext, forever. The value is written out of band:
#   aws secretsmanager put-secret-value --secret-id production/gcp/maps-geocoder \
#     --secret-string file://key.json
resource "aws_secretsmanager_secret" "gcp_maps_key" {
  name = "production/gcp/maps-geocoder"
  tags = local.common_tags
}
```

Never `resource "google_service_account_key"` in a root you care about: the private key lands in
state. State is a copy of every secret it touches.

## Decision: which GCP service, and where does it run?

| Need | Service | Note |
|---|---|---|
| Geocoding / maps | Maps Platform | The common case; a narrow API key or SA, restricted by referrer/IP |
| A container GCP-side | Cloud Run | Only if it must be GCP-side; ECS Fargate stays the default |
| Container images GCP-side | Artifact Registry | Do not mirror ECR for its own sake |
| Analytics warehouse | BigQuery | Genuinely worth crossing clouds for |
| ML inference | Vertex AI | Genuinely worth crossing clouds for |

**The bar for crossing clouds is a capability AWS does not have** — not preference. Every GCP
resource adds an identity boundary, a second bill, a second set of IAM semantics, and a second
place to look during an incident. `terraform-mechanics.md` covers the GCS backend for a
GCP-only stack; the AWS-primary rule means most roots never need one.

## IAM, briefly, because it is not AWS IAM

- Roles are **additive**; there is no deny by default to lean on the way an AWS policy `Deny`
  works. Grant narrowly — `roles/editor` is not a starting point, it is a finding.
- Grant at the **narrowest resource**, not the project, when the API supports it.
- Service accounts are both an identity *and* a resource — `roles/iam.workloadIdentityUser` on
  the service account is what lets the federated principal impersonate it.
