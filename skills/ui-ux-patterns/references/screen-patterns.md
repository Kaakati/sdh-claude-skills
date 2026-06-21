# Screen Pattern Specifications

Detailed specifications for the 8 core screen patterns.

---

## 1. Onboarding

### Purpose
Guide first-time users through initial setup and value demonstration.

### Structure
```
┌─────────────────────────────┐
│ [Logo]                      │
│                             │
│ ┌─────────────────────────┐ │
│ │     [Illustration]      │ │
│ └─────────────────────────┘ │
│                             │
│ Step X of Y    ● ● ○ ○     │
│                             │
│ [Heading: Value Prop]       │
│ [Body: Brief description]   │
│                             │
│ ┌─────────────────────────┐ │
│ │     [Primary CTA]       │ │
│ └─────────────────────────┘ │
│                             │
│ Skip →                      │
└─────────────────────────────┘
```

### Requirements
- **Progress**: Show step count (e.g., "Step 2 of 4") and visual dots/bar
- **Skip**: Always provide a skip option (never force onboarding)
- **Value-first**: Each step communicates a benefit, not a feature
- **Minimal input**: Defer configuration until after onboarding
- **Completion**: End with a success state and primary action to start using the product

### Key Decisions
| Decision | Recommended | Alternative |
|----------|-------------|------------|
| Navigation | Swipe/carousel | Step wizard |
| Length | 3-5 steps | 2 for simple products |
| Input | Defer to post-onboarding | Inline if critical (e.g., role selection) |
| Animation | Subtle slide transitions | Parallax for premium feel |

---

## 2. Dashboard

### Purpose
Provide an overview of key metrics, recent activity, and quick actions.

### Structure
```
┌─────────────────────────────────────┐
│ [Header: Welcome, {Name}]          │
│ [Date range selector] [Actions ▼]  │
├────────┬────────┬────────┬─────────┤
│ KPI 1  │ KPI 2  │ KPI 3  │ KPI 4   │
│ $1.2M  │ 3,421  │ 94.2%  │ +12.3%  │
│ ▲ 8%   │ ▼ 2%   │ — 0%   │ ▲ 3%    │
├────────┴────────┼────────┴─────────┤
│                 │                  │
│  [Line/Bar      │  [Activity       │
│   Chart]        │   Feed]          │
│                 │                  │
├─────────────────┼──────────────────┤
│  [Recent        │  [Quick          │
│   Items]        │   Actions]       │
└─────────────────┴──────────────────┘
```

### Requirements
- **KPIs at top**: 3-5 key metrics with trend indicators (up/down/stable)
- **Date range**: Allow filtering by time period
- **Charts**: Use appropriate chart type (line for trends, bar for comparison, donut for distribution)
- **Activity feed**: Recent events, chronologically ordered
- **Quick actions**: Frequently used actions accessible in 1 click
- **Responsive**: Stack columns on mobile; KPIs in horizontal scroll

### Key Decisions
| Decision | Recommended | Alternative |
|----------|-------------|------------|
| Layout | Bento grid (mixed sizes) | Equal cards |
| Charts | ApexCharts (project standard) | Recharts |
| Refresh | Real-time via Centrifugo | Pull-to-refresh (mobile) |
| Empty state | Guided setup checklist | Sample data |

---

## 3. List/Detail

### Purpose
Browse a collection and inspect individual items.

### Structure

**Desktop (side-by-side)**:
```
┌──────────────────┬──────────────────────┐
│ [Search]  [Filter]│ [Item Title]         │
│                   │                      │
│ ┌───────────────┐ │ [Content area]       │
│ │ Item 1    ►   │ │                      │
│ ├───────────────┤ │ [Details, metadata]  │
│ │ Item 2        │ │                      │
│ ├───────────────┤ │ [Actions]            │
│ │ Item 3        │ │                      │
│ └───────────────┘ │                      │
│                   │                      │
│ ← 1 2 3 ... →    │                      │
└──────────────────┴──────────────────────┘
```

**Mobile (stacked)**:
```
[Search] [Filter]
┌───────────────────┐
│ Item 1         →  │
├───────────────────┤
│ Item 2         →  │
├───────────────────┤
│ Item 3         →  │
└───────────────────┘
← Previous  Next →

→ Tap item → Navigate to detail page
```

### Requirements
- **Search**: Always visible, with debounced input (300ms)
- **Filters**: Collapsible on mobile, sidebar on desktop
- **Sort**: At least 2-3 sort options (date, name, relevance)
- **Pagination**: Cursor-based for large lists; infinite scroll for feeds
- **Empty state**: Meaningful message + CTA when list is empty
- **Loading**: Skeleton placeholders during data fetch

---

## 4. Forms

### Purpose
Collect structured user input.

### Structure
```
┌─────────────────────────────┐
│ [Form Title]                │
│ [Description/context]       │
│                             │
│ Section 1                   │
│ ┌─────────────────────────┐ │
│ │ Label                   │ │
│ │ [Input field]           │ │
│ │ Helper text             │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Label *                 │ │
│ │ [Input field]           │ │
│ │ ⚠ Error message         │ │
│ └─────────────────────────┘ │
│                             │
│ Section 2                   │
│ ┌─────────────────────────┐ │
│ │ ...                     │ │
│ └─────────────────────────┘ │
│                             │
│ [Cancel]    [Submit ▸]      │
└─────────────────────────────┘
```

### Requirements
- **Labels**: Every input has a visible label (never placeholder-only)
- **Validation**: Inline validation on blur; show errors next to the field
- **Required fields**: Marked with asterisk and `aria-required="true"`
- **Progressive disclosure**: Show advanced options only when needed
- **Error summary**: Scroll to first error on submit
- **Autosave**: For long forms, auto-save drafts with visual confirmation
- **Cancel**: Always provide a cancel/discard option

### Input Types
| Data Type | Component | Validation |
|-----------|-----------|------------|
| Text (short) | Input | minLength, maxLength, pattern |
| Text (long) | Textarea | maxLength, word count |
| Selection (few) | Radio group or Select | Required |
| Selection (many) | Combobox with search | Required |
| Multi-select | Checkbox group or multi-select | Min/max selections |
| Date | Date picker | Min/max date |
| File | File upload with preview | File type, max size |
| Toggle | Switch | — |

---

## 5. Search

### Purpose
Find items within large datasets.

### Requirements
- **Debounced input**: 300ms delay before triggering search
- **Instant results**: Show results as user types (typeahead)
- **Filters**: Category, date range, status; collapsible on mobile
- **Result count**: "X results for 'query'" above results
- **Highlight matches**: Bold the matching text in results
- **Empty state**: "No results for 'query'" + suggestions
- **Recent searches**: Show last 5 searches when input is focused and empty

---

## 6. Settings

### Purpose
Configure preferences and account settings.

### Requirements
- **Categories**: Left sidebar (desktop) or top tabs (mobile)
- **Save behavior**: Auto-save toggles; explicit save for text fields
- **Confirmation**: Show toast on save; confirm destructive changes
- **Defaults**: Show default values clearly; allow reset to defaults
- **Danger zone**: Group destructive actions (delete account) at bottom with red styling

---

## 7. Profile

### Purpose
Display and edit user identity and account information.

### Requirements
- **Avatar**: Upload with crop, default initials fallback
- **View/Edit modes**: Toggle between display and edit
- **Sections**: Personal info, preferences, security, connected accounts
- **Activity**: Recent actions or contributions timeline
- **Accessibility**: All form fields labeled, avatar has alt text

---

## 8. Empty States

### Purpose
Guide users when there is no data to display.

### Variants
| Type | When | Message Pattern |
|------|------|----------------|
| First use | User has never created content | "Create your first [item]" + CTA |
| No results | Search/filter returned nothing | "No [items] match your filters" + clear filters CTA |
| Error | Data failed to load | "Something went wrong" + retry CTA |
| Success | Task completed, list cleared | "All caught up!" + next action suggestion |

### Requirements
- **Illustration**: Simple, on-brand illustration or icon
- **Message**: Friendly, action-oriented (not just "No data")
- **CTA**: Primary action to resolve the empty state
- **No blame**: Never suggest user error for empty states
