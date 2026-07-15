# GCP — the Secondary Cloud

Read this **only** when a task genuinely requires a GCP service. An AWS task never needs this file.

Load-bearing rules restated (they hold even if you read nothing else):
- **AWS is the primary cloud.** GCP is reached for only when a specific service requires it (Maps, ML/Vertex, BigQuery). Do not split the primary stack across clouds.
- **GCP credentials are stored in AWS Secrets Manager**, so credentials have a single source of truth. Do not introduce GCP Secret Manager for an AWS-primary system.
- **Never hardcode a credential in `.tf` or `.tfvars`** — Terraform state stores variable values in plaintext.
- **Every resource is tagged/labelled** with `project`, `environment`, `team`, `managed-by = "terraform"`.

---

## Decision: I need something from GCP

- Authenticate with a **service account holding the minimum roles** for the one job. No `roles/editor`.
- **GCP credentials are stored in AWS Secrets Manager**, so credentials have a single source of truth. Do not introduce GCP Secret Manager for an AWS-primary system.
- GCP-only stacks use a **GCS backend with state locking**, mirroring the S3/DynamoDB arrangement described in `terraform-mechanics.md`.

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

# The generated key is placed in AWS Secrets Manager out of band:
#   aws secretsmanager put-secret-value --secret-id production/gcp/maps-geocoder \
#     --secret-string file://key.json
resource "aws_secretsmanager_secret" "gcp_maps_key" {
  name = "production/gcp/maps-geocoder"
  tags = local.common_tags
}
```
