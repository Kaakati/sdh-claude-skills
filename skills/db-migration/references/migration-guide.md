# Migration Patterns — ActiveRecord against PostgreSQL

Safe and unsafe approaches for common schema changes. "Unsafe" here means **it takes a lock long
enough to matter on a big table** — on a small table almost everything in this file is fine, and
building a two-phase deploy for a 500-row lookup table is its own kind of mistake.

Every example assumes `lock_timeout` is set —
`../../std-database/references/locking-and-timeouts.md` owns that and it is not repeated here.

---

## Add Column

**Most of the received wisdom about this operation is out of date**, and being out of date makes
teams do *more* work, not less. Postgres:

> *"When a column is added with `ADD COLUMN` and a non-volatile `DEFAULT` is specified, the
> default value is evaluated at the time of the statement and the result stored in the table's
> metadata… **making the `ALTER TABLE` very fast even on large tables**. In neither case is a
> rewrite of the table required."*

### Safe — a constant default is free

```ruby
class AddStatusToOrders < ActiveRecord::Migration[7.1]
  def change
    # Fast on ANY table size. No rewrite, no backfill loop, no two-phase dance.
    # This is a metadata change; the default materialises as rows are written.
    add_column :orders, :status, :string, default: "pending"
  end
end
```

### Unsafe — a *volatile* default rewrites the whole table

```ruby
class AddSeenAtToOrders < ActiveRecord::Migration[7.1]
  def change
    # ❌ clock_timestamp() is VOLATILE: Postgres must compute a different value per row, so
    # it "will cause the entire table and its indexes to be rewritten" — holding
    # ACCESS EXCLUSIVE for the duration. This is the case the folklore should warn about.
    add_column :orders, :seen_at, :timestamptz, default: -> { "clock_timestamp()" }
  end
end
```

Same trap: stored generated columns, identity columns, and domain types with constraints.

```ruby
# ✅ instead: add it nullable (free), then backfill out-of-band if existing rows need a value
add_column :orders, :seen_at, :timestamptz
```

### `NOT NULL` is the expensive half

`SET NOT NULL` does not rewrite, but it *"requires scanning the table to verify that existing
rows meet the constraint"* — and that scan holds `ACCESS EXCLUSIVE`. On a large table it is the
outage.

```ruby
# ❌ on a big table: a full scan under an exclusive lock
change_column_null :orders, :status, false
```

```ruby
# ✅ two migrations. A NOT VALID check constraint is instant; VALIDATE takes only a SHARE
#    UPDATE EXCLUSIVE lock, which does NOT block reads or writes.
class AddStatusCheckToOrders < ActiveRecord::Migration[7.1]
  def change
    add_check_constraint :orders, "status IS NOT NULL", name: "orders_status_null", validate: false
  end
end

class ValidateStatusCheckOnOrders < ActiveRecord::Migration[7.1]
  def change
    validate_check_constraint :orders, name: "orders_status_null"   # scans, but does not block
    # Postgres can now use the validated constraint to prove the column is NOT NULL, so this
    # is quick rather than a second full scan.
    change_column_null :orders, :status, false
    remove_check_constraint :orders, "status IS NOT NULL", name: "orders_status_null"
  end
end
```

### Rollback

```ruby
remove_column :orders, :status    # `change` infers this; data is gone either way
```

---

## Remove Column

The danger is not the `ALTER` — it is that **ActiveRecord caches the column list**. A running
instance still selects the dropped column and every query explodes with `PG::UndefinedColumn`,
including for rows it never touched.

### Safe — `ignored_columns` first, drop second

```ruby
# Deploy 1: tell ActiveRecord the column no longer exists. Ship this ALONE and wait for every
# instance to restart. This is the step people skip, and it is the whole safety.
class Order < ApplicationRecord
  self.ignored_columns += ["legacy_status"]
end
```

```ruby
# Deploy 2: now nothing references it
class RemoveLegacyStatusFromOrders < ActiveRecord::Migration[7.1]
  def change
    remove_column :orders, :legacy_status, :string   # give the type, or the rollback can't re-add it
  end
end
```

Passing the type to `remove_column` is what makes `change` reversible — without it,
`rails db:rollback` raises.

### Rollback

Re-adding the column restores the **schema**, never the **data**. If the data matters, copy it
out before the drop; a migration is not a backup.

---

## Rename Column

Never `rename_column` on a live table. It is instant and it breaks every running instance at
once — the fastest possible way to take an app down.

### Safe — expand/contract across three deploys

```ruby
# Deploy 1 — expand: add the new column (free), write to both
class AddOrderStatusToOrders < ActiveRecord::Migration[7.1]
  def change
    add_column :orders, :order_status, :string
  end
end

class Order < ApplicationRecord
  # Dual-write while both columns exist. Old instances keep reading `status`.
  before_save { self.order_status = status }
end
```

```ruby
# Backfill (out-of-band, not in the deploy)
Order.unscoped.where(order_status: nil).in_batches(of: 5_000) do |batch|
  batch.update_all("order_status = status")
  sleep 0.1     # let replication catch up
end
```

```ruby
# Deploy 2 — read from the new column, keep dual-writing.
# Deploy 3 — contract: stop writing `status`, add ignored_columns, THEN drop it.
```

Three deploys for a rename feels absurd until the alternative takes production down during a
rolling restart, when half the instances know the new name and half do not.

---

## Add Index

```ruby
class AddIndexToOrdersStatus < ActiveRecord::Migration[7.1]
  # CREATE INDEX CONCURRENTLY cannot run inside a transaction, and Rails wraps migrations in
  # one — without this line the migration simply errors.
  disable_ddl_transaction!

  def change
    add_index :orders, :status, algorithm: :concurrently
  end
end
```

```ruby
# ❌ a plain add_index blocks WRITES for the entire build — minutes on a large table
add_index :orders, :status
```

**The price of `disable_ddl_transaction!`:** the migration is no longer atomic. A failed
`CREATE INDEX CONCURRENTLY` leaves an **invalid index** behind that you must drop by hand before
retrying:

```sql
SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;
DROP INDEX CONCURRENTLY index_orders_on_status;
```

Keep such migrations to **one statement**, so "failed halfway" is a small place to be.

Index rules: index every foreign key; index what you filter, join, and sort on; put the most
selective column first in a composite; skip low-cardinality columns unless composite; drop
unused indexes — each one taxes every write.

---

## Change Column Type

> *"Changing the type of an existing column will normally cause the entire table and its indexes
> to be rewritten. As an exception… if the old type is either binary coercible to the new type…
> a table rewrite is not needed."*

### Safe — the free cases first

```ruby
# ✅ binary-coercible widening: no rewrite
change_column :orders, :code, :string           # varchar(50) -> text
change_column :orders, :quantity, :bigint       # integer -> bigint  (PG rewrites; see below)
```

Check before assuming. `varchar(n) → text` and `varchar(n) → varchar(m>n)` are free;
`integer → bigint` **does** rewrite, because the on-disk width changes.

### Safe — expand/contract for the rest

```ruby
# Deploy 1
add_column :orders, :amount_cents_v2, :bigint          # free
# dual-write in the model, backfill out-of-band in batches
# Deploy 2: read from v2
# Deploy 3: ignored_columns on the old, then drop it
```

### Unsafe

```ruby
# ❌ rewrites the table under ACCESS EXCLUSIVE — the whole table is offline for the duration
change_column :orders, :amount_cents, :bigint
```

Fine on 10k rows. An outage on 50M.

---

## Add Foreign Key

A plain `add_foreign_key` validates every existing row **while holding a lock on both tables** —
including the one you are not thinking about.

### Safe — two steps

```ruby
class AddUserFkToOrders < ActiveRecord::Migration[7.1]
  def change
    # Instant: the constraint applies to NEW rows only. Existing rows are not checked yet.
    add_foreign_key :orders, :users, validate: false
  end
end

class ValidateUserFkOnOrders < ActiveRecord::Migration[7.1]
  def change
    # Scans, but takes only SHARE UPDATE EXCLUSIVE — reads and writes keep flowing.
    validate_foreign_key :orders, :users
  end
end
```

### Unsafe

```ruby
add_foreign_key :orders, :users     # ❌ validates everything, locking both tables
```

The same `validate: false` → `validate_*` split works for check constraints, and it is the
general shape of "add the rule now, prove it later."

---

## Backfills

```ruby
# ❌ in the migration: holds the deploy, times out the release, one giant transaction
Order.update_all(status: "pending")
```

```ruby
# ✅ a job: batched, throttled, idempotent, resumable
class BackfillOrderStatusJob
  include Sidekiq::Job

  def perform
    Order.unscoped.where(status: nil).in_batches(of: 5_000) do |batch|
      batch.update_all(status: "pending")
      sleep 0.1        # replication lag is the thing that bites at 3am
    end
  end
end
```

`unscoped` matters: a `default_scope` (soft delete, tenancy) silently skips rows, and you find
out when the `NOT NULL` validation fails on the ones it missed.

`update_all` skips validations and callbacks **by design** — it is one `UPDATE` per batch rather
than N round trips. If the backfill genuinely needs callbacks, it is not a backfill; it is a data
migration that belongs in application code with its own tests.

---

## Large tables

- **Batch 1k–10k rows.** Bigger batches hold locks longer and bloat WAL; smaller ones are all
  overhead.
- **Watch replication lag**, not just the primary. A backfill that outruns the replicas breaks
  every read-replica query.
- **`pg_repack`** reclaims bloat without a long lock when a rewrite is unavoidable.
- **Resumable beats fast.** `where(status: nil)` means a crashed backfill can simply be re-run.
