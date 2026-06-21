---
name: marketing-assets
description: |
  Marketing asset creation with platform ad specs, email templates, landing page
  architecture, and social content planning. Covers Google, Meta, TikTok, LinkedIn
  ad formats and copy frameworks.
  Triggers on "marketing assets", "ad copy", "landing page", "email template",
  "social media content", "ad campaign", "marketing material", or "content calendar".
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
