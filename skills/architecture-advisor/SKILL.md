---
name: architecture-advisor
description: Evaluate architectural decisions, design system components, produce ADRs, and assess technical debt. Use this skill whenever someone asks to design a system, evaluate architecture, create an ADR, plan a large refactor, choose between technologies, or says things like "how should we architect X", "write an ADR", "evaluate this design", "what are the tradeoffs", "review the architecture", or "should we use X or Y". Also trigger for bounded context design, scalability planning, or migration strategy.
agent: architecture-advisor
context: fork
model: opus
---

# Architecture Advisor

This skill routes to the **architecture-advisor** agent — a principal software architect (Opus, plan mode) that provides strategic guidance on system design, technology evaluation, and architectural decisions.

## When to Use

- Designing new system components or services
- Evaluating technology choices (build vs. buy, library selection)
- Planning large-scale migrations or refactors
- Assessing technical debt and prioritizing remediation
- Creating Architecture Decision Records (ADRs) for `docs/adr/`
- Reviewing system design for quality attributes (scalability, maintainability, security)

## What the Agent Does

The architecture-advisor agent operates in **plan mode** — it researches the codebase, analyzes the current architecture, and presents a recommended approach for your approval before any changes are made.

1. **Understands current architecture** — reads config files, maps dependencies, reviews existing ADRs
2. **Identifies the concern** — new design, migration, scaling, tech debt
3. **Evaluates against principles** — Clean Architecture, SOLID, DDD, Twelve-Factor App
4. **Assesses quality attributes** — scalability, maintainability, testability, security, performance, reliability, observability
5. **Produces an ADR** — documents the decision with context, alternatives, consequences

## Output Format

The agent produces Architecture Decision Records in the standard ADR format:
`ADR-NNN: Title` with Status, Context, Decision, Consequences, and Alternatives Considered.

See `agents/architecture-advisor.md` for the full advisory protocol and ADR template.
