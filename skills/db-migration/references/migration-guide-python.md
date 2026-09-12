# Migration Patterns — Django migrations and Alembic against PostgreSQL

The Python edition of `migration-guide.md`: the same database, the same locks, the same rules. The
lock is the risk, not the rewrite, and which operation scans or rewrites is the table in the
`db-migration` skill body. What changes is how far the ORM hides the SQL — Django and Alembic will
both emit a write-blocking `CREATE INDEX` from a line that never says "index".

Load-bearing rules restated (hold even if you read nothing else):

1. **Read the SQL, not the operation.** `python manage.py sqlmigrate <app> <migration>`;
   `alembic upgrade <from_rev>:<to_rev> --sql`.
2. **Every migration runs with `lock_timeout` set.** The mechanism is owned by
   `@skills/std-database/references/locking-and-timeouts.md`; the Python wiring is below.
3. **A concurrent index build cannot run inside a transaction** — Django `atomic = False`, Alembic
   `autocommit_block()` — and a failed one leaves an invalid index to drop by hand.
4. **A large backfill is a Celery task run after the deploy**, never a `RunPython` or an
   `op.execute` inside the migration.
5. **Alembic `env.py` sets `transaction_per_migration=True`.** The default runs every revision one
   `alembic upgrade head` applies in a single transaction, so a lock one revision takes is still
   held while the next one runs.

---

## Read the SQL first

```bash
python manage.py sqlmigrate orders 0043        # Django: the exact SQL of one migration
alembic upgrade <from_rev>:<to_rev> --sql       # Alembic offline mode: SQL for a revision range
```

A Django `AddField` for a `ForeignKey` is **three** statements: the column, the foreign-key
constraint, and a plain `CREATE INDEX` that blocks writes for the whole build. On a small table
that is fine. On a large one it is the outage, and nothing in the migration file mentions an index.

Community linters read the SQL for you — `django-migration-linter` for Django, `squawk` over
Alembic's `--sql` output. Run one in CI beside `makemigrations --check` / `alembic check`.

---

## `lock_timeout` — set it on the migrating session, not per file

Per-file settings get forgotten, and Django adds a sharper trap: rolling back unapplies operations
in **reverse order**, so a `RunSQL("SET …")` placed first runs *last* on the way down — after the
operation it was meant to protect. Set it where the connection is made: one place, every
migration, both directions.

**Django** — a settings module used only by the deploy's migrate step
(`DJANGO_SETTINGS_MODULE=config.settings.migrate python manage.py migrate`):

```python
# config/settings/migrate.py
from .prod import *  # noqa: F403

DATABASES["default"]["OPTIONS"] = {  # noqa: F405
    **DATABASES["default"].get("OPTIONS", {}),  # noqa: F405
    # libpq applies these to the migrating session only; the app's sessions are untouched.
    # statement_timeout=0 so a CONCURRENTLY build is not killed; lock_timeout still refuses to queue.
    "options": "-c lock_timeout=5s -c statement_timeout=0",
}
```

**Alembic** — the engine `env.py` builds (the async template, asyncpg), and the
`context.configure()` call that runs on its connection:

```python
connectable = async_engine_from_config(
    config.get_section(config.config_ini_section, {}),
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
    # Every session this engine opens — upgrade AND downgrade.
    connect_args={"server_settings": {"lock_timeout": "5s", "statement_timeout": "0"}},
)
```

```python
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Each revision commits on its own, so no lock or autocommit_block spans two revisions.
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()
```

A sync psycopg engine takes the libpq form instead:
`connect_args={"options": "-c lock_timeout=5s -c statement_timeout=0"}`.

`transaction_per_migration` defaults to `False`; `True` means "nest each migration script in a
transaction rather than the full series of migrations to run" (Alembic —
`EnvironmentContext.configure`). Pass it in `run_migrations_offline()` too, so
`alembic upgrade --sql` prints the transactions the online run will use.

For one atomic migration, `SET LOCAL lock_timeout = '5s'` as its first statement scopes the
setting to that migration's transaction — forwards only, for the reason above. Either way,
`lock_timeout` must stay below any non-zero `statement_timeout` or it never fires, and a
lock-timeout failure is the system working: re-run the migration.

---

## Concurrent indexes

### Django — `AddIndexConcurrently` with `atomic = False`

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block, and Django wraps every
    # PostgreSQL migration in one. Without this line the migration errors.
    atomic = False

    dependencies = [("orders", "0042_order_placed_at")]
    operations = [
        AddIndexConcurrently(
            "order",
            models.Index(fields=["organization", "placed_at"], name="index_orders_on_org_placed_at"),
        ),
    ]
```

Generate it with `makemigrations` as usual, then swap `AddIndex` for `AddIndexConcurrently` and add
`atomic = False` — the migration state is identical; only the SQL changes. `RemoveIndexConcurrently`
is the same swap for `RemoveIndex`. Django caps index names at 30 characters, hence the
abbreviation.

**One operation per non-atomic migration.** Without a transaction, a failure after the first
operation leaves it applied but the migration unrecorded, and the re-run fails on "already
exists". A failed concurrent build also leaves an **invalid index** behind — find and drop it as in
`migration-guide.md` (Add Index) before retrying.

### Alembic — `postgresql_concurrently=True` inside `autocommit_block()`

```python
def upgrade() -> None:
    # autocommit_block() commits the open transaction, runs this outside one, then begins anew.
    with op.get_context().autocommit_block():
        op.create_index("index_orders_on_organization_id_placed_at", "orders",
                        ["organization_id", "placed_at"], postgresql_concurrently=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index("index_orders_on_organization_id_placed_at", table_name="orders",
                      postgresql_concurrently=True)
```

**Alembic runs a whole `upgrade head` in one transaction by default**, so the commit that
`autocommit_block()` makes also commits every revision before it in that run — a later failure can
no longer roll them back. Pass `transaction_per_migration=True` to `context.configure()` so each
revision commits on its own. Give the index the same name the model declares, or autogenerate
proposes dropping and recreating it.

---

## A foreign key on a large table

### Django — `SeparateDatabaseAndState`

Django's state gets the real field; the database gets the safe steps, one migration each, so every
lock is brief and every scan non-blocking.

```python
# 0044 — state: the whole ForeignKey. Database: a bare nullable column (metadata only).
migrations.SeparateDatabaseAndState(
    state_operations=[
        migrations.AddField("order", "coupon", models.ForeignKey(
            "billing.Coupon", null=True, on_delete=models.PROTECT, related_name="orders")),
    ],
    database_operations=[
        migrations.RunSQL("ALTER TABLE orders_order ADD COLUMN coupon_id bigint NULL",
                          reverse_sql="ALTER TABLE orders_order DROP COLUMN coupon_id"),
    ],
)
```

```python
# 0045 — atomic = False, alone: the index Django would have built, without the write lock.
migrations.RunSQL(
    "CREATE INDEX CONCURRENTLY orders_order_coupon_id_idx ON orders_order (coupon_id)",
    reverse_sql="DROP INDEX CONCURRENTLY orders_order_coupon_id_idx",
)

# 0046 — the constraint, checked for new rows only: instant.
migrations.RunSQL(
    "ALTER TABLE orders_order ADD CONSTRAINT orders_order_coupon_id_fk "
    "FOREIGN KEY (coupon_id) REFERENCES billing_coupon (id) DEFERRABLE INITIALLY DEFERRED NOT VALID",
    reverse_sql="ALTER TABLE orders_order DROP CONSTRAINT orders_order_coupon_id_fk",
)

# 0047 — its own migration, so its own transaction: scans under SHARE UPDATE EXCLUSIVE while
# reads and writes keep flowing.
migrations.RunSQL("ALTER TABLE orders_order VALIDATE CONSTRAINT orders_order_coupon_id_fk",
                  reverse_sql=migrations.RunSQL.noop)
```

`DEFERRABLE INITIALLY DEFERRED` matches what Django generates for its own foreign keys, so the
hand-written constraint behaves the same inside transactions. On a small table, skip all four —
the plain `AddField` is fine.

### Alembic

```python
def upgrade() -> None:
    op.add_column("orders", sa.Column("coupon_id", sa.BigInteger(), nullable=True))
    op.execute(
        "ALTER TABLE orders ADD CONSTRAINT fk_orders_coupon_id_coupons "
        "FOREIGN KEY (coupon_id) REFERENCES coupons (id) NOT VALID"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP CONSTRAINT fk_orders_coupon_id_coupons")
    op.drop_column("orders", "coupon_id")
```

The concurrent index is its own revision (above), and validation a third —
`op.execute("ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_coupon_id_coupons")` with a no-op
`downgrade()` — and, with `transaction_per_migration=True`, its own transaction, so its scan runs
under `SHARE UPDATE EXCLUSIVE` with no stronger lock held. A revision is not a transaction by
itself: without that setting, only the index revision's `autocommit_block()` commit happens to
separate the validation from the `ADD COLUMN` lock. The model then declares
`mapped_column(ForeignKey("coupons.id"), index=True)`, so the model and the database agree.

---

## `NOT NULL` without the long lock

The shape is ActiveRecord's (`migration-guide.md`, "`NOT NULL` is the expensive half"): a
`NOT VALID` CHECK is instant, validating it in a later transaction scans without blocking, and
PostgreSQL then uses the validated CHECK to skip the scan `SET NOT NULL` would otherwise make under
`ACCESS EXCLUSIVE`.

### Django — `AddConstraintNotValid` → `ValidateConstraint`

```python
from django.contrib.postgres.operations import AddConstraintNotValid, ValidateConstraint

# 0048 — the model's Meta.constraints gains the CheckConstraint in the same change.
# (condition= on Django 5.1+; check= before it.)
operations = [
    AddConstraintNotValid("order", models.CheckConstraint(
        condition=models.Q(status__isnull=False), name="chk_orders_status_not_null")),
]

# 0049 — the model drops the CheckConstraint and sets null=False.
operations = [
    ValidateConstraint("order", name="chk_orders_status_not_null"),
    migrations.AlterField("order", "status", models.CharField(max_length=20)),
    migrations.RemoveConstraint("order", name="chk_orders_status_not_null"),
]
```

When `makemigrations` offers a one-off default for existing NULL rows, choose to handle them
yourself — the backfill already did. A one-off default becomes an `UPDATE` over the whole table
inside this migration.

### Alembic

```python
# revision A
def upgrade() -> None:
    op.execute("ALTER TABLE orders ADD CONSTRAINT chk_orders_status_not_null "
               "CHECK (status IS NOT NULL) NOT VALID")


def downgrade() -> None:
    op.execute("ALTER TABLE orders DROP CONSTRAINT chk_orders_status_not_null")


# revision B
def upgrade() -> None:
    op.execute("ALTER TABLE orders VALIDATE CONSTRAINT chk_orders_status_not_null")
    op.alter_column("orders", "status", nullable=False)
    op.execute("ALTER TABLE orders DROP CONSTRAINT chk_orders_status_not_null")


def downgrade() -> None:
    # Reverse order — and put the constraint back, or revision A's downgrade has nothing to drop.
    op.execute("ALTER TABLE orders ADD CONSTRAINT chk_orders_status_not_null "
               "CHECK (status IS NOT NULL) NOT VALID")
    op.alter_column("orders", "status", nullable=True)
```

**Revision A and revision B must commit separately.** `ADD CONSTRAINT … CHECK … NOT VALID` takes
`ACCESS EXCLUSIVE`, and only a commit releases it. `transaction_per_migration=True` (the `env.py`
above) guarantees that commit. Without it, one `alembic upgrade head` that applies both holds A's
`ACCESS EXCLUSIVE` lock through B's `VALIDATE` scan, blocking every read and write on `orders` for
the whole scan. Django needs no setting: it runs each atomic migration in its own transaction.

---

## `RunPython` — always with a reverse

```python
def backfill_status(apps, schema_editor):
    Order = apps.get_model("orders", "Order")   # the historical model — never an import
    Order.objects.filter(status__isnull=True).update(status="pending")


class Migration(migrations.Migration):
    dependencies = [("orders", "0047_validate_coupon_fk")]
    operations = [
        # noop reverse: the values stay, and rolling the schema back past this still works.
        migrations.RunPython(backfill_status, reverse_code=migrations.RunPython.noop),
    ]
```

- **`apps.get_model`, never an import.** An imported model is today's class; the migration runs
  against the schema as of *this* migration, and a field added later breaks it for anyone
  migrating from scratch.
- **No `reverse_code` turns the migration into a wall** — `migrate` refuses to roll back past it.
  Give it `RunPython.noop` when leaving the data is correct, a real inverse when it is not.
- **Small tables only.** It runs inside the migration's transaction; a large table's backfill is
  the Celery task below. A schema change and a backfill never share a migration (`std-django`).

---

## `SeparateDatabaseAndState` beyond foreign keys

- **Removing a field — Django's `ignored_columns`.** Deploy 1: make the column nullable (or give it
  a database default with `db_default`, Django 5.0+), then remove the field with
  `state_operations=[migrations.RemoveField(...)]` and no database operations, so running instances
  stop selecting and writing it. Deploy 2: `RunSQL("ALTER TABLE … DROP COLUMN …")`, state untouched.
- **Renaming a model or moving it between apps** without touching the table: keep `Meta.db_table`
  on the existing table name and put the rename in `state_operations` only.
- **Never `RenameField` on a live table.** It emits `ALTER TABLE … RENAME COLUMN`, and every
  instance still selecting the old name fails at once. Use the expand/contract rename in
  `migration-guide.md`.

---

## Backfills outside the migration — a Celery task

```python
# app/tasks/backfills.py — a sync sessionmaker: Celery workers are not async
@celery_app.task(acks_late=True, autoretry_for=(OperationalError,), retry_backoff=True, max_retries=5)
def backfill_order_status(batch_size: int = 5_000) -> None:
    with SessionLocal() as session:
        ids = session.scalars(
            select(Order.id).where(Order.status.is_(None)).limit(batch_size)
        ).all()
        if not ids:
            return  # finished — and every re-run of a finished job is this no-op
        session.execute(update(Order).where(Order.id.in_(ids)).values(status="pending"))
        session.commit()
    # One batch per task: a worker restart loses a batch, not the run; the countdown lets replicas catch up.
    backfill_order_status.apply_async(kwargs={"batch_size": batch_size}, countdown=1)
```

- **Idempotent by predicate** (`status IS NULL`) — a retry or a duplicate enqueue costs nothing.
- **Django spelling of a batch**: `ids = list(Order._base_manager.filter(status__isnull=True)
  .values_list("pk", flat=True)[:batch_size])`, then
  `Order._base_manager.filter(pk__in=ids).update(status="pending")`. **`_base_manager`, not a
  custom default manager** — a soft-delete or tenant manager hides rows, and you find out when the
  `NOT NULL` validation fails on the ones it skipped: the Django face of ActiveRecord's `unscoped`.
- **A bulk update skips per-object hooks** — `save()`, signals, `auto_now`, SQLAlchemy mapper
  events. Set timestamps explicitly if they matter.
- **`ANALYZE orders` when it finishes** — statistics lag a large backfill
  (`@skills/std-database/references/design-and-query-plan.md`, section 8).

---

## Alembic autogenerate — review the draft before you commit it

- [ ] **Read the SQL** — `alembic upgrade <from_rev>:<to_rev> --sql`.
- [ ] **`env.py` passes `transaction_per_migration=True` to `context.configure()`**, online and
      offline — each revision commits on its own, so no revision's lock outlives it.
- [ ] **Renames came out as drop + add.** Autogenerate cannot detect a table or column rename, so
      the draft destroys the data. Rewrite it — on a live table, as expand/contract.
- [ ] **Every `op.create_index` on an existing table** uses `postgresql_concurrently=True` inside
      `autocommit_block()`, alone in its revision.
- [ ] **Every new foreign-key column has an index** — autogenerate emits only what the model
      declares, and nothing declares it unless the column says `index=True`.
- [ ] **`nullable=False` on `op.add_column`** to a populated table carries a constant
      `server_default`, or it fails on existing rows; a volatile default rewrites the table.
- [ ] **Constraints are named** by a `naming_convention` on the `MetaData` — an unnamed constraint
      gets a database-generated name that `downgrade()` cannot target.
- [ ] **What autogenerate misses, you write by hand**: CHECK constraints, PostgreSQL `ENUM` value
      changes, sequences, and server-default changes unless `compare_server_default` is on.
- [ ] **`downgrade()` is real** — `upgrade()` undone in reverse order, or it raises. A `pass` is a
      rollback that reports success and does nothing.
- [ ] **No large backfill** in `upgrade()`, and **`alembic check` runs in CI** — it fails when
      models and migrations have drifted.

The naming convention, set once on the declarative base:

```python
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention={
        "ix": "index_%(table_name)s_on_%(column_0_N_name)s",  # Rails' shape; "_" where Rails writes "_and_"
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "chk_%(table_name)s_%(constraint_name)s",       # every CheckConstraint needs name="<description>"
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    })
```

Because `ck` includes `%(constraint_name)s`, a full name handed to an Alembic constraint operation
is prefixed a second time — wrap it in `op.f("chk_orders_status_not_null")` to mark it final, or
use raw SQL as the examples above do. The Django review is the same list in Django terms:
`sqlmigrate` read, `makemigrations --check` in CI (`std-django`), and each operation above in its
safe form.
