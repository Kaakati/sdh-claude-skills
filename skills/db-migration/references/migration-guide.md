# Migration Patterns Guide

Safe and unsafe approaches for common database schema changes. Always prefer the safe approach. Use the unsafe approach only when the table is small and downtime is acceptable.

---

## Add Column

### Safe Approach
```sql
-- 1. Add nullable column (instant in most databases)
ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT NULL;

-- 2. Backfill data in batches (if default needed)
UPDATE users SET phone = 'unknown' WHERE phone IS NULL AND id BETWEEN 1 AND 10000;
-- Repeat for all batches

-- 3. Add NOT NULL constraint (after backfill is complete)
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
ALTER TABLE users ALTER COLUMN phone SET DEFAULT 'unknown';
```

### Unsafe Approach (small tables only)
```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20) NOT NULL DEFAULT 'unknown';
-- Rewrites entire table; locks table during operation
```

### Rollback
```sql
ALTER TABLE users DROP COLUMN phone;
```

---

## Remove Column

### Safe Approach
```sql
-- Phase 1: Remove all application references to the column (deploy code change)
-- Phase 2: Wait for all application instances to be updated
-- Phase 3: Drop the column
ALTER TABLE users DROP COLUMN legacy_phone;
```

### Important
- Never drop a column that any running application instance still references.
- If using ORMs, ensure the column is removed from the model before dropping.
- Consider keeping the column for one release cycle as a safety net.

### Rollback
```sql
-- Re-add the column (data will be lost unless backed up)
ALTER TABLE users ADD COLUMN legacy_phone VARCHAR(20);
-- Restore data from backup if available
```

---

## Rename Column

### Safe Approach (Expand/Contract)
```sql
-- Step 1: Add new column
ALTER TABLE users ADD COLUMN full_name VARCHAR(200);

-- Step 2: Backfill
UPDATE users SET full_name = name WHERE full_name IS NULL;

-- Step 3: Deploy app writing to both columns
-- Step 4: Deploy app reading from new column only
-- Step 5: Deploy app writing to new column only
-- Step 6: Drop old column
ALTER TABLE users DROP COLUMN name;
```

### Unsafe Approach (small tables, downtime acceptable)
```sql
ALTER TABLE users RENAME COLUMN name TO full_name;
-- Instant but breaks all queries referencing 'name'
```

### Rollback
```sql
-- If using expand/contract: drop the new column
ALTER TABLE users DROP COLUMN full_name;

-- If using rename: rename back
ALTER TABLE users RENAME COLUMN full_name TO name;
```

---

## Add Index

### Safe Approach
```sql
-- PostgreSQL: concurrent index (no table lock)
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);

-- MySQL: online DDL
ALTER TABLE users ADD INDEX idx_email (email), ALGORITHM=INPLACE, LOCK=NONE;
```

### Unsafe Approach
```sql
CREATE INDEX idx_users_email ON users(email);
-- Locks table for reads and writes until complete
```

### Rollback
```sql
DROP INDEX idx_users_email;
-- Or for MySQL: ALTER TABLE users DROP INDEX idx_email;
```

### Notes
- Concurrent index creation takes longer but does not block queries.
- If concurrent index creation fails, a partially-built invalid index may remain; drop it and retry.
- Monitor disk space — index creation requires temporary space.
- For composite indexes, put the most selective column first.

---

## Change Column Type

### Safe Approach (Expand/Contract)
```sql
-- Step 1: Add new column with target type
ALTER TABLE orders ADD COLUMN amount_cents BIGINT;

-- Step 2: Backfill in batches
UPDATE orders SET amount_cents = CAST(amount * 100 AS BIGINT)
  WHERE amount_cents IS NULL AND id BETWEEN 1 AND 10000;

-- Step 3: Deploy app to write to both columns
-- Step 4: Verify data consistency
SELECT COUNT(*) FROM orders WHERE amount_cents != CAST(amount * 100 AS BIGINT);

-- Step 5: Deploy app to read from new column
-- Step 6: Drop old column
ALTER TABLE orders DROP COLUMN amount;
```

### Unsafe Approach (small tables)
```sql
ALTER TABLE orders ALTER COLUMN amount TYPE BIGINT;
-- Rewrites entire table; locks table
```

### Rollback
```sql
-- If expand/contract: drop new column, app continues using old
ALTER TABLE orders DROP COLUMN amount_cents;
```

---

## Split Table

When a table grows too wide or contains logically separate data.

### Safe Approach
```sql
-- Step 1: Create new table
CREATE TABLE user_profiles (
  user_id UUID PRIMARY KEY REFERENCES users(id),
  bio TEXT,
  avatar_url VARCHAR(500),
  preferences JSONB
);

-- Step 2: Backfill in batches
INSERT INTO user_profiles (user_id, bio, avatar_url, preferences)
SELECT id, bio, avatar_url, preferences FROM users
WHERE id BETWEEN 1 AND 10000;

-- Step 3: Deploy app to read from both tables, write to new table
-- Step 4: Verify data consistency
-- Step 5: Deploy app to read only from new table
-- Step 6: Drop old columns from original table
ALTER TABLE users DROP COLUMN bio;
ALTER TABLE users DROP COLUMN avatar_url;
ALTER TABLE users DROP COLUMN preferences;
```

### Rollback
```sql
-- Re-add columns to original table
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
ALTER TABLE users ADD COLUMN preferences JSONB;

-- Copy data back
UPDATE users SET
  bio = up.bio,
  avatar_url = up.avatar_url,
  preferences = up.preferences
FROM user_profiles up WHERE users.id = up.user_id;

-- Drop new table
DROP TABLE user_profiles;
```

---

## Merge Tables

When separate tables should be consolidated.

### Safe Approach
```sql
-- Step 1: Add columns to target table
ALTER TABLE users ADD COLUMN bio TEXT;
ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);

-- Step 2: Backfill from source table
UPDATE users SET
  bio = up.bio,
  avatar_url = up.avatar_url
FROM user_profiles up WHERE users.id = up.user_id;

-- Step 3: Deploy app to write to both tables
-- Step 4: Deploy app to read from merged table
-- Step 5: Deploy app to stop writing to source table
-- Step 6: Drop source table
DROP TABLE user_profiles;
```

### Rollback
```sql
-- Re-create source table and copy data back
CREATE TABLE user_profiles AS
SELECT id AS user_id, bio, avatar_url FROM users;

-- Drop merged columns
ALTER TABLE users DROP COLUMN bio;
ALTER TABLE users DROP COLUMN avatar_url;
```

---

## Add Foreign Key Constraint

### Safe Approach
```sql
-- Step 1: Add the column (if new)
ALTER TABLE orders ADD COLUMN customer_id UUID;

-- Step 2: Backfill data

-- Step 3: Validate existing data satisfies the constraint
SELECT COUNT(*) FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE o.customer_id IS NOT NULL AND c.id IS NULL;
-- Must return 0

-- Step 4: Add constraint as NOT VALID (PostgreSQL — does not scan existing rows)
ALTER TABLE orders ADD CONSTRAINT fk_orders_customer
  FOREIGN KEY (customer_id) REFERENCES customers(id) NOT VALID;

-- Step 5: Validate the constraint (scans existing rows but does not block writes)
ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_customer;
```

### Unsafe Approach
```sql
ALTER TABLE orders ADD CONSTRAINT fk_orders_customer
  FOREIGN KEY (customer_id) REFERENCES customers(id);
-- Scans entire table; locks table during validation
```

### Rollback
```sql
ALTER TABLE orders DROP CONSTRAINT fk_orders_customer;
```

---

## General Rollback Principles

1. **Every migration has a corresponding rollback script** — no exceptions.
2. **Test rollback before production** — run the full up-then-down cycle in staging.
3. **Data-destructive rollbacks must be flagged** — if the down migration loses data, document it.
4. **Rollback window**: Define a maximum time after deployment during which rollback is feasible (typically 1-4 hours).
5. **After the rollback window**: Fixing forward (new migration) is safer than rolling back.
6. **Never rollback a migration that other migrations depend on** — rollback in reverse order.
