# Backend Deploys — Rails to ECS Fargate

How a merge reaches the Rails service. For PR checks and OIDC setup see `ci-pipeline.md`; for
frontend hosting see `frontend-deploys.md`; for the ECS/ALB Terraform see
`aws-compute-and-networking.md`.

Load-bearing rules restated (they hold even if you read nothing else):
- **`develop` merges deploy to staging automatically. `main` merges deploy to production behind a manual approval gate.**
- **Migrations run as a separate step before the deploy**, never as a container entrypoint.
- **Smoke tests run after every deployment.**
- **No long-lived AWS keys in CI** — GitHub Actions authenticates via OIDC role assumption (`permissions: id-token: write`).
- **Image tags are immutable git SHAs, never `latest`** — you cannot roll back to a tag that moved.

---

## Decision: how do I deploy Rails to ECS

Image tags are **immutable git SHAs**, never `latest` — you cannot roll back to a tag that moved. Migrations run as a standalone ECS task **before** the service update, so a failing migration aborts the deploy rather than crash-looping half the fleet.

### Bad — migrations in the entrypoint, mutable tag

```dockerfile
# BAD: every task on every scale-out event races to run migrations
CMD ["sh", "-c", "bundle exec rails db:migrate && bundle exec rails server -b 0.0.0.0"]
```

```yaml
      - run: docker build -t $ECR/app:latest . && docker push $ECR/app:latest
      - run: aws ecs update-service --cluster prod --service rails --force-new-deployment
      # BAD: no rollback target, no wait, no smoke test — the job goes green before the deploy lands
```

### Good — build once, migrate as a task, update service, wait, smoke test

```yaml
# .github/workflows/deploy-production.yml
name: Deploy production

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image: ${{ steps.build.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-production
          aws-region: eu-west-1
      - uses: aws-actions/amazon-ecr-login@v2
        id: ecr
      - name: Build and push
        id: build
        env:
          REGISTRY: ${{ steps.ecr.outputs.registry }}
          TAG: ${{ github.sha }}
        run: |
          docker build --target production -t "$REGISTRY/app:$TAG" .
          docker push "$REGISTRY/app:$TAG"
          echo "image=$REGISTRY/app:$TAG" >> "$GITHUB_OUTPUT"

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production        # manual approval gate configured on this environment
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy-production
          aws-region: eu-west-1

      - name: Run migrations (separate step, before deploy)
        run: |
          TASK_ARN=$(aws ecs run-task \
            --cluster production \
            --task-definition production-rails-migrate \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG],assignPublicIp=DISABLED}" \
            --overrides '{"containerOverrides":[{"name":"rails","command":["bundle","exec","rails","db:migrate"]}]}' \
            --query 'tasks[0].taskArn' --output text)
          aws ecs wait tasks-stopped --cluster production --tasks "$TASK_ARN"
          EXIT=$(aws ecs describe-tasks --cluster production --tasks "$TASK_ARN" \
            --query 'tasks[0].containers[0].exitCode' --output text)
          test "$EXIT" = "0" || { echo "Migration failed with exit $EXIT"; exit 1; }
        env:
          SUBNETS: ${{ vars.PRIVATE_SUBNET_IDS }}
          SG: ${{ vars.APP_SECURITY_GROUP_ID }}

      - name: Render task definition with the new image
        id: taskdef
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: deploy/ecs/production-rails.json
          container-name: rails
          image: ${{ needs.build.outputs.image }}

      - name: Deploy and wait for stability
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.taskdef.outputs.task-definition }}
          cluster: production
          service: production-rails
          wait-for-service-stability: true

      - name: Smoke test
        run: |
          for i in $(seq 1 10); do
            if curl -fsS https://api.example.com/up; then
              curl -fsS https://api.example.com/api/v1/health | tee /dev/stderr | grep -q '"status":"ok"'
              exit 0
            fi
            sleep 10
          done
          echo "Smoke test failed after deploy"; exit 1
```

Staging is the same workflow triggered on `push: branches: [develop]`, targeting the staging cluster, with the `environment: staging` gate removed.
