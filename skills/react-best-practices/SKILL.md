---
name: react-best-practices
description: |
  React and Next.js performance optimization with 57 rules across 8 categories.
  Use when reviewing React components for performance, optimizing bundle size,
  eliminating data fetching waterfalls, or refactoring for re-render efficiency.
  Triggers on "optimize React performance", "bundle size", "fix waterfall",
  "re-render optimization", "React best practices", or "performance review".
model: sonnet
---

# React Best Practices

Comprehensive performance optimization guide for React and Next.js applications. Contains 57 rules across 8 categories, prioritized by impact to guide automated refactoring and code generation.

## When to Apply

Reference these guidelines when:
- Writing new React components or Next.js pages
- Implementing data fetching (client or server-side)
- Reviewing code for performance issues
- Refactoring existing React/Next.js code
- Optimizing bundle size or load times

## Rule Categories by Priority

<!-- GENERATED from rules/_sections.md + the rule files on disk.
     CI (skills-lint) fails if this drifts. Edit _sections.md, not this table. -->

| # | Category | Impact | Rule prefix | Rules |
|---|---|---|---|---|
| 1 | Eliminating Waterfalls | CRITICAL | `async-` | 5 |
| 2 | Bundle Size Optimization | CRITICAL | `bundle-` | 5 |
| 3 | Server-Side Performance | HIGH | `server-` | 7 |
| 4 | Client-Side Data Fetching | MEDIUM-HIGH | `client-` | 4 |
| 5 | Re-render Optimization | MEDIUM | `rerender-` | 12 |
| 6 | Rendering Performance | MEDIUM | `rendering-` | 9 |
| 7 | JavaScript Performance | LOW-MEDIUM | `js-` | 12 |
| 8 | Advanced Patterns | LOW | `advanced-` | 3 |

## Quick Reference

### 1. Eliminating Waterfalls (CRITICAL)

*Waterfalls are the #1 performance killer. Each sequential await adds full network latency. Eliminating them yields the largest gains.*

- `async-api-routes` - Start promises early, await late in API routes
- `async-defer-await` - Move await into branches where actually used
- `async-dependencies` - Use better-all for partial dependencies
- `async-parallel` - Use Promise.all() for independent operations
- `async-suspense-boundaries` - Use Suspense to stream content

### 2. Bundle Size Optimization (CRITICAL)

*Reducing initial bundle size improves Time to Interactive and Largest Contentful Paint.*

- `bundle-barrel-imports` - Import directly, avoid barrel files
- `bundle-conditional` - Load modules only when feature is activated
- `bundle-defer-third-party` - Load analytics/logging after hydration
- `bundle-dynamic-imports` - Use next/dynamic for heavy components
- `bundle-preload` - Preload on hover/focus for perceived speed

### 3. Server-Side Performance (HIGH)

*Optimizing server-side rendering and data fetching eliminates server-side waterfalls and reduces response times.*

- `server-after-nonblocking` - Use after() for non-blocking operations
- `server-auth-actions` - Authenticate server actions like API routes
- `server-cache-lru` - Use LRU cache for cross-request caching
- `server-cache-react` - Use React.cache() for per-request deduplication
- `server-dedup-props` - Avoid duplicate serialization in RSC props
- `server-parallel-fetching` - Restructure components to parallelize fetches
- `server-serialization` - Minimize data passed to client components

### 4. Client-Side Data Fetching (MEDIUM-HIGH)

*Automatic deduplication and efficient data fetching patterns reduce redundant network requests.*

- `client-event-listeners` - Deduplicate global event listeners
- `client-localstorage-schema` - Version and minimize localStorage data
- `client-passive-event-listeners` - Use passive listeners for scroll
- `client-swr-dedup` - Use SWR for automatic request deduplication

### 5. Re-render Optimization (MEDIUM)

*Reducing unnecessary re-renders minimizes wasted computation and improves UI responsiveness.*

- `rerender-defer-reads` - Don't subscribe to state only used in callbacks
- `rerender-dependencies` - Use primitive dependencies in effects
- `rerender-derived-state` - Subscribe to derived booleans, not raw values
- `rerender-derived-state-no-effect` - Derive state during render, not effects
- `rerender-functional-setstate` - Use functional setState for stable callbacks
- `rerender-lazy-state-init` - Pass function to useState for expensive values
- `rerender-memo` - Extract expensive work into memoized components
- `rerender-memo-with-default-value` - Hoist default non-primitive props
- `rerender-move-effect-to-event` - Put interaction logic in event handlers
- `rerender-simple-expression-in-memo` - Avoid memo for simple primitives
- `rerender-transitions` - Use startTransition for non-urgent updates
- `rerender-use-ref-transient-values` - Use refs for transient frequent values

### 6. Rendering Performance (MEDIUM)

*Optimizing the rendering process reduces the work the browser needs to do.*

- `rendering-activity` - Use Activity component for show/hide
- `rendering-animate-svg-wrapper` - Animate div wrapper, not SVG element
- `rendering-conditional-render` - Use ternary, not && for conditionals
- `rendering-content-visibility` - Use content-visibility for long lists
- `rendering-hoist-jsx` - Extract static JSX outside components
- `rendering-hydration-no-flicker` - Use inline script for client-only data
- `rendering-hydration-suppress-warning` - Suppress expected mismatches
- `rendering-svg-precision` - Reduce SVG coordinate precision
- `rendering-usetransition-loading` - Prefer useTransition for loading state

### 7. JavaScript Performance (LOW-MEDIUM)

*Micro-optimizations for hot paths can add up to meaningful improvements.*

- `js-batch-dom-css` - Group CSS changes via classes or cssText
- `js-cache-function-results` - Cache function results in module-level Map
- `js-cache-property-access` - Cache object properties in loops
- `js-cache-storage` - Cache localStorage/sessionStorage reads
- `js-combine-iterations` - Combine multiple filter/map into one loop
- `js-early-exit` - Return early from functions
- `js-hoist-regexp` - Hoist RegExp creation outside loops
- `js-index-maps` - Build Map for repeated lookups
- `js-length-check-first` - Check array length before expensive comparison
- `js-min-max-loop` - Use loop for min/max instead of sort
- `js-set-map-lookups` - Use Set/Map for O(1) lookups
- `js-tosorted-immutable` - Use toSorted() for immutability

### 8. Advanced Patterns (LOW)

*Advanced patterns for specific cases that require careful implementation.*

- `advanced-event-handler-refs` - Store event handlers in refs
- `advanced-init-once` - Initialize app once per app load
- `advanced-use-latest` - useLatest for stable callback refs

## How to Use

Read individual rule files for detailed explanations and code examples:

```
rules/async-parallel.md
rules/bundle-barrel-imports.md
```

Each rule file contains:
- Brief explanation of why it matters
- Incorrect code example with explanation
- Correct code example with explanation
- Additional context and references

## Deep guides (read on demand, do not preload)

Every rule id listed above maps to a self-contained file at `rules/<rule-id>.md`, each with its
own bad/good code pair.

**Read only the rule file matching your task** — not the set:

```
rules/<rule-id>.md
```

Loading one ~60-line rule beats skimming a compiled monolith. Do not preload the directory.

### Which React am I writing for?

**Check before applying a version-specific rule** — this repo pins React unevenly, and a rule
written for the wrong major is worse than no rule:

| Platform | React version this repo pins |
|---|---|
| **Next.js (App Router)** | **19 minimum** — `std-nextjs` states it |
| **ReactJS (Vite SPA)** | *not pinned anywhere* — read the project's `package.json` |
| **React Native** | *not pinned anywhere* — and RN's React lags web, so do not assume the web answer |

Two rules here turn on it. `rerender-memo` notes that **React Compiler makes manual `memo()`/
`useMemo()` unnecessary** — true only where the Compiler is actually enabled, which is a build
decision, not a React version. And `/composition-patterns` carries `react19-no-forwardref`
(`ref` as a plain prop; `use()` over `useContext()`), which its own rule file flags **"React 19+
only — skip this if you're on React 18 or earlier."** That hedge exists because the repo does not
say. Confirm the major from `package.json` rather than from this table's Next.js row.

### Owned elsewhere

These rules are about **performance and re-render behaviour**. The stack conventions — which
library, which layer, what state goes where — are owned and **auto-load** on the files you edit:

- **`std-reactjs`** (Vite SPA) → state placement (Zustand vs TanStack Query vs local), data
  fetching, routing and the **300KB initial-JS budget** enforced by `chunkSizeWarningLimit`, forms,
  testing, animation, charts: `@skills/std-reactjs/references/state-placement.md`,
  `@skills/std-reactjs/references/routing-and-code-split.md`
- **`std-nextjs`** (App Router) → the Server/Client boundary is the first performance decision on
  that platform, and it is not a re-render question: `@skills/std-nextjs/references/rendering.md`
- **`/composition-patterns`** → compound components, context, and the React 19 APIs
