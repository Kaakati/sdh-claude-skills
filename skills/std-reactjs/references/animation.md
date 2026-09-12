# Animation (Framer Motion)

Load-bearing rules restated (hold even if you read nothing else):

1. **Framer Motion owns house motion** — page transitions, list enter/exit, micro-interactions.
   No GSAP, no react-spring.
2. **`tw-animate-css` is allowed for one job: shadcn/ui primitives' own enter/exit animation.**
   Their `animate-in` / `fade-in-0` / `zoom-in-95` classes come from it. House components never
   use those classes — a house animation is Framer Motion or a `motion-safe:` Tailwind transition.
3. **Every animation must respect `prefers-reduced-motion`.** This is a WCAG obligation, not a
   nicety. Framer Motion: `useReducedMotion()`. shadcn primitives: the global CSS backstop, which
   is **mandatory** in any package that imports `tw-animate-css`. Chart.js:
   `animation: false` (`references/charts.md`).
4. **Animate `transform` and `opacity` only** — they run on the compositor and never trigger
   layout.
5. **Framer Motion is ~35KB gzip.** Don't pull it into a route that only needs a hover colour
   change.

---

## Decision: animating with Framer Motion

### Reduced motion — the non-negotiable

`useReducedMotion()` returns the user's OS setting and updates live.

### Bad

```tsx
// ❌ animates regardless of user preference; can trigger vestibular disorders
<motion.div
  initial={{ opacity: 0, y: 40, scale: 0.9 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  transition={{ duration: 0.6 }}
>
  {children}
</motion.div>
```

### Good

```tsx
// src/components/molecules/FadeIn/FadeIn.tsx  ✅
import { motion, useReducedMotion } from 'framer-motion';
import type { ReactNode } from 'react';

export function FadeIn({ children }: { children: ReactNode }) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: shouldReduceMotion ? 0.15 : 0.3, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
```

Reduced motion means *reduced*, not *removed*: keep the opacity cross-fade so state changes
remain perceivable; drop the translation, scale, and parallax.

---

## Decision: shadcn/ui primitives' own animation

Dialogs, sheets, dropdowns and tooltips animate with enter/exit classes from `tw-animate-css`.
Measured against the published sources: `tw-animate-css@1.4.0` contains no
`prefers-reduced-motion` rule, and none of shadcn's animated primitives use `motion-safe:` or
`motion-reduce:`. Left alone, every overlay zooms in for a user who asked the OS for no motion.

### Bad — hand-guarding the vendored primitives

```tsx
// src/components/ui/dialog.tsx  ❌ an edited copy of CLI output
className={cn('motion-safe:animate-in motion-safe:fade-in-0 motion-safe:zoom-in-95 …', className)}
```

Every primitive and every class by hand, each edit a conflict the next time `add --diff` shows an
upstream change — and one missed class removes the guarantee without a signal.

### Good — one backstop in the Tailwind entry, primitives untouched

```css
/* src/styles/index.css — the file components.json names in `tailwind.css` */
@import "tailwindcss";
@import "tw-animate-css";

/* Mandatory once tw-animate-css is imported. */
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

The block is owned by `@skills/std-design-system/references/motion.md` — change it there first.
It collapses CSS keyframes and transitions to an instant. It cannot reach JavaScript-driven
motion, so Framer Motion still needs `useReducedMotion()` and Chart.js still needs
`animation: false` — canvas animation is JavaScript. The rest of the CSS entry — tokens,
`@theme inline`, the dark variant — → `@skills/theming/references/platform-integration.md`.

---

## Decision: what may I animate?

Only **`transform`** and **`opacity`** — they run on the compositor and never trigger layout.

### Bad — animating layout properties

```tsx
<motion.div
  animate={{ width: isOpen ? 280 : 64, height: 'auto', top: y }}  // ❌ layout thrash every frame
/>
```

### Good — transform-based, or let Framer's layout engine do it

```tsx
// Option A: transform only
<motion.div
  className="w-70"
  animate={{ x: isOpen ? 0 : -216 }}
  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
/>

// Option B: `layout` prop — Framer measures and runs it as a transform (FLIP)
<motion.aside layout className={cn('shrink-0', isOpen ? 'w-70' : 'w-16')}>
  <SidebarContent collapsed={!isOpen} />
</motion.aside>
```

---

## Decision: page transitions

Requires `AnimatePresence` + a `key` that changes per route, and `mode="wait"` so the outgoing
page finishes before the incoming one mounts.

```tsx
// src/components/templates/AppLayout/AppLayout.tsx
import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';

export function AppLayout() {
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 p-6">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: shouldReduceMotion ? 0 : -8 }}
            transition={{ duration: 0.2 }}
          >
            <Suspense fallback={<PageSkeleton />}>
              <Outlet />
            </Suspense>
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
```

Without `key={location.pathname}` React reuses the same element and `AnimatePresence` never sees
an exit. Without `mode="wait"` both pages overlap mid-transition.

This is the app-level `<Suspense>` that every lazy page route falls back to; area layouts add
their own around their `<Outlet />` — see `references/routing-and-code-split.md`.

**With area layouts, key the transition inside the area (house choice).** A motion element keyed
by pathname around the *app* `<Outlet />` unmounts the whole area layout on every drill, so the
section nav exits and re-enters between a list and its detail — the one piece of chrome that is
meant to stay put. Wrap the area layout's `<Outlet />` instead, and only the page moves.

---

## Decision: list item enter/exit

```tsx
// Bad ❌ — no key on the motion element, or index as key: exits animate the wrong row
{orders.map((order, i) => (
  <motion.li key={i} exit={{ opacity: 0 }}>{order.reference}</motion.li>
))}

// Good ✅ — stable key, AnimatePresence wrapping, layout for reflow
<AnimatePresence initial={false}>
  {orders.map((order) => (
    <motion.li
      key={order.id}
      layout
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.18 }}
      className="overflow-hidden border-b border-border"
    >
      <OrderRow order={order} />
    </motion.li>
  ))}
</AnimatePresence>
```

`height: 'auto'` is the documented exception to the transform-only rule — Framer measures it and
it is the only way to collapse a row cleanly. Keep it to list rows and accordions.

---

## Bundle note

`framer-motion` is ~35KB gzip. For simple hover/press feedback, prefer a Tailwind
`transition-colors` utility over pulling `framer-motion` into a route that has no other
animation. When a route does need it, it can share the `vendor-motion` code-splitting group — see
`references/routing-and-code-split.md`.
