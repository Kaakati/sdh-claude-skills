---
globs: backend/app/views/**/*.rb, backend/app/components/**/*.rb
---

# Phlex Component Conventions

Standards for building Phlex view components following Atomic Design methodology.

## Component Structure

### Base Classes
- `Components::Base < Phlex::HTML` -- base for all reusable components (atoms through templates)
- `Views::Base < Phlex::HTML` -- base for page-level views
- Include common helpers (asset paths, route helpers) in base classes

### Atomic Design Mapping
| Level | Namespace | Directory | Description |
|-------|-----------|-----------|-------------|
| Atom | `Components::Atoms::` | `components/atoms/` | Indivisible primitives (button, input, icon) |
| Molecule | `Components::Molecules::` | `components/molecules/` | Atom compositions (search form, nav link) |
| Organism | `Components::Organisms::` | `components/organisms/` | UI sections (header, product card) |
| Template | `Components::Templates::` | `components/templates/` | Layout skeletons (dashboard layout) |
| Page | `Views::{Resource}::` | `views/{resource}/` | Data-bound pages (articles/index) |

### Decision Tree
1. Is it an indivisible HTML element with styling? --> **Atom**
2. Does it compose only atoms into a small unit? --> **Molecule**
3. Does it form a distinct interface section? --> **Organism**
4. Does it define page layout without real data? --> **Template**
5. Does it represent a full page with data? --> **Page (View)**

## Component Patterns

### Props via Keyword Arguments
```ruby
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, size: :md, type: :button, **attrs)
    @label = label
    @variant = variant
    @size = size
    @type = type
    @attrs = attrs
  end

  def view_template
    button(type: @type, class: button_classes, **@attrs) { @label }
  end

  private

  def button_classes
    tokens(
      base: "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2",
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80"
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-lg"
      }
    )
  end
end
```

### Content Blocks (yield)
```ruby
class Components::Atoms::Card < Components::Base
  def view_template(&block)
    div(class: "rounded-lg border bg-card text-card-foreground shadow-sm p-6", &block)
  end
end
```

### Composition (render)
```ruby
class Components::Molecules::SearchForm < Components::Base
  def view_template
    form(class: "flex gap-2") do
      render Components::Atoms::Input.new(placeholder: "Search...", name: "q")
      render Components::Atoms::Button.new(label: "Search", variant: :primary)
    end
  end
end
```

### Variants with class_variants
```ruby
class Components::Atoms::Badge < Components::Base
  VARIANTS = class_variants(
    base: "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        destructive: "bg-destructive text-destructive-foreground",
        outline: "border border-input bg-background"
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

## Styling Rules

- Use Tailwind CSS utility classes exclusively -- no custom CSS unless absolutely necessary
- Consume design tokens via Tailwind classes: `bg-primary`, `text-foreground`, `rounded-lg`
- Never hardcode colors, sizes, or spacing: use token-based classes
- Use `class_variants` for components with multiple visual variants
- Group related Tailwind classes logically: layout, spacing, typography, color, state

## Stimulus Integration
```ruby
class Components::Organisms::Dropdown < Components::Base
  def view_template
    div(data: { controller: "dropdown" }) do
      render Components::Atoms::Button.new(
        label: "Menu",
        data: { action: "dropdown#toggle" }
      )
      div(data: { dropdown_target: "menu" }, class: "hidden") do
        yield
      end
    end
  end
end
```

- Bind `data-controller` on the outermost container element
- Use `data-action` on interactive elements: `"event->controller#method"`
- Use `data-{controller}-target` on elements the controller needs to reference
- Keep Stimulus controllers in `backend/app/javascript/controllers/`

## Turbo Integration
- Use `turbo_frame_tag` for partial page updates within a component
- Use `data: { turbo_action: "advance" }` for URL updates on navigation
- Prefer Turbo Frames over full-page Turbo Drive for component-level updates
- Use Turbo Streams for real-time server-pushed DOM updates (append, prepend, replace, remove)

## Testing
- Use `Phlex::Testing::ViewHelper` for unit testing components
- Test render output with `render` and assert against HTML content
- Test variants by instantiating with different keyword arguments
- Test content blocks by passing blocks to `render`
- Test Stimulus data attributes are present in rendered HTML

## File Limits
- Maximum 200 lines per component file (enforced by code-quality-checker)
- Extract complex logic into private methods or helper modules
- One component per file
- File name must match the class name in snake_case (e.g., `product_card.rb` for `ProductCard`)
