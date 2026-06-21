# Figma Auto Layout → CSS/Tailwind Mapping

Complete property mapping table for translating Figma Auto Layout to CSS and Tailwind CSS.

---

## Layout Direction

| Figma | CSS | Tailwind |
|-------|-----|----------|
| Auto Layout: Horizontal | `display: flex; flex-direction: row` | `flex flex-row` |
| Auto Layout: Vertical | `display: flex; flex-direction: column` | `flex flex-col` |
| Wrap | `flex-wrap: wrap` | `flex-wrap` |

---

## Spacing (Gap)

| Figma Gap | CSS | Tailwind |
|-----------|-----|----------|
| 0 | `gap: 0` | `gap-0` |
| 2px | `gap: 2px` | `gap-0.5` |
| 4px | `gap: 4px` | `gap-1` |
| 8px | `gap: 8px` | `gap-2` |
| 12px | `gap: 12px` | `gap-3` |
| 16px | `gap: 16px` | `gap-4` |
| 20px | `gap: 20px` | `gap-5` |
| 24px | `gap: 24px` | `gap-6` |
| 32px | `gap: 32px` | `gap-8` |
| 40px | `gap: 40px` | `gap-10` |
| 48px | `gap: 48px` | `gap-12` |
| 64px | `gap: 64px` | `gap-16` |

---

## Padding

### Uniform Padding
| Figma Padding | CSS | Tailwind |
|---------------|-----|----------|
| 4px all | `padding: 4px` | `p-1` |
| 8px all | `padding: 8px` | `p-2` |
| 12px all | `padding: 12px` | `p-3` |
| 16px all | `padding: 16px` | `p-4` |
| 20px all | `padding: 20px` | `p-5` |
| 24px all | `padding: 24px` | `p-6` |
| 32px all | `padding: 32px` | `p-8` |

### Independent Padding
| Figma | CSS | Tailwind |
|-------|-----|----------|
| Top: 16px | `padding-top: 16px` | `pt-4` |
| Right: 16px | `padding-right: 16px` | `pr-4` |
| Bottom: 16px | `padding-bottom: 16px` | `pb-4` |
| Left: 16px | `padding-left: 16px` | `pl-4` |
| Horizontal: 16px | `padding-left: 16px; padding-right: 16px` | `px-4` |
| Vertical: 16px | `padding-top: 16px; padding-bottom: 16px` | `py-4` |

---

## Alignment

### Primary Axis (Main Axis)

| Figma Alignment | CSS | Tailwind |
|----------------|-----|----------|
| Pack: Start | `justify-content: flex-start` | `justify-start` |
| Pack: Center | `justify-content: center` | `justify-center` |
| Pack: End | `justify-content: flex-end` | `justify-end` |
| Space between | `justify-content: space-between` | `justify-between` |
| Space around | `justify-content: space-around` | `justify-around` |
| Space evenly | `justify-content: space-evenly` | `justify-evenly` |

### Counter Axis (Cross Axis)

| Figma Alignment | CSS | Tailwind |
|----------------|-----|----------|
| Align: Start | `align-items: flex-start` | `items-start` |
| Align: Center | `align-items: center` | `items-center` |
| Align: End | `align-items: flex-end` | `items-end` |
| Align: Stretch | `align-items: stretch` | `items-stretch` |
| Align: Baseline | `align-items: baseline` | `items-baseline` |

---

## Sizing

### Width

| Figma Sizing | CSS | Tailwind |
|-------------|-----|----------|
| Fixed: Xpx | `width: Xpx` | `w-[Xpx]` or token |
| Fill container | `flex: 1; width: 100%` | `flex-1 w-full` |
| Hug contents | `width: auto` | `w-auto` |

### Height

| Figma Sizing | CSS | Tailwind |
|-------------|-----|----------|
| Fixed: Xpx | `height: Xpx` | `h-[Xpx]` or token |
| Fill container | `flex: 1; height: 100%` | `flex-1 h-full` |
| Hug contents | `height: auto` | `h-auto` |

### Min/Max Constraints

| Figma | CSS | Tailwind |
|-------|-----|----------|
| Min width: 200px | `min-width: 200px` | `min-w-[200px]` |
| Max width: 600px | `max-width: 600px` | `max-w-[600px]` or `max-w-xl` |
| Min height: 44px | `min-height: 44px` | `min-h-[44px]` |

---

## Overflow

| Figma | CSS | Tailwind |
|-------|-----|----------|
| Clip content | `overflow: hidden` | `overflow-hidden` |
| Scroll | `overflow: auto` | `overflow-auto` |
| Visible | `overflow: visible` | `overflow-visible` |

---

## Border Radius

| Figma Radius | CSS | Tailwind |
|-------------|-----|----------|
| 0 | `border-radius: 0` | `rounded-none` |
| 2px | `border-radius: 2px` | `rounded-sm` |
| 4px | `border-radius: 4px` | `rounded` |
| 6px | `border-radius: 6px` | `rounded-md` |
| 8px | `border-radius: 8px` | `rounded-lg` |
| 12px | `border-radius: 12px` | `rounded-xl` |
| 16px | `border-radius: 16px` | `rounded-2xl` |
| 9999px | `border-radius: 9999px` | `rounded-full` |

### Individual Corners
| Figma | CSS | Tailwind |
|-------|-----|----------|
| Top-left: 8px | `border-top-left-radius: 8px` | `rounded-tl-lg` |
| Top-right: 8px | `border-top-right-radius: 8px` | `rounded-tr-lg` |
| Bottom-left: 8px | `border-bottom-left-radius: 8px` | `rounded-bl-lg` |
| Bottom-right: 8px | `border-bottom-right-radius: 8px` | `rounded-br-lg` |

---

## Effects → Shadows

| Figma Shadow | CSS | Tailwind |
|-------------|-----|----------|
| 0 1px 2px rgba(0,0,0,0.05) | `box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05)` | `shadow-sm` |
| 0 1px 3px rgba(0,0,0,0.1) | `box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1)` | `shadow` |
| 0 4px 6px rgba(0,0,0,0.1) | `box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1)` | `shadow-md` |
| 0 10px 15px rgba(0,0,0,0.1) | `box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1)` | `shadow-lg` |
| 0 20px 25px rgba(0,0,0,0.1) | `box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1)` | `shadow-xl` |
| 0 25px 50px rgba(0,0,0,0.25) | `box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25)` | `shadow-2xl` |

---

## Typography

| Figma Property | CSS | Tailwind |
|---------------|-----|----------|
| Font family: Inter | `font-family: 'Inter', sans-serif` | `font-sans` |
| Size: 12px | `font-size: 12px` | `text-xs` |
| Size: 14px | `font-size: 14px` | `text-sm` |
| Size: 16px | `font-size: 16px` | `text-base` |
| Size: 18px | `font-size: 18px` | `text-lg` |
| Size: 20px | `font-size: 20px` | `text-xl` |
| Size: 24px | `font-size: 24px` | `text-2xl` |
| Size: 30px | `font-size: 30px` | `text-3xl` |
| Size: 36px | `font-size: 36px` | `text-4xl` |
| Weight: 300 | `font-weight: 300` | `font-light` |
| Weight: 400 | `font-weight: 400` | `font-normal` |
| Weight: 500 | `font-weight: 500` | `font-medium` |
| Weight: 600 | `font-weight: 600` | `font-semibold` |
| Weight: 700 | `font-weight: 700` | `font-bold` |
| Line height: 1.25 | `line-height: 1.25` | `leading-tight` |
| Line height: 1.5 | `line-height: 1.5` | `leading-normal` |
| Line height: 1.625 | `line-height: 1.625` | `leading-relaxed` |
| Letter spacing: -0.02em | `letter-spacing: -0.02em` | `tracking-tight` |
| Letter spacing: 0 | `letter-spacing: 0` | `tracking-normal` |
| Letter spacing: 0.05em | `letter-spacing: 0.05em` | `tracking-wide` |
| Text align: left | `text-align: left` | `text-left` |
| Text align: center | `text-align: center` | `text-center` |
| Text align: right | `text-align: right` | `text-right` |

---

## Position and Constraints

| Figma | CSS | Tailwind |
|-------|-----|----------|
| Absolute position | `position: absolute` | `absolute` |
| Constraints: Top + Left | `top: Xpx; left: Xpx` | `top-X left-X` |
| Constraints: Center | `top: 50%; left: 50%; transform: translate(-50%, -50%)` | `top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2` |
| Fixed on scroll | `position: fixed` | `fixed` |
| Sticky on scroll | `position: sticky` | `sticky` |
