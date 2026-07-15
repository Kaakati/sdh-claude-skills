---
name: std-security
description: Security standards — OWASP Top 10, input validation, parameterized queries, secret management, auth, web headers. Apply when handling user input, auth, secrets, or data access.
paths:
  - "**/*.rb"
  - "**/*.py"
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.js"
  - "**/*.jsx"
---

# Security Standards

Universal security rules for all code. Security is a first-class concern, not an afterthought.

## OWASP Top 10 Awareness

Every developer and AI agent must account for these risks in all code:

1. **Broken Access Control** — Enforce authorization on every protected resource. Deny by default.
2. **Cryptographic Failures** — Use strong, current algorithms (AES-256, bcrypt/argon2). Never roll your own crypto.
3. **Injection** — Parameterize all queries and commands. Never concatenate user input into SQL, OS commands, or LDAP queries.
4. **Insecure Design** — Threat model during design. Apply defense in depth.
5. **Security Misconfiguration** — Disable debug modes in production. Remove default credentials. Harden server configs.
6. **Vulnerable Components** — Audit dependencies. No known critical CVEs in production.
7. **Authentication Failures** — Enforce strong passwords, rate limit login attempts, implement MFA where possible.
8. **Data Integrity Failures** — Verify signatures on updates and serialized data. Use SRI for CDN assets.
9. **Logging & Monitoring Failures** — Log security events. Alert on anomalies. Retain audit logs.
10. **SSRF** — Validate and sanitize all URLs. Block requests to internal networks from user-supplied URLs.

## Input Validation

- Validate all user input on the server side, regardless of client-side validation.
- Use allowlists over denylists where possible.
- Validate type, length, range, and format for all inputs.
- Use schema validation libraries (Zod, Joi, Pydantic) at API boundaries:
  ```typescript
  const CreateUserSchema = z.object({
    email: z.string().email().max(255),
    name: z.string().min(1).max(100),
    role: z.enum(["admin", "user", "viewer"]),
  });
  ```
- Reject unexpected fields — do not silently pass them through.

## SQL and Data Access

- **Parameterized queries only**. No string concatenation or template literals for SQL:
  ```typescript
  // NEVER do this
  db.query(`SELECT * FROM users WHERE id = '${userId}'`);

  // Always do this
  db.query("SELECT * FROM users WHERE id = $1", [userId]);
  ```
- Use an ORM or query builder with built-in parameterization.
- Apply the principle of least privilege to database credentials.
- Encrypt sensitive data at rest (PII, financial data, health records).

## Secret Management

- **Never hardcode** secrets, API keys, tokens, or passwords in source code.
- Use environment variables for configuration. Load from `.env` in development only.
- `.env` files must be in `.gitignore` — never committed to version control.
- Use a secret manager in production (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault).
- Rotate secrets regularly. Revoke compromised secrets immediately.
- Provide `.env.example` with placeholder values for onboarding.

## Dependency Security

- Run `npm audit` / `pip audit` / equivalent in CI on every build.
- No dependencies with known critical or high severity vulnerabilities in production.
- Pin dependency versions in lock files. Review dependency updates before merging.
- Minimize dependency surface — evaluate whether a dependency is truly needed before adding it.
- Use tools like Dependabot, Snyk, or Renovate for automated vulnerability alerts.

## Authentication and Authorization

- Verify authentication on every protected route. Do not rely on client-side checks alone.
- Implement authorization checks at the service layer, not just the controller:
  ```typescript
  // Check both authentication AND authorization
  async function getOrder(orderId: string, currentUser: User) {
    const order = await orderRepo.findById(orderId);
    if (!order) throw new NotFoundError("Order", orderId);
    if (order.userId !== currentUser.id && !currentUser.isAdmin) {
      throw new ForbiddenError("Not authorized to view this order");
    }
    return order;
  }
  ```
- **The check must be impossible to forget, not merely written.** The common Broken Access
  Control bug is not a wrong policy — it is a correct policy nobody invoked, which returns
  `200 OK` with another user's data and raises nothing. Wire the framework's own enforcement:
  in Rails that is `after_action :verify_authorized` / `verify_policy_scoped` (Pundit) — see
  `../std-rails-conventions/references/authorization.md`.
- **Filter collections; don't just authorize them.** Asking "may you list orders?" is not the
  same as returning only *your* orders. Scope the query (`policy_scope`).
- Prefer **404 over 403** for a record the caller may not see — a 403 confirms it exists.
- Use short-lived tokens (JWTs with reasonable expiry). Implement refresh token rotation.
- **Sign-out must revoke**, not just discard client-side. `devise-jwt` does not revoke by
  default; a token kept after logout keeps working until expiry.
- Hash passwords with bcrypt (cost factor 12+) or argon2. Never use MD5 or SHA for passwords.
- Implement account lockout or exponential backoff after repeated failed login attempts.
- **Mounted engines authenticate too — `Sidekiq::Web` is the one that gets forgotten.**
  `mount Sidekiq::Web => '/sidekiq'` with nothing wrapping it publishes every job's *arguments*
  (user ids, emails, tokens routinely ride along) and lets any visitor retry or kill jobs. It
  raises nothing and looks finished. Wrap the mount in an `authenticate`/`constraints` block, or
  protect the Rack app itself in `config/initializers/sidekiq.rb`:
  ```ruby
  # config/initializers/sidekiq.rb  ✅  the fit for an API-only app
  require "sidekiq/web"
  Sidekiq::Web.use Rack::Auth::Basic do |user, password|
    ActiveSupport::SecurityUtils.secure_compare(user, ENV.fetch("SIDEKIQ_USER")) &
      ActiveSupport::SecurityUtils.secure_compare(password, ENV.fetch("SIDEKIQ_PASSWORD"))
  end
  ```
  **Know which recipe you are copying.** Devise's `authenticate :user do ... end` route helper
  needs Warden's session middleware, which an **API-only** Rails app does not load by default —
  so the recipe most blog posts give you can be present and still authenticate nobody. Verify it
  rejects an anonymous request; do not assume it. `rails-routes-checker.py` warns on an
  unguarded mount.

## Web Security Headers and Protections

- **CORS**: Configure explicitly. Never use `Access-Control-Allow-Origin: *` in production with credentials.
- **CSRF**: Use anti-CSRF tokens for state-changing requests. SameSite cookie attribute as defense in depth.
- **XSS Prevention**:
  - Escape all user-generated content before rendering in HTML.
  - Use Content-Security-Policy headers to restrict script sources.
  - Set `HttpOnly` and `Secure` flags on session cookies.
- **Security Headers**: Set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`.
- **Rate Limiting**: Apply rate limits to all public endpoints, especially authentication routes.

## Sensitive Data Handling

- Classify data by sensitivity level. Apply appropriate controls per classification.
- Never log passwords, tokens, session IDs, credit card numbers, or PII.
- Mask sensitive data in error messages and API responses.
- Use TLS 1.2+ for all data in transit. No HTTP — only HTTPS.
- Implement data retention policies. Delete data that is no longer needed.
