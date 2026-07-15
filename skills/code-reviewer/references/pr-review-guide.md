# PR Review Guide — Stack-Specific Checks

## Rails Red Flags
```ruby
# RED FLAG: Business logic in controller
class OrdersController < ApplicationController
  def create
    order = Order.new(order_params)
    order.calculate_tax  # Should be in a service
    order.apply_discount # Should be in a service
    order.save!
    render json: order   # Should use Panko serializer
  end
end

# GREEN: Proper separation
class OrdersController < ApplicationController
  def create
    result = CreateOrder.new(user: current_user, params: order_params).call
    if result.success?
      render json: { data: OrderDetailSerializer.new.serialize(result.value) }, status: :created
    else
      render json: { error: result.error, code: 422 }, status: :unprocessable_entity
    end
  end
end
```

## N+1 Query Detection
```ruby
# RED FLAG: N+1 on association
def index
  orders = Order.where(user: current_user)
  # Each order.customer triggers a separate query
  render json: Panko::ArraySerializer.new(orders, each_serializer: OrderSerializer).to_a
end

# GREEN: Eager loading
def index
  orders = Order.where(user: current_user).includes(:customer, :line_items)
  render json: Panko::ArraySerializer.new(orders, each_serializer: OrderSerializer).to_a
end
```

## Migration Safety Checks
```ruby
# RED FLAG: Non-reversible migration
def change
  remove_column :users, :legacy_field  # What type was it? Can't rollback
end

# GREEN: Explicit reversible
def change
  remove_column :users, :legacy_field, :string, default: ""
end

# RED FLAG: Missing index on foreign key
add_reference :orders, :customer  # No index!

# GREEN: With index
add_reference :orders, :customer, null: false, foreign_key: true, index: true
```

## PostGIS Spatial Checks
```ruby
# RED FLAG: Missing spatial index
create_table :locations do |t|
  t.st_point :coordinates, geographic: true, srid: 4326
end
# No index added!

# GREEN: With GiST index
create_table :locations do |t|
  t.st_point :coordinates, geographic: true, srid: 4326
end
add_index :locations, :coordinates, using: :gist

# RED FLAG: Using ST_Distance for filtering (doesn't use spatial index)
Location.where("ST_Distance(coordinates, ?) < ?", point, 5000)

# GREEN: Using ST_DWithin (uses spatial index)
Location.where("ST_DWithin(coordinates::geography, ?::geography, ?)", point, 5000)
```

## React Native Red Flags
```typescript
// RED FLAG: Server data in Zustand
const useOrderStore = create((set) => ({
  orders: [],
  fetchOrders: async () => {
    const orders = await api.orders.list();
    set({ orders });  // Server data should be in TanStack Query!
  },
}));

// GREEN: Server data in TanStack Query
const useOrders = () =>
  useQuery({
    queryKey: ['orders'],
    queryFn: api.orders.list,
    staleTime: 60_000,
  });

// RED FLAG: useEffect for data fetching
useEffect(() => {
  fetch('/api/orders').then(setOrders);
}, []);

// GREEN: TanStack Query
const { data: orders } = useOrders();
```

```typescript
// RED FLAG: ScrollView for long list
<ScrollView>
  {items.map(item => <ItemCard key={item.id} item={item} />)}
</ScrollView>

// GREEN: FlatList with optimization
<FlatList
  data={items}
  renderItem={renderItem}
  keyExtractor={keyExtractor}
  getItemLayout={getItemLayout}
/>
```

## Sidekiq Job Checks
```ruby
# RED FLAG: Passing ActiveRecord object to job
OrderNotificationJob.perform_later(order)  # Serializes entire object!

# GREEN: Pass ID
OrderNotificationJob.perform_later(order.id)

# RED FLAG: Non-idempotent job
class ChargeJob < ApplicationJob
  def perform(order_id)
    order = Order.find(order_id)
    PaymentGateway.charge(order.total)  # Double charge if retried!
  end
end

# GREEN: Idempotent job
class ChargeJob < ApplicationJob
  # One retry policy, where it is enforced. WITHOUT this line Sidekiq applies its default —
  # 25 retries over ~20 days — to a payment. And `retry_on ..., attempts: 5` does NOT cap it:
  # ActiveJob retries first, then hands the failure back to Sidekiq for its 25.
  sidekiq_options retry: 5

  # The last moment anyone can act. Without it the job dies into the Dead set and the
  # customer is simply never charged, silently.
  sidekiq_retries_exhausted { |job, ex| Sentry.capture_exception(ex, extra: { args: job["args"] }) }

  def perform(order_id)
    order = Order.find(order_id)
    return if order.charged?  # cheap guard — an optimisation, NOT the correctness
    # The KEY is what makes retry #5 safe: two workers can both pass the guard above, so
    # only the server-side dedupe actually prevents the double charge. Derive it from the
    # work, never per attempt — a fresh uuid each try defeats the whole mechanism.
    PaymentGateway.charge(order.total, idempotency_key: "order-#{order.id}-charge")
    order.update!(charged: true)
  end
end
```

See `../std-error-handling/references/background-jobs.md` for the retry semantics in full.

## Security Checks
```ruby
# RED FLAG: String interpolation in query
User.where("email = '#{params[:email]}'")  # SQL injection!

# GREEN: Parameterized
User.where(email: params[:email])

# RED FLAG: Mass assignment
User.create(params[:user].to_unsafe_h)  # Allows any field!

# GREEN: Strong parameters
User.create(user_params)  # Only permitted fields
```

## Checks earned from real defects

Every check below exists because this exact bug shipped in guidance the team trusted. They are
grouped here because they share a property: **nothing fails, nothing raises, and the diff looks
fine.** Each is a grep, not a judgement call.

### The policy nobody called

```ruby
# RED FLAG: authenticated, and completely unauthorized
def index
  @orders = Order.includes(:line_items)          # every order in the system, to any signed-in user
end

def show
  @order = Order.find(params[:id])               # any user can read any order by guessing an id
end
```

```ruby
# GREEN
def index
  @orders = policy_scope(Order).includes(:line_items)   # policy_scope FILTERS; authorize does not
end

def show
  @order = policy_scope(Order).find(params[:id])        # 404, not 403 — a 403 confirms it exists
  authorize @order
end
```

**Grep the controller for `authorize` / `policy_scope`, and `ApplicationController` for
`after_action :verify_authorized`.** A policy file existing proves nothing: the failure is that
nobody *called* it, and it returns `200 OK` with another user's data while raising nothing. This
is OWASP #1 and it is invisible in review precisely because `OrderPolicy` looks careful.
→ `../std-rails-conventions/references/authorization.md`

### The migration that waits

```ruby
# RED FLAG: no lock_timeout
def change
  add_column :orders, :status, :string          # millisecond-fast... and a full outage
end
```

`ALTER TABLE` needs `ACCESS EXCLUSIVE`, which blocks `SELECT`. If any slow query holds the
table, your fast migration **waits** — and every query arriving after it queues behind *it*. The
default `lock_timeout` is **0: wait forever**. Failing is the good outcome.

```ruby
# GREEN
def change
  execute "SET lock_timeout = '5s'"
  add_column :orders, :status, :string
end
```

→ `../std-database/references/locking-and-timeouts.md`

### The column drop that 500s

```ruby
# RED FLAG: drop first, ask later
remove_column :orders, :legacy_status, :string
```

ActiveRecord **caches the column list**. A running instance still selects the dropped column and
every query explodes with `PG::UndefinedColumn` — including for rows it never touched. The
`ignored_columns` deploy must land **first**, and alone.

```ruby
# GREEN — deploy 1, by itself
class Order < ApplicationRecord
  self.ignored_columns += ["legacy_status"]
end
# deploy 2: remove_column :orders, :legacy_status, :string
```

→ `../db-migration/references/migration-guide.md`

### The transaction that commits half

```ruby
# RED FLAG: non-bang inside a transaction
ActiveRecord::Base.transaction do
  order = Order.create(attrs)      # returns FALSE on failure — no raise, no rollback
  order.line_items.create(items)   # ...so the block completes and commits half the operation
end
```

```ruby
# GREEN
ActiveRecord::Base.transaction do
  order = Order.create!(attrs)     # raises -> rolls back
  order.line_items.insert_all!(items)
end
```

Also check: **`after_commit`, not `after_save`**, for anything the outside world sees. A Sidekiq
job enqueued inside the transaction can start — and fail to find the row — before the commit
lands.

### The trace that dies at the async boundary

```ruby
# RED FLAG: the job's logs are orphans
Rails.logger.info({ msg: "sending confirmation", order_id: })   # no request_id, no tag
```

A Sidekiq job runs in another process with no request, so `request_id` is `nil` exactly where
you need it — the async work is what failed. Check that client/server middleware propagates it.
→ `../std-monitoring/references/request-tracing.md`

## Common PR Review Comments

### Must Fix (Block Merge)
- Missing authentication/authorization on endpoint — **including a policy that exists but is
  never called** (`authorize` / `policy_scope` absent), and `index` using `authorize` instead of
  `policy_scope`
- SQL injection or XSS vulnerability
- Hardcoded secret or credential
- N+1 query on a list endpoint
- Missing database migration rollback
- **Migration with no `lock_timeout`** on a table of any size
- **`remove_column` without an `ignored_columns` deploy landing first**
- **Non-bang `create`/`save` inside a transaction** (commits half the operation silently)
- **A money/irreversible job with no explicit `sidekiq_options retry:`** (the default is 25
  retries over ~20 days) or with `retry_on` used as the policy (it stacks, it does not cap)
- Server data stored in Zustand instead of TanStack Query

### Should Fix (Strong Suggestion)
- Missing test coverage for changed code
- Inconsistent error handling
- Missing Panko serializer (raw model rendered)
- Missing index on foreign key
- Inline styles instead of StyleSheet.create

### Nit (Optional)
- Naming could be more descriptive
- Consider extracting to a helper
- Minor formatting inconsistency
