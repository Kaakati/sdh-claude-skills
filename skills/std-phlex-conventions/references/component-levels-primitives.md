# Building Phlex Primitives: Atoms and Molecules

Load-bearing rules restated (this file is self-contained):

- Reusable components inherit from `Components::Base < Phlex::HTML`. Page-level views inherit from
  `Views::Base < Phlex::HTML`.
- One component per file, file name is the class name in snake_case, max 200 lines.
- Props are keyword arguments. Never positional. Never a hash blob.
- Tailwind utilities only, consuming design tokens (`bg-primary`, `text-foreground`). No hardcoded
  hex, px, or rem values.
- View components never query or mutate. Controllers and services fetch; components receive props.

Namespace/directory map:

| Level | Namespace | Directory |
|-------|-----------|-----------|
| Atom | `Components::Atoms::` | `app/components/atoms/` |
| Molecule | `Components::Molecules::` | `app/components/molecules/` |
| Organism | `Components::Organisms::` | `app/components/organisms/` |
| Template | `Components::Templates::` | `app/components/templates/` |
| Page | `Views::{Resource}::` | `app/views/{resource}/` |

This file covers atoms and molecules. For organisms, templates, and pages, read
`references/component-levels-composites.md`.

---

## Decision: I'm building an atom

An atom is an indivisible HTML element with styling. It renders **one** semantic element (plus
optional wrapping for layout). It renders **no other component**.

### Rule: an atom must not know about the app

Bad — the atom reaches for a model, a route helper, and a global:

```ruby
# app/components/atoms/avatar.rb
class Components::Atoms::Avatar < Components::Base
  def initialize(user:)
    @user = user
  end

  def view_template
    a(href: user_path(@user)) do
      img(src: @user.avatar.attached? ? url_for(@user.avatar) : "/fallback.png",
          class: "h-10 w-10 rounded-full",
          alt: @user.full_name)
    end
  end
end
```

Good — the atom takes primitives; the caller (a molecule/organism/page) resolves the model:

```ruby
# app/components/atoms/avatar.rb
class Components::Atoms::Avatar < Components::Base
  SIZES = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-14 w-14" }.freeze

  def initialize(src:, alt:, size: :md, **attrs)
    @src = src
    @alt = alt
    @size = size
    @attrs = attrs
  end

  def view_template
    img(
      src: @src,
      alt: @alt,
      loading: :lazy,
      class: "#{SIZES.fetch(@size)} rounded-full object-cover bg-muted",
      **@attrs
    )
  end
end
```

The caller composes the link and the fallback:

```ruby
# app/components/molecules/user_chip.rb
class Components::Molecules::UserChip < Components::Base
  def initialize(name:, avatar_url:, profile_path:)
    @name = name
    @avatar_url = avatar_url
    @profile_path = profile_path
  end

  def view_template
    a(href: @profile_path, class: "inline-flex items-center gap-2 hover:underline") do
      render Components::Atoms::Avatar.new(src: @avatar_url, alt: @name, size: :sm)
      span(class: "text-sm font-medium text-foreground") { @name }
    end
  end
end
```

### Rule: pass through unknown attributes with `**attrs`

An atom that swallows extra attributes cannot be given `data-action`, `aria-*`, or an `id` by its
caller, which forces callers to fork the component.

Bad:

```ruby
def initialize(label:, variant: :primary)
  @label = label
  @variant = variant
end

def view_template
  button(type: :button, class: button_classes) { @label }
end
```

Good:

```ruby
def initialize(label:, variant: :primary, type: :button, **attrs)
  @label = label
  @variant = variant
  @type = type
  @attrs = attrs
end

def view_template
  button(type: @type, class: button_classes, **@attrs) { @label }
end
```

---

## Decision: I'm building a molecule

A molecule composes **only atoms** (and raw HTML) into one small unit with a single job. It holds no
business logic and does no data access.

Bad — the "molecule" queries the database and does branching business logic:

```ruby
class Components::Molecules::SearchForm < Components::Base
  def view_template
    form(action: "/search", class: "flex gap-2") do
      render Components::Atoms::Input.new(name: "q", placeholder: "Search...")
      select(name: "category") do
        Category.order(:name).each { |c| option(value: c.id) { c.name } } # DB call in a view component
      end
      render Components::Atoms::Button.new(label: "Search")
    end
  end
end
```

Good — data arrives as a prop; the molecule only arranges atoms:

```ruby
class Components::Molecules::SearchForm < Components::Base
  # categories: Array of [label, value] pairs
  def initialize(action:, categories: [], query: nil)
    @action = action
    @categories = categories
    @query = query
  end

  def view_template
    form(action: @action, method: :get, role: :search, class: "flex gap-2") do
      render Components::Atoms::Input.new(
        name: "q", value: @query, placeholder: "Search...", aria_label: "Search"
      )
      render Components::Atoms::Select.new(name: "category", options: @categories) if @categories.any?
      render Components::Atoms::Button.new(label: "Search", variant: :primary, type: :submit)
    end
  end
end
```

---

## Violation checklist: primitives

| Symptom | Level violation | Fix |
|---|---|---|
| Atom renders another component | Atom is really a molecule | Move to `Molecules::` |
| Atom swallows extra attributes | Callers must fork it to add `data-*`/`aria-*`/`id` | Accept and splat `**attrs` |
| Atom takes a model, calls a route helper | Atom knows about the app | Take primitives; let the caller resolve |
| Molecule renders an organism | Molecule is really an organism | Move to `Organisms::` |
| Molecule calls `Model.where/find/order` | Data access in the view layer | Move to controller/service, pass as prop |
