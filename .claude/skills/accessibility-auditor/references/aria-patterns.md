# ARIA Widget Patterns

Common ARIA patterns with keyboard interaction specifications. Based on WAI-ARIA Authoring Practices.

---

## General Principles

1. **Prefer native HTML over ARIA**: Use `<button>` over `<div role="button">`
2. **First rule of ARIA**: Don't use ARIA if native HTML provides the semantics
3. **Required attributes**: Every ARIA role has required states/properties
4. **Label everything**: Every interactive element needs an accessible name

---

## Button

### Native (preferred)
```html
<button type="button">Click me</button>
```

### Icon-only Button
```html
<button type="button" aria-label="Delete item">
  <svg aria-hidden="true">...</svg>
</button>
```

### Toggle Button
```html
<button type="button" aria-pressed="false" onClick={toggle}>
  Bold
</button>
```

### Keyboard
| Key | Action |
|-----|--------|
| Enter | Activate |
| Space | Activate |

---

## Dialog (Modal)

```html
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Delete</h2>
  <p>Are you sure you want to delete this item?</p>
  <button>Cancel</button>
  <button>Delete</button>
</div>
```

### Requirements
- `role="dialog"` and `aria-modal="true"`
- `aria-labelledby` pointing to the dialog title
- Focus trapped inside the dialog
- Focus returns to trigger element on close
- Background content is `aria-hidden="true"` or `inert`

### Keyboard
| Key | Action |
|-----|--------|
| Tab | Move focus within dialog |
| Shift+Tab | Move focus backward within dialog |
| Escape | Close dialog |

---

## Tabs

```html
<div role="tablist" aria-label="Account settings">
  <button role="tab" aria-selected="true" aria-controls="panel-1" id="tab-1">
    Profile
  </button>
  <button role="tab" aria-selected="false" aria-controls="panel-2" id="tab-2" tabindex="-1">
    Security
  </button>
</div>
<div role="tabpanel" id="panel-1" aria-labelledby="tab-1">
  Profile content
</div>
<div role="tabpanel" id="panel-2" aria-labelledby="tab-2" hidden>
  Security content
</div>
```

### Requirements
- Container: `role="tablist"` with `aria-label`
- Each tab: `role="tab"`, `aria-selected`, `aria-controls`
- Each panel: `role="tabpanel"`, `aria-labelledby`
- Only active tab in tab order (`tabindex="0"`), others `tabindex="-1"`

### Keyboard
| Key | Action |
|-----|--------|
| Arrow Left/Right | Move to previous/next tab |
| Home | Move to first tab |
| End | Move to last tab |
| Enter/Space | Activate focused tab (if manual activation) |

---

## Dropdown Menu

```html
<div>
  <button aria-haspopup="true" aria-expanded="false" aria-controls="menu-1">
    Actions
  </button>
  <ul role="menu" id="menu-1" hidden>
    <li role="menuitem">Edit</li>
    <li role="menuitem">Duplicate</li>
    <li role="separator"></li>
    <li role="menuitem">Delete</li>
  </ul>
</div>
```

### Requirements
- Trigger: `aria-haspopup="true"`, `aria-expanded`, `aria-controls`
- Container: `role="menu"`
- Items: `role="menuitem"`, `role="menuitemcheckbox"`, or `role="menuitemradio"`
- Focus management: first item focused on open

### Keyboard
| Key | Action |
|-----|--------|
| Enter/Space | Open menu (on trigger); activate item |
| Arrow Down | Open menu (on trigger); next item |
| Arrow Up | Previous item |
| Escape | Close menu, return focus to trigger |
| Home | First item |
| End | Last item |
| Character | Jump to item starting with character |

---

## Combobox (Autocomplete)

```html
<div>
  <label for="search">Search</label>
  <input
    id="search"
    role="combobox"
    aria-expanded="false"
    aria-autocomplete="list"
    aria-controls="listbox-1"
    aria-activedescendant=""
  />
  <ul role="listbox" id="listbox-1" hidden>
    <li role="option" id="opt-1">Option 1</li>
    <li role="option" id="opt-2">Option 2</li>
  </ul>
</div>
```

### Keyboard
| Key | Action |
|-----|--------|
| Arrow Down | Open listbox; highlight next option |
| Arrow Up | Highlight previous option |
| Enter | Select highlighted option |
| Escape | Close listbox |
| Type | Filter options |

---

## Tooltip

```html
<button aria-describedby="tooltip-1">
  <svg aria-hidden="true">...</svg>
  <span id="tooltip-1" role="tooltip" hidden>
    Save document
  </span>
</button>
```

### Requirements
- `role="tooltip"` on the tooltip element
- `aria-describedby` on the trigger pointing to the tooltip
- Show on focus and hover
- Dismiss on Escape
- Persist while mouse is over tooltip

### Keyboard
| Key | Action |
|-----|--------|
| Focus | Show tooltip |
| Escape | Dismiss tooltip |
| Blur | Hide tooltip |

---

## Alert / Toast

```html
<div role="alert" aria-live="assertive">
  Error: Please enter a valid email address.
</div>

<!-- For non-urgent notifications -->
<div aria-live="polite" aria-atomic="true">
  3 items added to cart.
</div>
```

### Requirements
- `role="alert"` for urgent messages (assertive)
- `aria-live="polite"` for non-urgent status updates
- `aria-atomic="true"` when entire region should be re-announced
- Don't use `role="alert"` for success toasts (too aggressive)

---

## Accordion

```html
<div>
  <h3>
    <button aria-expanded="true" aria-controls="section-1">
      Section 1
    </button>
  </h3>
  <div id="section-1" role="region" aria-labelledby="accordion-1">
    Section 1 content
  </div>

  <h3>
    <button aria-expanded="false" aria-controls="section-2">
      Section 2
    </button>
  </h3>
  <div id="section-2" role="region" aria-labelledby="accordion-2" hidden>
    Section 2 content
  </div>
</div>
```

### Keyboard
| Key | Action |
|-----|--------|
| Enter/Space | Toggle section |
| Arrow Down | Next accordion header |
| Arrow Up | Previous accordion header |
| Home | First header |
| End | Last header |

---

## Switch / Toggle

```html
<button role="switch" aria-checked="false" onClick={toggle}>
  <span>Enable notifications</span>
</button>
```

### Keyboard
| Key | Action |
|-----|--------|
| Space | Toggle on/off |
| Enter | Toggle on/off |

---

## Live Region Best Practices

| Politeness | Use Case | Attribute |
|-----------|----------|-----------|
| `assertive` | Error messages, critical alerts | `aria-live="assertive"` or `role="alert"` |
| `polite` | Status updates, notifications, cart counts | `aria-live="polite"` |
| `off` | Content not needing announcement | `aria-live="off"` (default) |

**Rules:**
- Inject content into the live region; don't add the live region attribute to new elements
- Keep announcements concise (under 100 characters)
- Don't announce every keystroke (debounce search results announcements)
- Use `aria-atomic="true"` when the entire message should be re-read
