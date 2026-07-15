---
name: accessibility-auditor
description: |
  WCAG 2.2 AA accessibility audit with 4-principle framework, automated checks,
  color contrast analysis, keyboard navigation testing, and ARIA pattern validation.
  Triggers on "accessibility audit", "WCAG audit", "a11y audit", "accessibility check",
  "screen reader test", "keyboard accessibility", or "accessibility compliance".
model: sonnet
---

# Accessibility Auditor

Systematic WCAG 2.2 AA audit protocol organized by the four accessibility principles: Perceivable, Operable, Understandable, and Robust (POUR).

## When to Apply

Use this skill when:
- Auditing a page, screen, or component for WCAG 2.2 AA compliance
- Reviewing a PR for accessibility regressions
- Building new interactive components that need accessibility
- Preparing for an accessibility compliance review
- Fixing reported accessibility issues

## Audit Protocol

### Principle 1: Perceivable

Information and UI components must be presentable in ways users can perceive.

| Criterion | What to Check | Automated? |
|-----------|---------------|-----------|
| 1.1.1 Non-text Content | All `<img>` have `alt`; decorative images have `alt=""` | Yes |
| 1.3.1 Info and Relationships | Semantic HTML, heading hierarchy, form labels | Partial |
| 1.3.2 Meaningful Sequence | DOM order matches visual order | Manual |
| 1.3.3 Sensory Characteristics | Instructions don't rely solely on shape, size, or position | Manual |
| 1.4.1 Use of Color | Information not conveyed by color alone | Manual |
| 1.4.3 Contrast (Minimum) | 4.5:1 normal text, 3:1 large text | Yes |
| 1.4.4 Resize Text | Text resizable to 200% without loss | Manual |
| 1.4.5 Images of Text | No text rendered as images (except logos) | Yes |
| 1.4.11 Non-text Contrast | 3:1 for UI components and graphical objects | Partial |

### Principle 2: Operable

UI components and navigation must be operable.

| Criterion | What to Check | Automated? |
|-----------|---------------|-----------|
| 2.1.1 Keyboard | All functionality available via keyboard | Manual |
| 2.1.2 No Keyboard Trap | Focus can be moved away from any component | Manual |
| 2.4.1 Bypass Blocks | Skip-to-content link present | Yes |
| 2.4.2 Page Titled | Descriptive `<title>` on every page | Yes |
| 2.4.3 Focus Order | Logical tab order | Manual |
| 2.4.4 Link Purpose | Link text describes destination (no "click here") | Partial |
| 2.4.6 Headings and Labels | Descriptive headings, no skipped levels | Yes |
| 2.4.7 Focus Visible | Visible focus indicator on all focusable elements | Partial |
| **2.4.11 Focus Not Obscured** (2.2) | Focused element not fully hidden by other content | Manual |
| **2.4.13 Focus Appearance** (2.2, **AAA** — house rule, not required for AA) | Focus indicator has 3:1 contrast, 2px minimum | Partial |
| **2.5.7 Dragging Movements** (2.2) | Drag operations have single-pointer alternative | Manual |
| **2.5.8 Target Size** (2.2) | Interactive targets minimum 24x24px (44x44px mobile) | Yes |

### Principle 3: Understandable

Information and UI operation must be understandable.

| Criterion | What to Check | Automated? |
|-----------|---------------|-----------|
| 3.1.1 Language of Page | `lang` attribute on `<html>` element | Yes |
| 3.1.2 Language of Parts | `lang` attribute on foreign language content | Manual |
| 3.2.1 On Focus | No context change on focus alone | Manual |
| 3.2.2 On Input | No unexpected context change on input | Manual |
| 3.3.1 Error Identification | Errors described in text, not just color | Manual |
| 3.3.2 Labels or Instructions | Form inputs have labels; complex inputs have instructions | Yes |
| **3.2.6 Consistent Help** (2.2) | Help mechanisms in same relative location across pages | Manual |
| **3.3.7 Redundant Entry** (2.2) | Previously entered info auto-populated or selectable | Manual |
| **3.3.8 Accessible Authentication** (2.2) | No cognitive function test for auth (allow paste, managers) | Manual |

### Principle 4: Robust

Content must be robust enough for assistive technologies.

| Criterion | What to Check | Automated? |
|-----------|---------------|-----------|
| 4.1.2 Name, Role, Value | Custom components have proper ARIA roles/states | Partial |
| 4.1.3 Status Messages | Dynamic content uses `aria-live` regions | Partial |

## Automated Checks

Run these checks programmatically:

### Code-Level (Grep/Read)
```
Check                          Pattern to Search
─────────────────────────────  ──────────────────────────────
Missing alt text               <img without alt=
Div as button                  <div.*onClick (without role="button")
Missing form labels            <input without associated <label>
Empty links                    <a>...</a> with no text content
Missing lang attribute         <html without lang=
Heading hierarchy              h1, h2, h3 order (no skipped levels)
Focus outline removed          outline: none without replacement
Hardcoded color as info        Color-only status indicators
```

### Token contrast is computable — do not send it to a browser

**Audit the tokens at their source, not only the rendered page.** A design token pair is two static
HSL values in a file; the WCAG ratio between them is arithmetic, so it belongs in a test, not in a
manual DevTools pass. Nobody opens DevTools 36 times, which is exactly how a contrast failure
survives: not because it is subtle, but because checking it by hand does not scale and so does not
happen.

Every `--x` / `--x-foreground` pair in `globals.css` (or wherever the tokens live) is a case:

```ts
// The formula and a ready-made contrastRatio() live in
// @skills/std-design-system/references/defining-tokens.md — import, do not re-derive.
import { contrastRatio } from './check-contrast';
import { light, dark } from './tokens';

// Iterate the PAIRS — do not hand-write two cases and call it covered.
const PAIRS = ['primary', 'success', 'error', 'warning', 'info'] as const;

describe.each([['light', light], ['dark', dark]])('%s token contrast', (_name, theme) => {
  it.each(PAIRS)('%s-foreground on %s clears 4.5:1', (token) => {
    expect(contrastRatio(theme[`${token}Foreground`], theme[token])).toBeGreaterThanOrEqual(4.5);
  });
  it('muted-foreground on muted clears 4.5:1', () => {
    expect(contrastRatio(theme.mutedForeground, theme.muted)).toBeGreaterThanOrEqual(4.5);
  });
});
```

Two traps this catches that a page-level audit does not:

- **A `-foreground` token is verified against its SOLID surface.** `bg-success/10
  text-success-foreground` is a 10% tint under near-white text — around 1:1, invisible — and no
  static check of the *token pair* sees it, because the pair itself is fine. On a tint, use
  `text-foreground`.
- **Presets and themes are copies.** If the project ships more than one theme, every theme is a
  case. A fix applied to the spec does not reach the preset beside it.

### Tool-Based
| Tool | Purpose | Integration |
|------|---------|-------------|
| `axe-core` / `jest-axe` | Automated WCAG checks in Vitest | `npm run test` |
| Token contrast test (above) | Every token pair, every theme | `npm run test` — **not manual** |
| Chrome DevTools | Accessibility tree, live contrast spot-checks | Manual |
| VoiceOver (macOS) | Screen reader testing | Manual |
| NVDA (Windows) | Screen reader testing | Manual |
| Lighthouse | Accessibility score | CI pipeline |

## Output Format

Present findings as:

```
[SEVERITY] | File:Line | WCAG Criterion | Finding | Remediation
───────────┼──────────┼────────────────┼─────────┼────────────
CRITICAL   | path:42  | 2.4.7          | No focus indicator on submit button | Add focus-visible:ring-2 focus-visible:ring-ring
MAJOR      | path:15  | 1.1.1          | <img> missing alt text | Add descriptive alt or alt="" for decorative
MINOR      | path:88  | 2.4.4          | Link text is "click here" | Use descriptive text: "View order details"
```

**Severity Levels:**
- **CRITICAL**: Blocks user access entirely (no keyboard access, missing essential alt text)
- **MAJOR**: Significantly impairs experience (low contrast, missing labels)
- **MINOR**: Degrades experience but workaround exists (non-descriptive link text)
- **INFO**: Best practice recommendation (could improve but compliant)

## Summary Metrics

End each audit with:

| Metric | Value |
|--------|-------|
| Total checks performed | X |
| CRITICAL issues | X |
| MAJOR issues | X |
| MINOR issues | X |
| Estimated compliance | X% (passing checks / total checks) |
| WCAG 2.2 AA conformance | Yes / No (any CRITICAL = No) |

## Full References

- `references/wcag-22-checklist.md` — Complete WCAG 2.2 AA checklist by principle
- `references/aria-patterns.md` — ARIA widget patterns with keyboard specifications

### Owned elsewhere

- **`std-accessibility`** is the always-on rule set — it **auto-loads on `.tsx`/`.jsx`** under
  `src/`, `app/`, and `components/`. Note the edge it does *not* cover: its `paths:` are component
  files, so it does **not** load on `globals.css` or a token file. Contrast decisions get made
  where the tokens are defined, and that is `std-design-system`'s territory (it auto-loads on
  `**/globals.css`, `**/styles/**`, `**/tailwind.config.*`). Auditing a colour system means opening
  both.
- **`@skills/std-design-system/references/defining-tokens.md`** — the `contrastRatio()`
  implementation, the Vitest wiring, and the rule for *which* side to fix: darken the **foreground**
  for a brand token (the surface is the brand decision), darken the **surface** for a semantic
  status token (which green is not the convention; "green means success" is).
- **`@skills/theming/references/design-tokens.md`** — the canonical token values and their measured
  ratios. **`@skills/theming/references/theme-presets.md`** — three presets meant to be copied
  wholesale, which is why each is audited as its own theme.
- `accessibility-checker.py` warns on `.tsx`/`.jsx`/`.css`/`.scss` (semantic HTML, alt text, label
  association, focus indicators, ARIA misuse). It does **not** compute contrast — that is the test
  above, because the ratio needs the token values, not the markup.
