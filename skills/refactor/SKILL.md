---
name: refactor
description: Safely refactor code using Fowler's patterns with test-first methodology and incremental steps. Use this skill whenever someone asks to refactor code, reduce technical debt, extract patterns, restructure modules, or says things like "refactor this", "clean up this code", "extract this into a service", "this code smells", "reduce duplication", "decompose this function", or "restructure this module". Also trigger for code smell identification, large-scale codebase transformations, or safe migration of legacy code.
agent: refactor-specialist
context: fork
argument-hint: "file path or pattern name"
model: opus
---

# Refactor

This skill routes to the **refactor-specialist** agent — a senior refactoring engineer (Opus) that transforms messy code into clean, maintainable systems without breaking existing behavior.

## When to Use

- Reducing technical debt in identified hotspots
- Extracting reusable patterns from duplicated code
- Restructuring modules that violate Single Responsibility
- Decomposing large functions (>30 lines) or classes
- Migrating legacy code to current architecture patterns
- Performing large-scale codebase transformations

## Safety Rules (Non-Negotiable)

1. **NEVER refactor without tests.** If tests do not exist, the agent writes characterization tests first.
2. **Each step is atomic.** One Extract Method, one Rename, one Move — never mixed. Safe to revert individually.
3. **Tests run after every step.** If a test fails, the change is reverted and investigated.
4. **Public API contracts are preserved** unless the explicit goal is to change them.
5. **Refactoring and feature work are never combined** in the same PR.

## What the Agent Does

1. **Identifies code smells** — Long Methods, God Objects, Feature Envy, Data Clumps, Duplicated Code, Dead Code
2. **Verifies test coverage** — runs suite, identifies gaps, writes characterization tests if needed
3. **Plans incremental steps** — ordered by risk (rename before restructure before rearchitect)
4. **Applies Fowler's patterns** — Extract Method/Class, Move Method, Replace Conditional with Polymorphism, Introduce Parameter Object
5. **Reports after each step** — what changed, why, test results

See `agents/refactor-specialist.md` for the full refactoring protocol and code smell catalog.
