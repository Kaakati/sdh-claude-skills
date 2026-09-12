---
name: std-accessibility
description: Accessibility standards (WCAG 2.2 AA) — semantic HTML, keyboard nav, color contrast, ARIA, focus, target size. Use when building or reviewing web UI components.
paths:
  - "**/src/**/*.tsx"
  - "**/src/**/*.jsx"
  - "**/app/**/*.tsx"
  - "**/app/**/*.jsx"
  - "**/components/**/*.tsx"
  - "**/components/**/*.jsx"
---

# Accessibility Standards (WCAG 2.2 AA)

Accessibility is a requirement, not a nice-to-have. All web and mobile frontends must meet WCAG 2.2 AA compliance.

## Semantic HTML

- Use semantic elements: `<nav>`, `<main>`, `<article>`, `<section>`, `<aside>`, `<header>`, `<footer>`
- Use heading hierarchy (`h1`-`h6`) — one `h1` per page, no skipped levels
- Use `<button>` for actions, `<a>` for navigation — never `<div onClick>`
- Use `<ul>`/`<ol>` for lists, `<table>` for tabular data

## Keyboard Navigation

- All interactive elements must be keyboard accessible (Tab, Enter, Space, Escape)
- Visible focus indicators on all focusable elements — never `outline: none` without a replacement
- Logical tab order following visual layout
- Skip-to-content link as first focusable element
- Trap focus inside modals and dialogs — release on close

## Color and Contrast

- Minimum contrast ratio: 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold)
- Never convey information by color alone — use icons, patterns, or text labels
- Test with grayscale filter to verify non-color cues exist

## Forms

- Every input must have an associated `<label>` (use `htmlFor`/`id` pairing or wrapping)
- Error messages must be programmatically associated with inputs (`aria-describedby`)
- Required fields marked with both visual indicator and `aria-required="true"`
- Group related fields with `<fieldset>` and `<legend>`

## Images and Media

- All `<img>` elements must have `alt` text — descriptive for informational, empty (`alt=""`) for decorative
- Use `next/image` (Next.js) or optimized `<img>` (Vite) with `alt` attribute
- Video content must have captions or transcripts

## ARIA

- Use ARIA only when native HTML semantics are insufficient
- `aria-label` for elements without visible text (icon buttons)
- `aria-live` regions for dynamic content updates (toast notifications, form errors)
- `aria-expanded` for collapsible sections and dropdowns
- Never use `aria-hidden="true"` on focusable elements

### Not permitted, blocked, locked

Which state an action is in is the UX rule in `@skills/ui-ux-patterns/references/role-based-ux.md`;
every other state a role meets — read-only, no access vs not found, empty, masked, loading — is
`@skills/ui-ux-patterns/references/role-based-ux-states.md`. This is how each reaches assistive tech:

- **Not permitted → not rendered.** Absent from the DOM — never shipped and then concealed with
  `hidden`, CSS, `sr-only` (a screen reader still reads it), or `aria-hidden="true"` (Tab still
  reaches a focusable child). Concealed markup still discloses what other roles can do.
- **Blocked by record state → `aria-disabled="true"` plus `aria-describedby`** pointing at a
  **visible** reason. Not native `disabled`: browsers drop it from the tab order, and the ARIA
  Authoring Practices Guide notes that screen reader users are far less likely to discover disabled
  elements that are not focusable — it keeps native `disabled` only where the control's presence is
  obvious from the controls around it. `aria-disabled` changes the announcement, not the behaviour
  (MDN: the developer must suppress the functionality) — the click handler must no-op, and for a
  submit button so must the form's submit handler, because Enter in a field still submits.
- **No tooltip on a natively disabled control.** It cannot take focus, so keyboard users never open
  it. A tooltip on an `aria-disabled` control may add detail and must meet **1.4.13 Content on Hover
  or Focus** (AA): it opens on keyboard focus as well as hover, is dismissible without moving hover
  or focus (Escape), is hoverable, and persists until dismissed. It never replaces the visible
  reason — touch has no hover.
- **Contrast: 1.4.3 exempts the inactive control, not its reason.** A disabled control's label may
  fall below 4.5:1; the reason is ordinary text and must meet it. Dim the control, never a wrapper
  that also holds the reason.
- **Locked on another plan → stays focusable and announces why.** Its name says what it is, its
  description says what unlocks it; activating it opens the upgrade or ask-an-admin path.
- **Read-only → text, or native `readonly`**, never `disabled`: a read-only field stays focusable and
  is read out. A masked value carries a text alternative ("ending in 4821"), or a screen reader reads
  the bullets.

### Navigation, location, and focus on a level change

What the navigation holds, how deep it goes and which cues each level carries is
`@skills/ui-ux-patterns/references/drill-down-navigation.md`. This is how it reaches assistive tech:

- **Each `nav` has a distinct, translated name** — "Main" for the areas, "Orders sections" for an
  area's section nav, "Breadcrumb" for the trail — and holds a list of links. Never `role="menu"` or
  `menubar` for site navigation (W3C WAI APG — Example Disclosure Navigation Menu). The one
  disclosure is the phone-width **Menu** button: a real `<button>` labelled with the word "Menu",
  carrying `aria-expanded`, controlling that list of links.
- **`aria-current="page"` goes only on the link to the current page** — in the global nav, the
  section nav, a split view's selected row, and the breadcrumb's last item. The area or section the
  page sits *inside* gets `aria-current="true"`; announcing "page" there names a different page as
  current. The visual state uses two cues (an indicator plus weight), never colour alone.
- **Breadcrumb (W3C WAI APG — Breadcrumb Pattern):** a labelled `<nav>` around an `<ol>` of links to
  the parent pages in hierarchy order; separators decorative (CSS, or `aria-hidden="true"`); the last
  item plain text with `aria-current="page"`; the narrow-screen parent link inside the same `<nav>`.
  Crumbs in a row are not inline links in a sentence, so the 2.5.8 inline exception does not apply —
  each target is at least 24×24.
- **Focus on a level change (2.4.3).** Drilling in, going Up or switching area moves focus to the new
  view's `h1` (`tabIndex={-1}`) once the title has updated; a full page load keeps the browser's own
  behaviour. A filter, sort, search, navigation-tab or section change leaves focus on the control
  that caused it. Back to a list focuses the row link that drilled in, or the list's `h1` when that
  row is gone. A split-view panel sits after the list in DOM order: opening it moves focus to its
  `h2`, and Close returns focus to the row. Where the panel covers the list as a modal, the primitive
  traps focus — never add a second trap. A sticky header or section nav never covers the focused
  heading (2.4.11; offset with `scroll-mt-*`).
- **3.2.3 Consistent Navigation (AA):** areas keep one relative order on every page and in every form
  of the nav — sidebar, Sheet, phone bar. Role trimming keeps the order; reordering per page breaks it.
- **2.4.5 Multiple Ways (AA):** every page set is reachable by search as well as by navigation;
  steps in a process are exempt. A command palette adds a way only with a visible button beside its
  shortcut.
- **2.4.8 Location (AAA — house rule, not required for AA):** "Information about the user's location
  within a set of web pages is available." Met by the breadcrumb (G65), the current item marked in
  the nav (G128) and `aria-current` (ARIA26) (W3C WAI — Understanding SC 2.4.8: Location). Adopted on
  purpose, and labelled like 2.4.13 below so nobody mistakes it for the AA requirement.

## Component Patterns

```tsx
// Accessible button with icon only
<button aria-label="Delete order" onClick={handleDelete}>
  <TrashIcon aria-hidden="true" />
</button>

// Accessible form field
<div>
  <label htmlFor="email">Email Address</label>
  <input id="email" type="email" aria-required="true" aria-describedby="email-error" />
  {error && <p id="email-error" role="alert">{error}</p>}
</div>

// Live region for dynamic updates
<div aria-live="polite" aria-atomic="true">
  {`${items.length} items in cart`}
</div>

// Blocked by record state — stays in the tab order; the visible reason is announced (reasonId from useId())
<button
  aria-disabled={blocked}
  aria-describedby={blocked ? reasonId : undefined}
  onClick={blocked ? undefined : handleCancel}
>
  Cancel order
</button>
{blocked && <p id={reasonId} className="text-muted-foreground">{reason}</p>}
```

## WCAG 2.2 New Criteria

WCAG 2.2 adds **9** success criteria beyond WCAG 2.1 and **removes 4.1.1 Parsing** (obsolete —
do not audit for it). Six of the nine bind at AA: `3.2.6` and `3.3.7` (Level A, which AA
includes) plus `2.4.11`, `2.5.7`, `2.5.8`, `3.3.8` (Level AA). The other three —
`2.4.12` Focus Not Obscured (Enhanced), `2.4.13` Focus Appearance, and `3.3.9` Accessible
Authentication (Enhanced) — are **AAA**.

**Of those three AAA additions we adopt one as a house rule: `2.4.13` Focus Appearance.** Labelled
honestly below so nobody mistakes our choice for the standard's requirement — it is stricter than
AA, we do it on purpose, and the design system already ships the ring that satisfies it. (One older
AAA criterion is a house rule too: `2.4.8` Location, under *Navigation, location, and focus* above.)

### 2.4.11 Focus Not Obscured (Minimum) (AA)
- When a component receives focus, it must not be entirely hidden by author-created content (sticky headers, floating toolbars, cookie banners)
- Ensure sticky/fixed elements don't cover focused items; use `scroll-margin-top` to offset

### 2.4.13 Focus Appearance (**AAA** — house rule, not required for AA)
- Focus indicator must be at least **2px thick** (outline or ring)
- Focus indicator must have at least **3:1 contrast** against the unfocused state
- Standard pattern: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`

### 2.5.7 Dragging Movements (AA)
- Any operation achievable by dragging must have a single-pointer alternative
- Examples: drag-to-reorder must have up/down buttons; drag-to-resize must have input fields
- Exception: dragging is essential to the functionality (e.g., drawing tool)

### 2.5.8 Target Size (Minimum) (AA)
- Interactive targets must be at least **24x24 CSS pixels**
- Mobile touch targets should be at least **44x44px** (a house rule for touch; WCAG's own 44×44 is 2.5.5 Target Size (Enhanced), AAA)
- Exceptions: inline links in text, spacing between targets provides equivalent area
- Use `min-h-11 min-w-11` (44px on the spacing scale) for mobile touch targets — never an arbitrary value

### 3.2.6 Consistent Help (A)
- Help mechanisms (chat, FAQ, contact) must appear in the same relative location across pages
- If a help button is in the footer on one page, it must be in the footer on all pages

### 3.3.7 Redundant Entry (A)
- Information previously entered by the user must be auto-populated or available for selection
- Don't ask users to re-enter data already provided in the same process
- Examples: shipping address auto-fills billing; previously entered email shown in confirmation

### 3.3.8 Accessible Authentication (Minimum) (AA)
- Authentication must not require a cognitive function test (e.g., remembering a password)
- Allow password managers to fill credentials (no blocking paste in password fields)
- CAPTCHAs must have accessible alternatives
- Biometric and WebAuthn are acceptable alternatives

## Testing

- Use `axe-core` or `jest-axe` for automated accessibility testing in Vitest
- Manual keyboard testing for all new interactive components
- Test with screen reader (VoiceOver on macOS, NVDA on Windows)
- Verify focus management on route changes and modal open/close
- A keyboard pass per drill-down level: after drilling in and after Up, focus is on the new `h1`; after a filter or tab change it stays on the control; after Back it is on the row that drilled in. On native, VoiceOver and TalkBack land on the new screen's header after a push
- Validate touch target sizes on mobile (44x44px minimum)
- Verify focus indicators are not obscured by sticky/fixed elements
- Vendored shadcn/ui primitives (under `components.json` `aliases.ui`) skip most accessibility hook checks, so their label props, ring contrast and target size are checked in review → @skills/std-shadcn-ui/references/accessibility-and-i18n.md
