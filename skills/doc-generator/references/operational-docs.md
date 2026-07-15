# Operational Documents — API Endpoints and Runbooks

Both are read by someone who is **not** the author, often under time pressure, and usually in a
hurry. That is the whole design constraint: an operational document that requires interpretation
has failed.

- **API endpoint documentation** is read by a client developer who wants to call the thing.
- **A runbook** is read at 3am by whoever is on call, who may never have seen this system.

Write for that reader. A runbook step that says "restart the service" fails; one that says
`aws ecs update-service --cluster production --service rails-app --force-new-deployment` succeeds,
because the reader can paste it.

For the error envelope shape an API returns, `std-api-design` is the owner — do not restate it
here: `@skills/std-api-design/references/errors-rails.md`. There is exactly one envelope
(`error`, `code`, `status`, `details`, `requestId`), and a second copy in a doc is how clients end
up parsing two.

Concrete runbooks for this stack — database connection exhaustion, Redis OOM, Sidekiq queue
backup — already exist as worked examples: `@skills/incident-response/references/runbooks.md`.
This file is the *template* for writing a new one; that file is the *instances*.

## API Endpoint Documentation
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


## Runbook
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


## What makes a runbook usable at 3am

- **Every step is copy-pasteable.** No "adjust as needed" — say what to adjust it to.
- **Verification after every mutating step**, not just at the end. A runbook that only verifies at
  the end tells you it failed, not where.
- **Rollback is a section, not a sentence.** If the rollback is "restore from backup", say which
  backup, how to find it, and how long it takes — that number changes what the on-call person
  decides.
- **Escalation names a human and a channel.** "Escalate to the platform team" is not a step.
