---
name: react-native-best-practices
description: |
  React Native and Expo performance best practices with 36 rules across
  14 categories. Use when optimizing list performance, implementing animations
  with Reanimated, reviewing React Native code for performance, or working with
  native modules. Triggers on "React Native performance", "list optimization",
  "FlashList", "Reanimated best practices", "mobile performance", or
  "React Native best practices".
model: sonnet
---

# React Native Best Practices

Comprehensive best practices for React Native and Expo applications. Contains
36 rules across 14 categories, prioritized by impact to guide automated
refactoring and code generation.

## When to Apply

Reference these guidelines when:

- Building React Native or Expo apps
- Optimizing list and scroll performance
- Implementing animations with Reanimated
- Working with images and media
- Configuring native modules or fonts
- Structuring monorepo projects with native dependencies

## Rule Categories by Priority

<!-- GENERATED from rules/_sections.md + the rule files on disk.
     CI (skills-lint) fails if this drifts. Edit _sections.md, not this table. -->

| # | Category | Impact | Rule prefix | Rules |
|---|---|---|---|---|
| 1 | Core Rendering | CRITICAL | `rendering-` | 2 |
| 2 | List Performance | HIGH | `list-performance-` | 8 |
| 3 | Animation | HIGH | `animation-` | 3 |
| 4 | Scroll Performance | HIGH | `scroll-` | 1 |
| 5 | Navigation | HIGH | `navigation-` | 1 |
| 6 | React State | MEDIUM | `react-state-` | 3 |
| 7 | State Architecture | MEDIUM | `state-` | 1 |
| 8 | React Compiler | MEDIUM | `react-compiler-` | 2 |
| 9 | User Interface | MEDIUM | `ui-` | 9 |
| 10 | Design System | MEDIUM | `design-system-` | 1 |
| 11 | Monorepo | LOW | `monorepo-` | 2 |
| 12 | Third-Party Dependencies | LOW | `imports-` | 1 |
| 13 | JavaScript | LOW | `js-` | 1 |
| 14 | Fonts | LOW | `fonts-` | 1 |

## Quick Reference

### 1. Core Rendering (CRITICAL)

*Fundamental React Native rendering rules. Violations cause runtime crashes or broken UI.*

- `rendering-no-falsy-and` - Avoid falsy && for conditional rendering
- `rendering-text-in-text-component` - Wrap text in Text components

### 2. List Performance (HIGH)

*Optimizing virtualized lists (FlatList, LegendList, FlashList) for smooth scrolling and fast updates.*

- `list-performance-callbacks` - Stabilize callback references
- `list-performance-function-references` - Extract functions outside render
- `list-performance-images` - Optimize images in lists
- `list-performance-inline-objects` - Avoid inline style objects
- `list-performance-item-expensive` - Move expensive work outside items
- `list-performance-item-memo` - Memoize list item components
- `list-performance-item-types` - Use item types for heterogeneous lists
- `list-performance-virtualize` - Use FlashList for large lists

### 3. Animation (HIGH)

*GPU-accelerated animations, Reanimated patterns, and avoiding render thrashing during gestures.*

- `animation-derived-value` - Use useDerivedValue for computed animations
- `animation-gesture-detector-press` - Use Gesture.Tap instead of Pressable
- `animation-gpu-properties` - Animate only transform and opacity

### 4. Scroll Performance (HIGH)

*Tracking scroll position without causing render thrashing.*

- `scroll-position-no-state` - Never track scroll position in useState

### 5. Navigation (HIGH)

*Using native navigators for stack and tab navigation instead of JS-based alternatives.*

- `navigation-native-navigators` - Use native stack and native tabs over JS navigators

### 6. React State (MEDIUM)

*Patterns for managing React state to avoid stale closures and unnecessary re-renders.*

- `react-state-dispatcher` - Use dispatcher pattern for callbacks
- `react-state-fallback` - Show fallback on first render
- `react-state-minimize` - Minimize state subscriptions

### 7. State Architecture (MEDIUM)

*Ground truth principles for state variables and derived values.*

- `state-ground-truth` - State must represent ground truth

### 8. React Compiler (MEDIUM)

*Compatibility patterns for React Compiler with React Native and Reanimated.*

- `react-compiler-destructure-functions` - Destructure for React Compiler
- `react-compiler-reanimated-shared-values` - Handle shared values with compiler

### 9. User Interface (MEDIUM)

*Native UI patterns for images, menus, modals, styling, and platform-consistent interfaces.*

- `ui-expo-image` - Use expo-image for all images
- `ui-image-gallery` - Use Galeria for image lightboxes
- `ui-measure-views` - Use onLayout, not measure()
- `ui-menus` - Use native context menus
- `ui-native-modals` - Use native modals when possible
- `ui-pressable` - Use Pressable over TouchableOpacity
- `ui-safe-area-scroll` - Handle safe areas in ScrollViews
- `ui-scrollview-content-inset` - Use contentInset for headers
- `ui-styling` - Use StyleSheet.create or Nativewind

### 10. Design System (MEDIUM)

*Architecture patterns for building maintainable component libraries.*

- `design-system-compound-components` - Compound components over polymorphic children

### 11. Monorepo (LOW)

*Dependency management and native module configuration in monorepos.*

- `monorepo-native-deps-in-app` - Keep native dependencies in app package
- `monorepo-single-dependency-versions` - Use single versions across packages

### 12. Third-Party Dependencies (LOW)

*Wrapping and re-exporting third-party dependencies for maintainability.*

- `imports-design-system-folder` - Organize design system imports

### 13. JavaScript (LOW)

*Micro-optimizations like hoisting expensive object creation.*

- `js-hoist-intl` - Hoist Intl object creation

### 14. Fonts (LOW)

*Native font loading for improved performance.*

- `fonts-config-plugin` - Use config plugins for custom fonts

## How to Use

Read individual rule files for detailed explanations and code examples:

```
rules/list-performance-virtualize.md
rules/animation-gpu-properties.md
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
