# Security Checklist — OWASP Top 10 Aligned

Comprehensive security checklist based on the OWASP Top 10 (2021). Each category includes detection patterns and remediation guidance.

---

## A01: Broken Access Control

Access control enforces that users cannot act outside of their intended permissions.

### Detection
- [ ] Every API endpoint has explicit authorization middleware or decorator.
- [ ] Resource access validates ownership (user can only access their own data).
- [ ] Admin/management endpoints require elevated privileges.
- [ ] API responses do not include data the user is not authorized to see.
- [ ] Directory listing is disabled on web servers.
- [ ] CORS policy does not use wildcard origins with credentials.
- [ ] JWT tokens are validated completely (signature, expiration, issuer, audience).
- [ ] ID parameters (user ID, order ID) are checked against the authenticated user's permissions.

### Remediation
- Implement centralized access control middleware.
- Default to deny — explicitly grant access rather than restricting it.
- Use resource-based authorization: `authorize(user, 'read', resource)`.
- Log all access control failures for monitoring and alerting.
- Rate limit API calls to minimize automated scanning.
- Invalidate server-side sessions on logout.

---

## A02: Cryptographic Failures

Sensitive data requires proper encryption in transit and at rest.

### Detection
- [ ] All connections use TLS 1.2 or higher (no SSL, no TLS 1.0/1.1).
- [ ] Passwords are hashed with bcrypt (cost >= 12), scrypt, or argon2 — not MD5, SHA1, or SHA256.
- [ ] Encryption keys are not hardcoded — they are loaded from environment or key management service.
- [ ] Sensitive data in database columns is encrypted (PII, payment info, health records).
- [ ] HTTP Strict-Transport-Security header is set with a long max-age.
- [ ] Cookies use `Secure`, `HttpOnly`, and `SameSite` attributes.
- [ ] Cryptographic randomness uses `crypto.randomBytes` or equivalent — not `Math.random`.

### Remediation
- Use well-known cryptographic libraries — never implement crypto from scratch.
- Classify data by sensitivity level and apply encryption accordingly.
- Rotate encryption keys on a defined schedule.
- Configure TLS with strong cipher suites and forward secrecy.
- Disable caching for responses containing sensitive data.

---

## A03: Injection

Untrusted data sent to an interpreter as part of a command or query.

### Detection
- [ ] SQL queries use parameterized statements — search for string concatenation in queries.
- [ ] NoSQL queries do not allow operator injection (`$gt`, `$ne` in MongoDB).
- [ ] Shell commands do not include user input — or use argument arrays, not string building.
- [ ] LDAP queries use parameterized methods.
- [ ] ORM queries do not use raw SQL with user input.
- [ ] GraphQL queries have depth and complexity limits.
- [ ] User input is never passed to `eval()`, `Function()`, or template compilation.

### Remediation
- Use parameterized queries or prepared statements for all database access.
- Validate and sanitize input using allowlists (not denylists).
- Escape special characters according to the context (SQL, HTML, shell).
- Use ORMs with query builders that handle escaping.
- Apply least privilege to database accounts — read-only where possible.

---

## A04: Insecure Design

Security flaws in the design, not just the implementation.

### Detection
- [ ] Threat modeling has been performed for critical features.
- [ ] Business logic includes abuse-case testing (what if a user tries to misuse this?).
- [ ] Rate limiting exists on authentication, registration, and sensitive operations.
- [ ] Resource limits prevent denial of service (file size, request size, query complexity).
- [ ] Multi-step processes cannot be bypassed by skipping steps.
- [ ] Fail-safe defaults — system fails closed, not open.

### Remediation
- Conduct threat modeling during design phase.
- Define security requirements alongside functional requirements.
- Write abuse stories alongside user stories.
- Use established secure design patterns (authorization frameworks, validated libraries).
- Review design with security-focused team members.

---

## A05: Security Misconfiguration

Insecure default configurations, incomplete configurations, or ad-hoc configurations.

### Detection
- [ ] Debug mode is disabled in production (`DEBUG=false`, no stack traces in responses).
- [ ] Default credentials are changed (admin/admin, root/root).
- [ ] Unnecessary features, ports, services, and pages are disabled.
- [ ] Security headers are configured (CSP, X-Frame-Options, X-Content-Type-Options).
- [ ] Error handling does not reveal stack traces, SQL queries, or internal paths.
- [ ] Cloud storage permissions are not public by default.
- [ ] Directory listing is disabled.
- [ ] Software and dependencies are up to date.

### Remediation
- Automate environment configuration using infrastructure-as-code.
- Use hardened base configurations as templates.
- Review and remove unnecessary features, components, and documentation.
- Conduct regular configuration audits across all environments.
- Implement a repeatable hardening process for new deployments.

---

## A06: Vulnerable and Outdated Components

Using components (libraries, frameworks) with known vulnerabilities.

### Detection
- [ ] No dependencies with known critical or high CVEs (`npm audit`, `pip-audit`, `bundler-audit`).
- [ ] Lock files are committed and reviewed for unexpected changes.
- [ ] Dependencies are not abandoned (last update > 2 years with open security issues).
- [ ] Only necessary dependencies are installed — no unused packages.
- [ ] Dependency sources are trusted registries (not arbitrary Git URLs or unknown packages).

### Remediation
- Run automated dependency scanning in CI/CD pipeline.
- Subscribe to security advisories for key dependencies.
- Update dependencies regularly — automate with Dependabot, Renovate, or similar.
- Remove unused dependencies.
- Evaluate alternatives for abandoned or poorly maintained packages.

---

## A07: Identification and Authentication Failures

Weaknesses in authentication mechanisms.

### Detection
- [ ] Passwords require minimum 8 characters with complexity or length-based policy.
- [ ] Credential stuffing is mitigated with rate limiting and account lockout.
- [ ] Session IDs are not in URLs.
- [ ] Session tokens are regenerated after login.
- [ ] Multi-factor authentication is available for sensitive accounts.
- [ ] Password recovery does not reveal whether an account exists.
- [ ] Failed login attempts are logged with details (IP, timestamp) but not the password.

### Remediation
- Use a well-tested authentication library or framework (not custom implementation).
- Implement progressive delays or account lockout after failed attempts.
- Use secure session management with server-side session storage.
- Enforce password policies aligned with current NIST guidelines.
- Implement MFA for admin and privileged accounts.

---

## A08: Software and Data Integrity Failures

Assumptions about software updates, critical data, or CI/CD pipelines without verifying integrity.

### Detection
- [ ] CI/CD pipeline has access controls — not everyone can modify build steps.
- [ ] Dependencies come from trusted sources with integrity verification (checksums, signatures).
- [ ] Deserialization of untrusted data is avoided or uses safe methods with type restrictions.
- [ ] Auto-update mechanisms verify signatures before applying updates.
- [ ] Code review is required before merging to production branches.

### Remediation
- Verify digital signatures on software and data.
- Use dependency lock files with integrity hashes.
- Implement code review and approval gates in CI/CD.
- Avoid deserializing untrusted data — use safe formats (JSON) with schema validation.
- Segregate CI/CD pipeline duties.

---

## A09: Security Logging and Monitoring Failures

Insufficient logging, monitoring, and alerting to detect and respond to breaches.

### Detection
- [ ] Authentication events (login, logout, failed attempts) are logged.
- [ ] Authorization failures are logged.
- [ ] Input validation failures are logged.
- [ ] Logs include sufficient context: timestamp, user ID, IP address, action, resource.
- [ ] Logs do NOT include sensitive data (passwords, tokens, PII).
- [ ] Log integrity is protected — logs cannot be tampered with by application users.
- [ ] Alerting exists for suspicious patterns (multiple failed logins, unusual access patterns).

### Remediation
- Implement structured logging with consistent fields.
- Centralize logs in a SIEM or log aggregation platform.
- Define and implement alerting rules for security events.
- Establish an incident response procedure triggered by alerts.
- Retain logs for a period aligned with compliance requirements.
- Conduct regular log reviews.

---

## A10: Server-Side Request Forgery (SSRF)

Application fetches a remote resource without validating the user-supplied URL.

### Detection
- [ ] User-supplied URLs are validated against an allowlist of permitted domains.
- [ ] Internal network addresses (10.x, 172.16.x, 192.168.x, 127.x, ::1) are blocked in URL inputs.
- [ ] URL redirects are not followed blindly — redirect targets are validated.
- [ ] DNS rebinding is mitigated (resolve DNS before making the request, verify the IP).
- [ ] Cloud metadata endpoints (169.254.169.254) are explicitly blocked.

### Remediation
- Validate and sanitize all user-supplied URLs on the server side.
- Use an allowlist of permitted protocols, domains, and ports.
- Deny access to private IP ranges and cloud metadata URLs.
- Do not send raw server responses to the client — validate and filter response content.
- Implement network-level segmentation to limit SSRF impact.
