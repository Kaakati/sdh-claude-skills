# Performance Benchmarks and Targets

Standard performance targets for the project. All new features and changes should meet these thresholds. Deviations require documented justification.

---

## API Response Times

| Metric | Target | Acceptable | Action Required |
|---|---|---|---|
| p50 latency | < 100ms | < 200ms | > 200ms |
| p95 latency | < 200ms | < 500ms | > 500ms |
| p99 latency | < 500ms | < 1000ms | > 1000ms |
| Timeout threshold | 5s | 10s | Endpoint redesign needed |

### By Endpoint Type

| Type | p95 Target | Notes |
|---|---|---|
| Simple CRUD (read) | < 50ms | Single resource fetch |
| Simple CRUD (write) | < 100ms | Single resource create/update |
| List/Search | < 200ms | Paginated, indexed queries |
| Aggregation/Report | < 500ms | Complex queries, consider caching |
| File upload/download | < 2s | Depends on size; use streaming |
| Webhook/Callback | < 1s | External service calls |
| Background job trigger | < 200ms | Job queued, not completed |

---

## Database Query Limits

| Metric | Target | Acceptable | Action Required |
|---|---|---|---|
| Single query execution | < 50ms | < 100ms | > 100ms |
| Queries per API request | < 10 | < 20 | > 20 |
| N+1 queries | 0 | 0 | Any N+1 pattern |
| Slow query log threshold | 100ms | 200ms | Configure per environment |

### Query Plan Rules
- No full table scans on tables with > 10,000 rows.
- All foreign key columns must have indexes.
- Composite indexes for multi-column WHERE clauses used in hot paths.
- Index-only scans preferred for high-frequency read queries.

### Connection Pool Settings

| Setting | Development | Staging | Production |
|---|---|---|---|
| Min connections | 2 | 5 | 10 |
| Max connections | 10 | 20 | 50 |
| Idle timeout | 30s | 30s | 60s |
| Connection timeout | 5s | 5s | 3s |
| Statement timeout | 30s | 15s | 10s |

---

## Frontend Bundle Size Budgets

| Asset | Target | Maximum | Notes |
|---|---|---|---|
| Initial JS bundle | < 150KB (gzipped) | 250KB | Critical path JavaScript |
| Initial CSS | < 50KB (gzipped) | 80KB | Above-the-fold styles |
| Total page weight | < 500KB | 1MB | All resources for initial load |
| Individual chunk | < 100KB (gzipped) | 150KB | Code-split chunks |
| Image (hero/banner) | < 200KB | 500KB | WebP/AVIF format, responsive |
| Image (thumbnail) | < 30KB | 50KB | Optimized, lazy loaded |
| Font file | < 50KB per font | 100KB | Subset to used characters |

### Bundle Analysis Triggers
Run bundle analysis when:
- Adding a new dependency.
- Total bundle size increases by more than 10KB.
- A new route or page is added.

---

## Core Web Vitals

| Metric | Good | Needs Improvement | Poor |
|---|---|---|---|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5s - 4.0s | > 4.0s |
| FID (First Input Delay) | < 100ms | 100ms - 300ms | > 300ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1 - 0.25 | > 0.25 |
| INP (Interaction to Next Paint) | < 200ms | 200ms - 500ms | > 500ms |
| TTFB (Time to First Byte) | < 800ms | 800ms - 1800ms | > 1800ms |

---

## Memory Thresholds

### Backend (Node.js)

| Metric | Target | Warning | Critical |
|---|---|---|---|
| Heap used | < 256MB | 512MB | 768MB |
| Heap total | < 512MB | 768MB | 1GB |
| RSS | < 512MB | 1GB | 1.5GB |
| GC pause (p95) | < 50ms | 100ms | 200ms |
| GC frequency | < 1/min | 5/min | 10/min |

### Memory Leak Detection
- Memory growth > 10MB/hour under stable load indicates a leak.
- Heap snapshots should be compared after 1 hour and 4 hours of load.
- Event listener count should not grow with request count.

### Backend (Rails / Ruby)

| Metric | Target | Warning | Critical |
|---|---|---|---|
| RSS per worker | < 256MB | 512MB | 768MB |
| Worker count (Puma) | CPU cores x 1.5 | Adjust per load | OOM risk |
| GC frequency | Minimal | Tune RUBY_GC_* env vars | High GC overhead |
| Sidekiq memory/worker | < 256MB | 512MB | Restart worker |

### React Native Mobile

| Metric | Target | Warning | Critical |
|---|---|---|---|
| JS heap | < 150MB | 200MB | 300MB |
| FlatList frame rate | 60fps | 45fps | < 30fps |
| Time to Interactive | < 2s | 3s | > 4s |
| Bundle size (JS) | < 5MB | 8MB | > 10MB |

### Sidekiq Job Performance

| Queue | Target Duration | Warning | Max Retries |
|---|---|---|---|
| critical | < 1s | 5s | 3 |
| default | < 5s | 30s | 5 |
| low_priority | < 30s | 2min | 10 |
| mailers | < 10s | 30s | 3 |

---

## Throughput Targets

| Scenario | Target RPS | Notes |
|---|---|---|
| Single instance | 500 RPS | Simple CRUD operations |
| Cluster (4 instances) | 1500 RPS | With load balancer |
| Peak load (expected) | 2x normal | Handle gracefully |
| Spike tolerance | 5x normal | Degrade gracefully, no crashes |

---

## Caching Performance

| Cache Layer | Hit Rate Target | TTL Range | Max Size |
|---|---|---|---|
| Application (in-memory) | > 90% | 1-5 minutes | 1000 entries |
| Distributed (Redis) | > 80% | 5-60 minutes | Per key policy |
| HTTP (CDN) | > 70% | 1 hour - 1 day | Per resource type |
| Browser | > 80% | Immutable for hashed assets | Cache-Control headers |

---

## Load Testing Requirements

### When to Load Test
- Before major releases.
- After significant architecture changes.
- When adding new high-traffic endpoints.
- After database schema changes on large tables.

### Load Test Profiles

| Profile | Duration | Pattern | Purpose |
|---|---|---|---|
| Smoke | 1 minute | 1 virtual user | Verify test works |
| Load | 10 minutes | Ramp to expected load | Baseline performance |
| Stress | 15 minutes | Ramp to 2x expected load | Find breaking point |
| Soak | 1 hour | Sustained expected load | Detect memory leaks |
| Spike | 5 minutes | Sudden 5x burst | Test auto-scaling |

### Success Criteria
- Error rate < 1% under expected load.
- p95 latency meets targets under expected load.
- No memory leaks during soak test.
- Recovery time < 30s after spike.
