---
name: std-database
description: "Database design and conventions for ANY schema, model, association, migration, index, or query change — Rails/ActiveRecord, Django ORM, SQLAlchemy 2.0 + Alembic, raw SQL, PostgreSQL/PostGIS, pgvector. Relationships are designed in Rails association terms (has_one, has_many, has_many :through, polymorphic), and the plan runs relationships → query/index plan → migration before any code is written."
paths:
  - "**/migrations/**"
  - "**/migrate/**"
  - "**/models/**"
  - "**/models.py"
  - "**/alembic/**"
  - "**/db/**"
  - "**/repositories/**"
  - "**/*.sql"
---

# Database Standards

Rules for designing schemas, relationships, indexes, and queries — and the plan that comes before
the migration. ActiveRecord spellings lead; Django ORM and SQLAlchemy 2.0 follow the same rules
with different spellings.

**Enforcement**: code-reviewer skill (Step 5: Performance Check, Step 8: Stack-Specific Checks),
db-migration skill (migration safety protocol), `migration-validator.py` and
`database-design-checker.py` hooks, dangerous-command-blocker.py hook (blocks unfiltered DELETE/DROP).

## Plan before you change the schema

A migration is the last step of a design. For a new table, association, or query path on a table
that is or will be large, work in this order — the template is `references/design-and-query-plan.md`:

1. **Relationships, in association terms** — `Organization has_many :memberships`,
   `User has_many :organizations, through: :memberships`. The association decides where each
   foreign key lives before any column exists (Relationships, below). Before naming a new
   entity, look it up — `arch_index.py --name <Entity>` (the `orthogonality` skill) shows whether
   the concept already has a model or table, and in which context.
2. **Access patterns → the query/index plan** — the top queries per table, their frequency and
   latency budget, and the index each needs. An index no named query uses is a write tax.
3. **Constraints and data types** — `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys with a chosen
   `on_delete`; column types per Data Types, below.
4. **The migration plan** — which operations lock, which need expand/contract, where the backfill
   runs → the `db-migration` skill (`../db-migration/references/migration-guide.md`,
   `../db-migration/references/migration-guide-python.md`).
5. **Verify** — `EXPLAIN (ANALYZE, BUFFERS)` on every planned query at production-like row counts,
   before and after, plus an N+1 check with the query count pinned in a test.

## Relationships

| Relationship | Rails association | Foreign key lives on | Its index | Its constraint |
|---|---|---|---|---|
| One-to-one | `has_one` / `belongs_to` | the dependent side (`profiles.user_id`) | **unique** `user_id` | FK, `NOT NULL` |
| One-to-many | `has_many` / `belongs_to` | the many side (`projects.organization_id`) | `organization_id`, leading any composite | FK, `NOT NULL`, a chosen `on_delete` |
| Many-to-many | `has_many :through` a join model | the join model (`memberships`), both keys | unique `[user_id, organization_id]` + `organization_id` | two FKs, both `NOT NULL` |
| Polymorphic | `belongs_to :subject, polymorphic: true` | `subject_type` + `subject_id` | `[subject_type, subject_id]` | **none possible** — orphan risk |
| Self-referential | `belongs_to :manager, class_name: "User"` | the same table (`users.manager_id`) | `manager_id` | FK to itself, `CHECK (manager_id <> id)` |

- **Never `has_and_belongs_to_many`** — a join without a model cannot carry a role, a timestamp, or
  a validation, and the day it needs one is a data migration.
- **PostgreSQL does not index foreign keys.** `t.references` and Django's `ForeignKey` add one;
  SQLAlchemy does not — `mapped_column(ForeignKey(...), index=True)`.
- **`belongs_to` is required by default, but only as a validation** — pair it with `null: false`
  and a real foreign key, or `insert_all`, `update_columns`, and raw SQL write orphans.
- **Polymorphic only for open type sets.** A small closed set gets separate nullable foreign keys
  plus a `CHECK`, or `delegated_type`.
- **Roles live on the membership (user × organization), never on `users`.**
- **Same-type trees** (folders, org units, categories) default to an adjacency list plus one guarded
  recursive query. Use `ancestry`, `closure_tree`, or `ltree` only when the plan shows the walk over
  budget, and never start a new nested set → `references/hierarchies.md`. A fixed chain of different
  models (region → site → asset) is not a tree; it uses plain associations.

## Migration Safety

- **Every migration sets `lock_timeout` (e.g. 5s).** The default is **0 — wait forever**, and a
  migration that *waits* is more dangerous than one that fails: `ALTER TABLE` needs
  `ACCESS EXCLUSIVE`, which blocks `SELECT`, and every query arriving after it queues behind it.
  A millisecond-fast, correctly-written migration becomes a full table outage for as long as some
  unrelated slow query runs. Failing is the good outcome — retry it. → `references/locking-and-timeouts.md`
- **All migrations must be reversible.** Prefer `change` — ActiveRecord infers the inverse. When it
  cannot (raw SQL, data changes), write `up`/`down` explicitly; Django gives every `RunPython` a
  reverse, Alembic every revision a real `downgrade()`.
- **A backfill is data, not schema.** On a small table (under ~100k rows) batching inside the
  migration is fine — and say it is irreversible rather than leaving the rollback undefined:
  ```ruby
  class BackfillOrderStatus < ActiveRecord::Migration[7.1]
    def up
      Order.unscoped.where(status: nil).in_batches(of: 5_000).update_all(status: "pending")
    end

    def down
      raise ActiveRecord::IrreversibleMigration   # the old NULLs are gone; say so
    end
  end
  ```
  On a large table the backfill is an idempotent, resumable Sidekiq job (a Celery task on the
  Python stack) run after the deploy — the schema/data split is owned by the `db-migration` skill.
- **No destructive migrations without a data backup plan.** Before dropping tables or columns or
  changing types: document the data impact in the migration, make sure a backup or data-migration
  step exists, and split risky changes (add new column → migrate data → drop old column).
- **Test migrations** in staging with production-like row counts; never modify production by hand.
  Name them for what they do: `create_orders`, `add_status_to_orders`.

## Naming Conventions

- **Tables**: `snake_case`, plural — `users`, `order_items`, `audit_logs`.
- **Columns**: `snake_case` — `first_name`, `created_at`, `is_active`.
- **Primary keys**: `id` (UUID preferred over auto-increment for distributed systems).
- **Foreign keys**: `referenced_table_singular_id` — `user_id`, `order_id`.
- **Indexes**: the Rails default, `index_<table>_on_<columns>` — `index_users_on_email`,
  `index_orders_on_user_id_and_created_at`. Let `add_index` generate it; pass `name:` only past
  PostgreSQL's 63-byte identifier limit. Django caps index names at 30 characters — keep the
  table-then-columns order and abbreviate; Alembic follows the `MetaData` naming convention.
- **Check constraints**: `chk_<table>_<description>` — `chk_orders_positive_amount`.
- **Booleans**: Prefix with `is_` or `has_` — `is_active`, `has_verified_email`.

## Indexing

- **Index every foreign key and every column a planned query filters, joins, or sorts on** — the
  query plan decides, not a guess.
- **Composite order: equality columns first, range and sort columns last.** `(user_id, created_at)`
  serves `WHERE user_id = ? ORDER BY created_at DESC` and `user_id` alone — never `created_at`
  alone. The query shape decides the order, not column selectivity.
- **Pick the type for the operator**: btree for equality, range, and sort; partial for the subset
  queries actually read (`WHERE deleted_at IS NULL`); covering (`INCLUDE`) for an index-only scan
  on a hot path; GIN for JSONB containment and trigram search; GiST for PostGIS; HNSW for pgvector.
- **Do not over-index** — every index is maintained on every insert and every update of its
  columns. An index on `(a)` beside one on `(a, b)` is a duplicate; drop what
  `pg_stat_user_indexes` shows is never scanned.
- **Validate with `EXPLAIN (ANALYZE, BUFFERS)`** on the planned query →
  `references/design-and-query-plan.md`. Building the index without blocking writes is the
  `db-migration` skill's.

## Transactions

- **Wrap multi-table writes in one transaction**, at the service boundary:
  ```ruby
  # app/services/orders/create.rb
  ActiveRecord::Base.transaction do
    order = Order.create!(user:, total_amount:)
    order.line_items.insert_all!(items)          # one statement, not N
  end
  ```
- **Keep transactions short — never make an HTTP call inside one.** Row locks are held for as long
  as the slowest thing in the block: a payment API that hangs for 30s holds them for 30s, and
  everything touching those rows queues. Call out first, then open the transaction to record it.
- **`create!` / `save!`, not `create` / `save`, inside a transaction.** The non-bang forms return
  `false`, the block completes, nothing rolls back, and half the operation commits — the most
  common way a Rails transaction silently does nothing.
- **`after_commit`, not `after_save`,** for anything the outside world sees (a Sidekiq job, a
  Centrifugo publish) — a job enqueued inside the transaction can run before the row exists.

## N+1 Query Prevention

- **Never query in a loop** — eager-load the association:
  ```ruby
  # BAD — one query per user; invisible with 10 rows in development
  User.all.each { |user| user.orders.each { |o| puts o.total_amount } }

  # GOOD — two queries total
  User.includes(:orders).each { |user| user.orders.each { |o| puts o.total_amount } }
  ```
- **`includes` vs `preload` vs `eager_load`** — `preload` always issues a separate query;
  `eager_load` always LEFT JOINs; `includes` picks, and joins when a hash condition names the
  association. A SQL-string condition on it needs `references`, or you get a missing-column error:
  `User.includes(:orders).where("orders.status = ?", "paid").references(:orders)`.
- **Serializers are where N+1 hides.** Panko does not eager-load: a `has_many` in a serializer
  fires a query per record unless the controller's scope already included it.
- **Catch it before production** — `bullet` in development, `strict_loading` on associations that
  must never lazy-load, a pinned query count in the test. Python spellings (`select_related`,
  `prefetch_related`, `selectinload`, `lazy="raise"`) → `std-python-performance`.

## Query Best Practices

- **Parameterized queries only**. Never concatenate user input into SQL strings.
- **Select specific columns**, not `SELECT *` — less data over the wire, no leaked sensitive columns.
- **Paginate every query that could return unbounded results** — cursor-based for deep lists; the
  response contract is `std-api-design`'s.
- **Avoid expensive operations in hot paths**: full table scans, `LIKE '%term%'` without a trigram
  index, complex subqueries.
- **Database-level constraints** (NOT NULL, UNIQUE, CHECK, FOREIGN KEY) enforce integrity;
  application validations alone do not.
- **Soft delete** auditable data: a `deleted_at` column, filtered with `WHERE deleted_at IS NULL`
  and backed by a partial index on the same predicate.

## Timestamps

- Every table has `created_at` and `updated_at` as `TIMESTAMPTZ`, stored in UTC; convert to local
  time only in the presentation layer.
- Let the ORM maintain `updated_at` (`t.timestamps`, `auto_now`, `onupdate=`), or a trigger when
  raw SQL writes the table.

## Data Types

- `UUID` primary keys in distributed systems; `BIGINT` auto-increment for single-database systems.
- `DECIMAL` for money, never `FLOAT` or `DOUBLE`.
- `TEXT` for variable-length strings; `VARCHAR(n)` only when the length limit is a real rule.
- `JSONB` sparingly — only for truly schemaless data. A key you filter, sort, join, or constrain is
  a column.
- **PostGIS**: `geography` (SRID 4326) when distances must come back in meters, with a GiST index —
  spatial queries, JSONB, recursive CTEs, and partitioning → `../db-migration/references/postgres-patterns.md`.
- **pgvector**: `vector(n)` with the dimension pinned to the embedding model, and an HNSW index
  whose operator class matches the query's distance operator; embedding conventions are
  `std-python-ai-ml`'s.

## Deep guides (read on demand, do not preload)

- The plan to fill in before a migration — entities, relationship map, top queries with frequency
  and latency budget, the index plan (btree / partial / covering / GIN / GiST / HNSW), constraints,
  volume and growth, migration steps with lock level and expand/contract phase, backfill,
  rollback, `EXPLAIN (ANALYZE, BUFFERS)` before and after, and the bottleneck checklist →
  `references/design-and-query-plan.md`
- Each relationship in code — association, migration, the indexes its queries need, `dependent:`
  vs `on_delete` at scale, polymorphic alternatives, self-referential trees and graphs,
  `inverse_of` / `counter_cache` / `touch` / `strict_loading`, the users ↔ organizations
  memberships example, and the Django / SQLAlchemy mapping → `references/relationships.md`
- Same-type trees: the decision table (adjacency list + recursive CTE, `ancestry`, `ltree`,
  `closure_tree`, why never nested sets), the guarded walk queries with `CYCLE` and a depth cap,
  Rails and Python library picks with maintenance status, index and write cost per storage, and
  the read models (counter caches, materialized views, `asOf`) behind overview counts →
  `references/hierarchies.md`
- `lock_timeout` vs `statement_timeout` (and why the ordering between them matters), the lock
  queue that turns a fast migration into an outage, `disable_ddl_transaction!` and the invalid
  index it can leave, retrying a lock timeout, finding the blocker with `pg_blocking_pids()`,
  row locks and advisory locks → `references/locking-and-timeouts.md`

Related, owned elsewhere — do not duplicate. **This skill owns the design-time query/index plan.**
Which migration *operation* is safe, the lock it takes, and its expand/contract rollout →
`../db-migration/references/migration-guide.md` (ActiveRecord) and
`../db-migration/references/migration-guide-python.md` (Django, Alembic); diagnosing a slow query
already in production → `../performance-profiler`; PostGIS and JSONB query patterns →
`../db-migration/references/postgres-patterns.md`; Python ORM query spellings and bulk operations
→ `std-python-performance`; what each role may do → `../access-control-designer`; the pagination
contract → `std-api-design`; the API shape for navigable hierarchies (levels, `ancestors`, scoped
counts, per-level authorization) → `../std-api-design/references/drill-down-resources.md`; a
second table for an existing concept, a column copying a fact reachable through a foreign key
(`orders.customer_email` beside `customers.email`), and read-model and denormalization
declarations → `../orthogonality/references/database-duplication.md`.
