---
name: compliance-auditor
description: Audit and generate compliance documentation for regulatory frameworks including SOC2, HIPAA, PCI-DSS, and GDPR. Use this skill whenever someone asks about compliance, regulatory requirements, data protection, or says things like "SOC2 audit", "HIPAA compliance", "PCI-DSS requirements", "GDPR review", "compliance checklist", "data protection audit", "regulatory controls", "privacy impact assessment", or "control mapping". Also trigger for data classification, retention policies, or audit evidence gathering.
model: sonnet
---

# Compliance Auditor

Audit application code, infrastructure, and processes against regulatory compliance frameworks. Generate compliance documentation, control mappings, and gap analysis reports.

## Supported Frameworks

### SOC 2 (Type I & Type II)

Trust Service Criteria coverage:

#### CC1 — Control Environment
- [ ] Security policies documented and reviewed annually
- [ ] Roles and responsibilities defined for security operations
- [ ] Background checks for personnel with system access
- [ ] Security awareness training program in place

#### CC2 — Communication and Information
- [ ] System description document maintained
- [ ] Security policies communicated to all personnel
- [ ] Incident reporting procedures documented and accessible

#### CC3 — Risk Assessment
- [ ] Annual risk assessment conducted
- [ ] Risk register maintained with owner, likelihood, impact, mitigation
- [ ] Third-party vendor risk assessments performed

#### CC4 — Monitoring Activities
- [ ] Continuous monitoring of security controls (CloudWatch, Sentry)
- [ ] Regular vulnerability scanning (dependency audit, SAST)
- [ ] Penetration testing performed annually

#### CC5 — Control Activities
- [ ] Access control policies enforced (Pundit, Devise)
- [ ] Change management process (PR reviews, CI gates)
- [ ] Encryption at rest and in transit (RDS encryption, TLS)

#### CC6 — Logical and Physical Access Controls
- [ ] MFA enforced for production access (AWS IAM)
- [ ] Least privilege principle applied (IAM roles, DB permissions)
- [ ] Access reviews conducted quarterly
- [ ] Production access logged and audited
- [ ] SSH key rotation policy

#### CC7 — System Operations
- [ ] Incident response plan documented and tested
- [ ] Backup and recovery procedures tested
- [ ] Capacity planning and monitoring in place
- [ ] System health checks automated

#### CC8 — Change Management
- [ ] All changes go through PR review
- [ ] CI/CD pipeline enforces tests and security scans
- [ ] Rollback procedures documented for every deployment
- [ ] Change log maintained (CHANGELOG.md)

#### CC9 — Risk Mitigation
- [ ] Business continuity plan documented
- [ ] Disaster recovery tested (RDS restore, ECS redeployment)
- [ ] Data replication across availability zones

### HIPAA (Health Insurance Portability and Accountability Act)

Applicable when handling Protected Health Information (PHI):

#### Administrative Safeguards
- [ ] Security officer designated
- [ ] Workforce access management (role-based, need-to-know)
- [ ] Security awareness and training
- [ ] Incident response procedures for PHI breaches
- [ ] Business Associate Agreements (BAA) with all vendors handling PHI

#### Technical Safeguards
- [ ] Access control: unique user identification, emergency access, automatic logoff, encryption
- [ ] Audit controls: record and examine system activity (audit-logger.py, CloudWatch)
- [ ] Integrity controls: data validation, error correction
- [ ] Transmission security: TLS 1.2+ for all PHI in transit
- [ ] Encryption: AES-256 for PHI at rest (RDS encryption, S3 SSE)

#### Physical Safeguards (AWS Managed)
- [ ] AWS data centers meet HIPAA physical security requirements
- [ ] BAA signed with AWS for covered services

### PCI-DSS (Payment Card Industry Data Security Standard)

Applicable when processing, storing, or transmitting cardholder data:

#### Requirements Checklist
- [ ] **Req 1-2**: Network segmentation, firewall rules, no default credentials
- [ ] **Req 3**: Cardholder data encrypted at rest, no storage of CVV/PIN
- [ ] **Req 4**: TLS 1.2+ for transmission of cardholder data
- [ ] **Req 5**: Anti-malware protection, vulnerability management
- [ ] **Req 6**: Secure development (OWASP Top 10, code review, security testing)
- [ ] **Req 7-8**: Access control, unique IDs, MFA for admin access
- [ ] **Req 9**: Physical access controls (AWS managed)
- [ ] **Req 10**: Logging and monitoring of all access to cardholder data
- [ ] **Req 11**: Regular vulnerability scans, penetration tests
- [ ] **Req 12**: Information security policy, incident response plan

#### Scope Reduction
- Use a PCI-compliant payment processor (Stripe, Adyen) to reduce scope.
- Never store full card numbers — use tokenization.
- Isolate payment processing in a separate service with restricted network access.

### GDPR (General Data Protection Regulation)

Applicable when processing personal data of EU/EEA residents:

#### Data Processing Principles (Article 5)
- [ ] **Lawfulness**: Legal basis for each processing activity documented
- [ ] **Purpose limitation**: Data collected for specified, explicit purposes
- [ ] **Data minimization**: Only necessary data collected
- [ ] **Accuracy**: Mechanisms to keep data accurate and up-to-date
- [ ] **Storage limitation**: Retention periods defined and enforced
- [ ] **Integrity & confidentiality**: Encryption, access controls, audit logs

#### Data Subject Rights (Articles 15-22)
- [ ] Right of access: API endpoint to export user data
- [ ] Right to rectification: Users can update their data
- [ ] Right to erasure: Account deletion with cascade (soft delete + scheduled hard delete)
- [ ] Right to portability: Data export in machine-readable format (JSON/CSV)
- [ ] Right to restrict processing: Flag to pause processing without deletion
- [ ] Right to object: Opt-out mechanism for marketing/profiling

#### Technical Implementation
```ruby
# Data export endpoint
# GET /api/v1/me/data_export
class Api::V1::DataExportController < ApplicationController
  def show
    authorize current_user, :export?
    data = UserDataExportService.call(current_user)
    send_data data.to_json, filename: "user_data_#{current_user.id}.json"
  end
end

# Account deletion (GDPR erasure)
class AccountDeletionService
  def call(user)
    user.anonymize_personal_data!    # Replace PII with anonymized values
    user.update!(deleted_at: Time.current, deletion_scheduled_at: 30.days.from_now)
    AccountDeletionJob.perform_at(user.deletion_scheduled_at, user.id)
  end
end
```

#### Privacy Impact Assessment (PIA)
For new features processing personal data, document:
1. What personal data is collected
2. Why it is needed (legal basis)
3. How it is stored and protected
4. Who has access
5. Retention period
6. Cross-border transfer considerations

## Audit Protocol

### Step 1: Scope Definition
1. Identify applicable frameworks based on data types and jurisdictions.
2. Map system components to compliance boundaries.
3. Document third-party services and their compliance certifications.

### Step 2: Control Assessment
1. For each applicable control, verify implementation in code and infrastructure.
2. Check for evidence: logs, configurations, policies, test results.
3. Mark each control as: Compliant, Partially Compliant, Non-Compliant, Not Applicable.

### Step 3: Gap Analysis
1. Identify non-compliant and partially compliant controls.
2. Assess risk level of each gap (Critical, High, Medium, Low).
3. Propose remediation with effort estimate (S/M/L/XL).

### Step 4: Evidence Collection
Document evidence for each compliant control:
- Code references (file:line for access controls, encryption, validation)
- Configuration files (Terraform, settings, environment variables)
- CI/CD pipeline definitions (security scans, test gates)
- Monitoring dashboards (CloudWatch, Sentry alerts)
- Process documentation (runbooks, incident response plans)

## Output Format

### Compliance Report

```markdown
# Compliance Audit Report — [Framework]
**Date**: YYYY-MM-DD | **Auditor**: Claude | **Scope**: [System/Component]

## Summary
| Status | Count |
|--------|-------|
| Compliant | XX |
| Partially Compliant | XX |
| Non-Compliant | XX |
| Not Applicable | XX |

## Findings
| # | Control | Status | Evidence | Gap | Remediation | Priority |
|---|---------|--------|----------|-----|-------------|----------|

## Risk Assessment
[Overall compliance posture and top risks]

## Remediation Roadmap
| Priority | Item | Effort | Owner | Target Date |
|----------|------|--------|-------|-------------|
```
