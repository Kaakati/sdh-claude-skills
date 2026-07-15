---
name: log-search
description: Read and query production logs — CloudWatch Logs Insights and `aws logs tail` on AWS, Cloud Logging (LQL) and `gcloud logging read` on GCP. Use when investigating a production error, tracing one request across services, finding what changed after a deploy, tailing a service live, counting error rates, or when someone asks "read the logs", "search CloudWatch", "why is prod 500ing", "find this request id", "grep the logs", "Logs Insights query", or "gcloud logging read".
model: sonnet
---

# Log Search — asking production a question

Reading logs is not grepping. Both clouds bill you for **how much data your question scans**, and
both make it trivially easy to scan a week of every service to answer something a two-minute
window would have answered. The skill is in narrowing.

Emitting good logs is a different job, owned by `std-monitoring` — structured JSON, a
`request_id` on every line. **This file assumes those exist.** If the logs are unstructured
strings, no query language saves you: fix the emitting first, because `filter @message like /…/`
on free text is a full scan every time.

## The first rule: time range before anything else

AWS says it plainly:

> *"To avoid incurring excessive charges by running large queries… Select only the necessary log
> groups for each query. **Always specify the narrowest possible time range** for your queries."*

Cost is the visible half. The real cost is that a 7-day query over 12 log groups takes minutes,
returns thousands of lines, and buries the answer. **Start at 15 minutes around the event and
widen only when it comes back empty.** An investigation is a sequence of narrow questions, not
one big one.

## Decision: which tool for this question?

| The question | AWS | GCP |
|---|---|---|
| "What is it doing *right now*?" | `aws logs tail --follow` | `gcloud beta logging tail` |
| "What happened at 14:32?" | Logs Insights, 15-min window | `gcloud logging read` with a timestamp range |
| "Trace this one request" | Insights: `filter request_id = "…"` | `jsonPayload.request_id="…"` |
| "How often, and is it getting worse?" | Insights: `stats count() by bin(5m)` | Log-based metric → Cloud Monitoring |
| "Did the deploy cause it?" | Insights `diff`, or count before/after | Compare two `read` windows |
| "Alert me next time" | Metric filter → alarm | Log-based metric → alert policy |

**If you are asking the same question a third time, it is a metric, not a query.** A recurring
Insights query is a dashboard you have not built yet — and it re-scans, and it costs, every time
someone wonders.

## The four questions that answer almost every incident

1. **Is it erroring?** — count errors in the last 15 minutes, bucketed. A rate tells you
   *severity*; a single line does not.
2. **Since when?** — bucket by time and find the edge. The edge usually matches a deploy.
3. **Which requests?** — take one `request_id` from a failure and pull *every* line for it,
   across services. This is the step that finds the cause.
4. **What is different about them?** — group the failures by endpoint, user, region, version.
   The dimension that is not uniform is the lead.

Doing (3) requires a `request_id` propagated across services. When it is missing, that is the
finding — see `std-monitoring`.

## Never paste secrets into a query, or results into a ticket

Query results are logs, and logs contain what the app logged. Before pasting output anywhere:
tokens, emails, and card numbers are the things most likely to be in the line you are about to
paste into a public issue. Sanitize, or link to the query instead of its output.

If the logs contain secrets, that is an emitting bug — the fix is at the source, not in the
query. CloudWatch data-protection policies mask on the way in; `unmask` in a query is an audited
action, and needing it routinely means the masking is doing your redaction *after* the leak.

## Deep guides (read on demand, do not preload)

- CloudWatch: the Insights query language (`fields`/`filter`/`stats`/`parse`/`sort`/`limit`),
  discovered `@`-fields, JSON dot notation, `bin()` histograms, `aws logs tail --follow`, the
  `start-query` → `get-query-results` CLI dance, and the cost discipline
  → `references/cloudwatch-insights.md`
- GCP: the Logging Query Language, `gcloud logging read` with `--freshness`/`--format`,
  `resource.type`, `severity>=ERROR`, `jsonPayload` fields, log-based metrics, and sinks for
  retention → `references/gcp-cloud-logging.md`

Related, owned elsewhere: what to log and the `request_id` that makes tracing possible →
`../std-monitoring`; running an actual incident → `../incident-response`.
