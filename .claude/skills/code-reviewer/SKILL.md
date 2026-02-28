---
name: code-reviewer
description: Review code and pull requests for quality, security, test coverage, and adherence to team conventions. Use this skill whenever someone asks to review a PR, check code quality, audit a diff, evaluate a changeset, or says things like "review my code", "check this PR", "look at my changes", "is this code good", "audit this module", or "what do you think of this diff". Also trigger when someone mentions code quality concerns, technical debt assessment, or asks for feedback on implementation approach.
agent: code-reviewer
model: sonnet
---

# Code Reviewer

This skill routes to the **code-reviewer agent** for systematic review. The agent's 11-step protocol covers: context understanding, naming conventions, cyclomatic complexity, SOLID principles, error handling, test coverage, DRY violations, documentation, performance, architecture fit, and web-specific patterns.

This file adds dynamic context injection and supplementary checklists.

## Dynamic Context (auto-loaded when available)

!`git diff HEAD~1 --stat 2>/dev/null || echo "No git diff available"`

!`git log --oneline -5 2>/dev/null || echo "No git log available"`

## Supplementary: Accessibility Check (Web — Vite SPA + Next.js)

In addition to the agent's web-specific review (Step 11), verify:
- Semantic HTML elements (`<nav>`, `<main>`, `<section>`, `<article>`, `<button>`, `<a>`)
- All interactive elements are keyboard accessible (Tab, Enter, Space, Escape)
- Images use `alt` attributes. Decorative images use `alt=""`
- Color contrast meets WCAG AA (4.5:1 normal text, 3:1 large text)
- Forms have `<label>` elements associated with inputs (via `htmlFor`)
- ARIA attributes used correctly — prefer semantic HTML over ARIA
- Focus management: modals trap focus, dialogs return focus on close
- Skip navigation link for keyboard users
- Next.js: `next/image` with `alt`, `next/link` for navigation

See `@rules/accessibility.md` for the full WCAG 2.1 AA standard.

## Supplementary: Accessibility Check (React Native)

- Interactive elements have `accessibilityLabel` and `accessibilityRole` props
- Touch targets are at least 44x44 points
- Color is not the sole means of conveying information
- Screen reader navigation order is logical
- Dynamic content updates announced via `AccessibilityInfo.announceForAccessibility`

```tsx
// Accessible touchable
<TouchableOpacity
  accessibilityRole="button"
  accessibilityLabel="Delete order"
  accessibilityHint="Removes this order from your history"
  style={{ minHeight: 44, minWidth: 44 }}
  onPress={handleDelete}
>
  <TrashIcon />
</TouchableOpacity>

// Accessible form field
<View>
  <Text nativeID="emailLabel">Email Address</Text>
  <TextInput
    accessibilityLabelledBy="emailLabel"
    textContentType="emailAddress"
    autoComplete="email"
  />
  {error && <Text accessibilityRole="alert">{error}</Text>}
</View>
```

## Supplementary: Stack-Specific Checks

**Rails**: Panko serializers used (not raw models)? Service objects for business logic? Pundit `authorize` on every action? Sidekiq jobs idempotent? Redis cache TTLs set?

**React Native**: Server data in TanStack Query (not Zustand)? Proper `staleTime`? `FlatList` for lists? `useCallback` on render functions? Centrifugo subscriptions cleaned up on unmount?

**ReactJS (Vite SPA)**: Routes lazy-loaded? TanStack Query for server data? Tailwind CSS (no inline styles)? Forms use react-hook-form + zod? Bundle size checked?

**Next.js (App Router)**: Server Components by default? Server actions validate with zod? `next/image` and `next/link`? Metadata exported? `loading.tsx`/`error.tsx` boundaries? `revalidatePath`/`revalidateTag` after mutations?

**Migrations**: Reversible? Foreign keys indexed? PostGIS columns have GiST index? No data + schema changes mixed?

## Output Format

Present findings in this table format:

| Category | Finding | Severity | File:Line | Recommendation |
|---|---|---|---|---|

**Severity Levels:**
- **Must-Fix**: Security vulnerabilities, data loss, production-breaking — block merge
- **Should-Fix**: Design problems, maintainability — strongly recommend before merge
- **Suggestion**: Quality improvements — consider for this or follow-up PR
- **Nit**: Style preferences — optional, do not block merge

End each review with:
1. **Overall Assessment**: Approve / Request Changes / Needs Discussion
2. **Strengths**: What was done well (always include positive feedback)
3. **Key Issues**: Top 3 items that must be addressed
4. **Key Takeaway**: Single most important improvement for future code
