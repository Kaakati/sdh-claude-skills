# Motion Tokens and Reduced Motion

Read this when you are **animating something** — picking a duration or easing, wiring Framer Motion,
Reanimated, or CSS transitions, or handling `prefers-reduced-motion`. Static styling does not need
this file.

Load-bearing rules restated (assume nothing else here has been read):

1. **Every animation must have a reduced-motion path.** On the web that means the `motion-safe:`
   prefix or a `useReducedMotion()` check. In React Native it means `AccessibilityInfo`. Every web
   token stylesheet also carries the global `prefers-reduced-motion` backstop, and that backstop is
   **mandatory**: it is the only path vendored shadcn/ui primitives have.
   Users with vestibular disorders are made physically ill by motion they did not opt into.
2. **Duration ceiling is 500ms.** Longer reads as sluggish, not as elegant.
3. Durations and easings come from the scale below — no `duration-[230ms]`, no invented beziers.

## Duration scale

| Token          | Duration | Usage                                 |
|----------------|----------|---------------------------------------|
| `duration-75`  | 75ms     | Instant feedback (toggle, checkbox)   |
| `duration-100` | 100ms    | Hover color changes                   |
| `duration-150` | 150ms    | Default UI interactions               |
| `duration-200` | 200ms    | Button presses, focus rings           |
| `duration-300` | 300ms    | Dropdowns, tooltips, slide-in         |
| `duration-500` | 500ms    | Page transitions, modals              |

## Easing scale

| Easing       | Curve                             | Usage                              |
|--------------|-----------------------------------|------------------------------------|
| `ease-in`    | `cubic-bezier(0.4, 0, 1, 1)`      | Elements **exiting** the viewport  |
| `ease-out`   | `cubic-bezier(0, 0, 0.2, 1)`      | Elements **entering** the viewport |
| `ease-in-out`| `cubic-bezier(0.4, 0, 0.2, 1)`    | Default for most transitions       |
| Spring       | `cubic-bezier(0.34, 1.56, 0.64, 1)` | Tactile bounce — toggles, modals |

The in/out mapping is not arbitrary: entering elements decelerate into place (`ease-out`), exiting
elements accelerate away (`ease-in`). Reversing them makes an interface feel broken in a way users
report as "laggy" without being able to say why.

---

## Decision: a CSS/Tailwind transition

### Bad — unguarded, off-scale, animating layout properties

```tsx
<div className="transition-all duration-[420ms] ease-linear hover:h-64 hover:w-96">
```

`transition-all` animates every property including layout, forcing reflow on each frame;
`duration-[420ms]` is off-scale; `ease-linear` reads mechanical; and there is no reduced-motion
guard at all.

### Good — guarded, on-scale, compositor-friendly properties

```tsx
<div className="motion-safe:transition-transform motion-safe:duration-200 motion-safe:ease-in-out hover:scale-105">
```

Animate `transform` and `opacity` — they run on the compositor and never trigger layout. Animating
`height`, `width`, `top`, or `margin` runs on the main thread and drops frames.

Tailwind v4 registers keyframe animations in the stylesheet's `@theme`, and the class is used as
`motion-safe:animate-slide-in`:

```css
/* globals.css (Next.js) or the Vite entry stylesheet */
@theme {
  --animate-slide-in: slide-in 300ms cubic-bezier(0, 0, 0.2, 1);

  @keyframes slide-in {
    from { opacity: 0; transform: translateY(-8px); }
    to { opacity: 1; transform: translateY(0); }
  }
}
```

### The global backstop (mandatory)

```css
/* same stylesheet, after the tokens */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

The duration is `0.01ms`, not `animation: none`. Radix and Base UI keep exit-animated content mounted
until `animationend` fires. A near-zero duration fires it at once, while removing the animation
changes the unmount path the primitive was written against.

**Why it is mandatory rather than a safety net:** shadcn/ui primitives animate their data-state
enter and exit through `tw-animate-css` (`animate-in`, `fade-in-0`, `zoom-in-95`). That is the one
place the house allows it; `framer-motion` stays for house page and list transitions, and one
element never gets both. Measured against the published packages, `tw-animate-css@1.4.0` ships no
`prefers-reduced-motion` or `motion-safe` rule at all. shadcn's own `tailwind.css` has exactly one,
and it only disables `.shimmer`. 39 of the 61 new-york-v4 primitives animate, and none carry
`motion-safe:`. Hand-editing `motion-safe:` into every vendored file breaks the `add --diff`
merges the files exist for, so the backstop is those primitives' reduced-motion path.

The backstop is still not a license to skip `motion-safe:` in code the house writes, and it
**cannot stop a JS-driven animation**. Framer Motion needs `useReducedMotion()` (below). Charts
animate in JS too: in Next.js, Recharts behind the shadcn chart component takes
`isAnimationActive={!reduce}` on each series (`@skills/std-shadcn-ui/references/charts.md`); Chart.js,
in the Vite SPA and in Rails Phlex views, takes `animation: false` under reduced motion
(`@skills/std-reactjs/references/charts.md`, `@skills/std-phlex-conventions/references/charts.md`).

---

## Decision: Framer Motion (Vite SPA / Next.js)

### Bad — motion regardless of preference

```tsx
import { motion } from 'framer-motion';

export function Card({ children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, ease: 'linear' }}
    >
      {children}
    </motion.div>
  );
}
```

800ms exceeds the ceiling, `linear` is off-scale, and the 40px slide will run for a user who
explicitly asked the OS for no motion.

### Good — `useReducedMotion` collapses movement, keeps the fade

```tsx
// src/components/ui/card.tsx
import { motion, useReducedMotion } from 'framer-motion';
import type { ReactNode } from 'react';

const SPRING = [0.34, 1.56, 0.64, 1] as const;
const EASE_OUT = [0, 0, 0.2, 1] as const;

export function Card({ children }: { children: ReactNode }) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={{ opacity: 0, y: reduce ? 0 : 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: reduce ? 0 : 8 }}
      transition={{ duration: reduce ? 0 : 0.3, ease: EASE_OUT }}
      className="rounded-lg border border-border bg-card p-4 text-card-foreground"
    >
      {children}
    </motion.div>
  );
}

export function Toggle({ on }: { on: boolean }) {
  const reduce = useReducedMotion();
  return (
    <span className="inline-flex h-6 w-11 items-center rounded-full bg-muted p-0.5 data-[on=true]:bg-primary" data-on={on}>
      <motion.span
        className="h-5 w-5 rounded-full bg-background shadow"
        animate={{ x: on ? 20 : 0 }}
        transition={reduce ? { duration: 0 } : { duration: 0.2, ease: SPRING }}
      />
    </span>
  );
}
```

Reduced motion means **removing movement, not removing feedback**. Keep the opacity change and the
color change; drop the translation and the bounce. Setting `duration: 0` (rather than skipping the
animation) keeps the final state correct with no special-casing.

Framer Motion is for what the house builds, such as route transitions, list reorder, and the card
above. A vendored shadcn/ui primitive keeps its `tw-animate-css` classes. Rewriting it onto
`AnimatePresence` forfeits every upstream diff for a behaviour the backstop already gives it.

---

## Decision: Reanimated (React Native)

React Native has no `motion-safe:`. Query `AccessibilityInfo` and cache it.

```tsx
// src/hooks/useReducedMotion.ts
import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

export function useReducedMotion(): boolean {
  const [reduce, setReduce] = useState(false);

  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled().then((value) => {
      if (mounted) setReduce(value);
    });
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduce);
    return () => {
      mounted = false;
      sub.remove();
    };
  }, []);

  return reduce;
}
```

```tsx
// src/components/ui/Sheet.tsx
import Animated, { useAnimatedStyle, withTiming, withSpring, Easing } from 'react-native-reanimated';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import { useTheme } from '../../theme/ThemeProvider';

export function Sheet({ open, children }: { open: boolean; children: React.ReactNode }) {
  const reduce = useReducedMotion();
  const theme = useTheme();

  const style = useAnimatedStyle(() => {
    const opacity = withTiming(open ? 1 : 0, {
      duration: reduce ? 0 : theme.duration.slow,          // 300ms
      easing: Easing.bezier(0, 0, 0.2, 1),                  // ease-out for entry
    });
    const translateY = reduce
      ? 0
      : withSpring(open ? 0 : 320, { damping: 18, stiffness: 180 });
    return { opacity, transform: [{ translateY }] };
  }, [open, reduce, theme.duration.slow]);

  return (
    <Animated.View style={[{ backgroundColor: theme.colors.card, borderRadius: theme.radius.lg }, style]}>
      {children}
    </Animated.View>
  );
}
```

Durations come from `theme.duration` — the same scale the web side gets from `duration-300`, so a
sheet and a dropdown feel like the same product.

---

## Decision: is this animation worth it at all?

Motion should communicate. Before adding it, name what it tells the user:

- **Continuity** — this new panel came *from* that button (shared position/scale).
- **Feedback** — the tap registered (75-150ms press state).
- **Status** — something is loading, arriving, or leaving.

If none of the three apply, the animation is decoration and it costs frames, battery, and — for
motion-sensitive users — comfort. Ship it static.
