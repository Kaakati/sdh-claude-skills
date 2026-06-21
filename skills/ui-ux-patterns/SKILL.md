---
name: ui-ux-patterns
description: |
  UI/UX pattern library with screen archetypes, Nielsen's heuristics evaluation,
  visual hierarchy principles, storytelling/narrative UX, and platform-specific adaptations.
  Triggers on "UI patterns", "UX patterns", "screen patterns", "heuristic evaluation",
  "visual hierarchy", "interaction design", "UX review", "UI best practices",
  "storytelling UI", "narrative design", "user journey arc", "StoryBrand",
  "emotional beats", or "scrollytelling".
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
- Shaping a flow as a narrative — onboarding, landing pages, feature tours, checkout (see **Storytelling UI** below)

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

## Storytelling UI

Structure flows as a **narrative** — beginning, middle, end — rather than a flat set of
screens. People engage with and retain a story far better than a feature list, so guide the
user along a deliberate arc. Reference `references/storytelling-ui.md` for the full framework
(StoryBrand SB7 mapping, per-pattern roles, emotional-beats catalogue, pacing techniques,
motion/continuity, microcopy voice, and the scored checklist).

### The five dimensions

| Dimension | Apply by |
|-----------|----------|
| **Narrative arc** | Give each flow a hook (setup) → middle (core value) → resolution (payoff + CTA). No dead ends. |
| **Sequence & pacing** | Release information deliberately — progressive disclosure, step flows, scroll-driven reveals. |
| **Protagonist** | The **user is the hero**, the product is the **guide**. Write copy around their goal and obstacle. |
| **Emotional beats** | Empty/loading/error/success states carry intentional tone, not just function. |
| **Continuity & motion** | Transitions maintain a thread between states (shared-element, scroll-linked) so it's one journey. |

### Narrative role of each screen pattern

| Pattern | Narrative role |
|---------|----------------|
| Onboarding | Act I — promise the payoff, show progress, reach first value fast |
| Dashboard | Home base — lead with "what changed", surface the next best action |
| List / Detail | Journey → destination; preserve context on the way back |
| Forms | The ordeal — pace with sections; inline validation is a guide that catches you |
| Search | The quest — zero-results is a fork with a suggested path, not a wall |
| Empty states | The invitation — most emotional weight per pixel; setup + first action |

### Storytelling review checklist (score 0–2 each, /16)

1. **Arc** — clear hook → value → payoff, no dead ends
2. **Hero framing** — copy centers the user's goal/obstacle; product is the guide
3. **Pacing** — information released deliberately, not dumped
4. **First value** — reaches the "aha"/first success quickly
5. **Emotional beats** — empty/loading/error/success carry intentional tone
6. **Continuity** — transitions maintain a thread between states
7. **Resolution** — satisfying success state with an obvious next step
8. **Restraint** — narrative never blocks clarity, speed, accessibility, or skip paths

> **≥13** strong narrative · **8–12** functional but flat · **<8** a disconnected set of screens.

**Restraint rule:** storytelling serves the user's goal — keep skip paths, never withhold
critical information for "drama," keep durations short, and honor `prefers-reduced-motion`.

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
- `references/storytelling-ui.md` — Storytelling UI framework (narrative arc, StoryBrand SB7, pacing, emotional beats, motion/continuity, microcopy, scored checklist)
