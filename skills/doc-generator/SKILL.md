---
name: doc-generator
description: Generate technical documentation including API docs, architecture decision records (ADRs), runbooks, changelogs, and technical specifications. Use this skill whenever someone asks to write documentation, create an ADR, generate API docs, write a runbook, or says things like "document this API", "write an ADR for X", "create a runbook for Y", "generate the tech spec", "write the changelog entry", "update the docs", or "we need documentation for this feature". Also trigger when someone mentions architecture decision recording, technical specification writing, or operational runbook creation.
model: sonnet
context: fork
---

# Documentation Generator

## Supported Document Types

### 1. Architecture Decision Record (ADR)
When to create: Any significant technical decision that affects the team.

```markdown
# ADR-NNN: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXX

## Context
What is the issue that we're seeing that is motivating this decision or change?

## Decision
What is the change that we're proposing and/or doing?

## Consequences

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Alternatives Considered
1. **[Alternative]**: [Why not chosen]

## References
- [Links to relevant resources]
```

### 2. API Endpoint Documentation
When to create: Every new API endpoint.

```markdown
# [Resource] API

## [METHOD] /api/v1/[resource]

### Description
[What this endpoint does]

### Authentication
Required. Bearer token in Authorization header.

### Authorization
[Pundit policy]: [Who can access]

### Parameters
| Name | Type | In | Required | Description |
|------|------|-----|----------|-------------|

### Request Body (if applicable)
```json
{
  "field": "type — description"
}
```

### Response
**200 OK**
```json
{
  "data": { },
  "meta": { "total": 100, "next_cursor": "abc" }
}
```

### Error Responses
| Status | Code | Description |
|--------|------|-------------|
| 401 | unauthorized | Missing or invalid token |
| 403 | forbidden | Insufficient permissions |
| 422 | validation_error | Invalid input |

### Example
```bash
curl -X GET https://api.example.com/api/v1/orders \
  -H "Authorization: Bearer $TOKEN"
```
```

### 3. Runbook
When to create: Every operational procedure that might be needed during incidents.

```markdown
# Runbook: [Procedure Name]

## Overview
[What this runbook covers and when to use it]

## Prerequisites
- [ ] Access to [system]
- [ ] Permissions: [required roles]

## Steps

### 1. [Step Name]
```bash
[command]
```
**Expected output**: [what you should see]
**If it fails**: [what to do]

### 2. [Next Step]
...

## Rollback
[How to undo if something goes wrong]

## Verification
[How to confirm the procedure succeeded]

## Escalation
- L1: [team/person]
- L2: [team/person]
```

### 4. Technical Specification
When to create: Before implementing complex features.

```markdown
# Tech Spec: [Feature Name]

## Summary
[1-2 sentence overview]

## Background
[Why we're building this]

## Goals
- [ ] [Goal 1]
- [ ] [Goal 2]

## Non-Goals
- [What this does NOT cover]

## Design

### Data Model
[PostgreSQL schema changes, PostGIS columns if geospatial]

### API Design
[New endpoints with request/response format]

### Mobile UI
[React Native screens, navigation flow]

### Real-time
[Centrifugo channels if applicable]

### Background Jobs
[Sidekiq jobs if applicable]

## Testing Plan
[How this will be tested]

## Rollout Plan
[Phased rollout, feature flags, migration plan]

## Open Questions
- [ ] [Question 1]
```

### 5. Changelog Entry
When to create: Every release or significant change merged to main.

Follow [Keep a Changelog](https://keepachangelog.com/) format in `CHANGELOG.md`:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature or capability (link to PR)

### Changed
- Modification to existing behavior (link to PR)

### Fixed
- Bug fix (link to PR/issue)

### Deprecated
- Feature marked for future removal

### Removed
- Feature or capability removed

### Security
- Security-related fix (link to advisory)
```

Rules:
- One entry per PR, not per commit.
- Link to the PR or issue for traceability.
- Write for the end user, not the developer. "Fixed login timeout" not "Refactored auth middleware".
- Unreleased changes go under `## [Unreleased]` at the top.
- Move from Unreleased to a versioned section when cutting a release.

### 6. Sprint / Project Retrospective

When to create: After every sprint or project milestone.

```markdown
# Retrospective: [Sprint/Project Name]
**Date**: YYYY-MM-DD | **Facilitator**: [Name] | **Participants**: [List]

## Sprint Summary
- **Sprint Goal**: [What we aimed to achieve]
- **Velocity**: [X] story points committed, [Y] completed
- **Carryover**: [Stories carried to next sprint, if any]

## Start (things to begin doing)
| # | Action | Owner | Due Date |
|---|--------|-------|----------|
| 1 | [New practice to adopt] | [Name] | [Date] |

## Stop (things to stop doing)
| # | Action | Reason |
|---|--------|--------|
| 1 | [Practice to discontinue] | [Why it's not working] |

## Continue (things working well)
| # | Practice | Impact |
|---|----------|--------|
| 1 | [Successful practice] | [Positive outcome] |

## Action Items from Previous Retro
| # | Action | Status | Notes |
|---|--------|--------|-------|
| 1 | [Previous action] | Done / In Progress / Not Started | [Update] |

## Metrics Review
- **Velocity trend**: [Improving / Stable / Declining] over last 3 sprints
- **Bug rate**: [X] bugs found in sprint vs [Y] previous sprint
- **Deployment frequency**: [X] deploys this sprint
- **Cycle time**: Average [X] days from start to done

## Key Discussion Points
[Summary of major discussion topics and decisions made]
```

### 7. Change Management Procedure

When to create: For significant system changes that affect production or team workflows.

```markdown
# Change Request: [CR-NNN] [Title]

## Change Details
- **Requester**: [Name]
- **Date**: YYYY-MM-DD
- **Priority**: Critical / High / Medium / Low
- **Type**: Standard / Normal / Emergency
- **Environment**: Production / Staging / All

## Description
[What is being changed and why]

## Impact Assessment

### Technical Impact
- **Systems affected**: [List of services, databases, infrastructure]
- **Downtime required**: Yes (estimated [X] minutes) / No
- **Data migration**: Yes / No
- **Backward compatible**: Yes / No

### Business Impact
- **Users affected**: [Count or percentage]
- **Revenue impact**: [Estimated impact during change window]
- **SLA impact**: [Any SLA considerations]

### Risk Assessment
| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | Low/Med/High | Low/Med/High | [Mitigation plan] |

## Implementation Plan
| Step | Action | Responsible | Duration | Verification |
|------|--------|-------------|----------|--------------|
| 1 | [Pre-change backup] | [Name] | [Time] | [How to verify] |
| 2 | [Execute change] | [Name] | [Time] | [How to verify] |
| 3 | [Post-change validation] | [Name] | [Time] | [How to verify] |

## Rollback Plan
| Step | Action | Responsible | Duration |
|------|--------|-------------|----------|
| 1 | [Rollback step] | [Name] | [Time] |

**Rollback decision criteria**: [When to trigger rollback]
**Maximum rollback time**: [X] minutes

## Approval
| Role | Name | Approved | Date |
|------|------|----------|------|
| Tech Lead | | [ ] | |
| Product Owner | | [ ] | |
| DevOps | | [ ] | |

## Communication Plan
- **Before change**: Notify [audience] via [channel] at [time]
- **During change**: Status updates every [X] minutes in [channel]
- **After change**: Confirmation to [audience] via [channel]
- **If rollback**: Notify [audience] immediately via [channel]

## Post-Change Review
- [ ] Change completed successfully
- [ ] All verification steps passed
- [ ] Monitoring confirms stable operation
- [ ] Documentation updated
- [ ] Stakeholders notified of completion
```

## Generation Protocol
1. Identify the document type needed
2. Gather information by reading relevant code files
3. Apply the appropriate template above
4. Fill in details from code analysis
5. Highlight any gaps or questions
6. Output the complete document

See references/doc-templates.md for additional templates.
