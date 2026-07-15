# Clean Architecture on Rails

Layer mapping, rules, and boundary violations for the Rails backend (Rails API-only + Phlex +
Panko + PostGIS + Sidekiq).

**The rule this file enforces:** dependencies point inward. Entities (models, value objects) know
nothing about use cases, controllers, or frameworks. Use cases (service objects) know about
entities but not about controllers, serializers, or HTTP. Interface adapters (controllers,
serializers, form objects) translate between use cases and external concerns. Frameworks
(Rails, ActiveRecord, Sidekiq) are implementation details — pluggable and replaceable.

## Decision: which layer does this Rails file belong to?

| Clean Architecture Layer | Rails Component | Directory |
|--------------------------|-----------------|-----------|
| Entities | Models, Value Objects | `backend/app/models/`, `backend/app/values/` |
| Use Cases | Service Objects | `backend/app/services/` |
| Interface Adapters | Controllers, Serializers, Form Objects | `backend/app/controllers/`, `backend/app/serializers/`, `backend/app/forms/` |
| Frameworks | Rails itself, ActiveRecord, Sidekiq | Framework code |

Rules per component:

- **Models** contain domain logic (validations, associations, scopes, domain methods). No HTTP or
  serialization concerns.
- **Service objects** orchestrate business workflows. They call models and return Result objects.
  No direct HTTP response handling.
- **Controllers** are thin — authorize, call a service, serialize the response. Max 5 public
  actions per controller.
- **Serializers** (Panko) handle JSON representation only. No business logic in serializers.
- **Jobs** (Sidekiq) are thin wrappers that delegate to service objects. Jobs contain retry/error
  config, not business logic.

## Decision: how do I keep business logic out of the controller?

Violation: **Controller contains business logic** — extract to a service object.

```ruby
# BAD — app/controllers/api/v1/orders_controller.rb
module Api
  module V1
    class OrdersController < ApplicationController
      def create
        order = Order.new(order_params.merge(user: current_user))
        order.total_cents = order.line_items.sum { |li| li.quantity * li.unit_price_cents }
        order.total_cents -= 500 if current_user.orders.count >= 10

        if order.save
          OrderMailer.confirmation(order).deliver_later
          InventoryReservation.create!(order: order)
          render json: OrderSerializer.new.serialize(order), status: :created
        else
          render json: { errors: order.errors.full_messages }, status: :unprocessable_entity
        end
      end
    end
  end
end
```

```ruby
# GOOD — app/controllers/api/v1/orders_controller.rb (thin adapter)
module Api
  module V1
    class OrdersController < ApplicationController
      def create
        authorize Order

        result = Orders::CreateOrder.new(user: current_user, attributes: order_params).call

        if result.success?
          render json: { data: OrderSerializer.new.serialize(result.value) }, status: :created
        else
          render json: { errors: result.errors }, status: :unprocessable_entity
        end
      end

      private

      def order_params
        params.require(:order).permit(:shipping_address_id, line_items: %i[sku quantity])
      end
    end
  end
end
```

## Decision: what does a service object return?

Violation: **Service returns HTTP status codes** — the use case knows about HTTP. Return Result
objects instead; the controller maps a Result onto a status code.

```ruby
# BAD — app/services/orders/create_order.rb
module Orders
  class CreateOrder
    def call
      order = Order.new(@attributes)
      return { status: :unprocessable_entity, body: order.errors } unless order.save

      { status: :created, body: order } # use case leaked HTTP into the domain
    end
  end
end
```

```ruby
# GOOD — app/services/orders/create_order.rb
module Orders
  class CreateOrder
    Result = Struct.new(:success?, :value, :errors, keyword_init: true)

    def initialize(user:, attributes:)
      @user = user
      @attributes = attributes
    end

    def call
      order = Order.new(@attributes.merge(user: @user))
      order.total_cents = Orders::TotalCalculator.new(order).call

      return failure(order.errors.full_messages) unless order.save

      Inventory::ReserveStock.new(order).call
      OrderMailer.confirmation(order).deliver_later
      success(order)
    end

    private

    def success(order) = Result.new(success?: true, value: order, errors: [])
    def failure(errors) = Result.new(success?: false, value: nil, errors: errors)
  end
end
```

## Decision: where does domain logic live — model or service?

Violation: **Model imports controller/serializer** — an entity depending on an adapter. Move the
logic to a service.

```ruby
# BAD — app/models/order.rb
class Order < ApplicationRecord
  def as_api_response
    OrderSerializer.new.serialize(self) # entity depends on an interface adapter
  end

  def notify_and_charge!
    PaymentGateway.charge(self)         # entity reaches into a framework/gateway
    ActionController::Base.helpers.sanitize(notes)
  end
end
```

```ruby
# GOOD — app/models/order.rb (pure domain logic)
class Order < ApplicationRecord
  belongs_to :user
  has_many :line_items, dependent: :destroy

  validates :total_cents, numericality: { greater_than_or_equal_to: 0 }

  scope :recent, -> { where(created_at: 30.days.ago..) }

  def discountable?
    user.orders.completed.count >= LOYALTY_THRESHOLD
  end
end

# GOOD — app/services/orders/charge_order.rb (use case owns the workflow)
module Orders
  class ChargeOrder
    def initialize(order, gateway: PaymentGateway)
      @order = order
      @gateway = gateway
    end

    def call
      @gateway.charge(amount_cents: @order.total_cents, customer: @order.user.stripe_id)
    end
  end
end
```

## Decision: may a serializer touch the database?

Violation: **Serializer queries the database** — the adapter bypasses the use case layer. Pre-load
data in the service.

```ruby
# BAD — app/serializers/order_serializer.rb
class OrderSerializer < Panko::Serializer
  attributes :id, :total_cents, :loyalty_tier

  def loyalty_tier
    # N+1 query from inside an adapter, and business logic to boot
    object.user.orders.completed.count >= 10 ? "gold" : "standard"
  end
end
```

```ruby
# GOOD — app/services/orders/list_orders.rb (use case pre-loads)
module Orders
  class ListOrders
    def call
      Order.includes(:user, :line_items).recent
    end
  end
end

# GOOD — app/serializers/order_serializer.rb (representation only)
class OrderSerializer < Panko::Serializer
  attributes :id, :total_cents, :loyalty_tier

  has_one :user, serializer: UserSerializer

  def loyalty_tier
    object.loyalty_tier # computed in the domain, read here
  end
end
```

## Decision: what goes in a Sidekiq job?

Violation: **Sidekiq job contains business logic** — the job should delegate to a service. Jobs
hold retry/error configuration only.

```ruby
# BAD — app/jobs/settle_order_job.rb
class SettleOrderJob
  include Sidekiq::Job

  def perform(order_id)
    order = Order.find(order_id)
    order.total_cents -= 500 if order.user.orders.count >= 10
    PaymentGateway.charge(amount_cents: order.total_cents, customer: order.user.stripe_id)
    order.update!(status: "settled")
    OrderMailer.receipt(order).deliver_later
  end
end
```

```ruby
# GOOD — app/jobs/settle_order_job.rb (thin wrapper)
class SettleOrderJob
  include Sidekiq::Job

  sidekiq_options queue: :payments, retry: 5

  def perform(order_id)
    Orders::SettleOrder.new(Order.find(order_id)).call
  end
end
```

## Decision: how do I test each Rails layer?

- **Entities** (models, value objects): unit tests, no mocks needed — pure domain logic.
- **Use Cases** (service objects): unit tests with mocked repositories/gateways — inject the
  gateway (`CreateOrder.new(order, gateway: fake_gateway)`) rather than stubbing constants.
- **Interface Adapters** (controllers, serializers): integration tests — request specs and
  serializer specs.
- **Frameworks** (Rails, ActiveRecord, Sidekiq): minimal testing — trust the framework, test your
  configuration.

```ruby
# GOOD — spec/services/orders/charge_order_spec.rb
RSpec.describe Orders::ChargeOrder do
  it "should charge the order total when the gateway succeeds" do
    order   = build_stubbed(:order, total_cents: 2_500)
    gateway = instance_double("PaymentGateway", charge: true)

    described_class.new(order, gateway: gateway).call

    expect(gateway).to have_received(:charge).with(
      amount_cents: 2_500, customer: order.user.stripe_id
    )
  end
end
```
