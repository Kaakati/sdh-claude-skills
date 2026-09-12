---
name: ui-ux-patterns
description: |
  UI/UX pattern library with screen archetypes, Nielsen's heuristics evaluation,
  visual hierarchy principles, storytelling/narrative UX, role-based UX,
  drill-down navigation, and platform-specific adaptations.
  Triggers on "UI patterns", "UX patterns", "screen patterns", "heuristic evaluation",
  "visual hierarchy", "interaction design", "UX review", "UI best practices",
  "storytelling UI", "narrative design", "user journey arc", "StoryBrand",
  "emotional beats", "scrollytelling", "role-based UX", "what should each role see",
  "persona walkthrough", "hidden vs disabled", "locked feature", "role-based dashboard",
  "role-based sidebar", "access denied vs not found", "read-only state", "masked field",
  "role management screen", "permission matrix editor", "audit log UI", "impersonation",
  "admin view as", "drill-down navigation", "navigation hierarchy", "information architecture",
  "sidebar clutter", "breadcrumbs", "sub-navigation", "list-detail", or "command palette".
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
- Designing for several roles — what each role sees and how, landing pages, sidebars, dashboards, not rendered vs disabled vs locked (see **Role-Based UX** below)
- Designing the states a role meets (read-only, no access vs not found, empty, masked) or the screens that grant access — role catalog, invites, matrix editor, audit log, "view as" (see **Role-Based UX** below)
- Structuring navigation — what the global nav holds, how deep a path goes, where people are at each level, how Back, search and the command palette behave — including migrating an existing product's navigation (see **Drill-down Navigation** below)

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
| 5 | Error Prevention | Confirmation, constraints, defaults; unavailable actions: not permitted → not rendered, record-blocked → disabled + visible reason, other plan → locked |
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

## Role-Based UX

In a multi-role product every role is the hero of its own story. Per role, per screen, ask
**"As a `<Role>`, what should I see, and how should I see it?"** — *what* is the permission matrix's
answer; *how* (prominence, format, density) comes from that role's tasks. Three references, one job
each:

| Reference | Covers |
|---|---|
| `references/role-based-ux.md` | **The lens** — persona cards, the walkthrough table, a worked five-role example, landing page, navigation order (Hick's law, WCAG 3.2.3), per-role dashboards (personalization vs customization), progressive disclosure, the canonical three-state rule and where it departs from Carbon, Primer, Helios, Cloudscape, and GOV.UK, multi-role union, per-role heuristics |
| `references/role-based-ux-states.md` | **Every state a role meets** — not rendered, disabled with a reason, read-only, locked by plan or quota, no access vs not found (403 vs 404), the kinds of empty, error, masked fields, loading; disabled reasons that reach keyboard and screen-reader users; copy per state; a decision table |
| `references/role-management-ux.md` | **The screens that grant access** — role catalog and ladders, permission sets, the matrix editor (tri-state groups, diff before save, dangerous-grant confirmation), invite and assign, separation of duties, the last-owner guard, audit log, "view as" and impersonation, masked secrets |

**The three-state rule** (canonical there): not permitted → **not rendered** · permitted but blocked
by record state → **disabled with a visible reason** · available on another plan → **visible and
locked**, only for roles that could act on it. The UI checks permission keys, never role names;
gates in code → `@skills/access-control-designer/references/ui-gates.md`.

## Drill-down Navigation

The global nav holds only **areas** and stays visible; depth lives in pages — area → overview → list
→ detail → sub-detail, nothing deeper — each with a URL, its location cues, and search as the second
way. It applies to existing products now, not at their next redesign. Rules, sources and
anti-patterns → `references/drill-down-navigation.md`.

- **The global sidebar lists areas only** — optional static group labels, no nested sections, no
  collapsible groups. Each area's sections render in that area's own layout.
- **Budget per role:** 7 or fewer desktop areas (an IA review above 10) and 3–5 native tabs; a breach
  triggers a design review. Phone-width web with 5 or more areas → a button labelled "Menu", with the
  area's section nav kept visible in the page.
- **Location at every level:** active area and section, `h1`, document title; breadcrumbs from level
  3, built from the API's `ancestors`.
- **Back and list state:** filters, sort and query live in the URL, and the list crumb's `href` brings
  them back; never an in-page Back that calls `history.back()`.
- **A second way:** header search on every page; one shared command palette, optional per product,
  never the only route.

Mechanics per stack → `@skills/std-nextjs/references/navigation.md`,
`@skills/std-reactjs/references/routing-and-code-split.md`,
`@skills/std-react-native/references/navigation.md`,
`@skills/std-phlex-conventions/references/turbo-frames-and-streams.md`. The API half →
`@skills/std-api-design/references/drill-down-resources.md`; the nav config and its gates →
`@skills/access-control-designer/references/ui-gates.md`.

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
| Disabled | Dimmed control with its reason beside it at full contrast (`aria-disabled`, not `disabled`); not-permitted items are not rendered | `aria-disabled:opacity-50 aria-disabled:cursor-not-allowed` |
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
- The desktop sidebar ships open and lists areas only; sections live in each area's layout

### Mobile (React Native)
- Touch targets minimum 44x44px
- Haptic feedback on significant actions (iOS)
- Bottom sheet instead of dropdown menus
- Pull-to-refresh on list screens
- Gesture navigation (swipe back, swipe to dismiss)
- Platform-specific patterns (iOS back gesture, Android material ripple)
- A persistent tab bar of 3–5 areas, Account included, with one stack per tab

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
- `references/role-based-ux.md` — Role-based UX lens (persona cards, per-role walkthroughs, landing page, navigation order, per-role dashboards, progressive disclosure, the canonical three-state rule and how it reconciles with other design systems, multi-role union, per-role heuristics)
- `references/role-based-ux-states.md` — Every state a role meets (not rendered, disabled with a reason, read-only, locked, no access vs not found, empty, error, masked, loading), accessible disabled reasons, copy patterns, decision table
- `references/role-management-ux.md` — Access-management screens (role catalog, permission sets, matrix editor, invite and assign, separation of duties, last-owner guard, audit log, impersonation and "view as", masked secrets) mapped to the grant rules
- `references/drill-down-navigation.md` — Drill-down navigation standard (areas-only global sidebar, budgets per role, the level model, location cues and breadcrumbs, Up/Back and list state, deep links, section navigation, search and the shared command palette, roles, accessibility outcomes, anti-patterns, existing products, per-stack mechanics)
