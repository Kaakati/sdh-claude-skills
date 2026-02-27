# PostgreSQL / PostGIS Patterns

## Common JSONB Patterns

### Querying JSONB
```sql
-- Key exists
SELECT * FROM products WHERE metadata ? 'color';

-- Key equals value
SELECT * FROM products WHERE metadata->>'color' = 'red';

-- Nested key
SELECT * FROM products WHERE metadata->'dimensions'->>'width' = '10';

-- Contains (uses GIN index)
SELECT * FROM products WHERE metadata @> '{"category": "electronics"}';

-- Array contains value
SELECT * FROM products WHERE metadata->'tags' ? 'sale';
```

### JSONB in Rails
```ruby
# Query
Product.where("metadata @> ?", { category: "electronics" }.to_json)

# Update specific key
Product.where(id: 1).update_all("metadata = jsonb_set(metadata, '{color}', '\"blue\"')")

# Scope
scope :with_tag, ->(tag) { where("metadata->'tags' ? :tag", tag: tag) }
```

## PostGIS Spatial Queries

### Find Nearby (Radius Search)
```ruby
# Using ST_DWithin (uses spatial index, best performance)
scope :nearby, ->(lat, lng, radius_m) {
  where(
    "ST_DWithin(coordinates::geography, ST_MakePoint(:lng, :lat)::geography, :radius)",
    lat: lat, lng: lng, radius: radius_m
  )
}

# With distance calculation and ordering
scope :nearby_with_distance, ->(lat, lng, radius_m) {
  select("*, ST_Distance(coordinates::geography, ST_MakePoint(#{lng}, #{lat})::geography) AS distance_meters")
    .where("ST_DWithin(coordinates::geography, ST_MakePoint(:lng, :lat)::geography, :radius)", lat: lat, lng: lng, radius: radius_m)
    .order("distance_meters ASC")
}
```

### Point in Polygon (Geofence Check)
```ruby
# Check if a point is inside a geofence
scope :containing_point, ->(lat, lng) {
  where(
    "ST_Contains(boundary, ST_MakePoint(:lng, :lat)::geometry)",
    lat: lat, lng: lng
  )
}

# In Rails model
def contains?(lat, lng)
  point = RGeo::Geographic.spherical_factory(srid: 4326).point(lng, lat)
  boundary.contains?(point)
end
```

### Bounding Box Query (Map Viewport)
```ruby
# Find locations within map bounds
scope :within_bounds, ->(sw_lat, sw_lng, ne_lat, ne_lng) {
  where(
    "coordinates && ST_MakeEnvelope(:sw_lng, :sw_lat, :ne_lng, :ne_lat, 4326)",
    sw_lat: sw_lat, sw_lng: sw_lng, ne_lat: ne_lat, ne_lng: ne_lng
  )
}
```

### Calculate Distance Between Two Points
```sql
SELECT ST_Distance(
  a.coordinates::geography,
  b.coordinates::geography
) AS distance_meters
FROM locations a, locations b
WHERE a.id = 1 AND b.id = 2;
```

## CTE (Common Table Expressions) Patterns

### Recursive CTE for Hierarchies
```sql
-- Organization tree
WITH RECURSIVE org_tree AS (
  SELECT id, name, parent_id, 0 AS depth
  FROM departments WHERE parent_id IS NULL
  UNION ALL
  SELECT d.id, d.name, d.parent_id, ot.depth + 1
  FROM departments d
  INNER JOIN org_tree ot ON d.parent_id = ot.id
)
SELECT * FROM org_tree ORDER BY depth, name;
```

### CTE for Complex Aggregations
```sql
-- Order statistics by customer
WITH order_stats AS (
  SELECT
    customer_id,
    count(*) AS order_count,
    sum(total_cents) AS total_spent,
    max(created_at) AS last_order
  FROM orders
  WHERE created_at > now() - interval '30 days'
  GROUP BY customer_id
)
SELECT c.name, os.*
FROM customers c
JOIN order_stats os ON c.id = os.customer_id
ORDER BY os.total_spent DESC;
```

## Window Functions

```sql
-- Rank by total orders per customer
SELECT
  customer_id,
  order_count,
  RANK() OVER (ORDER BY order_count DESC) AS rank
FROM (
  SELECT customer_id, count(*) AS order_count
  FROM orders GROUP BY customer_id
) subq;

-- Running total
SELECT
  created_at::date AS date,
  total_cents,
  SUM(total_cents) OVER (ORDER BY created_at) AS running_total
FROM orders;

-- Moving average (7-day)
SELECT
  date,
  revenue,
  AVG(revenue) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7d
FROM daily_revenue;
```

## Table Partitioning

```sql
-- Range partition by date (for large tables like events, logs)
CREATE TABLE events (
  id bigserial,
  event_type text,
  payload jsonb,
  created_at timestamptz NOT NULL
) PARTITION BY RANGE (created_at);

CREATE TABLE events_2025_01 PARTITION OF events
  FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE events_2025_02 PARTITION OF events
  FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
```

```ruby
# Rails migration for partitioned table
class CreateEventsPartitioned < ActiveRecord::Migration[7.1]
  def up
    execute <<-SQL
      CREATE TABLE events (
        id bigserial,
        event_type text NOT NULL,
        payload jsonb DEFAULT '{}',
        created_at timestamptz NOT NULL DEFAULT now()
      ) PARTITION BY RANGE (created_at);
    SQL
  end
end
```

## Materialized Views

```sql
-- For expensive aggregation queries
CREATE MATERIALIZED VIEW daily_order_stats AS
SELECT
  created_at::date AS date,
  count(*) AS order_count,
  sum(total_cents) AS revenue_cents,
  avg(total_cents) AS avg_order_cents
FROM orders
GROUP BY created_at::date;

CREATE UNIQUE INDEX ON daily_order_stats (date);

-- Refresh (run via Sidekiq cron job)
REFRESH MATERIALIZED VIEW CONCURRENTLY daily_order_stats;
```

## Index Best Practices

```sql
-- Create indexes concurrently (no table lock in production)
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);

-- Partial index for common filter
CREATE INDEX CONCURRENTLY idx_orders_active
ON orders(created_at DESC)
WHERE status = 'active';

-- Composite index (column order matters!)
-- Put equality columns first, range columns last
CREATE INDEX idx_orders_user_date ON orders(user_id, created_at DESC);

-- Check unused indexes (candidates for removal)
SELECT schemaname, relname, indexrelname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;
```
