# Authorization — a policy that is never called is not authorization

Load-bearing rules restated (hold even if you read nothing else):

1. **Every action authorizes, or explicitly declares that it doesn't.** `verify_authorized` /
   `verify_policy_scoped` as `after_action` is what makes that true at runtime.
2. **`index` uses `policy_scope`, not `authorize`.** Authorizing the collection does not filter
   it.
3. **Logout must revoke the JWT.** Without a revocation strategy, a signed-out token keeps
   working until it expires.

Rendering the 403 is **not** this file's job — `rescue_from Pundit::NotAuthorizedError` and the
error envelope are owned by `../../std-api-design/references/errors-rails.md`.

---

## Why this outranks writing good policies

Writing a policy is the easy half, and it is the half every codebase gets right. The failure is
mechanical: **the policy is never invoked.** A controller action that forgets `authorize` does
not raise, does not warn, and does not fail a test that only checks the happy path. It returns
`200 OK` with somebody else's data.

That is OWASP's **#1 — Broken Access Control**, which `std-security` lists first, and it is
invisible in review precisely because the policy file *exists*. A reviewer greps `OrderPolicy`,
finds a careful `owner? || admin?`, and moves on. Nothing connects that file to the action that
forgot to call it.

Pundit ships the fix. It is one line, and it is off by default.

## Decision: which mechanism does this action need?

| Action | Use | Why |
|---|---|---|
| `show`, `update`, `destroy` — one record | `authorize @record` | Asks the policy about *that* record |
| `index` — a collection | `policy_scope(Model)` | **Filters**; `authorize` would only ask "may you list?" |
| `create` | `authorize Model` (the class) | No instance yet |
| Genuinely public (health check, sign-up) | `skip_authorization` | Deliberate and greppable — not silence |

## Bad — the policy exists, and nothing calls it

```ruby
# app/controllers/api/v1/orders_controller.rb  ❌
module Api
  module V1
    class OrdersController < ApplicationController
      before_action :authenticate_user!

      def index
        # Authenticated, so it feels safe. It is not: this returns EVERY order in the
        # system to any signed-in user. OrderPolicy::Scope exists and is never consulted.
        @orders = Order.includes(:line_items).order(created_at: :desc)
        render json: Panko::ArraySerializer.new(@orders, each_serializer: OrderSerializer).to_json
      end

      def show
        # `find` enforces existence, not ownership. Any signed-in user can read any
        # order by guessing an id. OrderPolicy#show? is never called.
        @order = Order.find(params[:id])
        render json: OrderSerializer.new(@order).to_json
      end
    end
  end
end
```

Both actions pass authentication, pass code review, and pass a request spec written by someone
who only tests the owner's session. Neither is authorized.

## Good — verification is wired, so forgetting is impossible

```ruby
# app/controllers/application_controller.rb  ✅
class ApplicationController < ActionController::API
  # Pundit 2.x: the module is `Pundit::Authorization` (plain `include Pundit` is deprecated).
  include Pundit::Authorization

  # THE line. Without it, a forgotten `authorize` is silent; with it, the action raises
  # Pundit::AuthorizationNotPerformedError and the request spec goes red in CI.
  #
  # `except: :index` is deliberate: index authorizes by SCOPING, which the next line
  # verifies instead. Splitting them means neither check can be satisfied by the wrong one.
  after_action :verify_authorized,     except: :index
  after_action :verify_policy_scoped,  only:   :index

  # The 403 body/shape is owned by std-api-design/references/errors-rails.md.
  rescue_from Pundit::NotAuthorizedError, with: :render_forbidden
end
```

```ruby
# app/controllers/api/v1/orders_controller.rb  ✅
module Api
  module V1
    class OrdersController < ApplicationController
      before_action :authenticate_user!

      def index
        # policy_scope FILTERS. This is the only thing that keeps one tenant's orders
        # out of another's list.
        @orders = policy_scope(Order).includes(:line_items).order(created_at: :desc)
        render json: Panko::ArraySerializer.new(@orders, each_serializer: OrderSerializer).to_json
      end

      def show
        # Scope first so a non-owner gets 404 rather than 403 — a 403 confirms the record
        # exists, which leaks. Then authorize for the per-record rules.
        @order = policy_scope(Order).find(params[:id])
        authorize @order
        render json: OrderSerializer.new(@order).to_json
      end

      def create
        authorize Order   # the class: there is no instance to ask about yet
        order = Orders::Create.new(user: current_user, params: order_params).call
        render json: OrderSerializer.new(order).to_json, status: :created
      end
    end
  end
end
```

## The exception must be explicit

Public endpoints are real. Make them **greppable**, so "no authorization here" is a decision
somebody wrote down rather than a line somebody forgot:

```ruby
# app/controllers/api/v1/health_controller.rb  ✅
module Api
  module V1
    class HealthController < ApplicationController
      skip_before_action :authenticate_user!

      def show
        # Pundit's own escape hatch. `skip_authorization` (NOT `skip_verify_authorized`)
        # satisfies verify_authorized while announcing the intent in the diff.
        skip_authorization
        render json: { status: "ok" }
      end
    end
  end
end
```

`skip_policy_scope` is the equivalent for an `index` that genuinely lists public data.

> **Auditing an existing app:** turning on `verify_authorized` will light up every unauthorized
> action at once. That is the point — but it is also why teams disable it again. Enable it, let
> the specs fail, and fix or `skip_authorization` each one *deliberately*. A rule you adopt by
> silencing it is worse than no rule, because now the silence looks intentional.

## Test the negative, not just the happy path

The bug only exists for the *other* user, so that is the spec that has to exist:

```ruby
# spec/requests/api/v1/orders_spec.rb  ✅
RSpec.describe "Orders API" do
  let(:owner)    { create(:user) }
  let(:stranger) { create(:user) }
  let!(:order)   { create(:order, user: owner) }

  it "should not expose another user's order when a stranger requests it" do
    get "/api/v1/orders/#{order.id}", headers: auth_headers(stranger)
    # 404, not 403: a 403 would confirm the order exists.
    expect(response).to have_http_status(:not_found)
  end

  it "should return only the caller's orders when listing" do
    create(:order, user: stranger)
    get "/api/v1/orders", headers: auth_headers(owner)
    expect(json_body["data"].map { |o| o["id"] }).to contain_exactly(order.id)
  end
end
```

## JWT revocation — logout must actually log out

`devise-jwt` **does not revoke by default**. Without a strategy, "sign out" deletes the token
from the client and the token keeps authenticating anyone who kept a copy until it expires.

```ruby
# app/models/user.rb  ✅  JTIMatcher: rotating `jti` invalidates every token issued before it
class User < ApplicationRecord
  include Devise::JWT::RevocationStrategies::JTIMatcher

  devise :database_authenticatable, :registerable, :validatable,
         :jwt_authenticatable, jwt_revocation_strategy: self
end
```

```ruby
# db/migrate/20260715120000_add_jti_to_users.rb  ✅
class AddJtiToUsers < ActiveRecord::Migration[7.1]
  def change
    add_column :users, :jti, :string, null: false
    # Unique: two valid tokens must never share a jti.
    add_index  :users, :jti, unique: true
  end
end
```

On sign-out the user's `jti` changes, so previously issued tokens stop validating. Note the
blast radius, and choose it deliberately: JTIMatcher revokes **every** token for that user, so
signing out on a laptop signs out the phone too. If per-device sessions matter, use a
`Denylist`/`Allowlist` strategy instead — but pick one. The default (none) is the only option
that silently doesn't work.

> Adding `null: false` to a table with existing rows needs a backfill first — see
> `std-database` for the safe multi-step form.
