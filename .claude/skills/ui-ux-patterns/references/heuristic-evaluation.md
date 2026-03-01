# Nielsen's Heuristic Evaluation Rubric

Complete scoring rubric for evaluating interfaces against Jakob Nielsen's 10 Usability Heuristics.

---

## Evaluation Process

1. **Define scope**: Which screens, flows, or components to evaluate
2. **Walk through tasks**: Complete 3-5 key user tasks
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
- [ ] Current state visible (selected item, active tab, current page)
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
- [ ] Back navigation works as expected
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
- [ ] Disabled state for unavailable actions (with tooltip explaining why)
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
| 4 | Admin can accidentally remove their own admin access with no warning |

---

## Heuristic 6: Recognition Rather Than Recall

> Minimize the user's memory load by making elements, actions, and options visible. The user should not have to remember information from one part of the interface to another.

### What to Check
- [ ] Options visible (dropdowns show all choices)
- [ ] Recently used items accessible
- [ ] Breadcrumbs show current location
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
- [ ] Command palette (Cmd+K) for power users
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
