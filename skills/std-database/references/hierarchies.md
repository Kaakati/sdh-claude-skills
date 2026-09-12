# Hierarchies — storing a tree, and the read models above it

Load-bearing rules restated (hold even if you read nothing else):

1. **Most drill-down hierarchies are not trees.** Region → site → asset is a fixed chain of three
   different models. Model it with plain `has_many` / `belongs_to`, eager-loaded per level
   (`@skills/std-database/references/relationships.md`). This file covers **trees where every node
   is the same type and depth is open-ended**: folders, org units, categories, bills of materials.
2. **Start with an adjacency list (`parent_id`) and one recursive query per walk.** Guard it three
   ways: `CHECK (parent_id <> id)`, a `CYCLE` clause or depth cap on every walk, and moves serialized
   per tree.
3. **Change storage on evidence, not preference.** Move only when `EXPLAIN (ANALYZE, BUFFERS)` shows
   a walk over budget. Record the choice in an ADR through `architecture-advisor`, because changing
   storage later is a data migration.
4. **Never start a new nested set, and never adopt `django-mptt`.**
5. **Paths encode IDs, never display names.** Renaming a node must not rewrite its subtree.

Owned elsewhere — do not duplicate:
- The API shape above a tree (levels, `ancestors`, scoped counts, per-level authorization) →
  `@skills/std-api-design/references/drill-down-resources.md`.
- The plan template these choices slot into (sections 3, 4 and 10) →
  `@skills/std-database/references/design-and-query-plan.md`.
- Adding the column or index to a live table → `@skills/db-migration/references/migration-guide.md`
  and `@skills/db-migration/references/migration-guide-python.md`.
- Materialized-view SQL and its refresh job → `@skills/db-migration/references/postgres-patterns.md`.
- Advisory locks → `@skills/std-database/references/locking-and-timeouts.md`.
- Python eager-loading spellings → `std-python-performance`.

---

## Decision: which storage?

| Storage | Wins when | Reads | Writes and moves | Rails | Python |
|---|---|---|---|---|---|
| **Adjacency list + recursive query** (house default) | depth is moderate, moves are frequent, and concurrent writers matter | one `WITH RECURSIVE` statement per subtree or ancestor chain | one row per insert or move | `belongs_to :parent` + a query object | SQLAlchemy `remote_side` + `Select.cte(recursive=True)`; Django `ForeignKey("self")` + `django-tree-queries` or raw SQL |
| **Materialized path — `ancestry`** | reads dominate, ancestor or descendant lookups run on every request, and moves are rare | one indexed query each for `ancestors_of`, `children_of`, `descendants_of`, `subtree_of`, `siblings_of` | moving a node rewrites every descendant's path (inference) | `ancestry` | django-treebeard `MP_Node` |
| **Materialized path — `ltree`** | the product is committed to PostgreSQL and needs label-path pattern queries at scale | GiST serves `<@`, `@>`, `~`, `?` | moving a node rewrites every descendant's path (inference) | a `path ltree` column the move service maintains under the per-tree advisory lock (`ancestry`'s `:ltree` format is unreleased and integer-key only) | treebeard's ltree backend (**experimental**) |
| **Closure table — `closure_tree`** | trees are deep, whole-subtree reads and find-by-path dominate, and writes are moderate | "Grab all your descendants in 1 SELECT" | 2 INSERTs per new node; 3 INSERT/UPDATEs per reparent | `closure_tree` | none confirmed; run a spike first |
| **Nested sets (MPTT)** | almost never: only a static, read-only tree you already have | efficient reads | "high maintenance on write/delete operations" | no gem verified | never `django-mptt`; treebeard `NS_Node` only for an existing tree |

How to choose:

1. Start with an adjacency list and a recursive query.
2. Move to `ancestry` (`materialized_path2` format, C collation, `primary_key_format` set for UUID
   keys) when the plan shows ancestor or subtree queries over budget and moves are rare.
3. Move to `closure_tree` when subtree reads dominate and writes stay moderate.
4. Use `ltree` only when the product is committed to PostgreSQL and needs label-path patterns.

Whichever storage you choose, name its walks in section 3 of the plan, list its indexes in section 4,
and verify both with section 10. A tree is not exempt from any of them.

---

## Adjacency list + recursive query (the default)

SQLAlchemy calls the adjacency list "probably the most appropriate pattern for the large majority
of hierarchical storage needs". It prefers it to nested sets for concurrency and reduced complexity
(SQLAlchemy — Adjacency List Relationships).

```ruby
create_table :folders, id: :uuid do |t|
  t.references :organization, null: false, foreign_key: true, type: :uuid
  t.references :parent, type: :uuid, foreign_key: { to_table: :folders } # null means a root; indexed
  t.string :name, null: false
  t.timestamps
  t.check_constraint "parent_id <> id", name: "chk_folders_not_own_parent"
end
```

| Query | Index |
|---|---|
| children of a node; the recursive step; deleting a parent | `parent_id`, the foreign key's own index |
| a tenant's roots, when roots are few among many nodes | partial `(organization_id) WHERE parent_id IS NULL` (the predicate is a literal, so the plan can use it) |

```sql
-- The ancestor chain of one folder, root first: one statement, however deep the tree
WITH RECURSIVE chain AS (
  SELECT id, parent_id, name, 0 AS hops
  FROM folders
  WHERE id = :folder_id AND organization_id = :organization_id
  UNION ALL
  SELECT p.id, p.parent_id, p.name, c.hops + 1
  FROM folders p
  JOIN chain c ON p.id = c.parent_id
  WHERE c.hops < :max_depth AND p.organization_id = :organization_id
) CYCLE id SET is_cycle USING path
SELECT id, name FROM chain WHERE hops > 0 AND NOT is_cycle ORDER BY hops DESC;

-- A subtree in depth-first order, capped
WITH RECURSIVE subtree AS (
  SELECT id, parent_id, name, 1 AS depth
  FROM folders
  WHERE id = :root_id AND organization_id = :organization_id
  UNION ALL
  SELECT f.id, f.parent_id, f.name, s.depth + 1
  FROM folders f
  JOIN subtree s ON f.parent_id = s.id
  WHERE s.depth < :max_depth
) SEARCH DEPTH FIRST BY id SET ordercol
SELECT id, parent_id, name, depth FROM subtree ORDER BY ordercol;
```

- **Guard every walk.**
  - The recursive part must eventually return no rows, "or else the query will loop indefinitely".
  - Using `LIMIT` as the safety net is "not recommended" in production (PostgreSQL — 7.8 WITH
    Queries).
  - `CYCLE id SET is_cycle USING path` flags a loop and stops following it.
  - `SEARCH DEPTH FIRST BY id SET ordercol` adds a column to `ORDER BY` for tree order.
  - `:max_depth` is the product's real maximum depth, bound as a parameter, never a guess.
- **The `CHECK` stops a self-loop, not A → B → A.**
  - Before a move, reject a new parent that is the node itself or one of its descendants.
  - Two concurrent moves can each pass that check and close a loop together, so serialize moves per
    tree with a transaction-scoped advisory lock (`locking-and-timeouts.md`). `CYCLE` stays as the
    backstop (inference).
- **Cost grows with the size of the walk** (inference). That growth is what the alternatives below
  exist for.
- **A walk returns rows, not permissions.** Filter them through the read policy before they become
  `ancestors` (`drill-down-resources.md` §4).

Per stack:
- **Rails.** Put the SQL in a query object (`app/queries/folders/ancestors_query.rb`) and run it with
  `Folder.find_by_sql([SQL, { folder_id:, organization_id:, max_depth: }])`.
- **SQLAlchemy.** Map the parent with `relationship(remote_side=...)`.
  - Eager-loading a self-referential relationship needs `join_depth`, "otherwise the eager load will
    not take place at all" (SQLAlchemy — Adjacency List Relationships).
  - An unbounded walk is `Select.cte(recursive=True)` plus a `union_all` of the recursive term,
    below. The tutorial defers its recursive examples to the `CTE` docstring (SQLAlchemy — Using
    SELECT Statements), so check the shape against your installed 2.0.x.
- **Django.** `ForeignKey("self", null=True, on_delete=models.PROTECT, related_name="children")`.
  - "Recursive relationships, where a model has a relationship with itself, are also supported",
    and the column is indexed automatically (Django — Model field reference).
  - `django-tree-queries` computes tree fields with recursive CTEs. It supports only integer and
    UUID primary keys, and it does not fill in tree fields after `save()` or `create()` (feincms —
    django-tree-queries README).
  - Without it, run the SQL above through `Folder.objects.raw(sql, params)`.

```python
chain = (select(Folder.id, Folder.parent_id, Folder.name, literal(0).label("hops"))
         .where(Folder.id == folder_id, Folder.organization_id == org_id)
         .cte("chain", recursive=True))
step, parent = chain.alias(), aliased(Folder)
chain = chain.union_all(
    select(parent.id, parent.parent_id, parent.name, step.c.hops + 1)
    .where(parent.id == step.c.parent_id, step.c.hops < max_depth, parent.organization_id == org_id))
rows = await session.execute(
    select(chain.c.id, chain.c.name).where(chain.c.hops > 0).order_by(chain.c.hops.desc()))
```

---

## Materialized path — `ancestry` (Rails) / treebeard `MP_Node` (Django)

"each record stores its ancestor chain in a single column (e.g. 1/2/3/). No additional tables
needed." Scopes such as `roots`, `ancestors_of`, `children_of`, `descendants_of`, `subtree_of` and
`siblings_of` each run one query. `arrange_serializable` returns nested JSON, and a children
`counter_cache` is built in (ancestry maintainers — ancestry README).

```ruby
# migration (new table): C collation, so a prefix LIKE can use the btree index
t.string :ancestry, collation: "C", null: false
add_index :categories, :ancestry

class Category < ApplicationRecord
  # Options per the README at the tag you install (v5.1.0: README.md; CONFIGURATION.md exists only on master)
  has_ancestry ancestry_format: :materialized_path2, orphan_strategy: :restrict,
               primary_key_format: "[-A-Fa-f0-9]{36}" # UUID keys; omit for bigint keys
end
```

- **Read the README at the tag you install.** On master it "may describe features not yet released".
- **The default `:orphan_strategy` is `:destroy`**: deleting a node destroys its whole subtree. Set
  `:restrict` or `:adopt` on purpose.
- **Format and indexing.** `:materialized_path2` is the released format for new columns — "If you
  are unsure, choose `:materialized_path2`" — and the README's own PostgreSQL migration is
  `t.string "ancestry", collation: 'C', null: false` (ancestry maintainers — ancestry README v5.1.0).
  - `:materialized_path3` and `:ltree` exist only on ancestry master, not in 5.1.0, whose
    `has_ancestry` raises for any format but `:materialized_path` and `:materialized_path2`. Adopt
    them only once a release ships them.
  - **UUID keys need `primary_key_format`.** The default, `'[0-9]+'`, matches integer IDs, and
    ancestry validates the column against it; the README gives `'[-A-Fa-f0-9]{36}'` for UUIDs.
  - The legacy `:materialized_path` format needs an OR condition for descendant queries.
  - The format is fixed at design time. Changing it later is a data migration.
  - Without C collation, a prefix `LIKE` needs `text_pattern_ops` "when the database does not use
    the standard C locale". Range comparisons then need a second index with the default operator
    class (PostgreSQL — Operator Classes and Operator Families).
- **Django.** treebeard's `MP_Node` is "the most compatible and commonly used implementation"
  (django-treebeard project — Choosing a tree implementation). Its README lists v7.x as the current
  stable line, requiring Django 5.2+ and Python 3.10+.

## Materialized path — `ltree`

```sql
CREATE EXTENSION IF NOT EXISTS ltree;
ALTER TABLE folders ADD COLUMN path ltree;                                    -- labels are IDs, never names
CREATE INDEX CONCURRENTLY index_folders_on_path ON folders USING gist (path); -- serves <@ @> ~ ?
SELECT id, name FROM folders WHERE path <@ $1;                                -- a subtree, index-served
```

- **Only GiST serves the tree operators.** A GiST index (`gist_ltree_ops`) serves `@>`, `<@`, `~`
  and `?`. A btree covers only ordering and equality, and a hash index only equality. The GiST
  `siglen` defaults to 8 bytes, with a maximum of 2024 (PostgreSQL — F.22 ltree).
- **Label rules** (PostgreSQL 16 and later).
  - Labels allow letters, digits, `_` and `-`; which letters count depends on the locale.
  - A label is at most 1000 characters, and a path at most 65535 labels.
  - Encode IDs. **Hyphenated UUID labels need PostgreSQL 16+**: on 15 a label is only alphanumerics
    and `_`, and under 256 characters (PostgreSQL — F.23 ltree, versions 15 and 16).
- **It is an extension**, so the migration must create it. Building the index on a live table
  follows the `db-migration` guide.
- **Library support.** `ancestry`'s `:ltree` format exists only on master and takes "Integer primary
  keys only (not compatible with UUIDs)" (ancestry maintainers — CONFIGURATION.md, unreleased), so it
  does not fit UUID-keyed models. treebeard's ltree backend is marked experimental (django-treebeard
  project — Choosing a tree implementation).

## Closure table — `closure_tree`

The gem keeps a `<model>_hierarchies` closure table. Ancestors, descendants, siblings, lookup by
path, and a nested-hash subtree each take one SELECT. It also provides `depth` (root = 0) and
`rebuild!` for use after migrations (ClosureTree — closure_tree README).

- **Write cost.** Creating a node costs 2 INSERTs; reparenting costs 3 INSERT/UPDATEs.
- **Some methods are not concurrency-safe.** "Several methods, especially #rebuild and
  #find_or_create_by_path, cannot run concurrently correctly", which is why the gem takes
  `with_advisory_lock`.
- **Always pass `:limit_depth` to `hash_tree`.** Without it, `hash_tree` "will load the entire
  contents of that table into RAM".
- **Performance claims.** "Dramatically more performant than ancestry" is the gem's own claim, not
  an independent benchmark.
- **Size.** The hierarchy table grows roughly with nodes × depth (inference).
- **Requirements.** ActiveRecord 7.2+ and Ruby 3.3+.
- **Python.** No closure-table library was confirmed. Run a spike before choosing one.

## Nested sets — do not start one

- **Writes are expensive.** Nested sets give "efficient reads at the cost of high maintenance on
  write/delete operations" (django-treebeard project — Choosing a tree implementation). With MPTT,
  inserts and moves "are more involved" (django-mptt project — django-mptt README).
- **django-mptt is unmaintained.** "This project is currently unmaintained … If you are starting a
  new project, or can afford to migrate, consider an alternative." Its README points to
  recursive-CTE approaches instead.
- **SQLAlchemy also favors adjacency lists** over nested sets, for concurrency and reduced
  complexity (SQLAlchemy — Adjacency List Relationships).
- **Rails has no verified nested-set gem.**

## Indexing and write cost at a glance

| Storage | Index | Per insert | Per move |
|---|---|---|---|
| Adjacency list | btree on `parent_id` (+ the partial roots index) | one row | one row |
| `ancestry` | btree on the C-collated `ancestry` column | one row | every descendant's path (inference) |
| `ltree` | GiST on `path` | one row | every descendant's path (inference) |
| `closure_tree` | the gem's hierarchy table | 2 INSERTs | 3 INSERT/UPDATEs; table grows with nodes × depth (inference) |
| Nested sets | left/right bounds | "high maintenance" | "high maintenance" |

---

## Read models: the numbers on overview levels

| Need | Use | How stale |
|---|---|---|
| Child count per node, for a caller at `org` scope | `counter_cache`, plus `touch` when a validator depends on it | same transaction; drifts only through writes that bypass Active Record, repaired with `reset_counters` |
| Rollups by status or time across many descendants | a materialized view keyed by `(organization_id, node_id, …)` with a UNIQUE index, refreshed `CONCURRENTLY` by a scheduled job (a Sidekiq cron job; Celery beat on the Python stack) | as of the last refresh, returned as `asOf` |
| Counts for `own` or `team` scopes | one grouped `COUNT` over the policy scope per request, indexed per the plan | live |
| An expensive figure that is the same for everyone in the organization | `Rails.cache.fetch` keyed on organization + inputs, with an explicit TTL | up to the TTL |

- **Adding a counter to a large table.** Declare `counter_cache: { active: false }`, backfill, then
  remove the option. Rails: "To safely backfill the values while keeping counter cache columns
  updated with the child records creation/removal … use counter_cache: { active: false }" (Ruby on
  Rails API — ActiveRecord::Associations::ClassMethods).
- **Repairing a counter.** `reset_counters` fixes a counter that "has been corrupted or modified
  directly by SQL" (Ruby on Rails API — ActiveRecord::CounterCache::ClassMethods).
- **Hot rows.** Row-lock contention on a busy parent → `relationships.md`.
- **Materialized views are fast but stale.** Reading one is "often much faster than accessing the
  underlying tables directly", but "the data is not always current", and the view cannot be updated
  directly (PostgreSQL — 39.3 Materialized Views).
- **`REFRESH … CONCURRENTLY`** runs "without locking out concurrent selects on the materialized
  view" (PostgreSQL — REFRESH MATERIALIZED VIEW). Its requirements:
  - a UNIQUE index on plain column names that covers all rows;
  - a view that is already populated;
  - no `WITH NO DATA`;
  - only one refresh at a time.
- **A refresh without `CONCURRENTLY`** that touches many rows "could block other connections".
- **A stored number counts every row.** It is a valid badge only for a caller whose scope covers
  every row (`drill-down-resources.md` §5).

## Checklist

- [ ] A fixed chain of different models uses plain associations, not a tree library.
- [ ] `CHECK (parent_id <> id)` exists; every walk has `CYCLE` or a depth cap; moves are serialized
      per tree.
- [ ] Every walk is named in plan section 3, and its index is in section 4.
- [ ] For `ancestry`: C collation, `materialized_path2`, `primary_key_format` set for UUID keys, and
      `orphan_strategy` set on purpose.
- [ ] For `closure_tree`: `hash_tree` always has `:limit_depth`, and rebuilds never run
      concurrently.
- [ ] Paths and labels hold IDs, never names.
- [ ] An ancestor chain comes back in one query, and the query count is pinned per level.
- [ ] Overview numbers are either scoped or stored and served at `org` scope only; read models return
      `asOf`.
- [ ] The storage choice is recorded in an ADR.

## Sources

- PostgreSQL Global Development Group — 7.8. WITH Queries (Common Table Expressions) — https://www.postgresql.org/docs/current/queries-with.html
- PostgreSQL Global Development Group — F.22. ltree — https://www.postgresql.org/docs/current/ltree.html
- PostgreSQL Global Development Group — 39.3. Materialized Views — https://www.postgresql.org/docs/current/rules-materializedviews.html
- PostgreSQL Global Development Group — REFRESH MATERIALIZED VIEW — https://www.postgresql.org/docs/current/sql-refreshmaterializedview.html
- PostgreSQL Global Development Group — Operator Classes and Operator Families — https://www.postgresql.org/docs/current/indexes-opclass.html
- Ruby on Rails API — ActiveRecord::Associations::ClassMethods — https://api.rubyonrails.org/classes/ActiveRecord/Associations/ClassMethods.html
- Ruby on Rails API — ActiveRecord::CounterCache::ClassMethods — https://api.rubyonrails.org/classes/ActiveRecord/CounterCache/ClassMethods.html
- ancestry maintainers — ancestry README — https://github.com/stefankroes/ancestry
- ancestry maintainers — ancestry README v5.1.0 (the latest release) — https://github.com/stefankroes/ancestry/blob/v5.1.0/README.md
- ancestry maintainers — has_ancestry.rb v5.1.0 — https://github.com/stefankroes/ancestry/blob/v5.1.0/lib/ancestry/has_ancestry.rb
- ancestry maintainers — ancestry CONFIGURATION.md (master, unreleased) — https://github.com/stefankroes/ancestry/blob/master/CONFIGURATION.md
- PostgreSQL Global Development Group — F.23. ltree (version 15) — https://www.postgresql.org/docs/15/ltree.html
- PostgreSQL Global Development Group — F.23. ltree (version 16) — https://www.postgresql.org/docs/16/ltree.html
- ClosureTree — closure_tree README — https://github.com/ClosureTree/closure_tree
- Django Software Foundation — Model field reference — https://docs.djangoproject.com/en/stable/ref/models/fields/
- django-treebeard project — Choosing a tree implementation — https://django-treebeard.readthedocs.io/en/latest/choosing.html
- django-treebeard project — README — https://github.com/django-treebeard/django-treebeard
- django-mptt project — django-mptt README — https://github.com/django-mptt/django-mptt
- feincms — django-tree-queries README — https://github.com/feincms/django-tree-queries
- SQLAlchemy — Adjacency List Relationships — https://docs.sqlalchemy.org/en/20/orm/self_referential.html
- SQLAlchemy — Using SELECT Statements (Common Table Expressions) — https://docs.sqlalchemy.org/en/20/tutorial/data_select.html
