# Roles & Permissions — a policy asks for a key; the matrix decides who holds it

Load-bearing rules restated (hold even if you read nothing else):

1. **A policy checks a permission key, never a role name.** `permitted?("orders.cancel")`, not
   `user.admin?`. The key is the one grep that joins the matrix, the policy, and the CASL gate.
2. **The role lives on the membership (user × organization), and `pundit_user` carries it.** A
   policy handed a bare `current_user` cannot know *which* organization's role applies.
3. **`role` and `role_id` never appear in `permitted_attributes`.** A role changes only through
   `RoleAssignmentPolicy`: within the granter's own permissions, never the granter's own role (up or
   down), never stranding the last Owner. The audit event and the `permissions_version` bump commit
   in the same transaction as the change.
4. **Deny by default.** A key absent from a role's row is `:none`, a key absent from the catalog
   raises, and a policy action nobody wrote returns `false`.

Making the policy run at all (`verify_authorized`, `policy_scope`, 404-not-403) is
`authorization.md`, not repeated here. The 403 body is owned by
`../../std-api-design/references/errors-rails.md`.

Owned elsewhere — do not duplicate: keys, scopes, the sample matrix, its doc-drift spec, and when to
go DB-backed → `@skills/access-control-designer/references/permission-matrix.md`; the `/me`
contract, the scope → condition table, and per-record `actions` →
`@skills/access-control-designer/references/ui-gates.md`; what each role sees →
`@skills/ui-ux-patterns/references/role-based-ux.md`; what each UI state looks like (disabled with a
reason, read-only, locked, 403 vs 404, masked) →
`@skills/ui-ux-patterns/references/role-based-ux-states.md`; the memberships, roles, and role_permissions
tables with their indexes and query plan → `@skills/std-database/references/relationships.md`;
migration naming, `lock_timeout`, and reversibility → the `std-database` skill.

---

## What authorization adds to those tables

```ruby
# db/migrate/20260910090000_add_permission_tracking.rb  ✅  memberships itself → relationships.md
class AddPermissionTracking < ActiveRecord::Migration[7.1]
  def change
    # A constant default is metadata-only on Postgres 11+: no table rewrite.
    add_column :memberships, :permissions_version, :integer, null: false, default: 0

    create_table :role_assignment_events, id: :uuid do |t| # append-only
      t.references :organization, null: false, foreign_key: true, type: :uuid
      t.references :user, null: false, foreign_key: true, type: :uuid # the member affected
      t.references :actor, null: false, foreign_key: { to_table: :users }, type: :uuid
      t.string :from_role # null on the first grant
      t.string :to_role   # null on removal
      t.timestamps
    end
  end
end
```

`permissions_version` is the `version` on `/me`. The event names the member by `user_id` +
`organization_id`, the membership's natural key. A foreign key to the membership itself would either
block a removal or cascade the trail away. Append-only takes two layers: `def readonly? = persisted?`
on the model, and a `BEFORE UPDATE OR DELETE` trigger that raises. The trigger is needed because
`update_all`, `delete_all`, and a console session all skip `readonly?`.

## The catalog and the matrix

In a Rails-only product these constants *are* the source of truth. permission-matrix.md's doc spec
reads them as `PermissionMatrix::ROLES` and `PermissionCatalog::KEYS`.

```ruby
# app/authorization/permission_catalog.rb  ✅  every key, and what each resource maps to
module PermissionCatalog
  KEYS = %w[
    orders.read orders.create orders.update orders.cancel orders.approve orders.export
    members.read members.invite roles.assign billing.update
  ].to_set.freeze

  ENTITLEMENTS = { "orders.approve" => "approvals", "orders.export" => "exports" }.freeze

  # resource → CASL subject type, and the column each scope filters on
  SUBJECTS = {
    "orders" => { type: "Order", own: :user_id, team: :team_id },
    "members" => { type: "Member", own: :user_id, team: :team_id },
    "roles" => { type: "Role" },
    "billing" => { type: "Billing" }
  }.freeze

  # A typo must fail a spec, not deny in production and get triaged as "missing access".
  def self.fetch!(key) = KEYS.include?(key) ? key : raise(KeyError, "unknown permission key: #{key}")
  def self.subject(key) = SUBJECTS.fetch(fetch!(key).split(".").first)
end

# app/authorization/permission_matrix.rb  ✅  role → key → scope; absent means :none
module PermissionMatrix
  LEVELS = %i[none own team org all].freeze # ordered: each level contains the one before it

  ROLES = {
    # Listed like every other role. "The Owner gets every key" would grant every future key too.
    "owner" => { "orders.read" => :org, "orders.create" => :org, "orders.update" => :org,
                 "orders.cancel" => :org, "orders.approve" => :org, "orders.export" => :org,
                 "members.read" => :org, "members.invite" => :org, "roles.assign" => :org,
                 "billing.update" => :org },
    # "admin" and "manager": one entry per granted cell of the documented table, the same way
    "member" => { "orders.read" => :own, "orders.create" => :own, "orders.update" => :own,
                  "members.read" => :team },
    "viewer" => { "orders.read" => :org, "orders.export" => :org }
  }.freeze

  def self.covers?(held, needed) = LEVELS.index(held) >= LEVELS.index(needed)
end
```

`:all` crosses tenants. It belongs to platform staff, who live outside customer memberships, so it
never appears here.

## Tenancy: `pundit_user` carries the membership

```ruby
# app/authorization/user_context.rb  ✅  what every policy and scope receives
class UserContext
  attr_reader :user, :membership

  def initialize(user:, membership:)
    @user = user
    @membership = membership
  end

  # Memoized: one lookup per request, however many policies or serialized rows ask.
  def permissions = @permissions ||= membership ? EffectivePermissions.for(membership) : {}
  def team_ids = @team_ids ||= membership ? membership.team_ids : []
  def level(key) = permissions.fetch(PermissionCatalog.fetch!(key), :none)
  def granted?(key) = level(key) != :none # role + scope only: no record, no entitlement
end

# app/authorization/effective_permissions.rb  ✅  code-defined: a frozen constant, nothing to cache
module EffectivePermissions
  # The widest scope per key across the membership's roles, inside THIS organization only.
  def self.for(membership)
    membership.role_names.map { |role| PermissionMatrix::ROLES.fetch(role) }.reduce({}) do |acc, grants|
      acc.merge(grants) { |_key, held, other| PermissionMatrix.covers?(held, other) ? held : other }
    end
  end
end

# app/controllers/application_controller.rb  ✅  (Pundit wiring and verify_* → authorization.md)
class ApplicationController < ActionController::API
  private

  def pundit_user
    @pundit_user ||= UserContext.new(user: current_user, membership: current_membership)
  end

  # Found THROUGH current_user: a non-member gets RecordNotFound (404), never a borrowed role.
  # No organization on the request means no membership, so every key is :none.
  def current_membership
    org_id = params[:organization_id] || request.headers["X-Organization-Id"]
    return if org_id.blank?

    @current_membership ||= current_user.memberships.find_by!(organization_id: org_id)
  end
end
```

Never read the role from a JWT claim. A demoted admin keeps the claim until the token expires, while
the membership row changes the moment the grant commits.

## `ApplicationPolicy`: `permitted?(key)` and `scope_level(key)`

```ruby
# app/policies/application_policy.rb  ✅  keep the generated index?/show?/... that return false
class ApplicationPolicy
  attr_reader :context, :record

  def initialize(context, record)
    @context = context
    @record = record
  end

  # A per-record `actions` entry: only for a permitted action that this record blocks right now.
  def blocked_state(key, reason_code)
    { enabled: false, reasonCode: reason_code } if reason_code && permitted?(key)
  end

  private

  def user = context.user
  def membership = context.membership
  def scope_level(key) = context.level(key)

  # Effective access = permission AND entitlement, so no policy can forget the plan.
  def permitted?(key)
    level = scope_level(key)
    return false if level == :none || !entitled?(key)
    return true unless record.is_a?(ActiveRecord::Base) # a class or a symbol asks "ever?"

    within?(key, level)
  end

  def entitled?(key)
    feature = PermissionCatalog::ENTITLEMENTS[key]
    feature.nil? || membership.organization.entitlements.include?(feature)
  end

  def within?(key, level)
    return true if level == :all
    return false unless record.organization_id == membership.organization_id
    return true if level == :org

    value = record.public_send(PermissionCatalog.subject(key).fetch(level))
    level == :team ? context.team_ids.include?(value) : value == user.id
  end

  class Scope
    def initialize(context, scope)
      @context = context
      @scope = scope
    end

    private

    # One implementation for every model: the caller's level for the key becomes a where clause.
    def scope_for(key)
      level = @context.level(key)
      return @scope.none if level == :none
      return @scope.all if level == :all

      tenant = @scope.where(organization_id: @context.membership.organization_id)
      return tenant if level == :org

      match = level == :team ? @context.team_ids : @context.user.id
      tenant.where(PermissionCatalog.subject(key).fetch(level) => match)
    end
  end
end

# app/policies/order_policy.rb  ✅  key + scope + record state; no role names anywhere
class OrderPolicy < ApplicationPolicy
  def show? = permitted?("orders.read")
  def update? = permitted?("orders.update") && record.pending?
  def cancel? = permitted?("orders.cancel") && cancel_blocked_by.nil?
  def approve? = permitted?("orders.approve") && approve_blocked_by.nil?

  # Record state needs an instance: ask `policy(order)`, never `policy(Order)`.
  def cancel_blocked_by = ("ORDER_SHIPPED" if record.shipped?)
  def approve_blocked_by = ("SELF_APPROVAL" if record.created_by_id == user.id) # separation of duties
  def permitted_attributes = %i[notes delivery_window]

  class Scope < ApplicationPolicy::Scope
    def resolve = scope_for("orders.read")
  end
end

# app/serializers/order_serializer.rb  ✅  build one per call: Panko serializers are single-use
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :actions
  # Every column a CASL condition names, camelCased, or every scoped rule evaluates false.
  aliases user_id: :userId, team_id: :teamId, organization_id: :organizationId

  def actions
    policy = OrderPolicy.new(context.fetch(:user_context), object)
    { cancel: policy.blocked_state("orders.cancel", policy.cancel_blocked_by),
      approve: policy.blocked_state("orders.approve", policy.approve_blocked_by) }.compact
  end
end
```

A CASL rule can say no but not *why*, and the why is what makes a disabled button usable, so record
state travels on the record. Lists pass the same `context:` to `Panko::ArraySerializer`.
`UserContext` memoizes, so extra rows cost no extra permission or team lookups.

## `/me`: this organization's rules, and nothing more

```ruby
# app/authorization/ability_rules.rb  ✅  the /me rules generator (contract: ui-gates.md)
module AbilityRules
  def self.for(ctx)
    ctx.permissions.filter_map do |key, level|
      next if level == :all # platform staff only; never sent to a customer client

      action = key.split(".").last
      rule = { action:, subject: PermissionCatalog.subject(key).fetch(:type) } # orders → Order
      action == "create" ? rule : rule.merge(conditions: conditions(ctx, key, level))
    end
  end

  # camelCase, or CASL reads `user_id` off a camelCase record as undefined and the rule is silently
  # false. `organizationId` rides on every condition, so cached rows from another org never match.
  def self.conditions(ctx, key, level)
    tenant = { organizationId: ctx.membership.organization_id }
    return tenant if level == :org

    column = PermissionCatalog.subject(key).fetch(level).to_s.camelize(:lower).to_sym
    tenant.merge(column => level == :team ? { "$in" => ctx.team_ids } : ctx.user.id)
  end
  private_class_method :conditions
end

# app/serializers/current_user_serializer.rb  ✅  GET /api/v1/me, serialized from current_user
class CurrentUserSerializer < Panko::Serializer
  attributes :id, :roles, :entitlements, :permissions
  aliases organization_id: :organizationId

  def organization_id = membership.organization_id
  def roles = membership.role_names # display only; no gate reads it
  def entitlements = membership.organization.entitlements
  def permissions = { version: membership.permissions_version, rules: AbilityRules.for(user_context) }

  private

  def user_context = context.fetch(:user_context)
  def membership = user_context.membership
end
```

The controller calls `skip_authorization`, because the caller is reading themselves and every rule is
already theirs. It raises `ActiveRecord::RecordNotFound` when the request names no organization, then
renders `{ data: CurrentUserSerializer.new(context: { user_context: pundit_user }).serialize(current_user) }`.
Checked against Panko 0.8.4, that output is byte-for-byte the shape ui-gates.md pins. A matrix edit
that changes a role's grants ships a data migration that bumps that role's memberships. The gates
these rules drive are UX only; every endpoint behind them still authorizes here.
`permissions_version` also belongs in the ETag of every permission-scoped response. Without it, a
demoted member earns a `304` for data they can no longer read →
`@skills/std-api-design/references/drill-down-resources.md`.

## Granting a role: the escalation path, guarded

```ruby
# app/policies/membership_policy.rb (excerpt)  ✅  never :role / :role_id — one PATCH would self-promote
def permitted_attributes = %i[title notification_preference]

# app/policies/role_assignment_policy.rb  ✅  record: RoleAssignment = Data.define(:membership, :role)
class RoleAssignmentPolicy < ApplicationPolicy
  def create?
    permitted?("roles.assign") && same_tenant? && !self_grant? && !strands_organization? &&
      within_own?(record.role) && record.membership.role_names.all? { |role| within_own?(role) }
  end

  private

  def same_tenant? = record.membership.organization_id == membership.organization_id
  def self_grant? = record.membership.user_id == user.id # up or down: another member makes the change
  def strands_organization? = record.membership.last_owner? && record.role != "owner"

  # Same keys, no wider scope. The member's CURRENT roles must fit too, or an Admin "grants" the
  # Owner a demotion.
  def within_own?(role)
    grants = PermissionMatrix::ROLES.fetch(role) { return false } # an unknown role is denied
    grants.all? { |key, level| PermissionMatrix.covers?(scope_level(key), level) }
  end
end
```

```ruby
# app/models/membership.rb (excerpt, inside the class)
after_update_commit :publish_permissions_changed, if: :saved_change_to_permissions_version?

def role_names = [role] # one role column; roles hung off the membership would return several
def last_owner? = role == "owner" && Membership.where(organization_id:, role: "owner").count == 1

def publish_permissions_changed # after commit, so a refetch cannot beat the change (ui-gates.md)
  CentrifugoPublisher.publish("user:#{user_id}",
                              { event: "permissions_changed", version: permissions_version })
end

# app/services/memberships/assign_role.rb  ✅  the change, its event, and its version commit together
module Memberships
  AssignRole = Data.define(:actor, :membership, :role) do
    def call
      ActiveRecord::Base.transaction do
        # The policy's last-owner check races: two Owners demoting each other at once each count two
        # Owners, and both pass. Lock the organization row, reload, and recheck under the lock.
        membership.organization.lock!
        membership.reload
        next Result.failure(:last_owner) if membership.last_owner? && role != "owner"

        RoleAssignmentEvent.create!(organization_id: membership.organization_id,
                                    user_id: membership.user_id, actor:,
                                    from_role: membership.role, to_role: role)
        membership.update!(role:, permissions_version: membership.permissions_version + 1)
        Result.success(membership)
      end
    end
  end
end
```

The event commits inside the transaction, not in `after_commit` or a job. If a process dies between
the commit and a later write, the role has changed and the trail says it didn't. The controller finds
the target through `policy_scope(Membership)`, so another tenant's member is a 404. It then calls
`authorize RoleAssignment.new(membership: target, role: params.require(:role))`. Removing a member
runs the same guard and writes `to_role: nil`.

## Navigation: a headless policy on the same keys

```ruby
# app/policies/navigation_policy.rb  ✅  headless: `policy(:navigation)`; no record, no role names
class NavigationPolicy < ApplicationPolicy
  # The key each destination authorizes with, so a visible link never 403s. Role grant only: a
  # plan-gated item stays visible and locked (role-based-ux.md), which is what `locked?` answers.
  def orders? = context.granted?("orders.read")
  def approvals? = context.granted?("orders.approve")
  def members? = context.granted?("members.read")
  def billing? = context.granted?("billing.update")
  # Takes the nav item's entitlement, a plan feature name ("approvals", as in nav.ts and /me), never a
  # permission key: `entitled?(key)` maps keys to features and would call every feature entitled.
  def locked?(feature) = !membership.organization.entitlements.include?(feature)
end
```

The controller passes the answers down as props, `nav: { orders: nav.orders?, … }` for the sidebar
and `can_cancel: policy(order).cancel?` per row. Phlex components never call Pundit
(`std-phlex-conventions`).

## DB-backed: when customer admins create roles

Keys stay in `PermissionCatalog`. The `roles` and `role_permissions` tables come from
relationships.md, and authorization adds four things to them:

- **Seeded system roles.** `roles.organization_id` is null for system roles, which are seeded from
  `PermissionMatrix` and read-only. Make the `[organization_id, name]` index unique **with
  `nulls_not_distinct: true`**. Postgres treats NULLs as distinct, so without it two system roles
  named `admin` would both insert.
- **A `scope` column.** `role_permissions.scope` gets a CHECK holding it to `own`/`team`/`org`, so no
  customer-defined role can reach `:all`.
- **Write-time key validation.** `RolePermission` validates `permission_key` with
  `inclusion: { in: PermissionCatalog::KEYS }`. That is the write-time half of the orphaned-key
  check; the CI half is permission-matrix.md's. It also declares `belongs_to :role, touch: true`.
- **Grants read the database.** `within_own?` reads the target role's rows instead of
  `PermissionMatrix::ROLES`. Editing a custom role applies the same subset rule to each permission it
  adds, and bumps `permissions_version` for that role's memberships in the same transaction.

```ruby
# app/authorization/effective_permissions.rb  ✅  DB-backed: now there is something to cache
module EffectivePermissions
  TTL = 10.minutes

  # A grant changes the membership row; a custom-role edit touches the role and none of its
  # memberships. Key on both versions, or one of those two changes serves stale access.
  def self.for(membership)
    role = membership.role
    key = ["effective-permissions", membership.cache_key_with_version, role.cache_key_with_version]
    Rails.cache.fetch(key, expires_in: TTL) do
      role.role_permissions.pluck(:permission_key, :scope).to_h { |name, scope| [name, scope.to_sym] }
    end
  end
end
```

The code-defined variant needs no cache at all. A Redis round trip is slower than a lookup in a
frozen constant.

## Specs: the matrix is the table

```ruby
# spec/policies/order_policy_spec.rb  ✅  every role × key × reach; a new role or key adds its rows
RSpec.describe OrderPolicy do
  checks = { "orders.read" => :show?, "orders.update" => :update?, "orders.cancel" => :cancel?,
             "orders.approve" => :approve? }
  orders = {
    own: lambda { |m|
      create(:order, :pending, organization: m.organization, team: m.teams.first, user: m.user)
    },
    teammate: ->(m) { create(:order, :pending, organization: m.organization, team: m.teams.first) },
    other_tenant: ->(_m) { create(:order, :pending) } # the factory builds a fresh organization
  }
  reach = { own: %i[own team org all], teammate: %i[team org all], other_tenant: %i[all] }

  PermissionMatrix::ROLES.each do |role, grants|
    checks.each do |key, method|
      orders.each do |row, build|
        expected = reach[row].include?(grants.fetch(key, :none))

        it "should #{expected ? 'permit' : 'deny'} #{method} when a #{role} targets a #{row} order" do
          membership = create(:membership, :with_team, :fully_entitled, role:)
          order = instance_exec(membership, &build) # `create` lives on the example, not the group
          context = UserContext.new(user: membership.user, membership:)
          expect(described_class.new(context, order).public_send(method)).to be(expected)
        end
      end
    end
  end
end
```

The fixtures hold every other input permissive: the organization is entitled, and the order is
pending and created by someone else. That way the table measures the matrix alone, and entitlement,
record state, and separation of duties each get their own examples. Escalation gets request specs,
one per guard, each proving the guard refuses:

| Guard | Request | Expect |
|---|---|---|
| `role` not permitted | a Member `PATCH`es their own membership with `role: "owner"` | role unchanged on reload |
| Grant within own | an Admin grants `owner` | 403; role unchanged; no event |
| Current role within own | an Admin demotes the Owner | 403 |
| No self-grant | an Owner changes their own role, even down | 403 |
| Last owner | the sole Owner is removed | refused; the organization keeps its Owner |
| Tenant | an Admin of one organization grants in another | 404, not 403 (`authorization.md`) |
| Audit | any successful grant | exactly one `RoleAssignmentEvent`; `permissions_version` + 1 |

The first row is why a role change never goes through `permit`, and it is the one that ships broken.
`permit` drops an unlisted `role` without an error, so the response is `200` whether or not `role`
is in the list. Only a spec that reloads the record can tell the two apart.
