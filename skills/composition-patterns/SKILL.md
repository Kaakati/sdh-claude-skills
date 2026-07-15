---
name: composition-patterns
description: |
  React composition patterns for scalable component architecture. Use when
  refactoring components with boolean prop proliferation, building component
  libraries, designing compound components, or reviewing component APIs.
  Triggers on "composition pattern", "compound component", "boolean props",
  "component architecture", "render props", or "React 19 patterns".
model: sonnet
---

# React Composition Patterns

Composition patterns for building flexible, maintainable React components. Avoid
boolean prop proliferation by using compound components, lifting state, and
composing internals. These patterns make codebases easier for both humans and AI
agents to work with as they scale.

## When to Apply

Reference these guidelines when:

- Refactoring components with many boolean props
- Building reusable component libraries
- Designing flexible component APIs
- Reviewing component architecture
- Working with compound components or context providers

## Rule Categories by Priority

<!-- GENERATED from rules/_sections.md + the rule files on disk.
     CI (skills-lint) fails if this drifts. Edit _sections.md, not this table. -->

| # | Category | Impact | Rule prefix | Rules |
|---|---|---|---|---|
| 1 | Component Architecture | HIGH | `architecture-` | 2 |
| 2 | State Management | MEDIUM | `state-` | 3 |
| 3 | Implementation Patterns | MEDIUM | `patterns-` | 2 |
| 4 | React 19 APIs | MEDIUM | `react19-` | 1 |

## Quick Reference

### 1. Component Architecture (HIGH)

*Fundamental patterns for structuring components to avoid prop proliferation and enable flexible composition.*

- `architecture-avoid-boolean-props` - Don't add boolean props to customize
- `architecture-compound-components` - Structure complex components with shared

### 2. State Management (MEDIUM)

*Patterns for lifting state and managing shared context across composed components.*

- `state-context-interface` - Define generic interface with state, actions, meta
- `state-decouple-implementation` - Provider is the only place that knows how
- `state-lift-state` - Move state into provider components for sibling access

### 3. Implementation Patterns (MEDIUM)

*Specific techniques for implementing compound components and context providers.*

- `patterns-children-over-render-props` - Use children for composition instead
- `patterns-explicit-variants` - Create explicit variant components instead of

### 4. React 19 APIs (MEDIUM)

*React 19+ only. Don't use `forwardRef`; use `use()` instead of `useContext()`.*

- `react19-no-forwardref` - Don't use `forwardRef`; use `use()` instead of `useContext()`

## How to Use

Read individual rule files for detailed explanations and code examples:

```
rules/architecture-avoid-boolean-props.md
rules/state-context-interface.md
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
