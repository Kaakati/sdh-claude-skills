---
name: db-migration
description: Design PostgreSQL/PostGIS schemas and create safe ActiveRecord migrations with rollback plans, spatial column design, index strategy, and zero-downtime deployment patterns. Use this skill whenever someone asks to create a table, modify a schema, write a migration, design a data model, add an index, or says things like "create a migration for X", "add a column to Y", "design the database schema", "what indexes do I need", "plan the data model", or "how do I safely change this column type". Also trigger when someone mentions zero-downtime migrations, expand-and-contract pattern, backfills, PostGIS spatial columns, or large table migration strategy.
model: sonnet
---

# Database Migration

ActiveRecord migrations against PostgreSQL. Every migration must be reversible, tested, and safe
to run while the app is serving traffic.

## What actually locks — the table people get wrong

Most "unsafe migration" folklore predates PostgreSQL 11 and is now wrong in the expensive
direction: it makes teams hand-roll batched backfills for operations that are already free, and
leaves them unprepared for the ones that aren't.

| Operation | Rewrites the table? | Postgres says |
|---|---|---|
| `ADD COLUMN` with a **constant** default | **No** | *"the default value is evaluated at the time of the statement and the result stored in the table's metadata… making the `ALTER TABLE` very fast even on large tables"* |
| `ADD COLUMN` with a **volatile** default (`clock_timestamp()`), a stored generated column, or an identity column | **Yes** | *"will cause the entire table and its indexes to be rewritten"* |
| `ALTER COLUMN TYPE` | **Usually yes** | *"normally cause the entire table and its indexes to be rewritten"* — unless binary-coercible |
| `SET NOT NULL` | No rewrite, but **a full scan** | *"requires scanning the table to verify that existing rows meet the constraint"* |
| `CREATE INDEX` (non-concurrent) | No rewrite, but blocks **writes** for the whole build | — |

**The lock is the risk, not the rewrite.** A scan or a rewrite holds `ACCESS EXCLUSIVE`, which
blocks `SELECT` — and a migration *waiting* for that lock queues every query behind it. Every
migration therefore sets `lock_timeout`; that mechanism is owned by
`../std-database/references/locking-and-timeouts.md` and is not repeated here.

## Pre-flight

1. **Table size.** Under ~100k rows almost nothing here matters — don't build a two-phase
   deploy for a lookup table. Over ~1M, assume every scan is an outage risk.
2. **Will it scan, rewrite, or neither?** Use the table above. If you can't say, you're not
   ready to write it.
3. **Dependencies**: foreign keys, views, triggers, and Panko serializers referencing the column.
4. **Is the rollback real?** `rails db:rollback` must actually work, or the down is fiction.
5. **Backup verified restorable** — not merely present.

## Reversibility

Prefer `change`; ActiveRecord infers the inverse. When it cannot, be explicit rather than leaving
the rollback undefined:

```ruby
class BackfillOrderStatus < ActiveRecord::Migration[7.1]
  def up
    Order.unscoped.in_batches(of: 5_000) { |batch| batch.update_all(status: "pending") }
  end

  def down
    raise ActiveRecord::IrreversibleMigration   # say it, don't leave `rails db:rollback` to fail at 2am
  end
end
```

A data backfill is **not** reversible in general — the old NULLs are gone. Say so.

## Expand and contract

For any change that would break a running instance, split it across deployments. The rule that
makes it work: **at every step, both the old and the new code must run against the schema as it
exists.** During a rolling deploy, they literally do.

**Expand** (backwards compatible) → add the new thing, backfill, write to both, deploy.
**Contract** (after every instance uses the new thing) → stop writing the old, drop it, deploy.

The most common failure is skipping the wait between phases. "All instances updated" is a fact
you verify, not a minute you count.

## Separate schema from data

Schema migrations run in the deploy; **backfills do not belong there**. A `db:migrate` that
updates ten million rows holds the deploy hostage and times out the release.

- Small (<100k rows): `in_batches` inside the migration is fine.
- Large: ship the backfill as a **Sidekiq job** or a rake task, run it after deploy, and make it
  idempotent and resumable so a retry costs nothing.

## Deployment checklist

- [ ] Tested on a staging copy with production-like **row counts** (a fast migration on 1k rows tells you nothing)
- [ ] Rollback actually executed, not just written
- [ ] `lock_timeout` set (`../std-database/references/locking-and-timeouts.md`)
- [ ] Old and new application code both work against the intermediate schema
- [ ] Backfill split out of the migration if the table is large
- [ ] Backup verified restorable
- [ ] Post-migration validation query prepared

## Post-migration validation

1. Confirm the schema change landed (`\d orders`).
2. Row counts unchanged (no accidental loss).
3. App health: no `PG::UndefinedColumn` in the logs (`../log-search`).
4. Replication lag returned to normal.
5. Query performance — a new index changes plans, sometimes for the worse.

## Deep guides (read on demand, do not preload)

- Per-operation safe/unsafe with ActiveRecord: add/remove/rename column, add index, change type,
  add a foreign key without the long lock, `NOT NULL` without the scan, and batched backfills
  → `references/migration-guide.md`
- PostGIS spatial columns and JSONB patterns → `references/postgres-patterns.md`

Related, owned elsewhere — do not duplicate: `lock_timeout`/`statement_timeout`, the lock queue,
`disable_ddl_transaction!` and advisory locks → `../std-database/references/locking-and-timeouts.md`;
schema conventions, naming, and indexing rules → `../std-database`.
