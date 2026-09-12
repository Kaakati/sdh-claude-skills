# Role-Based UX — "As a `<Role>`, what should I see, and how should I see it?"

Load-bearing rules restated (these hold even if you read nothing else):

1. **Every role is the hero of its own story.** Design each key screen once per role — its want,
   its obstacle, its payoff — not once for "the user" with conditionals added afterwards.
2. **The three-state rule — this file is its canonical home.** Not permitted → **not rendered**.
   Permitted but blocked by record state → **disabled, with a visible reason**. Available on
   another plan → **visible and locked**, only for roles that could act on it.
3. **The UI checks permission keys (`orders.refund`), never role names.** A role may choose an
   *order* — a sidebar sorted for that job — but never whether something exists.
4. **Hiding is UX, not security.** The server policy is the authority. A field the role may not
   read never leaves the API; a record outside the role's scope is a 404.
5. **Personalize by role; customize only inside it.** The membership decides which nav items,
   widgets, and actions exist. A person may pin, reorder, or collapse among those; nothing they
   configure adds one.

Every state beyond the three — read-only, no access vs not found, the kinds of empty, masked fields,
loading, error — is `@skills/ui-ux-patterns/references/role-based-ux-states.md`. The screens that
grant access — role catalog, matrix editor, invites, audit log, "view as" — are
`@skills/ui-ux-patterns/references/role-management-ux.md`. Implementation is not this file's job —
gates, policies, ARIA: see **Owned elsewhere** at the end.

---

## The lens

`@skills/ui-ux-patterns/references/storytelling-ui.md` makes the user the hero and the product the
guide. A multi-role product has several heroes on the same screen, and they want different things
from it: the warehouse lead wants the queue empty before the truck leaves, the executive wants to
know whether this quarter beats the last. A screen designed for "the user" serves neither — the
operator wades through charts, the executive gets a table nobody scans.

So ask, per role and per screen: **"As a `<Role>`, what should I see, and how should I see it?"**

- **What** is a permission question, and the matrix answers it. Design does not overrule it: the UI
  never shows what the matrix denies, and never hides what it grants.
- **How** is a design question, and the role's tasks answer it: **prominence** (first, largest,
  primary), **format** (table, tile, trend, timeline), **density** (rows per view, words per row).

A permitted item the role rarely needs is **demoted** — overflow menu, lower in the sidebar, below
the fold, behind a disclosure. It is not hidden. *Hidden* means not permitted and nothing else, so
the word keeps one meaning in every review.

**A persona is not a role, though the two often share a name.** A persona is "a fictional, yet
realistic, description of a typical or target user of the product" (Nielsen Norman Group — Personas
Make Users Memorable): goals, behaviour, context. A role is a bundle of grants on a membership.
*What* reads the role; *how* reads the persona. When one role serves two very different personas,
keep one role and design *how* for the dominant one — a different persona alone never justifies a
new role.

## Step 1 — A persona card per role

One card for every role in the matrix. A role without a card still gets a UI — designed by accident.

| Field | What goes in it |
|---|---|
| **Role** | As named on the membership (user × organization) — the same key the matrix uses |
| **Story** | One sentence: wants ___ · the obstacle is ___ · success looks like ___ |
| **Goals** | One to three, in the role's words, not the product's |
| **Top tasks (frequency)** | Each with how often: many a day · daily · weekly · monthly · rarely. Measured — analytics, support tickets, interviews — not guessed. Landing page and navigation order come from this row |
| **Context / device** | Where and on what: dual monitors at a desk, a shared tablet on a warehouse cart, a phone between meetings |
| **Cost of a mistake** | What breaks when they press the wrong thing, and who pays. Sets confirmation strength, undo, and how much sits one tap away |
| **Must never see** | Records, fields, features. Each line becomes a matrix cell, not only a design note — if the API sends it, hiding it is cosmetic |
| **Lands on** | The screen for the most frequent task |

## Step 2 — A walkthrough table per role

Walk each key screen as that role — and each **state** of it, because states are where roles
diverge: the empty list, the record blocked by its status, the feature on another plan.

| Screen | What I see | How I see it (prominence, format, density) | Hidden | Why |
|---|---|---|---|---|
| *Screen or state* | *Content and actions present* | *First / largest / primary · table, tile, trend · rows per view* | *Not rendered* | *Permission key, or the persona row* |

- Every **Hidden** entry names a key the role lacks. If it names a preference ("they don't need
  it"), it is a demotion — move it to *How*.
- Every **Why** traces to the matrix or the persona card. "Cleaner" is not a reason.
- Add a **Navigation** row per role: the areas it sees in order, its landing page, and the number of
  selections to its top task (`@skills/ui-ux-patterns/references/drill-down-navigation.md`).

## Worked example — a wholesale ordering platform

A distributor's B2B platform: retail stores order stock; the distributor picks, ships, and
invoices. Five roles share one organization, which is on the **Growth** plan; partial refunds are an
entitlement of **Scale**. Matrix excerpt — cells are scopes:

| Permission key | Org Admin | Sales Rep | Warehouse Lead | Finance Clerk | Executive |
|---|---|---|---|---|---|
| `orders.read` | org | own | org | org | org |
| `orders.create`, `orders.cancel` | org | own | — | — | — |
| `orders.fulfil` | — | — | org | — | — |
| `orders.refund` | org | — | — | org | — |
| `orders.export` | org | — | — | org | org |
| `margins.read` | org | — | — | org | org |
| `billing.update` | org | — | — | — | — |

### The heroes

| Role | Story — wants · obstacle · success | Lands on | Context |
|---|---|---|---|
| **Org Admin** | A running organization · settings scattered across screens · every member productive, the bill predictable | Setup checklist until done, then Dashboard | Laptop, weekly |
| **Sales Rep** | Stores that reorder · chasing status by phone · answering "where is it?" in one tap | My orders | Phone and laptop between visits, many a day |
| **Warehouse Lead** | Everything due today on the truck · noise: orders not ready, actions not theirs · an empty queue | Pick queue, due today | Shared tablet on a cart, gloves, many a day |
| **Finance Clerk** | Invoices paid, refunds right · disputes with no context · nothing overdue without a note | Invoices needing action | Desk, dual monitors, daily |
| **Executive** | Is the business healthy? · dashboards built for operators · the answer in ten seconds | Dashboard | Phone, weekly |

### Warehouse Lead — dense and actionable

| Screen | What I see | How I see it | Hidden | Why |
|---|---|---|---|---|
| Pick queue (landing) | Orders due today: bins, line counts, delivery window | Dense table sorted by truck departure; one primary action per row (Mark packed); status as text + icon; large targets for gloved hands | Margin | `margins.read` — |
| Orders list | Every open order in the org; chips: Due today · Short-picked · On hold | Status-first columns; order value demoted to the detail page | New order, Export | `orders.create` —, `orders.export` — |
| Order detail | Lines in bin order, quantities, delivery address and window | Picking layout — bin, SKU, quantity in large type; timeline collapsed | Cancel, Refund, margin | `orders.cancel` —, `orders.refund` —, `margins.read` — |
| Order on credit hold | The same, plus "On credit hold — Finance releases it" | Mark packed **disabled**, the reason printed beside it | — | Permitted (`orders.fulfil`), blocked by the record: `reasonCode: "CREDIT_HOLD"` |

### Executive — summarized trends

| Screen | What I see | How I see it | Hidden | Why |
|---|---|---|---|---|
| Dashboard (landing) | Revenue, on-time shipping, refund rate, fastest-growing accounts | Four KPI tiles, each with a delta against last quarter; one trend chart; no row-level table above the fold | Pick queue, New order | `orders.fulfil` —, `orders.create` — |
| Orders list | Org-wide orders, defaulting to exceptions (late, refunded) | Grouped by week with a totals row; rows are a drill-down, not the default | New order, Cancel | `orders.create` —, `orders.cancel` — |
| Order detail | Totals, margin, timeline | Read-only layout with no action bar; Export sits in the page menu | Cancel, Refund | `orders.cancel` —, `orders.refund` — |

### Order #4812, shipped — one action bar, five roles

| Action | Org Admin | Sales Rep (own order) | Warehouse Lead | Finance Clerk | Executive |
|---|---|---|---|---|---|
| **Cancel** | Disabled — "Already shipped — start a return instead" | Disabled — same reason | Not rendered | Not rendered | Not rendered |
| **Full refund** | Enabled | Not rendered | Not rendered | Enabled | Not rendered |
| **Partial refund** (Scale) | Locked — "Available on Scale" · **Upgrade** | Not rendered | Not rendered | Locked — "Available on Scale — ask Priya (Org Admin)" | Not rendered |
| **Export** | Enabled | Not rendered | Not rendered | Enabled | Enabled |

Every cell is the resolution order below, applied. The Finance Clerk holds `orders.refund` but not
`billing.update`, so the lock names a person instead of offering a purchase; the Executive holds
neither, so there is no lock to see. A Sales Rep opening a colleague's order never reaches this bar
— `orders.read` is `own`, the API scopes before it looks up, and the UI renders the ordinary
not-found page.

## Landing page per role

- **Land on the most frequent task.** A dashboard is the landing page only for roles whose top task
  *is* watching — the Executive, and the Org Admin once setup is done. Everyone else lands on their
  queue or their list.
- **Derive it; don't switch on it.** The landing route is the first entry in the role's nav order
  that the membership can reach. Lose `orders.fulfil` and the landing page moves with the grant,
  instead of dropping the user on a screen that now denies them.
- **A deep link beats the landing page.** After sign-in, return to the URL that sent them; the
  landing page is for a cold start.

## Navigation order

Every item a role cannot use costs the people who can decision time: "The time it takes to make a
decision increases with the number and complexity of choices" (Laws of UX — Hick's Law). A trimmed
menu is a speed feature before it is a tidy one.

- **Visibility is a gate; order is presentation data.** Each item's visibility is its permission key
  and nothing else. The nav config may carry an order per role.
- **One canonical order, trimmed per role.** WCAG 3.2.3 wants repeated navigation in the same
  relative order on every page, and "Items are considered to be in the same relative order even if
  other items are inserted or removed from the original order" (W3C WAI — Understanding SC 3.2.3:
  Consistent Navigation). A role-trimmed menu conforms as long as what remains keeps its order.
- **Reorder for a role only on measured frequency.** The house reads the criterion across the pages
  one person moves through: a role whose order is fixed on every page stays consistent for everyone
  who holds it. That is our reading, not the criterion's text — so move an item up for a role only
  when the persona card's measured task frequency says so. A guess spends muscle memory for nothing.
- **Positions never move with usage, or between pages.** "Recent" belongs in its own section or the
  command palette.
- **A group with no visible items is not rendered** — no orphan "Billing" heading, no divider
  between nothing. A group left with one item is an item; flatten it.
- **Counts only where the role acts.** "Pick queue · 14" for the Warehouse Lead; the Executive's
  sidebar carries no badges.
- **Locked follows the three-state rule** — present only for roles holding the permission. If a plan
  locks a whole area, show one locked entry for the area, not a padlock per item.
- **A grant change re-derives the order once, and says so.** Changes to what authorization depends
  on apply immediately (OWASP — ASVS 5.0 V8 Authorization), so the nav re-derives on the next
  `['me']`. Tell the person their access changed rather than letting the sidebar shuffle unexplained.
- **What the nav holds and how deep it goes** — areas only in the global sidebar, sections in each
  area's own layout, the area budget per role, a role with one area landing inside it →
  `@skills/ui-ux-patterns/references/drill-down-navigation.md`.

## Per-role dashboards

A role-based dashboard is **personalization** — "Developers set up the system to identify users and
deliver to them the content, experience, or functionality that matches their role" — while
**customization** is what people configure for themselves (Nielsen Norman Group — Customization vs.
Personalization in the User Experience). The house uses both, in that order.

Compose **one dashboard per job**. A single dashboard with every widget gated individually leaves
holes, and the layout that survives was designed for nobody. Each widget is still gated by its key —
composing per role decides layout, not access.

| Job | Shape | Every number is… |
|---|---|---|
| **Operator** (Warehouse Lead, Sales Rep) | Dense and actionable: queues and exception counts on top, row actions in place, live updates where the queue moves | A door — "14 due today" opens that filtered list |
| **Manager** (Org Admin, Finance Clerk) | Exceptions first — what needs a decision today — then this week's trend | A door to the exception, or a trend |
| **Executive** | Summarized trends: three to five KPIs, each with a delta against a stated prior period; one trend chart; no row-level table above the fold | A trend; drill-down exists but is never the default |

- **Personalization sets the defaults:** which widgets, in what order, over what period — today for
  operators, this week for managers, the quarter for executives.
- **Customization sits on top, inside the grants.** Pin, reorder, collapse, hide — among widgets the
  membership may read. The widget picker lists only those; a widget the role lacks is not rendered
  there either, and a plan-locked one shows locked to roles holding its key.
- **A saved layout stores widget ids, never data.** A widget whose key the member has since lost is
  dropped at render, not shown empty.
- **"Reset to my role's default" is always one action away.**

## Progressive disclosure

"Initially, show users only a few of the most important options. Offer a larger set of specialized
options upon request" (Nielsen Norman Group — Progressive Disclosure). In a multi-role product,
disclosure works *inside* what the role may do: it is the demotion from **The lens**, never a gate.

- **"Most users" means most of this role.** "Do not use the details component to hide information
  that the majority of your users will need" (GOV.UK Design System — Details). Refund history is
  primary for the Finance Clerk and one expander down for the Org Admin — the same panel, two
  prominences.
- **Never disclose what is not permitted.** An "Advanced" section that opens onto greyed-out
  controls is the not-permitted state wearing a disclosure widget. Not rendered stays not rendered,
  collapsed or open.
- **Key actions and filters stay out of disclosures.** The primary action and the filters a role
  uses daily are never tucked away by default (Smashing Magazine — Hidden vs. Disabled In UX).
- **Long flows become steps.** Fewer choices per step is Hick's law applied to a task, not a menu.

## The three-state rule

| State | Condition | Render | Why not the alternative |
|---|---|---|---|
| **Not permitted** | The membership holds no grant for the key | **Not rendered** — no control, no greyed ghost, no tooltip, no screen-reader-only text | Disabled says "not now": people wait, retry, and file tickets for access they were deliberately not given — and every role learns every other role's capabilities |
| **Blocked by record state** | Grant held; this record says no, for now | **Disabled, with the reason visible beside it** — never tooltip-only | Hidden, the action vanishes the moment the order ships, and the user concludes the feature broke or their access changed |
| **Not entitled** | Grant held; the organization's plan lacks the feature | **Visible and locked** — what it does, which plan has it, how to get it | Hidden, the people who could use it never learn it exists; shown to a role without the grant, it is an upsell to someone who could not use it after paying |
| **Available** | Grant held, entitled, record allows | Enabled | — |

Resolve in this order — the first "no" decides:

```text
permission held for this key?      no → not rendered
organization entitled (plan)?      no → visible, locked — Upgrade if the role can change the plan, else "ask <admin name>"
this record allows it right now?   no → disabled + visible reason, mapped from the record's reasonCode
otherwise                             → enabled
```

Effective access is **permission AND entitlement** — that decides whether the capability exists for
this person. Record state decides only whether *this instance* can take it *now*. The two arrive
separately: rules carry role and scope; the record carries its own blocks, e.g.
`actions: { cancel: { enabled: false, reasonCode: "ORDER_SHIPPED" } }`, which the UI maps to a
translated sentence. Never write "disabled — you don't have permission": if that were true, the
control would not be there.

Actions keep one relative order for every role. A control that is not rendered closes its gap and
never reorders the rest; the primary action keeps its slot (heuristic 4).

### Why three

Two questions hide inside "can this person do this?" — *will they ever*, and *can they now*?
Smashing Magazine's test is the first: an element a user will never interact with is hidden — "due
to permissions, access controls, safety, and security" — and one they will is disabled with an
explanation of how it re-enables (Smashing Magazine — Hidden vs. Disabled In UX). Not permitted is
*never, in this membership*. Blocked is *not now, for this record*. Locked is *not on this plan* —
and the people who could act on it should know it exists. A disabled control with no reason answers
the second question with silence: "A lack of information often equates to a lack of control"
(Nielsen Norman Group — Visibility of System Status).

### Where other design systems agree, and where the house differs

| Source | Recommends | House |
|---|---|---|
| IBM Carbon Design System — Disabled states | A hidden variation "used when something or someone does not have permission to view, interact with, or take action"; visible disabled for unmet prerequisites; a read-only state screen readers still read | **Agrees.** Carbon's hidden variation is *not rendered*, its visible disabled is *blocked*, its read-only is in the states file |
| GitHub Primer — Links and buttons | Administration controls "only shown when the necessary permissions are granted"; disable only when an obvious, immediate action re-enables; say why; prefer `aria-disabled` | **Agrees** on hiding, on the reason, and on `aria-disabled`. **Differs** on blocks the user cannot clear — the order already shipped, Finance holding credit: Primer would hide or explain instead; the house disables in place and makes the reason name who or what unblocks it, because a vanished action reads as a broken feature |
| HashiCorp Helios — Show, hide, and disable | Hide actions, navigation items and views without permission; avoid disabled elements; at a quota, hide create and show an upgrade option or an alert | **Agrees** on hiding for permission. **Differs** twice: a record-state block stays in place, disabled with its reason; a plan or quota limit keeps the control in its slot, locked, carrying the same upgrade path, so actions keep one order |
| GOV.UK Design System — Button | Disabled buttons "have poor contrast and can confuse some users"; avoid them unless research shows they help | **Partly agrees.** Never disabled for permission; disabled for record state only, with the reason in full-contrast text beside it. Test those states with the role that meets them |
| Microsoft Fluent 2 — React Button usage | A tooltip on a disabled button stating what is unavailable, why, and/or how to gain access | **Differs.** A tooltip on a natively disabled element is not keyboard-accessible (GitHub Primer — Tooltip accessibility), so the reason is visible text; and a permission gap offers no "how to gain access" on the control — the control is not rendered |
| AWS Cloudscape — Disabled and read-only states | A one-sentence disabled reason with next steps — including "inform the user that the action is not supported due to lack of permission" — and no disabled items users have no way to enable | **Agrees** with the one-sentence reason and the no-way-to-enable rule. **Differs deliberately** on permission reasons: a permission gap known in advance is not rendered — which is where Cloudscape's own no-way-to-enable rule already points |
| Smashing Magazine — Hidden vs. Disabled In UX | Hide for permissions and security; disable with an explanation for temporary blocks; keep upgrade features visible | **Agrees** on all three states |
| IBM Carbon Design System — Empty states · Red Hat PatternFly — Empty state design guidelines · Salesforce Lightning Design System — Messaging overview | A no-access state that says what the user needs and how to request access; SLDS uses inline text for inaccessible content inside cards and related lists | **Agrees only for direct navigation.** Nav items, actions, and regions stay not rendered; a feature reached by URL gets the no-access page; a record gets not found — see the states file |

**Why the house departs on permission gaps: not advertising what a role can never do.** A disabled
Refund on every Sales Rep's screen tells them refunds exist, roughly who holds them, and that
someone decided they should not — and it invites retries, tickets, and requests for access withheld
on purpose. The server side follows the same principle: GitHub "uses a 404 Not Found response
instead of a 403 Forbidden response to avoid confirming the existence of private repositories"
(GitHub Docs — Troubleshooting the REST API), and HTTP allows that substitution when acknowledging a
resource to a client without the privilege is not desired (MDN Web Docs — 403 Forbidden).

Not rendering is still not the control. Client-side checks "may be permissible for improving the
user experience" but "should never be the decisive factor in granting or denying access" (OWASP
Cheat Sheet Series — Authorization), and bypassing a hidden link by editing the URL is a core
failure A01 lists (OWASP Top 10:2025 — A01 Broken Access Control). Gates name specific permissions
and deny by default (OWASP Top 10 Proactive Controls — C1: Implement Access Control); the server
re-checks every request.

## Beyond the three states

The three-state rule decides **controls**. Screens, records, fields, and data have states of their
own, each with one right answer per role → `@skills/ui-ux-patterns/references/role-based-ux-states.md`:
read-only (text, not a disabled input) · no access (a feature reached by URL) vs not found (a record
outside scope) · the kinds of empty (invitation, where it comes from, filtered, scoped) · masked
fields (partial vs omitted, never "—") · loading and error.

## Multi-role users

- **Roles live on the membership.** A user holding two roles in one organization sees the **union**:
  each key at the widest scope any of their roles grants (`own` with `org` is `org`). Stripe's
  job-function roles combine the same way — holding several grants all their permissions (Stripe
  Docs — User roles).
- **No in-organization role switcher.** The API enforces the union; a UI that shows one role at a
  time shows less than the person can do, and they find the rest by accident.
- **Layout merges too.** Each nav item takes its best rank across the roles held; the landing page is
  the top of that merged order; the dashboard carries both jobs, most frequent task first.
- **Switching organization switches membership** — a different permission set. The `['me']` query
  refetches, org-scoped cached data is dropped, landing and navigation are re-derived; nothing
  crosses the boundary. The mechanics → `@skills/access-control-designer/references/ui-gates.md`.

## Admin "view as"

"What does Dana actually see?" is a support question every multi-role product gets. Answer it in the
product, not over screenshots. The non-negotiables: **evaluated by the server**, never simulated by
filtering the admin's own rules in the client; **a persistent banner** naming the member, with Exit;
**read-only by default**, acting as someone being a separate, rarer grant; **a reason, a time box,
and an audit trail** written server-side; **no escalation** past the viewer's own grants, and never
across organizations. The screen, the session, and their sources →
`@skills/ui-ux-patterns/references/role-management-ux.md`.

## Nielsen's heuristics — once per role

`@skills/ui-ux-patterns/references/heuristic-evaluation.md` run as "the user" averages the roles, and
an average hides the one that is struggling. Run it once per persona, over that role's walkthrough.

| Heuristic | What changes per role |
|---|---|
| 1 · Visibility of system status | The status this role acts on is the prominent one — the queue count, not revenue |
| 4 · Consistency and standards | One relative order of actions and nav items for every role; a missing control closes its gap |
| 5 · Error prevention | The three-state rule on every action; the cost-of-mistake row sets confirmation strength |
| 6 · Recognition over recall | This role's frequent items are visible without search |
| 7 · Flexibility and efficiency | Operators get bulk actions and shortcuts; executives get drill-down |
| 8 · Aesthetic and minimalist | Not permitted is not rendered; density matches the persona's context |
| 9 · Error recovery | Denied, not found, and empty are distinct; every denial names a person or a path (`role-based-ux-states.md`) |

Score and report per role; never average across roles. A 4.6 for the Org Admin does not offset a
2.1 for the Warehouse Lead — the product ships at its lowest-scoring role.

## Checklist

- [ ] A persona card for every role in the matrix; story in one sentence; task frequency measured
- [ ] A walkthrough table per role × key screen, including its empty, blocked, and locked states
- [ ] Every Hidden cell names a permission key; preferences became demotions
- [ ] Each role lands on its most frequent task, derived from its nav order
- [ ] Navigation: one canonical order trimmed per role; reordered for a role only on measured frequency; groups with no visible items not rendered
- [ ] Dashboards personalized per job; customization only among widgets the role may read
- [ ] Progressive disclosure demotes permitted items, never discloses not-permitted ones, and never tucks away key actions or filters
- [ ] The three-state rule on every action, resolved permission → entitlement → record state
- [ ] Disabled reasons visible and mapped from `reasonCode`; none says "no permission"
- [ ] Locks only for roles holding the permission; Upgrade only for roles that can change the plan
- [ ] UI gates check permission keys, never role names
- [ ] Read-only, no access vs not found, empty, masked, loading, and error handled per `role-based-ux-states.md`
- [ ] Multi-role users see the union within one organization; nothing crosses an organization switch
- [ ] "View as": server-evaluated, reasoned, time-boxed, bannered, read-only by default, audited (`role-management-ux.md`)
- [ ] Heuristics scored once per role, never averaged
- [ ] Each state reaches assistive tech as the `std-accessibility` skill specifies

## Owned elsewhere — do not duplicate

- **Every state beyond the three** — read-only, no access vs not found, empty, masked, loading,
  error, copy per state → `@skills/ui-ux-patterns/references/role-based-ux-states.md`
- **The screens that grant access** — role catalog, matrix editor, invites, last-owner guard, audit
  log, "view as" → `@skills/ui-ux-patterns/references/role-management-ux.md`
- **The matrix** — scopes (— / own / team / org / all), roles on the membership, code-defined keys,
  deny by default → `@skills/access-control-designer/references/permission-matrix.md`
- **Gates in code** — CASL rules, the `['me']` query, route guards, plain rules passed from Server to
  Client Components → `@skills/access-control-designer/references/ui-gates.md`
- **The authority** — roles and Pundit policies on the Rails API →
  `@skills/std-rails-conventions/references/roles-and-permissions.md`; scope before lookup so an
  out-of-scope record is a 404 → `@skills/std-rails-conventions/references/authorization.md`
- **The 403 body** → `@skills/std-api-design/references/errors-rails.md`
- **ARIA for each state** — `aria-disabled` with a described reason, locked controls that stay
  focusable → the `std-accessibility` skill
- **Primitives** — Button, Tooltip, Sidebar on the package's shadcn/ui base → the `std-shadcn-ui`
  skill
- **Navigation structure** — areas, levels, location cues, breadcrumbs, Back, search and the command
  palette → `@skills/ui-ux-patterns/references/drill-down-navigation.md`
- **Empty-state and dashboard patterns** → `@skills/ui-ux-patterns/references/screen-patterns.md`;
  **narrative arc and hero framing** → `@skills/ui-ux-patterns/references/storytelling-ui.md`

## Sources

- AWS Cloudscape — Disabled and read-only states — https://cloudscape.design/patterns/general/disabled-and-read-only-states/
- GitHub Docs — Troubleshooting the REST API — https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api
- GitHub Primer — Links and buttons — https://primer.style/accessibility/design-guidance/links-and-buttons/
- GitHub Primer — Tooltip accessibility — https://primer.style/product/components/tooltip/accessibility/
- GOV.UK Design System — Button — https://design-system.service.gov.uk/components/button/
- GOV.UK Design System — Details — https://design-system.service.gov.uk/components/details/
- HashiCorp Helios — Show, hide, and disable — https://helios.hashicorp.design/patterns/disabled-patterns
- IBM Carbon Design System — Disabled states — https://v10.carbondesignsystem.com/patterns/disabled-states/
- IBM Carbon Design System — Empty states — https://v10.carbondesignsystem.com/patterns/empty-states-pattern/
- Laws of UX — Hick's Law — https://lawsofux.com/hicks-law/
- MDN Web Docs — 403 Forbidden — https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/403
- Microsoft Fluent 2 — React Button usage — https://fluent2.microsoft.design/components/web/react/core/button/usage
- Nielsen Norman Group — Customization vs. Personalization in the User Experience — https://www.nngroup.com/articles/customization-personalization/
- Nielsen Norman Group — Personas Make Users Memorable — https://www.nngroup.com/articles/persona/
- Nielsen Norman Group — Progressive Disclosure — https://www.nngroup.com/articles/progressive-disclosure/
- Nielsen Norman Group — Visibility of System Status — https://www.nngroup.com/articles/visibility-system-status/
- OWASP — ASVS 5.0 V8 Authorization — https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md
- OWASP Cheat Sheet Series — Authorization — https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- OWASP Top 10 Proactive Controls — C1: Implement Access Control — https://top10proactive.owasp.org/archive/2024/the-top-10/c1-accesscontrol/
- OWASP Top 10:2025 — A01 Broken Access Control — https://github.com/OWASP/Top10/blob/master/2025/docs/en/A01_2025-Broken_Access_Control.md
- Red Hat PatternFly — Empty state design guidelines — https://www.patternfly.org/components/empty-state/design-guidelines/
- Salesforce Lightning Design System — Messaging overview — https://winter-20.lightningdesignsystem.com/guidelines/messaging/overview/
- Smashing Magazine — Hidden vs. Disabled In UX — https://www.smashingmagazine.com/2024/05/hidden-vs-disabled-ux/
- Stripe Docs — User roles — https://docs.stripe.com/get-started/account/teams/roles
- W3C WAI — Understanding SC 3.2.3: Consistent Navigation — https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html
