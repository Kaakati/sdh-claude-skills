# Rails Patterns Library

## Service Object Pattern
```ruby
# backend/app/services/create_order.rb
class CreateOrder
  def initialize(user:, items:, location: nil)
    @user = user
    @items = items
    @location = location
  end

  def call
    ActiveRecord::Base.transaction do
      order = @user.orders.create!(
        status: :pending,
        location: build_point
      )
      create_line_items(order)
      schedule_notifications(order)
      Result.success(order)
    end
  rescue ActiveRecord::RecordInvalid => e
    Result.failure(e.message)
  end

  private

  def build_point
    return nil unless @location
    RGeo::Geographic.spherical_factory(srid: 4326)
      .point(@location[:lng], @location[:lat])
  end

  def create_line_items(order)
    @items.each do |item|
      order.line_items.create!(
        product_id: item[:product_id],
        quantity: item[:quantity],
        unit_price_cents: item[:price_cents]
      )
    end
  end

  def schedule_notifications(order)
    OrderConfirmationJob.perform_later(order.id)
    CentrifugoPublisher.publish(
      "user:#{@user.id}",
      { event: "order_created", order_id: order.id }
    )
  end
end
```

## Result Object Pattern
```ruby
# backend/app/lib/result.rb
class Result
  attr_reader :value, :error

  def self.success(value = nil)
    new(value: value, success: true)
  end

  def self.failure(error)
    new(error: error, success: false)
  end

  def success? = @success
  def failure? = !@success

  private

  def initialize(value: nil, error: nil, success:)
    @value = value
    @error = error
    @success = success
  end
end
```

## Query Object Pattern
```ruby
# backend/app/queries/nearby_locations_query.rb
class NearbyLocationsQuery
  def initialize(lat:, lng:, radius_km: 10, limit: 50)
    @lat = lat
    @lng = lng
    @radius_meters = radius_km * 1000
    @limit = limit
  end

  def call
    Location
      .where(active: true)
      .where(
        "ST_DWithin(coordinates::geography, ST_MakePoint(:lng, :lat)::geography, :radius)",
        lng: @lng, lat: @lat, radius: @radius_meters
      )
      .order(
        Arel.sql("ST_Distance(coordinates::geography, ST_MakePoint(#{@lng}, #{@lat})::geography)")
      )
      .limit(@limit)
  end
end
```

## Controller Pattern with Panko
```ruby
# backend/app/controllers/api/v1/orders_controller.rb
module Api
  module V1
    class OrdersController < ApplicationController
      include CursorPaginable # limits and the envelope are owned by std-api-design's pagination-rails
      before_action :authenticate_user!
      before_action :set_order, only: [:show, :update]

      def index
        orders = policy_scope(Order)
          .includes(:customer, :line_items)
          .order(created_at: :desc, id: :desc)

        records, pagination = paginate_by_cursor(orders)

        render json: {
          data: Panko::ArraySerializer.new(records, each_serializer: OrderListSerializer).to_a,
          pagination:
        }
      end

      def show
        authorize @order
        render json: { data: OrderDetailSerializer.new.serialize(@order) }
      end

      def create
        authorize Order
        result = CreateOrder.new(
          user: current_user,
          items: order_params[:items],
          location: order_params[:location]
        ).call

        if result.success?
          render json: { data: OrderDetailSerializer.new.serialize(result.value) },
                 status: :created
        else
          # The one envelope, rendered by the shared concern (std-api-design's errors-rails)
          render_api_error(message: result.error, code: "VALIDATION_ERROR",
                           status: :unprocessable_entity)
        end
      end

      private

      # Scoped: another tenant's order is a 404, never a 403 that confirms it exists
      def set_order
        @order = policy_scope(Order).find(params[:id])
      end

      def order_params
        params.require(:order).permit(
          items: [:product_id, :quantity, :price_cents],
          location: [:lat, :lng]
        )
      end
    end
  end
end
```

## Migration with PostGIS
```ruby
class CreateLocations < ActiveRecord::Migration[7.1]
  def change
    create_table :locations do |t|
      t.string :name, null: false
      t.text :address
      t.st_point :coordinates, geographic: true, srid: 4326, null: false
      t.jsonb :metadata, default: {}
      t.boolean :active, default: true, null: false
      t.references :organization, null: false, foreign_key: true

      t.timestamps
    end

    add_index :locations, :coordinates, using: :gist
    add_index :locations, :active
    add_index :locations, :metadata, using: :gin
    add_index :locations, [:organization_id, :active]
  end
end
```

## Centrifugo Publisher
```ruby
# backend/app/lib/centrifugo_publisher.rb
class CentrifugoPublisher
  def self.publish(channel, data)
    connection = Faraday.new(url: ENV["CENTRIFUGO_API_URL"]) do |f|
      f.request :json
      f.response :json
      f.headers["Authorization"] = "apikey #{ENV['CENTRIFUGO_API_KEY']}"
    end

    connection.post("/api/publish", {
      channel: channel,
      data: data
    })
  rescue Faraday::Error => e
    Rails.logger.error("Centrifugo publish failed: #{e.message}")
    Sentry.capture_exception(e) if defined?(Sentry)
  end
end
```

## Redis Caching Pattern
```ruby
# Controller-level caching with Panko, for a PUBLIC catalog: nothing in it varies by viewer.
# A permission-scoped list must add the viewer's scope and permissions_version to the key, or it
# serves one user's rows to another (@skills/std-api-design/references/drill-down-resources.md).
def index
  skip_policy_scope # deliberate: the catalog is public
  cache_key = "api:v1:products:#{params_fingerprint}"

  json = Rails.cache.fetch(cache_key, expires_in: 2.minutes) do
    products = Product.active.includes(:category).order(:name)
    pagy, records = pagy(products)

    {
      data: Panko::ArraySerializer.new(records, each_serializer: ProductSerializer).to_a,
      pagination: { page: pagy.page, pageSize: pagy.limit, totalItems: pagy.count, totalPages: pagy.pages }
    }.to_json
  end

  render json: json
end

private

def params_fingerprint
  Digest::MD5.hexdigest(params.slice(:page, :category, :q).to_s)
end
```

## Sidekiq Job with Error Handling
```ruby
class ProcessPaymentJob < ApplicationJob
  queue_as :critical

  # ONE retry policy, set where it is actually enforced. `retry_on ..., attempts: 5` would
  # NOT cap this at 5: ActiveJob retries first, then "kick[s] the job back to Sidekiq, where
  # Sidekiq's retries with exponential backoff will take over" — its default 25 retries over
  # ~20 days. On a payment. `sidekiq_options` works on ActiveJob classes and does not stack.
  sidekiq_options retry: 5

  # Permanent failure: don't burn attempts proving the request is still invalid.
  discard_on Stripe::InvalidRequestError

  # The last moment anyone can act. Without this the job dies into the Dead set and the
  # customer is simply never charged, silently. See std-error-handling/references/background-jobs.md
  sidekiq_retries_exhausted do |job, ex|
    Sentry.capture_exception(ex, extra: { job: job["class"], args: job["args"] })
  end

  def perform(order_id)
    order = Order.find(order_id)
    return if order.paid?   # cheap guard; the server-side idempotency key is the correctness

    result = PaymentProcessor.new(order: order).call

    if result.success?
      order.update!(status: :paid, paid_at: Time.current)
      CentrifugoPublisher.publish("user:#{order.user_id}", {
        event: "payment_confirmed",
        order_id: order.id
      })
    else
      order.update!(status: :payment_failed)
      AdminNotifier.payment_failed(order, result.error)
    end
  end
end
```

## Pundit Policy Pattern
Policies ask for a permission key, never a role name. `permitted?`, the scope levels it checks, and
the matrix behind them → `@skills/std-rails-conventions/references/roles-and-permissions.md`.

```ruby
# backend/app/policies/order_policy.rb
class OrderPolicy < ApplicationPolicy
  def show? = permitted?("orders.read")
  def update? = permitted?("orders.update") && record.pending?
  def cancel? = permitted?("orders.cancel") && !record.shipped?

  class Scope < ApplicationPolicy::Scope
    # scope_for turns the caller's level for the key (own / team / org / all) into a where
    # clause; no level at all resolves to scope.none
    def resolve = scope_for("orders.read")
  end
end
```
