---
name: brand-identity
description: |
  Brand identity creation with design tokens, color psychology, typography pairing,
  and brand book generation. Covers brand archetypes, voice matrix, narrative &
  protagonist voice (user-as-hero / StoryBrand), trend-aware positioning, and token
  output for Tailwind CSS and React Native.
  Triggers on "brand identity", "brand guidelines", "brand book", "logo usage",
  "brand colors", "brand voice", "brand archetype", "brand narrative", "storytelling",
  "narrative UX", "StoryBrand", or "brand system".
model: opus
---

# Brand Identity Creator

Guided workflow for establishing a complete brand identity system that outputs actionable design tokens, typography pairings, and a brand book template.

## When to Apply

Use this skill when:
- Starting a new product or project that needs a brand identity
- Refreshing or modernizing an existing brand
- Establishing brand guidelines for a client project
- Creating a design token system rooted in brand values
- Defining brand voice and personality for content creation

## Brand Discovery Protocol

### Step 1: Brand Brief

Gather the following from the user (ask if not provided):

1. **Company/Product Name**: What is the brand?
2. **Mission Statement**: What problem does the brand solve?
3. **Target Audience**: Demographics, psychographics, pain points
4. **Competitive Landscape**: Key competitors and their positioning
5. **Brand Values**: 3-5 core values (e.g., trust, innovation, simplicity)
6. **Tone Descriptors**: 3 adjectives that describe the desired feel (e.g., modern, approachable, premium)

### Step 2: Archetype Selection

Map the brand to one of 12 brand archetypes:

| Archetype | Core Desire | Strategy | Example Brands |
|-----------|------------|----------|---------------|
| Innocent | Safety | Be optimistic, simple, honest | Dove, Coca-Cola |
| Sage | Understanding | Seek truth, share knowledge | Google, TED |
| Explorer | Freedom | Push boundaries, discover | Patagonia, Jeep |
| Ruler | Control | Lead, create order | Mercedes, Rolex |
| Creator | Innovation | Build something meaningful | Apple, Adobe |
| Caregiver | Service | Protect, nurture | Johnson & Johnson |
| Magician | Transformation | Make dreams real | Disney, Tesla |
| Hero | Mastery | Prove worth through courage | Nike, FedEx |
| Outlaw | Liberation | Break the rules | Harley-Davidson, Virgin |
| Jester | Enjoyment | Have a good time | M&M's, Old Spice |
| Lover | Intimacy | Create connection | Chanel, Godiva |
| Everyman | Belonging | Be relatable, connect | IKEA, Target |

Present the top 2-3 archetypes that fit the brand brief and let the user choose.

### Step 3: Color System

Based on archetype and tone descriptors, create a color palette:

1. **Primary color**: The hero color representing the brand essence
2. **Secondary color**: Complementary, supporting the primary
3. **Accent color**: For highlights, CTAs, and energy
4. **Neutral palette**: Grays for text, backgrounds, borders
5. **Semantic colors**: Success (green), warning (amber), error (red), info (blue)

**Color method**: Choose from complementary, analogous, triadic, or split-complementary based on brand energy level. Reference `references/color-theory.md` for palette methods.

Output all colors in HSL format with foreground pairs meeting WCAG AA (4.5:1 contrast):

```css
:root {
  --primary: H S% L%;
  --primary-foreground: H S% L%;
  /* ... */
}
```

### Step 4: Typography Pairing

Select font pairing based on brand personality:

| Brand Personality | Heading Font | Body Font | Rationale |
|------------------|-------------|-----------|-----------|
| Modern + Clean | Inter | Inter | Single-family, maximum consistency |
| Premium + Editorial | Playfair Display | Source Sans 3 | Serif/sans contrast, luxury feel |
| Tech + Precise | Space Grotesk | JetBrains Mono | Geometric + monospace, developer appeal |
| Warm + Approachable | Nunito | Open Sans | Rounded + neutral, friendly |
| Bold + Dynamic | Montserrat | Roboto | Strong geometric + versatile |

Include weight scale (300-700) and size scale usage recommendations.

### Step 5: Logo Usage Guidelines

Define logo usage rules:

- **Clear space**: Minimum padding around logo (typically logo height / 4)
- **Minimum size**: Smallest acceptable rendering (e.g., 24px height)
- **Color variants**: Full color, monochrome, reversed (on dark), grayscale
- **Don'ts**: Stretch, rotate, add effects, change colors, place on busy backgrounds
- **Favicon**: Simplified mark for 16x16 and 32x32 contexts

### Step 6: Brand Voice Matrix

Define the brand's communication personality:

| Dimension | We Are | We Are Not |
|-----------|--------|------------|
| Tone | Confident, warm | Arrogant, cold |
| Language | Clear, conversational | Jargon-heavy, academic |
| Humor | Light, witty | Sarcastic, forced |
| Formality | Professional but human | Corporate or casual |

Include writing guidelines:
- Sentence structure preferences (short + direct vs. flowing + descriptive)
- Vocabulary level (accessible vs. technical)
- Point of view (we/our vs. the company/the product)
- CTA style (action-oriented, benefit-driven)

### Step 6b: Narrative & Protagonist Voice

The voice matrix (Step 6) defines *how* the brand sounds. This step defines *who the
story is about*. The answer must always be: the **user is the hero, the brand is the
guide**. The brand never casts itself as the protagonist who saves the day — it is the
mentor that hands the hero a plan and a tool ("you're Luke, we're Yoda"). This is the
StoryBrand (SB7) discipline applied to brand voice, and it should reinforce — not
contradict — the chosen archetype from Step 2.

For the canonical framework, see
`../ui-ux-patterns/references/storytelling-ui.md` (single source of truth for narrative
UI, SB7 mapping, emotional beats, and the scored review checklist). The notes below adapt
it specifically to brand voice and the brand book.

#### Archetype → guide role

The archetype shapes *what kind of guide* the brand is. The hero is always the user.

| Archetype | The brand as guide says, in effect… |
|-----------|-------------------------------------|
| Sage | "Here's what we've learned — now you decide." (knowledge, not gatekeeping) |
| Hero | "You've got this. Here's the training and the gear." (the brand equips, the user wins) |
| Caregiver | "We've got your back. Here's the safe path." |
| Magician | "Here's the shortcut to the transformation you want." |
| Creator | "Here are the tools — the masterpiece is yours." |
| Everyman | "We're in this with you. Here's the simple next step." |

> **Common mistake:** brands with the **Hero** archetype often write themselves as the
> protagonist ("We slay your problems"). Resist this. Even a Hero-archetype brand is the
> hero's *coach and equipment*, not the hero. The user must remain the one who wins.

#### Define the brand narrative arc

Write the brand's one-paragraph story using the SB7 beats. This is the spine that every
headline, onboarding flow, and campaign hangs from:

1. **Character (the user) + want** — Who they are and what they're trying to achieve.
2. **Problem** — The external blocker, the internal frustration it creates, and (if
   relevant) why it's wrong that they should have to put up with it.
3. **Guide (the brand) — empathy + authority** — One line showing you understand the
   pain, one line showing you're competent to fix it (proof, track record).
4. **Plan** — The simple 3-step path you offer.
5. **Call to action** — The direct ask (e.g. "Start free") + a transitional ask (e.g.
   "See how it works").
6. **Stakes (failure avoided)** — What the user loses by not acting — used sparingly.
7. **Success (transformation)** — The "after": who the hero becomes once the want is met.

#### The user's transformation story

State, in one line each, the before → after the brand delivers. This is the most reusable
artifact for marketing, onboarding, and landing copy:

- **Before (identity):** who the user is at the start (frustrated, stuck, overwhelmed).
- **After (identity):** who they become (confident, in control, recognized).
- **Brand's role:** the guide that made the shift possible.

> Example — "Before: a founder drowning in spreadsheets. After: a founder who runs the
> numbers in minutes and gets back to building. We're the tool that hands them the time."

#### Hero-framed vs. company-centered voice matrix

Extend the Step 6 "We Are / We Are Not" matrix with a protagonist axis. Every piece of
copy should be rewritable from the left column to the right:

| Company-centered ❌ (brand as hero) | Hero-framed ✅ (user as hero, brand as guide) |
|-------------------------------------|------------------------------------------------|
| "We built the most powerful analytics engine." | "See what's driving your growth — in one glance." |
| "Our platform supports multi-region deploys." | "Ship to your users anywhere; we handle the regions." |
| "We're the industry leader in security." | "Sleep easy — your data's locked down." |
| "Sign up for our newsletter." | "Get the playbook that keeps you ahead." |
| "Our award-winning support team." | "Stuck? You'll have an answer in minutes." |
| "Welcome to [Brand]." | "Welcome back — here's what changed since you left." |

Rules of thumb for the writing guidelines (Step 6.2):
- **Second person, user's goal first.** Lead with "you" and the outcome, not "we" and the
  feature.
- **Features earn their place by serving the want** — name the transformation, then the
  capability that enables it.
- **Reserve "we/our" for the guide's empathy and authority** ("We've been there", "Trusted
  by 4,000 teams"), not for claiming the win.
- **Emotional beats carry the arc** — empty states are invitations, errors are calm and
  blameless, success states name what the hero achieved. (See the emotional beats
  catalogue in the canonical reference.)

> **Restraint rule (inherited from the canonical framework).** Narrative voice serves the
> user's goal — it never overrides clarity, speed, or accessibility. Don't manufacture
> false stakes, don't bury critical information for "drama," keep skip paths in onboarding,
> and honor `prefers-reduced-motion` for any motion that carries the story.

### Step 7: Trend-Aware Positioning

Position the brand relative to current design trends:

- **Adopt**: Which trends align with the brand (e.g., glassmorphism, variable fonts)?
- **Adapt**: Which trends to use selectively (e.g., gradients for hero sections only)?
- **Avoid**: Which trends conflict with brand identity (e.g., brutalism for a luxury brand)?
- **Timeless**: Which elements should resist trend cycles (e.g., typography, logo)?

### Step 8: Token Output

Generate the complete design token JSON/CSS for integration:

```json
{
  "colors": {
    "primary": { "hsl": "222.2 47.4% 11.2%", "hex": "#0f172a" },
    "primary-foreground": { "hsl": "210 40% 98%", "hex": "#f8fafc" }
  },
  "typography": {
    "font-sans": "'Inter', system-ui, sans-serif",
    "font-mono": "'JetBrains Mono', monospace"
  },
  "spacing": { "unit": "4px", "scale": "0.5-24" }
}
```

### Step 9: Brand Book

Generate a brand book using the template in `references/brand-book-template.md`.

## Full References

- `references/brand-book-template.md` — Complete brand book markdown structure
- `references/color-theory.md` — Color psychology and palette generation methods
