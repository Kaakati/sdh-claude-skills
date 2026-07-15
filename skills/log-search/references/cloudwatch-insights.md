# CloudWatch — Logs Insights and `aws logs tail`

Load-bearing rules restated (hold even if you read nothing else):

1. **Narrow the time range and the log groups first.** You are billed on data scanned, and a
   wide query buries the answer as surely as it costs.
2. **`filter` on a discovered field, not on `@message`.** Free-text matching scans everything.
3. **Count before you read.** A rate tells you severity; one line tells you almost nothing.

---

## Tail: what is it doing right now

```bash
# The fastest way to see a live service. --since is not optional in spirit: without it you
# get a firehose from the beginning of the stream's retention.
aws logs tail /ecs/acme-api --follow --since 10m --format short

# Narrow live tailing to one thing
aws logs tail /ecs/acme-api --follow --since 5m --filter-pattern '"ERROR"'
```

`tail` is for *now*. For anything historical, it is the wrong tool — use Insights, which can
aggregate.

## The query language, in the order you actually use it

Commands are piped with `|`. The ones that carry the work:

| Command | Does |
|---|---|
| `fields` | Choose/compute columns |
| `filter` | Keep matching events — **put this as early as possible** |
| `stats` | Aggregate (`count()`, `avg()`, `pct()`), optionally `by` a dimension |
| `sort` | `asc` / `desc` |
| `limit` | Cap results; `limit any` stops scanning once enough are found |
| `parse` | Extract fields out of a string (glob or regex) |
| `dedup` | Drop duplicate rows by field |

CloudWatch *"automatically discovers fields for different log types and generates fields that
start with the `@` character"* — `@timestamp`, `@message`, `@logStream`, `@log`. If you log
**JSON**, its keys become fields too, and nested keys use dot notation. That is the whole payoff
of structured logging.

### Bad — the query that scans everything and answers nothing

```
fields @timestamp, @message
| sort @timestamp desc
| limit 1000
```

Run over 7 days and 6 log groups, this scans everything you have, costs accordingly, and hands
you a thousand lines to read by eye. It is `cat` with a bill.

```
fields @timestamp, @message
| filter @message like /error/          # ❌ free-text scan; also matches "no errors", "error_rate: 0"
```

### Good — filter early, on a real field

```
# Is it erroring, and since when? Answers questions 1 and 2 in one query.
filter level = "error"
| stats count() as errors by bin(5m)
| sort bin(5m) asc
```

`bin(5m)` buckets by time — the edge where the count jumps is your incident's start, and it
usually lines up with a deploy.

```
# What is different about the failures? The non-uniform dimension is the lead.
filter level = "error"
| stats count() as n by http.path, http.status
| sort n desc
| limit 20
```

```
# Trace ONE request across every service. This is the step that finds causes.
# Query all the log groups at once in the console, or pass several --log-group-names in the CLI.
filter ctx.request_id = "01HX7Z9K2M4N6P8Q"
| fields @timestamp, @log, level, msg
| sort @timestamp asc
```

Note `@log` in the fields: when querying several groups, it tells you *which service* each line
came from, which is exactly what you need and exactly what people forget to select.

```
# p95 latency by endpoint — logs answering a metrics question, acceptable once
filter ispresent(duration_ms)
| stats pct(duration_ms, 95) as p95, count() as n by http.path
| sort p95 desc
| limit 20
```

If you run that weekly, stop: make it a metric filter and an alarm. A query re-scans and
re-bills every time somebody wonders.

## `parse` — when the logs are not JSON (yet)

```
# Extract from an unstructured line. Works, and is a workaround, not a destination.
parse @message "duration=* status=*" as duration, status
| filter status >= 500
| stats count() by bin(1m)
```

`parse` runs on **every scanned event** — it does not reduce what you scan. It rescues a
badly-logged service during an incident; the fix is structured logs (`std-monitoring`), because
`parse` breaks the moment someone reformats the string.

## From the CLI: `start-query` → `get-query-results`

Insights is asynchronous. The CLI does not hide this, and the two-step trips people up:

```bash
QUERY_ID=$(aws logs start-query \
  --log-group-names /ecs/acme-api /ecs/acme-worker \
  --start-time "$(date -u -d '15 minutes ago' +%s)" \
  --end-time   "$(date -u +%s)" \
  --query-string 'filter level = "error" | stats count() by bin(1m)' \
  --query queryId --output text)

# Poll: status goes Scheduled -> Running -> Complete. Reading too early returns an EMPTY
# result set with no error — the classic "the query found nothing" that found nothing because
# it had not run yet.
until [ "$(aws logs get-query-results --query-id "$QUERY_ID" --query status --output text)" = "Complete" ]; do
  sleep 2
done
aws logs get-query-results --query-id "$QUERY_ID" --output table
```

Times are **epoch seconds**. Passing an ISO string gets you a validation error at best and a
wrong window at worst.

## Cost and speed discipline

AWS's own list, worth restating because every item is a real bill someone paid:

- **Select only the necessary log groups.** Six groups when one would do is six times the scan.
- **Always specify the narrowest possible time range.** This is the single biggest lever.
- **Cancel queries** you abandon in the console — closing the tab does not stop them.
- **Dashboard widgets re-run on every refresh.** A 30-second auto-refresh on an Insights widget
  is a query every 30 seconds, forever, whether anyone is looking or not.
- `limit any` stops scanning early once enough results are found — use it when you want
  *examples*, not *counts*.

## Retention is a decision, not a default

A log group with no retention set keeps logs **forever**, and you pay storage forever. Set it in
Terraform where the group is created, not by clicking:

```hcl
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/acme-api"
  retention_in_days = 30      # explicit. `null` means "never expire" — a bill with no end.
  tags              = local.common_tags
}
```

Pick from the question you will ask: 30 days answers incidents; compliance answers audits and
belongs in S3 via a subscription filter, not in CloudWatch at CloudWatch prices.

## When a query is really an alarm

The moment you would like to *know* rather than *look*, convert it:

```hcl
resource "aws_cloudwatch_log_metric_filter" "api_errors" {
  name           = "api-errors"
  log_group_name = aws_cloudwatch_log_group.api.name
  pattern        = "{ $.level = \"error\" }"   # JSON pattern — needs structured logs

  metric_transformation {
    name      = "ApiErrors"
    namespace = "Acme/Api"
    value     = "1"
  }
}
```

Then alarm on the metric (`std-monitoring` owns alarm design). Metric filters evaluate on
ingest — they cost nothing per look, and they notice at 3am when nobody is querying.
