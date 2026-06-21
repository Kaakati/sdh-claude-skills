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
- Propagate `X-Request-ID` header across all service boundaries
- Include request_id in all log entries, error reports, and API responses
- Centrifugo messages must carry request_id for end-to-end tracing

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
