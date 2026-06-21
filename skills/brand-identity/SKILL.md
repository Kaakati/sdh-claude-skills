---
name: brand-identity
description: |
  Brand identity creation with design tokens, color psychology, typography pairing,
  and brand book generation. Covers brand archetypes, voice matrix, trend-aware
  positioning, and token output for Tailwind CSS and React Native.
  Triggers on "brand identity", "brand guidelines", "brand book", "logo usage",
  "brand colors", "brand voice", "brand archetype", or "brand system".
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
