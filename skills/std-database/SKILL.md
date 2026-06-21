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

- **All migrations must be reversible**. Every `up` migration must have a corresponding `down` migration:
  ```typescript
  export async function up(knex: Knex): Promise<void> {
    await knex.schema.createTable("orders", (table) => {
      table.uuid("id").primary().defaultTo(knex.fn.uuid());
      table.uuid("user_id").notNullable().references("users.id");
      table.decimal("total_amount", 10, 2).notNullable();
      table.timestamps(true, true);
    });
  }

  export async function down(knex: Knex): Promise<void> {
    await knex.schema.dropTableIfExists("orders");
  }
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
  ```typescript
  async function createOrderWithItems(order: Order, items: OrderItem[]): Promise<void> {
    await db.transaction(async (trx) => {
      const [orderId] = await trx("orders").insert(order).returning("id");
      const itemsWithOrderId = items.map((item) => ({ ...item, order_id: orderId }));
      await trx("order_items").insert(itemsWithOrderId);
    });
  }
  ```
- Set appropriate isolation levels based on consistency requirements.
- Keep transactions short — do not perform external API calls inside a transaction.
- Handle transaction rollback explicitly when using manual transaction management.

## N+1 Query Prevention

- **Never query in a loop**. Use batch queries, JOINs, or eager loading:
  ```typescript
  // BAD — N+1: one query per user
  const users = await db("users").select("*");
  for (const user of users) {
    user.orders = await db("orders").where("user_id", user.id);
  }

  // GOOD — Two queries total
  const users = await db("users").select("*");
  const userIds = users.map((u) => u.id);
  const orders = await db("orders").whereIn("user_id", userIds);
  const ordersByUser = groupBy(orders, "user_id");
  users.forEach((u) => { u.orders = ordersByUser[u.id] || []; });
  ```
- When using ORMs, configure eager loading for known associations.
- Monitor query logs in development to catch N+1 patterns early.

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
