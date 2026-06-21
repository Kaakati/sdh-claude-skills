---
name: sprint-planner
description: Facilitate sprint planning, effort estimation, capacity planning, and backlog grooming. Use this skill whenever someone asks about sprint planning, story points, effort estimation, or says things like "plan the sprint", "estimate this work", "story points", "capacity planning", "backlog grooming", "prioritize the backlog", "what fits in this sprint", "velocity", or "sprint retrospective". Also trigger when someone mentions iteration planning, work breakdown, or release planning.
model: sonnet
---

# Sprint Planner

Facilitate sprint planning ceremonies, effort estimation, capacity planning, and backlog management for the development team.

## Sprint Planning Protocol

### Step 1: Review Previous Sprint

Before planning the next sprint, review:

1. **Velocity**: Average story points completed over last 3 sprints.
2. **Carryover**: Unfinished stories from the previous sprint (why weren't they completed?).
3. **Retrospective actions**: Are action items from the last retro being addressed?

```markdown
## Previous Sprint Summary
- **Sprint**: [Sprint Name/Number]
- **Committed**: [X] story points
- **Completed**: [Y] story points
- **Velocity trend**: [improving | stable | declining]
- **Carryover stories**: [list]
- **Blockers encountered**: [list]
```

### Step 2: Capacity Planning

Calculate team capacity for the upcoming sprint:

```markdown
## Team Capacity
| Team Member | Available Days | Capacity Factor | Effective Days |
|-------------|---------------|-----------------|----------------|
| [Name] | [X] / [Sprint Length] | [0.0-1.0] | [Result] |

**Total team capacity**: [Sum] effective days
**Capacity factor adjustments**: Holidays, PTO, on-call duty, meetings, tech debt allocation
**Recommended commitment**: [70-80%] of theoretical capacity
```

#### Capacity Factor Guide
- **1.0**: Fully available, no meetings or other obligations
- **0.8**: Standard (daily standups, sprint ceremonies, some meetings)
- **0.6**: Heavy meeting load, mentoring responsibilities
- **0.4**: On-call primary, significant non-sprint work
- **0.0**: On leave, unavailable

### Step 3: Backlog Grooming

Ensure stories are ready for sprint planning:

#### Story Readiness Checklist (Definition of Ready)
- [ ] User story follows format: "As a [role], I want [capability] so that [benefit]"
- [ ] Acceptance criteria are clear, testable, and complete
- [ ] Dependencies identified and resolved (or tracked)
- [ ] UI mockups/designs attached (for frontend stories)
- [ ] API contract defined (for backend stories)
- [ ] Data model changes identified
- [ ] Estimated by the team (story points assigned)
- [ ] Story fits within a single sprint (if not, split it)

#### Story Template
```markdown
## [TICKET-ID]: [Story Title]

**As a** [user role]
**I want** [capability]
**So that** [business value]

### Acceptance Criteria
- [ ] Given [context], when [action], then [expected result]
- [ ] Given [context], when [action], then [expected result]

### Technical Notes
- Backend: [API endpoints, service objects, migrations needed]
- Mobile: [Screens, hooks, components needed]
- Infrastructure: [Terraform changes, config updates]

### Dependencies
- Blocked by: [TICKET-ID] (if any)
- Blocks: [TICKET-ID] (if any)

### Estimate
- Story Points: [1 | 2 | 3 | 5 | 8 | 13]
- T-Shirt Size: [S | M | L | XL]
```

### Step 4: Effort Estimation

Use modified Fibonacci story points (1, 2, 3, 5, 8, 13, 21):

#### Story Point Reference

| Points | Complexity | Duration Guide | Example |
|--------|-----------|----------------|---------|
| **1** | Trivial | < 2 hours | Config change, copy update, simple bug fix |
| **2** | Small | 2-4 hours | Single endpoint CRUD, simple UI component |
| **3** | Medium-Small | 4-8 hours | Endpoint with business logic, form with validation |
| **5** | Medium | 1-2 days | Feature with multiple endpoints, complex UI flow |
| **8** | Large | 2-3 days | Multi-component feature, data migration, integration |
| **13** | Very Large | 3-5 days | Cross-cutting feature, architectural change |
| **21** | Epic | > 1 week | Must be broken down further — too large for a sprint |

#### Estimation Guidelines
- **Compare, don't calculate**: Estimate relative to a reference story the team agrees on.
- **Include everything**: Development, testing, code review, deployment verification.
- **Uncertainty adds points**: If unclear, round up. Uncertainty = risk.
- **21+ means split**: Any story estimated at 21 or above must be decomposed.
- **Spike stories**: Timeboxed research tasks. Always 3 or 5 points. Output is knowledge, not code.

### Step 5: Sprint Commitment

#### Sprint Backlog Template
```markdown
## Sprint [Number]: [Sprint Goal]
**Start**: YYYY-MM-DD | **End**: YYYY-MM-DD | **Duration**: [X] days

### Sprint Goal
[One sentence describing the sprint's primary objective]

### Committed Stories
| Priority | Ticket | Title | Points | Assignee | Status |
|----------|--------|-------|--------|----------|--------|
| P0 | PROJ-101 | [Critical story] | 5 | [Name] | To Do |
| P1 | PROJ-102 | [High priority] | 3 | [Name] | To Do |
| P2 | PROJ-103 | [Normal priority] | 8 | [Name] | To Do |

### Totals
- **Committed**: [X] story points
- **Team velocity (avg)**: [Y] story points
- **Commitment ratio**: [X/Y * 100]% (target: 80-100%)

### Risks and Dependencies
| Risk | Impact | Mitigation |
|------|--------|------------|

### Tech Debt Allocation
[10-20% of capacity reserved for tech debt, refactoring, and tooling improvements]
```

#### Commitment Guidelines
- **Never exceed velocity** by more than 10% unless the team explicitly agrees.
- **Reserve 10-20%** of capacity for tech debt, bugs, and operational work.
- **Prioritize by value**: P0 (must have) → P1 (should have) → P2 (nice to have).
- **Respect dependencies**: Do not commit to blocked stories without a resolution plan.
- **One sprint goal**: The team should be able to state the sprint's purpose in one sentence.

## Spike Stories

For uncertain or exploratory work, use timeboxed spike stories:

```markdown
## Spike: [Investigation Topic]

### Question to Answer
[What specific question or uncertainty are we resolving?]

### Timebox
[X] hours / [Y] story points (max 5 points)

### Expected Output
- [ ] Written summary of findings
- [ ] Recommendation with pros/cons
- [ ] Refined story estimates for the actual implementation
- [ ] Proof of concept (if applicable)

### Acceptance Criteria
- [ ] Question is answered with enough confidence to estimate implementation
- [ ] Findings are documented in [location]
```

## Velocity Tracking

### Sprint Velocity Report
```markdown
## Velocity Report

| Sprint | Committed | Completed | Carryover | Notes |
|--------|-----------|-----------|-----------|-------|
| Sprint N-2 | [X] | [Y] | [Z] | |
| Sprint N-1 | [X] | [Y] | [Z] | |
| Sprint N | [X] | [Y] | [Z] | |

**Average velocity**: [Mean of last 3 sprints]
**Trend**: [Improving | Stable | Declining]
**Recommended next sprint commitment**: [Average velocity * 0.85]
```

## Release Planning

Map sprints to releases for longer-term planning:

```markdown
## Release [vX.Y.Z] Plan

### Target Date: YYYY-MM-DD
### Sprints: [Sprint N] through [Sprint N+X]

### Epics and Progress
| Epic | Total Points | Completed | Remaining | Target Sprint |
|------|-------------|-----------|-----------|---------------|

### Release Risks
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|

### Release Checklist
- [ ] All stories completed and accepted
- [ ] Integration testing passed
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Stakeholder sign-off obtained
```
