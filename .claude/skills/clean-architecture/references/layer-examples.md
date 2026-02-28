# Clean Architecture — Layer Code Examples

Full code examples for each architecture layer across all frameworks.

## Layer 1: Entities

### Rails — Model (Domain Logic Only)
```ruby
# backend/app/models/order.rb
class Order < ApplicationRecord
  belongs_to :user
  has_many :order_items, dependent: :destroy

  validates :total_amount, numericality: { greater_than: 0 }
  validates :status, inclusion: { in: %w[pending confirmed shipped delivered cancelled] }

  def cancellable?
    %w[pending confirmed].include?(status)
  end

  def total
    order_items.sum(&:subtotal)
  end
end
```

### Rails — Value Object
```ruby
# backend/app/values/money.rb
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

### React Native — Domain Types
```typescript
// mobile/src/domain/order.ts — Pure TypeScript, no React imports
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

### Vite SPA — Domain Types
```typescript
// web/src/domain/order.ts — Pure TypeScript, no React imports
export interface Order {
  id: string;
  status: OrderStatus;
  totalAmount: number;
  items: OrderItem[];
}
export type OrderStatus = 'pending' | 'confirmed' | 'shipped' | 'delivered' | 'cancelled';

export function isCancellable(order: Order): boolean {
  return ['pending', 'confirmed'].includes(order.status);
}
```

## Layer 2: Use Cases

### Rails — Service Object with Result Pattern
```ruby
# backend/app/services/orders/create_order_service.rb
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
      OrderFulfillmentJob.perform_async(order.id)
    end
  end
end

# backend/app/services/result.rb
class Result
  attr_reader :value, :error_type, :error_message

  def self.success(value) = new(success: true, value: value)
  def self.failure(error_type, message) = new(success: false, error_type: error_type, error_message: message)
  def success? = @success
  def failure? = !@success

  private

  def initialize(success:, value: nil, error_type: nil, error_message: nil)
    @success = success
    @value = value
    @error_type = error_type
    @error_message = error_message
  end
end
```

### React Native — Custom Hook (Use Case)
```typescript
// mobile/src/hooks/useCreateOrder.ts
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

### Vite SPA — TanStack Query Hook (Use Case)
```typescript
// web/src/api/orders.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import type { Order } from '../domain/order';

export function useOrders() {
  return useQuery({
    queryKey: ['orders'],
    queryFn: () => apiClient.get<Order[]>('/api/v1/orders'),
    staleTime: 30_000,
  });
}
```

### Next.js — Server Action (Use Case)
```tsx
// next/src/actions/orders.ts
'use server';
import { revalidatePath } from 'next/cache';
import { z } from 'zod';

const CreateOrderSchema = z.object({ /* ... */ });

export async function createOrder(prevState: unknown, formData: FormData) {
  const parsed = CreateOrderSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { errors: parsed.error.flatten().fieldErrors };
  await railsApi.post('/api/v1/orders', parsed.data);
  revalidatePath('/orders');
  return { success: true };
}
```

## Layer 3: Interface Adapters

### Rails — Thin Controller
```ruby
# backend/app/controllers/api/v1/orders_controller.rb
class Api::V1::OrdersController < ApplicationController
  def create
    authorize Order

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

### Rails — Panko Serializer
```ruby
# backend/app/serializers/order_serializer.rb
class OrderSerializer < Panko::Serializer
  attributes :id, :status, :total_amount, :created_at
  has_many :order_items, serializer: OrderItemSerializer
end
```

### React Native — Thin Screen
```tsx
// mobile/src/screens/CreateOrderScreen.tsx
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

### Vite SPA — Thin Page
```tsx
// web/src/pages/Orders.tsx — Thin page, composes hooks + components
import { useOrders } from '../api/orders';
import { OrderTable } from '../components/OrderTable';

export default function OrdersPage() {
  const { data: orders, isLoading } = useOrders();
  return <OrderTable orders={orders ?? []} isLoading={isLoading} />;
}
```

### Next.js — Server Component Page
```tsx
// next/app/orders/page.tsx — Server Component fetches data, composes components
import { OrderTable } from '@/components/OrderTable';
import { railsApi } from '@/api/client';

export default async function OrdersPage() {
  const orders = await railsApi.get('/api/v1/orders');
  return <OrderTable initialData={orders} />;
}
```
