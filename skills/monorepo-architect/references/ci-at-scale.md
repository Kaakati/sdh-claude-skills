# CI at Scale — sublinear or bust

Load-bearing rules restated (hold even if you read nothing else):

1. **Affected-only execution** — compute what changed; run only those pipelines.
2. **Remote caching** — a build done on one machine is never repeated on another.
3. **Merge queue** — once past a few concurrent PRs. Trunk breakage blocks *everyone*.

---

## Why this is structural, not an optimization

In a polyrepo, CI time per PR is bounded by the repo you touched. In a monorepo, the naive
setup makes every PR pay for every app — so CI time grows with the *repo*, while the value of a
PR stays constant. That curve ends in one place: people batch changes to amortize the wait,
batches get harder to review, review quality drops, and trunk breaks more often. **Slow
monorepo CI degrades review quality**, which is why this outranks cost.

## Affected-only execution

### Bad — every PR runs everything

```yaml
# .github/workflows/ci.yml  ❌
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bundle exec rspec           # runs when only mobile/ changed
      - run: pnpm turbo run test         # runs when only rails-api/ changed
```

A one-line copy change in the RN app runs the whole Rails suite. Nothing is *wrong*; it is
just linear, and the fix gets deferred because "CI is only 12 minutes" — until it is 40.

### Good — each side computes its own affected set

```yaml
# .github/workflows/ci.yml  ✅
on: pull_request

jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      rails: ${{ steps.filter.outputs.rails }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            rails:
              - 'apps/rails-api/**'
              - 'Gemfile.lock'

  rails:
    needs: changes
    if: needs.changes.outputs.rails == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: bundle exec rspec

  js:
    runs-on: ubuntu-latest
    env:
      TURBO_TOKEN: ${{ secrets.TURBO_TOKEN }}
      TURBO_TEAM: ${{ vars.TURBO_TEAM }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # turbo needs history to diff against the base
      # Turborepo computes the affected set from the real dependency graph — strictly
      # better than path filtering, because it also catches DEPENDENTS of a changed
      # package. Path filtering is the right tool only for Rails, which has no graph here.
      - run: pnpm turbo run lint test typecheck --filter='...[origin/${{ github.base_ref }}]'
```

**Path filtering vs graph filtering.** Path filters are honest about one thing: they only know
what you tell them. If `packages/types` changes, a path filter for `apps/web/**` says "not
affected" and is wrong. Use the graph (`turbo --filter`) wherever a graph exists; use path
filters only for the language that has none.

## Required checks and the skipped-job trap

`if:` on a job makes it **skipped**, and a required check that is skipped blocks the PR forever
in some configurations. Use a gate job that always runs:

```yaml
  ci-ok:
    # The ONLY required check. Always runs, so a legitimately skipped job never wedges the PR.
    needs: [rails, js]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Fail if any needed job failed
        if: contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled')
        run: exit 1
      - run: echo "ok"
```

## Merge queue

Adopt once more than a few PRs land per hour. Without one, PRs are tested against a trunk that
has already moved — each is green alone and red together (*semantic merge conflict*), and in a
monorepo that broken trunk blocks **every team**, not just the one that broke it.

```yaml
# .github/workflows/ci.yml
on:
  pull_request:
  merge_group:          # required: the queue re-runs CI on the speculative merge
```

Then enable the queue in branch protection and require `ci-ok`. The queue's cost is latency on
the happy path; it buys down an outage that stops everyone. That trade flips somewhere around
"a few concurrent PRs" — before that, it is ceremony.

## CODEOWNERS — route review by path

```
# .github/CODEOWNERS  — last match wins, so order matters
*                         @acme/platform
/apps/rails-api/          @acme/backend
/apps/mobile/             @acme/mobile
/packages/api-client/     @acme/backend @acme/mobile   # the contract: both sides review
/packages/ui/             @acme/design-eng
/tooling/                 @acme/platform
```

**Every directory needs an owner, or quality decays uniformly** — an unowned directory is one
nobody is embarrassed by. Note `api-client` deliberately requires both producer and consumer:
that file *is* the cross-team contract.

## Git performance — earlier than you think

Clone and checkout cost grows with history and blob count, and it hits CI on every job before a
single test runs.

```bash
# CI: fetch trees/commits, download blobs only when touched
git clone --filter=blob:none --depth=1 <url>

# Huge repo: check out only what this job needs
git sparse-checkout init --cone
git sparse-checkout set apps/rails-api packages/types
```

```yaml
- uses: actions/checkout@v4
  with:
    filter: blob:none
    fetch-depth: 0     # graph diffing needs history; blob:none keeps it cheap
```

`fetch-depth: 0` and `filter: blob:none` together are the usual answer: you need the *history*
to compute affected, but not every *blob* ever committed.

## Order of adoption

1. **Affected-only** — biggest win, lowest cost.
2. **Remote cache** — compounding; see `references/task-orchestration.md`.
3. **`blob:none` clones** — one line, immediate.
4. **CODEOWNERS** — cheap, and it fixes review latency, not just quality.
5. **Merge queue** — when concurrency justifies the latency.
