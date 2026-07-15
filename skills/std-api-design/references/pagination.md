# Paginating a Collection

Load-bearing rules restated (these hold even if you read nothing else):

- **Cursor-based pagination is the default.** Offset-based is acceptable only for small, stable
  datasets that are not appended to in real time.
- Default page size **25**, maximum **100**. Clients request size via `?limit=`.
- **Always** return pagination metadata — never a bare array.
- Collections are wrapped in `data`: `{ "data": [...], "pagination": {...} }`.

Cursor response shape:

```json
{
  "data": [],
  "pagination": { "nextCursor": "eyJpZCI6MTAwfQ==", "hasMore": true, "limit": 25 }
}
```

Offset response shape:

```json
{
  "data": [],
  "pagination": { "page": 2, "pageSize": 25, "totalItems": 150, "totalPages": 6 }
}
```

---

## Decision: cursor or offset?

| Signal | Choose |
|--------|--------|
| Feed, activity log, chat, anything with inserts at the head | Cursor |
| Table > ~10k rows | Cursor |
| Client needs "jump to page 7" or a total count in the UI | Offset |
| Small, admin-only, rarely-changing lookup table | Offset |

Offset pagination on a live feed **skips and duplicates rows**: a row inserted at the head while
the user reads page 1 pushes one row from page 1 down into page 2, and the user sees it twice.
Offset also degrades — `OFFSET 100000` makes Postgres walk 100k rows before discarding them.

---

## Decision: implementing cursor pagination in Rails

The cursor must encode a **stable, unique, totally-ordered key**. `created_at` alone is not
unique — ties silently drop rows. Use a compound key of the sort column plus the primary key.

### Bad — timestamp-only cursor, unbounded limit, bare array

```ruby
class Api::V1::OrdersController < ApplicationController
  def index
    orders = Order.order(created_at: :desc)
    orders = orders.where("created_at < ?", params[:after]) if params[:after]
    orders = orders.limit(params[:limit] || 1000) # client can ask for a million
    render json: orders # bare array: no envelope, no metadata
  end
end
```

Two orders sharing a `created_at` at a page boundary: the second is never returned. And
`limit=1000000` is a free denial-of-service.

### Good — compound keyset cursor, clamped limit, full envelope

```ruby
# app/services/cursor.rb
class Cursor
  def self.encode(record)
    Base64.urlsafe_encode64(
      { t: record.created_at.iso8601(6), id: record.id }.to_json, padding: false
    )
  end

  # Returns nil on any malformed input — never raise on client-controlled data.
  def self.decode(value)
    return nil if value.blank?

    payload = JSON.parse(Base64.urlsafe_decode64(value))
    { time: Time.iso8601(payload.fetch("t")), id: payload.fetch("id") }
  rescue ArgumentError, JSON::ParserError, KeyError
    nil
  end
end
```

```ruby
# app/controllers/concerns/cursor_paginable.rb
module CursorPaginable
  extend ActiveSupport::Concern

  DEFAULT_LIMIT = 25
  MAX_LIMIT     = 100

  private

  def page_limit
    [[params.fetch(:limit, DEFAULT_LIMIT).to_i, 1].max, MAX_LIMIT].min
  end

  # scope must already be ordered created_at DESC, id DESC.
  def paginate_by_cursor(scope)
    cursor = Cursor.decode(params[:cursor])
    if cursor
      scope = scope.where(
        "(orders.created_at, orders.id) < (?, ?)", cursor[:time], cursor[:id]
      )
    end

    records = scope.limit(page_limit + 1).to_a   # fetch one extra to learn hasMore
    has_more = records.size > page_limit
    records  = records.first(page_limit)

    [records, {
      nextCursor: has_more ? Cursor.encode(records.last) : nil,
      hasMore: has_more,
      limit: page_limit
    }]
  end
end
```

```ruby
class Api::V1::OrdersController < ApplicationController
  include CursorPaginable

  def index
    scope = policy_scope(Order).order(created_at: :desc, id: :desc)
    orders, pagination = paginate_by_cursor(scope)

    render json: {
      data: OrderSerializer.new(orders, each_serializer: true).to_a,
      pagination: pagination
    }
  end
end
```

Row-value comparison `(created_at, id) < (?, ?)` is the whole trick: it is a single index range
scan and it is tie-safe.

The index this requires — without it the keyset scan is a sort of the whole table:

```ruby
class AddOrdersKeysetIndex < ActiveRecord::Migration[7.1]
  disable_ddl_transaction!

  def change
    add_index :orders, %i[created_at id], order: { created_at: :desc, id: :desc },
              algorithm: :concurrently
  end
end
```

Scoped feeds need the filter column leading the index:

```ruby
add_index :orders, %i[user_id created_at id],
          order: { created_at: :desc, id: :desc }, algorithm: :concurrently
```

---

## Decision: implementing offset pagination in Rails (use pagy)

Community libraries first — `pagy` is the house pagination gem. Do not hand-roll `.offset`.

### Bad — manual offset arithmetic, N+1 count, unbounded page size

```ruby
def index
  page      = params[:page].to_i
  page_size = params[:page_size].to_i
  orders    = Order.limit(page_size).offset(page * page_size)
  render json: { data: orders, total: Order.count } # page=0 vs 1 ambiguity, count on every call
end
```

`params[:page].to_i` on `"abc"` yields `0`; `page_size` unset yields `.limit(0)` — an empty page
with a 200. Silent, and reported as "the API returns nothing".

### Good — pagy, clamped, camelCase metadata

```ruby
class Api::V1::ProductCategoriesController < ApplicationController
  include Pagy::Backend

  def index
    pagy, categories = pagy(
      policy_scope(ProductCategory).order(:name),
      page: params[:page],
      limit: page_limit
    )

    render json: {
      data: ProductCategorySerializer.new(categories, each_serializer: true).to_a,
      pagination: {
        page: pagy.page,
        pageSize: pagy.limit,
        totalItems: pagy.count,
        totalPages: pagy.pages
      }
    }
  end

  private

  def page_limit
    [[params.fetch(:limit, 25).to_i, 1].max, 100].min
  end
end
```

```ruby
# config/initializers/pagy.rb
require "pagy/extras/overflow"
Pagy::DEFAULT[:limit]    = 25
Pagy::DEFAULT[:max_limit] = 100
Pagy::DEFAULT[:overflow] = :empty_page # page beyond the end => empty data, not a 500
```

---

## Decision: paginating a PostGIS proximity query

Distance ordering has the same tie problem. Break ties on `id` and keep the cursor on the
computed distance.

```ruby
class Api::V1::VenuesController < ApplicationController
  include CursorPaginable

  def index
    point = RGeo::Geographic.spherical_factory(srid: 4326)
                            .point(params[:lng].to_f, params[:lat].to_f)

    scope = Venue
            .select("venues.*, ST_Distance(venues.location, :p::geography) AS distance_m")
            .where("ST_DWithin(venues.location, :p::geography, :radius)",
                   p: point.to_s, radius: radius_meters)
            .order(Arel.sql("distance_m ASC, venues.id ASC"))

    venues, pagination = paginate_by_distance_cursor(scope)
    render json: {
      data: VenueSerializer.new(venues, each_serializer: true).to_a,
      pagination: pagination
    }
  end

  private

  def radius_meters
    [[params.fetch(:radius, 5_000).to_i, 100].max, 50_000].min
  end
end
```

Requires the geography GiST index, or `ST_DWithin` scans every venue:

```ruby
add_index :venues, :location, using: :gist, algorithm: :concurrently
```

---

## Decision: consuming a cursor API from the frontend

Use TanStack Query's `useInfiniteQuery` — the pagination envelope maps onto it directly.

### Bad — manual page state, appended by hand

```typescript
const [items, setItems] = useState<Order[]>([]);
const [cursor, setCursor] = useState<string | null>(null);

useEffect(() => {
  apiClient.get('/orders', { params: { cursor } }).then((res) => {
    setItems((prev) => [...prev, ...res.data.data]); // double-fires in StrictMode; duplicates rows
    setCursor(res.data.pagination.nextCursor);
  });
}, [cursor]); // and this loops forever
```

### Good — useInfiniteQuery reading nextCursor from the envelope

```typescript
// src/api/orders.ts
import { useInfiniteQuery } from '@tanstack/react-query';
import { apiClient } from './client';

export type Order = { id: string; total: number; createdAt: string };
export type Paginated<T> = {
  data: T[];
  pagination: { nextCursor: string | null; hasMore: boolean; limit: number };
};

export function useOrders(limit = 25) {
  return useInfiniteQuery({
    queryKey: ['orders', { limit }],
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }) => {
      const res = await apiClient.get<Paginated<Order>>('/orders', {
        params: { cursor: pageParam ?? undefined, limit },
      });
      return res.data;
    },
    getNextPageParam: (last) => (last.pagination.hasMore ? last.pagination.nextCursor : undefined),
  });
}
```

```tsx
// src/pages/orders/OrdersList.tsx
export function OrdersList() {
  const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders();
  const orders = data?.pages.flatMap((p) => p.data) ?? [];

  return (
    <div>
      <ul className="divide-y divide-slate-200">
        {orders.map((o) => (
          <li key={o.id} className="py-3">{o.id}</li>
        ))}
      </ul>
      {hasNextPage && (
        <button
          type="button"
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
          className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {isFetchingNextPage ? 'Loading…' : 'Load more'}
        </button>
      )}
    </div>
  );
}
```

React Native FlatList wiring uses the same hook:

```tsx
const { data, fetchNextPage, hasNextPage, isFetchingNextPage } = useOrders();

<FlatList
  data={data?.pages.flatMap((p) => p.data) ?? []}
  keyExtractor={(item) => item.id}
  renderItem={({ item }) => <OrderRow order={item} />}
  onEndReachedThreshold={0.5}
  onEndReached={() => {
    if (hasNextPage && !isFetchingNextPage) fetchNextPage();
  }}
/>;
```

`onEndReached` fires repeatedly while scrolling — the `!isFetchingNextPage` guard is what stops
it from firing the same cursor request five times.

---

## Testing pagination

```ruby
# spec/requests/api/v1/orders_spec.rb
it "should not drop rows when two records share a created_at" do
  time = Time.current
  a, b = create_list(:order, 2, user: user, created_at: time)

  get "/v1/orders", params: { limit: 1 }, headers: auth_headers
  first_page = response.parsed_body

  get "/v1/orders", params: { limit: 1, cursor: first_page["pagination"]["nextCursor"] },
      headers: auth_headers
  second_page = response.parsed_body

  ids = first_page["data"].map { _1["id"] } + second_page["data"].map { _1["id"] }
  expect(ids).to match_array([a.id, b.id])
end

it "should clamp limit to the maximum of 100" do
  get "/v1/orders", params: { limit: 5_000 }, headers: auth_headers
  expect(response.parsed_body["pagination"]["limit"]).to eq(100)
end
```
