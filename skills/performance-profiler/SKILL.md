---
name: performance-profiler
description: Profile and optimize application performance including Rails query optimization, React Native rendering, Redis cache strategy, PostgreSQL/PostGIS query tuning, and Sidekiq job performance. Use this skill whenever someone asks to investigate slowness, profile performance, optimize queries, reduce latency, or says things like "why is this slow", "profile this endpoint", "optimize this query", "find the bottleneck", "improve performance of X", or "this page takes too long to load". Also trigger when someone mentions N+1 queries, EXPLAIN ANALYZE, memory leaks, bundle size analysis, or cache hit rate optimization.
model: sonnet
allowed-tools: Read, Grep, Glob, Bash
---

# Performance Profiler

Investigate and resolve performance issues systematically across our stack: Rails + PostgreSQL/PostGIS + Redis + Sidekiq + React Native + Centrifugo.

## Performance Investigation Workflow

### Step 1: Identify the Bottleneck Type

Before optimizing, determine what is slow and why. The bottleneck categories for our stack:

| Type | Symptoms | Investigation Tool |
|---|---|---|
| **Rails** | Slow API responses, high CPU on ECS | rack-mini-profiler, bullet gem, Rails logs |
| **PostgreSQL** | Slow queries, lock waits, sequential scans | `EXPLAIN ANALYZE`, pg_stat_statements |
| **PostGIS** | Slow spatial queries, missing GiST indexes | `EXPLAIN ANALYZE` with ST_ functions |
| **Redis** | Cache misses, high memory, slow Sidekiq | redis-cli INFO, Sidekiq dashboard |
| **React Native** | Slow renders, jank, memory leaks | Flipper, React DevTools Profiler |
| **Centrifugo** | Connection drops, message delays | Centrifugo admin UI, connection metrics |

Key rule: **Measure first, optimize second.** Never optimize based on assumptions.

### Step 2: Gather Metrics

#### Backend Metrics
- **Response time**: p50, p95, p99 latency for each endpoint.
- **Throughput**: Requests per second the service handles.
- **Error rate**: Percentage of failed requests.
- **Database**: Query execution time, number of queries per request, slow query log.
- **Memory**: Heap usage, GC frequency and duration.
- **CPU**: Average utilization, spikes.

#### Frontend Metrics
- **Core Web Vitals**: LCP (Largest Contentful Paint), FID (First Input Delay), CLS (Cumulative Layout Shift).
- **TTFB**: Time to First Byte.
- **Bundle size**: Total JavaScript, CSS, and asset sizes.
- **Render performance**: Frame rate, long tasks.

### Step 3: Profile the Issue

#### Database Query Profiling
1. Enable slow query logging (threshold: 50ms).
2. Run `EXPLAIN ANALYZE` on slow queries.
3. Check for:
   - Full table scans (missing indexes).
   - N+1 patterns (many small queries instead of one batch).
   - Inefficient joins (wrong join type, missing index on join column).
   - Unnecessary columns fetched (`SELECT *` instead of specific columns).
   - Large result sets without pagination.

#### Application Code Profiling
1. Use a CPU profiler to capture a flame graph during the slow operation.
2. Identify hot functions — functions that consume the most time.
3. Check for:
   - Synchronous operations blocking the event loop.
   - Redundant computations (recalculating the same value).
   - Inefficient algorithms (O(n^2) where O(n log n) is possible).
   - Excessive object creation causing GC pressure.
   - Large string concatenation in loops.

#### Memory Profiling
1. Take heap snapshots before and after the suspected leak.
2. Compare snapshots to identify objects that grow but are never released.
3. Check for:
   - Event listeners not removed.
   - Closures retaining large objects.
   - Global caches without size limits or expiration.
   - Buffers not freed after use.

#### Frontend Bundle Analysis
1. Run the bundle analyzer to visualize module sizes.
2. Check for:
   - Large dependencies with smaller alternatives.
   - Duplicate dependencies (same library in multiple versions).
   - Unused code (tree-shaking not working).
   - Unminified or uncompressed assets.
   - Images without optimization or lazy loading.

### Step 4: Common Anti-Patterns and Fixes

#### N+1 Queries
```
// BAD: N+1 — one query per user
const users = await db.query('SELECT * FROM users');
for (const user of users) {
  user.orders = await db.query('SELECT * FROM orders WHERE user_id = ?', [user.id]);
}

// GOOD: Batch query
const users = await db.query('SELECT * FROM users');
const userIds = users.map(u => u.id);
const orders = await db.query('SELECT * FROM orders WHERE user_id IN (?)', [userIds]);
// Map orders to users in application code
```

#### Missing Database Indexes
```sql
-- Find slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 20;

-- Check if a query uses an index
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 'abc-123';
-- If "Seq Scan" appears, add an index:
CREATE INDEX CONCURRENTLY idx_orders_customer_id ON orders(customer_id);
```

#### Unnecessary Re-Renders (React)
```jsx
// BAD: New object reference on every render
<Component style={{ color: 'red' }} />

// GOOD: Stable reference
const style = useMemo(() => ({ color: 'red' }), []);
<Component style={style} />

// BAD: Inline function creates new reference
<Button onClick={() => handleClick(id)} />

// GOOD: Stable callback
const handleClickMemo = useCallback(() => handleClick(id), [id]);
<Button onClick={handleClickMemo} />
```

#### Blocking the Event Loop
```javascript
// BAD: Synchronous file read in request handler
app.get('/data', (req, res) => {
  const data = fs.readFileSync('/path/to/large-file.json');
  res.json(JSON.parse(data));
});

// GOOD: Async file read
app.get('/data', async (req, res) => {
  const data = await fs.promises.readFile('/path/to/large-file.json');
  res.json(JSON.parse(data));
});
```

#### Unbounded Caches
```javascript
// BAD: Cache grows without limit
const cache = new Map();
function getData(key) {
  if (cache.has(key)) return cache.get(key);
  const value = computeExpensive(key);
  cache.set(key, value);
  return value;
}

// GOOD: LRU cache with max size
const cache = new LRUCache({ max: 1000, ttl: 60000 });
```

#### Large Payloads
```javascript
// BAD: Return everything
app.get('/users', async (req, res) => {
  const users = await db.query('SELECT * FROM users');
  res.json(users);
});

// GOOD: Paginate and select fields
app.get('/users', async (req, res) => {
  const { page = 1, limit = 20 } = req.query;
  const users = await db.query(
    'SELECT id, name, email FROM users LIMIT ? OFFSET ?',
    [Math.min(limit, 100), (page - 1) * limit]
  );
  res.json({ data: users, pagination: { page, limit } });
});
```

### Step 5: Optimization Strategies

#### Caching Layers
1. **Application cache**: In-memory (LRU) for frequently accessed, rarely changed data.
2. **Distributed cache**: Redis/Memcached for data shared across instances.
3. **HTTP cache**: `Cache-Control` headers for static and semi-static responses.
4. **CDN**: Static assets and cacheable API responses at the edge.

Cache invalidation strategy must be defined for every cached item.

#### Database Optimization
1. Add indexes for query patterns (check with `EXPLAIN`).
2. Use connection pooling — do not open a new connection per request.
3. Denormalize read-heavy data where appropriate.
4. Use read replicas for reporting and analytics queries.
5. Archive old data to keep active tables small.

#### Frontend Optimization
1. Code splitting — load only the JavaScript needed for the current page.
2. Lazy load images and below-the-fold content.
3. Compress assets with gzip or brotli.
4. Preload critical resources, prefetch likely next pages.
5. Use a CDN for static assets.

### Step 6: Benchmark and Verify

After optimizing:

1. Run the same benchmark that revealed the issue.
2. Compare before/after metrics.
3. Verify no regressions in other areas.
4. Document the optimization with before/after numbers.

Benchmark methodology:
- Use consistent test data and load patterns.
- Run multiple iterations (minimum 10) and report p50/p95/p99.
- Test under realistic load, not just single-request timing.
- Include warm-up period to fill caches.

### Web Core Web Vitals

For web frontends (Vite SPA + Next.js), measure and optimize Core Web Vitals:

| Metric | Target | Tool |
|--------|--------|------|
| LCP (Largest Contentful Paint) | < 2.5s | Lighthouse, web-vitals |
| INP (Interaction to Next Paint) | < 200ms | Lighthouse, web-vitals |
| CLS (Cumulative Layout Shift) | < 0.1 | Lighthouse, web-vitals |
| TTFB (Time to First Byte) | < 800ms | Lighthouse |

#### Web Bundle Analysis
- **Vite SPA**: Use `vite-bundle-visualizer` (`npx vite-bundle-visualizer`) to audit chunk sizes. Target < 300KB initial JS.
- **Next.js**: Use `@next/bundle-analyzer` to inspect client and server bundles. Target < 200KB client JS per route.
- Check for: large dependencies, duplicate modules, missing tree-shaking, unoptimized images.

#### Hydration Performance (Next.js)
- Minimize Client Component boundaries — each `'use client'` component adds to hydration cost.
- Use `<Suspense>` to stream Server Component content progressively.
- Pass serialized data from Server Components to Client Components to avoid double-fetching.

#### Lighthouse CI
- Run Lighthouse CI in the deployment pipeline.
- Set performance budget: performance > 90, accessibility > 95, best practices > 90.
- Fail CI if scores drop below thresholds.

## Output Format

When reporting performance findings:

| Issue | Impact | Location | Current | Target | Fix |
|---|---|---|---|---|---|
| N+1 query on user orders | 200ms per request | api/users.ts:45 | 150 queries/req | 2 queries/req | Batch fetch with IN clause |
| Missing index on orders.status | Slow order listing | orders table | 850ms seq scan | <10ms index scan | Add index on status column |
| Unoptimized hero image | 3s LCP | public/hero.png | 2.4MB PNG | <200KB WebP | Convert and resize |
