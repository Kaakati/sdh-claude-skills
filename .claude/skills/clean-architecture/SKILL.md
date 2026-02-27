---
name: clean-architecture
description: Validate and implement Clean Architecture patterns including entity/use-case/adapter/framework layer separation, dependency direction enforcement, and architectural conformance checking. Use this skill whenever someone asks about architecture validation, layer boundaries, dependency direction, or says things like "check architecture", "validate clean architecture", "are my layers correct", "dependency direction", "refactor to clean architecture", "layer violation", or "architectural conformance". Also trigger for discussions about service object patterns, controller responsibilities, or domain model isolation.
agent: clean-architecture
model: sonnet
---

# Clean Architecture Skill

Validate, implement, and maintain Clean Architecture patterns across the full stack. This skill covers architectural conformance checking, layer boundary enforcement, and guided refactoring.

## Architecture Layers

### Layer 1: Entities (Domain Core)

The innermost layer. Pure business logic with zero framework dependencies.

#### Rails — Entities
```ruby
# app/models/order.rb — Domain logic only
class Order < ApplicationRecord
  # Associations (domain relationships)
  belongs_to :user
  has_many :order_items, dependent: :destroy

  # Validations (domain rules)
  validates :total_amount, numericality: { greater_than: 0 }
  validates :status, inclusion: { in: %w[pending confirmed shipped delivered cancelled] }

  # Domain methods (business rules)
  def cancellable?
    %w[pending confirmed].include?(status)
  end

  def total
    order_items.sum(&:subtotal)
  end
end

# app/values/money.rb — Value Object
class Money
  attr_reader :amount, :currency

  def initialize(amount, currency = 'USD')
    @amount = BigDecimal(amount.to_s)
    @currency = currency
  end

  def +(other)
    raise ArgumentError, "Currency mismatch" unless currency == other.currency
    Money.new(amount + other.amount, currency)
  end
end
```

#### React Native — Entities
```typescript
// src/domain/order.ts — Pure TypeScript, no React imports
export interface Order {
  id: string;
  userId: string;
  status: OrderStatus;
  totalAmount: number;
  items: OrderItem[];
  createdAt: string;
}

export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';

export function isCancellable(order: Order): boolean {
  return ['pending', 'confirmed'].includes(order.status);
}
```

### Layer 2: Use Cases (Application Logic)

Orchestrate business workflows. Depend on entities, return Result objects.

#### Rails — Service Objects
```ruby
# app/services/orders/create_order_service.rb
module Orders
  class CreateOrderService
    def initialize(user:, cart_items:, payment_method:)
      @user = user
      @cart_items = cart_items
      @payment_method = payment_method
    end

    def call
      ActiveRecord::Base.transaction do
        order = build_order
        process_payment(order)
        notify_fulfillment(order)
        Result.success(order)
      end
    rescue PaymentFailedError => e
      Result.failure(:payment_failed, e.message)
    rescue ActiveRecord::RecordInvalid => e
      Result.failure(:validation_error, e.record.errors.full_messages)
    end

    private

    def build_order
      # Domain logic orchestration — no HTTP, no serialization
    end

    def process_payment(order)
      # Calls payment gateway through an adapter
    end

    def notify_fulfillment(order)
      # Enqueues Sidekiq job — thin delegation
      OrderFulfillmentJob.perform_async(order.id)
    end
  end
end
```

#### Result Object Pattern
```ruby
# app/services/result.rb
class Result
  attr_reader :value, :error_type, :error_message

  def self.success(value)
    new(success: true, value: value)
  end

  def self.failure(error_type, message)
    new(success: false, error_type: error_type, error_message: message)
  end

  def success?
    @success
  end

  def failure?
    !@success
  end

  private

  def initialize(success:, value: nil, error_type: nil, error_message: nil)
    @success = success
    @value = value
    @error_type = error_type
    @error_message = error_message
  end
end
```

#### React Native — Custom Hooks (Use Cases)
```typescript
// src/hooks/useCreateOrder.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ordersApi } from '../api/orders';
import type { CreateOrderPayload } from '../domain/order';

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateOrderPayload) => ordersApi.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}
```

### Layer 3: Interface Adapters

Translate between the application core and external concerns.

#### Rails — Thin Controllers
```ruby
# app/controllers/api/v1/orders_controller.rb
class Api::V1::OrdersController < ApplicationController
  def create
    authorize Order  # Pundit authorization

    result = Orders::CreateOrderService.new(
      user: current_user,
      cart_items: permitted_params[:items],
      payment_method: permitted_params[:payment_method]
    ).call

    if result.success?
      render json: Panko::Response.new(
        order: OrderSerializer.new.serialize(result.value)
      ), status: :created
    else
      render json: { error: result.error_message, type: result.error_type }, status: error_status(result.error_type)
    end
  end

  private

  def permitted_params
    params.require(:order).permit(:payment_method, items: [:product_id, :quantity])
  end

  def error_status(error_type)
    { payment_failed: :payment_required, validation_error: :unprocessable_entity }.fetch(error_type, :internal_server_error)
  end
end
```

#### Rails — Panko Serializers
```ruby
# app/serializers/order_serializer.rb
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :total_amount, :created_at
  has_many :order_items, serializer: OrderItemSerializer
end
```

#### React Native — Screens (Thin)
```tsx
// src/screens/CreateOrderScreen.tsx
import { useCreateOrder } from '../hooks/useCreateOrder';
import { useCart } from '../hooks/useCart';
import { OrderForm } from '../components/OrderForm';

export function CreateOrderScreen() {
  const { data: cart } = useCart();
  const createOrder = useCreateOrder();

  const handleSubmit = (paymentMethod: string) => {
    createOrder.mutate({ items: cart.items, paymentMethod });
  };

  return (
    <OrderForm
      cart={cart}
      onSubmit={handleSubmit}
      isLoading={createOrder.isPending}
      error={createOrder.error}
    />
  );
}
```

### Layer 4: Frameworks & Drivers

External tools and infrastructure. Configured, not coded against directly.

- Rails framework, ActiveRecord, Puma
- React Native framework, Metro bundler
- PostgreSQL, Redis, Centrifugo
- AWS services (ECS, RDS, S3)
- Sidekiq, TanStack Query, Zustand

## Conformance Validation Checklist

### Dependency Direction
- [ ] Models do NOT import controllers, serializers, or jobs
- [ ] Services do NOT return HTTP status codes or render responses
- [ ] Services do NOT import controllers or serializers
- [ ] Controllers only contain: authorize, call service, serialize response
- [ ] Serializers do NOT query the database or contain business logic
- [ ] Sidekiq jobs delegate to service objects (no inline business logic)
- [ ] React Native screens delegate to hooks (no inline API calls or business logic)
- [ ] Hooks do NOT import React Native UI components
- [ ] Domain types are pure TypeScript (no React or framework imports)
- [ ] Zustand stores contain ONLY client state (no server data)

### Structural Health
- [ ] Each service object has a single public `call` method
- [ ] Controllers have max 5 public actions (index, show, create, update, destroy)
- [ ] Value objects are immutable
- [ ] No circular dependencies between services
- [ ] API client transforms responses to domain types at the boundary

## Common Refactoring Patterns

### Extract Service from Controller
**Before**: Controller with business logic inline.
**After**: Thin controller + service object + Result type.

### Extract Hook from Screen
**Before**: Screen with useEffect/API calls/state management inline.
**After**: Custom hook encapsulating data fetching + mutations, screen just renders.

### Extract Value Object from Model
**Before**: Model with related attributes and methods scattered.
**After**: Value object grouping related attributes with domain behavior.

### Extract Adapter for External Service
**Before**: Service directly calling external API with HTTP details.
**After**: Adapter interface that wraps the external API, service depends on abstraction.
