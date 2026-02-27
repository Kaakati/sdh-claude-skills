# Incident Runbooks

## Runbook: Database Connection Exhaustion

### Symptoms
- API requests timing out
- Errors: `PG::ConnectionBad: could not connect to server`
- `pg_stat_activity` shows max connections reached

### Diagnosis
```bash
# Check current connections vs max
psql -c "SELECT count(*) FROM pg_stat_activity;"
psql -c "SHOW max_connections;"

# Find connection hogs
psql -c "SELECT usename, application_name, count(*)
FROM pg_stat_activity GROUP BY usename, application_name ORDER BY count DESC;"

# Check for idle connections
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

### Resolution
1. Kill idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < now() - interval '10 minutes';`
2. Check Rails connection pool: `config/database.yml` → `pool` setting
3. Check Sidekiq concurrency vs pool size (Sidekiq concurrency should be <= pool size)
4. If persistent, increase RDS instance connection limit

### Prevention
- Set `idle_in_transaction_session_timeout` in PostgreSQL
- Use PgBouncer for connection pooling at scale
- Monitor with CloudWatch `DatabaseConnections` alarm

---

## Runbook: Redis Out of Memory

### Symptoms
- `MISCONF Redis is configured to save RDB snapshots` error
- Sidekiq jobs failing to enqueue
- Cache misses spiking

### Diagnosis
```bash
redis-cli INFO memory
redis-cli INFO keyspace
redis-cli DBSIZE

# Find large keys
redis-cli --bigkeys
```

### Resolution
1. Flush expired keys: `redis-cli --scan --pattern '*' | head -100` (investigate first)
2. If cache-only keys: `Rails.cache.clear` (nuclear option)
3. Scale up ElastiCache node type
4. Check for keys without TTL: review all `Rails.cache.write` calls for missing `expires_in`

### Prevention
- Always set `expires_in` on cache writes
- Configure `maxmemory-policy allkeys-lru` for cache Redis
- Set CloudWatch alarm on `BytesUsedForCache` at 80% threshold

---

## Runbook: Sidekiq Queue Backup

### Symptoms
- Queue sizes growing, latency increasing
- Background job results delayed (emails, notifications, data processing)

### Diagnosis
```bash
# Check queue sizes and latency
bundle exec rails runner "
Sidekiq::Queue.all.each { |q|
  puts \"#{q.name}: #{q.size} jobs, latency: #{q.latency.round(1)}s\"
}
puts \"Retry: #{Sidekiq::RetrySet.new.size}\"
puts \"Scheduled: #{Sidekiq::ScheduledSet.new.size}\"
"

# Check worker utilization
bundle exec rails runner "
ps = Sidekiq::ProcessSet.new
ps.each { |p| puts \"#{p['hostname']}: #{p['busy']}/#{p['concurrency']} busy\" }
"
```

### Resolution
1. Scale up Sidekiq workers: increase ECS desired count
2. If specific queue backed up: add dedicated workers for that queue
3. If a single job type is clogging: check for errors, consider `discard_on` or increased retries
4. If job is slow: profile and optimize the job code

### Prevention
- Set per-queue alerts on size > 1000 or latency > 60s
- Use separate queues for different priority levels
- Monitor Sidekiq dashboard regularly

---

## Runbook: ECS Task Crashes / Restart Loops

### Symptoms
- Service `runningCount` < `desiredCount`
- Tasks in STOPPED state
- Health checks failing

### Diagnosis
```bash
# Check stopped tasks and exit codes
aws ecs describe-tasks --cluster production \
  --tasks $(aws ecs list-tasks --cluster production --service-name rails-app \
    --desired-status STOPPED --query 'taskArns[0:5]' --output text)

# Check CloudWatch logs for crash reason
aws logs filter-log-events --log-group-name /ecs/rails-app \
  --filter-pattern "FATAL" --start-time $(date -u -d '1 hour ago' +%s)000
```

### Common Causes
- **Exit code 137**: OOM kill — increase task memory
- **Exit code 1**: Application error — check logs
- **Health check failure**: App not responding on health endpoint — check startup time

### Resolution
1. If OOM: increase task memory definition
2. If app error: fix code, redeploy
3. If health check timeout: increase `healthCheckGracePeriodSeconds`
4. Rollback to previous task definition if new deploy caused it

---

## Runbook: Centrifugo Disconnections

### Symptoms
- Users reporting real-time updates not working
- Chat/notifications delayed or missing
- WebSocket connection errors in React Native logs

### Diagnosis
```bash
# Check Centrifugo health and connections
curl -s -H "Authorization: apikey $CENTRIFUGO_API_KEY" \
  http://centrifugo:8000/api/info | jq '.'

# Check if ALB WebSocket timeout is configured (default 60s may be too short)
aws elbv2 describe-target-group-attributes \
  --target-group-arn $TG_ARN --query 'Attributes[?Key==`stickiness.enabled`]'
```

### Resolution
1. Restart Centrifugo service
2. Check JWT token expiration — tokens may be expiring
3. Check ALB idle timeout (increase to 3600s for WebSocket)
4. Check Redis pub/sub adapter connectivity (if using Redis engine)

---

## Runbook: PostGIS Query Timeouts

### Symptoms
- Spatial queries (nearby search, geofence check) timing out
- High CPU on RDS during spatial operations

### Diagnosis
```sql
-- Check for sequential scans on spatial tables
SELECT relname, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE relname IN ('locations', 'geofences', 'tracks');

-- Check spatial indexes exist
SELECT indexname, indexdef FROM pg_indexes
WHERE indexdef LIKE '%gist%';

-- Analyze slow spatial query
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM locations
WHERE ST_DWithin(coordinates::geography, ST_MakePoint(-73.98, 40.74)::geography, 5000);
```

### Resolution
1. Add GiST index if missing: `CREATE INDEX CONCURRENTLY idx_locations_coords ON locations USING gist(coordinates);`
2. Use `ST_DWithin` instead of `ST_Distance` for radius queries
3. Add `LIMIT` to spatial queries to prevent large result sets
4. VACUUM ANALYZE the spatial table
5. Consider simplifying complex geometries with `ST_Simplify`
