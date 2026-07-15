# Building Phlex Composites: Organisms, Templates, and Pages

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

This file covers organisms, templates, and pages. For atoms and molecules, read
`references/component-levels-primitives.md`.

---

## Decision: I'm building an organism

An organism is a distinct interface section (header, product card, comment thread). It may compose
atoms, molecules, and other organisms. It may accept domain objects — but only reads them for
display.

### Rule: an organism reads a model, it never mutates or queries

Bad — N+1 queries and a write from a view:

```ruby
class Components::Organisms::ProductCard < Components::Base
  def initialize(product:)
    @product = product
  end

  def view_template
    ProductView.create!(product: @product) # side effect from a render
    div do
      h3 { @product.name }
      p { "#{@product.reviews.count} reviews" }        # query per card
      p { @product.category.name }                     # N+1 per card
    end
  end
end
```

Good — the controller preloads and records the view; the organism renders:

```ruby
# app/components/organisms/product_card.rb
class Components::Organisms::ProductCard < Components::Base
  def initialize(product:, path:)
    @product = product
    @path = path
  end

  def view_template
    article(class: "group rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden") do
      a(href: @path, class: "block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring") do
        img(src: @product.thumbnail_url, alt: @product.name, loading: :lazy,
            class: "aspect-square w-full object-cover transition-transform group-hover:scale-105")
      end
      div(class: "p-4 space-y-2") do
        header(class: "flex items-start justify-between gap-2") do
          h3(class: "text-base font-semibold text-foreground") { @product.name }
          render Components::Atoms::Badge.new(label: @product.category_name)
        end
        p(class: "text-sm text-muted-foreground") { @product.summary }
        footer(class: "flex items-center justify-between pt-2") do
          span(class: "text-lg font-bold text-foreground") { @product.formatted_price }
          render Components::Atoms::Button.new(label: "Add to cart", size: :sm,
                                               data: { action: "cart#add", cart_id_param: @product.id })
        end
      end
    end
  end
end
```

```ruby
# app/controllers/products_controller.rb
def index
  @products = Product.includes(:category).with_review_counts.page(params[:page])
end
```

### Rule: extract private methods before the file hits 200 lines

Bad — one 90-line `view_template`:

```ruby
def view_template
  header(class: "...") do
    # 30 lines of nav
    # 25 lines of user menu
    # 30 lines of mobile drawer
  end
end
```

Good — `view_template` reads like a table of contents:

```ruby
class Components::Organisms::SiteHeader < Components::Base
  def initialize(nav_items:, current_user_name: nil)
    @nav_items = nav_items
    @current_user_name = current_user_name
  end

  def view_template
    header(class: "sticky top-0 z-40 border-b bg-background/95 backdrop-blur") do
      div(class: "container flex h-16 items-center justify-between") do
        brand
        primary_nav
        user_menu
      end
    end
  end

  private

  def brand
    a(href: "/", class: "font-bold text-lg text-foreground") { "Acme" }
  end

  def primary_nav
    nav(class: "hidden md:flex gap-6", aria_label: "Main") do
      @nav_items.each do |item|
        a(href: item[:path], class: "text-sm text-muted-foreground hover:text-foreground") { item[:label] }
      end
    end
  end

  def user_menu
    return render Components::Atoms::Button.new(label: "Sign in", variant: :secondary) if @current_user_name.nil?

    render Components::Molecules::UserChip.new(
      name: @current_user_name, avatar_url: "/avatars/me.png", profile_path: "/profile"
    )
  end
end
```

---

## Decision: I'm building a template (layout skeleton)

A template defines page structure and slot positions. It takes **blocks, not data**.

Bad — the "template" bakes in real content and thus can only ever render one page:

```ruby
class Components::Templates::DashboardLayout < Components::Base
  def view_template
    div(class: "grid grid-cols-[240px_1fr]") do
      aside { render Components::Organisms::Sidebar.new }
      main { render Views::Dashboard::Index.new(stats: Stat.all) } # data + a specific page
    end
  end
end
```

Good — named slots via blocks, zero data:

```ruby
class Components::Templates::DashboardLayout < Components::Base
  def initialize(title:)
    @title = title
  end

  def view_template(&block)
    div(class: "min-h-screen grid grid-cols-1 md:grid-cols-[240px_1fr] bg-background") do
      aside(class: "hidden md:block border-r p-4") { @sidebar_block&.call }
      div(class: "flex flex-col") do
        header(class: "border-b px-6 py-4") do
          h1(class: "text-xl font-semibold text-foreground") { @title }
        end
        main(class: "flex-1 p-6") { @main_block&.call }
      end
    end
  end

  def sidebar(&block) = @sidebar_block = block
  def main_content(&block) = @main_block = block

  def before_template
    vanish { yield_content_slots }
    super
  end
end
```

Simpler and preferred when you only need one slot — take a single block:

```ruby
class Components::Templates::CenteredLayout < Components::Base
  def view_template(&block)
    div(class: "min-h-screen flex items-center justify-center bg-background p-4") do
      div(class: "w-full max-w-md space-y-6", &block)
    end
  end
end
```

---

## Decision: I'm building a page (view)

A page lives in `Views::{Resource}::`, takes already-fetched data from the controller, and composes
templates + organisms. It performs no queries.

Bad — the page fetches its own data:

```ruby
class Views::Articles::Index < Views::Base
  def view_template
    Article.published.recent.each { |a| render Components::Organisms::ArticleCard.new(article: a) }
  end
end
```

Good — controller fetches, page renders:

```ruby
# app/controllers/articles_controller.rb
class ArticlesController < ApplicationController
  def index
    articles = Article.published.includes(:author).recent.page(params[:page])
    render Views::Articles::Index.new(articles: articles)
  end
end
```

```ruby
# app/views/articles/index.rb
class Views::Articles::Index < Views::Base
  def initialize(articles:)
    @articles = articles
  end

  def view_template
    render Components::Templates::CenteredLayout.new do
      h1(class: "text-2xl font-bold text-foreground mb-6") { "Articles" }

      if @articles.empty?
        render Components::Molecules::EmptyState.new(
          title: "No articles yet", description: "Published articles will appear here."
        )
      else
        div(class: "grid gap-4 sm:grid-cols-2 lg:grid-cols-3") do
          @articles.each do |article|
            render Components::Organisms::ArticleCard.new(
              article: article, path: article_path(article)
            )
          end
        end
      end
    end
  end
end
```

---

## Violation checklist: composites

| Symptom | Level violation | Fix |
|---|---|---|
| Organism calls `Model.where/find/create` | Data access or a write in the view layer | Move to controller/service, pass as prop |
| Organism reads an association per item | N+1 from a render | Preload in the controller (`includes`) |
| Template receives model data | Template is really a page | Move to `Views::{Resource}::` |
| Template renders a specific page/organism directly | Template is not reusable | Take blocks as slots instead |
| Page queries in `view_template` | Data access in the view layer | Controller fetches, passes as a prop |
| File > 200 lines | Multiple responsibilities | Extract private methods, then extract child components |
