# Locking & Timeouts — why a "safe" migration took the site down

Load-bearing rules restated (hold even if you read nothing else):

1. **Every migration sets `lock_timeout`.** A migration that *waits* for a lock is more dangerous
   than one that fails.
2. **`ALTER TABLE` blocks `SELECT`.** Postgres: *"Only an `ACCESS EXCLUSIVE` lock blocks a
   `SELECT`"* — and `ALTER TABLE` takes exactly that.
3. **Which operation is safe is owned by `../db-migration/references/migration-guide.md`.** This
   file is about the lock you take *while doing it*.

---

## The outage this file exists to prevent

The migration was reviewed. It uses the safe form. It adds a nullable column — an operation that
completes in milliseconds. It still took the site down for four minutes.

Here is the mechanism, and every step is documented:

1. A reporting query has been running for 90 seconds. It holds `ACCESS SHARE` on `orders`.
2. Your migration runs `ALTER TABLE orders ADD COLUMN …`, which needs `ACCESS EXCLUSIVE`. That
   mode *"conflicts with locks of all modes"*, so it cannot start. It **waits** — and Postgres is
   explicit that *"a transaction seeking either a table-level or row-level lock will wait
   indefinitely for conflicting locks to be released."*
3. **Every query that arrives after it queues behind it.** Lock requests are granted in order, so
   a normal `SELECT` — which would happily share with the reporting query — now waits for your
   `ALTER`, which is waiting for the report.
4. Your fast, safe migration is now a full outage on `orders`, and it will stay that way for as
   long as the *reporting query* runs. You are not the slow thing; you are the thing that turned
   someone else's slow thing into everyone's outage.

The fix is not a better `ALTER`. It is: **never wait.**

## `lock_timeout` — the one line every migration needs

Postgres, exactly:

> **`lock_timeout`** — *"Abort any statement that waits longer than the specified amount of time
> while attempting to acquire a lock on a table, index, row, or other database object."* … *"The
> time limit applies separately to each lock acquisition attempt."* … *"A value of zero (the
> default) disables the timeout."*

**Default zero means every migration you have ever written waits forever.**

```ruby
# ✅ config/initializers/migration_lock_timeout.rb — apply to every migration, not by memory
ActiveSupport.on_load(:active_record) do
  ActiveRecord::Migration.class_eval do
    # 5s: long enough to get the lock on a quiet table, short enough that failing is
    # cheaper than queueing. Failing is the GOOD outcome — it means nothing queued.
    LOCK_TIMEOUT = "5s"

    def with_lock_timeout(&block)
      connection.execute("SET lock_timeout = '#{LOCK_TIMEOUT}'")
      yield
    ensure
      connection.execute("SET lock_timeout = DEFAULT")
    end
  end
end
```

```ruby
# ✅ or per migration, explicitly
class AddStatusToOrders < ActiveRecord::Migration[7.1]
  def change
    # Aborts rather than queues. Re-run it in a minute; nothing broke.
    execute "SET lock_timeout = '5s'"
    add_column :orders, :status, :string
  end
end
```

**Do not set it in `postgresql.conf`.** Postgres: *"Setting `lock_timeout` in `postgresql.conf`
is not recommended because it would affect all sessions."*

### The interaction that makes people think it does nothing

> *"Note that if `statement_timeout` is nonzero, it is rather pointless to set `lock_timeout` to
> the same or larger value, since the statement timeout would always trigger first."*

So `lock_timeout` **must be smaller than** `statement_timeout`, or the statement dies first and
you never see the lock error you were trying to catch. If your app sets
`statement_timeout = 5s` and your migration sets `lock_timeout = 5s`, the lock timeout is
decoration.

| Setting | Aborts | Set it |
|---|---|---|
| `lock_timeout` | A statement **waiting for a lock** | Per migration (small: 5s) |
| `statement_timeout` | Any statement **taking too long** | Per app session (e.g. 15s), never globally |

## Bad — the migration that waits

```ruby
class AddIndexToOrders < ActiveRecord::Migration[7.1]
  def change
    # ❌ two independent disasters:
    #  1. no lock_timeout -> waits indefinitely, queueing every query behind it
    #  2. a plain CREATE INDEX takes a lock that blocks writes for the whole build
    add_index :orders, :user_id
  end
end
```

## Good — concurrent, and unwilling to wait

```ruby
class AddIndexToOrders < ActiveRecord::Migration[7.1]
  # CREATE INDEX CONCURRENTLY cannot run inside a transaction, and Rails wraps migrations
  # in one by default. Without this line the migration simply errors.
  disable_ddl_transaction!

  def change
    execute "SET lock_timeout = '5s'"
    add_index :orders, :user_id, algorithm: :concurrently
  end
end
```

**`disable_ddl_transaction!` has a price you must accept knowingly:** the migration is no longer
atomic. If it fails halfway, nothing rolls back — a failed `CREATE INDEX CONCURRENTLY` leaves an
**invalid index** behind that you must drop by hand before retrying. That is the trade for not
locking out writes; make it deliberately, and keep such migrations to one statement so "halfway"
is a small place to be.

## Retrying is the point

A `lock_timeout` failure is not an error to escalate — it is the system working. Retry:

```ruby
# ✅ try, back off, try again. Each attempt is harmless because each one refuses to queue.
class AddStatusToOrders < ActiveRecord::Migration[7.1]
  def change
    attempts = 0
    begin
      attempts += 1
      execute "SET lock_timeout = '5s'"
      add_column :orders, :status, :string
    rescue ActiveRecord::LockWaitTimeout
      raise if attempts >= 5
      say "lock busy, retrying (#{attempts}/5)"
      sleep 10
      retry
    end
  end
end
```

Five short attempts across a minute will win against transient traffic and will *correctly* fail
against a genuinely long-running query — at which point the answer is to find that query, not to
wait for it.

## Find what you are waiting for

```sql
-- Who is blocking whom, right now. Run this the moment a migration hangs.
SELECT blocked.pid          AS blocked_pid,
       blocked.query        AS blocked_query,
       blocking.pid         AS blocking_pid,
       blocking.query       AS blocking_query,
       now() - blocking.query_start AS blocking_duration
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```

`pg_blocking_pids()` names the culprit directly. The usual answer is a forgotten analytics query,
an idle-in-transaction connection from a crashed process, or a `psql` someone left open.

```sql
-- Idle in transaction: holds locks, does nothing, blocks everything. Hunt these.
SELECT pid, state, now() - state_change AS idle_for, query
FROM pg_stat_activity
WHERE state = 'idle in transaction' AND now() - state_change > interval '1 minute';
```

## Application-level locking

Same principle in the app: never wait forever, and hold the lock for as little as possible.

```ruby
# ✅ row lock, short critical section
order.with_lock do            # SELECT ... FOR UPDATE, released at the end of the block
  raise AlreadyPaid if order.paid?
  order.update!(status: "paid")
end
```

```ruby
# ✅ "only one of these runs at a time", cluster-wide — for a Sidekiq job that must not
# double-run. An advisory lock is NOT tied to a row, so it works when there is no row to lock.
ActiveRecord::Base.with_advisory_lock("nightly-invoice-run", timeout_seconds: 0) do
  Invoices::NightlyRun.new.call
end
```

`timeout_seconds: 0` means *"if someone else holds it, do not wait — just don't run."* For a
periodic job, skipping this tick is correct; queueing ten workers behind one lock is not.

> Deadlocks are Postgres detecting that two transactions each hold what the other wants. It kills
> one — that is a **retryable** error, not a bug to fix by locking harder. Reduce the odds by
> always acquiring locks in a **consistent order** (e.g. always the lower `id` first).
