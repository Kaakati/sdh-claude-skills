# WCAG 2.2 AA Checklist

Complete checklist organized by principle. Includes all WCAG 2.1 AA criteria plus the 7 new WCAG 2.2 criteria.

---

## Principle 1: Perceivable

### 1.1 Text Alternatives
- [ ] **1.1.1 Non-text Content (A)**: All non-text content has a text alternative
  - `<img alt="descriptive text">` for informational images
  - `<img alt="">` for decorative images
  - `aria-label` for icon-only buttons
  - Complex images (charts, diagrams) have extended descriptions

### 1.2 Time-based Media
- [ ] **1.2.1 Audio-only and Video-only (A)**: Transcripts for audio, descriptions for video
- [ ] **1.2.2 Captions (A)**: Synchronized captions for all video content
- [ ] **1.2.3 Audio Description (A)**: Audio description for video content
- [ ] **1.2.5 Audio Description (AA)**: Prerecorded audio description for video

### 1.3 Adaptable
- [ ] **1.3.1 Info and Relationships (A)**: Information conveyed through presentation is also available programmatically
  - Semantic HTML elements (`<nav>`, `<main>`, `<article>`)
  - Heading hierarchy (`h1`-`h6`, no skipped levels)
  - Lists use `<ul>/<ol>/<li>`
  - Tables use `<th>`, `<caption>`, `scope` attributes
  - Form labels associated with inputs
- [ ] **1.3.2 Meaningful Sequence (A)**: DOM order matches visual reading order
- [ ] **1.3.3 Sensory Characteristics (A)**: Instructions don't rely on shape, size, visual location, or sound alone
- [ ] **1.3.4 Orientation (AA)**: Content not restricted to a single display orientation
- [ ] **1.3.5 Identify Input Purpose (AA)**: Input purpose can be programmatically determined (autocomplete attributes)

### 1.4 Distinguishable
- [ ] **1.4.1 Use of Color (A)**: Color is not the only means of conveying information
- [ ] **1.4.2 Audio Control (A)**: Audio playing automatically can be paused/stopped
- [ ] **1.4.3 Contrast (Minimum) (AA)**: 4.5:1 for normal text, 3:1 for large text (18px+ or 14px+ bold)
- [ ] **1.4.4 Resize Text (AA)**: Text resizable to 200% without loss of content/functionality
- [ ] **1.4.5 Images of Text (AA)**: Use real text, not images of text (except logos)
- [ ] **1.4.10 Reflow (AA)**: Content reflows at 320px width without horizontal scrolling
- [ ] **1.4.11 Non-text Contrast (AA)**: 3:1 for UI components and meaningful graphics
- [ ] **1.4.12 Text Spacing (AA)**: No content loss when adjusting line height, spacing, word spacing
- [ ] **1.4.13 Content on Hover or Focus (AA)**: Additional content on hover/focus is dismissible, hoverable, persistent

---

## Principle 2: Operable

### 2.1 Keyboard Accessible
- [ ] **2.1.1 Keyboard (A)**: All functionality available via keyboard
- [ ] **2.1.2 No Keyboard Trap (A)**: Keyboard focus can be moved to and from all components
- [ ] **2.1.4 Character Key Shortcuts (A)**: Single-character shortcuts can be remapped/disabled

### 2.4 Navigable
- [ ] **2.4.1 Bypass Blocks (A)**: Skip-to-content link or landmark navigation
- [ ] **2.4.2 Page Titled (A)**: Descriptive `<title>` on every page
- [ ] **2.4.3 Focus Order (A)**: Focusable components in logical order
- [ ] **2.4.4 Link Purpose (A)**: Link purpose determinable from link text (or context)
- [ ] **2.4.5 Multiple Ways (AA)**: Multiple ways to locate a page (search, sitemap, nav)
- [ ] **2.4.6 Headings and Labels (AA)**: Descriptive headings and labels
- [ ] **2.4.7 Focus Visible (AA)**: Keyboard focus indicator visible on all focusable elements
- [ ] **2.4.11 Focus Not Obscured (Minimum) (AA)** [WCAG 2.2]: Focused component not entirely hidden by author-created content (sticky headers, modals)
- [ ] **2.4.13 Focus Appearance (AAA)** [WCAG 2.2] — *not required for AA; adopted as a house rule*: Focus indicator is at least 2px thick with 3:1 contrast against unfocused state

### 2.5 Input Modalities
- [ ] **2.5.1 Pointer Gestures (A)**: Multi-point/path-based gestures have single-pointer alternatives
- [ ] **2.5.2 Pointer Cancellation (A)**: Down-event doesn't trigger action; up-event can abort
- [ ] **2.5.3 Label in Name (A)**: Accessible name includes visible label text
- [ ] **2.5.4 Motion Actuation (A)**: Motion-triggered actions have UI alternatives
- [ ] **2.5.7 Dragging Movements (AA)** [WCAG 2.2]: Drag operations achievable with single pointer without dragging
- [ ] **2.5.8 Target Size (Minimum) (AA)** [WCAG 2.2]: Interactive targets at least 24x24 CSS pixels (with exceptions for inline, spacing, user-agent, essential)

---

## Principle 3: Understandable

### 3.1 Readable
- [ ] **3.1.1 Language of Page (A)**: `<html lang="en">` attribute set
- [ ] **3.1.2 Language of Parts (AA)**: `lang` attribute on sections in different languages

### 3.2 Predictable
- [ ] **3.2.1 On Focus (A)**: Focus doesn't trigger unexpected context change
- [ ] **3.2.2 On Input (A)**: Changing input value doesn't auto-submit or navigate
- [ ] **3.2.3 Consistent Navigation (AA)**: Navigation consistent across pages
- [ ] **3.2.4 Consistent Identification (AA)**: Same functionality labeled consistently
- [ ] **3.2.6 Consistent Help (A)** [WCAG 2.2]: Help mechanisms in same relative order across pages

### 3.3 Input Assistance
- [ ] **3.3.1 Error Identification (A)**: Errors described in text with specific field identified
- [ ] **3.3.2 Labels or Instructions (A)**: Labels or instructions provided for required input
- [ ] **3.3.3 Error Suggestion (AA)**: Suggestions for fixing errors when known
- [ ] **3.3.4 Error Prevention (AA)**: Reversible, checked, or confirmable for legal/financial/data
- [ ] **3.3.7 Redundant Entry (A)** [WCAG 2.2]: Previously entered information auto-populated or selectable (no re-entry)
- [ ] **3.3.8 Accessible Authentication (Minimum) (AA)** [WCAG 2.2]: No cognitive function test for authentication; allow password managers, copy-paste

---

## Principle 4: Robust

### 4.1 Compatible
- [ ] **4.1.2 Name, Role, Value (A)**: Custom UI components have accessible names, roles, and states via ARIA
- [ ] **4.1.3 Status Messages (AA)**: Status messages programmatically announced without focus change (use `aria-live`)

---

## WCAG 2.2 New Criteria Summary

These 7 criteria are new in WCAG 2.2 (not in WCAG 2.1):

| Criterion | Level | Key Requirement |
|-----------|-------|----------------|
| 2.4.11 Focus Not Obscured | AA | Focused element visible (not hidden by sticky/fixed elements) |
| 2.4.13 Focus Appearance | **AAA** (house rule) | 2px minimum focus indicator, 3:1 contrast |
| 2.5.7 Dragging Movements | AA | Single-pointer alternative for all drag operations |
| 2.5.8 Target Size | AA | 24x24px minimum (44x44px recommended for mobile) |
| 3.2.6 Consistent Help | A | Help in same relative location across pages |
| 3.3.7 Redundant Entry | A | Don't ask users to re-enter previously provided info |
| 3.3.8 Accessible Authentication | AA | No cognitive tests (CAPTCHAs with alternatives, password managers work) |
