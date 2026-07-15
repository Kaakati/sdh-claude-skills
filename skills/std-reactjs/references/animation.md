# Animation (Framer Motion)

Load-bearing rules restated (hold even if you read nothing else):

1. **Framer Motion is the animation library.** No CSS keyframe libraries, no GSAP, no
   react-spring.
2. **Every animation must respect `prefers-reduced-motion`.** This is a WCAG obligation, not a
   nicety. Use `useReducedMotion()`.
3. **Animate `transform` and `opacity` only** — they run on the compositor and never trigger
   layout.
4. **It is ~35KB gzip.** Don't pull it into a route that only needs a hover colour change.

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
// src/components/motion/FadeIn.tsx  ✅
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
// src/components/layouts/AppLayout.tsx
import { Suspense } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
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

This is the one layout-level `<Suspense>` that every lazy page route falls back to — see
`references/routing-and-code-split.md`.

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
      className="overflow-hidden border-b border-slate-200 dark:border-slate-800"
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
animation. When a route does need it, it can share a `manualChunks` vendor entry — see
`references/routing-and-code-split.md`.
