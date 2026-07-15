---
name: requirements-consultant
description: >-
  Clarify vague requirements, discover hidden assumptions, and produce scoped user stories
  with acceptance criteria. Use when requirements are ambiguous, incomplete, or when starting
  a new feature, epic, or project. Also trigger when someone says "what should we build",
  "scope this feature", "break this down", "write user stories", "acceptance criteria",
  "requirements gathering", "feasibility check", or mentions unclear specifications.
agent: requirements-consultant
context: fork
model: opus
---

# Requirements Consultant

Partner-level requirements discovery and clarification. This skill routes to the **requirements-consultant** agent for structured analysis.

## When to Use

- Requirements are vague or one-liner descriptions
- Starting a new feature, epic, or project
- Unclear scope, hidden assumptions, or missing acceptance criteria
- Need to break an epic into implementable user stories
- Feasibility analysis required (build vs. buy vs. partner)
- Stakeholder needs conflict or are undefined

## Discovery Protocol

The agent follows a structured seven-phase protocol (Phase 0 runs only for greenfield features):

### Phase 0: Discovery — greenfield only

Feasibility against the actual stack, a compliance triage flag, and a **research brief**. The
agent holds `Read, Grep, Glob` and no web access, so Phase 0 deliberately emits *spike stories*
for market and competitor questions rather than answering them — a named competitor or a quoted
price from an agent that cannot open a pricing page is recalled training data, and it lands in
build/buy decisions where nobody can cheaply check it.

### Phase 1: Why — Business Objective
- What business outcome does this serve?
- How will success be measured?
- Who are the stakeholders and their priorities?

### Phase 2: What — Feature Scope
- User personas and their goals
- Core use cases (must-have) vs. enhancements (nice-to-have)
- System boundaries — what is IN scope and OUT of scope

### Phase 3: Hidden Requirements
- Edge cases and error states
- Accessibility and i18n considerations
- Performance and scalability expectations
- Security and compliance requirements
- Data migration or backward compatibility needs

### Phase 4: Assumptions
- Technology constraints within the stack (Rails, React Native, Vite SPA, Next.js)
- Third-party dependencies and API availability
- Data availability and quality assumptions
- Timeline and resource assumptions

### Phase 5: Architecture Proposal
- Tech stack alignment and component selection
- Service boundaries and data flow
- Integration points with existing systems
- Spike stories for unknowns

### Phase 6: Delivery Plan
- Phased user stories: MVP → Enhancements → Polish
- Complexity ratings (S/M/L/XL) per story
- Risk and dependency map
- Sprint-ready acceptance criteria

## Output Artifacts

1. **User Stories** — `As a [persona], I want [action] so that [benefit]`
2. **Acceptance Criteria** — Given/When/Then format per story
3. **Complexity Ratings** — S (1-2 pts), M (3-5 pts), L (8 pts), XL (13+ pts, consider splitting)
4. **Risk Register** — Risk, likelihood, impact, mitigation
5. **Spike Stories** — Timeboxed research tasks for unknowns
6. **Dependency Map** — Blocking and blocked-by relationships

## Quality Checklist

- [ ] Every user story has acceptance criteria
- [ ] No story exceeds 13 points — split XL stories
- [ ] Spike stories identified for all technical unknowns
- [ ] Edge cases explicitly addressed (not deferred)
- [ ] Non-functional requirements captured (performance, security, a11y, i18n)
- [ ] Dependencies between stories mapped
- [ ] MVP scope is clearly separated from enhancements

## Keywords

requirements, user stories, acceptance criteria, scope, feasibility, epic breakdown,
PRD, BRD, stakeholder, discovery, spike, estimation, MVP
