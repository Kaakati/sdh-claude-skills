# Canary and Blue-Green Deployments (ECS Fargate)

Both are for the deploy you are **nervous about**. The default path in the skill body — build the
image, run migrations as a task, `aws ecs update-service`, wait, smoke test — is the right one for
almost every deploy, and reaching for a canary when a rolling update would do buys you two
services to reason about at the exact moment you want fewer moving parts.

Load-bearing rules restated (hold even if you read nothing else):

1. **Both strategies share one database.** Neither protects you from a migration. If the new
   revision needs a schema the old one cannot read, "instant rollback" rolls back the code and
   leaves the schema — see the expand/contract rule below.
2. **A canary that nobody measures is just a slower deploy.** The whole value is the comparison
   against primary; if you are not going to watch the deltas for the full window, do a rolling
   update and save yourself the target groups.
3. **`aws ecs update-service` raises a confirmation** (`deployment-gate.py`), and `aws ecs wait
   services-stable` is what makes "deployed" mean "running" rather than "accepted".

## Decision: canary or blue-green?

| | Canary | Blue-Green |
|---|---|---|
| Traffic | A slice (10% → 25% → 50% → 100%) | All of it, at once |
| Detects | Problems that only appear under **real** traffic — a slow query at p99, a hot partition | Problems a smoke test can catch |
| Rollback | Set canary weight to 0 | Switch the listener back — atomic |
| Cost | One extra task | A full second environment, always |
| Use when | The change is risky and its failure is **statistical** (latency, error rate) | The change is risky and its failure is **binary** (it boots or it does not) |

Canary is the better default for an application change. Blue-green earns its cost when you need
an atomic switch and an instant, deterministic way back — a runtime upgrade, a dependency bump
you cannot fully test, a cutover with a fixed window.

## Canary deployment

```bash
# 1. Deploy canary task definition (new version)
aws ecs create-service --cluster production \
  --service-name rails-app-canary \
  --task-definition rails-app:NEW_REVISION \
  --desired-count 1

# 2. Configure ALB weighted target group (10% to canary)
aws elbv2 modify-rule --rule-arn $RULE_ARN \
  --actions '[
    {"Type":"forward","ForwardConfig":{
      "TargetGroups":[
        {"TargetGroupArn":"'$PRIMARY_TG'","Weight":90},
        {"TargetGroupArn":"'$CANARY_TG'","Weight":10}
      ]
    }}
  ]'

# 3. Monitor canary for 15 minutes
# Check: error rate, latency p95, CPU/memory, business metrics
# Compare canary metrics vs primary metrics

# 4a. If healthy — shift traffic progressively: 10% → 25% → 50% → 100%
# 4b. If unhealthy — abort: set canary weight to 0, delete canary service
```

### Canary validation criteria

Compare against **primary over the same window**, not against an absolute threshold — a spike that
hits both is the world, not your deploy:

- Error rate delta < 0.5% compared to primary
- Latency p95 delta < 50ms compared to primary
- No new error types in logs
- Business metrics (conversion, transactions) within normal range

### Bad — a canary with no comparison

```bash
aws ecs create-service --service-name rails-app-canary --desired-count 1 ...
# ...wait a bit, looks fine?
aws elbv2 modify-rule ... Weight 100
```

10% of traffic for five minutes is a small sample. If the failure is a p99 latency regression or a
query that only degrades once the cache is cold, five minutes of eyeballing a dashboard will not
find it — and you have now shipped it to everyone while believing you tested it. Hold the window,
compare the deltas, and write down the numbers you saw.

### Good — the abort is decided before you start

Agree the criteria and the window **before** shifting any traffic, because the moment the canary
looks marginal you will be arguing about thresholds with traffic on it. Abort is cheap
(`Weight: 0`); a debate at 25% is not.

## Blue-green deployment

```bash
# 1. Deploy new version to green (inactive) environment
aws ecs update-service --cluster production \
  --service rails-app-green \
  --task-definition rails-app:NEW_REVISION

# 2. Wait for green to stabilize
aws ecs wait services-stable --cluster production --services rails-app-green

# 3. Run smoke tests against green
curl -s https://green.api.example.com/health | jq .

# 4. Switch ALB listener to green target group
aws elbv2 modify-listener --listener-arn $LISTENER_ARN \
  --default-actions '[{"Type":"forward","TargetGroupArn":"'$GREEN_TG'"}]'

# 5. Monitor for 15 minutes

# 6a. If stable — green is now primary. Update blue for next deployment.
# 6b. If issues — switch listener back to blue (instant rollback)
aws elbv2 modify-listener --listener-arn $LISTENER_ARN \
  --default-actions '[{"Type":"forward","TargetGroupArn":"'$BLUE_TG'"}]'
```

### Prerequisites

- Two identical ECS services (blue + green) behind the same ALB
- **Shared RDS database — migrations must be backward-compatible**
- Shared Redis/ElastiCache instance
- DNS or ALB listener swap for traffic routing

## The shared database is the trap in both

"Instant rollback" is a claim about **traffic**, not about data. The listener swap takes
milliseconds; the schema does not come back with it. So the guarantee only holds if the migration
was backward-compatible in the first place — meaning the *old* revision must keep working against
the *new* schema for as long as both are reachable, which during a canary is the entire window.

Expand/contract, across two deploys:

1. **Expand** — add the nullable column / new table / new index. Deploy. Both revisions work: the
   old one ignores it, the new one populates it.
2. **Contract** — only once the old revision is gone for good, drop the old column.

A `NOT NULL` column added in the same deploy as the code that fills it means the moment you shift
10% of traffic to the canary, the other 90% is writing rows the new schema rejects — or the old
code is inserting rows without the column and hitting a constraint violation. The canary looks
fine; primary is what breaks.

Depth on the locking mechanics — why a migration that *waits* is more dangerous than one that
fails, and why every migration needs `lock_timeout` — is in
`@skills/std-database/references/locking-and-timeouts.md`. A waiting `ALTER TABLE` queues every
query behind it, so a migration that stalls during a blue-green cutover presents as a total
outage across **both** environments, because they share the database.

## Rolling back

| Strategy | Rollback | Cost |
|---|---|---|
| Canary | `Weight: 0`, delete the canary service | Seconds. Nothing user-visible if you caught it in the slice. |
| Blue-green | Switch the listener back to `$BLUE_TG` | Seconds, atomic. |
| Either, **after a contract migration** | There is no traffic-level rollback | The schema no longer matches the old revision. This is why contract is a separate deploy. |

`deployment-gate.py` raises a confirmation on `aws ecs update-service` — that is the system
working. Do not route around it; if you are switching a listener under incident pressure, that
confirmation is the last chance to notice you named the wrong target group.
