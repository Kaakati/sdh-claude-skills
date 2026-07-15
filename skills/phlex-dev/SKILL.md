---
name: phlex-dev
description: |
  Build Phlex (Ruby) view components for Rails with Atomic Design methodology,
  Tailwind CSS styling, Stimulus controllers, and Turbo integration.
  Triggers on "Phlex component", "Phlex view", "Ruby view component",
  "build a Phlex", "Rails component", or "view_template".
model: sonnet
agent: phlex-developer
context: fork
---

# Phlex Development

Build Ruby view components using Phlex with Atomic Design methodology, Tailwind CSS, Stimulus, and Turbo.

## When to Apply

Use this skill when:
- Creating new Phlex view components (any atomic level)
- Converting ERB templates to Phlex components
- Building a component library in Rails
- Adding Stimulus interactivity to Phlex components
- Integrating Turbo frames/streams with Phlex views

## Workflow

### 8-Step Component Development

1. **Analyze requirements** -- Understand what the component needs to do, its props, and behavior
2. **Determine atomic level** -- Use the decision tree to classify as atom/molecule/organism/template/page
3. **Check existing components** -- Search `backend/app/components/` and `backend/app/views/` for reusable pieces
4. **Check theming tokens** -- Verify design tokens exist for needed visual properties
5. **Create component class** -- Inherit from `Components::Base` or `Views::Base`, use `view_template`
6. **Apply Tailwind styling** -- Use token-based utility classes, `class_variants` for variants
7. **Add Stimulus controllers** -- Wire up `data-controller`, `data-action`, `data-target` attributes
8. **Test the component** -- Unit test with `Phlex::Testing::ViewHelper`

## Component Class Reference

| Method | Purpose |
|--------|---------|
| `view_template` | Main render method (replaces ERB) |
| `render ComponentClass.new(...)` | Compose child components |
| `yield` / `&block` | Accept content blocks |
| `html`, `head`, `body`, `div`, `span`, ... | HTML element methods |
| `data: { controller: "name" }` | Stimulus controller binding |

## Key Conventions

- **Props**: keyword arguments in `initialize`
- **Composition**: `render` for child components
- **Content**: `yield` or `&block` for content slots
- **Styling**: Tailwind utilities, design tokens, `class_variants`
- **Variants**: `class_variants` gem for multi-variant components
- **File limit**: 200 lines max per component

## References

- `references/phlex-patterns.md` -- Comprehensive Phlex patterns and API
- `references/component-examples.md` -- Working examples at each atomic level

### Owned by `std-phlex-conventions` (auto-loads on `**/app/components/**/*.rb`)

The two files above are worked *patterns*. These are decision-shaped, carry the bad/good pairs,
and are what the conventions actually mean — naming the skill is not the same as reading them:

- **Atoms and molecules** → `@skills/std-phlex-conventions/references/component-levels-primitives.md`
- **Organisms, templates, pages** → `@skills/std-phlex-conventions/references/component-levels-composites.md`
- **Variants, tokens, class merging (`class_variants`)** → `@skills/std-phlex-conventions/references/variants-and-styling.md`
- **Stimulus wiring** → `@skills/std-phlex-conventions/references/stimulus-wiring.md`
- **Turbo Frames and Streams** → `@skills/std-phlex-conventions/references/turbo-frames-and-streams.md`
- **Testing components** → `@skills/std-phlex-conventions/references/testing.md`

Rails backend conventions → the `std-rails-conventions` skill.

**Two token facts before you style anything.** `destructive` and `neutral` are variant **keys**,
not tokens — the registered tokens are `error` and `muted`, and a class naming an unregistered
token (`bg-destructive`) compiles to **no CSS at all**, silently: the button renders transparent
with inherited text and review cannot see it. And a `-foreground` token is contrast-verified
against its **solid** surface, so `bg-success/10 text-success-foreground` is near-white on
near-white; on a tint use `text-foreground`. The registry is
`@skills/theming/references/platform-integration.md`.
