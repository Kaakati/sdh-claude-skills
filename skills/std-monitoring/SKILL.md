---
name: std-monitoring
description: Monitoring/observability standards — structured logs with request_id, no sensitive data, health checks, CloudWatch alarms, Sentry. Use when adding logging, jobs, or controllers.
paths:
  - "**/app/jobs/**/*.rb"
  - "**/app/controllers/**/*.rb"
  - "**/config/initializers/**/*.rb"
  - "**/*.tf"
  - "**/docker-compose*.yml"
  - "**/.github/workflows/**"
---

# Monitoring & Observability Standards

**Enforcement**: code-reviewer skill (Step 8: Stack-Specific Checks), devops-engineer agent (Step 8: Configure Monitoring), deploy skill (Step 7: Monitoring).

## Structured Logging
- Use lograge gem for Rails to produce structured JSON logs
- Every log entry must include: timestamp, level, request_id, user_id, action
- Never log sensitive data (passwords, tokens, PII)
- Use log levels consistently: DEBUG for dev, INFO for requests, WARN for recoverable issues, ERROR for failures

## Request Tracing
- **You do not build this — Rails already does.** `ActionDispatch::RequestId` is in the default
  middleware stack: it adopts an incoming `X-Request-Id` (typically set by the load balancer, so
  your logs join to the LB's for free) or generates a uuid, exposes it as `request.request_id`,
  and returns it to the client in the `X-Request-Id` header.
- **`config.log_tags = [:request_id]`** — one line, and every log line in the request carries it.
- Include request_id in all log entries, error reports, and API responses.
- **The trace breaks at the async boundary.** A Sidekiq job runs in another process with no
  request: `request_id` is `nil` there unless you propagate it through client/server middleware.
  That is exactly where you need it — the async work is what fails at 3am.
- Centrifugo messages must carry request_id for end-to-end tracing.
- The id is **outside input** (Rails sanitizes it to 255 alphanumeric-and-dash chars because a
  client can send it) — never interpolate it into SQL or a shell command.
- Deep guide → `references/request-tracing.md`

## Health Check Endpoints
- `/health` — application liveness (returns 200 if app process is running)
- `/health/db` — database connectivity (PostgreSQL/PostGIS query check)
- `/health/redis` — Redis connectivity and latency check
- `/health/centrifugo` — Centrifugo WebSocket server availability
- All health checks must respond within 5 seconds or return 503

## Key Metrics
- Request rate (requests/second by endpoint)
- Error rate (4xx and 5xx by endpoint)
- Latency percentiles: p50, p95, p99
- Sidekiq: queue depth, job execution time, retry count, dead jobs
- Database: active connections, query duration, slow queries (>100ms)
- Redis: memory usage, hit rate, connection count

## CloudWatch Alarms
- ECS task health: alarm if running tasks < desired tasks for >2 minutes
- RDS connections: alarm if connections > 80% of max
- ElastiCache memory: alarm if memory usage > 75%
- Error rate spikes: alarm if 5xx rate > 1% for >5 minutes
- Sidekiq dead jobs: alarm if dead job count increases

## Centrifugo Monitoring
- Track active WebSocket connection count
- Monitor message throughput (messages/second)
- Track channel count and subscriptions per channel
- Alert on connection drops or message delivery failures
- Monitor Centrifugo process memory and CPU usage

## Error Tracking
- Sentry for both Rails backend and React Native mobile
- Configure source maps for React Native for readable stack traces
- Set up release tracking to correlate errors with deployments
- Tag errors with: environment, user_id, device_info (mobile), request_id

## Grafana Dashboards
- Overview dashboard: request rate, error rate, latency, active users
- Infrastructure dashboard: ECS, RDS, ElastiCache, Centrifugo metrics
- Background jobs dashboard: Sidekiq queues, execution times, failures
- Mobile dashboard: crash-free rate, API latency from client, active sessions

## Deep guides (read on demand, do not preload)

- Where `request_id` comes from (`ActionDispatch::RequestId`), `config.log_tags`, `Current`
  attributes for services, **propagating the id into Sidekiq** (the boundary where the trace
  breaks), returning it to clients, and proving it end to end with one `curl`
  → `references/request-tracing.md`

Related, owned elsewhere — do not duplicate: *querying* the logs this produces (Logs Insights,
`gcloud logging read`) → `../log-search`; the API error envelope the id belongs in →
`../std-api-design/references/errors-rails.md`; what must never be logged → `../std-security`.
