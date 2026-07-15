# GCP — Cloud Logging and the Logging Query Language

Load-bearing rules restated (hold even if you read nothing else):

1. **Constrain `resource.type` and the time range first.** Everything else is a filter on a set
   you should already have made small.
2. **`severity>=ERROR` beats matching text.** Severity is indexed and structured; your message
   string is neither.
3. **`jsonPayload.*` only exists if you logged JSON.** Otherwise you get `textPayload` and are
   back to substring matching.

LQL is not SQL and not Insights QL. It is a **boolean filter expression** — there is no pipe, no
`stats`. Aggregation is a *log-based metric*, not a query.

---

## Read: the command you will actually use

```bash
# Errors from one Cloud Run service in the last hour.
# --freshness is the time range; without it you get the default window and a slow, wide read.
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND resource.labels.service_name="acme-api"
   AND severity>=ERROR' \
  --freshness=1h --limit=50 --format=json
```

```bash
# Trace ONE request across services — the step that finds causes.
gcloud logging read \
  'jsonPayload.request_id="01HX7Z9K2M4N6P8Q"' \
  --freshness=2h --limit=200 \
  --format='table(timestamp, resource.labels.service_name, severity, jsonPayload.msg)' \
  --order=asc
```

`--format` is the difference between reading this and drowning: raw JSON of 200 entries is
unreadable, and `table(...)` gives you the four columns you wanted.

```bash
# Live tail (needs the beta component)
gcloud beta logging tail 'resource.type="cloud_run_revision" AND severity>=WARNING' \
  --format='value(timestamp, jsonPayload.msg)'
```

## The filter language

Boolean expressions over the log entry's fields:

| Field | Is |
|---|---|
| `resource.type` | `cloud_run_revision`, `gce_instance`, `k8s_container`, … — **always set this** |
| `resource.labels.*` | Which service/cluster/instance |
| `severity` | `DEBUG` < `INFO` < `NOTICE` < `WARNING` < `ERROR` < `CRITICAL` < `ALERT` < `EMERGENCY` |
| `logName` | The full stream id — URL-encoded, which surprises everyone |
| `jsonPayload.*` | Your structured fields |
| `textPayload` | The whole line, when you did not log JSON |
| `timestamp` | RFC3339, always UTC |
| `httpRequest.*` | Populated automatically by Cloud Run / LB |

```
# Comparison and substring
severity>=ERROR
jsonPayload.status_code>=500
jsonPayload.msg:"timeout"          # `:` is "has substring" — NOT equals
textPayload=~"timeout|deadline"    # regex; powerful and slow — last resort
timestamp>="2026-07-15T14:00:00Z" AND timestamp<"2026-07-15T14:30:00Z"
```

`:` vs `=` is the one that bites: `jsonPayload.msg:"error"` matches *contains*, while
`jsonPayload.msg="error"` matches the whole value exactly. Reaching for `=` on a message field
and getting nothing back is the usual first confusion.

## Bad — a read that scans the project

```bash
# ❌ no resource.type, no time bound, matching free text across every service in the project
gcloud logging read 'textPayload:"error"' --limit=1000
```

Slow, expensive, and it matches `"no errors"` and `"error_rate=0"` along with your outage.

## Good — narrow, then narrow again

```bash
# ✅ one resource, one service, one severity, one window
gcloud logging read \
  'resource.type="cloud_run_revision"
   AND resource.labels.service_name="acme-api"
   AND severity>=ERROR
   AND timestamp>="2026-07-15T14:00:00Z"
   AND timestamp<"2026-07-15T14:15:00Z"' \
  --format='table(timestamp, jsonPayload.request_id, jsonPayload.msg)' \
  --order=asc --limit=100
```

`logName` when you need a specific stream — note the encoding:

```bash
# The "/" in the log id is percent-encoded as %2F. Copy it from the Console rather than
# hand-writing it; a wrong logName silently returns nothing rather than erroring.
gcloud logging read \
  'logName="projects/acme-prod/logs/run.googleapis.com%2Fstderr"' \
  --freshness=30m --limit=20
```

## There is no `stats` — aggregation is a metric

Insights answers "how many, bucketed by 5 minutes" in the query. LQL cannot. The GCP shape is:
**filter → log-based metric → Cloud Monitoring**, which is better for the recurring question and
worse for the one-off.

```hcl
# terraform — a counter over matching entries
resource "google_logging_metric" "api_errors" {
  name   = "api_errors"
  filter = <<-EOT
    resource.type="cloud_run_revision"
    AND resource.labels.service_name="acme-api"
    AND severity>=ERROR
  EOT

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    # Label the metric so you can group by endpoint later WITHOUT re-reading logs.
    labels { key = "path"; value_type = "STRING" }
  }
  label_extractors = {
    "path" = "EXTRACT(jsonPayload.http.path)"
  }
}
```

For a one-off count, pipe to `jq` rather than building a metric you will delete:

```bash
gcloud logging read '...' --freshness=1h --format=json | jq 'length'
gcloud logging read '...' --freshness=1h --format='value(jsonPayload.http.path)' | sort | uniq -c | sort -rn
```

## Retention, sinks, and the `_Default` bucket

Logs land in the `_Default` bucket with a fixed default retention (30 days). Longer retention or
cheaper storage is a **sink**, not a setting on the query:

```hcl
resource "google_logging_project_sink" "audit_archive" {
  name        = "audit-archive"
  destination = "storage.googleapis.com/${google_storage_bucket.audit_logs.name}"
  filter      = "logName:\"cloudaudit.googleapis.com\""

  # Required, or the sink's writer identity has no permission and the sink silently
  # exports nothing — a compliance gap that looks configured.
  unique_writer_identity = true
}

resource "google_project_iam_member" "sink_writer" {
  project = var.gcp_project_id
  role    = "roles/storage.objectCreator"
  member  = google_logging_project_sink.audit_archive.writer_identity
}
```

That last pair is the classic GCP logging bug: the sink exists, the console shows it, and
nothing arrives — because nobody granted the sink's generated writer identity permission on the
destination. **Verify a sink by reading the destination**, not by looking at the sink.

## Authentication

Do not download a service-account key to read logs. `gcloud auth application-default login`
locally, and Workload Identity Federation from CI — see
`../std-infrastructure/references/gcp-secondary-cloud.md`. Grant `roles/logging.viewer`;
`roles/logging.privateLogViewer` is only for access-transparency/data-access logs and is not the
default answer.
