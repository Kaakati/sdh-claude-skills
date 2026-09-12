# Nielsen's Heuristic Evaluation Rubric

Complete scoring rubric for evaluating interfaces against Jakob Nielsen's 10 Usability Heuristics.

---

## Evaluation Process

1. **Define scope**: Which screens, flows, or components to evaluate
2. **Walk through tasks**: Complete 3-5 key user tasks — in a multi-role product, once per role, scored per role and never averaged across roles (`role-based-ux.md`)
3. **Score each heuristic**: 0-4 severity for each issue found
4. **Document findings**: File:line, severity, description, recommendation
5. **Prioritize**: Sort by severity, then by frequency of user encounter

---

## Heuristic 1: Visibility of System Status

> The design should always keep users informed about what is going on, through appropriate feedback within a reasonable amount of time.

### What to Check
- [ ] Loading states shown for async operations
- [ ] Progress indicators for multi-step processes
- [ ] Success/failure feedback for user actions (toasts, inline messages)
- [ ] Current location visible at every level: active area and section, `h1`, document title, a breadcrumb from level 3 (`@skills/ui-ux-patterns/references/drill-down-navigation.md`)
- [ ] Real-time data has visible refresh indicators
- [ ] Form submission shows processing state

### Severity Examples
| Score | Example |
|-------|---------|
| 0 | Button shows spinner during submission, success toast appears after |
| 1 | Loading state exists but disappears too quickly to notice |
| 2 | No loading state on a 2-second API call; content appears abruptly |
| 3 | Form submits with no feedback; user unsure if action worked |
| 4 | Destructive action completes silently; user doesn't know data was deleted |

---

## Heuristic 2: Match Between System and Real World

> The design should speak the users' language. Use words, phrases, and concepts familiar to the user, rather than internal jargon.

### What to Check
- [ ] Labels use user's vocabulary, not developer terms
- [ ] Icons are universally recognizable or paired with text
- [ ] Information ordered logically (chronological, alphabetical, by importance)
- [ ] Metaphors align with real-world expectations
- [ ] Date/time/currency formats match user's locale

### Severity Examples
| Score | Example |
|-------|---------|
| 0 | "Save changes" button, "Shopping cart" icon |
| 1 | "Persist" instead of "Save" in a non-technical product |
| 2 | Technical error codes shown to non-technical users |
| 3 | Navigation labels use internal project codenames |
| 4 | Critical action labeled ambiguously ("Process" could mean approve or delete) |

---

## Heuristic 3: User Control and Freedom

> Users often perform actions by mistake. They need a clearly marked "emergency exit" to leave the unwanted action without having to go through an extended process.

### What to Check
- [ ] Undo available for destructive actions
- [ ] Cancel button on all forms and dialogs
- [ ] Back returns to the view people last saw; every level, filter and overlay has a URL; Up is a real link, never an in-page Back that calls `history.back()`
- [ ] Modal/dialog has clear close mechanism (X button, Escape key, backdrop click)
- [ ] Multi-step processes allow going back to previous steps
- [ ] Confirmation before irreversible actions

### Severity Examples
| Score | Example |
|-------|---------|
| 0 | "Undo" toast after deleting an item, with 10-second window |
| 1 | Cancel button exists but is hard to find (small, low contrast) |
| 2 | No way to undo a bulk action that affected 100 items |
| 3 | Modal has no close button; only way out is to complete the form |
| 4 | Destructive action with no confirmation and no undo |

---

## Heuristic 4: Consistency and Standards

> Users should not have to wonder whether different words, situations, or actions mean the same thing. Follow platform and industry conventions.

### What to Check
- [ ] Same action → same visual treatment everywhere
- [ ] Design tokens used consistently (no hardcoded colors)
- [ ] Button styles match their importance (primary, secondary, ghost)
- [ ] Terminology consistent throughout the app
- [ ] Platform conventions followed (iOS back gesture, Android Material patterns)
- [ ] Same component used for same purpose across screens
- [ ] Navigation keeps one relative order on every page and breakpoint (WCAG 3.2.3)

### Severity Examples
| Score | Example |
|-------|---------|
| 0 | All primary actions use the same button style and placement |
| 1 | "Delete" is red in one place, gray in another |
| 2 | "Save" button is top-right on one form, bottom-left on another |
| 3 | Same feature called "Projects" in nav but "Workspaces" in settings |
| 4 | Critical action styled like a link in one place, button in another |

---

## Heuristic 5: Error Prevention

> Good error messages are important, but the best designs carefully prevent problems from occurring in the first place.

### What to Check
- [ ] Confirmation dialogs for destructive actions
- [ ] Input constraints prevent invalid data (date picker vs. free text)
- [ ] Unavailable actions follow the three-state rule: not permitted → not rendered; permitted but blocked by record state → disabled with a visible reason (never tooltip-only); available on another plan → visible and locked, only for roles that could act on it (`@skills/ui-ux-patterns/references/role-based-ux.md`). Every other state a role meets — read-only, no access vs not found, the kinds of empty, masked fields, loading — and a disabled reason that reaches keyboard and screen-reader users → `@skills/ui-ux-patterns/references/role-based-ux-states.md`
- [ ] Sensible defaults reduce required input
- [ ] Inline validation catches errors before submission
- [ ] Autocomplete/suggestions reduce typing errors

### Severity Examples
| Score | Example |
|-------|---------|
| 0 | Date picker with min/max dates prevents invalid range selection |
| 1 | Free text input for dates, but with format hint |
| 2 | No character limit on a field that truncates on save |
| 3 | Delete button with no confirmation, adjacent to Edit button |
| 4 | Admin can remove their own admin access, or demote the last Owner, with no guard (`@skills/ui-ux-patterns/references/role-management-ux.md`) |

---

## Heuristic 6: Recognition Rather Than Recall

> Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part of the interface to another.

### What to Check
- [ ] Options visible (dropdowns show all choices)
- [ ] Recently used items accessible
- [ ] Breadcrumbs from level 3 show the hierarchy, built from the API's `ancestors` — never history; a product only one or two levels deep needs none
- [ ] Related information visible in context (not requiring navigation)
- [ ] Search suggestions and autocomplete
- [ ] Preview before committing (e.g., file upload preview)

---

## Heuristic 7: Flexibility and Efficiency of Use

> Shortcuts — hidden from novice users — can speed up the interaction for the expert user.

### What to Check
- [ ] Keyboard shortcuts for common actions
- [ ] Bulk actions for list operations
- [ ] Customizable views (column order, density)
- [ ] Recently used / favorites for quick access
- [ ] A command palette (Cmd/Ctrl+K) mirrors the permission-filtered nav and search — opened by a visible button too, and never the only route
- [ ] Drag-and-drop for reordering

---

## Heuristic 8: Aesthetic and Minimalist Design

> Interfaces should not contain information that is irrelevant or rarely needed. Every extra unit of information competes with relevant information.

### What to Check
- [ ] Whitespace used effectively (not cramped)
- [ ] Only essential information shown (progressive disclosure for details)
- [ ] Visual noise minimized (borders, shadows, colors used purposefully)
- [ ] Content hierarchy clear (most important information most prominent)
- [ ] No decorative elements that don't serve a purpose
- [ ] Information density appropriate for the context
- [ ] The global nav holds only areas — no nested sections or collapsible groups in the sidebar; depth lives in pages

### Navigation Severity Examples
| Score | Example |
|-------|---------|
| 2 | A long breadcrumb trail that wraps instead of overflowing its middle; an overview page with one card |
| 3 | A nested section tree in the global sidebar; desktop navigation hidden by default; breadcrumbs built from history; an in-page Back that leaves the app from a deep link; a dead-end detail page |
| 4 | No second way to reach a page set — no search (WCAG 2.4.5) |

Legacy screens score at full severity: the drill-down standard applies to existing products now
(`@skills/ui-ux-patterns/references/drill-down-navigation.md`).

---

## Heuristic 9: Help Users Recognize, Diagnose, and Recover from Errors

> Error messages should be expressed in plain language (no error codes), precisely indicate the problem, and constructively suggest a solution.

### What to Check
- [ ] Error messages in plain language (not technical codes)
- [ ] Error clearly states what went wrong
- [ ] Error suggests how to fix the problem
- [ ] Inline errors positioned next to the relevant field
- [ ] Error state visually distinct (red border, error icon)
- [ ] Retry option for network/server errors
- [ ] Denied, not found, and empty are distinct states with distinct copy; every denial names a person or a path (`@skills/ui-ux-patterns/references/role-based-ux-states.md`)

---

## Heuristic 10: Help and Documentation

> It's best if the system can be used without documentation. However, it may be necessary to provide help and documentation.

### What to Check
- [ ] Tooltips on non-obvious UI elements
- [ ] Contextual help links near complex features
- [ ] Searchable documentation or knowledge base
- [ ] Onboarding tour for new users
- [ ] Empty states include guidance
- [ ] Error messages link to relevant help articles

---

## Aggregate Scoring

After evaluating all heuristics, calculate the overall score:

| Metric | Calculation |
|--------|-------------|
| **Total issues** | Count of all findings |
| **Critical issues** | Count of severity 4 findings |
| **Major issues** | Count of severity 3 findings |
| **Average severity** | Sum of severities / total issues |
| **Overall rating** | 5.0 - (weighted average severity) |

### Rating Scale
| Score | Rating | Action |
|-------|--------|--------|
| 4.5-5.0 | Excellent | Ship with confidence |
| 3.5-4.4 | Good | Ship, address minor issues post-launch |
| 2.5-3.4 | Acceptable | Fix major issues before launch |
| 1.5-2.4 | Poor | Significant redesign needed |
| 0-1.4 | Critical | Do not ship; fundamental usability problems |
