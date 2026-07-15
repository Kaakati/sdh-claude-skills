---
name: std-database
description: Database conventions — migrations, indexing, query optimization, PostGIS, zero-downtime expand/contract. Use when writing migrations or designing schema.
paths:
  - "**/migrations/**"
  - "**/migrate/**"
  - "**/models/**"
  - "**/schemas/**"
  - "**/repositories/**"
  - "**/db/**/*.rb"
---

# Database Standards

Rules for database design, migrations, queries, and data management.

**Enforcement**: code-reviewer skill (Step 5: Performance Check, Step 8: Stack-Specific Checks), db-migration skill (migration safety protocol), dangerous-command-blocker.py hook (blocks unfiltered DELETE/DROP).

## Migration Safety

- **Every migration sets `lock_timeout` (e.g. 5s).** The default is **0 — wait forever**, and a
  migration that *waits* is more dangerous than one that fails: `ALTER TABLE` needs
  `ACCESS EXCLUSIVE`, which blocks `SELECT`, and every query arriving after it queues behind it.
  A millisecond-fast, correctly-written migration becomes a full table outage for as long as some
  unrelated slow query runs. Failing is the good outcome — retry it. → `references/locking-and-timeouts.md`
- **All migrations must be reversible**. Prefer `change` — ActiveRecord infers the inverse. When
  it cannot (raw SQL, data backfills), write `up`/`down` explicitly rather than leaving the
  rollback undefined:
  ```ruby
  class CreateOrders < ActiveRecord::Migration[7.1]
    def change
      create_table :orders, id: :uuid do |t|
        t.references :user, null: false, foreign_key: true, type: :uuid
        t.decimal :total_amount, precision: 10, scale: 2, null: false
        t.timestamps                      # created_at / updated_at
      end
    end
  end
  ```
  ```ruby
  # Irreversible by inference -> say so, or `rails db:rollback` fails at 2am
  class BackfillOrderStatus < ActiveRecord::Migration[7.1]
    def up
      Order.where(status: nil).in_batches.update_all(status: "pending")
    end

    def down
      raise ActiveRecord::IrreversibleMigration
    end
  end
  ```

- **No destructive migrations without a data backup plan**. Before dropping tables, columns, or changing types:
  1. Document the data impact in the migration file.
  2. Ensure a backup or data migration step exists.
  3. Use multi-step migrations for risky changes (add new column -> migrate data -> drop old column).

- **Test migrations** in a staging environment before running in production.
- Never manually modify the database in production. All changes go through migrations.
- Name migration files descriptively: `20240115_create_orders_table`, `20240116_add_status_to_orders`.

## Naming Conventions

- **Tables**: `snake_case`, plural — `users`, `order_items`, `audit_logs`.
- **Columns**: `snake_case` — `first_name`, `created_at`, `is_active`.
- **Primary keys**: `id` (UUID preferred over auto-increment for distributed systems).
- **Foreign keys**: `referenced_table_singular_id` — `user_id`, `order_id`.
- **Indexes**: `idx_table_column` — `idx_users_email`, `idx_orders_user_id_created_at`.
- **Constraints**: `chk_table_description` — `chk_orders_positive_amount`.
- **Booleans**: Prefix with `is_` or `has_` — `is_active`, `has_verified_email`.

## Indexing

- **Index all foreign keys**. Every column referenced in a JOIN or WHERE clause on a foreign key must be indexed.
- **Index frequently queried columns**: columns used in WHERE, ORDER BY, and GROUP BY clauses.
- **Composite indexes**: Order columns from most selective to least selective. The index on `(user_id, created_at)` supports queries filtering by `user_id` alone, but not `created_at` alone.
- **Do not over-index**. Each index has a write performance cost. Monitor query patterns and add indexes based on actual usage.
- Use `EXPLAIN ANALYZE` to validate that queries use expected indexes.

## Transactions

- **Use transactions for multi-table operations**. Any operation that modifies more than one table must be wrapped in a transaction:
  ```ruby
  # app/services/orders/create.rb
  ActiveRecord::Base.transaction do
    order = Order.create!(user:, total_amount:)
    order.line_items.insert_all!(items)          # one statement, not N
  end
  ```
- Set appropriate isolation levels based on consistency requirements.
- **Keep transactions short — never make an HTTP call inside one.** The transaction holds its
  row locks for as long as the slowest thing in the block, so a payment API that hangs for 30s
  holds those locks for 30s and everything touching those rows queues behind it. Do the external
  call first, then open the transaction to record the result.
- **`create!` / `save!`, not `create` / `save`, inside a transaction.** The non-bang forms return
  `false` instead of raising, so the block completes, nothing rolls back, and you commit half the
  operation. This is the single most common way a Rails transaction silently does nothing.
- `after_commit`, not `after_save`, for anything the outside world sees (enqueuing a Sidekiq job,
  publishing to Centrifugo). A job enqueued inside the transaction can start — and fail to find
  the row — before the commit lands.

## N+1 Query Prevention

- **Never query in a loop**. Eager-load the association instead:
  ```ruby
  # BAD — N+1: one query per user, and it looks fine with 10 rows in development
  User.all.each { |user| user.orders.each { |o| puts o.total_amount } }

  # GOOD — two queries total
  User.includes(:orders).each { |user| user.orders.each { |o| puts o.total_amount } }
  ```
- **`includes` vs `preload` vs `eager_load`** — `preload` always issues a separate query;
  `eager_load` always LEFT JOINs; `includes` picks, and switches to a JOIN when you reference the
  association in a `where`. If you filter on the association, say `references` or you get a
  missing-column error at runtime:
  ```ruby
  User.includes(:orders).where(orders: { status: "paid" }).references(:orders)
  ```
- **Serializers are where N+1 hides.** Panko does not eager-load for you: a `has_many` in a
  serializer fires a query per record unless the controller's scope already included it.
- Add `bullet` in development — an N+1 with 10 rows in dev is invisible and a full-table stall in
  production.

## Query Best Practices

- **Parameterized queries only**. Never concatenate user input into SQL strings.
- **Select specific columns**, not `SELECT *`. Reduces data transfer and avoids leaking sensitive columns.
- **Use pagination** for any query that could return unbounded results.
- **Avoid expensive operations** in hot paths: full table scans, `LIKE '%term%'`, complex subqueries.
- **Use database-level constraints** (NOT NULL, UNIQUE, CHECK, FOREIGN KEY) to enforce data integrity. Do not rely solely on application-level validation.
- **Soft delete** for auditable data: add `deleted_at` column instead of hard deleting. Filter with `WHERE deleted_at IS NULL`.

## Timestamps

- All tables must include `created_at` and `updated_at` columns.
- Store timestamps in UTC. Convert to local time zones only in the presentation layer.
- Use `TIMESTAMPTZ` (timestamp with time zone) in PostgreSQL.
- Use database triggers or ORM hooks to auto-update `updated_at`.

## Data Types

- Use `UUID` for primary keys in distributed systems. Use `BIGINT` auto-increment for single-database systems.
- Use `DECIMAL` for monetary values, never `FLOAT` or `DOUBLE`.
- Use `TEXT` for variable-length strings with no practical limit. Use `VARCHAR(n)` only when a specific length constraint is meaningful.
- Use `JSONB` (PostgreSQL) sparingly — only for truly schemaless data. Prefer normalized columns for structured data.

## Deep guides (read on demand, do not preload)

- `lock_timeout` vs `statement_timeout` (and why the ordering between them matters), the lock
  queue that turns a fast migration into an outage, `disable_ddl_transaction!` and the invalid
  index it can leave, retrying a lock timeout, finding the blocker with `pg_blocking_pids()`,
  row locks and advisory locks → `references/locking-and-timeouts.md`

Related, owned elsewhere — do not duplicate: which migration *operation* is safe and its
expand/contract form (add/remove/rename column, change type, add FK) →
`../db-migration/references/migration-guide.md`; index/query tuning and `EXPLAIN` →
`../performance-profiler`.
