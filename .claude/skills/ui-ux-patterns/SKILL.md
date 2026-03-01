---
name: ui-ux-patterns
description: |
  UI/UX pattern library with screen archetypes, Nielsen's heuristics evaluation,
  visual hierarchy principles, and platform-specific adaptations.
  Triggers on "UI patterns", "UX patterns", "screen patterns", "heuristic evaluation",
  "visual hierarchy", "interaction design", "UX review", or "UI best practices".
model: sonnet
---

# UI/UX Pattern Master

Reference-based protocol for evaluating and implementing UI/UX patterns across web and mobile platforms.

## When to Apply

Use this skill when:
- Designing a new screen or feature flow
- Reviewing an existing UI for usability issues
- Choosing between interaction patterns for a feature
- Evaluating visual hierarchy and information architecture
- Adapting a pattern across platforms (web SPA, SSR, mobile)

## 8 Core Screen Patterns

Reference `references/screen-patterns.md` for detailed specifications.

### Pattern Index

| # | Pattern | When to Use | Key Components |
|---|---------|------------|----------------|
| 1 | **Onboarding** | First-time user experience | Progress steps, value proposition, skip option |
| 2 | **Dashboard** | Overview, metrics, quick actions | Cards, charts, KPIs, activity feed |
| 3 | **List/Detail** | Browse + inspect collections | Filterable list, detail panel/page, pagination |
| 4 | **Forms** | Data input, configuration | Sections, inline validation, progressive disclosure |
| 5 | **Search** | Finding items in large datasets | Search bar, filters, results, empty state |
| 6 | **Settings** | User preferences, configuration | Categories, toggles, save confirmation |
| 7 | **Profile** | User identity, account management | Avatar, info sections, edit mode, activity |
| 8 | **Empty States** | No data, first use, errors | Illustration, message, primary CTA |

## Nielsen's 10 Heuristics

Reference `references/heuristic-evaluation.md` for the complete scoring rubric.

### Quick Reference

| # | Heuristic | Check For |
|---|-----------|-----------|
| 1 | Visibility of System Status | Loading indicators, progress bars, state feedback |
| 2 | Match Real World | Natural language, familiar metaphors, logical order |
| 3 | User Control & Freedom | Undo, cancel, clear exits, back navigation |
| 4 | Consistency & Standards | Same patterns for same actions, platform conventions |
| 5 | Error Prevention | Confirmation, constraints, defaults, disabled states |
| 6 | Recognition > Recall | Visible options, contextual help, recent items |
| 7 | Flexibility & Efficiency | Shortcuts, bulk actions, customization |
| 8 | Aesthetic & Minimalist | Whitespace, information density, visual noise |
| 9 | Error Recovery | Helpful messages, suggested fixes, retry options |
| 10 | Help & Documentation | Tooltips, inline help, searchable docs |

### Scoring

| Score | Label | Meaning |
|-------|-------|---------|
| 0 | No issue | Heuristic fully satisfied |
| 1 | Cosmetic | Fix if time permits |
| 2 | Minor | Low priority fix |
| 3 | Major | High priority, fix before release |
| 4 | Catastrophic | Must fix immediately, blocks usability |

## Visual Hierarchy Checklist

When reviewing any screen, verify:

1. **F-pattern or Z-pattern**: Content follows natural eye movement (F for text-heavy, Z for landing pages)
2. **Size hierarchy**: Most important elements are largest (headings > subheadings > body)
3. **Color weight**: Primary CTA has the strongest color; secondary actions are muted
4. **Whitespace**: Generous spacing between sections; breathing room around key elements
5. **Grouping**: Related items grouped by proximity, borders, or shared background
6. **Alignment**: All elements snap to a grid; no orphaned alignments
7. **Contrast**: Key content has the highest contrast ratio against its background
8. **Focal point**: Each screen has exactly one primary focal point (the thing the user should do first)

## Interaction Principles

### Feedback Timing
| Action | Expected Feedback | Maximum Delay |
|--------|------------------|---------------|
| Button click | Visual state change | Immediate (< 100ms) |
| Form submission | Loading indicator | 100ms |
| Page navigation | Progress bar or skeleton | 200ms |
| Data operation | Success/error toast | Complete + 300ms display |

### State Management Patterns
| State | Visual Treatment | Example |
|-------|-----------------|---------|
| Default | Standard appearance | Idle button |
| Hover | Subtle highlight, cursor change | `bg-primary/90`, pointer |
| Active/Pressed | Slight scale down or darken | `scale-95`, `bg-primary/80` |
| Focus | Ring indicator | `ring-2 ring-ring` |
| Disabled | Reduced opacity, no cursor | `opacity-50 cursor-not-allowed` |
| Loading | Spinner or skeleton | `animate-pulse` or spinner icon |
| Error | Red border/text, error icon | `border-error text-error` |
| Success | Green indicator, checkmark | `border-success text-success` |

## Platform Adaptations

### Web (Vite SPA / Next.js)
- Hover states on all interactive elements (desktop has cursor)
- Keyboard navigation with visible focus indicators
- Lazy-loaded routes for navigation performance
- React Router (Vite) or App Router (Next.js) for SPA-like UX
- `Suspense` boundaries with `loading.tsx` (Next.js) for streaming

### Mobile (React Native)
- Touch targets minimum 44x44px
- Haptic feedback on significant actions (iOS)
- Bottom sheet instead of dropdown menus
- Pull-to-refresh on list screens
- Gesture navigation (swipe back, swipe to dismiss)
- Platform-specific patterns (iOS back gesture, Android material ripple)

### Cross-Platform Shared
- Same information architecture and user flows
- Same data model and API contracts
- Consistent empty states and error messages
- Unified design tokens (colors, typography, spacing)

## Trend-Aware Context (2025-2026)

Current design trends to consider in pattern selection:

| Trend | Application | Use When |
|-------|------------|----------|
| Bento grid layouts | Dashboards, feature showcases | Diverse content types, visual interest |
| Glassmorphism | Cards, modals on hero backgrounds | Premium feel, layered depth |
| Micro-interactions | Button feedback, list animations | Polish, delight, state communication |
| Variable fonts | Headings, display text | Performance + typographic range |
| AI-assisted UI | Search, forms, content generation | Natural language inputs, smart defaults |
| Dark mode first | All new components | User preference (60%+ prefer dark) |

## Full References

- `references/screen-patterns.md` — Detailed specifications for all 8 screen patterns
- `references/heuristic-evaluation.md` — Complete Nielsen's heuristic scoring rubric
