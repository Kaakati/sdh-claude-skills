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
```

## WCAG 2.2 New Criteria

WCAG 2.2 adds 7 success criteria beyond WCAG 2.1. All are required for AA compliance:

### 2.4.11 Focus Not Obscured (Minimum) (AA)
- When a component receives focus, it must not be entirely hidden by author-created content (sticky headers, floating toolbars, cookie banners)
- Ensure sticky/fixed elements don't cover focused items; use `scroll-margin-top` to offset

### 2.4.13 Focus Appearance (AA)
- Focus indicator must be at least **2px thick** (outline or ring)
- Focus indicator must have at least **3:1 contrast** against the unfocused state
- Standard pattern: `focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2`

### 2.5.7 Dragging Movements (AA)
- Any operation achievable by dragging must have a single-pointer alternative
- Examples: drag-to-reorder must have up/down buttons; drag-to-resize must have input fields
- Exception: dragging is essential to the functionality (e.g., drawing tool)

### 2.5.8 Target Size (Minimum) (AA)
- Interactive targets must be at least **24x24 CSS pixels**
- Mobile touch targets should be at least **44x44px** (WCAG recommendation)
- Exceptions: inline links in text, spacing between targets provides equivalent area
- Use `min-h-[44px] min-w-[44px]` for mobile touch targets

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
- Validate touch target sizes on mobile (44x44px minimum)
- Verify focus indicators are not obscured by sticky/fixed elements
