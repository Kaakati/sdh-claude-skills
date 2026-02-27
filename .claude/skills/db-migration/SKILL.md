---
name: db-migration
description: Design PostgreSQL/PostGIS schemas and create safe database migrations with rollback plans, spatial column design, index strategy, and zero-downtime deployment patterns. Use this skill whenever someone asks to create a table, modify a schema, write a migration, design a data model, add an index, or says things like "create a migration for X", "add a column to Y", "design the database schema", "what indexes do I need", "plan the data model", or "how do I safely change this column type". Also trigger when someone mentions zero-downtime migrations, expand-and-contract pattern, PostGIS spatial columns, or large table migration strategy.
model: sonnet
---

# Database Migration

Create and execute database migrations safely. Every migration must be reversible, tested, and designed for zero-downtime deployment.

## Migration Safety Protocol

### Pre-Flight Checks

Before writing any migration:

1. **Verify current schema state**: Review the current migration history and database schema.
2. **Check for pending migrations**: Ensure all previous migrations have been applied and are not in a failed state.
3. **Assess table size**: For large tables (>1M rows), use the large table migration patterns below.
4. **Identify dependencies**: Check for foreign keys, triggers, views, and dependent queries.
5. **Estimate lock duration**: Will this migration require an exclusive lock? For how long?
6. **Confirm backup**: Verify that a recent database backup exists and is restorable.

### Migration File Requirements

Every migration must include:

1. **Descriptive name**: `YYYYMMDDHHMMSS_description.{sql,ts,py}`
   - Example: `20240115103000_add_status_column_to_orders.sql`
2. **Up migration**: The forward schema change.
3. **Down migration**: The exact reverse that restores the previous state.
4. **Data migration** (if needed): Separate from schema migration.
5. **Validation query**: A query to verify the migration was applied correctly.

### Reversibility Requirement

Every migration MUST be reversible. If a migration cannot be trivially reversed, document:
- Why it is not trivially reversible.
- The manual rollback procedure.
- Data preservation strategy for the rollback.

Test the rollback in a non-production environment before applying to production.

### Data Preservation Strategy

When modifying columns or tables that contain data:

1. **Never drop a column with data without a backup plan.**
2. Copy data to a temporary column or table before destructive changes.
3. Verify data integrity after the migration with count and checksum queries.
4. Keep backup columns/tables for a defined retention period (typically one release cycle).

## Zero-Downtime Patterns

### Expand and Contract Pattern

For breaking schema changes, split into two deployments:

**Phase 1 — Expand** (backwards compatible):
1. Add the new column/table.
2. Backfill data from the old structure.
3. Update application to write to both old and new.
4. Deploy application.

**Phase 2 — Contract** (after all clients use the new structure):
1. Stop writing to the old structure.
2. Drop the old column/table.
3. Deploy application.

### Adding a Column
```sql
-- Safe: add nullable column (no lock on reads)
ALTER TABLE orders ADD COLUMN status VARCHAR(50) DEFAULT NULL;

-- Then backfill in batches
UPDATE orders SET status = 'pending' WHERE status IS NULL AND id BETWEEN 1 AND 10000;
UPDATE orders SET status = 'pending' WHERE status IS NULL AND id BETWEEN 10001 AND 20000;
-- ...continue in batches

-- Then add NOT NULL constraint if needed (after backfill)
ALTER TABLE orders ALTER COLUMN status SET NOT NULL;
ALTER TABLE orders ALTER COLUMN status SET DEFAULT 'pending';
```

### Removing a Column
```sql
-- Phase 1: Stop reading the column in application code
-- Phase 2: Stop writing to the column in application code
-- Phase 3: Drop the column
ALTER TABLE orders DROP COLUMN legacy_status;
```

Never drop a column that the application still references.

### Renaming a Column
```sql
-- DO NOT: ALTER TABLE orders RENAME COLUMN status TO order_status;
-- This breaks existing queries instantly.

-- DO: Use expand/contract
-- Step 1: Add new column
ALTER TABLE orders ADD COLUMN order_status VARCHAR(50);
-- Step 2: Backfill
UPDATE orders SET order_status = status WHERE order_status IS NULL;
-- Step 3: Application writes to both columns (deploy code change)
-- Step 4: Application reads from new column (deploy code change)
-- Step 5: Drop old column
ALTER TABLE orders DROP COLUMN status;
```

### Adding an Index

Indexes on large tables can lock the table for minutes. Use concurrent index creation:

```sql
-- PostgreSQL: CREATE INDEX CONCURRENTLY (does not lock the table)
CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status);

-- MySQL: Use pt-online-schema-change or gh-ost for large tables
-- Or: ALTER TABLE orders ADD INDEX idx_status (status), ALGORITHM=INPLACE, LOCK=NONE;
```

Rules for indexes:
- Always add indexes for foreign key columns.
- Add indexes for columns used in WHERE, JOIN, ORDER BY, GROUP BY.
- Avoid indexes on low-cardinality columns (boolean, enum with few values) unless combined with other columns.
- Composite indexes: place the most selective column first.
- Monitor index usage — drop unused indexes.

### Changing a Column Type

```sql
-- DO NOT: ALTER TABLE orders ALTER COLUMN amount TYPE BIGINT;
-- This rewrites the entire table and locks it.

-- DO: Use expand/contract
-- Step 1: Add new column with the new type
ALTER TABLE orders ADD COLUMN amount_v2 BIGINT;
-- Step 2: Backfill with type conversion
UPDATE orders SET amount_v2 = amount::BIGINT WHERE amount_v2 IS NULL;
-- Step 3: Switch application to use new column
-- Step 4: Drop old column
ALTER TABLE orders DROP COLUMN amount;
-- Step 5: Rename new column (if desired, use expand/contract for rename too)
```

## Large Table Migration Patterns

For tables with millions of rows:

### Batch Processing
- Process rows in batches of 1,000-10,000.
- Add a small delay between batches to reduce load.
- Use indexed columns for batch boundaries (WHERE id BETWEEN x AND y).
- Monitor replication lag during backfill.

### Online Schema Change Tools
- **PostgreSQL**: `pg_repack`, or application-level expand/contract.
- **MySQL**: `pt-online-schema-change` (Percona), `gh-ost` (GitHub).
- These tools create a shadow table, copy data, swap tables — with minimal locking.

### Shadow Table Pattern
1. Create a new table with the desired schema.
2. Set up triggers to sync writes from old to new table.
3. Backfill historical data in batches.
4. Swap old and new tables atomically.
5. Drop the old table after verification.

## Deployment Checklist

Before applying a migration to production:

- [ ] Migration tested in a staging environment with production-like data volume.
- [ ] Rollback tested — down migration verified.
- [ ] Backup verified — restorable and recent.
- [ ] Application code is compatible with both the old and new schema (expand/contract).
- [ ] Monitoring alerts configured for database errors and performance.
- [ ] Team notified of the migration window.
- [ ] Estimated lock duration and data backfill time documented.
- [ ] Migration runs within the maintenance window (if locking is required).
- [ ] Post-migration validation queries prepared.

## Post-Migration Validation

After applying a migration:

1. Run validation queries to confirm schema changes.
2. Verify row counts (no accidental data loss).
3. Check application health — no errors related to schema.
4. Verify replication is not lagging.
5. Monitor query performance — check for slow queries caused by the change.
6. If issues found, execute rollback within the defined rollback window.
