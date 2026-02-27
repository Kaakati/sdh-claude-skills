---
name: incident-response
description: Guide incident response for production issues including diagnosis, mitigation, communication, and post-mortem analysis. Use this skill whenever someone reports an outage, performance degradation, production error, or says things like "production is down", "users are reporting errors", "the API is slow", "we have an incident", "something broke in prod", "check the logs for errors", or "we need a post-mortem". Also trigger when someone mentions SEV1/SEV2 classification, incident communication, root cause analysis, or wants to write a post-mortem document.
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash
model: opus
---

# Incident Response

## Severity Classification

| Level | Definition | Response Time | Examples |
|-------|-----------|---------------|---------|
| **SEV1** | Service down, data loss risk | Immediate (< 15 min) | API completely unreachable, database corruption, security breach |
| **SEV2** | Major feature broken, significant user impact | < 30 min | Auth failing, payments broken, real-time (Centrifugo) down |
| **SEV3** | Degraded performance or minor feature broken | < 2 hours | Slow API responses, background jobs backed up, partial outage |
| **SEV4** | Minor issue, workaround exists | Next business day | UI glitch, non-critical job failing, minor data inconsistency |

## Diagnosis Protocol

### Step 1: Triage (First 5 Minutes)
```bash
# Check Rails app health
curl -s https://api.example.com/health | jq .

# Check ECS task status
aws ecs describe-services --cluster production --services rails-app \
  --query 'services[0].{desired: desiredCount, running: runningCount, pending: pendingCount}'

# Check recent deployments (was something just deployed?)
aws ecs describe-services --cluster production --services rails-app \
  --query 'services[0].deployments[*].{status: status, created: createdAt, running: runningCount}'

# Check error spike in CloudWatch
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name CPUUtilization --period 300 --statistics Average \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S)
```

### Step 2: Identify the Failing Component

#### Rails Application (ECS Fargate)
```bash
# Check application logs (last 30 min)
aws logs filter-log-events --log-group-name /ecs/rails-app \
  --start-time $(date -u -d '30 min ago' +%s)000 \
  --filter-pattern "ERROR"

# Check for OOM kills
aws logs filter-log-events --log-group-name /ecs/rails-app \
  --filter-pattern "OutOfMemoryError"

# Check Puma worker status
curl -s https://api.example.com/health/detailed | jq .
```

#### PostgreSQL / PostGIS (RDS)
```bash
# Check connections
psql -c "SELECT count(*) as total, state FROM pg_stat_activity GROUP BY state;"

# Check for locks
psql -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;"

# Check long-running queries
psql -c "SELECT pid, now() - query_start AS duration, query FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '30 seconds';"

# Check replication lag (if read replicas)
psql -c "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"

# Check PostGIS-specific: spatial query performance
psql -c "SELECT relname, seq_scan, idx_scan FROM pg_stat_user_tables
WHERE relname IN ('locations', 'geofences') ORDER BY seq_scan DESC;"
```

#### Redis / Sidekiq
```bash
# Check Redis memory
redis-cli INFO memory | grep used_memory_human

# Check Redis connection count
redis-cli INFO clients | grep connected_clients

# Check Sidekiq queues
# Via Rails console or Sidekiq API
bundle exec rails runner "Sidekiq::Queue.all.each { |q| puts \"#{q.name}: #{q.size} jobs, latency: #{q.latency.round(1)}s\" }"

# Check failed jobs
bundle exec rails runner "puts \"Retry: #{Sidekiq::RetrySet.new.size}, Dead: #{Sidekiq::DeadSet.new.size}\""
```

#### Centrifugo (Real-time)
```bash
# Check Centrifugo health
curl -s http://centrifugo:8000/health | jq .

# Check connection count
curl -s -H "Authorization: apikey $CENTRIFUGO_API_KEY" \
  http://centrifugo:8000/api/info | jq '.result.nodes[0].num_clients'

# Check channel count
curl -s -H "Authorization: apikey $CENTRIFUGO_API_KEY" \
  http://centrifugo:8000/api/info | jq '.result.nodes[0].num_channels'
```

### Step 3: Mitigation

#### If recent deployment caused it:
```bash
# Immediate rollback to previous ECS task definition
aws ecs update-service --cluster production --service rails-app \
  --task-definition rails-app:PREVIOUS_REVISION

# Rollback database migration if needed
bundle exec rails db:rollback STEP=1 RAILS_ENV=production
```

#### If database-related:
```bash
# Kill long-running queries
psql -c "SELECT pg_terminate_backend(PID);" -- Replace PID

# Scale up connections (if pool exhausted)
# Update RDS parameter group or application pool settings

# Clear specific cache if stale data
bundle exec rails runner "Rails.cache.delete_matched('problematic_key_pattern*')"
```

#### If Redis/Sidekiq-related:
```bash
# Flush stuck queue (CAUTION: loses jobs)
# bundle exec rails runner "Sidekiq::Queue.new('queue_name').clear"

# Restart Sidekiq workers
aws ecs update-service --cluster production --service sidekiq --force-new-deployment
```

## Communication Templates

### SEV1/SEV2 — Initial (within 15 min)
```
INCIDENT: [Brief description]
SEVERITY: SEV[X]
STATUS: Investigating
IMPACT: [What users are experiencing]
STARTED: [Time]
TEAM: [Who is responding]
NEXT UPDATE: [Time + 30 min]
```

### Update (every 30 min)
```
UPDATE — [Incident title]
STATUS: [Investigating | Identified | Mitigating | Resolved]
CAUSE: [Root cause if known]
ACTION: [What's being done]
ETA: [Expected resolution time]
NEXT UPDATE: [Time]
```

## Post-Mortem Template
After every SEV1/SEV2, within 48 hours:

```markdown
# Post-Mortem: [Incident Title]
**Date**: [Date] | **Duration**: [X hours] | **Severity**: SEV[X]

## Summary
[1-2 sentences]

## Timeline
| Time | Event |
|------|-------|
| HH:MM | [What happened] |

## Root Cause
[Technical explanation]

## Impact
- Users affected: [count/percentage]
- Revenue impact: [if applicable]
- Data impact: [any data loss/corruption]

## Resolution
[What fixed it]

## Action Items
| # | Action | Owner | Due Date | Status |
|---|--------|-------|----------|--------|

## Lessons Learned
- What went well
- What went wrong
- Where we got lucky
```

## Operational Procedures

### Backup & Recovery

#### Backup Strategy
- **RDS (PostgreSQL)**: Automated daily snapshots with 7-day retention. Point-in-time recovery enabled.
- **Redis (ElastiCache)**: Daily snapshots. Recovery from snapshot restores cache state.
- **S3 (ActiveStorage)**: Versioning enabled on production buckets. Cross-region replication for critical assets.
- **Application Config**: All in Git (Terraform state in S3 with versioning + DynamoDB lock).

#### Recovery Procedures
```bash
# Restore RDS from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier rails-app-restored \
  --db-snapshot-identifier rds:rails-app-YYYY-MM-DD-HH-MM

# Point-in-time recovery (restore to specific moment)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier rails-app \
  --target-db-instance-identifier rails-app-pitr \
  --restore-time YYYY-MM-DDTHH:MM:SSZ

# Restore Redis from snapshot
aws elasticache create-replication-group \
  --replication-group-id rails-cache-restored \
  --snapshot-name daily-snapshot-YYYY-MM-DD
```

### Capacity Planning

#### Key Metrics to Monitor for Scaling Decisions
| Resource | Warning Threshold | Critical Threshold | Action |
|----------|------------------|-------------------|--------|
| ECS CPU | > 60% sustained 15 min | > 80% sustained 5 min | Scale out ECS tasks |
| ECS Memory | > 70% sustained | > 85% sustained | Scale out or increase task size |
| RDS CPU | > 70% sustained | > 85% sustained | Scale up instance class |
| RDS Connections | > 70% of max | > 85% of max | Increase max connections or add read replica |
| ElastiCache Memory | > 65% | > 80% | Scale up node type or add shards |
| Sidekiq Queue Depth | > 1000 jobs for 10 min | > 5000 jobs | Add Sidekiq workers |

#### Quarterly Capacity Review
1. Review 90-day trends for all resources above.
2. Project growth based on user/traffic trajectory.
3. Identify bottlenecks before they become incidents.
4. Plan infrastructure changes with Terraform for next quarter.

### On-Call Management

#### On-Call Rotation
- Primary on-call rotates weekly among senior engineers.
- Secondary (backup) on-call is always assigned.
- Handoff happens Monday 09:00 local time with a brief sync.
- On-call engineer has admin access to AWS console, RDS, ECS, Redis.

#### Escalation Path
| Level | Who | When |
|-------|-----|------|
| L1 | On-call engineer | SEV3/SEV4 — first 30 minutes |
| L2 | Tech lead + on-call | SEV2 or L1 cannot resolve within 30 min |
| L3 | CTO + full team | SEV1 or data loss risk |

#### On-Call Expectations
- Acknowledge alerts within 15 minutes (SEV1/2) or 2 hours (SEV3/4).
- Access to laptop + internet required during on-call rotation.
- Document all actions taken during incidents in the incident channel.
- Handoff unresolved issues to next on-call with full context.

### SLA Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Uptime | 99.9% (8.7h downtime/year) | CloudWatch synthetic canary |
| API Latency (p95) | < 200ms | CloudWatch API Gateway metrics |
| Incident Response | SEV1: < 15 min, SEV2: < 30 min | PagerDuty acknowledgment time |
| Incident Resolution | SEV1: < 4h, SEV2: < 8h | Incident tracker duration |
| Deployment Frequency | >= 1 per week to production | CI/CD pipeline metrics |
| Change Failure Rate | < 5% of deployments cause incidents | Incident correlation |

## Chaos Engineering

Proactively test system resilience by introducing controlled failures. Chaos experiments validate that the system degrades gracefully and recovers automatically.

### Principles
1. **Hypothesis-driven**: Define expected behavior before introducing failure.
2. **Minimize blast radius**: Start in staging, use feature flags to limit scope in production.
3. **Automated rollback**: Every experiment must have automatic abort conditions.
4. **Observe, don't assume**: Monitor metrics during experiments, don't rely on assumptions.

### GameDay Template

```markdown
# GameDay: [Experiment Name]
**Date**: YYYY-MM-DD | **Environment**: staging | **Lead**: [Name]

## Hypothesis
When [failure condition], the system should [expected behavior] within [time].

## Steady State
- API latency p95: [baseline]ms
- Error rate: [baseline]%
- Active users: [baseline]

## Experiment
- **Failure type**: [network | compute | storage | dependency]
- **Target**: [component]
- **Duration**: [X minutes]
- **Blast radius**: [what is affected]

## Abort Conditions
- Error rate exceeds [X]%
- Latency exceeds [X]ms for [Y] minutes
- Any SEV1 alert fires

## Results
- Hypothesis confirmed/denied
- Observations: [what actually happened]
- Action items: [improvements needed]
```

### Fault Injection Patterns

#### Network Failures
```bash
# Simulate network latency (using toxiproxy)
toxiproxy-cli toxic add -t latency -a latency=1000 -a jitter=500 rails_pg

# Simulate connection timeout
toxiproxy-cli toxic add -t timeout -a timeout=5000 rails_redis

# Simulate packet loss (using tc netem on Linux)
tc qdisc add dev eth0 root netem loss 10%
```

#### Compute Failures
```bash
# CPU stress test
stress-ng --cpu 4 --timeout 60s

# Memory pressure
stress-ng --vm 2 --vm-bytes 80% --timeout 60s

# Kill application process (test restart behavior)
kill -9 $(pgrep -f puma)
```

#### Storage Failures
```bash
# Simulate disk full
fallocate -l 95G /tmp/fill_disk  # Fill to 95%

# Simulate slow disk I/O
tc qdisc add dev sda root netem delay 100ms
```

#### Dependency Failures
```bash
# Block external API (via toxiproxy)
toxiproxy-cli toxic add -t timeout -a timeout=0 payment_gateway

# Simulate Centrifugo outage
docker-compose stop centrifugo

# Simulate Redis failure
docker-compose stop redis
# Verify: Does Sidekiq degrade gracefully? Does Rails cache fallback work?

# Simulate PostgreSQL failover
# Trigger RDS failover in staging:
aws rds reboot-db-instance --db-instance-identifier staging-db --force-failover
```

### Resilience Checklist
- [ ] Circuit breakers on external service calls (Faraday middleware)
- [ ] Retry with exponential backoff on transient failures
- [ ] Graceful degradation when Redis is unavailable (cache miss = DB query)
- [ ] Health check endpoint reflects actual component health
- [ ] Sidekiq jobs are idempotent and safe to retry
- [ ] Centrifugo reconnection with backoff in React Native client
- [ ] Database connection pool handles transient connection failures
- [ ] Application starts successfully even if optional dependencies are down

See references/runbooks.md for component-specific runbooks.
