---
name: technical-rfc
description: Write Technical RFCs (Request for Comments) for proposing significant technical changes that require team review and consensus. Use this skill whenever someone asks to write an RFC, technical proposal, design proposal, or says things like "propose a new approach", "get buy-in for this change", "write a proposal for X", "create an RFC", or "I want to propose we change how we do Y". Also trigger when someone needs to propose a new library, framework migration, process change, or architectural shift that affects multiple teams.
model: sonnet
---

# Technical RFC

Write Technical RFCs that drive informed decision-making for significant changes. An RFC is a structured proposal that invites feedback before commitment — it's cheaper to debate a document than to rewrite a system.

## When to Write an RFC

An RFC is required when a change meets **any** of these criteria:

- Introduces a new dependency, library, or framework (e.g., replacing Panko with a different serializer)
- Changes how data flows between systems (e.g., adding a new Centrifugo channel pattern)
- Modifies database schema in a way that affects multiple services or teams
- Proposes a new architectural pattern that deviates from current conventions
- Requires migration effort across existing code (e.g., switching from callbacks to async/await)
- Affects the deployment pipeline, infrastructure, or operational procedures
- Changes shared APIs that other teams or clients consume
- Introduces a new third-party service or cloud provider integration

An RFC is **not** needed for:

- Bug fixes following established patterns
- Adding features within existing architecture
- Dependency version upgrades (patch/minor) without API changes
- Documentation updates
- Refactors that don't change external behavior or interfaces

## RFC Writing Protocol

### Step 1: Understand the Problem Before Proposing a Solution

Before writing the RFC:

1. Identify the pain point, limitation, or opportunity that motivates the change.
2. Gather evidence: error rates, performance metrics, developer friction, customer complaints.
3. Confirm the problem is real — not hypothetical, not premature optimization.
4. Check if someone has already proposed a solution (search existing RFCs, ADRs, Slack threads).

### Step 2: Research Alternatives Thoroughly

For every RFC, evaluate at minimum:

1. **Do nothing** — What happens if we don't make this change? Sometimes the status quo is the right choice.
2. **The proposed solution** — Your recommended approach.
3. **At least one alternative** — A meaningfully different approach, not a strawman.

For each alternative, assess against our stack:

| Concern | Questions to Answer |
|---------|-------------------|
| **Rails backend** | Does it work with our service object pattern? Panko serialization? Sidekiq jobs? |
| **React Native** | Does it work with Zustand state management? TanStack Query? Is the npm package actively maintained? |
| **PostgreSQL/PostGIS** | What schema changes are needed? Migration strategy? Spatial query impact? |
| **Centrifugo** | Does it affect real-time channels? WebSocket connection patterns? |
| **Redis** | Cache invalidation impact? Sidekiq queue changes? |
| **Infrastructure** | Terraform changes? Docker Compose updates? AWS/GCP service additions? |
| **Team** | Learning curve? Hiring impact? On-call complexity? |

### Step 3: Write the RFC

Use the template in `references/rfc-guide.md`. Every section is mandatory — if a section is not applicable, write "N/A" with a one-sentence explanation of why.

Key writing principles:

- **Lead with the problem, not the solution.** The reader must feel the pain before evaluating the fix.
- **Be specific.** "Improves performance" is useless. "Reduces p95 API latency from 450ms to under 100ms by eliminating N+1 queries in the order listing endpoint" is useful.
- **Show your work.** Include benchmarks, prototypes, proof-of-concept results, or load test data.
- **Name the risks honestly.** A proposal that claims zero downsides is not credible.
- **Write for the skeptic.** Assume the reader's default position is "no" — persuade them with evidence.
- **Keep it under 3 pages.** If the RFC is longer, the proposal is probably too big. Split it.

### Step 4: Stack-Specific Impact Assessment

Every RFC must include an impact assessment against our stack. Use this checklist:

#### Backend Impact
- [ ] Rails routes, controllers, or middleware changes
- [ ] Service object interface changes
- [ ] Panko serializer additions or modifications
- [ ] Sidekiq job changes (new queues, changed priorities, retry behavior)
- [ ] Gem additions or upgrades (check license, maintenance status, download count)

#### Frontend Impact
- [ ] React Native screen or component changes
- [ ] Zustand store modifications
- [ ] TanStack Query cache key or fetching pattern changes
- [ ] New npm package additions (check bundle size, maintenance, React Native compatibility)
- [ ] Centrifugo subscription changes

#### Data Impact
- [ ] PostgreSQL schema migrations (use expand/contract for breaking changes)
- [ ] PostGIS spatial column or index changes
- [ ] Redis key namespace or TTL changes
- [ ] Data backfill required (estimate volume and duration)

#### Infrastructure Impact
- [ ] Terraform resource additions or changes
- [ ] Docker Compose service modifications
- [ ] Environment variable additions
- [ ] CI/CD pipeline changes
- [ ] Monitoring and alerting updates

### Step 5: Define the Migration Path

If the RFC changes existing behavior, the migration path must:

1. Be **incremental** — no big-bang switchover.
2. Support **rollback** at every step.
3. Define **done criteria** — how do we know the migration is complete?
4. Estimate **effort** in developer-days (not story points).
5. Identify **who** does each step.

### Step 6: Specify the Review Process

1. List required reviewers by role (backend lead, frontend lead, DevOps, etc.).
2. Set a review deadline (default: 5 business days).
3. Define the decision process: consensus, maintainer approval, or tech lead decision.
4. Specify how feedback is incorporated: comment threads on the RFC document.

## Output Format

Produce the RFC using the template from `references/rfc-guide.md`. The output must be a complete, ready-to-share document — not a skeleton or placeholder.

## Relationship to ADRs

- **RFC** = "Should we do X?" (pre-decision proposal, invites debate)
- **ADR** = "We decided X because Y." (post-decision record, documents outcome)

After an RFC is accepted, create a corresponding ADR using the `/doc-generator` skill to permanently record the decision. Reference the RFC number in the ADR.
