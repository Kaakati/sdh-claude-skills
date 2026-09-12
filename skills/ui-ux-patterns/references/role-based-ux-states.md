# Role-Based UX States — every state a role can meet

Load-bearing rules restated (these hold even if you read nothing else):

1. **The three-state rule is canonical in `role-based-ux.md`.** Not permitted → not rendered;
   blocked by record state → disabled with a visible reason; another plan → visible and locked.
   This file details those three and every state beyond them.
2. **A reason is visible text beside the control.** Never tooltip-only, and never "you don't have
   permission" — if that were true, the control would not be there.
3. **Anything a person must find stays focusable:** `aria-disabled="true"` plus `aria-describedby`
   pointing at the visible reason — never the native `disabled` attribute.
4. **Records and features are denied differently.** A record outside the role's scope is not found
   (404), identical to one that never existed. A feature reached by direct link gets a no-access
   page that names a person.
5. **Empty has causes, and they never share copy.** Nothing yet, filtered to nothing, nothing the
   role can create. "No permission" is never an empty list.
6. **Masking is presentation; the server decides what is sent.** A value the role may not read never
   reaches the client, masked or not.

The lens and the rule itself → `@skills/ui-ux-patterns/references/role-based-ux.md`; markup → the
`std-accessibility` skill; gates and `reasonCode` → `@skills/access-control-designer/references/ui-gates.md`.

---

## Decision table

Resolve top to bottom inside each block; the first match decides.

```text
CONTROL  (action, menu item, nav item, widget)
  permission held for its key?            no  → NOT RENDERED
  organization entitled (plan, quota)?    no  → LOCKED — Upgrade if the role can change the plan, else "ask <admin name>"
  this record allows it right now?        no  → DISABLED + visible reason (from reasonCode)
  otherwise                                   → enabled

ROUTE    (a screen reached by URL, bookmark, email, notification)
  permission held for the feature?        no  → NO ACCESS — what is needed, who grants it, a way back
  record inside the role's scope?         no  → NOT FOUND — the same page as an id that never existed

FIELD    (one attribute of a record the role can read)
  grant for the field                         none → OMITTED · partial → MASKED by the API · read → TEXT · read + write → INPUT

DATA     (the collection behind a screen)
  not loaded yet                              → LOADING — skeleton of the ungated shell
  request failed                              → ERROR — what failed, what to do, retry
  zero rows, filters or search active         → EMPTY, FILTERED
  zero rows, the role holds the .create key   → EMPTY, INVITATION
  zero rows, the role cannot create           → EMPTY, WHERE IT COMES FROM
```

## The states at a glance

| State | When | Renders | Assistive tech | Copy |
|---|---|---|---|---|
| **Not rendered** | No grant for the key | Nothing — the gap closes | Absent from the DOM | None |
| **Disabled + reason** | Grant held; the record blocks it now | Control in place, dimmed; reason beside it at full contrast | `aria-disabled="true"`, `aria-describedby` → the reason | What is blocked · why · who or what unblocks it |
| **Read-only** | Can read, cannot write | Text, not an input | Plain text; native `readonly` if it must stay a form | Usually none |
| **Locked** | Grant held; plan or quota lacks it | Control in place with the plan or the limit | Focusable; activates the upgrade or ask path | What it does · which plan · Upgrade or ask |
| **No access** | Feature reached directly without its grant | A page: what is needed, who grants it, a way back | The heading states the need | "You need access to Refunds" |
| **Not found** | Record outside the role's scope | The ordinary not-found page | Same as any not-found page | "We can't find that order" |
| **Empty** | Zero rows — invitation, where it comes from, filtered, scoped | Why it is empty and where to go next | Plain text | Per kind, below |
| **Error** | A request failed | What failed, what to do, retry; input kept | Announced in a live region | Problem · remedy |
| **Masked** | Partial read grant | Label + masked value | A text alternative: "ending in 4821" | — |
| **Loading** | Data or `['me']` pending | Skeleton of the ungated shell | `aria-busy="true"` on the region | — |

## Not rendered

- **Absent from the DOM, and from the payload that builds it.** No greyed ghost, no `sr-only` hint,
  no skeleton in its shape. Carbon's hidden variation is "used when something or someone does not
  have permission to view, interact with, or take action" (IBM Carbon Design System — Disabled
  states); Primer's administration controls are "only shown when the necessary permissions are
  granted to a user" (GitHub Primer — Links and buttons); Helios says to "hide the related actions,
  navigation items, and views" (HashiCorp Helios — Show, hide, and disable).
- **The gap closes; the order holds.** Remaining actions keep their relative order, and WCAG counts
  removed items as keeping it (W3C WAI — Understanding SC 3.2.3: Consistent Navigation).
- **Containers follow their contents.** A menu with no items renders no trigger; a nav group with no
  items renders no heading; a toolbar left with one action is a button.
- **Calls to action inside other states obey it.** An empty state links to the task that fills it —
  only if this role can do that task.

## Disabled, with a visible reason

When the grant is held, the plan includes it, and this record says no for now: shipped, on credit
hold, created by the would-be approver, still processing.

- **Visible text, beside the control, in the record's terms.** One sentence and the next step:
  Cloudscape pairs a one-sentence disabled reason with next steps (AWS Cloudscape — Disabled and
  read-only states), and "Merely stating the problem is also not enough; offer some potential
  remedies" (Nielsen Norman Group — Error-Message Guidelines).
- **Name who or what unblocks it.** Primer disables only when an obvious, immediate action
  re-enables the control (GitHub Primer — Links and buttons). Many record blocks are cleared by
  someone else, or never; the house keeps the control in place anyway and makes the reason carry the
  path: "On credit hold — Finance releases it", "Already shipped — start a return instead".
- **Mapped from `reasonCode`** to translated copy — never the raw code, never a server-written
  sentence (`@skills/access-control-designer/references/ui-gates.md`).
- **Never "you don't have permission".** That is a different state, and its control is not rendered.
- **Keep them few.** Disabled buttons "have poor contrast and can confuse some users" (GOV.UK Design
  System — Button). When one record status blocks several actions, put the status at the top of the
  record, point each control's `aria-describedby` at it, and test the screen with the role that meets
  it.

### Reasons that reach everyone

- **Focusable: `aria-disabled="true"`, not `disabled`.** Browsers drop natively disabled controls
  from the tab order, and "screen reader users are far less likely to discover disabled elements
  that are not focusable" (W3C WAI APG — Developing a Keyboard Interface). The APG keeps the native
  attribute only where a control's presence is obvious from the controls around it.
- **`aria-disabled` suppresses nothing.** It only informs assistive technology: "Web developers must
  manually ensure such elements have their functionality suppressed when exposed to the disabled
  state" (MDN Web Docs — ARIA: aria-disabled attribute). Guard the click handler — and, for a submit
  button, the form's submit handler, because Enter in a field still submits.
- **`aria-describedby` points at the visible reason**, so focusing the control announces why.
- **Tooltips add detail; they never carry the reason.** "A Tooltip is not allowed on disabled
  elements because such elements are not keyboard-accessible" (GitHub Primer — Tooltip
  accessibility). A tooltip on an `aria-disabled` control must meet WCAG 1.4.13 — "Content which can
  be triggered via pointer hover should also be able to be triggered by keyboard focus", and it must
  be dismissible, hoverable, and persistent (W3C WAI — Understanding SC 1.4.13: Content on Hover or
  Focus). Even then it is not the only copy: touch has no hover.
- **The contrast exemption covers the control, not its reason.** WCAG 1.4.3 exempts "User Interface
  Components that are not available for user interaction (e.g., a disabled control in HTML)" (W3C
  WAI — Understanding SC 1.4.3: Contrast (Minimum)). The reason is ordinary text and meets 4.5:1. Dim
  the control, never a wrapper that also holds the reason.

The markup → the `std-accessibility` skill (*Not permitted, blocked, locked*).

## Read-only

When the role can read the record or the field and cannot change it — a Viewer on Settings, an
Executive on an order.

- **Text, not a disabled input.** A greyed input invites "why can't I edit this?", drops out of the
  tab order, and is exempt from contrast. Carbon keeps the two apart: its read-only state is still
  read by screen readers, where its default disabled state is not (IBM Carbon Design System —
  Disabled states); Cloudscape uses read-only for view-only access (AWS Cloudscape — Disabled and
  read-only states).
- **If the layout must stay a form** — the same settings page other roles edit — use the native
  `readonly` attribute: focusable, readable, selectable. Never `disabled`.
- **No Edit, no Save, no "request to edit".** Those are actions the role lacks: not rendered.
- **The server rejects the attribute on write regardless.** Field-level restrictions are enforced at
  a trusted service layer, not by the form (OWASP — ASVS 5.0 V8 Authorization).

## Locked — plan, entitlement, quota

When the role holds the grant, and the organization's plan does not include the feature or its
limit is used up.

- **In its slot, saying what it does, which plan has it, and how to get it.** Upgrade features stay
  visible so the people who could use them discover them (Smashing Magazine — Hidden vs. Disabled
  In UX). For a whole screen, Pajamas uses a "Higher tier feature" empty state — "a placeholder when
  a certain feature isn't available under the current tier" (GitLab Pajamas Design System — Empty
  states).
- **Only for roles that hold the permission.** A lock shown to a role without the grant is an upsell
  to someone who could not use it after paying.
- **Upgrade only for roles holding `billing.update`.** Everyone else gets "ask `<admin name>`",
  resolved from the organization's members.
- **A quota is a lock with a number:** "10 of 10 seats used — Scale includes 50". Helios swaps the
  create action for an upgrade option or an alert that explains the limit (HashiCorp Helios — Show,
  hide, and disable); the house keeps the control in place, locked, carrying that explanation, so
  actions keep their order.
- **One lock per locked area**, not a padlock on every item inside it.
- **Focusable and operable, not `aria-disabled`** — it does something. Its name says what it is, its
  description says what unlocks it, and activating it opens the upgrade or ask path.

## No access and not found — 403 vs 404

| Reached | Server | UI |
|---|---|---|
| A **record** outside the role's scope, by pasted URL | 404: scoped before lookup | The ordinary not-found page, identical to an id that never existed |
| A **feature** the role lacks, by deep link, bookmark, old email, or notification | 403 on its data; the route gate answers first | The no-access page |
| An action the UI offered, refused because the role changed mid-session | 403 | Refetch `['me']`, re-derive the screen, say "Your access changed" |
| A **region** of a page the role can open — a card, a related list — it cannot read | The relation or field is omitted | Not rendered |

- **Records look absent.** Whether this customer has an order is itself confidential. GitHub "uses a
  404 Not Found response instead of a 403 Forbidden response to avoid confirming the existence of
  private repositories" (GitHub Docs — Troubleshooting the REST API), and HTTP permits it: "send a
  404 response instead of a 403 if acknowledging the existence of a resource to clients with
  insufficient privileges is not desired" (MDN Web Docs — 403 Forbidden).
- **Features say what is needed, who grants it, and the way back.** A feature's existence is public
  — it is on the pricing page — so saying so leaks nothing and saves a ticket. "State what the user
  needs to access the page instead of what they don't have or can't do", with a button back (Red Hat
  PatternFly — Empty state design guidelines); "Suggest steps or process to request access" (IBM
  Carbon Design System — Empty states). Name a real admin: "contact your administrator" fails
  exactly the person who does not know who that is.
- **A fallback for direct navigation only.** PatternFly and Carbon render the no-access state as a
  place in the product, and Salesforce's "Inline Text is used for empty and inaccessible states in
  feed/card/related list" (Salesforce Lightning Design System — Messaging overview). The house shows
  the page only to someone who arrives by URL; nav items, actions, and regions stay not rendered, so
  nobody browses into it.
- **Mid-session changes apply at once.** Changes to what authorization depends on take effect
  immediately (OWASP — ASVS 5.0 V8 Authorization). The UI catches up on the next 403 or realtime
  event (`@skills/access-control-designer/references/ui-gates.md`) and says so, instead of leaving a
  dead control.
- The response bodies → `@skills/std-api-design/references/errors-rails.md`; scoping before lookup
  → `@skills/std-rails-conventions/references/authorization.md`.

## Empty — the kinds, and what each says

"Do not default to totally empty states. This approach creates confusion for users, who may be left
wondering if the system is still loading information" (Nielsen Norman Group — Designing Empty States
in Complex Applications). Every kind follows one rule: "Include the reason for the empty state and
where they can go next" (Atlassian Design System — Empty state).

| Kind | Condition | Say | Offer |
|---|---|---|---|
| **Invitation** | Nothing yet; the role holds the `.create` key | What this space is for | The create action |
| **Where it comes from** | Nothing yet; the role cannot create | The event that fills it: "Invoices appear here once an order ships" | A link to where that happens, if the role can go there |
| **Filtered** | Filters or search exclude every row | "No orders match these filters" | Clear filters |
| **Scoped** | The role's scope is `own` or `team` and nothing is in it | "You have no orders yet" — never "No orders", which is false for the organization | The invitation or where-it-comes-from offer, as above |

- **No permission is not an empty state.** An empty Refunds list for a role that cannot read refunds
  says refunds don't exist — false — and sends the person off to create one. Not rendered in the
  nav; reached directly, the no-access page.
- **Filtered never looks like first use.** A first-use illustration over an active filter makes
  people think their data is gone.
- The layout → `@skills/ui-ux-patterns/references/screen-patterns.md` (Empty States).

## Error

- **Plain language, the problem, a remedy, and the input kept** — people fix it without starting
  over (Nielsen Norman Group — Error-Message Guidelines).
- **Never disguised as another state.** A 403 is not "Something went wrong", a failed load is not
  "No orders", and a record outside scope is not an error toast.
- **Mapped from the envelope's `code`** to translated copy; raw codes and server sentences never
  render → `@skills/std-api-design/references/errors-rails.md`.
- **Field validation stays on the field**, never in a toast → the `std-shadcn-ui` skill.

## Masked — partial vs omitted

| Grant for the field | Render | What the API sends |
|---|---|---|
| **None** | **Omit** — no label, no blank, no "—". A column the role cannot read is not a column; the layout reflows | Nothing. Omitting it only in the component is cosmetic — the network tab is a UI too |
| **Partial** | **Mask** — label intact, so the role knows which field it is: Tax ID `•••• 4821` | The masked value; the full value never reaches this client |
| **Read, reveal on demand** (secrets) | A masked input with a Show toggle | The masked form; the full value only from an explicit reveal request, which is logged |
| **Read, not write** | Plain text | The value; the attribute is rejected on write |
| **Read and write** | An input | The value |

- **"—" means empty.** Reused for *you may not see this*, it tells the role data is missing and
  sends them off to fix it.
- **On-screen masking protects nothing.** Helios' masked input "is meant for visual obfuscation
  only. Consumers should be aware that the hidden text value could still be obtained through other
  means" (HashiCorp Helios — Masked Input). The server decides whether the role receives the value.
- **Give a masked value a text alternative** — "ending in 4821" — or a screen reader reads out a row
  of bullets.
- **Reveal toggles follow GOV.UK's password input:** "Hide passwords by default until the user
  chooses to show it using the 'show' button"; a distinct label for each toggle on the page; paste
  allowed; `spellcheck="false"` so spell-check tools don't collect the value (GOV.UK Design System —
  Password input).
- **A reveal or a copy is access to sensitive data, and gets logged** — without the value itself
  (OWASP Cheat Sheet Series — Logging). The secrets screen →
  `@skills/ui-ux-patterns/references/role-management-ux.md`.

## Loading

- **A skeleton of the ungated shell.** Before `['me']` arrives nothing is permitted
  (`@skills/access-control-designer/references/ui-gates.md`), so the skeleton draws only what every
  role gets. A placeholder shaped like the Margin widget tells a Sales Rep it exists.
- **Gated controls appear once, never twice.** A control rendered from stale or empty rules and then
  removed reads as access revoked.
- **Loading is not empty.** Hold the empty state until the request resolves; a blank that later fills
  is the confusion the empty-state guidance warns about.

## Copy patterns per state

| State | Pattern | Example | Never |
|---|---|---|---|
| Disabled | `<What> — <why, in the record's terms> — <who or what unblocks it>` | "Already shipped — start a return instead" | "You don't have permission" · "Unavailable" |
| Locked | `<Feature> is on <Plan>` + Upgrade, or ask `<admin name>` | "Partial refunds are on Scale — ask Priya (Org Admin)" | Upgrade for a role that cannot change the plan |
| Quota | `<used> of <limit> <unit> — <Plan> includes <more>` | "10 of 10 seats used — Scale includes 50" | Invite silently gone |
| No access | `You need access to <feature>` + who grants it + the way back | "You need access to Refunds. Priya (Org Admin) can grant it." · Back to My orders | "403 Forbidden" · "Contact your administrator" |
| Not found | `We can't find that <thing>` + the way back | "We can't find that order" · Back to orders | "You don't have access to this order" |
| Access changed | `Your access changed` + where they are now | "Your access changed — you're back on My orders" | A control that vanishes unexplained |
| Empty — invitation | `<What this space is for>` + the create action | "Every store order lands here." · New order | A create action for a role without `.create` |
| Empty — where it comes from | `<Items> appear here once <event>` | "Invoices appear here once an order ships" | "No data" |
| Empty — filtered | `No <items> match these filters` + Clear filters | "No orders match these filters" | A first-use illustration |
| Error | `<What failed>. <What to do>` + Retry | "Orders didn't load. Check your connection and try again." | Error codes · blame |
| Masked | Label + `•••• <last 4>` | "Tax ID •••• 4821" | "—" |

Every string is a translation key; reason codes map to keys → the `std-i18n` skill.

## Checklist

- [ ] Every control resolved permission → entitlement → record state; nothing not permitted reaches the DOM or the payload
- [ ] Every disabled control has a visible, full-contrast reason that names the next step; none says "no permission"
- [ ] `aria-disabled` + `aria-describedby`, handlers guarded; no tooltip on a natively disabled control; any tooltip meets 1.4.13 and duplicates visible text
- [ ] Read-only renders text (or native `readonly`), never disabled inputs; no Edit or Save for the role
- [ ] Locks only for roles holding the grant; Upgrade only for roles holding `billing.update`; quotas show the number
- [ ] Out-of-scope record → the not-found page, identical to a missing id; feature by direct link → the no-access page naming a person
- [ ] Empty states distinguish invitation, where it comes from, filtered, and scoped; no permission is never an empty list
- [ ] Errors say what failed and what to do; never shown as empty or denied
- [ ] Fields: none → omitted and never sent; partial → masked by the API with a text alternative; "—" only for empty
- [ ] Reveals and copies of secrets are logged, without the value
- [ ] Skeletons draw only the ungated shell; gated controls never flash in and out

## Owned elsewhere — do not duplicate

- **The lens, the three-state rule, navigation and dashboards per role** →
  `@skills/ui-ux-patterns/references/role-based-ux.md`
- **Admin screens** — role catalog, matrix editor, invites, audit log, impersonation, secrets →
  `@skills/ui-ux-patterns/references/role-management-ux.md`
- **Markup for each state** → the `std-accessibility` skill
- **Base-correct Button, Tooltip, and Field APIs** (Base UI `render` vs Radix `asChild`) → the
  `std-shadcn-ui` skill
- **Gates, `/me`, `reasonCode`, per-record `actions`** →
  `@skills/access-control-designer/references/ui-gates.md`
- **Scoping before lookup** → `@skills/std-rails-conventions/references/authorization.md`; **the
  error envelope** → `@skills/std-api-design/references/errors-rails.md`
- **Empty-state layout** → `@skills/ui-ux-patterns/references/screen-patterns.md`
- **Translated copy and key naming** → the `std-i18n` skill

## Sources

- Atlassian Design System — Empty state — https://atlassian.design/foundations/content/designing-messages/empty-state
- AWS Cloudscape — Disabled and read-only states — https://cloudscape.design/patterns/general/disabled-and-read-only-states/
- GitHub Docs — Troubleshooting the REST API — https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api
- GitHub Primer — Links and buttons — https://primer.style/accessibility/design-guidance/links-and-buttons/
- GitHub Primer — Tooltip accessibility — https://primer.style/product/components/tooltip/accessibility/
- GitLab Pajamas Design System — Empty states — https://design.gitlab.com/patterns/empty-states/
- GOV.UK Design System — Button — https://design-system.service.gov.uk/components/button/
- GOV.UK Design System — Password input — https://design-system.service.gov.uk/components/password-input/
- HashiCorp Helios — Masked Input — https://helios.hashicorp.design/components/form/masked-input
- HashiCorp Helios — Show, hide, and disable — https://helios.hashicorp.design/patterns/disabled-patterns
- IBM Carbon Design System — Disabled states — https://v10.carbondesignsystem.com/patterns/disabled-states/
- IBM Carbon Design System — Empty states — https://v10.carbondesignsystem.com/patterns/empty-states-pattern/
- MDN Web Docs — 403 Forbidden — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403
- MDN Web Docs — ARIA: aria-disabled attribute — https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-disabled
- Nielsen Norman Group — Designing Empty States in Complex Applications — https://www.nngroup.com/articles/empty-state-interface-design/
- Nielsen Norman Group — Error-Message Guidelines — https://www.nngroup.com/articles/error-message-guidelines/
- OWASP — ASVS 5.0 V8 Authorization — https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md
- OWASP Cheat Sheet Series — Logging — https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Red Hat PatternFly — Empty state design guidelines — https://www.patternfly.org/components/empty-state/design-guidelines/
- Salesforce Lightning Design System — Messaging overview — https://winter-20.lightningdesignsystem.com/guidelines/messaging/overview/
- Smashing Magazine — Hidden vs. Disabled In UX — https://www.smashingmagazine.com/2024/05/hidden-vs-disabled-ux/
- W3C WAI — Understanding SC 1.4.13: Content on Hover or Focus — https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html
- W3C WAI — Understanding SC 1.4.3: Contrast (Minimum) — https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- W3C WAI — Understanding SC 3.2.3: Consistent Navigation — https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html
- W3C WAI APG — Developing a Keyboard Interface — https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/
