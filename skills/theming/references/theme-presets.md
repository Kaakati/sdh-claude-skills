# Theme Presets

Three ready-to-use theme presets with complete CSS custom property definitions. Copy the relevant `:root` and `.dark` blocks into your project's token stylesheet.

Each preset includes all variables from the design token specification, ensuring full compatibility with the Tailwind configuration and component library.

---

## Corporate Preset

Professional and trustworthy. Deep blue primary, slate neutrals, system font stack, conservative sizing, subtle shadows, and small border radius.

**Personality**: Authoritative, reliable, enterprise-ready.

### Light Mode

```css
:root {
  /* ============================================
     CORPORATE PRESET -- Light Mode
     ============================================ */

  /* Surface */
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;

  /* Card */
  --card: 0 0% 100%;
  --card-foreground: 222.2 84% 4.9%;

  /* Popover */
  --popover: 0 0% 100%;
  --popover-foreground: 222.2 84% 4.9%;

  /* Core Palette */
  --primary: 222.2 47.4% 11.2%;
  --primary-foreground: 210 40% 98%;

  --secondary: 210 40% 96.1%;
  --secondary-foreground: 222.2 47.4% 11.2%;

  --accent: 210 40% 96.1%;
  --accent-foreground: 222.2 47.4% 11.2%;

  --neutral: 0 0% 46.1%;

  /* Muted */
  --muted: 210 40% 96.1%;
  --muted-foreground: 215.4 16.3% 46.9%;

  /* Semantic */
  --success: 142.1 76.2% 36.3%;
  --success-foreground: 355.7 100% 97.3%;

  --warning: 37.7 92.1% 50.2%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 84.2% 60.2%;
  --error-foreground: 0 0% 98%;

  --info: 199.4 95.5% 53.8%;
  --info-foreground: 200 100% 10%;

  /* Borders & Ring */
  --border: 214.3 31.8% 91.4%;
  --input: 214.3 31.8% 91.4%;
  --ring: 222.2 84% 4.9%;

  /* Border Radius */
  --radius: 0.375rem;

  /* Typography */
  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas,
    'Liberation Mono', monospace;
}
```

### Dark Mode

```css
.dark {
  /* ============================================
     CORPORATE PRESET -- Dark Mode
     ============================================ */

  /* Surface */
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;

  /* Card */
  --card: 222.2 84% 4.9%;
  --card-foreground: 210 40% 98%;

  /* Popover */
  --popover: 222.2 84% 4.9%;
  --popover-foreground: 210 40% 98%;

  /* Core Palette */
  --primary: 210 40% 98%;
  --primary-foreground: 222.2 47.4% 11.2%;

  --secondary: 217.2 32.6% 17.5%;
  --secondary-foreground: 210 40% 98%;

  --accent: 217.2 32.6% 17.5%;
  --accent-foreground: 210 40% 98%;

  --neutral: 0 0% 63.9%;

  /* Muted */
  --muted: 217.2 32.6% 17.5%;
  --muted-foreground: 215 20.2% 65.1%;

  /* Semantic */
  --success: 142.1 70.6% 45.3%;
  --success-foreground: 144.9 80.4% 10%;

  --warning: 43.3 96.4% 56.3%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 62.8% 30.6%;
  --error-foreground: 0 85.7% 97.3%;

  --info: 199.4 80% 46%;
  --info-foreground: 200 100% 95%;

  /* Borders & Ring */
  --border: 217.2 32.6% 17.5%;
  --input: 217.2 32.6% 17.5%;
  --ring: 212.7 26.8% 83.9%;
}
```

### Corporate Preset Characteristics

| Property | Value | Rationale |
|----------|-------|-----------|
| Primary color | Deep slate-blue (`222.2 47.4% 11.2%`) | Conveys trust, professionalism |
| Border radius | `0.375rem` (6px) | Conservative, not too rounded |
| Font stack | System fonts | Fast loading, native feel |
| Shadows | Subtle (default Tailwind scale) | Not flashy, functional depth |
| Spacing | Standard Tailwind scale | Comfortable without being generous |

---

## Modern Preset

Vibrant and energetic. Purple/violet primary, zinc neutrals, Inter font, generous spacing, medium shadows, and rounded corners.

**Personality**: Creative, contemporary, engaging.

### Light Mode

```css
:root {
  /* ============================================
     MODERN PRESET -- Light Mode
     ============================================ */

  /* Surface */
  --background: 0 0% 100%;
  --foreground: 240 10% 3.9%;

  /* Card */
  --card: 0 0% 100%;
  --card-foreground: 240 10% 3.9%;

  /* Popover */
  --popover: 0 0% 100%;
  --popover-foreground: 240 10% 3.9%;

  /* Core Palette */
  --primary: 262.1 83.3% 57.8%;
  --primary-foreground: 0 0% 100%;

  --secondary: 240 4.8% 95.9%;
  --secondary-foreground: 240 5.9% 10%;

  --accent: 240 4.8% 95.9%;
  --accent-foreground: 240 5.9% 10%;

  --neutral: 240 3.8% 46.1%;

  /* Muted */
  --muted: 240 4.8% 95.9%;
  --muted-foreground: 240 3.8% 46.1%;

  /* Semantic */
  --success: 160.1 84.1% 39.4%;
  --success-foreground: 0 0% 100%;

  --warning: 43.3 96.4% 56.3%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 72.2% 50.6%;
  --error-foreground: 0 0% 100%;

  --info: 217.2 91.2% 59.8%;
  --info-foreground: 0 0% 100%;

  /* Borders & Ring */
  --border: 240 5.9% 90%;
  --input: 240 5.9% 90%;
  --ring: 262.1 83.3% 57.8%;

  /* Border Radius */
  --radius: 0.75rem;

  /* Typography */
  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo,
    Consolas, 'Liberation Mono', monospace;
}
```

### Dark Mode

```css
.dark {
  /* ============================================
     MODERN PRESET -- Dark Mode
     ============================================ */

  /* Surface */
  --background: 240 10% 3.9%;
  --foreground: 0 0% 98%;

  /* Card */
  --card: 240 10% 3.9%;
  --card-foreground: 0 0% 98%;

  /* Popover */
  --popover: 240 10% 3.9%;
  --popover-foreground: 0 0% 98%;

  /* Core Palette */
  --primary: 263.4 70% 50.4%;
  --primary-foreground: 0 0% 100%;

  --secondary: 240 3.7% 15.9%;
  --secondary-foreground: 0 0% 98%;

  --accent: 240 3.7% 15.9%;
  --accent-foreground: 0 0% 98%;

  --neutral: 240 5% 64.9%;

  /* Muted */
  --muted: 240 3.7% 15.9%;
  --muted-foreground: 240 5% 64.9%;

  /* Semantic */
  --success: 160.1 84.1% 39.4%;
  --success-foreground: 0 0% 100%;

  --warning: 43.3 96.4% 56.3%;
  --warning-foreground: 26 83.3% 14.1%;

  --error: 0 62.8% 30.6%;
  --error-foreground: 0 85.7% 97.3%;

  --info: 217.2 91.2% 59.8%;
  --info-foreground: 0 0% 100%;

  /* Borders & Ring */
  --border: 240 3.7% 15.9%;
  --input: 240 3.7% 15.9%;
  --ring: 263.4 70% 50.4%;
}
```

### Modern Preset Characteristics

| Property | Value | Rationale |
|----------|-------|-----------|
| Primary color | Vibrant violet (`262.1 83.3% 57.8%`) | Eye-catching, creative energy |
| Border radius | `0.75rem` (12px) | Generously rounded, friendly feel |
| Font stack | Inter as primary | Modern geometric sans-serif |
| Shadows | Medium (emphasized elevation) | Clear depth hierarchy |
| Ring color | Matches primary | Focus states use brand color |
| Neutrals | Zinc scale (cool gray) | Complements purple hues |

---

## Minimal Preset

Clean and restrained. Near-black primary, pure monochrome palette, system font stack, tight spacing, minimal shadows, and sharp corners.

**Personality**: Focused, content-first, editorial.

### Light Mode

```css
:root {
  /* ============================================
     MINIMAL PRESET -- Light Mode
     ============================================ */

  /* Surface */
  --background: 0 0% 100%;
  --foreground: 0 0% 3.9%;

  /* Card */
  --card: 0 0% 100%;
  --card-foreground: 0 0% 3.9%;

  /* Popover */
  --popover: 0 0% 100%;
  --popover-foreground: 0 0% 3.9%;

  /* Core Palette */
  --primary: 0 0% 9%;
  --primary-foreground: 0 0% 98%;

  --secondary: 0 0% 96.1%;
  --secondary-foreground: 0 0% 9%;

  --accent: 0 0% 96.1%;
  --accent-foreground: 0 0% 9%;

  --neutral: 0 0% 46.1%;

  /* Muted */
  --muted: 0 0% 96.1%;
  --muted-foreground: 0 0% 45.1%;

  /* Semantic */
  --success: 142.1 76.2% 36.3%;
  --success-foreground: 0 0% 100%;

  --warning: 37.7 92.1% 50.2%;
  --warning-foreground: 0 0% 9%;

  --error: 0 84.2% 60.2%;
  --error-foreground: 0 0% 98%;

  --info: 199.4 95.5% 53.8%;
  --info-foreground: 0 0% 9%;

  /* Borders & Ring */
  --border: 0 0% 89.8%;
  --input: 0 0% 89.8%;
  --ring: 0 0% 3.9%;

  /* Border Radius */
  --radius: 0.25rem;

  /* Typography */
  --font-sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas,
    'Liberation Mono', monospace;
}
```

### Dark Mode

```css
.dark {
  /* ============================================
     MINIMAL PRESET -- Dark Mode
     ============================================ */

  /* Surface */
  --background: 0 0% 3.9%;
  --foreground: 0 0% 98%;

  /* Card */
  --card: 0 0% 3.9%;
  --card-foreground: 0 0% 98%;

  /* Popover */
  --popover: 0 0% 3.9%;
  --popover-foreground: 0 0% 98%;

  /* Core Palette */
  --primary: 0 0% 98%;
  --primary-foreground: 0 0% 9%;

  --secondary: 0 0% 14.9%;
  --secondary-foreground: 0 0% 98%;

  --accent: 0 0% 14.9%;
  --accent-foreground: 0 0% 98%;

  --neutral: 0 0% 63.9%;

  /* Muted */
  --muted: 0 0% 14.9%;
  --muted-foreground: 0 0% 63.9%;

  /* Semantic */
  --success: 142.1 70.6% 45.3%;
  --success-foreground: 0 0% 9%;

  --warning: 43.3 96.4% 56.3%;
  --warning-foreground: 0 0% 9%;

  --error: 0 62.8% 30.6%;
  --error-foreground: 0 85.7% 97.3%;

  --info: 199.4 80% 46%;
  --info-foreground: 0 0% 98%;

  /* Borders & Ring */
  --border: 0 0% 14.9%;
  --input: 0 0% 14.9%;
  --ring: 0 0% 83.1%;
}
```

### Minimal Preset Characteristics

| Property | Value | Rationale |
|----------|-------|-----------|
| Primary color | Near-black (`0 0% 9%`) | Maximum contrast, content-first |
| Border radius | `0.25rem` (4px) | Sharp, clean, editorial |
| Font stack | System fonts | Maximum performance, zero FOUT |
| Shadows | Minimal (mostly flat design) | Clean, no visual clutter |
| Neutrals | Pure gray (0 saturation) | True monochrome, no color bias |
| Spacing | Tight | Dense, information-rich layouts |

---

## Preset Comparison

| Feature | Corporate | Modern | Minimal |
|---------|-----------|--------|---------|
| Primary Hue | Blue (222) | Violet (262) | Achromatic (0) |
| Saturation | Medium (47%) | High (83%) | None (0%) |
| Border Radius | 6px | 12px | 4px |
| Font | System stack | Inter | System stack |
| Shadow Intensity | Subtle | Medium | Almost none |
| Neutral Tone | Slate (cool) | Zinc (cool) | Pure gray |
| Best For | Enterprise, finance, legal | SaaS, creative, consumer | Editorial, portfolio, docs |

## Applying a Preset

1. Copy the desired `:root` and `.dark` CSS blocks into your token stylesheet.
2. The Tailwind configuration (`@theme` or `tailwind.config.ts`) remains unchanged -- it references the CSS variables, not the values.
3. All components automatically adopt the new theme without modification.
4. Customize individual tokens as needed after applying a preset. Always update foreground pairs when changing base colors and re-validate WCAG AA contrast ratios.
