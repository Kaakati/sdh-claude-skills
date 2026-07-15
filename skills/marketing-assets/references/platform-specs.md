# Marketing Platform Specifications

Ad format dimensions, character limits, and technical requirements by platform — **a cached copy,
not the source of truth.**

> ## These numbers expire, and this file does not know when
>
> **Undated by construction.** Nothing here records when it was last checked against a platform,
> because nothing here ever was. Ad specs are the most volatile facts in this plugin: Meta, TikTok
> and LinkedIn revise limits and formats without notice and without a changelog you can subscribe
> to, and a spec that was right when it was written stays in a file looking exactly as confident as
> one that is current.
>
> **Verify before you ship anything that depends on a number below.** The platform's own ads guide
> is the only authority — Google Ads Help, Meta's Ads Guide, TikTok Ads Manager, LinkedIn Campaign
> Manager. That check costs a minute; a wrong limit costs a truncated headline in a live campaign
> or an upload rejected at 5pm on launch day.
>
> **Do not extend this table from memory.** Asked for a platform that is not here — Pinterest,
> Snapchat, Reddit, X — you will produce a plausible number, because you have seen thousands of
> them. It will be indistinguishable from the rows below and it will be unsourced. Say the platform
> is not covered and point at its ads guide.
>
> **"Recommended" and "maximum" are different numbers**, and a table cell hides which one it is. A
> character count that triggers truncation (Meta's primary text collapsing behind *See more*) is
> not the same as one the uploader rejects. Where it matters to the campaign, confirm which you are
> reading at the source.

---

## Google Ads

### Search Ads
| Element | Specification |
|---------|--------------|
| Headlines | Up to 15 headlines, 30 characters each |
| Descriptions | Up to 4 descriptions, 90 characters each |
| Display URL path | 2 paths, 15 characters each |
| Final URL | Required, landing page URL |

### Display Ads (Responsive)
| Element | Specification |
|---------|--------------|
| Landscape image | 1200x628px (1.91:1), max 5MB |
| Square image | 1200x1200px (1:1), max 5MB |
| Logo | 1200x1200px (landscape: 1200x300px) |
| Headline | 30 characters (short), 90 characters (long) |
| Description | 90 characters |
| Business name | 25 characters |

### YouTube Video Ads
| Format | Spec | Length |
|--------|------|--------|
| Skippable in-stream | 16:9, 1920x1080 | 12s-3min recommended |
| Non-skippable | 16:9, 1920x1080 | 15-20 seconds max |
| Bumper | 16:9, 1920x1080 | 6 seconds max |
| Shorts | 9:16, 1080x1920 | 60 seconds max |

---

## Meta (Facebook / Instagram)

### Feed Ads
| Element | Facebook | Instagram |
|---------|----------|-----------|
| Image | 1080x1080px (1:1) or 1200x628px (1.91:1) | 1080x1080px (1:1) |
| Video | 1080x1080px, up to 240min | 1080x1080px, up to 60min |
| Primary text | 125 characters (before "see more") | 125 characters |
| Headline | 40 characters | 40 characters |
| Description | 25 characters | 25 characters |
| File size | Image: 30MB, Video: 4GB | Image: 30MB, Video: 4GB |

### Stories / Reels
| Element | Specification |
|---------|--------------|
| Dimensions | 1080x1920px (9:16) |
| Video length | Stories: 1-15s, Reels: up to 90s |
| Safe zone | Keep text within center 1080x1420px |
| File size | Video: 4GB max |
| Text overlay | Keep under 20% of image area |

### Carousel
| Element | Specification |
|---------|--------------|
| Cards | 2-10 cards |
| Image size | 1080x1080px (1:1) per card |
| Headline | 40 characters per card |
| Description | 25 characters per card |

---

## TikTok

### In-Feed Ads
| Element | Specification |
|---------|--------------|
| Dimensions | 1080x1920px (9:16) |
| Video length | 5-60 seconds (9-15s recommended) |
| File size | 500MB max |
| Description | 100 characters |
| CTA | Select from predefined CTAs |
| File format | MP4, MOV, MPEG, AVI |

### TopView
| Element | Specification |
|---------|--------------|
| Dimensions | 1080x1920px (9:16) |
| Video length | Up to 60 seconds |
| Sound | Required (sound-on platform) |

### Spark Ads
| Element | Specification |
|---------|--------------|
| Source | Existing organic TikTok post |
| Boosted | Amplified with targeting |
| Best for | Authentic, native-feeling content |

---

## LinkedIn

### Single Image Ads
| Element | Specification |
|---------|--------------|
| Image size | 1200x627px (1.91:1) or 1080x1080px (1:1) |
| File size | 5MB max |
| Intro text | 150 characters (before "see more") |
| Headline | 70 characters |
| Description | 100 characters |

### Carousel Ads
| Element | Specification |
|---------|--------------|
| Cards | 2-10 cards |
| Image size | 1080x1080px (1:1) per card |
| Headline | 45 characters per card |

### Video Ads
| Element | Specification |
|---------|--------------|
| Dimensions | 1920x1080 (landscape) or 1080x1080 (square) |
| Length | 15 seconds to 30 minutes (15-30s recommended) |
| File size | 200MB max |
| Captions | Strongly recommended (85% watch without sound) |

### Text Ads
| Element | Specification |
|---------|--------------|
| Image | 100x100px |
| Headline | 25 characters |
| Description | 75 characters |

---

## Cross-Platform Best Practices

### Image Optimization
| Recommendation | Details |
|---------------|---------|
| Format | WebP for web, JPEG for email, PNG for transparency |
| Compression | 80% quality JPEG typically sufficient |
| Safe zones | Keep key content away from edges (10% margin) |
| Text on images | Minimum 16px, high contrast, under 20% coverage |

### Video Best Practices
| Recommendation | Details |
|---------------|---------|
| Hook | First 3 seconds must grab attention |
| Sound | Design for sound-off (captions/text overlays) |
| CTA | Visual CTA in final 3-5 seconds |
| Branding | Logo in first 5 seconds |
| Length | Platform-optimized (6s bumper, 15s awareness, 30-60s consideration) |

### Copy Formulas

| Formula | Structure | Example |
|---------|-----------|---------|
| PAS | Problem → Agitate → Solution | "Losing leads? Every hour without follow-up costs $X. {Product} responds instantly." |
| BAB | Before → After → Bridge | "Before: manual reports. After: auto-generated dashboards. Bridge: {Product}." |
| 4U | Useful, Urgent, Unique, Ultra-specific | "Save 10 hours this week with automated reporting — only 3 spots left." |
| AIDA | Attention → Interest → Desire → Action | "Did you know 73% of teams waste 5 hours/week on reports? Here's how top teams fixed it..." |
