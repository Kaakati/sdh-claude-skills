---
name: figma-handoff
description: |
  Figma-to-code translation for Auto Layout, frames, components, and design tokens.
  Maps Figma properties to CSS/Tailwind, HTML structure, and React Native styles.
  Triggers on "Figma handoff", "Figma to code", "auto layout", "design handoff",
  "Figma translation", "design specs", or "Figma implementation".
model: sonnet
---

# Figma Auto-Layout Expert

Systematic translation from Figma design specifications to production code across Tailwind CSS, React Native, and Phlex platforms.

## When to Apply

Use this skill when:
- Translating Figma designs into HTML/CSS/Tailwind code
- Converting Auto Layout properties to CSS flexbox/grid
- Extracting design tokens from Figma files
- Creating responsive implementations from static designs
- Generating a handoff documentation package for developers

## Translation Protocol

### Step 1: Auto Layout → CSS/Tailwind Mapping

Reference `references/auto-layout-mapping.md` for the complete property mapping table.

#### Quick Reference

| Figma Property | CSS Equivalent | Tailwind Class |
|---------------|---------------|----------------|
| Auto Layout: Horizontal | `display: flex; flex-direction: row` | `flex flex-row` |
| Auto Layout: Vertical | `display: flex; flex-direction: column` | `flex flex-col` |
| Gap: 8px | `gap: 8px` | `gap-2` |
| Padding: 16px | `padding: 16px` | `p-4` |
| Alignment: Center | `align-items: center; justify-content: center` | `items-center justify-center` |
| Fill container | `flex: 1` | `flex-1` |
| Hug contents | `width: auto` | `w-auto` |
| Fixed | `width: Xpx` | `w-[Xpx]` (use token if available) |

### Step 2: Frame → HTML Structure

Map Figma frames to semantic HTML:

| Figma Element | HTML Element | When |
|--------------|-------------|------|
| Top-level frame | `<main>`, `<section>` | Page-level container |
| Navigation frame | `<nav>` | Contains nav links |
| Header frame | `<header>` | Page/section header |
| Card frame | `<article>` or `<div>` | Self-contained content unit |
| Text layer | `<h1>`-`<h6>`, `<p>`, `<span>` | Based on hierarchy |
| Button component | `<button>` | Interactive action |
| Link component | `<a>` | Navigation action |
| Input frame | `<input>`, `<textarea>` | Data entry |
| List frame | `<ul>` + `<li>` | Repeating items |
| Image layer | `<img>` or `next/image` | Visual content |

### Step 3: Component Extraction

For each unique Figma component:

1. **Identify atomic level**: Is it an atom, molecule, organism, or template?
2. **Map variants**: Figma variants → component props (size, variant, state)
3. **Extract tokens**: Colors, typography, spacing → design tokens
4. **Define props**: Required and optional parameters
5. **Generate code**: Platform-specific implementation

### Step 4: Token Extraction

Extract design tokens from Figma styles:

| Figma Style | Token Category | Example |
|-------------|---------------|---------|
| Color styles | `--primary`, `--secondary` | `Fill: #0F172A` → `--primary: 222.2 47.4% 11.2%` |
| Text styles | Font family, size, weight | `Inter 16/24 Regular` → `text-base font-normal leading-normal` |
| Effect styles | Shadows, blurs | `Shadow: 0 4px 6px rgba(0,0,0,0.1)` → `shadow-md` |
| Grid styles | Columns, gutters, margins | `12col / 24px gutter / 80px margin` → grid config |

**Map onto the registry — do not mint token names from Figma's.** A Figma file names styles for
designers (`Brand/Green/500`, `Semantic/Success`), and the tempting move is to transliterate:
`--brand-green-500`, `--semantic-success`. Those compile to **nothing**. Tailwind only emits a
utility for a token registered in the config, so `bg-brand-green-500` is not a broken colour — it is
**no CSS at all**, silently, and the element renders with whatever it inherited. Review does not
catch it because the class name looks right.

The registered names are in `@skills/theming/references/platform-integration.md` — that list, and
nothing else, is what exists. Two that catch people out: **`destructive` and `neutral` are variant
*keys*, not tokens** (the registered ones are `error` and `muted`), so a Figma layer called
"Destructive" maps to `bg-error`, not `bg-destructive`.

If a Figma style has no registered counterpart, that is a **finding, not a naming exercise**:
report it, and let `/theming` or `std-design-system` decide whether the design system gains a token.
Inventing one in a handoff doc means the design system grew a member nobody registered.

**Colour pulled from Figma is unverified.** A designer's green is a brand decision, not a contrast
measurement — `Fill: #10B981` on white is about 2.5:1. Do not carry a fill straight into a
`--x` / `--x-foreground` pair and call it a token: compute the ratio
(`@skills/std-design-system/references/defining-tokens.md`), and if it fails, darken the **surface**
for a semantic colour or the **foreground** for a brand one. The three presets this repo ships were
built without that step and 13 of their pairs measured below AA.

### Step 5: Responsive Strategy

Map Figma breakpoints to Tailwind breakpoints:

| Figma Frame Width | Tailwind Breakpoint | Prefix |
|-------------------|--------------------|---------|
| 320-639px | Default (mobile-first) | — |
| 640px+ | `sm` | `sm:` |
| 768px+ | `md` | `md:` |
| 1024px+ | `lg` | `lg:` |
| 1280px+ | `xl` | `xl:` |
| 1536px+ | `2xl` | `2xl:` |

For each component, document layout changes per breakpoint:
- Stack → row transitions
- Show/hide elements
- Font size adjustments
- Spacing changes

### Step 6: Asset Export

Specify export settings for design assets:

| Asset Type | Format | Size | Notes |
|-----------|--------|------|-------|
| Icons | SVG | Original | Inline or sprite sheet |
| Illustrations | SVG or WebP | 1x, 2x | Responsive, `loading="lazy"` |
| Photos | WebP + JPEG fallback | 1x, 2x, 3x | `next/image` with blur placeholder |
| Logos | SVG | Original | Inline for crisp rendering |
| Favicons | PNG + ICO | 16, 32, 180, 512 | Include manifest.json |

### Step 7: Handoff Document

Generate a developer handoff document:

```markdown
# Design Handoff — [Feature/Page Name]

## Design Link
[Figma URL]

## Tokens Used
| Token | Value | Tailwind |
|-------|-------|----------|
| ... | ... | ... |

## Components
| Component | Level | Variants | Props |
|-----------|-------|----------|-------|
| ... | ... | ... | ... |

## Responsive Behavior
| Breakpoint | Layout Changes |
|-----------|---------------|
| Mobile (default) | ... |
| Tablet (md:) | ... |
| Desktop (lg:) | ... |

## Assets to Export
| Asset | Format | Location |
|-------|--------|----------|
| ... | ... | ... |

## Accessibility Notes
- Focus order: [describe]
- ARIA requirements: [describe]
- Keyboard interactions: [describe]
```

## Full References

- `references/auto-layout-mapping.md` — Complete Figma → CSS/Tailwind property mapping
- `references/figma-to-code.md` — Detailed Figma-to-code translation workflow
