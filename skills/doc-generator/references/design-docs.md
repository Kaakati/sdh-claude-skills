# Design Documents — ADR and Technical Specification

Both record a decision. The difference is scope, and picking the wrong one is the usual mistake:
an **ADR** records *one* choice and why the alternatives lost — it is short, permanent, and
numbered. A **technical specification** describes *how a feature will be built* — it is longer,
and it goes stale the moment the feature ships.

If you find yourself writing "Alternatives Considered" in a spec, the decision inside it wanted
to be an ADR.

**The ADR template below is a contract, not a suggestion.** `architecture-advisor` emits exactly
these sections as its output format, and CLAUDE.md pins the shape
(`ADR-NNN: Title · Status · Context · Decision · Consequences`, stored in `docs/adr/`). A test
holds the two in sync — if you change the section set here, that test fails and it is telling you
the truth: an ADR whose sections drift is no longer greppable by the people who rely on them.

**Do not invent the Decision.** If the material for it came from outside this repository — a
price, a vendor's SLA, a competitor's approach — it belongs under *Alternatives Considered* as an
assumption to verify, never under *Decision* as a finding. An ADR is cited for years by people who
reasonably assume it was checked.

## Architecture Decision Record (ADR)
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


## Technical Specification
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


## Which one am I writing?

| | ADR | Technical Specification |
|---|---|---|
| Answers | *Why did we choose X?* | *How will we build X?* |
| Lifespan | Permanent — superseded, never deleted | Until the feature ships |
| Length | One page | As long as the design needs |
| Lives in | `docs/adr/ADR-NNN-title.md` | Wherever the team keeps specs |
| Written by | `architecture-advisor` (or you, with its format) | The implementing team |

A superseded ADR keeps its file and gets `Status: Superseded by ADR-NNN`. Deleting it destroys the
only record of why the old decision looked right at the time, which is the thing a future reader
actually needs.
