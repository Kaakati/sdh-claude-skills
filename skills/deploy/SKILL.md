---
name: deploy
description: Execute deployment workflows with pre-flight checks, environment validation, health verification, and rollback procedures. Use this skill whenever someone asks to deploy, push to staging, release to production, or says things like "deploy to staging", "release this to production", "run the deployment checklist", "is this ready to deploy", "execute the release", or "roll back the deployment". Also trigger when someone mentions deployment readiness, smoke tests after deploy, rollback procedures, or canary/blue-green deployment strategy.
model: sonnet
agent: devops-engineer
context: fork
disable-model-invocation: true
argument-hint: "staging or production"
hooks:
  - event: PreToolUse
    matcher: Bash
    type: prompt
    prompt: |
      DEPLOYMENT GATE: The user has invoked the /deploy skill. Before executing any Bash command, verify:
      1. Is the current git branch clean? (no uncommitted changes)
      2. Has the user confirmed the target environment (staging/production)?
      3. For production: Has a staging deployment succeeded first?
      If any check fails, BLOCK the command and explain what must be resolved first.
      Do NOT block read-only commands (git status, curl health checks, docker-compose ps).
---

# Deploy

Execute deployments safely with pre-flight validation, step-by-step execution, and rollback procedures. This skill is user-invoked only — deployments are never triggered automatically.

## Pre-Flight Checklist

Complete every item before proceeding with deployment.

### Code Readiness
- [ ] All CI checks pass on the deployment branch (tests, lint, build).
- [ ] Code has been reviewed and approved via pull request.
- [ ] No open merge conflicts with the target branch.
- [ ] All dependent PRs have been merged.
- [ ] Version number or release tag is updated if applicable.

### Database
- [ ] Database migrations are tested in staging.
- [ ] Migration rollback is tested and documented.
- [ ] Migrations are backwards-compatible with the current application version.
- [ ] Large data migrations have been estimated for duration and load impact.

### Configuration
- [ ] Environment variables for the target environment are set and verified.
- [ ] Secrets and credentials are in the secrets manager (not in code or env files).
- [ ] Feature flags are configured for the target environment.
- [ ] Third-party service configurations (API keys, webhook URLs) are updated.

### Dependencies
- [ ] No known critical vulnerabilities in dependencies.
- [ ] Lock files are up to date and committed.
- [ ] External service dependencies are healthy (check status pages).

### Communication
- [ ] Team is notified of the deployment window.
- [ ] Stakeholders are informed of changes being deployed.
- [ ] On-call engineer is available for the deployment window.

## Deployment Procedure

### Step 1: Environment Verification

Verify the target environment is healthy before deploying:

```bash
# Check current application health
curl -s https://{environment}/health | jq .

# Verify database connectivity
curl -s https://{environment}/health/db | jq .

# Check current deployed version
curl -s https://{environment}/version | jq .

# Verify external service connectivity
curl -s https://{environment}/health/dependencies | jq .
```

### Step 2: Create Deployment Record

```bash
# Tag the release
git tag -a v{version} -m "Release v{version}: {description}"
git push origin v{version}
```

### Step 3: Run Database Migrations (if applicable)

```bash
# Apply migrations
{migration-command} --env={environment}

# Verify migration status
{migration-status-command} --env={environment}

# Validate schema
{migration-validate-command} --env={environment}
```

If migration fails: STOP. Do not proceed with application deployment. Execute migration rollback.

### Step 4: Deploy Application

```bash
# Deploy using the project's deployment tool
# Examples:
# - Kubernetes: kubectl apply -f deployment.yaml
# - AWS ECS: aws ecs update-service --cluster {cluster} --service {service} --force-new-deployment
# - Docker: docker-compose up -d --build
```

Monitor the deployment for:
- All instances starting successfully.
- No crash loops or restart cycles.
- Health checks passing on new instances.

### Step 5: Health Checks

After deployment completes, verify:

```bash
# Application health
curl -s https://{environment}/health | jq .

# Database health
curl -s https://{environment}/health/db | jq .

# Version verification
curl -s https://{environment}/version | jq .
```

### Step 6: Smoke Tests

Run automated smoke tests against the deployed environment:

```bash
# Run smoke test suite
{test-runner} --suite=smoke --env={environment}
```

Smoke tests should verify:
- [ ] Authentication flow works (login, token refresh).
- [ ] Core CRUD operations succeed.
- [ ] Critical business workflows complete end-to-end.
- [ ] External integrations respond correctly.
- [ ] Static assets are served correctly.

### Step 7: Monitoring

After deployment, monitor for 15-30 minutes:

- **Error rate**: Should not increase above baseline. Alert threshold: >1% increase.
- **Response time**: p95 latency should remain within targets. Alert threshold: >50% increase.
- **Resource usage**: CPU and memory should stabilize. Alert threshold: >80% sustained.
- **Business metrics**: Conversion rate, signup rate, transaction volume should be stable.

### Step 8: Post-Deployment

- [ ] Update deployment tracking (mark as successful).
- [ ] Notify the team that deployment is complete.
- [ ] Update changelog or release notes.
- [ ] Close related tickets/issues.
- [ ] Remove old feature flags if applicable (schedule for next sprint).

## Rollback Procedure

If issues are detected after deployment:

### Decision Criteria for Rollback
- Error rate exceeds 5% for more than 5 minutes.
- Critical business workflow is broken.
- Data integrity issue detected.
- Security vulnerability discovered in deployed code.

### Rollback Steps

```bash
# 1. Announce rollback — notify team immediately

# 2. Rollback application to previous version
# Use your deployment tool's rollback mechanism

# 3. Rollback database migrations (if applicable)
{migration-rollback-command} --env={environment} --steps=1

# 4. Verify rollback
curl -s https://{environment}/health | jq .
curl -s https://{environment}/version | jq .

# 5. Run smoke tests
{test-runner} --suite=smoke --env={environment}
```

### After Rollback
- [ ] Confirm system is stable.
- [ ] Investigate root cause.
- [ ] Document the incident with timeline and cause.
- [ ] Fix the issue and plan a new deployment.

## Environment-Specific Notes

### Staging
- Deploy frequently (after each PR merge or on a schedule).
- Run full test suite after deployment.
- Use production-like data (anonymized).
- Test migrations with realistic data volume.

### Production
- Deploy during business hours when the team is available (unless zero-downtime is verified).
- Use canary or blue-green deployment when available.
- Have a rollback plan ready before starting.
- Monitor for at least 30 minutes after deployment.
- Avoid deploying on Fridays unless the change is critical and low-risk.

## Deep guides (read on demand, do not preload)

- **Canary and blue-green on ECS** — when to pick which, the validation deltas, the abort, and why
  a shared database is the trap in both → `references/ecs-strategies.md`

  The procedure above is the right one for almost every deploy. Reach for a canary only when the
  change is risky *and* its failure is statistical (latency, error rate); reach for blue-green when
  you need an atomic switch back. Neither protects you from a migration.

- **Web frontend deploys — Vercel (Next.js) and S3+CloudFront (Vite SPA)** →
  `@skills/std-infrastructure/references/frontend-deploys.md`

  That reference owns this, and it auto-loads for infrastructure work. It is decision-shaped
  (*"how do I deploy the Vite SPA"*, *"how do I deploy Next.js"*, *"what gates the web pipeline"*)
  and covers `vercel.json`, the `output: 'standalone'` ECS alternative, and the pipeline gates.
  This body carried a second copy until it drifted from it — the copy's HSTS header had lost
  `includeSubDomains; preload`, which is exactly what the preload list requires, so following the
  duplicate produced a header that looks right and qualifies for nothing.
