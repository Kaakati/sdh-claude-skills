# Design & Query Plan — the page you fill in before the migration

Load-bearing rules restated (hold even if you read nothing else):

1. **Relationships → query/index plan → constraints → migration → verify.** In that order. A
   migration written first encodes guesses the queries then have to live with.
2. **Every index answers a named query, and every planned query on a large table has an index** —
   or a written reason it does not need one.
3. **Verify with `EXPLAIN (ANALYZE, BUFFERS)` at production-like row counts, before and after.** A
   plan on 1,000 rows says nothing about 10 million: the planner picks a sequential scan on a small
   table because there it *is* faster.

Owned elsewhere — do not duplicate: relationship code and pitfalls →
`@skills/std-database/references/relationships.md`; which operation takes which lock and its
expand/contract form → `@skills/db-migration/references/migration-guide.md` (ActiveRecord) and
`@skills/db-migration/references/migration-guide-python.md` (Django, Alembic); `lock_timeout` →
`@skills/std-database/references/locking-and-timeouts.md`; query latency targets →
`@skills/performance-profiler/references/performance-benchmarks.md`; diagnosing a slow query that
is already in production → the `performance-profiler` skill.

---

## When to fill it in

Any change that adds a table, adds an association, or adds a query path to a table that is — or
within a year will be — large. A lookup table of a few hundred rows needs sections 1, 2, and 5 and
nothing else; the row counts at which a migration turns dangerous are the `db-migration` skill's
pre-flight, not restated here.

Put the filled plan in the PR description. The example rows follow one feature (organizations,
memberships, projects, tasks) through every section — replace them with yours.

---

## 1. Entities

| Entity | Table | Bounded context | Tenant-scoped | Soft delete | Primary key |
|---|---|---|---|---|---|
| Organization | `organizations` | accounts | — (it is the tenant) | yes | uuid |
| Membership | `memberships` | accounts | yes | no | uuid |
| Project | `projects` | work | yes | yes | uuid |
| Task | `tasks` | work | yes | no | uuid |

## 2. Relationship map

Association notation, because it decides where every foreign key lives (the which-side table is
in `relationships.md`):

```text
Organization has_many :memberships, dependent: :destroy     # counter_cache from Membership
Organization has_many :users, through: :memberships
User         has_many :memberships;  has_many :organizations, through: :memberships
Membership   belongs_to :user;  belongs_to :organization     # role lives here
Organization has_many :projects, dependent: :restrict_with_error
Project      belongs_to :organization;  has_many :tasks      # FK on_delete: :cascade
Task         belongs_to :project;  belongs_to :organization  # denormalized tenant key
Task         belongs_to :assignee, class_name: "User", optional: true
```

Flag every `polymorphic: true` and every `has_and_belongs_to_many` here. The first needs a written
reason; the second is always replaced by a join model.

## 3. Top queries per table

Name the queries before the indexes — frequency and budget decide which ones earn an index.

| # | Query — in words, then the ORM call | Frequency | p95 budget | Rows | Pagination |
|---|---|---|---|---|---|
| Q1 | membership for the current user in the current org — `Membership.find_by!(user:, organization:)` | every authorized request | 5 ms | 1 | — |
| Q2 | an org's projects, newest first — `org.projects.order(created_at: :desc)` | dashboard load | 20 ms | one page | cursor |
| Q3 | an org's open tasks by due date — `org.tasks.open.order(:due_on)` | task board load | 20 ms | one page | cursor |
| Q4 | an org's members — `org.memberships.includes(:user)` | members admin page | 50 ms | one page | cursor |
| Q5 | tasks assigned to me — `Task.where(assignee: current_user)` | inbox | 20 ms | one page | cursor |

A query's budget is a share of its endpoint's, and both have targets in
`@skills/performance-profiler/references/performance-benchmarks.md` — cite them rather than
inventing new ones. The pagination contract (cursor shape, metadata) is `std-api-design`'s.

## 4. Index plan

One row per query. The **Type** column is where most mistakes surface.

| Query | Index | Type | Why |
|---|---|---|---|
| Q1 | unique `index_memberships_on_user_id_and_organization_id` | btree | equality on both columns; also enforces one membership per pair |
| Q4 | `index_memberships_on_organization_id` | btree | Q1's index cannot serve it — `organization_id` is not its left prefix |
| Q2 | `index_projects_on_organization_id_and_created_at` | btree | equality first, sort last: rows come back ordered, no Sort node |
| Q3 | `(organization_id, due_on) WHERE status = 'open'` | partial | the board reads only open tasks; the index stays small as closed ones pile up |
| Q5 | `index_tasks_on_assignee_id` | btree | the foreign-key index doubles as the query's |
| composite FK (section 5) | unique `index_projects_on_id_and_organization_id` | btree | the target `tasks`' composite foreign key references; the primary key on `id` alone cannot serve it |
| Q2, if hot | `(organization_id, created_at) INCLUDE (name, status)` | covering | index-only scan for the list columns — only when `BUFFERS` shows the heap fetch is the cost |
| tag filter | `USING gin (metadata jsonb_path_ops)` | GIN | `@>` containment; `jsonb_path_ops` is smaller but has no key-exists (`?`) support |
| name search | `USING gin (name gin_trgm_ops)` | GIN (pg_trgm) | `ILIKE '%term%'`, which no btree can serve |
| near me | `USING gist (location)` | GiST | PostGIS `ST_DWithin` on `geography` — query shapes in `@skills/db-migration/references/postgres-patterns.md` |
| similar items | `USING hnsw (embedding vector_cosine_ops)` | HNSW | pgvector nearest-neighbour on `<=>`; the operator class must match the query's distance operator or the index is ignored |

The table is done when it passes these:

- **Equality columns first, range and sort columns last.** `(organization_id, created_at)` serves
  `WHERE organization_id = ? ORDER BY created_at DESC`; `(created_at, organization_id)` serves
  neither well. The query shape decides the order, not which column is more selective.
- **No left-prefix duplicates.** An index on `(a)` beside one on `(a, b)` is a second copy of the
  same lookup, maintained on every write — `t.references … index: false` exists for this. The one
  planned exception is a unique index a composite foreign key references: `projects (id,
  organization_id)` beside the primary key, because the key cannot reference anything else.
- **A partial index must be provable when the query is planned.** PostgreSQL: *"Matching takes
  place at query planning time, not at run time. As a result, parameterized query clauses do not
  work with a partial index."* ActiveRecord sends `status = $1` as a prepared statement, and once
  the plan goes generic the index can drop out — write the predicate as a literal in the scope
  (`scope :open, -> { where("status = 'open'") }`) and confirm with `EXPLAIN`.
- **`INCLUDE` columns are payload, not keys** — nothing filters or sorts on them through the index.
- **Every foreign key leads some index**, or the parent's `DELETE` scans the child table.
- **Count the write tax.** A table taking thousands of writes a second earns fewer indexes than one
  read on every request; each index is maintained on every insert and every update of its columns.
- **Append-only time series** (events, logs) read by time range: consider a BRIN index on
  `created_at` — a fraction of a btree's size when rows arrive in time order.

## 5. Constraints

The database guards every write path; validations guard only the paths that call them.

| Table | Column(s) | NOT NULL | UNIQUE | CHECK | Foreign key → on_delete |
|---|---|---|---|---|---|
| `memberships` | `user_id`, `organization_id` | both | together | — | users, organizations → default (`dependent: :destroy` removes memberships first) |
| `memberships` | `role` | yes | — | `chk_memberships_role` — `role IN (…)` | — |
| `projects` | `organization_id`, `name` | both | `(organization_id, name)` | — | organizations → default (restrict) |
| `tasks` | `project_id` | yes | — | — | projects → cascade |
| `tasks` | `organization_id` | yes | — | — | `(project_id, organization_id)` → `projects (id, organization_id)` → cascade |
| `tasks` | `assignee_id` | no | — | — | users → nullify |
| `tasks` | `status` | yes | — | `chk_tasks_status` — `status IN (…)` | — |

A **denormalized tenant key can disagree with its parent** — a task whose `organization_id` is not
its project's. The composite foreign key in the table makes that unrepresentable; it needs a unique
index on `projects (id, organization_id)` to reference (section 4). Two details keep it honest:

- **Its `on_delete` matches `project_id`'s key: cascade.** PostgreSQL fires a table's triggers for
  one event "in alphabetical order by name" (PostgreSQL — CREATE TRIGGER), foreign-key triggers
  included. A default `NO ACTION` composite key therefore refuses a project delete whenever its
  trigger runs before the cascade's, which depends on which constraint was created first
  (reproduced on PostgreSQL 17.11).
- **A row whose `organization_id` is `NULL` is not checked** (`MATCH SIMPLE`, the default). The
  expand steps in section 7 rely on that, and `NOT NULL` closes it once the backfill has run.

## 6. Data volume and growth

| Table | Rows today | Rows in 12 months | Peak writes/s | Hot rows | Retention |
|---|---|---|---|---|---|
| `memberships` | 40k | 200k | low | none | forever |
| `tasks` | 2M | 15M | 50 | none | forever |
| `organizations` | 5k | 20k | **high, via `counter_cache` / `touch`** | every busy organization | forever |
| `task_events` | 30M | 400M | 500 | none | 13 months, then drop partitions |

Growth decides three things: whether each migration needs the expand/contract form (the
`db-migration` pre-flight), whether a table wants partitioning
(`@skills/db-migration/references/postgres-patterns.md`), and whether a `counter_cache` or `touch`
turns its parent into a hot row.

## 7. Migration plan

One row per migration, in deploy order. Take the lock for each operation from the `db-migration`
skill's "What actually locks" table and the PostgreSQL lock documentation — not from memory.

| Step | Ships in | Operation | Lock | Phase |
|---|---|---|---|---|
| 1 | deploy 1 | `create_table :memberships` (FKs to `users`, `organizations`) | new table, plus `SHARE ROW EXCLUSIVE` on each referenced table while its FK is added — brief, `lock_timeout` applies | expand |
| 2 | deploy 1 | `add_column :tasks, :organization_id, :uuid` (nullable, no default) | `ACCESS EXCLUSIVE`, metadata only — milliseconds | expand |
| 3 | deploy 2 | `add_index :tasks, [:organization_id, :due_on], where: "status = 'open'", algorithm: :concurrently` | `SHARE UPDATE EXCLUSIVE` — reads and writes continue | expand |
| 4 | deploy 2 | `add_index :projects, [:id, :organization_id], unique: true, algorithm: :concurrently` | `SHARE UPDATE EXCLUSIVE` — reads and writes continue | expand |
| 5 | deploy 2 | `add_foreign_key :tasks, :projects, column: [:project_id, :organization_id], primary_key: [:id, :organization_id], name: "fk_tasks_project_organization", on_delete: :cascade, validate: false` (composite keys: Rails 7.1+) | `SHARE ROW EXCLUSIVE` on `tasks` and `projects`, brief; existing rows unchecked | expand |
| 6 | after deploy 2 | **backfill** `tasks.organization_id` from `projects` (section 8) | row locks, one batch at a time | backfill |
| 7 | deploy 3 | `validate_foreign_key :tasks, name: "fk_tasks_project_organization"` | `SHARE UPDATE EXCLUSIVE` on `tasks`, `ROW SHARE` on `projects` — scans without blocking | expand |
| 8 | deploy 3 | `NOT NULL` via a `NOT VALID` CHECK → validate → `change_column_null` | per the guide's `NOT NULL` form; on Alembic the CHECK's revision commits before validation (`transaction_per_migration=True`) | contract |
| 9 | deploy 4 | drop the old `tasks → projects → organizations` join from every tenant query | — | contract |

Steps 3 and 4 are each a migration of their own with `disable_ddl_transaction!`: a `CONCURRENTLY`
build cannot run inside a transaction (the Django and Alembic spellings are in
`migration-guide-python.md`). Step 5 needs step 4's index to exist and be valid.

At every step the code running in production and the code about to run both work against the
schema as it stands — the expand/contract rule the `db-migration` skill owns.

## 8. Backfill

| Job | Selects (the idempotent predicate) | Batch | Throttle | Resumable | Runs |
|---|---|---|---|---|---|
| `BackfillTaskOrganizationJob` | `tasks.organization_id IS NULL` | per the guide | pause per batch; watch replica lag | yes — the predicate skips finished rows | after deploy 2, before deploy 3 |

Once a table is large, a backfill is a Sidekiq job (a Celery task on the Python stack) run after
the deploy, never a data change inside the deploy's migration; batching, `unscoped`, and
replication lag are in `@skills/db-migration/references/migration-guide.md` (Backfills). When it
finishes, run `ANALYZE tasks` — until autovacuum gets there, the statistics may still describe the
column as all-NULL, and the planner chooses plans for data that no longer exists.

## 9. Rollback

| Step | Undo | One-way? |
|---|---|---|
| 1–5, 7, 8 | `rails db:rollback` / `migrate <app> <previous>` / `alembic downgrade -1` — each migration's own inverse | no |
| 6 | nothing to undo — code that ignores the column keeps working | the written values stay; harmless |
| 9 | redeploy the previous release | no — the old join path still resolves |

The point of no return is the first contract step that **drops** something — a column, a table, a
code path whose data stops being written. Mark it in the plan and in the PR; everything before it
must roll back with a command, not a restore.

## 10. Verify — `EXPLAIN (ANALYZE, BUFFERS)`, before and after

Run every planned query against production-like row counts — staging restored from a recent
snapshot, not seeds.

```sql
-- ANALYZE executes the statement. For a write, wrap it so nothing persists.
BEGIN;
EXPLAIN (ANALYZE, BUFFERS)
  UPDATE tasks SET status = 'done'
  WHERE organization_id = '<organization uuid>' AND id = '<task uuid>';
ROLLBACK;
```

PostgreSQL is explicit that *"the statement is actually executed when the ANALYZE option is
used"* — an `EXPLAIN ANALYZE DELETE` outside a transaction deletes.

Plan the SQL the ORM actually sends, not the SQL you imagine:

| Stack | Getting the plan |
|---|---|
| Rails | `org.tasks.open.order(:due_on).explain(:analyze, :buffers)` (Rails 7.1+), or `.to_sql` into `psql` |
| Django | `Task.objects.filter(...).explain(analyze=True, buffers=True)` |
| SQLAlchemy | compile with `compile_kwargs={"literal_binds": True}` and run `EXPLAIN (ANALYZE, BUFFERS)` on the text — literals, so test the partial-index case in section 4 separately |

What to read, before and after:

| In the plan | Means | Usual fix |
|---|---|---|
| `Seq Scan` on a large table with a selective filter | no usable index | the index from section 4 |
| `Rows Removed by Filter` far above rows returned | an index exists but is not selective for this query | reorder the composite, or make it partial |
| `Sort` above the scan; `Sort Method: external merge  Disk` | the index order does not match `ORDER BY` | put the sort column last in the index |
| large `Buffers: shared read=` | pages came from disk, not cache | touch fewer pages: a covering index, fewer columns |
| high `Heap Fetches:` on an `Index Only Scan` | the visibility map is stale | vacuum — `INCLUDE` cannot help until it is current |
| estimated rows off from actual by 10× or more | stale statistics | `ANALYZE <table>`, always after a backfill |
| `Nested Loop` with `loops=` in the thousands | a per-row lookup — an N+1 inside the database | an index on the inner side's join column, or a different join shape |

Record the before and after (plan shape, execution time, buffers) in the PR. The same pass covers
the application: an N+1 is many fast plans, not one slow one, so pin the query count — `bullet` and
`strict_loading` in Rails, `assertNumQueries` in Django, `lazy="raise"` in SQLAlchemy.

---

## Bottleneck checklist

Tick each against the plan before the migration is written:

- [ ] **N+1** — every association a serializer, view, or policy scope touches is eager-loaded, and
      the query count is pinned in a test.
- [ ] **Missing foreign-key index** — every FK column leads some index. PostgreSQL adds none, and
      neither does SQLAlchemy.
- [ ] **Unbounded lists** — every list query is paginated, cursor-based for deep or infinite lists
      (`OFFSET` walks every skipped row). No unpaginated `.all` behind an endpoint.
- [ ] **Counts** — a count on every page load comes from `counter_cache` or a cache, never
      `COUNT(*)` over a large table per request; infinite scroll drops the total entirely. Every
      count is computed within the caller's policy scope. A stored counter counts every row, so it
      is a valid badge only at `org` scope (`@skills/std-api-design/references/drill-down-resources.md`).
- [ ] **Tree walks** — a same-type hierarchy's ancestor and subtree queries are named in section 3,
      indexed in section 4, cycle-guarded and depth-capped
      (`@skills/std-database/references/hierarchies.md`).
- [ ] **Hot-row lock contention** — `counter_cache`, `touch: true`, or a running balance on a parent
      that many writers share becomes one row lock they all queue on. Append rows and aggregate,
      or update in batches from a job.
- [ ] **Cascading deletes on large tables** — `dependent: :destroy`, Django `CASCADE`, or
      `ON DELETE CASCADE` over an unbounded child set is one giant transaction. Soft-delete the
      parent; purge the children in batches.
- [ ] **Polymorphic without the composite index** — `[subject_type, subject_id]` exists (Rails adds
      it; Django's `GenericForeignKey` does not).
- [ ] **JSONB overuse** — a key you filter, sort, join, or constrain is a real column. JSONB has no
      per-key NOT NULL, foreign key, or type, and updating one key rewrites the whole value.
- [ ] **Many-to-many fan-out** — `organization.users` on the largest tenant is paginated, and
      fan-out on write (notify every follower) runs in a batched job, not the request.
- [ ] **Leading-wildcard search** — `LIKE '%term%'` has a trigram GIN index or goes through
      `pg_search`; otherwise it is a full scan.
- [ ] **Tenant scoping** — every tenant-owned table's indexes lead with `organization_id`.
