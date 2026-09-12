# Role Management UX — the screens where access is granted

Load-bearing rules restated (these hold even if you read nothing else):

1. **These screens read the matrix; they never become a second one.** Permission keys are defined
   in code. An admin screen assigns roles — and, only with DB-backed assignments, edits custom roles
   built from those keys. It never invents a key.
2. **The grant rules show up in the UI before the API refuses.** Roles, keys, and scopes beyond the
   granter's own are not rendered. Your own role, the last Owner, and a member who already exceeds
   you are disabled with a visible reason. The API still enforces every one of them.
3. **Least privilege is the default in every picker.** The narrowest role is preselected; wider
   access is a deliberate choice, reviewed as a diff before it saves.
4. **Dangerous grants confirm by consequence:** what becomes possible, for how many people.
5. **Every change is an audit event written by the server** in the same transaction. The audit log
   is append-only on screen too — no edit, no delete, for anyone.
6. **"View as" is read-only, reasoned, time-boxed, bannered, and audited on both sides.** Acting as
   someone is a separate, rarer grant.

These screens follow the three-state rule in `@skills/ui-ux-patterns/references/role-based-ux.md` and
render the states in `@skills/ui-ux-patterns/references/role-based-ux-states.md`. The rules they
apply are owned by `@skills/access-control-designer/references/permission-matrix.md`.

---

## The screens and their gates

The keys below extend the sample catalog. Like every key, each ships granted to no role until the
matrix grants it on purpose.

| Screen | Gate key | Enforces |
|---|---|---|
| Members list | `members.read` | The scope column: `team` sees their teams' members |
| Invite members | `members.invite` | Grant rule 1: roles offered fit within the inviter's own |
| Change a member's role | `roles.assign` | Grant rules 1–3 |
| Remove a member | `members.remove` | Grant rule 3: the last-owner guard |
| Role catalog | `roles.read` | System roles read-only |
| Custom role or permission set editor | `roles.update` (DB-backed only) | Grant rule 1 per key and scope; locked on plans without custom roles |
| Audit log | `audit_events.read` | Append-only; exports are themselves audited |
| View as | `members.view_as` | No escalation; same organization only |
| Act as (impersonation) | `members.impersonate` | As above, plus writes attributed to both identities |
| API keys and secrets | `api_keys.read`, `api_keys.create` | Reveals and copies logged |

## Role catalog

- **Describe each role by who it is for, then by what it can and can't do.** GitHub describes each
  of its five repository roles — Read, Triage, Write, Maintain, Admin — by the people it suits, and
  asks admins to "Choose the role that best fits each person or team's function in your project
  without giving people more access to the project than they need" (GitHub Docs — Repository roles
  for an organization). Stripe publishes can and can't lists per job-function role: "This role is
  for people who need to view payments, balance, and connected accounts, but can’t edit any of
  them" (Stripe Docs — User roles).
- **A ladder only when each rung contains the one below.** GitHub's roles escalate — Maintain stops
  short of sensitive and destructive actions that Admin holds — so a ladder reads true there. B2B
  job roles usually don't: a finance Viewer reads more than a sales Member. Present those as a
  catalog of job cards, never as a rank.
- **A compare view is the matrix, read-only:** resources down the side, roles across, scopes in the
  cells — in the product's words ("Their own orders", "Whole organization"), not key names.
- **Flag the roles that can grant.** Stripe warns that roles able to invite users are high-risk if
  compromised (Stripe Docs — User roles). Mark roles holding `members.invite` or `roles.assign` as
  sensitive in the catalog and in every picker.
- **System roles are read-only.** A custom role starts as a copy of one, so the entry point is
  Duplicate, not Edit.
- **Custom roles may be a plan feature**, and then follow the three-state rule: GitHub offers custom
  repository roles only on GitHub Enterprise Cloud (GitHub Docs — Repository roles for an
  organization). For a role holding `roles.update` on a plan without them, "Create custom role" is
  locked, not hidden.
- **The model underneath:** "Each user is assigned one or more roles, and each role is assigned one
  or more privileges that are permitted to users in that role", with role hierarchies and mutually
  exclusive roles as part of the reference model (NIST CSRC — Role Based Access Control (RBAC)).

## Permission sets layered on roles

Salesforce layers permission sets over a base profile — "Permission sets are bundles of settings and
permissions that can be applied to users without changing their profiles" — to fit access to
specific job functions and tasks under least privilege (Salesforce Trailhead — Improve Salesforce
Security Practices).

- **Additive only.** A set grants keys at scopes and never subtracts. Effective access is the union
  across the member's roles and sets, within one organization — the same union as multi-role users
  in `@skills/ui-ux-patterns/references/role-based-ux.md`.
- **A DB-backed feature.** Sets are runtime assignments, so they are decided in the same ADR as
  custom roles.
- **Show where every effective grant comes from.** On a member's page: "Refund orders — from Finance
  Clerk", "Export orders — from Month-end close". Without the source, nobody can remove the one grant
  that should go.
- **Name sets by task** ("Month-end close"), never by the person who first needed one.

## Permission matrix editor

For a custom role or a permission set: rows are keys grouped by resource, and each row is a grant
plus a scope.

- **Cells are scopes, not booleans.** A granted row carries a scope choice in words — "Their own",
  "Their teams'", "Whole organization" — and only the scopes the resource supports.
- **Group rows are tri-state checkboxes.** A resource header is checked when every key in it is
  granted, unchecked when none is, and partially checked otherwise: the APG's "tri-state checkboxes,
  which allow an additional third state known as partially checked", exposed as
  `aria-checked="mixed"` inside a `role="group"` labelled by `aria-labelledby` (W3C WAI APG —
  Checkbox Pattern). Checking the header grants every key in the group at the narrowest scope;
  unchecking revokes them all. Whichever primitive renders it, confirm `mixed` in the accessibility
  tree — the base-correct Checkbox API → the `std-shadcn-ui` skill.
- **Only what the editor may grant is offered.** Keys the granter does not hold, and scopes wider
  than their own, are not rendered (grant rule 1). If the role being edited already exceeds the
  granter, the editor opens read-only with the reason: "This role includes access you don't hold —
  an Owner can change it."
- **Diff before save.** The save step lists keys added and removed, scopes widened and narrowed, and
  how many members hold the role — the change as a reviewer reads it, not the whole matrix again.
- **Dangerous grants confirm by consequence.** Adding a sensitive key (`roles.assign`,
  `members.invite`, `members.impersonate`, `billing.update`, `orders.refund`) or widening any key to
  the whole organization opens a confirmation that says what becomes possible and for whom: "12
  members will be able to invite people and give them any role you hold." The confirm button names
  the change — "Grant invite access to 12 members" — never "OK".
- **Entitlement-gated keys show locked** on plans without the feature, like any locked control.

## Invite and assign

- **Invite:** addresses, then a role picker. The picker lists only roles that fit within the
  inviter's own grants (grant rule 1), preselects the narrowest, shows each role's one-line audience
  and its can and can't summary, and carries the sensitive flag.
- **Pending invites** are their own list — the address, the role each will receive, Resend, Revoke.
- **Changing a role** shows from → to and the effective access that results. For a member with
  several roles or sets, show the union with its sources.
- **Your own row:** the role control is permitted and blocked by record state — disabled, with "You
  can't change your own role — another admin can" (grant rule 2, `reasonCode: "SELF_GRANT"`).
- **A member whose current role exceeds yours:** disabled, with "Owners are changed by an Owner"
  (grant rule 1, `reasonCode: "EXCEEDS_GRANTER"`).
- **After save**, the affected member's permissions version bumps and their open sessions catch up
  (`@skills/access-control-designer/references/ui-gates.md`); they see "Your access changed", not a
  sidebar that shuffles on its own.

## Separation of duties

- **Per record — creator ≠ approver — is record state.** Approve is disabled with "You created this
  order — another manager approves it" (`reasonCode: "SELF_APPROVAL"`), as the matrix flags it.
- **Per assignment — mutually exclusive roles.** NIST's RBAC model includes mutually exclusive roles
  (NIST CSRC — Role Based Access Control (RBAC)). In the picker, a role that conflicts with one the
  member already holds is disabled with the conflict named: "Can't be combined with Payment
  Creator". The API refuses the combination as well.
- **The pairs live in the matrix**, where grants are reviewed; the UI reads them and never hard-codes
  them.

## Last-owner guard

- **The last Owner's role control, their Remove, and their own Leave organization are disabled**,
  with "An organization needs at least one Owner — make someone else Owner first" and a link that
  does exactly that (`reasonCode: "LAST_OWNER"`).
- **Handle the race anyway.** Two Owners demoting each other at the same moment both see enabled
  controls; the server rechecks under a lock (grant rule 3) and refuses one. Render the refusal from
  the envelope's `code`, then refetch the members list — never assume the save landed.

## Audit log

GitHub's organization audit log records "who performed the action, what the action was, and when it
was performed"; only organization owners see it; it filters by actor, action, repository, date, and
country, and exports as JSON or CSV (GitHub Docs — Reviewing the audit log for your organization).

- **Columns:** when (absolute, in the viewer's time zone), actor, action in words, target (the member
  or record affected), change (from → to), and where from. OWASP's minimum for each event is when,
  where, who, and what (OWASP Cheat Sheet Series — Logging).
- **What must appear:** authorization failures, user administration and privilege changes,
  administrative access, and access to sensitive data (OWASP Cheat Sheet Series — Logging) — here,
  every invite, role change, removal, set assignment, custom role edit, impersonation start, end, and
  action, and every secret reveal or copy.
- **What must not:** passwords, session ids, tokens, keys, payment data, and personal data are left
  out or masked (OWASP Cheat Sheet Series — Logging). The row reads "API key ending 4821 revealed",
  never the key.
- **Filters** by actor, action, target, and date range; **export** as CSV or JSON — and the export is
  itself an audited event.
- **Append-only on screen.** No role holds a key to edit or delete an event, so no such control
  exists. Events are written server-side with the change they record; the client never writes one
  (grant rule 4).
- **Rows outlive their subjects.** An event about a removed member still reads "Dana Reyes
  (removed)", because the name at the time is stored with the event.

## Impersonation and "view as"

Two powers, two keys:

| | View as | Act as (impersonation) |
|---|---|---|
| Answers | "What does Dana see?" | "Do this as Dana" |
| Key | `members.view_as` | `members.impersonate` — granted to fewer people |
| Writes | None | Allowed, attributed to both identities; destructive actions still blocked |

RFC 8693 draws the same line. In impersonation, "When principal A impersonates principal B, A is
given all the rights that B has within some defined rights context"; in delegation, A keeps its own
identity and acts for B; the `act` claim names the acting party (IETF — RFC 8693: OAuth 2.0 Token
Exchange). Carry both identities — actor and subject — in the session, so server-side authorization,
the audit log, and the banner all know who is really acting.

**Starting**

- **A reason, required.** GitHub: "For each impersonation session, you need to provide a reason for
  the impersonation" (GitHub Docs — Impersonating a user). WorkOS: "The reason is required and will
  be recorded internally on the session.created event" (WorkOS Docs — Impersonation (AuthKit)). A
  free-text field that takes a ticket reference, not a preset "Support".
- **A time box.** GitHub limits a session to one hour; WorkOS sessions expire after 60 minutes. Show
  the time left; expiry ends the session rather than extending it quietly.
- **No escalation.** Nobody views or acts as a member whose grants exceed their own, and never
  across organizations. Platform staff come from the separate staff model, never a membership row —
  the `access-control-designer` skill.

**During**

- **Evaluated by the server, as the member.** A GitHub impersonation session carries exactly the
  user's access. Never simulate by filtering the admin's own rules in the client — that
  approximation is where the bug being chased hides.
- **A persistent, visually distinct frame.** GitHub shows a banner across the top with the way back
  (GitHub Docs — Impersonating a user, Enterprise Server 3.20); WorkOS renders a distinct frame with
  a stop control (WorkOS Docs — Impersonation (AuthKit)). Not dismissible, on every screen, naming
  the member and role ("Viewing as Dana Reyes — Warehouse Lead"), with Exit and the time left;
  carried by text and position, not colour alone.
- **No destructive actions by default.** Even act-as leaves deletions, refunds, role and billing
  changes, security settings, and secret reveals disabled, with "Not available while acting as Dana".
  A product that needs one of them grants it as a further, audited exception.

**Around it**

- **Audited on both sides.** "Actions you perform during an impersonation session are recorded as
  events in the enterprise audit log, as well as the impersonated user's security log" (GitHub Docs —
  Impersonating a user, Enterprise Server 3.20). Record start, end, reason, and every action, each
  with actor and subject.
- **The member is told.** GitHub emails the impersonated user, and that email cannot be turned off
  (GitHub Docs — Impersonating a user). Say who, when, and why.

## Masked secrets inputs

API keys, webhook signing secrets, SSO certificates.

- **Masked by default, revealed on purpose.** Helios hides secret keys, tokens, variables, and
  certificates behind a show/hide toggle, with an optional copy button — and warns "This component is
  meant for visual obfuscation only" (HashiCorp Helios — Masked Input). The server decides whether
  this role receives the value at all; a role without the read grant gets the last characters and no
  toggle — not a disabled one.
- **Reveal follows GOV.UK's password input:** "Hide passwords by default until the user chooses to
  show it using the 'show' button"; each toggle labelled for its own field ("Show webhook secret");
  paste allowed; `spellcheck="false"` (GOV.UK Design System — Password input).
- **Show once, where the product can re-issue.** A newly created API key is shown in full once, with
  Copy; afterwards the screen shows "ending in 4821" and offers Roll, not Reveal.
- **Every reveal and copy is logged** as access to sensitive data, naming the secret and never
  containing it (OWASP Cheat Sheet Series — Logging).

## How the screens map to the grant rules

| Grant rule (`permission-matrix.md`) | Where it shows | What renders |
|---|---|---|
| 1 · A grant fits within the granter's own permissions | Invite, change role, matrix editor | Roles, keys, and scopes beyond the granter: **not rendered**. A member or role already beyond them: **disabled**, with the reason |
| 2 · No self-grant | Your own row | Role control **disabled**: "You can't change your own role — another admin can" |
| 3 · Last-owner guard | The last Owner's row; Leave organization | Role control, Remove, and Leave **disabled**, with the way forward; the race handled on refusal |
| 4 · Audit in the same transaction | Audit log | The event appears with the change; no client-written events; no edit or delete |
| 5 · A role change bumps the permissions version | The affected member's session | `['me']` refetches, nav and actions re-derive, "Your access changed" |
| Separation of duties | Record actions; role picker | `SELF_APPROVAL` disabled with its reason; conflicting roles disabled in the picker |
| Platform staff are not a customer role | View as, act as | Staff sessions come from the staff model, never a membership row |

## Checklist

- [ ] Every admin screen gated by its own key; none of those keys is `*.manage`
- [ ] Role catalog: each role described by audience with can and can't lists; sensitive roles flagged; a ladder only where rungs contain each other
- [ ] Pickers list only roles within the granter's grants and preselect the narrowest
- [ ] Matrix editor: scopes not booleans; tri-state group rows exposing `aria-checked="mixed"`; out-of-reach keys and scopes not rendered
- [ ] Diff before save; dangerous grants confirmed by consequence and head count
- [ ] Own row, last Owner, and members who exceed the granter: disabled with visible reasons; the server refusal still handled
- [ ] Separation of duties: `SELF_APPROVAL` on records; conflicting roles disabled in the picker
- [ ] Audit log: who, what, when, where; privilege changes, impersonation, and secret access recorded; no secrets in rows; append-only; export audited
- [ ] View as and act as on separate keys; reason required; time-boxed; persistent banner with Exit; destructive actions disabled; audited on both sides; the member notified
- [ ] Secrets masked by default, the value sent only to roles allowed to receive it; show once where re-issuable; reveals and copies logged

## Owned elsewhere — do not duplicate

- **Grant rules, separation of duties, static vs DB-backed roles** →
  `@skills/access-control-designer/references/permission-matrix.md`
- **The role-grant policy, the lock, and the audit event in Ruby** →
  `@skills/std-rails-conventions/references/roles-and-permissions.md`
- **`/me`, the permissions version, and realtime invalidation** →
  `@skills/access-control-designer/references/ui-gates.md`
- **Membership, role, and audit tables with their indexes** →
  `@skills/std-database/references/relationships.md`
- **The refusal's error envelope** → `@skills/std-api-design/references/errors-rails.md`
- **Sensitive data in log statements** → the `std-monitoring` skill
- **The lens and the three-state rule** → `@skills/ui-ux-patterns/references/role-based-ux.md`;
  **the states these screens render** → `@skills/ui-ux-patterns/references/role-based-ux-states.md`
- **ARIA** → the `std-accessibility` skill; **Checkbox, Dialog, and Field primitives on the package's
  base** → the `std-shadcn-ui` skill
- **The platform-staff model and its audited impersonation** → the `access-control-designer` skill

## Sources

- GitHub Docs — Impersonating a user — https://docs.github.com/en/enterprise-server@latest/admin/managing-accounts-and-repositories/managing-users-in-your-enterprise/impersonating-a-user
- GitHub Docs — Impersonating a user, Enterprise Server 3.20 — https://docs.github.com/en/enterprise-server@3.20/admin/managing-accounts-and-repositories/managing-users-in-your-enterprise/impersonating-a-user
- GitHub Docs — Repository roles for an organization — https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization
- GitHub Docs — Reviewing the audit log for your organization — https://docs.github.com/en/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/reviewing-the-audit-log-for-your-organization
- GOV.UK Design System — Password input — https://design-system.service.gov.uk/components/password-input/
- HashiCorp Helios — Masked Input — https://helios.hashicorp.design/components/form/masked-input
- IETF — RFC 8693: OAuth 2.0 Token Exchange — https://datatracker.ietf.org/doc/html/rfc8693
- NIST CSRC — Role Based Access Control (RBAC) — https://csrc.nist.gov/projects/role-based-access-control
- OWASP Cheat Sheet Series — Logging — https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Salesforce Trailhead — Improve Salesforce Security Practices — https://trailhead.salesforce.com/content/learn/modules/essential-habits-for-salesforce-admins/get-the-scoop-on-security
- Stripe Docs — User roles — https://docs.stripe.com/get-started/account/teams/roles
- W3C WAI APG — Checkbox Pattern — https://www.w3.org/WAI/ARIA/apg/patterns/checkbox/
- WorkOS Docs — Impersonation (AuthKit) — https://workos.com/docs/authkit/impersonation
