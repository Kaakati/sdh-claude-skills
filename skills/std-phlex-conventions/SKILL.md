---
name: std-phlex-conventions
description: Phlex view component conventions — Atomic Design structure, class_variants, Stimulus, Turbo. Use when building Phlex (Ruby) view components.
paths:
  - "**/app/views/**/*.rb"
  - "**/app/components/**/*.rb"
---

# Phlex Component Conventions

Standards for building Phlex view components following Atomic Design methodology.

## Base Classes

- `Components::Base < Phlex::HTML` — base for all reusable components (atoms through templates)
- `Views::Base < Phlex::HTML` — base for page-level views
- Include common helpers (asset paths, route helpers, `turbo_frame_tag`) in base classes

## Atomic Design Mapping

| Level | Namespace | Directory | Description |
|-------|-----------|-----------|-------------|
| Atom | `Components::Atoms::` | `components/atoms/` | Indivisible primitives (button, input, icon) |
| Molecule | `Components::Molecules::` | `components/molecules/` | Atom compositions (search form, nav link) |
| Organism | `Components::Organisms::` | `components/organisms/` | UI sections (header, product card) |
| Template | `Components::Templates::` | `components/templates/` | Layout skeletons (dashboard layout) |
| Page | `Views::{Resource}::` | `views/{resource}/` | Data-bound pages (articles/index) |

### Decision tree

1. Indivisible HTML element with styling? → **Atom**
2. Composes only atoms into a small unit? → **Molecule**
3. Forms a distinct interface section? → **Organism**
4. Defines page layout without real data? → **Template**
5. Represents a full page with data? → **Page (View)**

## Core Patterns

Props are keyword arguments; pass unknown attributes through with `**attrs`:

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
    button(type: @type, class: VARIANTS.render(variant: @variant, size: @size), **@attrs) { @label }
  end
end
```

Content blocks yield straight into the element:

```ruby
class Components::Atoms::Card < Components::Base
  def view_template(&block)
    div(class: "rounded-lg border bg-card text-card-foreground shadow-sm p-6", &block)
  end
end
```

Composition uses `render`:

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

## Styling Rules

- Tailwind CSS utility classes exclusively — no custom CSS unless absolutely necessary
- Consume design tokens via Tailwind classes: `bg-primary`, `text-foreground`, `rounded-lg`
- Never hardcode colors, sizes, or spacing — use token-based classes
- Use `class_variants` for components with multiple visual variants
- Group related Tailwind classes logically: layout, spacing, typography, color, state

## Data Access

View components never query or mutate. Controllers and services fetch; components receive props.

## Interactivity

- Bind `data-controller` on the outermost element the controller owns
- Use `data-action` on interactive elements: `"event->controller#method"`
- Use `data-{controller}-target` on elements the controller references
- Stimulus controllers live in `app/javascript/controllers/`
- Never use inline `onclick`/`onchange` attributes
- Prefer Turbo Frames over full-page Turbo Drive for component-level updates; Turbo Streams for
  server-pushed DOM updates (append, prepend, replace, remove)

## Testing

- Unit test with `Phlex::Testing::ViewHelper`; assert rendered output, never private methods
- Cover each variant, content blocks, and the emitted Stimulus `data-*` attributes

## File Limits

- Maximum 200 lines per component file (enforced by code-quality-checker)
- Extract complex logic into private methods or helper modules
- One component per file
- File name must match the class name in snake_case (e.g., `product_card.rb` for `ProductCard`)

## Deep guides (read on demand, do not preload)

- Building an atom / molecule / organism / template / page, with level-violation checklist → `references/component-levels.md`
- `class_variants` multi-axis variants, caller class merging, `tokens` vs `class_variants`, token reference table → `references/variants-and-styling.md`
- Stimulus controller scoping and values API, Turbo Frame vs Stream decision, frame form submission → `references/stimulus-and-turbo.md`
- Component/page spec patterns, table-driven variant tests, block and `data-*` assertions, what not to test → `references/testing.md`
