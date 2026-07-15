# GitHub Actions — workflows as supply chain

Load-bearing rules restated (hold even if you read nothing else):

1. **A third-party action is code you run with your token.** `@v4` is a *mutable tag* — pin to a
   full commit SHA.
2. **Set `permissions:` explicitly.** The default `GITHUB_TOKEN` is broader than your job needs.
3. **Every deploy-ish workflow needs a `concurrency` group**, or two merges race to production.

What runs on a pull request, and how CI assumes an AWS role, are owned by
`references/ci-pipeline.md`. This file is about the workflows themselves.

---

## Pinning: the supply-chain rule people skip because the tag looks like a version

`uses: some/action@v4` does not mean "version 4". It means *"whatever commit the `v4` tag points
at, right now"*. Tags are mutable and the action's maintainer — or anyone who compromises their
account — can move it. Your next run then executes code you never reviewed, **with your
`GITHUB_TOKEN` and every secret in scope**.

This is not theoretical: it is how the 2025 `tj-actions/changed-files` compromise leaked secrets
out of thousands of repos in an afternoon. The tag moved; nobody's YAML changed.

```yaml
# ❌ a moving target you re-run daily
- uses: tj-actions/changed-files@v44

# ✅ immutable. The comment keeps it readable; the SHA is what runs.
- uses: tj-actions/changed-files@a29e8b565651ce417abb5db7164b4a2ad8b6155c  # v44.5.7
```

Get the SHA rather than guessing it:

```bash
gh api repos/actions/checkout/git/ref/tags/v4.2.2 --jq '.object.sha'
```

**Dependabot updates pinned SHAs**, so pinning costs you nothing ongoing — this is the whole
reason the objection ("then we never get updates") is wrong:

```yaml
# .github/dependabot.yml  ✅
version: 2
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
```

**Pin third-party actions always.** First-party `actions/*` and `github/*` are a defensible
exception if your risk appetite says so — decide it deliberately and write the decision down,
rather than pinning some and not others by accident.

## Permissions: the token is more powerful than the job

`GITHUB_TOKEN` defaults to a broad scope. A job that only reads code should not be able to write
to it, and a compromised action inherits whatever you left switched on.

```yaml
# ✅ top-level default of least privilege; widen per job, never globally
permissions:
  contents: read

jobs:
  test:
    # inherits contents: read — nothing more
    runs-on: ubuntu-latest

  comment:
    permissions:
      contents: read
      pull-requests: write     # widened for exactly one job, one reason
    runs-on: ubuntu-latest
```

Cloud auth needs `id-token: write` — grant it **only** on the job that authenticates, never at
the top level:

```yaml
  deploy:
    permissions:
      contents: read
      id-token: write          # OIDC only. See references/ci-pipeline.md (AWS) / gcp-secondary-cloud.md (GCP)
```

## Concurrency: the race nobody notices until it corrupts something

Two PRs merge a minute apart. Two deploy workflows run. They apply in an order nobody chose, and
the second-to-finish wins — which may be the *older* commit.

```yaml
# ✅ PR CI: cancel superseded runs, save minutes and get faster feedback
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

```yaml
# ✅ deploys: QUEUE, never cancel
concurrency:
  group: deploy-production
  # false is deliberate: cancelling a half-finished `terraform apply` or migration leaves
  # the world in a state neither version expects. Serialise; do not interrupt.
  cancel-in-progress: false
```

Getting this backwards — `cancel-in-progress: true` on a deploy — is worse than having no
concurrency at all, because it turns a queue into a torn write.

## Reusable workflows vs composite actions

Both exist to stop the copy-paste. They are not interchangeable:

| Need | Use | Why |
|---|---|---|
| A whole job (or several), with its own runner/secrets | **Reusable workflow** (`workflow_call`) | It *is* jobs; can be required, can gate environments |
| A sequence of steps inside someone else's job | **Composite action** | Steps only; no runner or secrets of its own |
| Same 6 setup steps in 5 workflows | Composite action | Cheapest fix |
| Same "build → sign → upload" job for 4 apps | Reusable workflow | Inputs make it one definition |

```yaml
# .github/workflows/rails-ci.yml  ✅ reusable
on:
  workflow_call:
    inputs:
      ruby-version: { type: string, default: "3.3" }
    secrets:
      DATABASE_URL: { required: true }

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
      - uses: ruby/setup-ruby@v1
        with: { ruby-version: "${{ inputs.ruby-version }}", bundler-cache: true }
      - run: bundle exec rspec
        env: { DATABASE_URL: "${{ secrets.DATABASE_URL }}" }
```

```yaml
# .github/workflows/pr.yml  ✅ the caller
jobs:
  rails:
    uses: ./.github/workflows/rails-ci.yml
    # `inherit` passes ALL the caller's secrets. Convenient, and it hands the called
    # workflow more than it needs — name them explicitly when the workflow isn't yours.
    secrets:
      DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

```yaml
# .github/actions/setup-node-pnpm/action.yml  ✅ composite
name: Setup Node + pnpm
runs:
  using: composite
  steps:
    - uses: pnpm/action-setup@v4
      with: { version: 9 }
    - uses: actions/setup-node@v4
      with: { node-version: 20, cache: pnpm }
    - run: pnpm install --frozen-lockfile
      shell: bash        # required in composite steps, and the error if you forget is opaque
```

## Environments: where the human gate actually lives

Branch protection guards the *merge*. An **environment** guards the *deploy* — and it is the
only place a required reviewer can stand between a green pipeline and production.

```yaml
  deploy-production:
    environment:
      name: production
      url: https://app.acme.com
    # Configure in repo settings: required reviewers, a wait timer, and which branches may
    # deploy. Secrets scoped to the environment are unreachable from any other job — which
    # is what keeps a fork PR away from your production credentials.
```

This is layer 6 in workflow form: the irreversible step asks a person. Pair it with the
`deployment-gate` hook, which asks the *developer* before the push — different layer, same
intent, and neither replaces the other.

## The fork-PR hole

`pull_request` from a fork gets **no secrets** — that is the platform protecting you.
`pull_request_target` runs **with secrets**, in the base repo's context. Combine it with a
checkout of the PR's head and you have handed an attacker your credentials:

```yaml
on: pull_request_target        # ⚠️ has secrets
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with: { ref: ${{ github.event.pull_request.head.sha }} }   # ❌ runs their code, with your secrets
      - run: pnpm install && pnpm build                            # ❌ postinstall scripts, now privileged
```

If you need `pull_request_target` (to label, to comment), do **not** check out or execute the
PR's code in that job.

## Caching that is actually a cache

```yaml
- uses: actions/cache@v4
  with:
    path: ~/.gem
    # The lockfile hash IS the key. A key without it never invalidates and you ship a
    # stale cache; a key too specific never hits and the cache does nothing.
    key: ${{ runner.os }}-gems-${{ hashFiles('**/Gemfile.lock') }}
    restore-keys: ${{ runner.os }}-gems-
```

Most ecosystems ship this already — `bundler-cache: true`, `cache: pnpm`, `setup-java` with
`cache: gradle`. Prefer those over hand-rolling; they get the key right.

> **Never cache credentials or a `~/.docker/config.json`.** A cache is shared across branches,
> including branches from people who should not have your registry token.

## Make the workflow legible when it fails

```yaml
- name: Summary
  if: always()
  run: |
    echo "### Deployed \`${GITHUB_SHA:0:7}\` to production" >> "$GITHUB_STEP_SUMMARY"
    echo "- image: \`$IMAGE_TAG\`" >> "$GITHUB_STEP_SUMMARY"
```

A pipeline that says only "✅ passed" is an audit trail nobody can act on at 2am. Say what
shipped, and where.
