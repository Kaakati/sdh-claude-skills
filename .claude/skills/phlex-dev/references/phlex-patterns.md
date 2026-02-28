# Phlex Patterns Reference

Comprehensive reference for Phlex component patterns, API, and Rails integration.

## 1. Component Class Structure

Every Phlex component is a Ruby class that inherits from `Phlex::HTML` (or a project base class). The primary render method is `view_template`.

```ruby
# frozen_string_literal: true

class Components::Atoms::Alert < Components::Base
  def initialize(message:, type: :info)
    @message = message
    @type = type
  end

  def view_template
    div(class: "alert alert-#{@type}", role: "alert") do
      p { @message }
    end
  end
end
```

### HTML Element Methods

Phlex provides methods for every standard HTML element. These methods accept keyword arguments for attributes and a block for content.

```ruby
def view_template
  div(class: "container", id: "main") do
    h1(class: "text-2xl font-bold") { "Page Title" }
    p(class: "text-foreground/80") { "Paragraph content" }
    span(class: "text-sm text-muted-foreground") { "Small text" }
    a(href: "/about", class: "underline text-primary") { "About Us" }
  end
end
```

### Attributes Hash Syntax

All HTML attributes are passed as keyword arguments. Nested hashes create hyphenated attributes (useful for `data-*` and `aria-*`).

```ruby
div(
  class: "dropdown",
  id: "user-menu",
  role: "menu",
  aria: { label: "User menu", expanded: "false" },
  data: {
    controller: "dropdown",
    dropdown_open_value: "false"
  }
)
```

This renders:
```html
<div class="dropdown" id="user-menu" role="menu"
     aria-label="User menu" aria-expanded="false"
     data-controller="dropdown" data-dropdown-open-value="false">
</div>
```

### Void Elements

Void elements (self-closing) do not accept a block.

```ruby
def view_template
  input(type: "text", name: "email", placeholder: "Enter email")
  br
  hr(class: "my-4 border-border")
  img(src: "/logo.png", alt: "Company Logo", class: "h-8 w-auto")
  meta(charset: "utf-8")
  link(rel: "stylesheet", href: "/styles.css")
end
```

## 2. Keyword Arguments for Props

Always use keyword arguments in `initialize` for component props. This makes the API explicit and self-documenting.

### Required Props

```ruby
class Components::Atoms::Heading < Components::Base
  def initialize(text:, level: 1)
    @text = text
    @level = level
  end

  def view_template
    case @level
    when 1 then h1(class: "text-4xl font-bold tracking-tight") { @text }
    when 2 then h2(class: "text-3xl font-semibold tracking-tight") { @text }
    when 3 then h3(class: "text-2xl font-semibold") { @text }
    when 4 then h4(class: "text-xl font-semibold") { @text }
    when 5 then h5(class: "text-lg font-medium") { @text }
    when 6 then h6(class: "text-base font-medium") { @text }
    end
  end
end
```

### Optional Props with Defaults

```ruby
class Components::Atoms::Avatar < Components::Base
  def initialize(src:, alt:, size: :md, rounded: true)
    @src = src
    @alt = alt
    @size = size
    @rounded = rounded
  end
end
```

### Pass-Through Attributes with `**attrs`

Use `**attrs` to forward arbitrary HTML attributes to the root element.

```ruby
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, **attrs)
    @label = label
    @variant = variant
    @attrs = attrs
  end

  def view_template
    button(class: button_classes, **@attrs) { @label }
  end
end

# Usage: render Components::Atoms::Button.new(label: "Save", id: "save-btn", disabled: true)
```

### Prop Validation

Validate required props and enum values in `initialize`.

```ruby
class Components::Atoms::Icon < Components::Base
  VALID_SIZES = %i[xs sm md lg xl].freeze

  def initialize(name:, size: :md)
    @name = name
    raise ArgumentError, "Invalid size: #{size}" unless VALID_SIZES.include?(size)
    @size = size
  end
end
```

## 3. Content Blocks

### Basic Yield

Accept a block to let the caller provide arbitrary content.

```ruby
class Components::Atoms::Card < Components::Base
  def view_template(&block)
    div(class: "rounded-lg border bg-card text-card-foreground shadow-sm p-6", &block)
  end
end

# Usage:
# render Components::Atoms::Card.new do
#   h2 { "Card Title" }
#   p { "Card content goes here." }
# end
```

### Conditional Content

```ruby
class Components::Atoms::Panel < Components::Base
  def initialize(title:)
    @title = title
  end

  def view_template
    div(class: "panel") do
      h3(class: "panel-title") { @title }
      div(class: "panel-body") do
        yield if block_given?
      end
    end
  end
end
```

### Named Slots via Method-Based Slots

Phlex supports slots through public methods that callers can invoke inside the block.

```ruby
class Components::Organisms::Modal < Components::Base
  def initialize(title:)
    @title = title
  end

  def view_template
    div(class: "fixed inset-0 z-50 flex items-center justify-center bg-black/50") do
      div(class: "bg-background rounded-lg shadow-lg max-w-md w-full") do
        header(class: "p-4 border-b") do
          h2(class: "text-lg font-semibold") { @title }
        end
        div(class: "p-4") do
          yield
        end
      end
    end
  end
end
```

### Multiple Content Areas with Lambdas

For components with multiple content slots, accept lambdas or use method-based rendering.

```ruby
class Components::Templates::TwoColumn < Components::Base
  def initialize(sidebar:, &main_content)
    @sidebar = sidebar
    @main_content = main_content
  end

  def view_template
    div(class: "grid grid-cols-12 gap-6") do
      aside(class: "col-span-3") { @sidebar.call(self) }
      main(class: "col-span-9") { @main_content.call(self) }
    end
  end
end
```

## 4. Composition

### Rendering Child Components

Use `render` to compose components from smaller pieces.

```ruby
class Components::Molecules::UserCard < Components::Base
  def initialize(user:)
    @user = user
  end

  def view_template
    div(class: "flex items-center gap-3 p-4 rounded-lg border") do
      render Components::Atoms::Avatar.new(
        src: @user.avatar_url,
        alt: @user.name,
        size: :sm
      )
      div do
        render Components::Atoms::Heading.new(text: @user.name, level: 4)
        p(class: "text-sm text-muted-foreground") { @user.email }
      end
    end
  end
end
```

### Nesting Components Inside Blocks

```ruby
class Components::Organisms::Sidebar < Components::Base
  def initialize(links:)
    @links = links
  end

  def view_template
    nav(class: "flex flex-col gap-1 p-4") do
      @links.each do |link|
        render Components::Molecules::NavLink.new(
          label: link[:label],
          href: link[:href],
          icon: link[:icon],
          active: link[:active]
        )
      end
    end
  end
end
```

### Rendering Collections

```ruby
class Components::Organisms::ProductGrid < Components::Base
  def initialize(products:)
    @products = products
  end

  def view_template
    div(class: "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6") do
      @products.each do |product|
        render Components::Organisms::ProductCard.new(product: product)
      end
    end
  end
end
```

## 5. Layouts

### Composition-Based Layout (Preferred)

The layout component yields to the caller for the main content area.

```ruby
class Components::Templates::AppLayout < Components::Base
  def initialize(title: "App")
    @title = title
  end

  def view_template(&block)
    html do
      head do
        title { @title }
        meta(charset: "utf-8")
        meta(name: "viewport", content: "width=device-width, initial-scale=1")
      end
      body(class: "min-h-screen bg-background text-foreground") do
        render Components::Organisms::Header.new
        main(class: "container mx-auto px-4 py-8", &block)
        render Components::Organisms::Footer.new
      end
    end
  end
end
```

### Dashboard Layout with Sidebar

```ruby
class Components::Templates::DashboardLayout < Components::Base
  def initialize(title: "Dashboard")
    @title = title
  end

  def view_template(&block)
    div(class: "min-h-screen flex flex-col") do
      render Components::Organisms::Header.new
      div(class: "flex flex-1") do
        render Components::Organisms::Sidebar.new(links: sidebar_links)
        main(class: "flex-1 p-6 bg-muted/30", &block)
      end
    end
  end

  private

  def sidebar_links
    [
      { label: "Dashboard", href: "/dashboard", icon: "home", active: true },
      { label: "Projects", href: "/projects", icon: "folder" },
      { label: "Settings", href: "/settings", icon: "cog" }
    ]
  end
end
```

### Page Using a Layout

```ruby
class Views::Dashboard::Index < Views::Base
  def initialize(stats:, recent_activity:)
    @stats = stats
    @recent_activity = recent_activity
  end

  def view_template
    render Components::Templates::DashboardLayout.new(title: "Dashboard") do
      render Components::Atoms::Heading.new(text: "Dashboard", level: 1)
      render_stats_grid
      render_recent_activity
    end
  end

  private

  def render_stats_grid
    div(class: "grid grid-cols-1 md:grid-cols-3 gap-4 mt-6") do
      @stats.each do |stat|
        render Components::Molecules::StatCard.new(
          label: stat[:label],
          value: stat[:value],
          trend: stat[:trend]
        )
      end
    end
  end

  def render_recent_activity
    div(class: "mt-8") do
      render Components::Atoms::Heading.new(text: "Recent Activity", level: 2)
      # ... activity list
    end
  end
end
```

## 6. Rails Integration

### Controller Rendering

Render Phlex views directly from Rails controllers.

```ruby
class ArticlesController < ApplicationController
  def index
    articles = Article.published.order(created_at: :desc).page(params[:page])
    render Views::Articles::Index.new(articles: articles)
  end

  def show
    article = Article.find(params[:id])
    render Views::Articles::Show.new(article: article)
  end
end
```

### Route Helpers

Include Rails route helpers in your base class.

```ruby
class Components::Base < Phlex::HTML
  include Phlex::Rails::Helpers::Routes
  include Phlex::Rails::Helpers::ContentFor
  include Phlex::Rails::Helpers::CSRFMetaTags

  # Access route helpers via `helpers`
  # e.g., helpers.articles_path, helpers.root_url
end
```

### Using URL Helpers in Components

```ruby
class Components::Molecules::NavLink < Components::Base
  def initialize(label:, href:, active: false)
    @label = label
    @href = href
    @active = active
  end

  def view_template
    a(
      href: @href,
      class: link_classes
    ) { @label }
  end

  private

  def link_classes
    base = "px-3 py-2 rounded-md text-sm font-medium transition-colors"
    if @active
      "#{base} bg-primary/10 text-primary"
    else
      "#{base} text-muted-foreground hover:text-foreground hover:bg-muted"
    end
  end
end
```

### CSRF Token (Authenticity Token)

```ruby
class Components::Molecules::LoginForm < Components::Base
  def view_template
    form(action: helpers.sessions_path, method: "post") do
      authenticity_token_input
      # form fields...
      render Components::Atoms::Button.new(label: "Log In", type: :submit)
    end
  end

  private

  def authenticity_token_input
    input(
      type: "hidden",
      name: "authenticity_token",
      value: helpers.form_authenticity_token
    )
  end
end
```

### Turbo Frame Integration

```ruby
class Components::Organisms::CommentList < Components::Base
  def initialize(comments:, article_id:)
    @comments = comments
    @article_id = article_id
  end

  def view_template
    turbo_frame_tag("comments") do
      div(class: "space-y-4") do
        @comments.each do |comment|
          render Components::Molecules::Comment.new(comment: comment)
        end
      end
    end
  end

  private

  def turbo_frame_tag(id, &block)
    tag("turbo-frame", id: id, &block)
  end
end
```

### Turbo Stream Integration

```ruby
class Components::Organisms::LiveNotifications < Components::Base
  def initialize(notifications:)
    @notifications = notifications
  end

  def view_template
    div(id: "notifications", data: { controller: "notifications" }) do
      turbo_stream_from("notifications")
      div(class: "space-y-2") do
        @notifications.each do |notification|
          render Components::Molecules::NotificationItem.new(notification: notification)
        end
      end
    end
  end

  private

  def turbo_stream_from(channel)
    tag("turbo-cable-stream-source", channel: channel, signed_stream_name: channel)
  end
end
```

## 7. Kits (Module Grouping)

Group related components with Ruby modules. Rails autoloading handles resolution automatically if the directory structure matches the namespace.

```ruby
# backend/app/components/atoms/button.rb
module Components
  module Atoms
    class Button < Components::Base
      # ...
    end
  end
end
```

### Autoloading with Rails

Ensure `backend/app/components` and `backend/app/views` are in the autoload paths:

```ruby
# config/application.rb
config.autoload_paths << Rails.root.join("app/components")
config.autoload_paths << Rails.root.join("app/views")
```

Phlex-rails handles this automatically when installed via the generator.

## 8. class_variants

The `class_variants` gem provides a structured way to manage multi-variant Tailwind classes.

### Definition Syntax

```ruby
class Components::Atoms::Button < Components::Base
  VARIANTS = class_variants(
    base: "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline"
      },
      size: {
        sm: "h-8 rounded-md px-3 text-xs",
        md: "h-9 px-4 py-2 text-sm",
        lg: "h-10 rounded-md px-6 text-base",
        icon: "h-9 w-9"
      }
    },
    defaults: {
      variant: :primary,
      size: :md
    }
  )

  def initialize(label:, variant: :primary, size: :md, **attrs)
    @label = label
    @variant = variant
    @size = size
    @attrs = attrs
  end

  def view_template
    button(class: VARIANTS.render(variant: @variant, size: @size), **@attrs) do
      @label
    end
  end
end
```

### Compound Variants

```ruby
VARIANTS = class_variants(
  base: "...",
  variants: {
    variant: { primary: "...", secondary: "..." },
    size: { sm: "...", lg: "..." }
  },
  compound_variants: [
    { variant: :primary, size: :lg, class: "uppercase tracking-wide" }
  ],
  defaults: { variant: :primary, size: :sm }
)
```

### Rendering

```ruby
VARIANTS.render(variant: :primary, size: :lg)
# => "inline-flex items-center ... bg-primary ... h-10 ... uppercase tracking-wide"
```

## 9. Stimulus Data Attributes

### Controller Binding

```ruby
div(data: { controller: "clipboard" }) do
  input(
    type: "text",
    value: "Copy me",
    data: { clipboard_target: "source" }
  )
  button(
    data: { action: "clipboard#copy" },
    class: "btn"
  ) { "Copy" }
end
```

### Multiple Controllers

```ruby
div(data: { controller: "dropdown tooltip" }) do
  # Both controllers attach to this element
end
```

### Action Descriptors

```ruby
# Click action (default for buttons)
button(data: { action: "controller#method" })

# Explicit event
input(data: { action: "input->search#filter" })

# Multiple actions
button(data: { action: "click->dropdown#toggle keydown.escape->dropdown#close" })
```

### Values

```ruby
div(
  data: {
    controller: "countdown",
    countdown_seconds_value: 60,
    countdown_interval_value: 1000
  }
)
```

### Targets

```ruby
div(data: { controller: "tabs" }) do
  button(data: { tabs_target: "tab", action: "tabs#select" }) { "Tab 1" }
  button(data: { tabs_target: "tab", action: "tabs#select" }) { "Tab 2" }
  div(data: { tabs_target: "panel" }) { "Panel 1 content" }
  div(data: { tabs_target: "panel" }, class: "hidden") { "Panel 2 content" }
end
```

## 10. Installation and Setup

### Gemfile

```ruby
gem "phlex-rails", "~> 2.0"
gem "class_variants", "~> 1.0"
```

### Generator

```bash
rails generate phlex:install
```

This creates:
- `app/views/base.rb` (or `app/views/application_view.rb`)
- Configures autoloading

### Component Generator

```bash
rails generate phlex:component Atoms::Button
# Creates: app/components/atoms/button.rb
```

### Base Classes Setup

```ruby
# backend/app/components/base.rb
class Components::Base < Phlex::HTML
  include Phlex::Rails::Helpers::Routes
  include Phlex::Rails::Helpers::ContentFor

  if Rails.env.development?
    def before_template
      comment { "#{self.class.name}" }
      super
    end
  end
end

# backend/app/views/base.rb
class Views::Base < Phlex::HTML
  include Phlex::Rails::Helpers::Routes
  include Phlex::Rails::Helpers::ContentFor
  include Phlex::Rails::Helpers::CSRFMetaTags
end
```

### Development Helpers

In development mode, add HTML comments before each component for debugging:

```ruby
class Components::Base < Phlex::HTML
  if Rails.env.development?
    def before_template
      comment { self.class.name }
      super
    end
  end
end
```

This renders `<!-- Components::Atoms::Button -->` before each component in development HTML.
