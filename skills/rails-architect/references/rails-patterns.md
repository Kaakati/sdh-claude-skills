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
      before_action :authenticate_user!
      before_action :set_order, only: [:show, :update]

      def index
        orders = policy_scope(Order)
          .includes(:customer, :line_items)
          .order(created_at: :desc)

        pagy, records = pagy(orders, items: 20)

        render json: {
          data: Panko::ArraySerializer.new(records, each_serializer: OrderListSerializer).to_a,
          meta: pagy_metadata(pagy)
        }
      end

      def show
        authorize @order
        render json: { data: OrderDetailSerializer.new.serialize(@order) }
      end

      def create
        result = CreateOrder.new(
          user: current_user,
          items: order_params[:items],
          location: order_params[:location]
        ).call

        if result.success?
          render json: { data: OrderDetailSerializer.new.serialize(result.value) },
                 status: :created
        else
          render json: { error: result.error, code: 422 },
                 status: :unprocessable_entity
        end
      end

      private

      def set_order
        @order = Order.find(params[:id])
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
# Controller-level caching with Panko
def index
  cache_key = "api:v1:products:#{params_fingerprint}"

  json = Rails.cache.fetch(cache_key, expires_in: 2.minutes) do
    products = Product.active.includes(:category).order(:name)
    pagy, records = pagy(products)

    {
      data: Panko::ArraySerializer.new(records, each_serializer: ProductSerializer).to_a,
      meta: pagy_metadata(pagy)
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
  retry_on Stripe::RateLimitError, wait: :polynomially_longer, attempts: 5
  discard_on Stripe::InvalidRequestError

  def perform(order_id)
    order = Order.find(order_id)
    return if order.paid?

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
```ruby
# backend/app/policies/order_policy.rb
class OrderPolicy < ApplicationPolicy
  def show?
    owner? || admin?
  end

  def update?
    owner? && record.pending?
  end

  def destroy?
    admin? && !record.paid?
  end

  class Scope < Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(user: user)
      end
    end
  end

  private

  def owner?
    record.user_id == user.id
  end

  def admin?
    user.admin?
  end
end
```
