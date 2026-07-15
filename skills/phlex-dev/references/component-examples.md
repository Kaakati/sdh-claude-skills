# Phlex Component Examples

Complete, working Phlex component examples at each Atomic Design level.

---

## Atoms

### Components::Atoms::Button

```ruby
# frozen_string_literal: true

# backend/app/components/atoms/button.rb
class Components::Atoms::Button < Components::Base
  VARIANTS = class_variants(
    base: [
      "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md",
      "font-medium transition-colors focus-visible:outline-none focus-visible:ring-2",
      "focus-visible:ring-ring focus-visible:ring-offset-2",
      "disabled:pointer-events-none disabled:opacity-50"
    ].join(" "),
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground shadow hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        destructive: "bg-error text-error-foreground shadow-sm hover:bg-error/90",
        outline: "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline"
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-9 px-4 py-2 text-sm",
        lg: "h-10 px-6 text-base",
        icon: "h-9 w-9 p-0"
      }
    },
    defaults: { variant: :primary, size: :md }
  )

  def initialize(label: nil, variant: :primary, size: :md, type: :button, disabled: false, **attrs)
    @label = label
    @variant = variant
    @size = size
    @type = type
    @disabled = disabled
    @attrs = attrs
  end

  def view_template(&block)
    button(
      type: @type,
      class: VARIANTS.render(variant: @variant, size: @size),
      disabled: @disabled,
      **@attrs
    ) do
      if block
        yield
      else
        plain @label
      end
    end
  end
end
```

### Components::Atoms::Input

```ruby
# frozen_string_literal: true

# backend/app/components/atoms/input.rb
class Components::Atoms::Input < Components::Base
  VARIANTS = class_variants(
    base: [
      "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1",
      "text-sm shadow-sm transition-colors file:border-0 file:bg-transparent",
      "file:text-sm file:font-medium placeholder:text-muted-foreground",
      "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
      "disabled:cursor-not-allowed disabled:opacity-50"
    ].join(" "),
    variants: {
      state: {
        default: "border-input",
        error: "border-error focus-visible:ring-error"
      }
    },
    defaults: { state: :default }
  )

  def initialize(name:, type: :text, placeholder: nil, value: nil, required: false, error: nil, **attrs)
    @name = name
    @type = type
    @placeholder = placeholder
    @value = value
    @required = required
    @error = error
    @attrs = attrs
  end

  def view_template
    state = @error ? :error : :default
    input(
      type: @type,
      name: @name,
      placeholder: @placeholder,
      value: @value,
      required: @required,
      class: VARIANTS.render(state: state),
      aria: @error ? { invalid: "true", describedby: "#{@name}-error" } : {},
      **@attrs
    )
  end
end
```

### Components::Atoms::Label

```ruby
# frozen_string_literal: true

# backend/app/components/atoms/label.rb
class Components::Atoms::Label < Components::Base
  def initialize(text:, for_input: nil, required: false)
    @text = text
    @for_input = for_input
    @required = required
  end

  def view_template
    label(
      for: @for_input,
      class: "text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    ) do
      plain @text
      span(class: "text-error ml-1") { "*" } if @required
    end
  end
end
```

### Components::Atoms::Badge

```ruby
# frozen_string_literal: true

# backend/app/components/atoms/badge.rb
class Components::Atoms::Badge < Components::Base
  VARIANTS = class_variants(
    base: "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground shadow",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive: "border-transparent bg-error text-error-foreground shadow",
        outline: "border-border text-foreground"
      }
    },
    defaults: { variant: :default }
  )

  def initialize(label:, variant: :default)
    @label = label
    @variant = variant
  end

  def view_template
    span(class: VARIANTS.render(variant: @variant)) { @label }
  end
end
```

### Components::Atoms::Heading

```ruby
# frozen_string_literal: true

# backend/app/components/atoms/heading.rb
class Components::Atoms::Heading < Components::Base
  LEVEL_CLASSES = {
    1 => "scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl",
    2 => "scroll-m-20 text-3xl font-semibold tracking-tight",
    3 => "scroll-m-20 text-2xl font-semibold tracking-tight",
    4 => "scroll-m-20 text-xl font-semibold tracking-tight",
    5 => "text-lg font-medium",
    6 => "text-base font-medium"
  }.freeze

  def initialize(text:, level: 1, **attrs)
    @text = text
    @level = level.clamp(1, 6)
    @attrs = attrs
  end

  def view_template
    send(:"h#{@level}", class: LEVEL_CLASSES[@level], **@attrs) { @text }
  end
end
```

---

## Molecules

### Components::Molecules::SearchForm

```ruby
# frozen_string_literal: true

# backend/app/components/molecules/search_form.rb
class Components::Molecules::SearchForm < Components::Base
  def initialize(action: "/search", query: nil, placeholder: "Search...")
    @action = action
    @query = query
    @placeholder = placeholder
  end

  def view_template
    form(
      action: @action,
      method: "get",
      class: "flex items-center gap-2",
      data: {
        controller: "search",
        action: "input->search#filter"
      }
    ) do
      render Components::Atoms::Input.new(
        name: "q",
        type: :search,
        placeholder: @placeholder,
        value: @query,
        data: { search_target: "input", action: "input->search#filter" }
      )
      render Components::Atoms::Button.new(
        label: "Search",
        variant: :primary,
        size: :md,
        type: :submit
      )
    end
  end
end
```

### Components::Molecules::FormField

```ruby
# frozen_string_literal: true

# backend/app/components/molecules/form_field.rb
class Components::Molecules::FormField < Components::Base
  def initialize(name:, label:, type: :text, placeholder: nil, value: nil, required: false, error: nil, **attrs)
    @name = name
    @label = label
    @type = type
    @placeholder = placeholder
    @value = value
    @required = required
    @error = error
    @attrs = attrs
  end

  def view_template
    div(class: "space-y-2") do
      render Components::Atoms::Label.new(
        text: @label,
        for_input: @name,
        required: @required
      )
      render Components::Atoms::Input.new(
        name: @name,
        type: @type,
        placeholder: @placeholder,
        value: @value,
        required: @required,
        error: @error,
        id: @name,
        **@attrs
      )
      render_error if @error
    end
  end

  private

  def render_error
    p(
      id: "#{@name}-error",
      class: "text-sm text-error",
      role: "alert"
    ) { @error }
  end
end
```

### Components::Molecules::NavLink

```ruby
# frozen_string_literal: true

# backend/app/components/molecules/nav_link.rb
class Components::Molecules::NavLink < Components::Base
  def initialize(label:, href:, icon: nil, active: false)
    @label = label
    @href = href
    @icon = icon
    @active = active
  end

  def view_template
    a(
      href: @href,
      class: link_classes,
      aria: { current: @active ? "page" : nil }
    ) do
      render_icon if @icon
      span { @label }
    end
  end

  private

  def link_classes
    base = "flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors"
    if @active
      "#{base} bg-primary/10 text-primary"
    else
      "#{base} text-muted-foreground hover:text-foreground hover:bg-muted"
    end
  end

  def render_icon
    # Placeholder: swap for your icon system (Heroicons, Lucide, SVG sprites, etc.)
    span(class: "w-4 h-4") { @icon }
  end
end
```

---

## Organisms

### Components::Organisms::Header

```ruby
# frozen_string_literal: true

# backend/app/components/organisms/header.rb
class Components::Organisms::Header < Components::Base
  def initialize(current_user: nil, nav_links: default_nav_links)
    @current_user = current_user
    @nav_links = nav_links
  end

  def view_template
    header(class: "sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60") do
      div(class: "container mx-auto flex h-14 items-center justify-between px-4") do
        render_logo
        render_desktop_nav
        render_mobile_menu_button
      end
      render_mobile_nav
    end
  end

  private

  def render_logo
    a(href: "/", class: "flex items-center gap-2 font-bold text-lg") do
      span { "AppName" }
    end
  end

  def render_desktop_nav
    nav(class: "hidden md:flex items-center gap-1") do
      @nav_links.each do |link|
        render Components::Molecules::NavLink.new(**link)
      end
      render Components::Molecules::SearchForm.new(placeholder: "Search...")
    end
  end

  def render_mobile_menu_button
    div(class: "md:hidden") do
      render Components::Atoms::Button.new(
        variant: :ghost,
        size: :icon,
        data: { action: "mobile-menu#toggle" },
        aria: { label: "Toggle navigation menu" }
      ) do
        # Hamburger icon placeholder
        span(class: "sr-only") { "Menu" }
        svg_hamburger_icon
      end
    end
  end

  def render_mobile_nav
    nav(
      class: "md:hidden hidden border-t",
      data: {
        controller: "mobile-menu",
        mobile_menu_target: "menu"
      }
    ) do
      div(class: "flex flex-col gap-1 p-4") do
        @nav_links.each do |link|
          render Components::Molecules::NavLink.new(**link)
        end
      end
    end
  end

  def svg_hamburger_icon
    svg(
      xmlns: "http://www.w3.org/2000/svg",
      fill: "none",
      viewbox: "0 0 24 24",
      stroke_width: "1.5",
      stroke: "currentColor",
      class: "w-5 h-5"
    ) do |s|
      s.path(
        stroke_linecap: "round",
        stroke_linejoin: "round",
        d: "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
      )
    end
  end

  def default_nav_links
    [
      { label: "Dashboard", href: "/dashboard", active: false },
      { label: "Projects", href: "/projects", active: false },
      { label: "Team", href: "/team", active: false }
    ]
  end
end
```

### Components::Organisms::ProductCard

```ruby
# frozen_string_literal: true

# backend/app/components/organisms/product_card.rb
class Components::Organisms::ProductCard < Components::Base
  def initialize(product:)
    @product = product
  end

  def view_template
    div(class: "group rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden transition-shadow hover:shadow-md") do
      render_image
      div(class: "p-4 space-y-3") do
        render_header
        render_description
        render_footer
      end
    end
  end

  private

  def render_image
    div(class: "aspect-video overflow-hidden bg-muted") do
      img(
        src: @product.image_url,
        alt: @product.name,
        class: "h-full w-full object-cover transition-transform group-hover:scale-105",
        loading: "lazy"
      )
    end
  end

  def render_header
    div(class: "flex items-start justify-between gap-2") do
      render Components::Atoms::Heading.new(text: @product.name, level: 3)
      render Components::Atoms::Badge.new(
        label: @product.category,
        variant: :secondary
      )
    end
  end

  def render_description
    p(class: "text-sm text-muted-foreground line-clamp-2") do
      @product.description
    end
  end

  def render_footer
    div(class: "flex items-center justify-between pt-2") do
      span(class: "text-lg font-bold text-foreground") { format_price }
      render Components::Atoms::Button.new(
        label: "Add to Cart",
        variant: :primary,
        size: :sm,
        data: {
          action: "cart#add",
          cart_product_id_param: @product.id
        }
      )
    end
  end

  def format_price
    "$#{"%.2f" % @product.price}"
  end
end
```

---

## Templates

### Components::Templates::DashboardLayout

```ruby
# frozen_string_literal: true

# backend/app/components/templates/dashboard_layout.rb
class Components::Templates::DashboardLayout < Components::Base
  def initialize(title: "Dashboard", current_user: nil)
    @title = title
    @current_user = current_user
  end

  def view_template(&block)
    div(class: "min-h-screen flex flex-col bg-background") do
      render Components::Organisms::Header.new(
        current_user: @current_user,
        nav_links: nav_links
      )
      div(class: "flex flex-1") do
        render_sidebar
        main(class: "flex-1 overflow-y-auto") do
          div(class: "container mx-auto p-6 space-y-6") do
            render_page_header
            yield if block_given?
          end
        end
      end
    end
  end

  private

  def render_sidebar
    aside(
      class: "hidden lg:flex w-64 flex-col border-r bg-card",
      data: { controller: "sidebar" }
    ) do
      nav(class: "flex-1 p-4 space-y-1") do
        sidebar_links.each do |link|
          render Components::Molecules::NavLink.new(**link)
        end
      end
    end
  end

  def render_page_header
    div(class: "flex items-center justify-between") do
      render Components::Atoms::Heading.new(text: @title, level: 1)
    end
  end

  def nav_links
    [
      { label: "Dashboard", href: "/dashboard", active: true },
      { label: "Analytics", href: "/analytics", active: false }
    ]
  end

  def sidebar_links
    [
      { label: "Overview", href: "/dashboard", icon: "home", active: true },
      { label: "Projects", href: "/projects", icon: "folder", active: false },
      { label: "Tasks", href: "/tasks", icon: "check-square", active: false },
      { label: "Team", href: "/team", icon: "users", active: false },
      { label: "Settings", href: "/settings", icon: "cog", active: false }
    ]
  end
end
```

---

## Pages (Views)

### Views::Articles::Index

```ruby
# frozen_string_literal: true

# backend/app/views/articles/index.rb
class Views::Articles::Index < Views::Base
  def initialize(articles:, pagy: nil)
    @articles = articles
    @pagy = pagy
  end

  def view_template
    render Components::Templates::DashboardLayout.new(title: "Articles") do
      render_toolbar
      render_articles_grid
      render_pagination if @pagy
    end
  end

  private

  def render_toolbar
    div(class: "flex items-center justify-between") do
      render Components::Molecules::SearchForm.new(
        action: helpers.articles_path,
        placeholder: "Search articles..."
      )
      render Components::Atoms::Button.new(
        label: "New Article",
        variant: :primary,
        data: { turbo_action: "advance" }
      )
    end
  end

  def render_articles_grid
    if @articles.any?
      div(class: "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-6") do
        @articles.each do |article|
          render_article_card(article)
        end
      end
    else
      render_empty_state
    end
  end

  def render_article_card(article)
    a(href: helpers.article_path(article), class: "block group") do
      div(class: "rounded-lg border bg-card p-4 space-y-2 transition-shadow hover:shadow-md") do
        div(class: "flex items-center justify-between") do
          render Components::Atoms::Badge.new(
            label: article.status.humanize,
            variant: article.published? ? :default : :secondary
          )
          span(class: "text-xs text-muted-foreground") do
            article.created_at.strftime("%b %d, %Y")
          end
        end
        render Components::Atoms::Heading.new(text: article.title, level: 3)
        p(class: "text-sm text-muted-foreground line-clamp-2") { article.excerpt }
        div(class: "flex items-center gap-2 text-xs text-muted-foreground") do
          span { "By #{article.author.name}" }
          span { "#{article.reading_time} min read" }
        end
      end
    end
  end

  def render_empty_state
    div(class: "text-center py-12") do
      render Components::Atoms::Heading.new(text: "No articles found", level: 3)
      p(class: "text-muted-foreground mt-2") { "Create your first article to get started." }
      div(class: "mt-4") do
        render Components::Atoms::Button.new(
          label: "Create Article",
          variant: :primary
        )
      end
    end
  end

  def render_pagination
    nav(class: "flex items-center justify-center gap-2 mt-8", aria: { label: "Pagination" }) do
      if @pagy.prev
        a(href: helpers.articles_path(page: @pagy.prev), class: "pagination-link") do
          render Components::Atoms::Button.new(label: "Previous", variant: :outline, size: :sm)
        end
      end
      span(class: "text-sm text-muted-foreground") do
        "Page #{@pagy.page} of #{@pagy.last}"
      end
      if @pagy.next
        a(href: helpers.articles_path(page: @pagy.next), class: "pagination-link") do
          render Components::Atoms::Button.new(label: "Next", variant: :outline, size: :sm)
        end
      end
    end
  end
end
```

### Views::Articles::Show

```ruby
# frozen_string_literal: true

# backend/app/views/articles/show.rb
class Views::Articles::Show < Views::Base
  def initialize(article:, comments: [])
    @article = article
    @comments = comments
  end

  def view_template
    render Components::Templates::DashboardLayout.new(title: @article.title) do
      render_article_header
      render_article_body
      render_article_footer
      render_comments_section
    end
  end

  private

  def render_article_header
    div(class: "space-y-4") do
      div(class: "flex items-center gap-2") do
        a(href: helpers.articles_path, class: "text-sm text-muted-foreground hover:text-foreground") do
          "Back to Articles"
        end
      end
      render Components::Atoms::Heading.new(text: @article.title, level: 1)
      div(class: "flex items-center gap-4 text-sm text-muted-foreground") do
        span { "By #{@article.author.name}" }
        span { @article.published_at&.strftime("%B %d, %Y") || "Draft" }
        span { "#{@article.reading_time} min read" }
        render Components::Atoms::Badge.new(
          label: @article.status.humanize,
          variant: @article.published? ? :default : :secondary
        )
      end
    end
  end

  def render_article_body
    div(class: "prose prose-neutral dark:prose-invert max-w-none mt-8") do
      # Rendered markdown/HTML content from the article body
      unsafe_raw @article.rendered_body
    end
  end

  def render_article_footer
    div(class: "flex items-center justify-between border-t pt-6 mt-8") do
      div(class: "flex items-center gap-2") do
        @article.tags.each do |tag|
          render Components::Atoms::Badge.new(label: tag.name, variant: :outline)
        end
      end
      div(class: "flex items-center gap-2") do
        render Components::Atoms::Button.new(
          label: "Share",
          variant: :outline,
          size: :sm
        )
        render Components::Atoms::Button.new(
          label: "Edit",
          variant: :ghost,
          size: :sm
        )
      end
    end
  end

  def render_comments_section
    div(class: "mt-12 space-y-6", id: "comments") do
      render Components::Atoms::Heading.new(
        text: "Comments (#{@comments.size})",
        level: 2
      )
      turbo_frame_tag("comments") do
        div(class: "space-y-4") do
          @comments.each do |comment|
            render_comment(comment)
          end
        end
      end
    end
  end

  def render_comment(comment)
    div(class: "flex gap-3 p-4 rounded-lg border") do
      div(class: "flex-1 space-y-1") do
        div(class: "flex items-center gap-2") do
          span(class: "text-sm font-medium") { comment.author.name }
          span(class: "text-xs text-muted-foreground") do
            comment.created_at.strftime("%b %d, %Y at %I:%M %p")
          end
        end
        p(class: "text-sm text-foreground") { comment.body }
      end
    end
  end

  def turbo_frame_tag(id, &block)
    tag("turbo-frame", id: id, &block)
  end
end
```
