# RFC Template & Guide

## Template

```markdown
# RFC-[NUMBER]: [Title — Action-Oriented, Under 10 Words]

## Metadata

| Field | Value |
|-------|-------|
| **Author** | [Name] |
| **Status** | Draft | In Review | Accepted | Rejected | Deferred | Superseded by RFC-[N] |
| **Created** | YYYY-MM-DD |
| **Review Deadline** | YYYY-MM-DD |
| **Reviewers** | [Names and roles] |
| **Related** | RFC-[N], ADR-[N], [TICKET-ID] |

## Summary

[2-3 sentences maximum. What are you proposing and why? A busy reader should understand the core proposal from this section alone.]

## Motivation

### Problem Statement

[What specific problem are we solving? Include quantitative evidence: error rates, latency numbers, developer time wasted, customer complaints, operational incidents.]

### Why Now?

[What makes this urgent or timely? A trigger event, a growth milestone, a dependency EOL, a recurring incident?]

## Current State

[How does the system work today in the area this RFC touches? Include a diagram if the data flow is non-trivial. Be specific about which components are involved.]

### Limitations of Current Approach

[What specifically fails, degrades, or causes friction with the current approach? Tie back to the problem statement with concrete examples.]

## Proposed Solution

### Overview

[High-level description of the proposed change. What changes, what stays the same.]

### Detailed Design

[Technical details. For our stack, address the relevant layers:]

#### Backend Changes (Rails)
[Controllers, services, models, serializers, jobs affected. New gems required.]

#### Frontend Changes (React Native)
[Screens, components, stores, queries affected. New packages required.]

#### Database Changes (PostgreSQL/PostGIS)
[Schema migrations, index changes, spatial considerations. Include SQL or migration snippets.]

#### Infrastructure Changes (Terraform/Docker)
[New services, configuration, environment variables.]

#### Real-Time Changes (Centrifugo/Redis)
[Channel patterns, subscription changes, cache strategy.]

### Proof of Concept

[Link to prototype branch, benchmark results, or spike findings. If no POC exists, state what would need to be validated before implementation.]

## Impact Assessment

### Stack Compatibility Checklist

- [ ] Works with Rails API-only mode and Panko serializers
- [ ] Compatible with React Native (iOS + Android)
- [ ] No breaking changes to Zustand stores or TanStack Query cache
- [ ] PostgreSQL/PostGIS migration is reversible
- [ ] Centrifugo channels and subscriptions unaffected (or migration path defined)
- [ ] Redis cache keys and Sidekiq queues compatible
- [ ] Terraform plan shows expected changes only
- [ ] Docker Compose local dev still works
- [ ] CI/CD pipeline passes without modification (or changes documented)

### Performance Impact

[Expected impact on: API response times, database query load, memory usage, bundle size, real-time latency.]

### Security Impact

[New attack surface? Authentication/authorization changes? Data exposure risk?]

## Alternatives Considered

### Alternative 1: Do Nothing

- **What happens**: [Describe the trajectory if we don't act]
- **Acceptable for**: [How long / under what conditions]
- **Breaks when**: [What trigger makes this untenable]

### Alternative 2: [Name]

- **Approach**: [Brief description]
- **Pros**: [Specific advantages]
- **Cons**: [Specific disadvantages]
- **Why not chosen**: [The decisive factor]

### Alternative 3: [Name] (if applicable)

- **Approach**: [Brief description]
- **Pros**: [Specific advantages]
- **Cons**: [Specific disadvantages]
- **Why not chosen**: [The decisive factor]

## Migration Plan

### Phase 1: [Name] — [Estimated Duration]
[What happens, who does it, rollback plan]

### Phase 2: [Name] — [Estimated Duration]
[What happens, who does it, rollback plan]

### Phase 3: Cleanup — [Estimated Duration]
[Remove old code, update docs, close migration tracking ticket]

### Done Criteria
- [ ] [Specific, measurable criteria that define "migration complete"]

### Estimated Total Effort
[X developer-days across Y phases]

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| [Risk 1] | Low/Med/High | Low/Med/High | [How we prevent or handle it] |
| [Risk 2] | Low/Med/High | Low/Med/High | [How we prevent or handle it] |

## Open Questions

[Numbered list of unresolved questions that need team input during review. These are things you genuinely don't know the answer to — not rhetorical questions.]

1. [Question 1]
2. [Question 2]

## Decision

**Status**: [Pending — filled in after review]

**Decision Date**: YYYY-MM-DD

**Decision**: Accept / Reject / Defer until [condition]

**Rationale**: [Why this decision was made, addressing key concerns raised during review]

**Follow-up ADR**: ADR-[NUMBER] (created after acceptance)
```

## RFC Numbering

- Number RFCs sequentially: RFC-001, RFC-002, etc.
- Store accepted RFCs in `docs/rfcs/` alongside ADRs in `docs/adr/`.
- Never delete or modify accepted RFCs. If the approach changes, write a new RFC that supersedes the old one.

## RFC Review Checklist (For Reviewers)

When reviewing an RFC, evaluate:

1. **Problem validity**: Is the problem real and well-evidenced, or hypothetical?
2. **Solution completeness**: Does the proposal cover all affected layers of our stack?
3. **Alternatives fairness**: Were alternatives genuinely considered, or are they strawmen?
4. **Migration feasibility**: Is the migration plan realistic given team capacity?
5. **Risk honesty**: Are risks acknowledged honestly, or is the proposal overselling?
6. **Reversibility**: Can we undo this if it doesn't work out? What's the blast radius?
7. **Scope**: Is this one proposal or multiple proposals bundled together? Split if needed.

## Examples of Good RFC Titles

- RFC-012: Replace Panko with Alba for JSON serialization
- RFC-015: Add PostGIS-based geofencing to delivery service
- RFC-018: Migrate background jobs from Sidekiq to GoodJob
- RFC-021: Introduce feature flags via Flipper gem
- RFC-024: Split monolith notifications into dedicated service
- RFC-027: Add offline-first support to React Native app
