# Rails Backend i18n

Load-bearing rules restated (hold even if you read nothing else):

1. **Never interpolate a user-facing string.** If it reaches a human, it is a key.
2. **The API returns keys or localized text, never both conventions at once** — decide per
   endpoint and write it down.
3. **`Accept-Language` is a hint, not an identity.** A user's saved preference wins.

---

### Setup

Use Rails built-in i18n framework. No additional gems needed for basic i18n.

```ruby
# backend/config/application.rb
config.i18n.default_locale = :en
config.i18n.available_locales = [:en, :ar, :fr, :es, :de]
config.i18n.fallbacks = true
config.i18n.enforce_available_locales = true
```

### Locale File Organization

```
backend/config/locales/
├── en/
│   ├── models.en.yml        # ActiveRecord model names and attributes
│   ├── errors.en.yml        # Error messages
│   ├── notifications.en.yml # Push notification templates
│   ├── mailers.en.yml       # Email templates
│   └── api.en.yml           # API response messages
├── ar/
│   ├── models.ar.yml
│   ├── errors.ar.yml
│   └── ...
└── defaults/
    └── devise.en.yml        # Devise-specific translations
```

### Translation Key Naming

Follow dot-separated hierarchical keys matching the domain structure:

```yaml
# backend/config/locales/en/errors.en.yml
en:
  errors:
    not_found: "%{resource} not found"
    unauthorized: "You are not authorized to perform this action"
    validation:
      blank: "%{field} cannot be blank"
      too_short: "%{field} is too short (minimum %{count} characters)"
      taken: "%{field} is already taken"

# backend/config/locales/en/models.en.yml
en:
  activerecord:
    models:
      user: "User"
      order: "Order"
    attributes:
      user:
        email: "Email address"
        full_name: "Full name"
```

### Lazy Lookup in Rails

Use lazy lookup in controllers and mailers to keep keys DRY:

```ruby
# backend/app/controllers/api/v1/orders_controller.rb
class Api::V1::OrdersController < ApplicationController
  def create
    # Looks up: en.api.v1.orders.create.success
    render json: { message: t('.success') }
  end
end
```

### Pluralization

Rails handles pluralization rules per locale:

```yaml
en:
  orders:
    count:
      zero: "No orders"
      one: "%{count} order"
      other: "%{count} orders"

ar:
  orders:
    count:
      zero: "لا طلبات"
      one: "طلب واحد"
      two: "طلبان"
      few: "%{count} طلبات"
      many: "%{count} طلبًا"
      other: "%{count} طلب"
```

### API Response i18n

Set locale from request header in the base controller:

```ruby
# backend/app/controllers/application_controller.rb
class ApplicationController < ActionController::API
  before_action :set_locale

  private

  def set_locale
    locale = request.headers['Accept-Language']&.scan(/^[a-z]{2}/)&.first
    I18n.locale = I18n.available_locales.map(&:to_s).include?(locale) ? locale : I18n.default_locale
  end
end
```

### Date, Time, and Number Formatting

```yaml
en:
  date:
    formats:
      default: "%Y-%m-%d"
      short: "%b %d"
      long: "%B %d, %Y"
  number:
    currency:
      format:
        unit: "$"
        precision: 2
        separator: "."
        delimiter: ","
```

Use `I18n.l(date, format: :short)` and `number_to_currency(amount)` — never format manually.
