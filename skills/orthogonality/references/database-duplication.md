# Database duplication — one concept, one table; one fact, one column

DRY is about **knowledge**, and a database schema is knowledge: "one piece of knowledge in the
domain changes, one piece of the system changes". A clone detector cannot see a second table for a
concept, or a column that copies a fact reachable through a foreign key. These detectors can.

This file covers detection, and whether a copy may stay. The **design rules** remain
`std-database`'s: relationships, constraints, indexes, polymorphic, JSONB. Cite
`@skills/std-database/references/design-and-query-plan.md` and
`@skills/std-database/references/relationships.md`. The **migration** that fixes a finding is
`db-migration`'s: `@skills/db-migration/references/migration-guide.md`.

## How tables are compared

### Names

1. CamelCase and kebab-case become snake_case.
2. Namespaces are stripped (`Billing::Invoice` → `invoice`). So are a leading context prefix when
   contexts are declared (`billing_invoices` → `invoices`), and the prefixes `tbl_` and `app_`.
3. Conservative singularization: `ies → y`, `(s|x|z|ch|sh)es → \1`, a final `s` unless the word ends
   `ss`, `us` or `is`, plus a small irregulars table (`people → person`).
4. The suffixes `_record`, `_entity`, `_model`, `_data`, `_info`, `_details` are recorded, never
   stripped. A match found only after removing one is a **near-name** match, one confidence step lower.

### Synonyms

- **House list** (short on purpose): `customer~client`, `invoice~bill`, `organization~company~org`,
  `vendor~supplier`, `employee~staff_member`.
- **Deliberately absent**, because each has two common meanings: `account` (a user account or a
  ledger account), `item`, `member`, `location` (a PostGIS point or an address), `delivery`.
- **Project additions** go in `concepts.synonyms` in `.claude/orthogonality.json`; they extend the
  house list.
- **A synonym match alone is `info`.** It becomes `warn` only together with column overlap.

### Columns

- A column key is `(name, type family)`. Families: int, uuid, text, bool, time, decimal, json, geo,
  vector, enum, other.
- **Infrastructure columns are removed first:** `id`, `created_at`, `updated_at`, `deleted_at`,
  `discarded_at`, `lock_version`, `organization_id`, `tenant_id`.
- **A foreign key counts as `fk:<parent table>`.** So `orders.customer_id` and `invoices.customer_id`
  match as the same relationship, not the same fact.
- **Value groups fold to one key.** Address columns (`line1`, `line2`, `city`, `postal_code`) count as
  `value:address`; money columns (`amount`, `currency`) as `value:money`. A group scores one point, not
  six, and the evidence suggests a value object or `composed_of`.

### Overlap

`J(A, B) = |A ∩ B| / |A ∪ B|` over the normalized keys.

| Band | Severity |
|---|---|
| J ≥ 0.6 with at least 4 shared keys | `warn` |
| 0.4 ≤ J < 0.6 with at least 3 shared keys | `info` |
| below | nothing |

`find_duplicates.py --min-jaccard` and `--min-shared` change the bands for one scan.

### Contexts decide whether a match is a finding

| The two tables sit in | Result |
|---|---|
| the same context (declared, or the same inferred directory group) | `warn` when the name and overlap bands are met |
| two **inferred** contexts | `info`: an inferred context is a guess, and a guess does not speak at edit time |
| two **declared** contexts | quiet: bounded contexts may model one concept differently, mapped at their integration points |

### Excluded by convention (`info` in scans, never at edit time)

- **Join tables:** exactly two FK columns plus at most two other non-infrastructure columns.
- **Declared read models:** `CREATE [MATERIALIZED] VIEW`, Rails `create_view` (scenic), Django
  `Meta.managed = False` on a view name, SQLAlchemy `info={"read_model": True}`.
- **History and audit tables:** `versions`, `*_versions`, `*_history`, `*_audits`, `*_snapshots`, `*_archive`.
- **Partitions:** `PARTITION OF`, `*_yYYYYmMM`.
- **Staging and import tables:** `staging_*`, `raw_*`, `*_imports`.
- **One table per type:** tables sharing a suffix, each with a different parent FK (`project_members`,
  `group_members`). This is the shape GitLab prescribes to replace polymorphic associations, so a
  duplicate detector must not flag the remedy.

## DK1 — a second table or model for an existing concept

- **Signals.** Rails: `create_table` in migrations, `db/schema.rb`, `db/structure.sql`, model classes
  with `self.table_name`. Django: `models.Model` subclasses, `Meta.db_table`, `Meta.managed`.
  SQLAlchemy: `__tablename__`, `mapped_column`/`Column`, Alembic `op.create_table` when no model maps
  the table. Raw `.sql` `CREATE TABLE`.
- **Quiet.** The exclusions above; STI subclasses without a table; abstract classes
  (`ApplicationRecord`, `__abstract__ = True`, Django `abstract = True`); Django proxy models; test
  factories. A model file with no columns yet is name-only, so `info`.
- **Precedent.** Django already errors on the exact case, one `db_table` used by several models
  (`models.E028`). DK1 extends the idea to near-names and synonyms.
- **Resolve.** Extend the existing table and model. If the second concept is real, it belongs in its
  own **declared** context (`@skills/orthogonality/references/context-maps.md`). If it is a derived
  copy, it is a read model (below).

## DK2 — overlapping columns under another name

The same evidence and quiet cases as DK1, with no name match required. It catches the renamed
concept DK1 misses (`contacts` vs `customers`). Check value groups first: two tables sharing only an
address are telling you about a missing value object, not a duplicate concept.

## DK3 — a fact reachable through a foreign key

- **Fires.** A child with `<p>_id` → parent `P` gains `<p>_<col>` whose `(col, family)` exists on `P`:
  `orders.customer_email` beside `customers.email`. An exact same-name copy (`orders.email`) is `info`.
- **Snapshot columns are `info`, never `warn`.** On `*_items`, `*_lines`, `invoices`, `orders` or
  `receipts`, a money, name or tax column written once at creation is a legal record of what was
  true then: `unit_price` on a line item, a product name on an invoice line.
- **The denormalized tenant key.** `tasks.organization_id` is quiet when a composite FK
  `(project_id, organization_id)` → `projects (id, organization_id)` makes disagreement
  unrepresentable, as §5 of `@skills/std-database/references/design-and-query-plan.md` prescribes.
  Without that composite FK, it is `info` pointing there.
- **Scans add the writers.** They name every code path that writes the copied column, from the
  index's write graph. A copy written outside the parent's update path is the dangerous kind.

## DK4 — a repeating group

Three or more numbered siblings sharing one stem and numbered in one unbroken run from 0 or 1
(`phone_1`, `phone_2`, `phone_3`) are the first-normal-form smell: `info`, and `warn` at five or more.
Not a group: two siblings (`address_line1`, `address_line2`), `sha256`, `utf8`, `oauth2_token`, API
version columns (`v1_payload`), percentile columns (`latency_p50` … `latency_p99`, each its own
meaning), and a gapped set (`slot_2`, `slot_5`, `slot_9`). The usual fix is a child table; its
relationship and indexes are `std-database`'s.

## DK5 — one rule in two places (scan-only in this release)

- **Why.** A Rails uniqueness validation creates no database constraint, and the Rails guide requires
  a unique index. RuboCop's `Rails/UniqueValidationWithoutIndex` checks this statically, and does
  nothing when `db/schema.rb` is absent. This detector also reads `db/structure.sql`, and says "not
  checked" rather than passing when neither schema file parses.
- **Covered when:** `uniqueness: { scope: … }` has a unique index leading with the attribute and scope
  columns, in any order; `case_sensitive: false` has a `lower()` expression index. `conditions:` needs
  a partial unique index, and only a name-level match is possible.
- **Django.** `unique=True` creates the constraint, so only a `validate_unique` override without a
  matching constraint is a candidate. Uniqueness checked in a Pydantic model or service is invisible.
- **Owner.** "Database-level constraints enforce integrity" is `std-database`'s rule.

## MF3 — an entity-attribute-value table

A table shaped `(entity type or entity FK, entity_id, key or attribute or name, value)`. EAV is the
worst design for performance: reads join across attribute rows, and one entity write touches many
rows and index entries. The alternative is frequent attributes as columns, plus one `jsonb` column
with a GIN index for the rare ones, within `std-database`'s "JSONB sparingly". Quiet: a settings
table with **no** entity column (`settings(key UNIQUE, value)`), feature-flag library tables,
translation tables (`*_translations`).

## MF4 — STI bloat (scans only)

An STI table (`type` column, subclasses with no table) where at least 4 nullable columns are used by
one subclass only. Bloat is STI's stated cost, and `delegated_type` is the Rails remedy. When to move
is covered in the polymorphic section of `@skills/std-database/references/relationships.md`.

## MF5 — a JSONB key used as a column

A key used in a filter, sort, join or constraint: Rails `.where("data->>'status' = ?")` or
`order("data->>'x'")`; Django `filter(data__status=…)` or `order_by("data__x")`; SQLAlchemy
`Model.data["x"].astext == …`; raw `->>` in `WHERE`, `ORDER BY` or `JOIN`. `std-database` says such a
key is a column. Quiet: `@>` containment over genuinely schemaless tags; pgvector and PostGIS operators.

## Copy, or read model? Deciding whether it may stay

| The second representation is | Make it | Why |
|---|---|---|
| derived from other columns in the **same row** (a total from quantity and price) | a generated column | always computed from the row; it cannot be written directly |
| derived from **another table**, read-only, staleness acceptable | a view, or a materialized view with a named refresh | a generated column cannot reference other tables, and a cross-table `CHECK` cannot keep a copy correct |
| needed strongly consistent (money, inventory) | a trigger, or a redesign through the FK | a materialized view accepts staleness these domains cannot |
| a legal snapshot at creation (a price on an invoice line) | a column written once, at creation | it records history; it is not a copy of current state |
| none of the above | removed: read it through the association | two writable copies drift |

An intentional read copy is legitimate only when it meets three criteria, and its declaration must
state all three:

1. **Derived** — rebuildable from a named source of truth.
2. **Never written directly by the application**; only its refresh path writes it.
3. **Refreshed by** a named job, trigger or schedule.

Declare it as `kind: "read-model"` with `source_of_truth`, `refreshed_by` and `writes`, naming an ADR
(`@skills/orthogonality/references/declaring-intent.md`). A missing field is a `CFG-READMODEL` finding.
Adding a stored generated column or a foreign key to a large table safely is covered in
`@skills/db-migration/references/migration-guide.md`.

## Delegated, not detected here

- **A new polymorphic association.** The house rule "polymorphic only for open type sets" and its
  alternatives belong to `std-database`; stored class names must stay in sync with code. An
  edit-time warning belongs in `database-design-checker.py`, not in this skill's checker.
- **Enum or status lists copied between Rails and the TypeScript clients.** That drift is prevented
  by the generated client contract (`@skills/monorepo-architect/references/api-contract.md`). Scans
  report only whether that generation exists.

## Sources

- Artima (Bill Venners) — Orthogonality and the DRY Principle: A Conversation with Andy Hunt and Dave Thomas, Part II — https://www.artima.com/intv/dry.html
- Eric S. Raymond — The Art of Unix Programming, ch. 4, "The SPOT Rule" (Linuxtopia mirror) — https://www.linuxtopia.org/online_books/programming_books/art_of_unix_programming/ch04s02_2.html
- Microsoft Learn — Database normalization description — https://learn.microsoft.com/en-us/troubleshoot/microsoft-365-apps/access/database-normalization-description
- martinfowler.com — Bounded Context — https://martinfowler.com/bliki/BoundedContext.html
- PostgreSQL Global Development Group — 5.4. Generated Columns — https://www.postgresql.org/docs/current/ddl-generated-columns.html
- PostgreSQL Global Development Group — 5.5. Constraints — https://www.postgresql.org/docs/current/ddl-constraints.html
- Microsoft Learn (Azure Architecture Center) — Materialized View pattern — https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view
- CYBERTEC PostgreSQL International (Laurenz Albe) — Entity-attribute-value (EAV) design in PostgreSQL - don't do it! — https://www.cybertec-postgresql.com/en/entity-attribute-value-eav-design-in-postgresql-dont-do-it/
- Ruby on Rails — Active Record Associations — https://guides.rubyonrails.org/association_basics.html
- Ruby on Rails — Active Record Validations — https://guides.rubyonrails.org/active_record_validations.html
- RuboCop — Rails/UniqueValidationWithoutIndex (source) — https://raw.githubusercontent.com/rubocop/rubocop-rails/master/lib/rubocop/cop/rails/unique_validation_without_index.rb
- GitLab — Polymorphic associations (development guidelines) — https://docs.gitlab.com/development/database/polymorphic_associations/
- Django Software Foundation — The contenttypes framework — https://docs.djangoproject.com/en/stable/ref/contrib/contenttypes/
- Django Software Foundation — System check framework reference — https://docs.djangoproject.com/en/stable/ref/checks/
