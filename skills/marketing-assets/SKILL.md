---
name: marketing-assets
description: |
  Marketing asset creation with platform ad specs, email templates, landing page
  architecture, and social content planning. Covers Google, Meta, TikTok, LinkedIn
  ad formats and copy frameworks.
  Triggers on "marketing assets", "ad copy", "landing page", "email template",
  "social media content", "ad campaign", "marketing material", "content calendar",
  "storytelling", "narrative UX", or "StoryBrand".
model: sonnet
---

# Marketing Asset Factory

Template-driven workflow for creating marketing assets with platform-specific specifications, copy frameworks, and content planning.

## When to Apply

Use this skill when:
- Creating digital advertising assets (specs, copy, targeting)
- Designing email marketing templates
- Planning landing page architecture
- Building a social media content calendar
- Generating marketing copy for product launches

## Platform Ad Specifications

Reference `references/platform-specs.md` for complete dimension and format specifications.

### Platform Quick Reference

| Platform | Key Formats | Character Limits |
|----------|-------------|-----------------|
| Google Ads | Search (text), Display (banner), YouTube (video) | Headline: 30 chars, Description: 90 chars |
| Meta (Facebook/Instagram) | Feed, Stories, Reels, Carousel | Primary: 125 chars, Headline: 40 chars |
| TikTok | In-feed, TopView, Spark Ads | Description: 100 chars |
| LinkedIn | Single image, Carousel, Video, Text | Intro: 150 chars, Headline: 70 chars |

## Ad Copy Framework

### AIDA Structure
For each ad, follow the AIDA framework:

1. **Attention**: Hook that stops the scroll (question, statistic, bold claim)
2. **Interest**: Elaborate on the problem or opportunity
3. **Desire**: Show the transformation or benefit
4. **Action**: Clear CTA with urgency or value proposition

### Copy Variants
Generate 3 variants for each ad:

| Variant | Approach | Example |
|---------|----------|---------|
| **Benefit-led** | Lead with outcome | "Save 10 hours/week on reporting" |
| **Problem-led** | Lead with pain point | "Tired of manual spreadsheet updates?" |
| **Social proof** | Lead with credibility | "Join 50,000+ teams who automated reporting" |

### CTA Patterns
| Goal | CTA Text | Color |
|------|----------|-------|
| Sign up | "Get Started Free" | Primary |
| Learn more | "See How It Works" | Secondary |
| Purchase | "Buy Now — 30% Off" | Primary |
| Trial | "Start 14-Day Free Trial" | Primary |
| Demo | "Book a Demo" | Secondary |

## Email Template Architecture

### Structural Template
```
┌─────────────────────────────┐
│ [Logo]            [View web] │
├─────────────────────────────┤
│ [Hero Image/Banner]         │
├─────────────────────────────┤
│ [Preheader: 85-100 chars]   │
│                             │
│ Hi {first_name},            │
│                             │
│ [Opening: 1-2 sentences]    │
│                             │
│ [Body: 3-5 short paragraphs]│
│                             │
│ ┌─────────────────────────┐ │
│ │    [Primary CTA]        │ │
│ └─────────────────────────┘ │
│                             │
│ [Closing: 1 sentence]       │
│ {sender_name}, {title}      │
├─────────────────────────────┤
│ [Footer: Unsubscribe, legal]│
└─────────────────────────────┘
```

### Email Types
| Type | Subject Line Pattern | Content Focus |
|------|---------------------|---------------|
| Welcome | "Welcome to {Product} — here's what's next" | Value prop, first steps |
| Onboarding | "Step {N}: {Action} to get more from {Product}" | Feature tutorial, CTA |
| Announcement | "New: {Feature} is here" | Feature benefits, try now |
| Re-engagement | "We miss you, {name}" | Value reminder, incentive |
| Transactional | "Your {action} was successful" | Confirmation, next steps |

### Email Best Practices
- **Width**: 600px maximum for email clients
- **Images**: Include `alt` text; design for images-off
- **CTA button**: Minimum 44px height, high contrast, single primary CTA
- **Mobile**: 50%+ opens are mobile; stack columns, increase font to 16px+
- **Subject line**: 40-60 characters, front-load key info
- **Preheader**: 85-100 characters, complement (don't repeat) subject

## Landing Page Architecture

### Above-the-Fold Structure
```
┌─────────────────────────────────────┐
│ [Nav: Logo | Links | CTA]           │
├──────────────────┬──────────────────┤
│                  │                  │
│ [Headline]       │ [Hero Image/    │
│ [Subheadline]    │  Product Shot/  │
│                  │  Video]         │
│ [Primary CTA]    │                  │
│ [Social proof]   │                  │
│                  │                  │
└──────────────────┴──────────────────┘
```

### Section Sequence
1. **Hero**: Headline + subheadline + CTA + social proof (above the fold)
2. **Problem**: Paint the pain point (3 pain points with icons)
3. **Solution**: How the product solves it (feature highlights with screenshots)
4. **Social proof**: Testimonials, logos, stats, case studies
5. **Features**: Detailed feature grid or comparison table
6. **Pricing**: Plans with recommended option highlighted (if applicable)
7. **FAQ**: Address top 5-7 objections
8. **Final CTA**: Repeat hero CTA with urgency element

### Landing Page Rules
- **One CTA per page**: Every CTA points to the same action
- **F-pattern layout**: Important content top-left and along left edge
- **Load time**: Under 3 seconds (optimize images, defer scripts)
- **Mobile-first**: Responsive design, thumb-friendly CTAs
- **Trust signals**: Security badges, review scores, customer logos

## Storytelling Landing Pages (StoryBrand SB7)

A landing page is the most literal storytelling application: it walks one reader through a
narrative from headline to final CTA. Where the architecture above defines the *structural*
sections, this layer defines the *narrative* purpose of each one. The user is the **hero**;
the product is the **guide**. Copy is about the user's goal and obstacle, not the feature set.

> Canonical framework: `skills/ui-ux-patterns/references/storytelling-ui.md` (single source of
> truth for narrative arc, StoryBrand SB7, emotional beats, pacing, and the scored review
> checklist). Read it before designing a story-driven page.

### SB7 beats mapped to landing-page sections

Map Donald Miller's StoryBrand (SB7) beats onto the existing section sequence:

| SB7 beat | Landing-page section | What the section must do |
|----------|---------------------|--------------------------|
| 1. **Character** (a want) | Hero headline | Name the user's goal in their words ("Ship to any region in minutes"), not the product's spec sheet |
| 2. **Problem** (external + internal + philosophical) | Hero subheadline + Problem section | Name the pain they *feel* ("Manual deploys eat your Fridays"), not just the technical gap |
| 3. **Guide** (empathy + authority) | Solution intro | Show you understand ("We've shipped to 30 regions too") **and** are competent (results, credentials) |
| 4. **Plan** | "How it works" — a **3-step plan** | Reduce perceived effort to three simple steps; make the path feel inevitable |
| 5. **Call to Action** | Primary CTA (+ secondary) | One **direct** CTA (Start free) + one **transitional** CTA (See how it works / Read the guide) |
| 6. **Avoid Failure** (stakes) | Stakes line near CTA | Make tangible what they lose by not acting — used *sparingly*, one line, never fear-mongering |
| 7. **Success** (transformation) | Proof + Success-vision section | Proof (testimonials, logos, metrics) backs the promise; success vision paints life *after* |

### Narrative arc for scroll order

The scroll itself is the arc — *hook → middle → resolution*, no dead ends. Annotate the
section sequence (from Landing Page Architecture above) with its narrative role:

| Scroll order | Section | Narrative role |
|--------------|---------|----------------|
| 1 | Hero | **Hook / setup** — names want + problem, hero (user) and guide (product) established |
| 2 | Problem | **Rising tension** — make the pain vivid and shared |
| 3 | Solution | **The guide steps in** — empathy + authority |
| 4 | Social proof | **Proof the guide can be trusted** — early authority before the plan |
| 5 | Features | **The plan in detail** — capabilities framed as steps toward the user's goal |
| 6 | Pricing | **Lowering the cost of action** |
| 7 | FAQ | **Removing the last obstacles** — objection handling |
| 8 | Final CTA | **Resolution + success vision** — repeat the direct CTA, paint the transformed after |

Keep the single-CTA rule from Landing Page Architecture: every direct CTA points to the same
action; transitional CTAs (See how it works) may differ but never compete with the direct one.

### Scrollytelling pacing

For product walkthroughs and data-story pages, pace the reveal so understanding is *earned*
section by section rather than dumped at once (progressive disclosure applied to scroll):

- **Scroll-driven reveals** — sections animate in as they enter the viewport. Web: Framer
  Motion `whileInView` (Next.js/Vite + Tailwind) backed by `IntersectionObserver`.
- **Continuity / shared-element** — carry a visual thread between beats (a product shot that
  travels and reframes from hero to feature) with Framer Motion `layoutId`. Mobile equivalents
  use React Native + Reanimated.
- **One idea per beat** — each scroll stop delivers a single point; don't stack three claims.
- **Restraint** — never withhold critical info (price, what it does) for drama, always keep a
  skip path to the CTA, and gate all non-essential motion behind `prefers-reduced-motion`.
  Microcopy and CTA labels are i18n-keyed.

### Story-driven vs feature-led copy

Lead with the user's transformation, not the capability. This complements the AIDA copy
variants above (the **problem-led** and **benefit-led** variants are the story-driven framings):

| Feature-led ❌ | Story-driven (user as hero) ✅ |
|----------------|-------------------------------|
| "Multi-region deployment support." | "Ship to your users anywhere — we handle the regions." |
| "Automated reporting engine with 40+ integrations." | "Get your Fridays back — reports build themselves." |
| "Enterprise-grade SSO and RBAC." | "Onboard your whole team in one click, lock down access in another." |
| "Real-time analytics dashboard." | "Know what changed the moment it changes." |
| Hero: "The all-in-one platform for X." | Hero: "Stop wrestling with X. Start shipping." |

Run the page through the **Storytelling review checklist** (0–2 each, /16: arc, hero framing,
pacing, first-value speed, emotional beats, continuity, resolution, restraint) from the
canonical reference. Aim for ≥13.

## Social Content Calendar

### Weekly Template

| Day | Platform | Content Type | Theme |
|-----|----------|-------------|-------|
| Mon | LinkedIn | Educational post | Industry insight, how-to |
| Tue | Instagram | Visual/carousel | Product feature showcase |
| Wed | Twitter/X | Thread | Tips, behind-the-scenes |
| Thu | LinkedIn | Case study/testimonial | Social proof, results |
| Fri | Instagram | Reel/video | Personality, culture, fun |

### Content Pillars
Define 3-5 content pillars for consistent messaging:

| Pillar | Purpose | Example Topics |
|--------|---------|---------------|
| Educational | Establish expertise | How-tos, industry trends, best practices |
| Product | Drive awareness | Features, updates, use cases |
| Social proof | Build trust | Testimonials, case studies, stats |
| Culture | Humanize brand | Team stories, behind-the-scenes, values |
| Engagement | Build community | Polls, questions, user-generated content |

## Output Format

For each asset type, produce:

1. **Specifications**: Dimensions, format, character limits
2. **Copy**: 3 variants (benefit-led, problem-led, social proof)
3. **Visual direction**: Describe imagery, colors (from brand tokens), typography
4. **Targeting notes**: Audience, placement, objective (where applicable)

## Full References

- `references/platform-specs.md` — Complete platform dimensions and requirements
