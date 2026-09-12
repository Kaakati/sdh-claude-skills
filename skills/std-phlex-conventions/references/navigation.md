# Drill-down Navigation in Phlex Views

How a Rails app rendered with Phlex builds the house drill-down navigation. The rules — levels,
location cues, Up and Back, search as the second way, the command palette, the anti-patterns — are
`@skills/ui-ux-patterns/references/drill-down-navigation.md`. The endpoints behind each level —
shallow routes, `ancestors`, scoped counts, list parameters, search — are
`@skills/std-api-design/references/drill-down-resources.md`. This file is the Phlex mechanics only.

Load-bearing rules restated (this file is self-contained):

1. **The global sidebar lists areas only**, with optional static group labels. It never nests an
   area's sections; those render in the area's own layout as the section sub-nav.
2. **Routes nest collections one level and keep members flat** (`shallow: true`).
3. **The controller builds everything a nav component shows** — areas, sections, current state,
   breadcrumb items — from `policy(:navigation)` booleans and the permission-filtered `ancestors`.
   Components never call Pundit, read `request.path`, or look at history.
4. **Current state matches whole path segments:** a path is inside `/orders` when it equals it or
   starts with `/orders/`, never on a bare prefix. `aria-current="page"` goes only on a link to the
   current URL; `"true"` goes on the area or section the page sits inside.
5. **Breadcrumbs are rendered from `ancestors`**, and the list crumb's `href` carries that list's
   last query string — one control, no separate "Back to results".
6. **A level change inside a frame carries `data-turbo-action="advance"`**, so it has a URL and a
   history entry (list-detail → `references/turbo-frames-and-streams.md`).
7. **Filters sit beside the list, in the page content** — never in the global sidebar or its slot.
8. **A command palette, where a product has one, mirrors the nav:** its "Go to" entries are the same
   controller-built areas, its records come from the search endpoint, a visible button opens it,
   and nothing is reachable only through it.

**Owned elsewhere — do not duplicate:**

| Topic | Owner |
|---|---|
| Levels, area budget, the phone-width Menu rule, breadcrumb and palette rules, anti-patterns | `@skills/ui-ux-patterns/references/drill-down-navigation.md` |
| Shallow routes, `ancestors`, scoped counts, list parameters, search, 404 not 403 | `@skills/std-api-design/references/drill-down-resources.md` |
| `NavigationPolicy` and its predicates | `@skills/std-rails-conventions/references/roles-and-permissions.md` |
| The React stacks' nav config, `visibleNav`, per-role UI tests | `@skills/access-control-designer/references/ui-gates.md` |
| Hide, disable-with-reason, locked; derived landing; empty and one-item groups | `@skills/ui-ux-patterns/references/role-based-ux.md` |
| List-detail frames and focus on frame load | `references/turbo-frames-and-streams.md` |
| A page receives its location from the controller | `references/component-levels-composites.md` |
| ARIA, target sizes, focus appearance | the `std-accessibility` skill |

---

## Decision: routes for the levels

```ruby
# config/routes.rb — collections nest one level under their one canonical parent; members stay flat
resources :orders, only: %i[index show], shallow: true do
  resources :shipments, only: %i[index show]
end
resources :approvals, only: :index
# => /orders · /orders/:id · /orders/:order_id/shipments · /shipments/:id · /approvals
```

- "The general rule of thumb is to only nest resources 1 level deep" (Ruby on Rails Guides — Rails
  Routing from the Outside In). A flat member action scopes the record itself —
  `policy_scope(Shipment).find(params[:id])` — so a record outside the caller's scope is a 404.
- **One canonical parent means one home area and one breadcrumb path.** A second nested route to
  the same record is a second location; link to the canonical URL instead.
- **A detail's sub-collections are navigation tabs at the same level**, each with its own URL
  (`/orders/:order_id/shipments`), rendered by the detail page — not new levels.

---

## Decision: the nav the controller builds

The config mirrors `src/lib/nav.ts` (`ui-gates.md`) field for field — `key`, `label`, `icon`, `href`,
`permission`, `entitlement`, `match`, `sections` — with a `NavigationPolicy` predicate standing in for
the permission key.

```ruby
# app/models/navigation.rb
class Navigation
  AREAS = [ # canonical order; labels are i18n keys; match: flat member routes the area owns
    { key: :orders, label: "nav.orders", icon: "shopping-cart", href: "/orders", permission: :orders?,
      match: ["/shipments"] },
    { key: :approvals, label: "nav.approvals", icon: "check-circle", href: "/approvals", permission: :approvals?,
      entitlement: "approvals" }, # a plan feature name, as in nav.ts and /me — never a permission key
    { key: :organization, label: "nav.organization", icon: "building", href: "/members", permission: :members?,
      sections: [
        { key: :members, label: "nav.members", href: "/members", permission: :members? },
        { key: :billing, label: "nav.billing", href: "/billing", permission: :billing? }
      ] }
  ].freeze

  def initialize(policy, path)
    @policy = policy
    @path = path
  end

  # Filter first, then mark. An area or section the role cannot use never reaches a component.
  def areas
    @areas ||= AREAS.filter_map do |area|
      next unless @policy.public_send(area[:permission])
      sections = Array(area[:sections]).select { |section| @policy.public_send(section[:permission]) }
      next if area[:sections] && sections.empty?
      display(area.merge(sections:)).merge(sections: sections.map { |section| display(section) }) # state from permitted sections only
    end
  end

  private

  def display(item)
    { label: I18n.t(item[:label]), href: item[:href], current: state(item),
      locked: item[:entitlement] ? @policy.locked?(item[:entitlement]) : false } # locked? takes the feature name
  end

  def state(item)
    return "page" if @path == item[:href]
    prefixes = [item[:href], *item[:match], *Array(item[:sections]).map { |section| section[:href] }]
    "true" if prefixes.any? { |prefix| @path == prefix || @path.start_with?("#{prefix}/") }
  end
end
```

```ruby
# app/controllers/application_controller.rb — excerpt
private

def navigation = @navigation ||= Navigation.new(policy(:navigation), request.path)
```

- **Pass `navigation.areas` — plain hashes — never the `Navigation` object.** Its predicates would
  then run inside a render, which is authorization in the view layer.
- `/orders-archive` is not inside `/orders`; a `start_with?("/orders")` test says it is.
- A plan-locked area stays visible and locked as **one** entry (`role-based-ux.md`). Its
  `entitlement` is a plan feature name — the string `nav.ts` and `/me` use — and
  `NavigationPolicy#locked?` takes that name, never a permission key (`roles-and-permissions.md`).

---

## Decision: the app sidebar holds areas only

```ruby
# app/components/organisms/app_sidebar.rb
class Components::Organisms::AppSidebar < Components::Base
  def initialize(areas:)
    @areas = areas # Navigation#areas: filtered, marked, translated
  end

  def view_template
    return if @areas.size < 2 # one area: its section nav is that role's primary nav

    div(data: { controller: "disclosure" }) do
      button(type: "button", class: "min-h-11 px-3 text-sm font-medium lg:hidden", aria_expanded: "false",
             aria_controls: "app-nav", data: { action: "disclosure#toggle", disclosure_target: "trigger" }) { I18n.t("nav.menu") }
      nav(id: "app-nav", aria_label: I18n.t("nav.main"), class: "hidden border-r border-border bg-card p-4 lg:block",
          data: { disclosure_target: "panel" }) do
        ul(class: "space-y-1") do
          @areas.each { |area| li { render Components::Molecules::NavLink.new(**area.slice(:label, :href, :current, :locked)) } }
        end
      end
    end
  end
end
```

```ruby
# app/components/molecules/nav_link.rb
class Components::Molecules::NavLink < Components::Base
  BASE = "flex min-h-11 items-center rounded-md border-l-2 px-3 text-sm " \
         "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
  CURRENT = "border-primary bg-accent font-semibold text-accent-foreground" # two cues: the bar and the weight
  OTHER = "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"

  def initialize(label:, href:, current: nil, locked: false)
    @label = label
    @href = href
    @current = current # "page" | "true" | nil: a boolean cannot tell the page from the area it sits in
    @locked = locked # plan-locked: still a link; the page explains the plan and how to get it
  end

  def view_template
    a(href: @href, aria_current: @current, class: "#{BASE} #{@current ? CURRENT : OTHER}") do
      plain @label
      span(class: "ml-auto rounded-sm bg-muted px-1.5 text-xs text-muted-foreground") { I18n.t("plans.locked") } if @locked
    end
  end
end
```

```js
// app/javascript/controllers/disclosure_controller.js — a button that shows a list of links, never role="menu"
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["trigger", "panel"]

  toggle() {
    const open = this.triggerTarget.getAttribute("aria-expanded") !== "true"
    this.triggerTarget.setAttribute("aria-expanded", String(open))
    this.panelTarget.classList.toggle("hidden", !open)
  }
}
```

- **The desktop sidebar ships visible.** Below `lg` the labelled "Menu" button reveals the same list
  — the sketch shows the many-areas case; when to use a visible bar instead is
  `drill-down-navigation.md`'s phone-width rule.
- **The class is toggled, not the `hidden` attribute**: Tailwind's preflight hides `[hidden]` with
  `!important`, so `lg:block` could never show it on desktop.
- **Group labels, when a role needs them, are static headings** — never links, never collapsible.
  A group with one visible area loses its label (`role-based-ux.md`).
- **Never** a section list under an area, a recursive renderer over `sections`, or list filters in
  this organism or in the template slot that holds it.

---

## Decision: the area layout renders the section sub-nav

```ruby
# app/components/templates/area_layout.rb — every page of every area renders through this
class Components::Templates::AreaLayout < Components::Base
  def initialize(areas:)
    @areas = areas
  end

  def view_template
    div(class: "min-h-screen bg-background text-foreground lg:flex") do
      render Components::Organisms::AppSidebar.new(areas: @areas)
      main(class: "min-w-0 flex-1 space-y-6 p-6") do
        section_nav
        yield
      end
    end
  end

  private

  def section_nav
    area = @areas.find { |candidate| candidate[:current] }
    return unless area && area[:sections].size > 1 # one permitted section: no sub-nav

    render Components::Organisms::SectionNav.new(label: I18n.t("nav.sections", area: area[:label]), sections: area[:sections])
  end
end
```

```ruby
# app/components/organisms/section_nav.rb — local navigation: visible on every page of the area, quieter than the sidebar
class Components::Organisms::SectionNav < Components::Base
  def initialize(label:, sections:)
    @label = label
    @sections = sections
  end

  def view_template
    nav(aria_label: @label) do
      ul(class: "flex gap-6 overflow-x-auto border-b border-border") do
        @sections.each { |section| li { section_link(section) } }
      end
    end
  end

  private

  def section_link(section)
    state = section[:current] ? "border-primary font-semibold text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"
    a(href: section[:href], aria_current: section[:current],
      class: "inline-flex min-h-11 items-center border-b-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring #{state}") { section[:label] }
  end
end
```

- Local navigation makes second- and third-tier content cheaper to reach and must stay less salient
  than the global nav (Nielsen Norman Group — Local Navigation Is a Valuable Orientation and
  Wayfinding Aid). Tabs fit a handful of sections; the section-count thresholds for a local list or
  an overview page are in `drill-down-navigation.md`.
- A flat member route (`/shipments/:id`) marks its area through `match`. No section is marked there;
  the breadcrumb carries that context.

---

## Decision: breadcrumbs from `ancestors`

```ruby
# app/controllers/orders_controller.rb — excerpt: the list remembers its state for the crumb
def index
  session[:orders_list_query] = list_params.to_h # filters, sort, query — never a cursor
  # …scope, paginate, render Views::Orders::Index.new(orders:, areas: navigation.areas)
end

private

def list_params = params.permit(:status, :sort, :q)
```

```ruby
# app/controllers/shipments_controller.rb — L5 on a flat route
class ShipmentsController < ApplicationController
  CRUMB_PATHS = { "order" => :order_path }.freeze # a closed map: data never names a route

  def show
    shipment = policy_scope(Shipment).includes(:order).find(params[:id])
    authorize shipment
    ancestors = Hierarchy::Ancestors.new(pundit_user).for(shipment) # readable records, root first; Shipment#ancestor_chain is [order]
    render Views::Shipments::Show.new(shipment:, areas: navigation.areas, crumbs: crumbs_for(ancestors))
  end

  private

  def crumbs_for(ancestors) # records, per drill-down-resources.md's ancestors contract — not hashes
    list = { label: t("orders.list.title"), href: orders_path(session.fetch(:orders_list_query, {}).symbolize_keys) }
    [list, *ancestors.map { |node| { label: node.name, href: public_send(CRUMB_PATHS.fetch(node.model_name.element), node) } }]
  end
end
```

```ruby
# app/components/molecules/breadcrumb.rb — display-ready items, root → parent
class Components::Molecules::Breadcrumb < Components::Base
  def initialize(items:, current:)
    @items = items
    @current = current
  end

  def view_template
    return if @items.empty? # an area root, or a list with no page above it, shows no trail

    nav(aria_label: I18n.t("breadcrumb.label")) do
      ol(class: "hidden items-center gap-2 text-sm text-muted-foreground md:flex") do
        @items.each { |item| li(class: "flex items-center gap-2") { crumb_link(item); span(aria_hidden: "true") { "/" } } }
        li { span(aria_current: "page", class: "font-medium text-foreground") { @current } }
      end
      p(class: "text-sm md:hidden") { crumb_link(@items.last) } # narrow screens: the parent only
    end
  end

  private

  def crumb_link(item) # not `link`: Phlex already defines the <link> element under that name
    a(href: item[:href], class: "inline-flex min-h-6 items-center hover:text-foreground " \
                                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring") { item[:label] }
  end
end
```

- **The trail is hierarchy, not history** — "Breadcrumbs are not intended to show the history of
  pages traversed" (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and
  Mobile). An ancestor the caller cannot read never arrives, so the molecule renders what it gets.
- **The last item is the current page, marked `aria-current="page"`, inside a labelled `nav`** (W3C
  WAI APG — Breadcrumb Pattern). Separators are hidden from assistive technology. Each crumb is at
  least 24px tall: a row of crumbs is not an inline link in a sentence.
- **A long trail never wraps.** Beyond four items, show the first, an overflow, and the last two
  (`drill-down-navigation.md`).
- **Never `link_to "Back", :back`.** `:back` follows the referrer, so on a deep link it leaves the
  app. The crumb is the Up link.

The page slots the pieces together → `references/component-levels-composites.md`.

---

## Decision: overviews, frames, and cached fragments

```ruby
# app/views/reports/index.rb — excerpt: an L2 overview; each card previews a section with a scoped count
@sections.each do |section|
  article(class: "space-y-2 rounded-lg border border-border bg-card p-4") do
    h2(class: "text-base font-semibold text-foreground") { section[:label] }
    turbo_frame_tag "#{section[:key]}_count", src: section[:count_path], loading: :lazy do
      render Components::Molecules::Skeleton.new(rows: 1)
    end
    a(href: section[:href], class: "text-sm text-primary hover:underline") { I18n.t("overview.view_all") }
  end
end
```

- **Counts are computed inside the caller's policy scope** (`drill-down-resources.md`). A lazy frame
  per card keeps a slow count from holding the page.
- **A cached fragment needs the viewer's permission context in its key.** Phlex's `cache` adds the
  boot time, class, method and line, and nothing about the viewer (Phlex — Fragment caching in Phlex
  Components). Add `permissions_version` to any key over authorized content.
- **Filter forms push a history entry; search-as-you-type replaces it** — Back undoes a filter, not a
  keystroke (Turbo Handbook — Navigate with Turbo Drive). A search form carries
  `data: { turbo_action: "replace" }`.

---

## Decision: the command palette, if the product has one

- **Optional per product, never the only way.** The spec — one shared organism, fed by the
  permission-filtered nav and the search endpoint — is in `drill-down-navigation.md`. The React
  implementation is shadcn's; a Phlex product builds the same organism on a Stimulus controller.
- **"Go to" entries render from `navigation.areas`** and their sections, so the palette offers only
  what the role can open. **Records come from the search endpoint**, and each hit shows its
  `ancestors` as a path and opens the canonical URL.
- **A visible button opens it** as well as the shortcut, and search stays in the header on every
  page regardless.

---

## Decision: testing navigation per role

```ruby
# spec/requests/navigation_spec.rb — what each role really sees, rendered
require "rails_helper"

RSpec.describe "Navigation per role", type: :request do
  let(:area_budget) { 7 } # the budget this project's design review agreed (drill-down-navigation.md)

  PermissionMatrix::ROLES.each_key do |role|
    it "should render areas only, within the budget, when the caller is #{role}" do
      sign_in create(:membership, role:).user # the app's Devise helper and membership factory

      get root_path
      follow_redirect! while response.redirect?

      nav = Nokogiri::HTML5(response.body).at_css("nav[aria-label='#{I18n.t('nav.main')}']") # nil for a one-area role

      expect(Array(nav&.css("ul ul"))).to be_empty # no list nested inside the area list
      expect(Array(nav&.css("a")).size).to be <= area_budget
    end
  end

  it "should render Approvals once, marked locked, when the organization's plan lacks approvals" do
    organization = create(:organization, entitlements: []) # the plan without the feature
    sign_in create(:membership, role: "owner", organization:).user # the owner holds orders.approve

    get root_path
    follow_redirect! while response.redirect?

    nav = Nokogiri::HTML5(response.body).at_css("nav[aria-label='#{I18n.t('nav.main')}']")
    approvals = nav.css("a[href='/approvals']")

    expect(approvals.size).to eq(1) # one entry for the area, never a padlock per item
    expect(approvals.first.text).to include(I18n.t("plans.locked"))
  end
end
```

- The component specs for `NavLink`, `Breadcrumb` and `SectionNav` assert `aria-current` values and
  the rendered links — patterns in `references/testing.md`.
- A system spec per level walks drill-in, Up and Back with the keyboard: after a level change focus
  is on the `h1`, after a filter it stays on the control, after Back it is on the row.

---

## Anti-patterns

| Symptom | Why it fails | Fix |
|---|---|---|
| Sections listed under their area in the sidebar | A tree in the global nav; the house bans it | Areas only; `SectionNav` in `AreaLayout` |
| A `FilterPanel` rendered into the layout's sidebar slot | Filters posing as navigation | Filters beside the list, in the content |
| `request.path.start_with?(href)` for the active item | `/orders` lights up on `/orders-archive` | Whole-segment match (`Navigation#state`) |
| Crumbs from `request.referer`, `:back`, or URL segments | Wrong or empty on a deep link or refresh | Controller crumbs from `ancestors` |
| A frame swap between levels without `advance` | No URL, no history entry; Back skips the level | `data-turbo-action="advance"` |
| A template with hardcoded `sidebar_links` | Every role sees every link | `areas:` from the controller |
| `helpers.policy` inside a nav component | Authorization in the view layer | `policy(:navigation)` in the controller |

---

## Sources

- Ruby on Rails Guides — Rails Routing from the Outside In — https://guides.rubyonrails.org/routing.html
- Turbo Handbook — Decompose with Turbo Frames — https://turbo.hotwired.dev/handbook/frames
- Turbo Handbook — Navigate with Turbo Drive — https://turbo.hotwired.dev/handbook/drive
- Nielsen Norman Group — Local Navigation Is a Valuable Orientation and Wayfinding Aid — https://www.nngroup.com/articles/local-navigation/
- Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile — https://www.nngroup.com/articles/breadcrumbs/
- W3C WAI APG — Breadcrumb Pattern — https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/
- Phlex — Fragment caching in Phlex Components — https://www.phlex.fun/components/caching
