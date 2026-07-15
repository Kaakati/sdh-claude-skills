# Background Jobs — retries you did not ask for

Load-bearing rules restated (hold even if you read nothing else):

1. **Sidekiq retries by default: 25 times over ~20 days.** You did not configure this. It is
   already happening to every job you have ever written.
2. **`retry_on` does not replace that — it stacks on top of it.** Your "5 attempts" job retries
   5 times, then hands the failure back to Sidekiq for 25 more.
3. **A retried job must be idempotent**, because delivery is at-least-once and the retry is not
   optional.

---

## The defaults nobody reads

Sidekiq's wiki, exactly:

> *"It will perform **25 retries over approximately 20 days**."*
> *"The Dead set is limited by default to **10,000 jobs or 6 months** so it doesn't grow
> infinitely."*

Sit with the first one. A job that calls a payment API, fails, and is left at defaults will keep
calling that API **for three weeks**. Nobody decided that. It is what "not configuring retries"
means — the absence of a decision *is* a decision here, and it is rarely the one you want.

Backoff is `(retry_count ** 4) + 15 + (rand(10) * (retry_count + 1))` seconds — so the early
retries are fast (seconds) and the late ones are days apart. The fast ones are what hammer a
struggling downstream during an incident.

## Decision: what should this job do when it fails?

| The failure | Setting | Why |
|---|---|---|
| Transient (network, 503, lock timeout) | leave the default, or `retry: 10` | Retrying is the whole point |
| Permanent (validation, 404, bad input) | `discard_on` / `retry: false` | 25 retries of a guaranteed failure is pure noise |
| Money / irreversible | `retry: 5` **+ idempotency key** | Retry is safe only if the server dedupes |
| Must not outlive its usefulness | `retry_for: 1.hour` (7.1.3+) | A password-reset email retried on day 19 is a bug |
| Needs a human to look | `retry: 0` | Straight to the Dead set, where it is visible |

### `retry: 0` and `retry: false` are not the same thing

One character, opposite outcomes:

- **`retry: 0`** — *"Skips retries, sends failed job directly to the Dead set"*. The job is
  **kept**, visible in the UI, manually retryable for 6 months.
- **`retry: false`** — *"Job executes only once with no retries; **discarded** if it fails"*.
  Gone. No Dead set, no record, no evidence.

`retry: false` on a job that matters is how work disappears silently. Reach for `retry: 0` unless
you genuinely do not care whether it ran.

## The trap: `retry_on` stacks with Sidekiq

The repo currently says *"configure `retry_on` for transient errors"*. That is an **ActiveJob**
API, and on Sidekiq it does not do what it looks like it does. Sidekiq's wiki:

> *"This can be confusing when comparing Sidekiq and ActiveJob documentation, as **ActiveJob does
> not provide a retry mechanism on its own, but failed ActiveJob jobs will retry**."*

And the two run **sequentially** — ActiveJob's retries first, then *"Active Job will kick the job
back to Sidekiq, where Sidekiq's retries with exponential backoff will take over."*

### Bad — "give up after 5 attempts" that runs for 20 days

```ruby
# app/jobs/charge_order_job.rb  ❌
class ChargeOrderJob < ApplicationJob
  # Reads as: try 5 times, 3s apart, then stop. That is NOT what happens.
  retry_on Payments::TimeoutError, wait: 3.seconds, attempts: 5

  def perform(order_id)
    Payments::Charge.new(Order.find(order_id)).call
  end
end
```

After the 5th failure, ActiveJob re-raises — and **Sidekiq's own 25 retries over ~20 days take
over**. The charge is attempted 30 times across three weeks, by a job whose author believed it
gave up in fifteen seconds.

### Good — one retry policy, stated once

```ruby
# app/jobs/charge_order_job.rb  ✅
class ChargeOrderJob < ApplicationJob
  # sidekiq_options works on ActiveJob classes. One policy, in the layer that actually
  # enforces it, so the number in the code is the number of attempts that happen.
  sidekiq_options retry: 5

  # Permanent failures: discard rather than burn 5 attempts proving the record is still gone.
  discard_on ActiveRecord::RecordNotFound

  def perform(order_id)
    order = Order.find(order_id)
    # The idempotency key makes attempt #5 safe — the server returns the original result
    # instead of charging again. Derived from the order, NOT generated here: a fresh uuid
    # per attempt would defeat the entire mechanism.
    Payments::Charge.new(order, idempotency_key: "order-#{order.id}-charge").call
  end
end
```

## Decision: ActiveJob or `include Sidekiq::Job`?

**This repo is currently split** — some jobs subclass `ApplicationJob`, others include
`Sidekiq::Job`. That is a decision worth making once rather than per file:

| | ActiveJob (`< ApplicationJob`) | Native (`include Sidekiq::Job`) |
|---|---|---|
| Overhead | *"about 30% overhead versus Sidekiq's native Sidekiq::Job API"* | Baseline |
| Retries | `retry_on` **stacks** on Sidekiq's (above) | One mechanism, `sidekiq_options` |
| Arguments | Serializes AR objects via GlobalID — convenient, and it re-queries | Plain JSON only |
| Portability | Swap the queue backend | Sidekiq forever |
| `sidekiq_options` | **Works** | Native |
| `sidekiq_retries_exhausted` / `sidekiq_retry_in` | Works (7.1.3+) | Native |

**Default to native `Sidekiq::Job`** unless you have a concrete plan to change backends: one
retry mechanism instead of two is worth more than portability you will never use. If you stay on
ActiveJob, set `sidekiq_options retry:` and treat `retry_on` as a thing you have decided *not*
to use — half a retry policy is worse than none, because it reads as complete.

Either way: **pass ids, never records.** GlobalID makes passing an AR object look fine, and then
the job deserializes a row that changed — or was deleted — between enqueue and run.

## The Dead set is not an inbox

Exhausted jobs go to the Dead set and sit there for 6 months. Nobody looks. That is Ch. 9's
silent failure wearing a queue's clothes: the work did not happen, and no page fired.

```ruby
# app/jobs/charge_order_job.rb  ✅ say something when it finally gives up
class ChargeOrderJob < ApplicationJob
  sidekiq_options retry: 5

  sidekiq_retries_exhausted do |job, ex|
    # This is the last moment anyone can act. Without it, the job dies into the Dead set
    # and the customer's order is simply never charged, silently, forever.
    Sentry.capture_exception(ex, extra: { job: job["class"], args: job["args"] })
    Rails.logger.error({ msg: "job dead", job: job["class"], args: job["args"], error: ex.message })
  end

  def perform(order_id) = Payments::Charge.new(Order.find(order_id)).call
end
```

```ruby
# config/initializers/sidekiq.rb  ✅ a floor for every job, including the ones that forgot
Sidekiq.configure_server do |config|
  config.death_handlers << lambda do |job, ex|
    Sentry.capture_exception(ex, extra: { job: job["class"], args: job["args"] })
  end
end
```

Alert on **Dead set size** (`std-monitoring`). A growing Dead set is work silently not happening.

## Never rescue-and-swallow inside a job

```ruby
# ❌ this job can never fail, so it can never retry, so it can never succeed later
def perform(order_id)
  Payments::Charge.new(Order.find(order_id)).call
rescue => e
  Rails.logger.error(e.message)   # Sidekiq sees SUCCESS. The charge never happened.
end
```

A job's exception **is** its retry signal. Swallowing it converts a transient network blip into
permanent silent data loss, and the queue reports 100% success while doing so. Log *and re-raise*,
or do not rescue:

```ruby
# ✅
def perform(order_id)
  Payments::Charge.new(Order.find(order_id)).call
rescue => e
  Rails.logger.error({ msg: "charge failed", order_id:, error: e.message })
  raise            # <- the retry, and the alert, both depend on this line
end
```

## Timeouts: the job that never fails and never finishes

An HTTP call with no timeout inside a job holds a worker thread indefinitely. Enough of them and
the queue stops — not because of errors, but because every thread is waiting.

```ruby
# ✅ faraday, per the stack. A timeout turns a hang into a retryable error.
conn = Faraday.new(url: base) do |f|
  f.options.timeout      = 10   # total
  f.options.open_timeout = 2    # connect
end
```

`retry` is only a safety net if failure is *fast*. Without timeouts, there is no failure to
retry — just a stuck queue and a green dashboard.

## Idempotency, concretely

At-least-once delivery means the server may see the same job twice — a retry after a lost
response is indistinguishable from a fresh attempt.

```ruby
# ✅ a natural, stable key derived from the work — not from the attempt
def perform(order_id)
  order = Order.find(order_id)
  return if order.charged?              # cheap guard; not sufficient alone (race)
  Payments::Charge.new(order, idempotency_key: "order-#{order.id}-charge").call
end
```

The guard is an optimisation; the **key** is the correctness. Two workers can pass `charged?`
simultaneously — only the server-side dedupe (or a unique index, or `with_lock`) actually
prevents the double charge. See `../std-database/references/locking-and-timeouts.md`.
