---
name: incident-response
description: Guide incident response for production issues including diagnosis, mitigation, communication, and post-mortem analysis. Use this skill whenever someone reports an outage, performance degradation, production error, or says things like "production is down", "users are reporting errors", "the API is slow", "we have an incident", "something broke in prod", "check the logs for errors", or "we need a post-mortem". Also trigger when someone mentions SEV1/SEV2 classification, incident communication, root cause analysis, or wants to write a post-mortem document.
agent: incident-responder
context: fork
argument-hint: "incident description or error message"
model: opus
---

# Incident Response

This skill routes to the **incident-responder** agent — a senior incident commander and SRE specialist (Opus) that diagnoses production incidents methodically, mitigates impact quickly, and produces thorough post-mortems.

## Severity Classification

| Level | Definition | Response Time | Examples |
|-------|-----------|---------------|---------|
| **SEV1** | Service down, data loss risk | Immediate (< 15 min) | API unreachable, database corruption, security breach |
| **SEV2** | Major feature broken, significant user impact | < 30 min | Auth failing, payments broken, Centrifugo down |
| **SEV3** | Degraded performance or minor feature broken | < 2 hours | Slow API, Sidekiq backed up, partial outage |
| **SEV4** | Minor issue, workaround exists | Next business day | UI glitch, non-critical job failing |

## What the Agent Does

The incident-responder agent has access to **Read, Grep, Glob, and Bash** tools for live diagnosis:

1. **Triage** — checks health endpoints, ECS task status, recent deployments, CloudWatch metrics
2. **Component identification** — systematically checks Rails (ECS), PostgreSQL/PostGIS (RDS), Redis/Sidekiq, Centrifugo
3. **Mitigation** — ECS rollback, migration rollback, query termination, Sidekiq worker restart
4. **Communication** — generates incident notifications and status updates
5. **Post-mortem** — produces structured post-mortem documents with timeline, root cause, action items

## Escalation Path

| Level | Who | When |
|-------|-----|------|
| L1 | On-call engineer | SEV3/SEV4 — first 30 minutes |
| L2 | Tech lead + on-call | SEV2 or L1 unresolved within 30 min |
| L3 | CTO + full team | SEV1 or data loss risk |

## Chaos Engineering

The agent also supports proactive resilience testing:
- GameDay experiment design (hypothesis, steady state, abort conditions)
- Fault injection patterns (network, compute, storage, dependency failures)
- Resilience checklist validation

See `agents/incident-responder.md` for the full diagnosis protocol, communication templates, and chaos engineering procedures.
See `docs/runbooks/` for component-specific operational runbooks.

## Deep guides (read on demand, do not preload)

- Runbooks: database connection exhaustion, Redis OOM, Sidekiq queue backup, ECS crash loops, Centrifugo disconnections, PostGIS query timeouts → `references/runbooks.md`
