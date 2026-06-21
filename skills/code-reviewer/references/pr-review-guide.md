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
  def perform(order_id)
    order = Order.find(order_id)
    return if order.charged?  # Idempotency guard
    PaymentGateway.charge(order.total)
    order.update!(charged: true)
  end
end
```

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

## Common PR Review Comments

### Must Fix (Block Merge)
- Missing authentication/authorization on endpoint
- SQL injection or XSS vulnerability
- Hardcoded secret or credential
- N+1 query on a list endpoint
- Missing database migration rollback
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
