# Drill-down Navigation — areas in the chrome, depth in pages

Load-bearing rules restated (these hold even if you read nothing else):

1. **Drill-down moves depth out of the chrome and into pages. It never hides navigation.** The
   global nav stays visible and holds only top-level **areas**.
2. **The global sidebar lists areas and nothing below them.** Static group labels are allowed; a
   section tree, a nested sub-menu, or a collapsible group is not. Every area's sections render in
   that area's own layout.
3. **Levels:** area → overview (optional) → list → detail → sub-detail. Nothing below level 5 is a
   page.
4. **Every level has a URL.** Filters, sort, query and the selected tab live in it, and Back returns
   to the view people last saw.
5. **Every level says where you are:** the active area and section, the `h1`, the document title.
   Breadcrumbs from level 3 on wide screens, a parent link on narrow ones, a header title with back
   on native.
6. **Breadcrumbs come from the server's `ancestors`** — never from history, never from URL segments.
7. **Search is the second way to every page set** (WCAG 2.4.5). A command palette mirrors the nav and
   never replaces it.
8. **Budgets count what one role sees after filtering:** 7 or fewer areas on desktop (an IA review
   above 10), 3–5 native tabs. Exceeding a budget triggers a design review, not a hard block.
9. **Permissions filter before levels are built.** An area a role cannot use never appears; a role
   with one area lands inside it.
10. **Flat is still right** for linear flows, small products and one-collection areas. Never
    manufacture depth.
11. **It applies to every product now** — new builds and existing ones. Migrating an existing
    navigation is in-scope work, and a violation on a legacy screen is scored at full severity.

The API half — endpoints per level, flat member URLs, `ancestors`, scoped counts, list parameters,
search, 404 for out-of-scope records — is `@skills/std-api-design/references/drill-down-resources.md`;
this file uses that contract without restating it. The worked example is the wholesale ordering
platform in `@skills/ui-ux-patterns/references/role-based-ux.md`.

---

## What "always drill-down" means

The hierarchy is revealed one level at a time **in the content area**, and the level above always
stays one step away. Clutter drops because depth leaves the global chrome — into overviews, lists,
details and area-local navigation — never because chrome is hidden:

- **Visible navigation wins.** "Visible navigation is the gold standard for both mobile and desktop"
  (Nielsen Norman Group — Left-Side Vertical Navigation on Desktop). Hidden navigation cut
  discoverability almost in half and made desktop users at least 39% slower (Nielsen Norman Group —
  Hamburger Menus and Hidden Navigation Hurt UX Metrics).
- **Deep is not safe either.** "Requiring users to click through so many levels to get to specific
  content usually doesn't work well" (Nielsen Norman Group — Flat vs. Deep Website Hierarchies).
- **Areas need local navigation** that stays less salient than the global nav (Nielsen Norman Group
  — Local Navigation Is a Valuable Orientation and Wayfinding Aid), and large sites use landing pages
  instead of multilevel cascades (Nielsen Norman Group — Menu-Design Checklist: 17 UX Guidelines).

**Not drill-down, and not allowed:** a sequential drill-down menu inside the global menu — people
press Back and leave it by accident (Nielsen Norman Group — Mobile Subnavigation); a sidebar that
swaps its contents for the current area behind "Back to main menu"; hub-and-spoke area switching on
mobile, where changing area means returning to a hub (Nielsen Norman Group — Basic Patterns for
Mobile Navigation).

## Primary navigation: visible, areas only

**An area** is a job-shaped part of the product that a role switches between — Orders, Fulfilment,
Invoices. It is not a site map (GOV.UK Design System — Help users to navigate a service), it is a
destination and never an action (Apple Human Interface Guidelines — Tab bars), and its label is
specific, because people choose a path without seeing what is deeper (Nielsen Norman Group —
Information Scent) — "be careful not to simplify to the point of abstraction" (Laws of UX — Hick's
Law).

**Visible by default.** The desktop sidebar ships open; collapsing it is the person's choice. "Do not
use hidden navigation (such as hamburger icons) in desktop user interfaces" (Nielsen Norman Group —
Hamburger Menus and Hidden Navigation Hurt UX Metrics), and Apple discourages hiding the sidebar by
default too (Apple Human Interface Guidelines — Sidebars).

| Context | Sources | House rule (per role, after filtering) |
|---|---|---|
| Phone, native tab bar | Tab bars struggle past 5 (Nielsen Norman Group — Basic Patterns for Mobile Navigation); "three to five destinations of equal importance" (Android Developers — Navigation bar); never hide or disable a tab (Apple Human Interface Guidelines — Tab bars) | **3–5 tabs, Account included.** More work areas → 4 area tabs plus a **More** tab that opens a visible list screen, never a drawer |
| Phone-width web | Show links openly at 4 or fewer top-level items (Nielsen Norman Group — Hamburger Menus and Hidden Navigation Hurt UX Metrics); GOV.UK collapses service navigation into a menu button on mobile (GOV.UK Design System — Service navigation) | **4 or fewer areas → a visible nav bar. 5 or more → a button labelled with the word "Menu"**, with the current area's section nav kept visible in the page |
| Desktop sidebar | Items from the seventh collapse into "View more" (Shopify — Navigation); flat for fewer than 8 peers (Microsoft Learn — Navigation basics for Windows apps); more than about 10 options overwhelmed test users (Baymard Institute — Homepage & Navigation UX Best Practices 2025); a collapsed rail holds "three to no more than seven app destinations" (Material Components for Android — Navigation rail) | **7 or fewer areas.** Above 10 for any role → an IA review: split, merge, or move into an overview. A rail only as the person's own collapse |

A breach triggers a **design review, not a hard block**: the review changes the IA or records why
the role needs more, and the per-role structure test carries the reviewed number. One canonical
order is trimmed per role and kept on every page and breakpoint (`role-based-ux.md`; W3C WAI
Tutorials — Menu Structure). The active area is marked — 95% of benchmarked sites fail to highlight
the current scope (Baymard Institute — Homepage & Navigation UX Best Practices 2025). Account,
profile and sign-out live in the header's user menu, not among the areas.

## The global sidebar: areas only

- **Allowed:** areas, and static group labels above them when a role sees about 6 or more areas that
  fall into 2–3 recognizable clusters. A group with one visible area loses its label; a group with
  none is not rendered (`role-based-ux.md`).
- **Banned:** a nested sub-menu under any area (the shadcn `SidebarMenuSub` included, even under the
  active area); section trees; collapsible groups — a collapsed group is hidden navigation; a
  recursive renderer over `children`; contents that swap per area.
- **Why no nesting at all.** Sidebars show "no more than two levels of hierarchy" (Apple Human
  Interface Guidelines — Sidebars), Nav "only supports one level of nesting" (Microsoft Fluent 2 —
  Nav usage), and a third tier becomes tabs in the page (IBM Carbon Design System — UI shell left
  panel). The house takes the strict reading so one rule holds at every width: the shadcn sidebar
  becomes an off-canvas Sheet on mobile (shadcn/ui — Sidebar (Base UI)), where nested sections would
  vanish behind the menu button, while sections in the area layout stay on screen. Primer moves
  sidebar links into the page on narrow viewports for the same reason (GitHub Primer — Navigation).
- **A tree is not navigation.** Primer forbids replacing NavList with a TreeView (GitHub Primer —
  NavList). Depth becomes pages.

## When flat is still right

- **Linear journeys** — wizard, checkout, onboarding — get steps, not navigation links (GOV.UK Design
  System — Help users to navigate a service). Breadcrumbs never show progress through a journey
  (GOV.UK Design System — Breadcrumbs), and steps in a process are exempt from Multiple Ways (W3C WAI
  — Understanding SC 2.4.5: Multiple Ways).
- **Small products whose areas are one screen deep:** the sidebar or tab bar *is* the IA, with no
  overviews and no breadcrumbs — breadcrumbs are unnecessary for 1–2-level sites (Nielsen Norman
  Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile).
- **An area with one collection** lands on its list; **a role with one area** lands inside it.
- **Never manufacture depth.** Subdividing too far creates thin, deep levels (Baymard Institute —
  Homepage & Navigation UX Best Practices 2025): no overview over one section, no sub-list for a
  handful of rows.

## The level model

| Level | What it is | Web URL shape | Exists when |
|---|---|---|---|
| **1 Area** | A global nav destination, not a page | — | Something inside it is permitted |
| **2 Overview** | The area's landing: sections previewed, scoped counts, "View all" per section | `/reports` | 2+ collections to choose between, or the role's job is watching |
| **3 List** | A collection — filtered, sorted, searched | `/orders?status=late&sort=due` | Always |
| **4 Detail** | One record; its sub-collections are URL tabs at the same level | `/orders/:orderId`, `/orders/:orderId/shipments` | Always |
| **5 Sub-detail** | A child record people act on individually | `/shipments/:shipmentId` (flat) | Children are records, not rows |
| *below 5* | Never a page: a row, a section, an in-page tab, or a URL-backed panel on level 5 | — | — |

- **Why level 5, and the click budget.** "Designs that go beyond 2 disclosure levels typically have
  low usability" (Nielsen Norman Group — Progressive Disclosure) — by analogy, at most two choice
  pages before a record. House choice: a detail is at most 2 selections from its area item, or 3 with
  an overview, and that overview links straight to each list, because "a roughly equal number of
  users preferred to bypass" intermediary pages (Baymard Institute — Consider Providing
  "Intermediary Category Pages").
- **Data depth is not IA depth.** User-created trees (folders in folders) repeat the list level, and
  their trail overflows the middle (IBM Carbon Design System — Breadcrumb). Storage →
  `@skills/std-database/references/hierarchies.md`.
- **One home area per record.** One canonical parent means one home area and one breadcrumb path. A
  Dashboard tile opens the canonical URL and the highlight moves to the home area; a second nested
  URL to the same record is forbidden.
- **Skip rules.** An overview with one visible section is not rendered. A list is never auto-skipped
  because it has one row: the redirect breaks Back, and the structure changes when a second row
  arrives.

## Location at every level

Cues that look obvious to designers often go unnoticed (Nielsen Norman Group — Navigation: You Are
Here), and a single-page app must update titles, headings and regions to match the view (W3C WAI
Curricula — Module 7: Rich Applications). People often arrive deep, so every page answers "where am
I?" by itself:

| Cue | L2 Overview | L3 List | L4 Detail | L5 Sub-detail |
|---|---|---|---|---|
| **Global nav** | Area current | Area current | Home area current | Home area current |
| **Section nav** | Overview current | Its section current | Its section marked | Its section marked |
| **`h1`** | Area name | List name | Record name | Record name |
| **Document title** (most specific first) | `Reports · Acme` | `Orders · Acme` | `Order #4812 · Orders · Acme` | `Shipment 2 · Order #4812 · Orders · Acme` |
| **Breadcrumb, wide web** | None | Only under an overview | Area root › `ancestors` › current | Area root › `ancestors` › current |
| **Narrow web** | None | Parent link under an overview | `‹ Orders` | `‹ Order #4812` |
| **Native header** | Tab root title | Title, back if pushed | Title + back | Title + back |

| Breadcrumb question | Sources | House rule |
|---|---|---|
| Start | Start at home (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile; GOV.UK Design System — Breadcrumbs) | **The area root page** — the visible global nav already carries "home" |
| Current page | Plain text last (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile); `aria-current="page"` (W3C WAI APG — Breadcrumb Pattern); omitted by default (IBM Carbon Design System — Breadcrumb) | **Included, last,** as plain text with `aria-current="page"` |
| When | Unnecessary for 1–2-level sites (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile); beyond two levels (Microsoft Learn — Navigation basics for Windows apps); deeper than parent/detail (GitHub Primer — Navigation) | **From level 3,** whenever the page has an ancestor page inside its area; never on the area root |
| Narrow screens | Never wrap; overflow the middle (IBM Carbon Design System — Breadcrumb); back links on narrow details (GitHub Primer — Navigation) | **Below `md`, only the parent item,** inside the same `nav`. Wide trails over 4 items show the first link, an overflow and the last two |
| Role | They add to global and local nav, never replace it (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile) | **Never the only way around an area** |

## Up, Back, and list state

- **Back is chronological; Up is hierarchical** (Android Developers — Principles of navigation). On
  the web Back is history, so Up is a real link — the breadcrumb, or the parent link on narrow
  screens. On native, the header back pops the area's stack.
- **Never an in-page "Back" that calls `history.back()`** — on a deep link it leaves the app. Apps
  give people breadcrumbs or a Back affordance (Shopify — Navigation); the house builds it as the Up
  link.
- **Back returns to the view people last saw.** Overlays, filtered lists and list → detail transitions
  each need a history entry; 59% of sites break this (Baymard Institute — 4 Design Patterns That
  Violate "Back" Button UX Expectations). Level changes, filter or sort changes and split-view row
  selection **push**; typing into a search box **replaces** until the query is committed.
- **List state lives in the URL:** filters, sort, query, view mode and the selected tab — the same
  parameters the API list takes (`drill-down-resources.md`; cursors and limits →
  `@skills/std-api-design/references/pagination-rails.md`). A cursor never goes into the UI URL.
- **The list crumb carries the list's state — one control, no separate "Back to results" link.**
  Baymard pairs hierarchy crumbs with a history link (Baymard Institute — E-Commerce Sites Need 2
  Types of Breadcrumbs); GOV.UK never combines a back link with breadcrumbs (GOV.UK Design System —
  Back link). The crumb's label and position stay pure hierarchy, and its `href` carries the query
  string last used on that list this session; someone arriving deep gets the plain list URL. The list
  always shows active filters with Clear, so a restored filter is never a surprise.
- **Scroll and per-area state.** Restore scroll on return to an unchanged list in the same session —
  "in most cases, preserving scroll position is the right choice" (Nielsen Norman Group — Designing
  Scroll Behavior; Baymard Institute — Return Users to the Same Place in the Product List); live
  queues start at the top on a fresh visit. On mobile each tab keeps its stack (Apple Human Interface
  Guidelines — Tab bars), and re-tapping the tab returns to the area root (React Navigation — Nesting
  navigators).

## Deep links

- **Every level is linkable:** a URL per level on the web; a linking path per screen mirroring the
  navigator nesting on native (React Navigation — Configuring links); frame navigation promoted to a
  visit with `data-turbo-action` (Turbo Handbook — Decompose with Turbo Frames); Next.js overlays that
  deep-link, survive a refresh and close on Back (Next.js docs — Parallel Routes).
- **A deep link renders the full location** — area, section, `h1`, title, and a breadcrumb from the
  detail's `ancestors` (an unreadable ancestor never arrives). On native the linking config seeds the
  area's list beneath the detail, which shows an up link to its real parent.
- **After sign-in, return to the deep link** (`role-based-ux.md`).
- **Denials:** a record outside scope → the not-found page; a feature without its grant → the
  no-access page (`@skills/ui-ux-patterns/references/role-based-ux-states.md`). A 404 never refetches
  `['me']`.

## Section navigation inside an area

Rendered by the area's own layout, in one placement — never in the global sidebar, never twice.

| Pattern | Fits when | Rules |
|---|---|---|
| **Section nav (local nav)** | The area has 2+ sections the role can open | Visible on every page of the area, less salient than the global nav (Nielsen Norman Group — Local Navigation Is a Valuable Orientation and Wayfinding Aid). By count (house choice, from Nielsen Norman Group — Mobile Subnavigation): **2–5** → navigation tabs in the area header; **6–15** → a section list beside the content on wide screens, a section menu on narrow; **more than 15** → an overview. One section → none |
| **Navigation tabs** | A detail's sub-collections (Lines · Shipments · Timeline) | Each tab is a link with its own URL and `aria-current`; in-page tabs only for alternate views nobody links to; never tabs when people must compare the content (Nielsen Norman Group — Tabs, Used Right; GitHub Primer — UnderlineNav) |
| **List-detail (split view)** | Wide windows; lists worked in sequence; a detail readable at half width with no sub-collections | Persistent selection highlight; one pane at a time at compact widths, Back returns to the list with its state (Apple Human Interface Guidelines — Split views; Android Developers — Canonical layouts) |
| **Overview** | Several collections, or a watching job | Previews each section with scoped counts and "View all" — the scent the sidebar no longer shows (Baymard Institute — Have a "View All" Option in the Main Navigation at Each Level of the Mobile Product Catalog) |
| **Lateral links** | Related records; working a queue | Related-record links; next and previous on a queue detail, so nobody pogo-sticks (Microsoft Learn — Navigation basics for Windows apps) |

## Search and the command palette — the second way

- **WCAG 2.2 AA requires a second way** to locate a page within a set, and W3C notes that search can
  be easier than a hierarchy for people with cognitive limitations (W3C WAI — Understanding SC 2.4.5:
  Multiple Ways). It does not replace navigation: "Using the navigation categories is often faster
  and easier for users than generating a good search query" (Nielsen Norman Group — Search Is Not
  Enough).
- **A global search field sits in the app header on every page** of every multi-level web app. It
  calls the permission-scoped search endpoint; each result shows its `ancestors` path and opens the
  canonical URL. The default scope (current area or everything) is a per-project decision, with the
  other scope one visible action away (GitHub Docs — GitHub Command Palette; Apple Human Interface
  Guidelines — Search fields). **Native search** sits in each area root's header; a Search tab only
  when search is a role's top task.

**The command palette — one shared organism.** "An accelerator is not a new feature — it is merely
an additional way of completing an existing action" (Nielsen Norman Group — Accelerators Maximize
Efficiency in User Interfaces). The house builds **one** `CommandPalette` organism for web products
(Next.js and the Vite SPA); each product decides whether to ship it, and nothing may depend on it.

| Part | Spec |
|---|---|
| **Opens from** | A visible, labelled header button showing the shortcut, **and** Cmd/Ctrl+K — never a shortcut alone |
| **Go to** | The same `visibleNav` output as the sidebar — areas and their sections — so it offers only pages the person can open, as GitHub's palette offers "any page that you have access to" (GitHub Docs — GitHub Command Palette). Never a second nav config |
| **Records** | The permission-scoped search endpoint, in the product's search scope; each hit shows its `ancestors` path |
| **Recent** | Pages and records opened this session; it never reorders the nav (`role-based-ux.md`) |
| **Actions** | House choice: only page actions also visible on their page, gated by the same permission key |
| **Selecting** | Navigates with a pushed history entry and focuses the new `h1`; Escape closes and returns focus to the opener |
| **Copy** | Every label, placeholder, group heading and empty message is a translation key |
| **Never** | The only route to anything; a palette-only feature; on native, where search lives in headers |

The markup → the `std-accessibility` skill. The web implementation — verify the installed `command`
primitive and its base before writing code → `@skills/std-shadcn-ui/references/components-and-blocks.md`.

## Actions: at most two disclosure levels

- **One primary action per level, in the page header;** secondary actions in one overflow menu named
  for its object ("Order actions", not "More") (Apple Human Interface Guidelines — Toolbars; Nielsen
  Norman Group — Information Scent).
- **Overflow → dialog is two levels; overflow → submenu → dialog is three, and too many** (Nielsen
  Norman Group — Progressive Disclosure).
- **In lists** the row is the drill-in link, a row menu holds secondary actions, and bulk actions
  appear once rows are selected. **Destinations and actions never mix:** "New order" is a page action,
  never a nav item. Which actions a role gets → `role-based-ux.md`.

## Roles and permissions

1. **Filter before building.** `visibleNav` runs before the global nav, section nav, overview cards,
   palette and landing page are composed — in the Next.js server layout, in `AppLayout` in the Vite
   SPA, at navigator registration in React Native, as controller booleans in Phlex. Hiding branches
   of a built tree leaves orphan headings and cards linking nowhere. The config, `visibleNav` and
   `areaState` → `@skills/access-control-designer/references/ui-gates.md`.
2. **An area a role cannot use never appears** — not in the sidebar, tab bar, overview cards,
   palette, or a breadcrumb.
3. **One permitted section → no section nav;** the area item links straight to that section.
4. **A role with one area lands inside it.** No global area list renders, and the area's section nav
   is that role's primary nav; on native the Account tab stays, so the role gets two tabs.
5. **Landing is derived** from the role's order and reachable sections (`role-based-ux.md`); a
   plan-locked area shows one locked entry, not a padlock per section.
6. **Compose the shell from `['me']`; never toggle visible tabs** (Apple Human Interface Guidelines
   — Tab bars).
7. **A role-conditional parallel slot is not authorization:** "Both slots render on the server,
   regardless of which one the layout returns" (Next.js docs — Parallel Routes).
8. **The role walkthrough gains a Navigation row:** areas in order, landing, selections to the top
   task.

| Role | Areas it sees, in order | Lands on | Global nav |
|---|---|---|---|
| Org Admin | Dashboard, Orders, Customers, Invoices, Reports, Organization | Dashboard, once setup is done | 6 areas; Organization's Members · Billing are section tabs in its layout |
| Sales Rep | Orders, Customers | My orders (a filtered list URL) | 2 areas |
| Warehouse Lead | Fulfilment, Orders | Pick queue, due today | 2 areas |
| Finance Clerk | Invoices, Orders, Reports | Invoices needing action | 3 areas |
| Executive | Dashboard, Orders, Reports | Dashboard | 3 areas; every KPI tile opens a filtered list in its home area |

## Accessibility — what each level exposes

The markup belongs to the `std-accessibility` skill; these are the outcomes it must produce.

- **Labelled landmarks holding lists of links** — Main, the area's sections, Breadcrumb — never
  `role="menu"`, which typical site navigation does not need (W3C WAI APG — Example Disclosure
  Navigation Menu; W3C WAI Tutorials — Menu Structure). The one disclosure is the phone-width
  **Menu** button.
- **`aria-current="page"`** only on the link to the current page, including the breadcrumb's last
  item (W3C WAI APG — Breadcrumb Pattern); `aria-current="true"` on the area or section the page sits
  inside.
- **Focus follows the level.** WCAG's focus-order criterion is silent on route changes (W3C WAI —
  Understanding SC 2.4.3: Focus Order), and W3C's curriculum fills the gap (W3C WAI Curricula —
  Module 7: Rich Applications): a level change focuses the new `h1`; a filter, sort or tab change
  keeps focus on its control; Back to a list focuses the row that drilled in.
- **One order, a second way:** areas keep their relative order everywhere (W3C WAI — Understanding
  SC 3.2.3: Consistent Navigation), and every page set is also reachable by search (2.4.5).
- **WCAG 2.4.8 Location — AAA, adopted as a house rule** and labelled the way `std-accessibility`
  labels 2.4.13: "Information about the user's location within a set of web pages is available." The
  cues above meet it through the breadcrumb (G65), the current location marked in the nav (G128) and
  `aria-current` (ARIA26) (W3C WAI — Understanding SC 2.4.8: Location).

## Verifying it — rendered, per role; no static hook

- **A rendered navigation test per role** renders the real layout with each role's `/me` fixture and
  asserts exactly the expected areas in order, nothing nested under the main nav, the count within
  the reviewed budget, no area list for a one-area role, section nav only in the area layout, and
  palette "Go to" entries equal to the visible nav → `@skills/access-control-designer/references/ui-gates.md`.
- **A keyboard pass per level** (arrival, Up, Back) → the `std-accessibility` skill. **Review:** the
  `design-critique` and `code-reviewer` agents check structure, location cues and the anti-patterns
  below on every screen, legacy screens included.
- **No static hook.** Every role sees a filtered subset of one config, so a file-level count or
  nesting match fires on correct code; only a rendered, per-role test sees what a person gets.

## Anti-patterns

| Anti-pattern | Symptoms | Fix |
|---|---|---|
| **Mega sidebar** | Every list, report and setting in the global sidebar; more than about 10 entries for a role (Laws of UX — Hick's Law; Baymard Institute — Homepage & Navigation UX Best Practices 2025) | Areas only; sections into the area layout |
| **Nested tree in the global sidebar** | Chevrons; a sub-menu under an area; group → area → section (Apple Human Interface Guidelines — Sidebars; GitHub Primer — NavList) | Areas only; depth becomes pages |
| **Hidden desktop navigation** | The sidebar collapsed by default; areas behind a menu icon on a wide screen (Nielsen Norman Group — Hamburger Menus and Hidden Navigation Hurt UX Metrics) | Visible by default; the person may collapse it |
| **Icon-only rail as shipped** | An icon rail by default; names only in tooltips (Nielsen Norman Group — Left-Side Vertical Navigation on Desktop) | Labelled by default; a rail only as the person's collapse |
| **Duplicate navigation** | The same sections in the sidebar and in page tabs; quick links repeating the nav; two items current | One placement per product |
| **Filters in the navigation sidebar** | List filters mixed into the global sidebar, so the nav changes shape per page | A filter panel in the list page (`screen-patterns.md`) |
| **Dead-end detail** | No breadcrumb or parent link, no related links, no next item in a queue (Shopify — Navigation) | Location cues, an Up link, lateral links |
| **Breadcrumbs from history** | The trail changes with the route taken; a refresh empties it (Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile) | Render the server's `ancestors` |
| **Manufactured depth** | An overview with one card; a "choose a region" page for a one-region role (Nielsen Norman Group — Flat vs. Deep Website Hierarchies) | The click budget and skip rules |
| **Back-button traps** | An in-app Back calling `history.back()`; filters or overlays with no history entry (Baymard Institute — 4 Design Patterns That Violate "Back" Button UX Expectations) | Real Up links; push per level; test Back at every level |
| **Search or palette as the only route** | Records reachable only by typing; a shortcut with no button (Nielsen Norman Group — Search Is Not Enough; Nielsen Norman Group — Accelerators Maximize Efficiency in User Interfaces) | A browsable hierarchy plus search |
| **Drawer-only areas on mobile** | Areas in a hamburger or a hub (Nielsen Norman Group — Mobile Subnavigation) | A persistent tab bar of 3–5 |
| **Tabs as fake navigation** | In-page tabs for sections that need URLs (Nielsen Norman Group — Tabs, Used Right) | Navigation tabs with URLs |

## Existing products

The standard applies to existing products now, not at their next redesign. The
`requirements-consultant` and `architecture-advisor` agents treat migrating an existing navigation
as in-scope work — flattening a nested sidebar into areas plus area layouts, moving filters out of
it, putting list state into URLs, building breadcrumbs from `ancestors`, adding search — and
`design-critique` scores legacy violations at full severity.

## Platform mechanics

| | Next.js (App Router) | Vite SPA (React Router) | React Native (React Navigation) | Rails Phlex (Turbo + Stimulus) |
|---|---|---|---|---|
| **Area** | A route group with its own layout | A pathless layout route around its own `<Outlet />` | A bottom tab owning one native stack | An area layout template |
| **Section nav** | A client leaf in the area layout reading `usePathname()` | The area layout component | A segmented control (2–4) or a section list screen | An organism fed controller booleans |
| **List state** | `searchParams` | `useSearchParams` | Screen params | Query params; the list crumb's query kept in the session |
| **Breadcrumb** | Server-rendered from `ancestors` | Rendered from `ancestors` | Header title + back; an up link from `ancestors` | Items built by the controller from `ancestors` |
| **Split view** | A parallel slot plus an intercepting route | A child route rendered beside the list | The platform's split view on tablets | A Turbo Frame with `data-turbo-action="advance"` |
| **Back and scroll** | Test Back on the pinned version | `<ScrollRestoration />` | The stack keeps the list mounted | Restoration visits (Turbo Handbook — Navigate with Turbo Drive) |
| **Guide** | `@skills/std-nextjs/references/navigation.md` | `@skills/std-reactjs/references/routing-and-code-split.md` | `@skills/std-react-native/references/navigation.md` | `@skills/std-phlex-conventions/references/turbo-frames-and-streams.md`, `@skills/std-phlex-conventions/references/component-levels-composites.md` |

The global `AppSidebar` on shadcn/ui primitives → `@skills/std-shadcn-ui/references/components-and-blocks.md`.

## Checklist

- [ ] Each role's areas counted after filtering: 7 or fewer on desktop, 3–5 native tabs, or a recorded design review
- [ ] The global sidebar lists areas only — optional static group labels, nothing nested or collapsible — and ships open
- [ ] Each area's sections render in its own layout, once, only when two or more remain
- [ ] Phone-width web: 4 or fewer areas shown openly; 5 or more behind a "Menu" button, section nav kept in the page
- [ ] Every page sits at one level of one area; nothing below level 5 is a page; no manufactured depth
- [ ] Location cues at every level; breadcrumbs from level 3, built from `ancestors`
- [ ] Every level, filter, sort, query and tab has a URL; Up is a real link; Back tested at every level
- [ ] The list crumb's `href` restores the list's state; scroll restored on return
- [ ] A record outside scope is not found; a feature without its grant is no access
- [ ] Header search on every page; a shipped palette is fed by `visibleNav` and search and has a visible button
- [ ] Actions disclose at most two levels; destinations and actions never mix
- [ ] A rendered navigation test per role; a keyboard pass per level; existing products migrated, not grandfathered

## Owned elsewhere — do not duplicate

- **Nav order per role, landing, the three-state rule, locked areas** → `@skills/ui-ux-patterns/references/role-based-ux.md`
- **No access vs not found, the kinds of empty, loading** → `@skills/ui-ux-patterns/references/role-based-ux-states.md`
- **The nav config, `visibleNav`, `areaState`, feature gates, per-role tests** → `@skills/access-control-designer/references/ui-gates.md`
- **Endpoints per level, `ancestors`, scoped counts, list parameters, search** → `@skills/std-api-design/references/drill-down-resources.md`; hierarchy storage → `@skills/std-database/references/hierarchies.md`
- **ARIA, focus management, target sizes, the 2.4.8 house rule** → the `std-accessibility` skill
- **Selected-state cues and the salience of navigation chrome** → the `std-design-system` skill
- **Sidebar, breadcrumb and command primitives; `render` vs `asChild`** → `@skills/std-shadcn-ui/references/components-and-blocks.md`
- **List/Detail, Search, Settings and Dashboard layouts** → `@skills/ui-ux-patterns/references/screen-patterns.md`

## Sources

**Research and guidelines**

- Nielsen Norman Group — Flat vs. Deep Website Hierarchies — https://www.nngroup.com/articles/flat-vs-deep-hierarchy/
- Nielsen Norman Group — Local Navigation Is a Valuable Orientation and Wayfinding Aid — https://www.nngroup.com/articles/local-navigation/
- Nielsen Norman Group — Left-Side Vertical Navigation on Desktop — https://www.nngroup.com/articles/vertical-nav/
- Nielsen Norman Group — Hamburger Menus and Hidden Navigation Hurt UX Metrics — https://www.nngroup.com/articles/hamburger-menus/
- Nielsen Norman Group — Menu-Design Checklist: 17 UX Guidelines — https://www.nngroup.com/articles/menu-design/
- Nielsen Norman Group — Navigation: You Are Here — https://www.nngroup.com/articles/navigation-you-are-here/
- Nielsen Norman Group — Breadcrumbs: 11 Design Guidelines for Desktop and Mobile — https://www.nngroup.com/articles/breadcrumbs/
- Nielsen Norman Group — Progressive Disclosure — https://www.nngroup.com/articles/progressive-disclosure/
- Nielsen Norman Group — Information Scent — https://www.nngroup.com/articles/information-scent/
- Nielsen Norman Group — Mobile Subnavigation — https://www.nngroup.com/articles/mobile-subnavigation/
- Nielsen Norman Group — Basic Patterns for Mobile Navigation — https://www.nngroup.com/articles/mobile-navigation-patterns/
- Nielsen Norman Group — Tabs, Used Right — https://www.nngroup.com/articles/tabs-used-right/
- Nielsen Norman Group — Search Is Not Enough — https://www.nngroup.com/articles/search-not-enough/
- Nielsen Norman Group — Accelerators Maximize Efficiency in User Interfaces — https://www.nngroup.com/articles/ui-accelerators/
- Nielsen Norman Group — Designing Scroll Behavior — https://www.nngroup.com/articles/saving-scroll-position/
- Baymard Institute — Homepage & Navigation UX Best Practices 2025 — https://baymard.com/blog/ecommerce-navigation-best-practice
- Baymard Institute — Consider Providing "Intermediary Category Pages" — https://baymard.com/blog/ecommerce-sub-category-pages
- Baymard Institute — Have a "View All" Option in the Main Navigation at Each Level of the Mobile Product Catalog — https://baymard.com/blog/mobile-main-nav-view-all
- Baymard Institute — E-Commerce Sites Need 2 Types of Breadcrumbs — https://baymard.com/blog/ecommerce-breadcrumbs
- Baymard Institute — 4 Design Patterns That Violate "Back" Button UX Expectations — https://baymard.com/blog/back-button-expectations
- Baymard Institute — Return Users to the Same Place in the Product List — https://baymard.com/blog/return-same-place
- Laws of UX — Hick's Law — https://lawsofux.com/hicks-law/

**W3C WAI**

- W3C WAI APG — Breadcrumb Pattern — https://www.w3.org/WAI/ARIA/apg/patterns/breadcrumb/
- W3C WAI APG — Example Disclosure Navigation Menu — https://www.w3.org/WAI/ARIA/apg/patterns/disclosure/examples/disclosure-navigation/
- W3C WAI Tutorials — Menu Structure — https://www.w3.org/WAI/tutorials/menus/structure/
- W3C WAI — Understanding SC 2.4.3: Focus Order — https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html
- W3C WAI — Understanding SC 2.4.5: Multiple Ways — https://www.w3.org/WAI/WCAG22/Understanding/multiple-ways.html
- W3C WAI — Understanding SC 2.4.8: Location — https://www.w3.org/WAI/WCAG22/Understanding/location.html
- W3C WAI — Understanding SC 3.2.3: Consistent Navigation — https://www.w3.org/WAI/WCAG22/Understanding/consistent-navigation.html
- W3C WAI Curricula — Module 7: Rich Applications — https://www.w3.org/WAI/curricula/developer-modules/rich-applications/

**Design systems**

- GOV.UK Design System — Help users to navigate a service — https://design-system.service.gov.uk/patterns/navigate-a-service/
- GOV.UK Design System — Service navigation — https://design-system.service.gov.uk/components/service-navigation/
- GOV.UK Design System — Breadcrumbs — https://design-system.service.gov.uk/components/breadcrumbs/
- GOV.UK Design System — Back link — https://design-system.service.gov.uk/components/back-link/
- Apple Human Interface Guidelines — Tab bars — https://developer.apple.com/design/human-interface-guidelines/tab-bars
- Apple Human Interface Guidelines — Sidebars — https://developer.apple.com/design/human-interface-guidelines/sidebars
- Apple Human Interface Guidelines — Split views — https://developer.apple.com/design/human-interface-guidelines/split-views
- Apple Human Interface Guidelines — Toolbars — https://developer.apple.com/design/human-interface-guidelines/toolbars
- Apple Human Interface Guidelines — Search fields — https://developer.apple.com/design/human-interface-guidelines/search-fields
- Android Developers — Principles of navigation — https://developer.android.com/guide/navigation/principles
- Android Developers — Canonical layouts — https://developer.android.com/develop/ui/compose/layouts/adaptive/canonical-layouts
- Android Developers — Navigation bar — https://developer.android.com/develop/ui/compose/components/navigation-bar
- Material Components for Android — Navigation rail — https://raw.githubusercontent.com/material-components/material-components-android/master/docs/components/NavigationRail.md
- Microsoft Learn — Navigation basics for Windows apps — https://learn.microsoft.com/en-us/windows/apps/design/basics/navigation-basics
- Microsoft Fluent 2 — Nav usage — https://fluent2.microsoft.design/components/web/react/core/nav/usage
- IBM Carbon Design System — UI shell left panel — https://carbondesignsystem.com/components/UI-shell-left-panel/usage/
- IBM Carbon Design System — Breadcrumb — https://carbondesignsystem.com/components/breadcrumb/usage/
- Shopify — Navigation — https://shopify.dev/docs/apps/design/navigation
- GitHub Primer — Navigation — https://primer.style/product/ui-patterns/navigation/
- GitHub Primer — NavList — https://primer.style/product/components/nav-list/
- GitHub Primer — UnderlineNav — https://primer.style/product/components/underline-nav/

**Framework and product documentation**

- shadcn/ui — Sidebar (Base UI) — https://ui.shadcn.com/docs/components/base/sidebar
- GitHub Docs — GitHub Command Palette — https://docs.github.com/en/get-started/accessibility/github-command-palette
- Next.js docs — Parallel Routes — https://nextjs.org/docs/app/api-reference/file-conventions/parallel-routes
- React Navigation — Nesting navigators — https://reactnavigation.org/docs/nesting-navigators
- React Navigation — Configuring links — https://reactnavigation.org/docs/configuring-links
- Turbo Handbook — Decompose with Turbo Frames — https://turbo.hotwired.dev/handbook/frames
- Turbo Handbook — Navigate with Turbo Drive — https://turbo.hotwired.dev/handbook/drive
