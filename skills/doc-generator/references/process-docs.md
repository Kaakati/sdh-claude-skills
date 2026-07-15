# Process Documents — Changelog, Retrospective, Change Management

These three share a failure mode: they get written **for the ritual rather than the reader**, and
then nobody reads them, which retroactively proves they were not worth writing. Each has one job:

- **Changelog** — tells a *user* what changed in a release.
- **Retrospective** — turns what a *team* learned into something that changes next sprint.
- **Change management** — records that a risky change was *approved* by someone accountable.

The house changelog format is **Keep a Changelog** (`Added`, `Changed`, `Fixed`, `Deprecated`,
`Removed`, `Security`) and CLAUDE.md pins it. The categories are not decoration: `Security` is the
one a reader scans for, and burying a security fix under `Fixed` is how it gets missed.

A changelog entry is written **for the person deciding whether to upgrade**. "Refactored the
serializer layer" tells them nothing. "Error responses now use `requestId` (was `request_id`) —
update any client parsing the old key" tells them exactly what it costs.

## Changelog Entry
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


## Sprint / Project Retrospective

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


## Change Management Procedure

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


## The retrospective's only real output is the action items

Start/Stop/Continue is a way to *find* them, not the deliverable. A retro that produces no owned,
dated action item was a meeting. The template's "Action Items from Previous Retro" section is the
load-bearing one — reviewing last time's items first is what stops a team from raising the same
thing every sprint and changing nothing.

## Change management is a Layer 6 artifact

It exists so that a human is accountable for a risky change, and so that the reasoning survives the
person. If the approval is a rubber stamp, the procedure is theatre — and theatre in a control is
worse than nothing, because it buys confidence without buying safety. Either the approver can
refuse, or do not ask them.
