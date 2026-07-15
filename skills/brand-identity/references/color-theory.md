# Color Theory Reference

Color psychology and palette generation methods for brand identity creation.

---

## Color Psychology

### Primary Color Associations

| Color Family | Emotions / Associations | Industries |
|-------------|------------------------|------------|
| **Blue** | Trust, stability, professionalism, calm | Finance, healthcare, tech, enterprise |
| **Red** | Energy, urgency, passion, excitement | Food, entertainment, retail, sports |
| **Green** | Growth, health, nature, money | Finance, health, sustainability, agriculture |
| **Purple** | Luxury, creativity, wisdom, mystery | Beauty, luxury goods, education, spirituality |
| **Orange** | Friendliness, confidence, enthusiasm | Food, fitness, youth brands, SaaS |
| **Yellow** | Optimism, warmth, attention, caution | Retail, children, food, transportation |
| **Black** | Sophistication, power, elegance, authority | Luxury, fashion, automotive, premium tech |
| **White** | Purity, simplicity, cleanliness, space | Healthcare, tech, minimalist brands |
| **Pink** | Playfulness, romance, care, modernity | Beauty, wellness, fashion, food |
| **Teal** | Balance, sophistication, clarity | Healthcare, tech, wellness, finance |

### Warm vs. Cool

| Property | Warm Colors (Red-Yellow) | Cool Colors (Blue-Green) |
|----------|------------------------|-------------------------|
| Energy | High energy, active | Calm, composed |
| Distance | Feel closer, more intimate | Feel distant, expansive |
| Appetite | Stimulate appetite (food) | Suppress appetite |
| Trust | Excitement-based trust | Competence-based trust |
| Action | Urgency, impulse | Consideration, planning |

---

## Palette Generation Methods

### 1. Complementary

Two colors opposite on the color wheel. High contrast, vibrant.

```
Primary:       HSL(220, 80%, 50%)    — Blue
Complement:    HSL(40, 80%, 50%)     — Gold/Orange
Offset:        180° from primary hue
```

**Best for**: High-energy brands, CTAs that need to stand out, sports/entertainment.

### 2. Analogous

Three colors adjacent on the color wheel. Harmonious, low contrast.

```
Primary:       HSL(220, 80%, 50%)    — Blue
Analogous -1:  HSL(190, 80%, 50%)    — Teal
Analogous +1:  HSL(250, 80%, 50%)    — Indigo
Offset:        ±30° from primary hue
```

**Best for**: Serene brands, nature/wellness, editorial, cohesive designs.

### 3. Triadic

Three colors equally spaced on the color wheel. Balanced, colorful.

```
Primary:       HSL(220, 80%, 50%)    — Blue
Triadic 1:     HSL(340, 80%, 50%)    — Pink/Red
Triadic 2:     HSL(100, 80%, 50%)    — Green
Offset:        ±120° from primary hue
```

**Best for**: Playful brands, children's products, creative agencies, diverse product lines.

### 4. Split-Complementary

Primary + two colors adjacent to the complement. Versatile, less tension than complementary.

```
Primary:       HSL(220, 80%, 50%)    — Blue
Split 1:       HSL(25, 80%, 50%)     — Warm orange
Split 2:       HSL(55, 80%, 50%)     — Warm yellow
Offset:        180° ± 30° from primary hue
```

**Best for**: Most brand identities — provides contrast without the harshness of direct complements.

### 5. Monochromatic

Single hue with varying saturation and lightness. Sophisticated, cohesive.

```
Primary:       HSL(220, 80%, 30%)    — Dark blue
Mid:           HSL(220, 70%, 50%)    — Medium blue
Light:         HSL(220, 60%, 80%)    — Light blue
Offset:        Same hue, vary S and L
```

**Best for**: Premium brands, minimalist design, enterprise software, financial services.

---

## Generating Token-Ready Palettes

### From Primary to Full Palette

1. **Choose primary hue** based on brand psychology
2. **Select palette method** based on brand energy
3. **Generate core colors** (primary, secondary, accent)
4. **Derive neutrals** from primary hue:
   - Warm neutrals: Add 2-5% saturation of primary hue to grays
   - Cool neutrals: Use primary hue at 5-15% saturation, varying lightness
5. **Set semantic colors** (keep standard associations). **A lightness range is only meaningful
   once you name the foreground it carries** — these assume the usual near-white
   `*-foreground` (~`0 0% 98%`), and the caps are what 4.5:1 actually permits:

   | Token | Hue / saturation | Lightness **with a near-white foreground** |
   |---|---|---|
   | Success | HSL(142, 70-76%) | **≤ 29%** — e.g. `142 76% 28%` → 4.96:1 |
   | Error | HSL(0, 62-84%) | **≤ 48%** — e.g. `0 84% 47%` → 4.82:1 |
   | Info | HSL(199, 80-95%) | **≤ 35%** — e.g. `199 80% 35%` → 5.01:1 |

   The cap is set by the **most saturated** end of each range — higher saturation needs lower
   lightness — and it is **floored, not rounded**. Success at 76% saturation clears AA at 29.7%,
   so the published cap is 29%: rounding it to 30% yields 4.43:1, which fails. One percent.
   | Warning | HSL(38-43, 92-96%, 50-56%) | **This one takes a DARK foreground** (e.g. `38 92% 12%`). Amber at any readable lightness is ~1.9:1 against white — there is no lightness in the usable amber range that works with white text. |

   > **This table used to prescribe `success: 36-45%`, `info: 46-54%`, `error: 30-60%` with no
   > foreground named — and *the entire success and info ranges fail against a near-white
   > foreground* (best case 3.40:1 and 3.12:1). Step 6 then asked for pairs "meeting 4.5:1",
   > which steps 1-5 had already made impossible. This is not theoretical: all three presets in
   > `@skills/theming/references/theme-presets.md` were built from that recipe and **13 of their
   > pairs measured below AA** — `--success` at 2.54:1, `--info` at 2.99:1. The recipe was the
   > bug, and the palettes inherited it.

6. **Create foreground pairs** meeting WCAG 4.5:1 contrast — **by computing the ratio, not by
   judging it.** Use `contrastRatio()` from
   `@skills/std-design-system/references/defining-tokens.md` and record the measured number beside
   each pair. Nobody can eyeball a gamma-corrected luminance ratio; a mid-tone green with white
   text reads fine and measures 3:1.
7. **Generate dark mode** — **not by inverting lightness.** Inversion is a plausible-looking rule
   that produces failures: flip `success 36% → 64%` and you now have a light green that fails
   against a *light* foreground and needs a dark one, so the pair changes character rather than
   just its numbers. Dark mode is **a separate set of pairs, measured independently** — pick each
   surface for the dark background, then solve its foreground and record the ratio. The dark
   halves of all three presets failed on exactly this.

### Saturation Guidelines

| Context | Saturation Range | Why |
|---------|-----------------|-----|
| Primary/accent colors | 60-90% | Strong brand presence |
| Secondary colors | 30-60% | Supporting without competing |
| Neutral backgrounds | 0-15% | Clean, unobtrusive |
| Semantic colors | 60-80% | Clear status communication |
| Muted/disabled | 10-25% | Visually recessed |

### Lightness for Accessibility

| Role | Light Mode Lightness | Dark Mode Lightness |
|------|---------------------|---------------------|
| Background | 95-100% | 4-10% |
| Foreground (text) | 4-15% | 90-98% |
| Primary actions | 30-50% | 60-80% |
| Muted text | 40-50% | 55-65% |
| Borders | 85-92% | 15-25% |

---

## Archetype-to-Color Mapping

Quick reference for selecting primary color direction based on brand archetype:

| Archetype | Recommended Hue Range | Saturation | Lightness |
|-----------|----------------------|------------|-----------|
| Innocent | 40-60° (warm yellow) or 190-210° (soft blue) | 40-60% | 50-70% |
| Sage | 200-230° (blue) | 30-50% | 40-55% |
| Explorer | 140-170° (teal/green) or 20-40° (earth) | 50-70% | 35-50% |
| Ruler | 220-240° (navy) or 0° (deep red) | 40-60% | 15-30% |
| Creator | 0-30° (coral/orange) or 260-290° (purple) | 60-80% | 45-60% |
| Caregiver | 150-180° (soft green) or 200-220° (calm blue) | 30-50% | 50-65% |
| Magician | 260-290° (purple) or 200-220° (electric blue) | 60-80% | 40-55% |
| Hero | 0-20° (red) or 30-50° (orange) | 70-90% | 40-55% |
| Outlaw | 0-10° (red) or 0° (black) | 80-100% or 0% | 20-40% |
| Jester | 30-60° (orange/yellow) or 280-320° (magenta) | 70-90% | 50-65% |
| Lover | 330-350° (pink/rose) or 280-300° (lavender) | 50-70% | 40-60% |
| Everyman | 200-220° (blue) or 100-130° (green) | 30-50% | 45-55% |
