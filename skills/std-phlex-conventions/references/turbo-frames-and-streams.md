# Turbo Frames and Streams with Phlex Components

Load-bearing rules restated (this file is self-contained):

- Prefer Turbo Frames over full-page Turbo Drive navigation for component-level updates.
- Use Turbo Streams for server-pushed DOM updates (append, prepend, replace, remove).
- Rails view helpers (`turbo_frame_tag`, `turbo_stream_from`, `dom_id`) must be included into
  `Components::Base` before a Phlex component can call them.
- View components never query or mutate; controllers and jobs fetch and pass data in as props.

For Stimulus controller scoping, the values API, and passing `data-action` into nested components,
read `references/stimulus-wiring.md`.

---

## Decision: partial page update — Frame or Stream?

| Situation | Use |
|---|---|
| User action replaces a region with a server-rendered response | **Turbo Frame** |
| Server pushes an update nobody asked for (broadcast, job finished) | **Turbo Stream** |
| Region must update its URL/history | Frame + `data-turbo-action="advance"` |
| A list opens a record beside it (list-detail) | Frame + `data-turbo-action="advance"` on the row; the record's own page wraps its body in the same frame id |
| Multiple disjoint regions change from one response | Turbo Stream (multi-target) |

---

## Decision: rendering a Turbo Frame — lazy-loaded section

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
            current: (category.slug == @current_category ? "page" : nil)
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

---

## Decision: rendering a Turbo Stream — server-pushed update

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

---

## Decision: a list opens a record beside it (list-detail)

Only for lists people work through in order, on wide screens, when the record reads well at half
width and has no tabs of its own. Anything else drills into a full page. The rule is
`@skills/ui-ux-patterns/references/drill-down-navigation.md`; the areas, section nav and breadcrumb
used below are `references/navigation.md`.

Bad — the record loads into the frame and the URL never changes:

```ruby
a(href: invoice_path(invoice), data: { turbo_frame: "invoice_detail" }) { invoice.reference }
# no URL for the record and no history entry: a refresh or a shared link loses it, and Back skips it
```

Good — the frame navigation is promoted to a visit, and the record's page is the same frame:

```ruby
# app/views/invoices/index.rb — excerpt
def view_template
  render Components::Templates::AreaLayout.new(areas: @areas) do
    div(class: "flex gap-6", data: { controller: "list-detail", list_detail_frame_value: "invoice_detail" }) do
      ul(class: "min-w-0 flex-1 divide-y divide-border") do
        @invoices.each do |invoice|
          li do
            a(href: invoice_path(invoice), class: "block min-h-11 px-3 py-2 text-sm text-foreground hover:bg-accent",
              data: { list_detail_target: "row", turbo_frame: "invoice_detail", turbo_action: "advance",
                      action: "list-detail#select" }) { invoice.reference }
          end
        end
      end
      turbo_frame_tag "invoice_detail", class: "hidden min-w-0 flex-1 lg:block",
                      data: { list_detail_target: "panel", action: "turbo:frame-load->list-detail#focus" }
    end
  end
end
```

```ruby
# app/views/invoices/show.rb — excerpt: a hard load renders the full page; a frame visit keeps only the frame
def view_template
  render Components::Templates::AreaLayout.new(areas: @areas) do
    render Components::Molecules::Breadcrumb.new(items: @crumbs, current: @invoice.reference)
    turbo_frame_tag "invoice_detail" do
      send(@panel ? :h2 : :h1, tabindex: "-1", class: "text-xl font-semibold text-foreground") { @invoice.reference }
      render Components::Organisms::InvoiceDetail.new(invoice: @invoice)
    end
  end
end
# controller: render Views::Invoices::Show.new(invoice:, areas: navigation.areas, crumbs:, panel: turbo_frame_request?)
```

```js
// app/javascript/controllers/list_detail_controller.js
import { Controller } from "@hotwired/stimulus"

const wide = window.matchMedia("(min-width: 64rem)") // Tailwind's lg

export default class extends Controller {
  static targets = ["row", "panel"]
  static values = { frame: String }

  initialize() { this.retarget = this.retarget.bind(this) }

  connect() {
    wide.addEventListener("change", this.retarget)
    this.retarget()
  }

  disconnect() { wide.removeEventListener("change", this.retarget) }

  // One pane at a time on narrow screens: rows open the record's full page, not a hidden panel.
  retarget() {
    this.rowTargets.forEach((row) => { row.dataset.turboFrame = wide.matches ? this.frameValue : "_top" })
  }

  select({ currentTarget }) {
    this.rowTargets.forEach((row) => row.removeAttribute("aria-current"))
    currentTarget.setAttribute("aria-current", "page")
  }

  focus() { this.panelTarget.querySelector("h2")?.focus() } // a frame swap moves no focus by itself
}
```

- **`advance` makes the level real.** "To promote a Frame navigation to a Visit, render the element
  with the [data-turbo-action] attribute" (Turbo Handbook — Decompose with Turbo Frames). The record
  gets a URL and a history entry, and Back and Forward become restoration visits (Turbo Handbook —
  Navigate with Turbo Drive).
- **The record's page wraps its body in the same frame id.** A hard load, refresh or shared link
  renders the full page with its breadcrumb and `h1`; a frame visit keeps only the matching frame.
  `turbo_frame_request?` tells the controller which one it is rendering.
- **Focus goes to the panel heading.** `turbo:frame-load` fires on the `<turbo-frame>` element once
  it finishes loading (Turbo reference — Events), so the action sits on the frame itself and needs
  no bubbling. The heading carries `tabindex="-1"`.
- **The selected row keeps a visible selection with two cues** (a background and a weight), styled
  from its `aria-current` in the stylesheet — never colour alone.
- **Verify in the app before shipping:** Back and Forward reopen the previous record in the panel and
  move the row selection with it. The restoration of a promoted frame visit was not tested end to end.
