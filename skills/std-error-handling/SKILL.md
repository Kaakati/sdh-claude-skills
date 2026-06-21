---
name: std-error-handling
description: Error handling standards across Rails, React Native, Sidekiq, and API responses — Result objects, custom errors, retry/discard, consistent error JSON. Use when handling errors.
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
All API errors must follow this structure:
```json
{
  "error": "Human-readable error message",
  "code": 422,
  "type": "validation_error",
  "details": {
    "field": ["specific error"]
  },
  "request_id": "uuid-for-tracing"
}
```

Error types: `validation_error`, `authentication_error`, `authorization_error`, `not_found`, `rate_limited`, `server_error`

## Background Jobs (Sidekiq)
- Configure `retry_on` for transient errors (network, timeouts)
- Configure `discard_on` for permanent errors (record not found, invalid data)
- Dead letter jobs must be monitored and alerted on
- Never swallow errors silently in jobs — always log or report
