# Relationships — design them in association terms, enforce them in the database

Load-bearing rules restated (hold even if you read nothing else):

1. **Name the relationship in Rails association vocabulary before any column exists.** The word —
   `has_one`, `has_many`, `has_many :through`, polymorphic, self-referential — decides where the
   foreign key lives, and that decides the index.
2. **Every foreign key gets an index and a constraint.** PostgreSQL creates no index for you:
   *"the declaration of a foreign key constraint does not automatically create an index on the
   referencing columns."* Rails `t.references` and Django `ForeignKey` add one; SQLAlchemy does not.
3. **A join is a model.** `has_many :through`, never `has_and_belongs_to_many`.
4. **A validation is not integrity.** `belongs_to` checks presence on `save`; `insert_all`,
   `update_columns`, and raw SQL never ask it. `null: false` plus a foreign key holds on every path.

The migrations here create **new** tables. Adding a foreign key or an index to a large live table
is the two-step form in `@skills/db-migration/references/migration-guide.md` (ActiveRecord) and
`@skills/db-migration/references/migration-guide-python.md` (Django, Alembic).

---

## One-to-one — `has_one` / `belongs_to`

The foreign key lives on the **dependent** side: the row that cannot exist without the other. A
profile cannot exist without its user; a user is fine without a profile. So `profiles.user_id`.

```ruby
class User < ApplicationRecord
  has_one :profile, dependent: :destroy, inverse_of: :user
end

class Profile < ApplicationRecord
  belongs_to :user, inverse_of: :profile
end

# migration — unique: the index IS the one-to-one; without it two concurrent requests create two rows
create_table :profiles, id: :uuid do |t|
  t.references :user, null: false, foreign_key: true, type: :uuid, index: { unique: true }
  t.text :bio
  t.timestamps
end
```

**Indexes** — the unique index on `user_id` serves the only query (`user.profile`) and enforces
the cardinality, in one structure.

**Pitfalls**
- **No unique index is one-to-many in disguise.** `has_one` reads with `LIMIT 1` and no
  `ORDER BY`; the table happily holds two profiles, and which one you get is unspecified.
- **Assigning replaces.** `user.profile = other` removes the existing row — destroyed or deleted
  per `dependent:`, otherwise its foreign key is set to NULL, which `null: false` refuses.
- **Split a table one-to-one only for a reason** — a different lifecycle, wide rarely-read columns
  off a hot row, a different permission boundary. Every split is a join or an extra query, forever.

---

## One-to-many — `has_many` / `belongs_to`

The foreign key lives on the **many** side: `Organization has_many :projects` and
`Project belongs_to :organization` put `organization_id` on `projects`.

```ruby
create_table :projects, id: :uuid do |t|
  # index: false — the composite below leads with organization_id; a single-column index beside
  # it is a second copy of its left prefix, paid for on every write.
  t.references :organization, null: false, foreign_key: true, type: :uuid, index: false
  t.string :name, null: false
  t.timestamps
end
# Equality first, sort last: serves "an organization's projects" and "... newest first", no Sort node.
add_index :projects, [:organization_id, :created_at]
```

**Indexes** — one index leading with the foreign key, the sort column after it. It is also what a
parent `DELETE` uses to find children; without it, every parent delete scans the child table.

### Deleting the parent — `dependent:` vs the database's `on_delete`

| Option | What actually runs | Callbacks | At scale |
|---|---|---|---|
| `dependent: :destroy` | loads every child, one `DELETE` each, in the parent's transaction | yes | N queries holding locks — 50k children is a request that times out |
| `dependent: :delete_all` | one `DELETE … WHERE organization_id = ?` | no | fast, but the grandchildren's `dependent:` never runs — an FK error or orphans one level down |
| `dependent: :destroy_async` | deletes the parent, enqueues a job to destroy the children | yes, later | children outlive their parent, so a foreign key refuses the delete or cascades it synchronously — the Rails guide warns against pairing it with FK constraints |
| `dependent: :nullify` | `UPDATE … SET organization_id = NULL` | no | needs a nullable FK; orphans by design |
| `dependent: :restrict_with_error` | refuses, adds an error to the parent | — | right for business records (invoices, orders) |
| FK `on_delete: :cascade` | the database deletes children in the same statement | no — Rails never sees them | fastest; one transaction, so a large cascade holds locks and spikes WAL |
| FK default (`NO ACTION`) or `on_delete: :restrict` | the database refuses | — | the backstop for every write path, raw SQL included |

Which one is right at scale:
- **Bounded children with no side effects** (an order's line items) → FK
  `foreign_key: { on_delete: :cascade }` and no `dependent:` — one mechanism, not two.
- **Bounded children with side effects** (S3 objects, a search index, Centrifugo publishes) →
  `dependent: :destroy` over the default FK: children go first, inside the parent's transaction.
- **Business records** → `dependent: :restrict_with_error` plus the default FK. An organization
  with invoices is soft-deleted, never cascaded.
- **Unbounded children** (events, audit logs, messages) → nothing in the request. Soft-delete the
  parent; a batched background job purges the children, then the parent.

---

## Many-to-many — `has_many :through` (worked example: memberships, the access-control tables)

**Never `has_and_belongs_to_many`.** A join table without a model cannot carry an attribute (a
role), a validation, a timestamp, or a callback — and the day it needs one you are migrating data
out of a table Rails gives you no class for. The join model costs one file on day one.

**Roles live on the membership, never on `users`.** A `users.role` column gives a person one role
across every organization — admin in one tenant is admin in all of them. The membership is the
(user × organization) pair, so the role belongs to it.

```ruby
class User < ApplicationRecord
  has_many :memberships, dependent: :destroy, inverse_of: :user
  has_many :organizations, through: :memberships
end

class Organization < ApplicationRecord
  has_many :memberships, dependent: :destroy, inverse_of: :organization
  has_many :users, through: :memberships
end

class Membership < ApplicationRecord
  belongs_to :user, inverse_of: :memberships
  belongs_to :organization, inverse_of: :memberships, counter_cache: true

  # Role names are data; what each role may do is code (the permission matrix).
  enum :role, { viewer: "viewer", member: "member", admin: "admin", owner: "owner" }
  validates :user_id, uniqueness: { scope: :organization_id }
end
```

```ruby
class CreateMemberships < ActiveRecord::Migration[7.1]
  def change
    create_table :memberships, id: :uuid do |t|
      t.references :user, null: false, foreign_key: true, type: :uuid, index: false
      t.references :organization, null: false, foreign_key: true, type: :uuid
      t.string :role, null: false
      t.timestamps
      # Changes with the enum, in the same PR — a new role is a code change AND a migration.
      t.check_constraint "role IN ('viewer', 'member', 'admin', 'owner')", name: "chk_memberships_role"
    end
    # One membership per pair — and the index every authorization check hits.
    add_index :memberships, [:user_id, :organization_id], unique: true
    add_column :organizations, :memberships_count, :integer, default: 0, null: false
  end
end
```

**Indexes** — two, each serving queries the other cannot:

| Query | Runs | Index |
|---|---|---|
| `current_user.memberships.find_by!(organization: current_organization)` | every authorized request | unique `[user_id, organization_id]` — also one row per pair |
| `current_user.organizations` | login, organization switcher | the same index, left prefix |
| `organization.memberships.includes(:user)` | members admin page | `organization_id` — not the composite's left prefix |
| `organization.memberships_count` | organization header | none — `counter_cache` |

Lead the composite with the column looked up alone most often; the other gets its own index.
Creating the foreign keys briefly blocks writes on `users` and `organizations`, so a new table
still needs `lock_timeout` (`@skills/std-database/references/locking-and-timeouts.md`).

**Pitfalls**
- **`validates … uniqueness:` races.** Two requests both pass it and both insert; the unique index
  is the guarantee. Rescue `ActiveRecord::RecordNotUnique` where a duplicate is a normal outcome.
- **`organization.users << user` writes a join row with only the two keys**, so the `null: false`
  role fails. Create the join model: `organization.memberships.create!(user:, role:)`.
- **`organization.users` on a 50,000-member organization** loads 50,000 rows. Paginate it, count it
  with `counter_cache`, never iterate it in a request.

Every tenant-owned table carries `organization_id` (`null: false`, foreign key), and its indexes
**lead with it** — `[organization_id, created_at]`, `[organization_id, status]` — because every
query on it is scoped to one organization first.

**When customer admins must create roles at runtime** — and only then — the role becomes a row:
`memberships.role_id` → `roles` (`organization_id`, `name`; unique `[organization_id, name]`) →
`role_permissions` (`role_id`, `permission_key`; unique `[role_id, permission_key]`). Permission
**keys** stay defined in code; the database stores only which role holds which key.

Owned elsewhere — do not duplicate: the permission matrix, its scopes, and when roles become
DB-backed → `@skills/access-control-designer/references/permission-matrix.md`; Pundit policies and
scopes over these tables → `@skills/std-rails-conventions/references/roles-and-permissions.md`.

---

## Polymorphic — `belongs_to :subject, polymorphic: true`

```ruby
class Comment < ApplicationRecord
  belongs_to :subject, polymorphic: true
end

class Post < ApplicationRecord
  has_many :comments, as: :subject, dependent: :destroy
end

# migration — adds subject_type + subject_id AND the composite index on [subject_type, subject_id]
create_table :comments, id: :uuid do |t|
  t.references :subject, polymorphic: true, null: false, type: :uuid
  t.text :body, null: false
  t.timestamps
end
```

**Indexes** — `[subject_type, subject_id]`. `t.references … polymorphic: true` adds it; a
hand-written pair of `add_column`s does not, and every `post.comments` becomes a sequential scan.

**Pitfalls**
- **No foreign key is possible.** `subject_id` points at a different table per row, so the
  database cannot check it. Delete a post with `delete_all` or raw SQL and its comments point at
  nothing — silently, forever. Cascades happen only through each parent's `dependent:`.
- **`subject_type` stores class names.** Renaming `Post` is a data migration over every comment.
- **You cannot join through it.** `Comment.joins(:subject)` raises; `includes(:subject)` works by
  issuing one query per type.

**When the type set is small and closed, prefer an alternative:**

1. **Separate nullable foreign keys + a CHECK** — real foreign keys, real cascades, joinable:
   ```ruby
   create_table :comments, id: :uuid do |t|
     t.references :post, foreign_key: true, type: :uuid   # nullable
     t.references :task, foreign_key: true, type: :uuid   # nullable
     t.text :body, null: false
     t.timestamps
     t.check_constraint "num_nonnulls(post_id, task_id) = 1", name: "chk_comments_one_subject"
   end

   class Comment < ApplicationRecord
     belongs_to :post, optional: true
     belongs_to :task, optional: true
     def subject = post || task
   end
   ```
2. **`delegated_type`** — when the rows are one entity with type-specific detail (an `Entry` that
   is a `Message` or a `Comment`): shared columns in one table, a closed `types:` list, generated
   predicates and scopes (`entry.message?`, `Entry.messages`). It is polymorphic underneath
   (`entryable_type`, `entryable_id`), so it closes the type list — not the integrity gap:
   `delegated_type :entryable, types: %w[Message Comment], dependent: :destroy`.

Keep plain polymorphic for genuinely open type sets — an audit log, an activity feed, attachments
— where an orphan is tolerable or a cleanup job owns it.

---

## Self-referential

**A tree** — each user has at most one manager:

```ruby
class User < ApplicationRecord
  belongs_to :manager, class_name: "User", optional: true, inverse_of: :reports
  has_many :reports, class_name: "User", foreign_key: :manager_id,
                     inverse_of: :manager, dependent: :nullify
end

# migration — new or small users table; a large live one takes validate: false + a concurrent index
add_reference :users, :manager, type: :uuid, foreign_key: { to_table: :users }
add_check_constraint :users, "manager_id <> id", name: "chk_users_not_own_manager"
```

The CHECK stops a self-loop, not a cycle (A manages B manages A). A cycle needs an application
validation, serialized moves, and a `CYCLE` guard on every walk. How to walk the tree, and when
`ancestry`, `closure_tree`, or `ltree` is worth its write cost over a recursive query →
`@skills/std-database/references/hierarchies.md`.

**A graph** — users follow users: many-to-many with itself, so it gets a join model:

```ruby
class User < ApplicationRecord
  has_many :active_follows, class_name: "Follow", foreign_key: :follower_id,
                            inverse_of: :follower, dependent: :destroy
  has_many :passive_follows, class_name: "Follow", foreign_key: :followed_id,
                             inverse_of: :followed, dependent: :destroy
  has_many :following, through: :active_follows, source: :followed
  has_many :followers, through: :passive_follows, source: :follower
end

class Follow < ApplicationRecord
  belongs_to :follower, class_name: "User", inverse_of: :active_follows
  belongs_to :followed, class_name: "User", inverse_of: :passive_follows
end

# migration
create_table :follows, id: :uuid do |t|
  t.references :follower, null: false, type: :uuid, foreign_key: { to_table: :users }, index: false
  t.references :followed, null: false, type: :uuid, foreign_key: { to_table: :users }
  t.timestamps
  t.check_constraint "follower_id <> followed_id", name: "chk_follows_not_self"
end
add_index :follows, [:follower_id, :followed_id], unique: true
```

The same shape as memberships: the unique composite serves "who do I follow", the `followed_id`
index serves "who follows me".

---

## Options that change what the database sees

- **`inverse_of`** — Rails finds inverses on its own only for plain associations; it gives up when
  a side has `foreign_key:`, `:through`, or a scope. Without it, `membership.user` loads a second
  copy of a user you already hold, and a change to one copy is invisible to the other. Declare it
  wherever `foreign_key:` or a scope appears — in practice, next to every `class_name:`.
- **`counter_cache: true`** — needs `<children>_count` (`integer, default: 0, null: false`) on the
  parent. Every child create or destroy is an `UPDATE` of the parent row, so a parent with many
  concurrent writers becomes one row lock they all queue on. `insert_all`, `delete_all`, and raw
  SQL bypass it and the count drifts; repair with `reset_counters` from a background job. A
  counter counts every row, so it is a valid badge only for a caller whose scope covers every row
  (`org`) → `@skills/std-api-design/references/drill-down-resources.md`.
- **`touch: true`** — every child save updates the parent's `updated_at`, fires its `after_touch`,
  and continues up the parent's own `touch:`. Right for cache keys; on a hot parent, the same
  row-lock queue as `counter_cache`.
- **`strict_loading`** — `has_many :memberships, strict_loading: true`, or `User.strict_loading`
  on a relation, raises `ActiveRecord::StrictLoadingViolationError` on a lazy load: an N+1 becomes
  a failing test instead of a slow page. Roll it out with
  `config.active_record.action_on_strict_loading_violation = :log` first.
- **Required `belongs_to` + `null: false`** — `belongs_to` is required by default, and that
  requirement is a validation. The column needs `null: false` and a foreign key to match;
  `optional: true` belongs with a nullable column. A mismatch is a bug only some write paths hit.

---

## Django ORM and SQLAlchemy 2.0 equivalents

Same design, same indexes, same constraints — different spellings.

| Rails | Django ORM | SQLAlchemy 2.0 |
|---|---|---|
| `has_one` / `belongs_to` | `OneToOneField(User, on_delete=models.CASCADE, related_name="profile")` — unique index created | `mapped_column(ForeignKey("users.id"), unique=True)`; the parent's `Mapped[Optional["Profile"]]` infers `uselist=False` |
| `has_many` / `belongs_to` | `ForeignKey(Organization, on_delete=models.PROTECT, related_name="projects")` — index created | `mapped_column(ForeignKey("organizations.id"), index=True)` — **`index=True` is on you** |
| `has_many :through` | `ManyToManyField(User, through="Membership", related_name="organizations")` | an association object — a mapped `Membership` class holding both keys |
| unique `[a_id, b_id]` | `UniqueConstraint(fields=["user", "organization"], name=...)` in `Meta.constraints` | `UniqueConstraint("user_id", "organization_id")` in `__table_args__` |
| `polymorphic: true` | `GenericForeignKey("content_type", "object_id")` — caveats below | nothing built in; use separate foreign keys + CHECK |
| self-referential | `ForeignKey("self", null=True, on_delete=models.SET_NULL, related_name="reports")`; a graph is `ManyToManyField("self", through="Follow", symmetrical=False)` | `relationship(back_populates="reports", remote_side=[id])` on the many-to-one side |
| `inverse_of` | automatic | `back_populates=` on both sides |
| `dependent:` | `on_delete=` | `ondelete=` on `ForeignKey` (database) or `cascade=` on `relationship` (ORM) |
| `strict_loading` | none built in — pin counts with `assertNumQueries` | `lazy="raise"` |
| `has_and_belongs_to_many` (never) | `ManyToManyField` without `through=` — the same trap | `relationship(secondary=...)` — the same trap |

**Django caveats**
- **`on_delete` is emulated in Python.** The ORM's delete collector finds related rows and deletes
  them itself — fetching them into memory whenever signals or further cascades are involved — and
  the database constraint carries no `ON DELETE` action. `CASCADE` over a large child set is the
  `dependent: :destroy` problem, and a raw SQL delete of the parent is refused, not cascaded.
  Recent Django releases add database-level variants; on Django 5.x the emulation is all there is.
- **A join model's two `ForeignKey`s each get an index, and the `UniqueConstraint` adds a third** —
  set `db_index=False` on the key that leads the constraint, as `index: false` does in Rails.
- **`GenericForeignKey` has every polymorphic pitfall and two more.** Django does not index it —
  add `models.Index(fields=["content_type", "object_id"])` yourself — and `object_id`'s type must
  match every target's primary key (UUID keys need a `UUIDField`; a text column of mixed types
  defeats the index with casts). No `filter()` or `select_related()` through it;
  `prefetch_related()` works. `GenericRelation` on the target gives ORM-level cascade only.
- **Always set `related_name`.** The default `<model>_set` is unreadable, and two foreign keys to
  the same model clash until you do.

**SQLAlchemy caveats**
- **`ForeignKey` columns need `index=True`.** Nothing adds it — not SQLAlchemy, not Alembic
  autogenerate, not PostgreSQL.
- **An association object, not `secondary=`**, for the reason `has_many :through` beats HABTM:

  ```python
  class Membership(Base):
      __tablename__ = "memberships"
      __table_args__ = (UniqueConstraint("user_id", "organization_id"),)

      id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
      # No index=True: the unique constraint leads with user_id and serves it.
      user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
      organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
      role: Mapped[str]

      user: Mapped["User"] = relationship(back_populates="memberships", lazy="raise")
      organization: Mapped["Organization"] = relationship(back_populates="memberships", lazy="raise")
  ```
- **`lazy="raise"`** so an unloaded access fails loudly; load explicitly with `selectinload()`
  (collections) or `joinedload()` (many-to-one). An async session fails a lazy load anyway, but
  with an error that never names the relationship.
- **`ondelete="CASCADE"` + `passive_deletes=True`** lets the database cascade without the ORM
  loading children first; `cascade="all, delete-orphan"` without it is `dependent: :destroy`.
