# Styling Phlex Components: Variants, Tokens, and Class Merging

Load-bearing rules restated (this file is self-contained):

- Tailwind utility classes exclusively. No custom CSS unless there is no utility for it.
- Consume design tokens through Tailwind class names (`bg-primary`, `text-foreground`,
  `border-input`, `rounded-lg`). Never hardcode a hex, `px`, or `rem` value.
- Any component with more than one visual variant uses `class_variants`.
- Group classes logically: layout, spacing, typography, color, state.

---

## Decision: does this component need `class_variants`?

| Situation | Use |
|---|---|
| One fixed appearance | Plain string in `class:` |
| One axis, 2-3 fixed options, no compounds | Frozen `Hash` + `fetch` |
| 2+ axes (variant × size), defaults, or compound rules | `class_variants` |

Bad — variant branching with string interpolation and conditionals:

```ruby
class Components::Atoms::Alert < Components::Base
  def initialize(message:, variant: :info)
    @message = message
    @variant = variant
  end

  def view_template
    classes = "rounded-md p-4 text-sm "
    classes += "bg-blue-50 text-blue-900 " if @variant == :info
    classes += "bg-red-50 text-red-900 " if @variant == :error       # hardcoded palette, not tokens
    classes += "bg-yellow-50 text-yellow-900 " if @variant == :warning
    div(class: classes) { @message }
  end
end
```

Good — declarative, token-based, defaulted:

```ruby
class Components::Atoms::Alert < Components::Base
  VARIANTS = class_variants(
    base: "rounded-md border p-4 text-sm",
    variants: {
      variant: {
        info: "border-border bg-muted text-foreground",
        success: "border-success/30 bg-success/10 text-success-foreground",
        warning: "border-warning/30 bg-warning/10 text-warning-foreground",
        error: "border-destructive/30 bg-destructive/10 text-destructive-foreground"
      }
    },
    defaults: { variant: :info }
  )

  def initialize(message:, variant: :info, **attrs)
    @message = message
    @variant = variant
    @attrs = attrs
  end

  def view_template
    div(class: VARIANTS.render(variant: @variant), role: :alert, **@attrs) { @message }
  end
end
```

---

## Decision: I have two style axes (variant AND size)

Bad — a nested case that explodes combinatorially:

```ruby
def button_classes
  case [@variant, @size]
  when [:primary, :sm] then "bg-primary text-primary-foreground h-8 px-3 text-sm"
  when [:primary, :md] then "bg-primary text-primary-foreground h-10 px-4"
  when [:secondary, :sm] then "bg-secondary text-secondary-foreground h-8 px-3 text-sm"
  # ...six more, each restating the color
  end
end
```

Good — axes declared independently; `class_variants` composes them:

```ruby
class Components::Atoms::Button < Components::Base
  VARIANTS = class_variants(
    base: "inline-flex items-center justify-center gap-2 rounded-md font-medium " \
          "transition-colors disabled:pointer-events-none disabled:opacity-50 " \
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    variants: {
      variant: {
        primary: "bg-primary text-primary-foreground hover:bg-primary/90",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        ghost: "hover:bg-accent hover:text-accent-foreground"
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base"
      },
      full_width: { true: "w-full", false: "" }
    },
    defaults: { variant: :primary, size: :md, full_width: false }
  )

  def initialize(label:, variant: :primary, size: :md, full_width: false, type: :button, **attrs)
    @label = label
    @variant = variant
    @size = size
    @full_width = full_width
    @type = type
    @attrs = attrs
  end

  def view_template
    button(
      type: @type,
      class: VARIANTS.render(variant: @variant, size: @size, full_width: @full_width),
      **@attrs
    ) { @label }
  end
end
```

---

## Decision: a caller needs to add classes to my component

This is the single most common source of broken styling. Naive concatenation produces
`px-4 px-8` and Tailwind resolves by stylesheet order, not by argument order — the caller's
override silently loses.

Bad — string concat, override does not win:

```ruby
def view_template
  button(class: "#{VARIANTS.render(variant: @variant)} #{@attrs[:class]}") { @label }
end

# render Components::Atoms::Button.new(label: "Go", class: "px-8")
# => class="... px-4 ... px-8"  -> whichever Tailwind emits last wins. Unpredictable.
```

Good — let `class_variants` do the tailwind-merge-aware merge:

```ruby
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, size: :md, class: nil, **attrs)
    @label = label
    @variant = variant
    @size = size
    @extra_class = binding.local_variable_get(:class)
    @attrs = attrs
  end

  def view_template
    button(
      type: :button,
      class: VARIANTS.render(variant: @variant, size: @size, class: @extra_class),
      **@attrs
    ) { @label }
  end
end
```

`class_variants`' `render(class:)` argument runs the merge, so `px-8` correctly replaces `px-4`.

If a component genuinely should not be restyled from outside (a brand lockup, a legal footer),
say so explicitly rather than silently dropping the argument:

```ruby
def initialize(**attrs)
  raise ArgumentError, "BrandLockup does not accept :class" if attrs.key?(:class)
  @attrs = attrs
end
```

---

## Decision: I want to use `tokens` instead of `class_variants`

`tokens` (built into Phlex) is fine for **inline conditional** classes inside a template. It does
not merge conflicting Tailwind utilities and has no defaults, so it is not a `class_variants`
replacement for a component's public variant API.

Good use of `tokens` — state-driven classes local to one element:

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
      aria_current: (@active ? "page" : nil),
      class: tokens(
        "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
        @active => "bg-accent text-accent-foreground",
        !@active => "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )
    ) { @label }
  end
end
```

Bad use of `tokens` — reimplementing a variant API with no defaults and no merge safety:

```ruby
class: tokens(
  "rounded-md",
  (@variant == :primary) => "bg-primary text-primary-foreground",
  (@variant == :secondary) => "bg-secondary text-secondary-foreground",
  (@size == :sm) => "h-8 px-3",
  (@size == :md) => "h-10 px-4"
)
# nil variant renders an unstyled button; caller `class:` cannot override anything.
```

---

## Decision: which token do I reach for?

Bad — raw palette values leak brand decisions into every component and break dark mode:

```ruby
div(class: "bg-white text-gray-900 border-gray-200 dark:bg-gray-900 dark:text-gray-50 p-[13px]") do
  span(class: "text-[#6B7280]") { "Draft" }
  hr(class: "border-[1px] border-solid border-[#E5E7EB] my-[17px]")
end
```

Good — semantic tokens carry light/dark automatically; spacing comes off the scale:

```ruby
div(class: "bg-card text-card-foreground border border-border rounded-lg p-4") do
  span(class: "text-muted-foreground text-sm") { "Draft" }
  hr(class: "border-border my-4")
end
```

Reference table:

| Need | Token class | Never |
|---|---|---|
| Page background | `bg-background` | `bg-white`, `bg-[#fff]` |
| Card surface | `bg-card text-card-foreground` | `bg-white text-gray-900` |
| Body text | `text-foreground` | `text-gray-900` |
| Secondary text | `text-muted-foreground` | `text-gray-500` |
| Border | `border-border` / `border-input` | `border-gray-200` |
| Primary action | `bg-primary text-primary-foreground` | `bg-blue-600 text-white` |
| Danger | `bg-destructive text-destructive-foreground` | `bg-red-600` |
| Focus ring | `ring-ring` | `ring-blue-500` |
| Spacing | `p-4`, `gap-2`, `my-6` | `p-[13px]`, `my-[17px]` |
| Radius | `rounded-md`, `rounded-lg` | `rounded-[6px]` |

---

## Decision: how do I order the classes in a string?

Group in this order so diffs stay readable and duplicates are visible: **layout → spacing →
typography → color → state**.

Bad — random order, a duplicate hiding in plain sight:

```ruby
class: "text-sm hover:bg-accent flex p-4 text-foreground rounded-md items-center p-2 gap-2"
```

Good:

```ruby
class: "flex items-center gap-2 " \          # layout
       "rounded-md p-4 " \                   # spacing/shape
       "text-sm font-medium " \              # typography
       "bg-card text-foreground " \          # color
       "transition-colors hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring" # state
```

---

## Decision: I really need custom CSS

Exhaust utilities first. If you must, add a component layer class in the app stylesheet — never
inline `style:` with literal values.

Bad:

```ruby
div(style: "clip-path: polygon(0 0, 100% 0, 100% 85%, 0 100%); background: #4F46E5;") { yield }
```

Good:

```css
/* app/assets/stylesheets/application.css */
@layer components {
  .clip-diagonal { clip-path: polygon(0 0, 100% 0, 100% 85%, 0 100%); }
}
```

```ruby
div(class: "clip-diagonal bg-primary") { yield }
```
