---
paths:
  - "web/**"
  - "next/**"
  - "frontend/**"
---

# Web Accessibility Standards (WCAG 2.1 AA)

Accessibility is a requirement, not a nice-to-have. All web frontends must meet WCAG 2.1 AA compliance.

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

## Testing

- Use `axe-core` or `jest-axe` for automated accessibility testing in Vitest
- Manual keyboard testing for all new interactive components
- Test with screen reader (VoiceOver on macOS, NVDA on Windows)
- Verify focus management on route changes and modal open/close
