---
name: security-auditor
description: Audit code for security vulnerabilities, OWASP Top 10 issues, exposed secrets, and compliance gaps. Use this skill whenever someone asks to check security, scan for vulnerabilities, audit authentication, review access control, or says things like "is this secure", "check for secrets", "security review", "audit this for OWASP", "scan for vulnerabilities", or "check our auth flow". Also trigger when someone mentions penetration testing prep, dependency CVE scanning, or security hardening.
agent: security-auditor
context: fork
model: sonnet
---

# Security Auditor

Perform thorough security audits of application code. This skill identifies vulnerabilities, exposed secrets, insecure configurations, and compliance gaps.

## Security Audit Protocol

### Phase 1: Secret Scanning

Scan the entire codebase for hardcoded secrets using these patterns:

#### High-Confidence Patterns
```
# API Keys and Tokens
(?i)(api[_-]?key|apikey)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]
(?i)(access[_-]?token|auth[_-]?token)\s*[:=]\s*['"][A-Za-z0-9_\-\.]{16,}['"]
(?i)(secret[_-]?key|client[_-]?secret)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]

# AWS Credentials
AKIA[0-9A-Z]{16}
(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*['"][A-Za-z0-9/+=]{40}['"]

# Private Keys
-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----

# Database Connection Strings
(?i)(postgres|mysql|mongodb|redis)://[^\s'"]+:[^\s'"]+@

# JWT Secrets
(?i)(jwt[_-]?secret|signing[_-]?key)\s*[:=]\s*['"][^'"]{8,}['"]

# Generic Passwords
(?i)(password|passwd|pwd)\s*[:=]\s*['"][^'"]{4,}['"]
```

#### Files to Check
- `.env` files (should be in `.gitignore`)
- Configuration files (`config.*`, `settings.*`, `*.config.*`)
- Docker files (`docker-compose.*`, `Dockerfile`)
- CI/CD configurations (`.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`)
- Infrastructure as code (`*.tf`, `*.tfvars`, `*.yaml` in deploy directories)

#### Verify .gitignore Coverage
Confirm that `.gitignore` excludes:
- `.env`, `.env.*` (except `.env.example`)
- `*.pem`, `*.key`, `*.p12`
- `credentials.json`, `serviceAccount.json`
- `node_modules/`, `vendor/`, `.terraform/`

### Phase 2: Authentication and Authorization

#### Authentication Checks
1. Password storage uses a strong hashing algorithm (bcrypt, scrypt, or argon2) with appropriate cost factor.
2. Session tokens are cryptographically random, have expiration, and are invalidated on logout.
3. JWT tokens have short expiration, use strong signing algorithms (RS256 or ES256, not HS256 with weak secrets), and validate all claims.
4. Multi-factor authentication is available for privileged accounts.
5. Account lockout or rate limiting protects against brute force.
6. Password reset flows do not reveal whether an account exists.

#### Authorization Checks
1. Every API endpoint has an authorization check — no endpoint is accidentally public.
2. Authorization is checked on the server, not only the client.
3. Resource-level access control (users can only access their own resources).
4. Role/permission checks use a centralized mechanism, not ad-hoc checks scattered in code.
5. Admin endpoints have additional protection (IP allowlisting, separate auth).
6. IDOR (Insecure Direct Object Reference) — user-supplied IDs validated against the current user's permissions.

### Phase 3: Input Validation and Injection

#### SQL Injection
- All database queries use parameterized statements or an ORM.
- Search for string concatenation in queries: `query + userInput`, template literals in SQL.
- Stored procedures also use parameterization.
- Dynamic table/column names (if any) use allowlists, not user input directly.

#### Cross-Site Scripting (XSS)
- All user-generated content is escaped before rendering in HTML.
- Framework's auto-escaping is enabled and not bypassed (`dangerouslySetInnerHTML`, `{!! !!}`, `| safe`).
- Content-Security-Policy header is configured to restrict inline scripts.
- User input in URLs is encoded.

#### Command Injection
- No user input passed to `exec`, `system`, `eval`, `spawn` without sanitization.
- Shell commands use argument arrays, not string interpolation.
- File paths from user input are validated against a base directory (no path traversal).

#### Other Injection Types
- LDAP queries use parameterized methods.
- XML parsers disable external entity processing (XXE prevention).
- Deserialization of untrusted data uses safe deserializers with type restrictions.
- Template injection — user input is not part of template strings evaluated by template engines.

### Phase 4: Data Protection

1. **In Transit**: All communications use TLS 1.2+. HSTS header is set. No mixed content.
2. **At Rest**: Sensitive data (PII, credentials, payment info) is encrypted in the database.
3. **In Logs**: Sensitive fields are redacted from application logs.
4. **In Responses**: API responses do not leak internal data (stack traces, DB schema, internal IDs).
5. **In Errors**: Error messages for users are generic — detailed errors go only to logs.
6. **Retention**: Data retention policies are implemented — old data is purged per requirements.

### Phase 5: Configuration and Infrastructure

1. **CORS**: Origins are explicitly listed — no wildcard (`*`) in production. Credentials mode is restrictive.
2. **CSRF**: Anti-CSRF tokens on all state-changing requests. SameSite cookie attribute set.
3. **Headers**: Security headers configured — `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`.
4. **Rate Limiting**: API endpoints have rate limiting to prevent abuse.
5. **Dependencies**: No known vulnerable dependencies — `bundle exec bundler-audit check --update`
   and `npm audit`/`pnpm audit` pass, and `bundle exec brakeman --exit-on-warn` is clean. Run what
   CI runs (`std-infrastructure/references/ci-pipeline.md`) so findings and the merge gate agree.
6. **Debug Mode**: Debug/development mode is disabled in production configurations.
7. **Default Credentials**: No default admin accounts, passwords, or API keys.

### Phase 6: Dependency Analysis

1. Run dependency audit tools to check for known CVEs.
2. Check for outdated packages with known security patches.
3. Verify that lock files (`package-lock.json`, `yarn.lock`, `Pipfile.lock`) are committed.
4. Review dependency tree for suspicious or abandoned packages.

### Phase 7: Software Bill of Materials (SBOM) and Supply Chain

#### SBOM Generation
1. Generate SBOM in CycloneDX or SPDX format for all application components.
2. Include: direct dependencies, transitive dependencies, versions, licenses, package URLs (purl).
3. Rails: `gem 'cyclonedx-ruby'` or `bundle exec cyclonedx-ruby` to generate `bom.xml`/`bom.json`.
4. React Native: `npx @cyclonedx/cyclonedx-npm --output-file bom.json` for npm dependencies.
5. Store SBOM artifacts alongside releases for traceability.

#### License Compliance
1. Scan all dependencies for license types.
2. **Approved licenses**: MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, PostgreSQL.
3. **Requires review**: LGPL-2.1, LGPL-3.0, MPL-2.0 (copyleft — may require source disclosure).
4. **Prohibited in production**: GPL-2.0, GPL-3.0, AGPL-3.0 (strong copyleft — incompatible with proprietary distribution).
5. Flag any dependency with `UNKNOWN` or missing license.

#### Supply Chain Attestation
1. Verify package integrity: lock files committed, checksums match.
2. Check for typosquatting: compare dependency names against known packages.
3. Review recently added dependencies: new deps added in last 30 days get extra scrutiny.
4. Verify maintainer activity: flag packages with no commits in 12+ months.
5. Check for known supply chain attacks (event-stream pattern, ua-parser-js pattern).

#### SBOM Output
```markdown
## Software Bill of Materials Summary
| Component | Version | License | Risk | Notes |
|-----------|---------|---------|------|-------|
| rails | 7.x.x | MIT | Low | Framework |
| pg | 1.x.x | BSD-2-Clause | Low | PostgreSQL adapter |
| [flagged] | x.x.x | GPL-3.0 | High | License incompatible |
```

## Output Format

### Findings Report

| # | Category | Finding | Severity | CVSS | File:Line | Remediation |
|---|---|---|---|---|---|---|
| 1 | Secrets | AWS access key hardcoded | Critical | 9.8 | config/aws.ts:12 | Move to environment variable or secrets manager |
| 2 | Injection | SQL concatenation in search query | Critical | 9.1 | api/search.ts:45 | Use parameterized query |
| 3 | Auth | No rate limiting on login endpoint | High | 7.5 | api/auth.ts:23 | Add rate limiter middleware |
| 4 | XSS | User bio rendered with dangerouslySetInnerHTML | High | 6.1 | components/Profile.tsx:67 | Use sanitized HTML renderer |
| 5 | Config | CORS allows all origins | Medium | 5.3 | server.ts:15 | Restrict to known domains |

### Severity Levels
- **Critical** (CVSS 9.0-10.0): Immediate exploitation risk. Fix before deploy.
- **High** (CVSS 7.0-8.9): Significant vulnerability. Fix within current sprint.
- **Medium** (CVSS 4.0-6.9): Moderate risk. Fix within next sprint.
- **Low** (CVSS 0.1-3.9): Minor concern. Track and remediate during maintenance.
- **Info**: Best practice recommendation, no direct vulnerability.

### Summary
After the findings table, provide:
1. **Risk Assessment**: Overall security posture (Critical / High / Medium / Low risk).
2. **Top Priority Items**: The 3 most important fixes.
3. **Positive Findings**: Security practices done well.
4. **Recommendations**: Longer-term security improvements.

## Deep guides (read on demand, do not preload)

- The OWASP Top 10 pass, A01–A10, with what to grep for in this stack → `references/security-checklist.md`
