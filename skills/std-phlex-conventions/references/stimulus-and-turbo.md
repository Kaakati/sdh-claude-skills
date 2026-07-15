# Wiring Interactivity: Stimulus and Turbo in Phlex Components

Load-bearing rules restated (this file is self-contained):

- `data-controller` goes on the **outermost element the controller owns** — nothing else.
- `data-action` uses `"event->controller#method"` and goes on the interactive element.
- `data-{controller}-target` marks elements the controller reads or writes.
- Stimulus controllers live in `app/javascript/controllers/`.
- Prefer Turbo Frames over full-page Drive navigation for component-level updates.

Phlex renders `data:` hashes with underscores converted to dashes:
`data: { dropdown_target: "menu" }` → `data-dropdown-target="menu"`. Nested hashes are **not**
supported — flatten them.

---

## Decision: where does `data-controller` go?

Bad — controller on the page wrapper, so every dropdown on the page shares one instance and
`this.menuTarget` picks the wrong menu:

```ruby
class Views::Dashboard::Index < Views::Base
  def view_template
    div(data: { controller: "dropdown" }) do          # scope is the whole page
      @menus.each { |m| render Components::Organisms::Dropdown.new(label: m.label) }
    end
  end
end
```

Good — each component instance carries its own controller scope:

```ruby
# app/components/organisms/dropdown.rb
class Components::Organisms::Dropdown < Components::Base
  def initialize(label:, align: :start)
    @label = label
    @align = align
  end

  def view_template(&block)
    div(class: "relative inline-block", data: { controller: "dropdown" }) do
      render Components::Atoms::Button.new(
        label: @label,
        variant: :outline,
        aria_haspopup: "menu",
        aria_expanded: "false",
        data: {
          action: "click->dropdown#toggle",
          dropdown_target: "trigger"
        }
      )

      div(
        role: :menu,
        class: menu_classes,
        hidden: true,
        data: { dropdown_target: "menu" },
        &block
      )
    end
  end

  private

  def menu_classes
    tokens(
      "absolute z-50 mt-2 min-w-[12rem] rounded-md border border-border bg-popover " \
      "p-1 text-popover-foreground shadow-md",
      (@align == :start) => "left-0",
      (@align == :end) => "right-0"
    )
  end
end
```

```js
// app/javascript/controllers/dropdown_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["menu", "trigger"]

  connect() {
    this.close = this.close.bind(this)
  }

  toggle(event) {
    event.stopPropagation()
    this.menuTarget.hidden ? this.open() : this.close()
  }

  open() {
    this.menuTarget.hidden = false
    this.triggerTarget.setAttribute("aria-expanded", "true")
    document.addEventListener("click", this.close)
  }

  close() {
    this.menuTarget.hidden = true
    this.triggerTarget.setAttribute("aria-expanded", "false")
    document.removeEventListener("click", this.close)
  }

  disconnect() {
    document.removeEventListener("click", this.close)
  }
}
```

---

## Decision: how do I pass data into a Stimulus controller?

Bad — inline JS, and server data smuggled through a class name:

```ruby
button(onclick: "fetch('/cart/add/#{@product.id}')", class: "js-add-#{@product.id}") { "Add" }
```

Good — Stimulus values API, typed and reactive:

```ruby
class Components::Molecules::Countdown < Components::Base
  def initialize(ends_at:)
    @ends_at = ends_at
  end

  def view_template
    div(
      class: "font-mono text-sm text-muted-foreground",
      data: {
        controller: "countdown",
        countdown_ends_at_value: @ends_at.iso8601,
        countdown_expired_text_value: "Expired"
      }
    ) do
      span(data: { countdown_target: "output" }) { "--:--" }
    end
  end
end
```

```js
// app/javascript/controllers/countdown_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["output"]
  static values = { endsAt: String, expiredText: { type: String, default: "Expired" } }

  connect() {
    this.tick()
    this.timer = setInterval(() => this.tick(), 1000)
  }

  disconnect() {
    clearInterval(this.timer)
  }

  tick() {
    const remaining = new Date(this.endsAtValue) - Date.now()
    if (remaining <= 0) {
      this.outputTarget.textContent = this.expiredTextValue
      clearInterval(this.timer)
      return
    }
    const m = Math.floor(remaining / 60000)
    const s = Math.floor((remaining % 60000) / 1000)
    this.outputTarget.textContent = `${m}:${String(s).padStart(2, "0")}`
  }
}
```

Rule: **never** put an event handler attribute (`onclick`, `onchange`) in a Phlex template. It
bypasses Stimulus lifecycle and breaks under a CSP.

---

## Decision: passing an action to a nested component

An atom must accept `**attrs` for this to work (see the component-levels reference). The parent
supplies the action; the atom stays generic.

Bad — the atom hardcodes a controller it should know nothing about:

```ruby
class Components::Atoms::Button < Components::Base
  def view_template
    button(data: { action: "modal#close" }, class: button_classes) { @label } # atom coupled to modal
  end
end
```

Good:

```ruby
class Components::Organisms::Modal < Components::Base
  def view_template(&block)
    div(data: { controller: "modal" }) do
      dialog(class: "rounded-lg border bg-card p-6 shadow-lg backdrop:bg-black/50",
             data: { modal_target: "dialog", action: "close->modal#onClose" }) do
        div(&block)
        render Components::Atoms::Button.new(
          label: "Close", variant: :secondary,
          data: { action: "click->modal#close" }
        )
      end
    end
  end
end
```

---

## Decision: partial page update — Frame or Stream?

| Situation | Use |
|---|---|
| User action replaces a region with a server-rendered response | **Turbo Frame** |
| Server pushes an update nobody asked for (broadcast, job finished) | **Turbo Stream** |
| Region must update its URL/history | Frame + `data-turbo-action="advance"` |
| Multiple disjoint regions change from one response | Turbo Stream (multi-target) |

### Turbo Frame — lazy-loaded section

Bad — a full-page reload for a filter change:

```ruby
a(href: "/products?category=shoes") { "Shoes" } # Turbo Drive swaps the whole <body>
```

Good — frame-scoped navigation with a URL update:

```ruby
class Components::Organisms::ProductList < Components::Base
  def initialize(products:, categories:, current_category: nil)
    @products = products
    @categories = categories
    @current_category = current_category
  end

  def view_template
    div(class: "space-y-4") do
      nav(class: "flex gap-2", aria_label: "Filter by category") do
        @categories.each do |category|
          render Components::Molecules::NavLink.new(
            label: category.name,
            href: "/products?category=#{category.slug}",
            active: category.slug == @current_category
          )
        end
      end

      turbo_frame_tag "product_list", data: { turbo_action: "advance" } do
        div(class: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3") do
          @products.each do |product|
            render Components::Organisms::ProductCard.new(product: product, path: "/products/#{product.id}")
          end
        end
      end
    end
  end
end
```

In Phlex, `turbo_frame_tag` is a Rails helper — expose it in `Components::Base`:

```ruby
# app/components/base.rb
class Components::Base < Phlex::HTML
  include Phlex::Rails::Helpers::TurboFrameTag
  include Phlex::Rails::Helpers::Routes
  include Phlex::Rails::Helpers::ImageTag
end
```

Lazy frame — defers an expensive section until it scrolls into view:

```ruby
turbo_frame_tag "recommendations", src: "/products/#{@product.id}/recommendations", loading: :lazy do
  render Components::Molecules::Skeleton.new(rows: 3)
end
```

### Turbo Stream — server-pushed update

Bad — polling from a Stimulus controller:

```js
setInterval(() => fetch("/notifications").then(r => r.text()).then(h => this.element.innerHTML = h), 3000)
```

Good — broadcast a Phlex-rendered component over a stream:

```ruby
# app/views/notifications/create.turbo_stream.erb equivalent, rendered from a job:
class NotificationBroadcastJob < ApplicationJob
  def perform(notification)
    Turbo::StreamsChannel.broadcast_prepend_to(
      "user_#{notification.user_id}_notifications",
      target: "notification_list",
      html: Components::Molecules::NotificationItem.new(notification: notification).call
    )
  end
end
```

```ruby
# the subscribing component
class Components::Organisms::NotificationList < Components::Base
  include Phlex::Rails::Helpers::TurboStreamFrom

  def initialize(user_id:, notifications:)
    @user_id = user_id
    @notifications = notifications
  end

  def view_template
    turbo_stream_from "user_#{@user_id}_notifications"

    ul(id: "notification_list", class: "divide-y divide-border") do
      @notifications.each { |n| render Components::Molecules::NotificationItem.new(notification: n) }
    end
  end
end
```

Rule: a Turbo Stream target must be a **stable DOM id**. Derive it from the record, never from
the loop index.

Bad:

```ruby
@comments.each_with_index { |c, i| li(id: "comment_#{i}") { c.body } } # ids shift on delete
```

Good:

```ruby
@comments.each { |c| li(id: dom_id(c), class: "py-3") { c.body } }
```

---

## Decision: form submission inside a frame

Bad — the form escapes its frame because the redirect target has no matching frame:

```ruby
turbo_frame_tag "new_comment" do
  form_with(model: @comment) { |f| ... }   # controller redirects to a page with no "new_comment" frame
end
```

Good — respond to the frame; on invalid, re-render the frame with `:unprocessable_entity`:

```ruby
# app/controllers/comments_controller.rb
def create
  @comment = @post.comments.build(comment_params)

  if @comment.save
    render turbo_stream: turbo_stream.append(
      "comment_list", Components::Molecules::CommentItem.new(comment: @comment).call
    )
  else
    render Components::Organisms::CommentForm.new(comment: @comment), status: :unprocessable_entity
  end
end
```

The 422 status is required — Turbo ignores non-2xx form responses unless they are 4xx/5xx with
renderable HTML, and a `200` on failure leaves the form silently unchanged.
