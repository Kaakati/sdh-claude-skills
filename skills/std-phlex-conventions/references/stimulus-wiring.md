# Wiring Stimulus into Phlex Components

Load-bearing rules restated (this file is self-contained):

- `data-controller` goes on the **outermost element the controller owns** — nothing else.
- `data-action` uses `"event->controller#method"` and goes on the interactive element.
- `data-{controller}-target` marks elements the controller reads or writes.
- Stimulus controllers live in `app/javascript/controllers/`.
- Never use an inline `onclick`/`onchange` attribute.

Phlex renders `data:` hashes with underscores converted to dashes:
`data: { dropdown_target: "menu" }` → `data-dropdown-target="menu"`. Nested hashes are **not**
supported — flatten them.

For server-driven partial page updates (Turbo Frames and Turbo Streams), read
`references/turbo-frames-and-streams.md`.

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

An atom must accept `**attrs` and splat it onto its element for this to work — otherwise the
`data-action` is swallowed and the caller has to fork the atom. The parent supplies the action; the
atom stays generic.

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
