# Brand Book Template

Use this structure to generate a complete brand book document.

---

## Cover Page

```markdown
# [Brand Name] Brand Guidelines
Version [X.X] — [Date]
```

---

## 1. Brand Foundation

### 1.1 Mission
> [One sentence: What we do and why it matters]

### 1.2 Vision
> [One sentence: The future we're building toward]

### 1.3 Values
| Value | Meaning | In Practice |
|-------|---------|-------------|
| [Value 1] | [Definition] | [How this shows up in our product/communication] |
| [Value 2] | [Definition] | [How this shows up] |
| [Value 3] | [Definition] | [How this shows up] |

### 1.4 Brand Archetype
**Primary**: [Archetype name]
**Secondary influence**: [Archetype name]

[2-3 sentences on how this archetype manifests in the brand personality]

---

## 2. Logo

### 2.1 Primary Logo
[Description of primary logo mark]

### 2.2 Logo Variants
| Variant | Usage | Background |
|---------|-------|------------|
| Full color | Default, marketing materials | Light backgrounds |
| Monochrome | Documents, co-branding | Any background |
| Reversed | Dark backgrounds, overlays | Dark backgrounds |
| Mark only | Favicon, app icon, small spaces | Any background |

### 2.3 Clear Space
Minimum clear space: **[X]** (height of logo mark / 4) on all sides.

### 2.4 Minimum Size
- Print: [X]mm width
- Digital: [X]px width
- Favicon: [X]px

### 2.5 Logo Don'ts
- Do not stretch or distort the logo
- Do not rotate the logo
- Do not add drop shadows, outlines, or effects
- Do not change the logo colors outside approved variants
- Do not place the logo on visually busy backgrounds
- Do not rearrange logo elements

---

## 3. Color System

### 3.1 Primary Palette
| Token | HSL | Hex | Usage |
|-------|-----|-----|-------|
| `--primary` | [H S% L%] | [#hex] | Brand color, primary actions, headers |
| `--primary-foreground` | [H S% L%] | [#hex] | Text on primary backgrounds |
| `--secondary` | [H S% L%] | [#hex] | Secondary actions, accents |
| `--secondary-foreground` | [H S% L%] | [#hex] | Text on secondary backgrounds |
| `--accent` | [H S% L%] | [#hex] | Highlights, hover states, CTAs |
| `--accent-foreground` | [H S% L%] | [#hex] | Text on accent backgrounds |

### 3.2 Neutral Palette
| Token | HSL | Hex | Usage |
|-------|-----|-----|-------|
| `--background` | [H S% L%] | [#hex] | Page background |
| `--foreground` | [H S% L%] | [#hex] | Default body text |
| `--muted` | [H S% L%] | [#hex] | Subtle backgrounds, disabled states |
| `--muted-foreground` | [H S% L%] | [#hex] | Secondary/muted text |

### 3.3 Semantic Colors
| Token | HSL | Hex | Usage |
|-------|-----|-----|-------|
| `--success` | [H S% L%] | [#hex] | Confirmations, positive states |
| `--warning` | [H S% L%] | [#hex] | Caution, pending states |
| `--error` | [H S% L%] | [#hex] | Errors, destructive actions |
| `--info` | [H S% L%] | [#hex] | Informational states |

### 3.4 Contrast Compliance
| Pair | Ratio | WCAG Level |
|------|-------|------------|
| primary / primary-foreground | [X]:1 | AA / AAA |
| background / foreground | [X]:1 | AA / AAA |
| ... | ... | ... |

### 3.5 Dark Mode
All tokens have dark mode overrides defined in the `.dark` class scope.

---

## 4. Typography

### 4.1 Font Families
| Role | Font | Weight Range | Fallback Stack |
|------|------|-------------|----------------|
| Headings | [Font] | 600-700 | [stack] |
| Body | [Font] | 300-500 | [stack] |
| Code | [Font] | 400 | [stack] |

### 4.2 Type Scale
| Token | Size | Usage |
|-------|------|-------|
| `text-xs` | 12px | Captions, labels |
| `text-sm` | 14px | Secondary text |
| `text-base` | 16px | Body text |
| `text-lg` | 18px | Subheadings |
| `text-xl` | 20px | Section headings |
| `text-2xl` | 24px | Page titles |
| `text-3xl` | 30px | Major headings |
| `text-4xl` | 36px | Hero titles |

### 4.3 Heading Styles
| Level | Size | Weight | Line Height | Letter Spacing |
|-------|------|--------|-------------|----------------|
| H1 | text-4xl | bold (700) | tight (1.25) | -0.02em |
| H2 | text-3xl | semibold (600) | tight (1.25) | -0.01em |
| H3 | text-2xl | semibold (600) | snug (1.375) | normal |
| H4 | text-xl | medium (500) | snug (1.375) | normal |

---

## 5. Brand Voice

### 5.1 Voice Matrix
| Dimension | We Are | We Are Not |
|-----------|--------|------------|
| [dim1] | [positive] | [negative] |
| [dim2] | [positive] | [negative] |
| [dim3] | [positive] | [negative] |

### 5.2 Writing Guidelines
- **Sentence length**: [Preference]
- **Vocabulary**: [Level]
- **Point of view**: [we/our vs. third person]
- **CTA style**: [Pattern]

### 5.3 Examples
| Context | Do | Don't |
|---------|-----|-------|
| Error messages | "We couldn't save your changes. Try again?" | "Error 500: Internal Server Error" |
| Empty states | "No projects yet. Create your first one!" | "No data found." |
| Success | "Changes saved!" | "Operation completed successfully." |

### 5.4 Narrative & Protagonist Voice

The **user is the hero; the brand is the guide** (StoryBrand SB7). Every headline,
onboarding step, and campaign casts the user as the protagonist and the brand as the
mentor that hands them a plan and a tool — never the hero who saves the day. See the
canonical framework at `../ui-ux-patterns/references/storytelling-ui.md`.

**Guide role (from our archetype):** [One line — the kind of guide our archetype makes us,
e.g. "Sage: we share what we've learned and let the user decide."]

#### Brand Narrative Arc (SB7)
| Beat | Our brand |
|------|-----------|
| Character + want | [The user and what they're trying to achieve] |
| Problem | [External blocker + the internal frustration it creates] |
| Guide (empathy + authority) | [We understand: …] / [We're competent: …] |
| Plan | [Step 1] → [Step 2] → [Step 3] |
| Call to action | Direct: [e.g. "Start free"] · Transitional: [e.g. "See how it works"] |
| Stakes (failure avoided) | [What the user loses by not acting — used sparingly] |
| Success (transformation) | [Who the hero becomes once the want is met] |

#### User Transformation Story
> **Before:** [Who the user is at the start — frustrated, stuck, overwhelmed]
> **After:** [Who they become — confident, in control, recognized]
> **Our role:** [The guide that made the shift possible]

#### Hero-Framed vs. Company-Centered
| Company-centered ❌ (brand as hero) | Hero-framed ✅ (user as hero, brand as guide) |
|-------------------------------------|------------------------------------------------|
| "We built the most powerful [X]." | "[Outcome] — in one glance." |
| "Our platform supports [feature]." | "[User goal]; we handle the rest." |
| "We're the industry leader in [Y]." | "Sleep easy — [user benefit]." |
| "Welcome to [Brand]." | "Welcome back — here's what changed since you left." |

**Restraint rule:** narrative voice serves the user's goal; it never overrides clarity,
speed, or accessibility. No false stakes, no withholding critical info for drama, always
keep skip paths, and honor `prefers-reduced-motion` for story-bearing motion.

---

## 6. Design Tokens (CSS Output)

```css
:root {
  /* Colors — paste full :root block */
}

.dark {
  /* Dark mode overrides — paste full .dark block */
}
```

---

## 7. Trend Positioning

| Trend | Stance | Rationale |
|-------|--------|-----------|
| [Trend 1] | Adopt / Adapt / Avoid | [Why] |
| [Trend 2] | Adopt / Adapt / Avoid | [Why] |
