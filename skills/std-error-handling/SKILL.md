---
name: std-error-handling
description: Error handling standards across Rails, React Native, Sidekiq, and API responses — Result objects, custom errors, retry/discard, consistent error JSON. Use when handling errors.
paths:
  - "**/*.rb"
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---

# Error Handling Standards

## Rails Backend
- Never rescue `Exception` — rescue `StandardError` or more specific errors
- Use custom error classes inheriting from `StandardError` for domain errors
- Service objects return Result objects, never raise for business logic failures
- Controllers rescue specific errors and render consistent JSON:
  ```ruby
  rescue ActiveRecord::RecordNotFound
    render json: { error: "Resource not found", code: 404 }, status: :not_found
  rescue ActiveRecord::RecordInvalid => e
    render json: { error: e.message, code: 422, details: e.record.errors }, status: :unprocessable_entity
  ```
- Log all rescued exceptions with context (user_id, request_id, params)
- Use Sentry/Rollbar for error tracking — tag with environment and user

## React Native
- TanStack Query error handling: use `onError` callbacks and `error` state
- Global error boundary for unhandled React errors
- Network errors: show user-friendly messages, retry with exponential backoff
- Form validation: display inline errors from zod schemas
- Never show raw error messages/stack traces to users
- Log errors to crash reporting (Sentry, Crashlytics)

## API Error Response Format

Owned by `std-api-design` — see the "Related, owned elsewhere" pointer at the end of this file.
This skill auto-loads on every `.rb`/`.ts`/`.tsx` file, so a second copy of the envelope here is
a second source of truth on nearly every task. It had already drifted from the owner on every
axis that matters — `code` as an integer rather than the string error code, the HTTP status in
`code` rather than `status`, `details` as an object rather than an array, and `request_id` in an
API whose keys are camelCase.

## Background Jobs (Sidekiq)
- **Sidekiq already retries: 25 times over ~20 days, by default.** Not configuring retries is not
  "no retries" — it is three weeks of them. Set `sidekiq_options retry:` deliberately on every job.
- **`retry_on` does not replace Sidekiq's retries — it stacks on top of them.** ActiveJob retries
  first, then hands the failure back to Sidekiq for its 25. `retry_on ..., attempts: 5` runs 30
  attempts over ~20 days, not 5. Set the policy with `sidekiq_options retry:`, in one place.
- `retry: 0` sends the job to the **Dead set** (kept, visible, retryable for 6 months);
  `retry: false` **discards it** (gone, no record). One character, opposite outcomes.
- Use `discard_on` for permanent errors (record not found, invalid data) — 25 retries of a
  guaranteed failure is noise that hides real failures.
- **Never rescue-and-swallow inside a job.** The exception *is* the retry signal: swallowing it
  makes Sidekiq report success while the work never happened.
- **A retried job must be idempotent** — delivery is at-least-once. Derive the idempotency key
  from the work, never per attempt.
- **Timeouts on every outbound call.** Without them there is no failure to retry — just a worker
  thread held forever and a queue that stops with a green dashboard.
- Dead-set jobs must be alerted on (`sidekiq_retries_exhausted` per job, `death_handlers`
  globally). A job dying into the Dead set is work silently not happening.
- Deep guide → `references/background-jobs.md`

## Deep guides (read on demand, do not preload)

- Sidekiq's real defaults (25 retries / ~20 days; Dead set 10k jobs / 6 months), `retry: 0` vs
  `retry: false`, the `retry_on`-stacks-on-Sidekiq trap, ActiveJob vs `include Sidekiq::Job`
  (~30% overhead), alerting on the Dead set, why swallowing an exception disables the retry, and
  idempotency keys → `references/background-jobs.md`

Related, owned elsewhere — do not duplicate: the API error envelope →
`../std-api-design/references/errors-rails.md`; row/advisory locks behind idempotency →
`../std-database/references/locking-and-timeouts.md`; alert design →
`../std-monitoring`.
