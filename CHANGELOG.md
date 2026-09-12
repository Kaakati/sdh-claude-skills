# Changelog

All notable changes to the `sdh` plugin are documented here, following
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/).

> **This changelog is an interface.** When a release changes what gets **denied**, how a **gate**
> behaves, or what the **permission floor** contains, that is a behavioural change to every
> consuming repo's development process — read it as you would an API changelog.
>
> **⚠️ A plugin cannot ship `permissions`.** Any change under **Permission floor** below must be
> **copied by hand** into your project's `.claude/settings.json`. The SessionStart sentinel will
> tell you, by name, exactly which rules you are missing — including when a floor you copied
> earlier has gone **stale**.

## [Unreleased]

## [4.0.0] - 2026-09-11

**MAJOR, because this release adds deny rules and changes what the gates decide.** The permission
floor gains two Bash denies and a `PowerShell(...)` mirror of every shell deny. Several PreToolUse
gates now deny or ask where they did not, PowerShell and Monitor commands included, which reached no
gate in 3.2.0 (*Changed → Hook decisions*). Per `docs/releasing.md`, either change alone makes a
major bump.

**Drill-down navigation becomes the house standard, for new and existing products.** The global
navigation lists areas only, and each area's sections live in that area's own layout. Every level
has a URL, breadcrumbs come from the API's `ancestors`, and search is the second way in. APIs become
drill-down-ready to match: shallow nesting, a permission-filtered `ancestors` chain, counts computed
inside the caller's scope, and authorization at every level.

**Access control — in the product you are building.** This release teaches how to design
application authorization: roles, a permission matrix, Pundit policies on the Rails API, CASL gates
in the JS frontends, and role-gated sidebars, menus, and actions. That work is **not** about Claude
Code's own tool permissions. Alongside it:

- `std-database` learns to design relationships and hierarchies before migrating them, and Next.js
  UI gets its own agent.
- **shadcn/ui becomes the component standard for Next.js and the Vite SPA** (Base UI by default,
  Radix kept for existing packages). It is delivered as a new path-scoped skill, `std-shadcn-ui`.
- **Charts get one library per stack, and ApexCharts leaves the house** over its licence. Next.js
  uses shadcn/ui's `chart` component (Recharts), the Vite SPA uses Chart.js through
  `react-chartjs-2`, and Rails Phlex views use Chart.js through a house Stimulus controller.
  shadcn's token names become aliases of the house tokens.
- **`--border` and `--input` are darker** in every preset, so field edges and borders reach 3:1.
- **Architecture and database orthogonality, caught early.** A new `orthogonality` skill, a shared
  standard-library engine, and three advisory hooks find:
  - a second model or table for an existing concept, and a fact stored twice;
  - a second library for a concern the house already covers;
  - imports, writes, or cycles across bounded contexts.

  None of the three hooks asks or denies, the feature changes nothing in the permission floor, and
  no tool is ever installed (*Added → Orthogonality*).
- **Every hook was re-audited against the current Claude Code hook contract**, and its confirmed
  defects were fixed. That *does* change what Claude may run or write. Some commands and edits that
  were denied now pass, and some that passed are now denied or asked. The five shell gates now also
  judge the PowerShell and Monitor tools, and the permission floor mirrors every shell deny for
  PowerShell. Every such change is listed under *Changed → Hook decisions*.

### Upgrade steps (ACTION REQUIRED)

1. **Permission floor.** A plugin cannot ship `permissions`, so copy these by hand into every
   consuming project's `.claude/settings.json`, and into any deployed `managed-settings.json`:
   - replace the malformed `Bash(rm -rf /)*` with `Bash(rm -rf /)` (*Fixed*);
   - add `Bash(terraform apply -destroy:*)` and `Bash(tofu apply -destroy:*)` beside the existing
     destroy rules (*Changed*);
   - **add the `PowerShell(...)` mirrors** (*Changed → Permission floor*). A `Bash(...)` rule never
     matches the PowerShell tool, which is on by default on Windows. Into every project floor, these
     16, as `.claude/settings.json` lists them:

     ```
     PowerShell(sudo:*)
     PowerShell(chmod 777:*)
     PowerShell(Remove-Item / *)
     PowerShell(Remove-Item * /)
     PowerShell(Remove-Item * / *)
     PowerShell(Remove-Item *:/)
     PowerShell(Remove-Item *:/ *)
     PowerShell(Invoke-Expression:*)
     PowerShell(terraform destroy:*)
     PowerShell(tofu destroy:*)
     PowerShell(terraform apply -destroy:*)
     PowerShell(tofu apply -destroy:*)
     PowerShell(terraform state rm:*)
     PowerShell(terraform state mv:*)
     PowerShell(terraform state push:*)
     PowerShell(terraform force-unlock:*)
     ```

     Into a deployed `managed-settings.json`, the same 16 plus `PowerShell(nc:*)` and
     `PowerShell(ncat:*)` beside `Bash(nc:*)` and `Bash(ncat:*)`: 18, as
     `.claude/managed-settings.template.json` lists them.
   - **`PowerShell(Invoke-Expression:*)` denies `iex` outright.** Claude Code checks each command of
     a PowerShell pipeline on its own, so the rule cannot see what feeds `iex`: an `irm <url> | iex`
     installer and `fnm env | Out-String | Invoke-Expression` are both denied. Run those outside
     Claude Code.

   Until you do, the SessionStart sentinel reports the floor as stale and names each missing rule,
   the PowerShell mirrors included. **A managed floor does not need `Read(**/*secret*)`:** when
   managed settings carry the whole catastrophic tier (the managed template's list), the sentinel
   treats that floor as complete and reports a missing `Read(**/*secret*)` to the model as a note,
   not a GOVERNANCE GAP. The rule belongs in project settings, and the managed template leaves it out
   on purpose. With no managed floor, a project floor that lacks it is still a gap.
2. **Design tokens, if you copied them.**
   - Re-copy the Tailwind v4 stylesheet from `theming/references/platform-integration.md`
     (*Changed → Design tokens*): complete `hsl()` values registered under `@theme inline`, and the
     alias block for shadcn's token names. House classes keep working with an older stylesheet, but
     shadcn primitives' alias classes (`bg-destructive`, `bg-sidebar`, `fill-chart-1`) compile to no
     CSS without the new one. Change any `hsl(var(--X))` to `var(--X)`.
   - Replace `--border` and `--input`, light and dark, in the stylesheet and the React Native
     tokens (*Fixed → Accessibility tokens*). They now measure about 3.2:1 against `--background`
     and `--card`: Default and Corporate `214.3 31.8% 59%` / `217.2 32.6% 42%`, Modern
     `240 5.9% 58%` / `240 3.7% 39%`, Minimal `0 0% 56%` / `0 0% 38%`. Re-measure any customised
     preset against 3:1. Card edges, table rules and separators become visibly darker.
   - **Tinted surfaces stay below 3:1.** A field on `muted`, `secondary` or `accent` measures
     2.92:1 (light) and 2.40:1 (dark), so give that field its own `bg-background` fill and a visible
     label.
3. **Charts, per stack. ApexCharts leaves the house over its licence.** Nothing flags an existing
   chart, but agents and the skills now write the stack's library, and `code-reviewer` reports any
   other (*Changed → Charts*):
   - **Next.js:** `shadcn add chart`. The Server Component renders the caption, summary and data
     table; every Recharts series takes `isAnimationActive={!reduceMotion}`.
   - **Vite SPA:** `npm install chart.js@4.5.1 react-chartjs-2@5.3.1`, then add
     `src/lib/charts/register.ts` and `useChartTokens`, and put `vitest-canvas-mock` plus a
     `ResizeObserver` stub in test setup. Chart tokens must hold complete `hsl()` values.
   - **Rails Phlex views:** Chart.js 4.5.1 through the house `chart` Stimulus controller. Replace
     Chartkick helpers. Importmap apps replace any `bin/importmap pin chart.js` with the committed
     single-file build, or move to jsbundling-rails.
   - Then drop `apexcharts` and `react-apexcharts` from `package.json`, along with any vendor chunk
     that names them.
   - **Vite SPA vendor chunks on Vite 8:** replace `build.rollupOptions.output.manualChunks` with
     `build.rolldownOptions.output.codeSplitting.groups` (*Changed*). The `manualChunks` object form
     that `std-reactjs/references/routing-and-code-split.md` showed in 3.2.0 fails a Vite 8 build. A
     Vite 7 package keeps `manualChunks` until it upgrades.
4. **Drill-down navigation applies to existing products now.** The global sidebar (the bottom tab
   bar on mobile) lists areas only, and each area's section nav lives in that area's own layout.
   `design-critique` scores violations on existing screens at full severity, and
   `requirements-consultant` and `architecture-advisor` treat migrating existing navigation as
   in-scope work, so expect new findings on products that already ship:
   - **Web:** flatten nested global sidebars into areas plus area layouts, moving `SidebarMenuSub`
     and collapsible nav sections into each area's layout. Replace hardcoded `navItems` arrays and
     nested sidebar sections (as the earlier `atomic-design` page examples showed) with
     `NAV: Area[]` plus `visibleNav`, and `pathname.startsWith` active checks with `areaState`. Move
     list filters out of the sidebar into the URL, build breadcrumbs from `ancestors`, and add
     header search.
   - **Command palette:** optional per product. Where a web product has one, build the one shared
     organism in `std-shadcn-ui/references/components-and-blocks.md`: it is fed by `visibleNav` and
     the search endpoint, opens from a visible button, and is never the only way to reach a page.
   - **Vite SPA on React Router 8:** uninstall `react-router-dom`, import from `react-router`, and
     take `RouterProvider` from `react-router/dom`. v8 needs React 19.2.7+ and Node 22.22+, so an
     app still on React 18 stays on v7 until it moves.
   - **React Native:** replace any drawer used to switch areas with one bottom tab per area, each
     holding a native stack. Give every screen a linking path that matches the web URL, send links a
     role cannot open to the no-access screen, and add the per-role rendered navigation test.
   - **Rails Phlex views:** move section links out of the global sidebar into each area's layout,
     build nav and breadcrumbs in the controller, and rename `NavLink`'s `active:` to `current:`.
5. **Drill-down-ready APIs, existing endpoints included** (*Added →
   `std-api-design/references/drill-down-resources.md`*). Collection routes nest one level under one
   canonical parent, and member routes are flat by ID. A detail carries a permission-filtered
   `ancestors` chain, every level scopes before it finds (404 outside scope), and counts are computed
   inside the caller's scope. Migrate endpoints that nest member routes under a parent, show
   `counter_cache` badges to own- or team-scoped callers, or build ETags without the viewer and
   `permissions_version`. `requirements-consultant` asks each product's open drill-down questions,
   and `architecture-advisor` records the answers in an ADR.
6. **Read *Changed → Hook decisions*** before rolling this out to a team. It is the same seven
   PreToolUse gate scripts, but their decisions moved:
   - the three security gates now fail closed when Python is missing;
   - the five shell gates now judge PowerShell and Monitor commands as well as Bash, so a PowerShell
     `irm <url> | iex` installer, or `Remove-Item -Recurse -Force` on a drive root, is denied;
   - a bare `git push` or `git push origin HEAD` that lands on a protected branch now asks, and a
     forced one is denied;
   - MCP tools reach `security-scan` and `mcp-install-gate` only through an anchored list of
     file-writing tool names (`write_file`, `edit_file`, `create_directory`, `move_file`,
     `create_or_update_file`, `push_files`), so an MCP file server whose writers use other names is
     not scanned.
7. **Orthogonality asks nothing of you.** Its three hooks never ask, deny or block, and the feature
   adds nothing to the permission floor.
   - **The index** is a rebuildable cache under `${CLAUDE_PLUGIN_DATA}/orthogonality/`, removed with
     the plugin. Nothing is written into a project unless a scan runs with `--write-report`
     (`.claude/orthogonality/last-scan.json`, in a directory that gitignores itself), so there is
     nothing to add to your `.gitignore`.
   - **Optional:** commit `.claude/orthogonality.json` to declare bounded contexts, table ownership,
     sanctioned cross-context writes, intentional duplicates and library migrations. Every kept
     exception names an ADR, and once a migration's `until` date passes, its finding returns.
     Projects already on packwerk, import-linter or tach need no change: those declarations are read
     as they are.
   - **Switches:** `SDH_ORTHOGONALITY=off` turns the hooks off. The watcher runs community tools the
     project already has only with `SDH_ORTHOGONALITY_TOOLS=1`, and never installs one.

**Pin it** (the `/plugin marketplace add` form floats on `main`):

```json
{ "name": "sdh",
  "source": { "source": "github", "repo": "Kaakati/sdh-claude-skills", "ref": "v4.0.0" } }
```

### Added

- **`ui-ux-patterns/references/drill-down-navigation.md`** — the house drill-down navigation
  standard. It applies to existing products now:
  - **Global sidebar:** areas only, no nested sections (static group labels allowed). Each area's
    sections render in that area's own layout.
  - **Budgets per role, after permission filtering:** 7 or fewer desktop areas (an IA review above
    10) and 3–5 native tabs. A breach triggers a design review, not a hard block.
  - **Structure and location:** the level model (area → overview → list → detail → sub-detail),
    location cues at every level, and breadcrumbs from the API's `ancestors`.
  - **Back and list state:** Up links, and list state (filters, sort, query) that comes back
    through the list breadcrumb's `href`.
  - **Search as the second way** (WCAG 2.4.5), plus one shared command-palette organism fed by
    `visibleNav` and the search endpoint: optional per product, never the only way to a page.
  - **Phone-width web** with 5 or more areas gets a button labelled "Menu", and the current area's
    section nav stays visible in the page.
  - Accessibility outcomes, anti-patterns, and the mechanics for each stack.

  **Reached from** every skill and agent that builds or reviews navigation: the per-stack `std-*`
  skills and their `-dev` skills, `ui-ux-patterns`, `atomic-design`, `std-accessibility`,
  `std-design-system`, `access-control-designer`, `figma-handoff`, `web-design-guidelines`,
  `design-to-code`, and the `design-critique`, `design-system-architect`, `code-reviewer`,
  `requirements-consultant`, `architecture-advisor`, `nextjs-developer`, and `phlex-developer`
  agents.
- **`std-api-design/references/drill-down-resources.md`** — the drill-down-ready API contract:
  - level → endpoint mapping, shallow nesting with flat member IDs, and deep links
  - the permission-filtered `ancestors` payload inside `{ data }`, root first
  - counts computed inside the caller's scope, with summary endpoints (`asOf` on read models)
  - the list contract, citing the house pagination references without restating their numbers
  - closed `?include=` allow-lists, per-level ETags carrying `permissions_version`, and realtime
    invalidation by `ancestorIds`
  - search as the second way in, and authorization at every level (scope, then find; 404)
  - one ancestors contract: `Hierarchy::Ancestors#for(record)` returns policy-filtered records from
    each model's `ancestor_chain`, root first
  - Rails, FastAPI, and DRF sketches. The DRF nested-collection ViewSet checks the parent in
    `initial()` for every action, create included (DRF's `create()` never calls `get_queryset()`),
    saves under that parent in `perform_create`, and ships a test that a cross-tenant POST returns
    404 and creates nothing
  - the per-project questions `requirements-consultant` asks (the answers go in an ADR through
    `architecture-advisor`)

  **Reached from** `std-api-design`, `api-designer`, `std-rails-conventions`, `rails-architect`,
  `std-fastapi`, `std-django`, `python-dev`, `std-database`, `std-python-performance`,
  `performance-profiler`, the frontend `std-*` and `-dev` skills, `ui-gates.md`, and the
  `requirements-consultant`, `architecture-advisor`, `code-reviewer`, `design-critique`,
  `nextjs-developer`, and `phlex-developer` agents.
- **`std-database/references/hierarchies.md`** — how to store a tree. The default is an adjacency
  list with a recursive CTE, guarded by `CYCLE` and a depth cap; `ancestry`, `ltree`, and
  `closure_tree` are the alternatives; new nested sets and django-mptt are ruled out. The Rails
  `ancestry` sketch uses the released `:materialized_path2` format with `primary_key_format` for UUID
  keys; its `:ltree` format is unreleased and integer-key only, and hyphenated UUID ltree labels need
  PostgreSQL 16+. It covers
  library choices with maintenance status, index and write cost per storage, and the read models
  (counter caches, materialized views, `asOf`) behind overview counts. **Reached from**
  `std-database`, `std-api-design`, `api-designer`, `db-migration`, `rails-architect`,
  `std-django`, `std-python-performance`, `python-dev`, and the `architecture-advisor` and
  `code-reviewer` agents.
- **Drill-down navigation, per stack:**
  - `std-nextjs/references/navigation.md` — one route group per area. The app layout filters with
    `visibleNav`, and a one-area role gets no sidebar. Section sub-nav lives in area layouts (via
    `areaState`), list state in `searchParams`, and list-detail uses parallel plus intercepting
    routes, with an `@detail/page.tsx` returning null so a soft navigation closes the panel.
    Breadcrumbs come from `ancestors`, with a list crumb that restores the query; focus
    moves on each level change; nav structure is tested per role.
  - **Vite SPA**, in `std-reactjs/references/routing-and-code-split.md` — each area is a pathless
    layout route whose `AreaLayout` renders the section nav and its own `<Suspense>`.
    `<ScrollRestoration />` is keyed by pathname plus search for lists; list state lives in search
    params (filters push, typing replaces); the list crumb restores this session's list state;
    breadcrumbs come from `ancestors`; code and data are prefetched on hover and focus.
    `data-fetching.md` gains hierarchical TanStack Query keys per drill level and ancestor
    invalidation from `ancestorIds` change events. `state-placement.md` puts a list's filters in the
    URL; Zustand keeps panel filters, and cursors stay in `useInfiniteQuery`.
  - `std-react-native/references/navigation.md` — three navigators at most (a root stack, one
    bottom tab per area, a native stack per tab), and 3–5 tabs including Account, built from
    `visibleNav`. Every level has a linking path that matches the web URL, and a `getStateFromPath`
    guard sends a path the role lacks to no-access. Up after a deep link is rebuilt from
    `ancestors`; section switching and list state live in route params; screen-reader focus moves
    with `sendAccessibilityEvent`; a rendered navigation test runs per role. **Reached from**
    `std-react-native`, `react-native-dev`, and `react-native-best-practices`.
  - `std-phlex-conventions/references/navigation.md` — shallow routes; a controller-built
    `Navigation` over `policy(:navigation)` with whole-segment current state; an areas-only
    `AppSidebar`; an `AreaLayout` that renders the section sub-nav; breadcrumbs from the
    permission-filtered `ancestors` records, with the list crumb carrying list state; lazy scoped-count
    frames; command-palette rules; a per-role navigation request spec; and anti-patterns.
    `turbo-frames-and-streams.md` gains the list-detail decision: row links promoted with
    `data-turbo-action="advance"`, the record page wrapping its body in the same frame, focus moved
    on `turbo:frame-load`, and one pane at a time below `lg`.
- **The shared command palette** on shadcn `command` (cmdk), in
  `std-shadcn-ui/references/components-and-blocks.md`. It is fed by `visibleNav` and the search
  endpoint, opens from a visible button and Cmd/Ctrl+K, uses translated dialog labels, and documents
  the verified per-base difference in `CommandDialog`.
- **Chart references, one per stack** (the standard is under *Changed → Charts*):
  - `std-shadcn-ui/references/charts.md` — Next.js, on shadcn's `chart` (Recharts). A Server
    Component fetches and renders the loading, empty and error states plus the caption, summary and
    data table; a `'use client'` leaf draws from plain points with `var(--chart-N)` colours and
    `isAnimationActive={!reduceMotion}`. It also covers lazy chart modules, tests, and the fact that
    chart blocks exist only for Radix.
  - `std-phlex-conventions/references/charts.md` — Chart.js 4.5.1 in Rails Phlex views through a
    house Stimulus controller:
    - install through jsbundling-rails (preferred); why `bin/importmap pin chart.js` 404s, and the
      committed single-file esbuild build with its exact pin (no separate `@kurkle/color` pin)
    - a `ChartFigure` organism with a caption, summary, and a data table outside the canvas
    - a Turbo-safe lifecycle: preview skip, `Chart.getChart` guard, destroy on disconnect and
      `turbo:before-cache`, rebuild on `turbo:render`, and morph handling
    - token colours re-read on `.dark`, reduced motion, a CSP with no `unsafe-inline`, I18n
      formatting, and component plus system specs; a missing `Filler` logs Chart.js's console
      warning, which the system spec fails on

    Chartkick is rejected.
- **`std-nextjs/references/caching.md` · per-level revalidation:** entity plus ancestor tags,
  per-user levels never cached, `cacheTag` limits, `revalidatePath` layout scope, and the Next.js 16
  forms (*Changed*).
- **`std-accessibility` · *Navigation, location, and focus on a level change*:** labelled `nav`
  landmarks, `aria-current` `page` vs `true`, the APG breadcrumb pattern, focus on drill-in, Up and
  Back, 3.2.3, and 2.4.5. WCAG 2.4.8 Location is adopted as an AAA house rule.
- **`std-design-system` · *Navigation chrome*:** the salience ladder, a two-cue selected state, and
  a desktop sidebar that ships open. It points to `drill-down-navigation.md` for navigation
  structure.
- **Review and planning agents learn drill-down:**
  - `design-critique` step 9, *Navigation Structure (drill-down)*, scores each role on the area
    budget, an areas-only global sidebar, section nav in the area layout, location cues,
    breadcrumbs from level 3 built from `ancestors`, search as the second way, and no hidden
    desktop navigation. The report gains a Navigation Structure table; the protocol is 9 steps in
    both agent and skill.
  - `requirements-consultant` Phase 3 asks information-architecture questions (areas per role, depth
    per area, landing per role, search scope, existing navigation to migrate) and the per-project
    drill-down API decisions (fixed or user-defined depth, badge freshness, totals vs load more,
    restricted ancestors, not found vs request access, readable URLs, live levels). The output gains
    a Navigation Map. It still has seven phases.
  - `code-reviewer` checks drill-down APIs (nesting deeper than one level, unscoped parent or member
    lookups, `ancestors` loaded one parent at a time, counts outside the caller's scope, ETags
    without `permissions_version`), navigation (sections in the global sidebar, bare `startsWith`
    active matching, hardcoded `navItems`, feature gates answering `notFound()`, breadcrumbs built
    from history), and chart libraries outside the per-stack split. The review checklist gains
    Navigation and Drill-down APIs sections, and the PR review guide gains "The count that leaked".
  - `design-system-architect` gains a navigation spec (area budget per role, an areas-only
    `AppSidebar`, one shared command-palette organism that is never the only route) and required
    NavLink, Breadcrumb, AppSidebar, SectionNav, and AreaLayout components. `/design-to-code` maps
    designed navigation to areas and levels.
  - `architecture-advisor` gains reference rows for drill-down resources, hierarchy storage, and
    drill-down navigation. The hierarchy-storage choice and each product's drill-down decisions are
    marked ADR-worthy, and navigation migration is a team-lead breakdown task.
- **A routed memory-router harness (`renderRoute`)** for per-role navigation tests, in
  `std-testing/references/react-components.md`, pointed to from `std-reactjs`, `/reactjs-dev`, and
  `test-generator`.
- **`/access-control-designer`** — a workflow skill (Opus) for application roles and permissions:
  - **Roles:** personas per tenant.
  - **The matrix:** `resource.action` keys as rows, roles as columns, scope cells
    `—` / `own` / `team` / `org` / `all`, deny by default.
  - **The role model:** code-defined vs DB-backed, recorded as an ADR through
    `architecture-advisor`.
  - **Enforcement and UI:** Pundit, the `/api/v1/me` contract, UI gates, and the per-role lens.
  - **Verification and grants:** matrix-driven checks, and grants that are guarded and audited.

  **It is delivered as a description-loaded skill:** no `paths:`, no hooks, no gates, and nothing to
  copy. Its description draws the boundary itself: application authorization only, not Claude Code
  permission settings, and not which skills or agents Claude may use.
- **Four reference files for access control**, loaded on demand from where the work happens:
  - `access-control-designer/references/permission-matrix.md` covers:
    - vocabulary, and a sample five-role B2B matrix with an Entitlement column
    - the single source-of-truth file, plus the spec that keeps the documented table in sync
      with it
    - static vs DB-backed roles, roles on the membership, separation of duties, and grant rules
    - DRF `BasePermission` + `get_queryset`, and a FastAPI `require_permission` dependency

    **Reached from** the skill, `security-auditor` (skill, checklist, and agent),
    `architecture-advisor`, `code-reviewer`, `std-django`, and `std-fastapi`.
  - `access-control-designer/references/ui-gates.md` covers:
    - the `/me` contract: `permissions: { version, rules }` plus entitlements, inside `{ data }`
    - scope → CASL conditions, and per-record `actions` carrying a `reasonCode`
    - `ability.ts` on `@casl/react@^7` with `@casl/ability@^7`. The house `AbilityProvider` wraps
      CASL's `<AbilityProvider value>` and exports `useAppAbility()` and a typed `Can`.
      `useAbility()` throws outside a provider, so component tests wrap gated leaves in one, and
      the Vite `AppLayout` provides the ability while a child `AppShell` reads it
    - the shared nav interface: `NAV: Area[]` with `sections`, `match` prefixes and an optional
      `group` label key. `visibleNav` filters sections and derives each area's landing, and
      `areaState(pathname, item)` matches whole path segments. React Native tabs are built from
      `visibleNav`, and Phlex nav molecules take `href:`, `label:` and `current:`
    - gates per stack: Vite SPA loaders, the Next.js layout (plain rules to Client Components),
      React Native navigators, and Phlex props. A feature reached by URL without its grant renders
      the no-access page: a Next.js page never calls `notFound()` for it, and the Vite
      `requirePermission` never silently redirects. Records outside scope still render not found
    - breadcrumbs from permission-filtered `ancestors`, scoped counts, and deep links
    - switching organization, realtime invalidation, and per-role UI tests that check navigation
      structure against a reviewed area budget

    **Reached from** `std-reactjs`, `std-nextjs`, `std-react-native`, `std-api-design`,
    `reactjs-dev`, `nextjs-dev`, `react-native-dev`, `ui-ux-patterns`, `atomic-design`'s organism
    rule, and the `nextjs-developer`, `code-reviewer`, and `architecture-advisor` agents.
  - `std-rails-conventions/references/roles-and-permissions.md` covers Pundit in Ruby:
    - `PermissionCatalog` / `PermissionMatrix`, and `pundit_user` tenancy
    - `permitted?(key)`, and `Scope#resolve` by scope level
    - a headless `NavigationPolicy` for Phlex
    - `RoleAssignmentPolicy`: a grant must fit within the granter's own permissions, no
      self-grant, a last-owner guard under a lock, and the audit event in the same transaction
    - the `/me` CASL rules generator, the DB-backed variant, and matrix-driven policy specs
    - a pointer to `ui-ux-patterns`' `role-based-ux-states.md` for how each UI state looks

    **Reached from** `std-rails-conventions`, `rails-architect`, `std-phlex-conventions`,
    `phlex-dev`, and the `security-auditor`, `code-reviewer`, and `phlex-developer` agents.
  - `ui-ux-patterns/references/role-based-ux.md` asks, per role: *"As a <Role>, what should I see,
    and how should I see it?"* It covers:
    - persona cards, walkthrough tables, and a worked five-role example
    - landing pages, sidebars, and dashboards per role
    - the multi-role union, and heuristics run once per role (field masking, denied vs empty, and
      admin "view as" now live in the two references added below)

    **It is the canonical home of the three-state rule** (see *Changed*). **Reached from**
    `ui-ux-patterns`, `std-accessibility`, `nextjs-dev`, `design-critique` (skill and agent), and
    the `nextjs-developer` and `phlex-developer` agents.
- **`nextjs-developer` agent** (Sonnet; Read, Grep, Glob, Bash, Write, Edit, WebFetch) — builds App
  Router UI from shadcn/ui components and blocks on house tokens:
  - **Standards preloaded:** frontmatter `skills:` preloads `sdh:std-shadcn-ui` and `sdh:std-nextjs`.
  - **Base-aware:** it reads the base from `components.json`. Primitives are installed
    **unmodified**; only raw palette classes, `/50` focus rings under 3:1, and CSS variables the CLI
    appends need attention.
  - **Components:** reuse before `add`; never `--overwrite`; ask when `components.json` is
    missing; never `npx shadcn mcp init`. Its building blocks are `Field` forms, toasts through
    `useNotify()` from `@/lib/notify`, shadcn `chart` (Recharts) charts, `next-themes`, and one
    Toaster, with pointer targets at the house web minimum of 32×32.
  - **Permissions:** gated with CASL built from `/me` on the server, with plain rules passed to
    Client Components and `AbilityProvider` imported from `@/components/providers/AbilityProvider`.
    A failed action's error key is translated with `t()` before it renders.
  - **Structure:** a 12-step protocol. Step 2 places each route in the drill-down model (area,
    level, URL, location cues, Up/Back, focus) and counts migrating an existing nested sidebar as in
    scope; the project shape uses `(app)/(orders)/`, and the layout template renders areas only.
    Screens sit on the atomic ladder.
  - **Role-based UX:** steps 1 and 9 and the reference table point at `role-based-ux-states.md`
    (empty by cause, the no-access page, masked values) and, for admin screens that grant access,
    `role-management-ux.md`.

  **`/nextjs-dev` now routes to it** (`agent: nextjs-developer`, `context: fork`), the same shape as
  `/phlex-dev` → `phlex-developer`. Bundled agents: 13 → 14.
- **Library Preferences** (`CLAUDE.md`, `README.md`, `sdh-engineering-standards`):
  - **UI gates:** `@casl/ability` + `@casl/react`, both on major 7, for Vite SPA, Next.js, and React
    Native.
    - The rules come from the Rails `/me` payload.
    - CASL is UX only; Pundit decides.
    - `/me` lives in TanStack Query under `['me']`, never in Zustand.
    - Condition keys must be camelCase, or they silently evaluate false.
  - **Web UI:** `shadcn/ui` for Next.js and the Vite SPA (see *Changed*).

  Rails authorization stays `pundit`.
- **Two `std-database` references:**
  - `relationships.md`, each relationship in code:
    - one-to-one: foreign key on the dependent side, plus a unique index
    - one-to-many: `dependent:` vs `on_delete` at scale
    - many-to-many: `has_many :through`, worked as users ↔ organizations memberships carrying
      the role
    - polymorphic: composite index and orphan risk, with the alternatives (separate nullable
      foreign keys plus a `CHECK`, or `delegated_type`)
    - self-referential: trees and graphs
    - `inverse_of` / `counter_cache` / `touch` / `strict_loading`, and the Django / SQLAlchemy
      mapping
  - `design-and-query-plan.md`, the plan to fill in before a migration:
    - entities and the relationship map
    - top queries, each with frequency and a latency budget
    - the index plan: btree, partial, covering, GIN, GiST, HNSW
    - constraints, and volume and growth
    - migration steps with lock level and expand/contract phase, including a composite tenant key
      added safely: a concurrent unique index on `(id, organization_id)`, the composite foreign key
      `NOT VALID` with `on_delete: :cascade`, then `validate_foreign_key` by name
    - backfill and rollback
    - `EXPLAIN (ANALYZE, BUFFERS)` before and after, and the bottleneck checklist

  Both are **reached from** the `std-database` body, `db-migration`, `rails-architect`,
  `std-rails-conventions`, `std-django`, `std-fastapi`, `performance-profiler`,
  `std-python-performance`, and the `requirements-consultant`, `code-reviewer`, and
  `architecture-advisor` agents.
- **`db-migration/references/migration-guide-python.md`** — Django and Alembic:
  - `lock_timeout` set on the migrating connection, and `transaction_per_migration=True` in the
    house Alembic `env.py`, so the revisions of one `alembic upgrade head` commit separately and a
    `NOT VALID` step's lock is not held through the `VALIDATE` scan
  - concurrent indexes: `AddIndexConcurrently` with `atomic = False`, or `postgresql_concurrently`
    inside `autocommit_block()`
  - a foreign key on a large table: `SeparateDatabaseAndState`, then `NOT VALID`, then `VALIDATE`
  - NOT NULL through `AddConstraintNotValid` / `ValidateConstraint`
  - `RunPython` with a reverse, and Celery backfills
  - an autogenerate review checklist

  `/db-migration`'s description now names Django migrations and Alembic.
- **`database-design-checker.py`** — an **advisory** PostToolUse checker that **never blocks**. It is
  a deterministic command hook, not an agent, dispatched in-process by `post-edit-dispatch.py`.
  - **Scope:** Rails migrations, `db/schema.rb`, `structure.sql`, `app/models`, Django migrations
    and models, `alembic/versions`, and any `.sql`, under any wrapper dir.
  - **Once per session**, on the first in-scope edit, a plan-first notice: (0) look up whether the
    concept already exists (the `orthogonality` skill's `arch_index.py --name <Entity>`), then
    relationships → query/index plan → constraints → migration plan → verify. Duplicate tables,
    copied columns, EAV and JSONB-as-column are `orthogonality-checker.py`'s.
  - **It warns on:**
    - `has_and_belongs_to_many`: use `has_many :through` a join model instead.
    - A Rails migration foreign-key column with no index leading on it: `add_column … :x_id`
      typed bigint/integer/uuid, or a reference with `index: false`. An index in a sibling
      migration counts.
    - A SQLAlchemy `ForeignKey` with no index: no `index=True`, unique, primary key, or leading
      `Index`.

  It leaves Django's `ForeignKey` alone, because Django indexes it. `test_database_design_checker`
  pins 22 cases.
- **`_hooklib.first_in_session(event, key)`** — the one once-per-session marker implementation.
  `notice_once` and `seen_this_session` now both call it, and both fail toward speaking.
- **`std-shadcn-ui`** — the 26th convention skill: shadcn/ui in Next.js and the Vite SPA.

  **Delivery tier: [Skill + `paths:`]** (`**/components.json`, `**/components/ui/**`), **plus a
  preload.** `nextjs-developer` names `sdh:std-shadcn-ui` and `sdh:std-nextjs` in frontmatter
  `skills:`, so both skill bodies are in that agent's context at startup, whatever file it touches.
  Their references are not preloaded. `mcp-install-gate` asks on `shadcn mcp init`; no hook enforces
  the skill's other CLI rules.

  The body covers:
  - **Reading `components.json`.** `style` gives the base (`base-*` → Base UI, `radix-*` / `new-york`
    / `default` → Radix, `aria-*` → React Aria). It also reads `rsc`, `aliases.ui`, `tailwind.css`,
    and `rtl`. When the file is missing, stop and ask.
  - **Writing the base's API.** Base UI's `render` vs Radix's `asChild`; never two bases in one
    package.
  - **CLI safety.** `shadcn docs|view|search`, `add --dry-run`, `add --diff`. Ask a human before
    `init` on an existing app, `apply`, `--overwrite`, `eject`, or `mcp init`. No shadcn MCP server
    by default.
  - **Ownership.** The copied code is yours. The only local edits allowed are label props, palette
    classes to tokens, focus-ring opacity, target size, and `BreadcrumbPage` as plain text with
    `aria-current="page"` instead of `role="link" aria-disabled`.
  - **House rules:**
    - label props filled from `t()`, `CommandDialog`'s title and description and `Breadcrumb`'s
      `aria-label` included
    - focus rings at full opacity unless measured ≥ 3:1, and pointer targets at the house web
      minimum of 32×32 (WCAG 2.5.8's floor is 24×24)
    - `tw-animate-css` only with the reduced-motion backstop
    - charts with a text alternative
    - `Field` forms. In the Vite SPA, a failure other than `VALIDATION_ERROR` goes to
      `setError('root', …)` with its `requestId`, and a `notify()` toast may add to it but never
      replace it
    - toasts per base behind `useNotify()` → `{ success(key, vars), error(key, vars) }`, which
      takes next-intl's `useTranslations` in Next.js and react-i18next in the Vite SPA
    - primitives as atoms
    - CASL-filtered navigation. Rules 12 and 13: the global `AppSidebar` lists areas only
      (`SidebarMenuSub`, collapsible groups and section trees are banned there), its active state
      comes from `areaState` and its group labels from `area.group`, and adopting a block strips
      nested `nav-main` / `sidebar-*` sub-items into area layouts
  - **MCP:** `shadcn mcp init` writes MCP configuration from inside the CLI, and `mcp-install-gate`
    asks on it; a human adds servers through `/mcp-advisor`.
  - **Checked upstream:** `shadcn docs -b` takes `base`, `radix` or `aria`. Base UI's
    `focusableWhenDisabled` renders `aria-disabled` with no `disabled` attribute, and Base UI
    Checkbox's `indeterminate` renders `aria-checked="mixed"`. The TanStack Table v9 imports match
    its migration, features and sorting guides.

  It ships five references: `cli-and-registry.md`, `components-and-blocks.md`,
  `forms-and-feedback.md`, `accessibility-and-i18n.md`, and `charts.md` (*Chart references*). The
  border/input row in `accessibility-and-i18n.md` records the house `--input` and `--border` at
  ≥ 3:1 on background and card, and the field on a tinted surface that still needs its own fill.
  The SessionStart area line now names the
  skill for `nextjs` and `vite` areas. Its `**/components/ui/**` glob also matches React Native and
  Phlex `components/ui` directories. The body says that a `components/ui` with no `components.json`
  above it is not shadcn.
- **Two role-based UX references with cited sources** (`ui-ux-patterns`):
  - `role-based-ux-states.md` — every state a role can meet. It holds a decision table (control,
    route, field, data), copy for each state, and accessible disabled reasons, drawn from:
    - APG and MDN on `aria-disabled`
    - Primer's tooltip rule
    - WCAG 1.4.13, and WCAG 1.4.3's contrast exemption, which does not cover the reason text
  - `role-management-ux.md` — the screens that grant access:
    - members and roles
    - diff before save, and the dangerous-grant confirmation
    - view-as and impersonation
    - API keys, and the audit log

    It closes with a map to `permission-matrix.md`'s grant rules.

  `role-based-ux.md` also covers:
  - **Navigation order:** Hick's law, and the house's reading of WCAG 3.2.3.
  - **Per-role dashboards, and progressive disclosure.**
  - **A reconciliation table** of where the house agrees with, and departs from, Carbon, Primer,
    Helios, GOV.UK, Fluent, Cloudscape, PatternFly, and SLDS.
  - **Permission keys:** the worked example uses plural `resource.action` keys (`orders.read`,
    `orders.refund`, `margins.read`, `billing.update`).

  **How sources are cited:**
  - Every inline citation matches the file's *Sources* list, and every source there was re-fetched
    and confirmed.
  - Refuted sources are not cited.
  - House positions with no source are written as house positions.
- **`hooks/_vendored.py`** — `is_vendored_ui(file_path)` answers one question: is this file a
  shadcn/ui primitive in the `components.json` `aliases.ui` directory?
  - **Resolution:** it resolves the alias the way the build does: tsconfig / jsconfig `paths` with one
    `extends` hop, then `package.json` `imports`, then `@/` as `src/`, then a bare relative alias.
  - **Safety:** it never raises, and it refuses an alias that would exempt house components: one
    that resolves to the package root or its `src/`, equals `aliases.components`, or holds
    `molecules/`, `organisms/` or `templates/`.
  - **Callers:** six frontend checkers, `auto-format.py`, and `teammate-idle-checker.py` (see
    *Changed*).
- **Trigger-precision matrix** (`hooks/tests/run-all.py`). For each hook, crafted events that must
  **fire** sit beside the nearest correct work, which must stay **quiet**:
  - a commit body mentioning `DROP TABLE`
  - a `feature/…-main-nav` branch
  - `.env.example`
  - a stock shadcn primitive

  A precision fix can no longer silently cost recall, and a new rule can no longer silently start
  firing on correct work.
- **Hook tests:** new doc-drift tests (the `hooks/README.md` formatter commands and advisory-checker
  order match the code; `CLAUDE.md` Hooks names every `hooks.json` script under its event). Also
  new: an agent `sdh:<skill>` preload check, an in-process no-raise check for fail-open gates,
  `std-shadcn-ui` path scoping, contrast gates for card/accent pairs, the 3:1 focus ring and alias
  equality, a token-utility parser that reads multi-segment and digit names and variant-map class
  lists with no `class=` beside them, and harness matcher semantics per the hooks reference.
- **Hook tests for this release's floor, tokens, MCP routing, and stack text:**
  - **Boundary contrast:** a gate fails when `--border` or `--input` measures below 3:1 against
    `--background` or `--card` in any of the 8 token blocks in `design-tokens.md` and
    `theme-presets.md`.
  - **The two new floor denies:** the SessionStart sentinel reports a floor copied before them as
    STALE and names both, a probe confirms the managed template carries both, and one parity row per
    terraform/tofu floor rule proves `terraform-command-gate` denies the same command.
  - **MCP routing:** filesystem and plugin-scoped file writers reach both PreToolUse gates; Gmail
    `create_draft`, Notion update-page, memory `create_entities`, and Drive `create_file` start no
    gate. A parity probe fails when `hooks.json`, `_hooklib`, `security-scan`, and
    `mcp-install-gate` disagree on the list.
  - **Subagent stack text:** each chart library must be named in a clause with its own stack and no
    other web stack.
- **`_hooklib` helpers:** `load_event_strict()`, `match_path()`, `project_root()` / `rel_to_root()`,
  `redact()`, `audit_dir()` / `append_audit()`, `formatter_marker()`, and `emit(…, system_message=)`.
  `MCP_FILE_WRITE_MATCHER` and `is_mcp_file_write(name)` hold the one list of MCP file-writing tools
  that `hooks.json`, `security-scan`, and `mcp-install-gate` share, GitHub `push_files` included, and
  `get_file_entries()` reads its `files[]` (whose content `get_content()` also joins). `SHELL_TOOLS`,
  `is_shell_tool()`, `shell_command()` and `shell_dialect()` let a gate treat Bash, PowerShell and
  Monitor alike. Every existing public signature is unchanged.
- **Internal hook modules:** `_jsx.py` (the one JSX tag/token scanner), `_teamgate.py` (lock-free git
  and team-gate helpers, no longer loaded from `task-completed-checker.py`), `_testpaths.py`,
  `_shellcore.py` (the POSIX lexer), `_shellpwsh.py` (the PowerShell lexer), `_dangerpwsh.py`
  (PowerShell's destructive forms), and `_protected.py` (the protected-file and provider-key tables
  `security-scan` reads, and `shell_write_verdict`, which `dangerous-command-blocker` applies to
  shell writes). `_shell.shell_segments`, `command_pipelines` and `executed_segments`, and
  `_gitpush.git_calls`, take an optional dialect.
  `_hooklib.py` is split into `_hookpaths.py` (path matching, framework detection) and
  `_hookaudit.py` (audit trail) and re-exports every name, so hook code is unchanged.
- **`SDH_HOOK_MAX_WARNINGS`** sets how many lines of advisory hook output the model gets per edit
  (default 20; `0` shows everything).
- **Orthogonality · the `orthogonality` skill** [Skill, no `paths:`]. It loads from its description
  whenever someone adds a model, table, column, library, client wrapper, error handler or
  cross-module import, or a hook reports an ORTHOGONALITY finding.
  - **Policy:** one concept → one owner; one concern → one mechanism per deployable; dependencies
    follow the declared context map.
  - **Detector catalog:** DK1–DK6, CM1–CM5, BC1–BC4, MF1–MF5, TF1–TF3, and CFG-*.
  - **Declarations:** `.claude/orthogonality.json`, with inline `sdh:orthogonal-ok <ID> <reason>`
    markers.
  - **Scans through the plugin launcher:** `arch_index.py --name` before adding a concept,
    `check_mechanisms.py`, and `arch_scan.py`.
  - **Seven references:** detectors, database-duplication, competing-mechanisms, context-maps,
    declaring-intent, scans-and-tools, adoption.
  - **Every fix routes to its existing owner** (`std-database`, `std-api-design`,
    `std-clean-architecture`, `monorepo-architect`, `db-migration`, `std-code-standards`) instead of
    restating it.
- **Orthogonality · `orthogonality-checker.py`** [Hook: advisory PostToolUse checker]: the 15th
  dispatched checker, and it runs last.
  - **What it reads:** the architecture index, read-only, and only the edited file.
  - **What it reports:** within 1.5 s, at most 3 `ORTHOGONALITY [<ID> <slug>]` lines, only for
    findings new since the baseline: DK1–DK4, CM1–CM4, BC1–BC3, MF3 and MF5. Each line gives both
    locations, the measured signal, the owner skill and the `orthogonality` skill.
  - **Where it stays quiet:** a cycle between inferred contexts warns only between sibling folders,
    and a single library off the house list is silent here (`info` in scans).
  - **Without an index:** it checks DK4, MF3, MF5 and CM1 on the file alone, and says once per
    session that the index is not built, or that a first build is still running. A session outside
    a project (the home directory, a filesystem root, a folder with no `.git` or package manifest)
    builds no index and is told so once.
  - **Large files:** a file over the index's 1 MB per-file cap is never re-parsed; an over-cap
    schema, migration or manifest is checked from its stored index rows within the budget.
  - **Keeping a finding:** every line says how, as `Keep: sdh:orthogonal-ok <ID> <reason>, or <config key> with an ADR.`
    A `package.json` subject names only the config key.
  - **Scan-only:** cross-file clones (DK6) and Terraform.
- **Orthogonality · `orthogonality-index.py`** [Hook: SessionStart async], matcher
  `startup|resume|fork`, `async: true`.
  - **What it does:** refreshes the project's architecture index incrementally in the background,
    seeds a linked worktree from the main checkout, and stamps the findings baseline once the index
    is complete, inside the same budget, for the detectors that finished.
  - **Output:** none. A failure is recorded in the index and reported once per session by the
    checker.
- **Orthogonality · `orthogonality-watch.py`** [Hook: PostToolUse and PostToolUseFailure asyncRewake],
  on `Edit|Write|MultiEdit|Bash|PowerShell` and the MCP file writers, and on a failed `Bash` or
  `PowerShell` call (one the user interrupted wakes nobody). It catches what the edit checkers never
  see: package installs, generators and `git pull`, also through `bundle exec`, `uv run`,
  `poetry run`, `pipenv run`, `pdm run`, `python -m`, `docker compose run|exec` and `./manage.py`.
  - **What it does:** updates the index for the changed paths, and wakes Claude with at most 5 lines,
    only for findings not yet shown in the session. When another refresh holds the index lock, it
    waits up to 15 s, then checks against the index as it stands and keeps those files out of the
    first baseline.
  - **When it stays quiet:** irrelevant commands exit before the engine loads, and a crash exits
    silently and is recorded.
- **Orthogonality · the shared engine** (`hooks/_arch*.py`, 32 standard-library modules). The
  orthogonality hooks and the skill's scripts both import it; no detector code lives under
  `skills/`.
  - **Parses:** Rails schema, migrations and models; Django; SQLAlchemy and Alembic; SQL DDL; Ruby,
    Python and TS/JS code facts; Terraform; and manifests.
  - **Resolves bounded contexts:** from packwerk, import-linter, tach, Nx tags or
    `.claude/orthogonality.json`, and infers them otherwise.
  - **Implements detectors:** DK1–DK4, DK6, CM1–CM5, BC1–BC4, MF1–MF3, MF5, FC1 and TF1–TF2. DK5, MF4
    and TF3 are catalogued but not implemented yet; scans list them as not run.
  - **Stays fast:** MF2 and CM2–CM4 group their sites once; `--paths` and `--changed-since` start
    MF2, CM2–CM4 and DK6 only from in-scope sites and files; `--budget` bounds detector loops and the
    `--changed-since` base pass; DK3 builds its per-deployable table map once; DK6 keeps compact
    token arrays, reads one file at a time and skips files over 1 MB.
  - **Reads precisely:** client-factory targets are normalized to lowercase `host[:port]`, so URL
    credentials never reach the index, a hook line or a report. MF5 ignores Django lookups through
    relations and plain columns. Rails contexts are inferred from `app/models/<namespace>/` only,
    Python layer folders are not contexts, and nested Ruby modules resolve to `Api::V1::X`. DK4
    ignores percentile columns and gapped numbering.
- **Orthogonality · `hooks/_mechanisms.json`**, the competing-mechanism registry.
  - **Scope:** only concerns with a stated house choice.
  - **Charts, per stack:** Next.js uses Recharts through the shadcn/ui chart component, the Vite SPA
    uses `chart.js` with `react-chartjs-2`, and Rails views use `chart.js` through Stimulus.
    ApexCharts and `react-apexcharts` appear only as competitors.
  - **Schema consistency:** `database_consistency` is the house Rails schema-consistency tool.
- **Orthogonality · the skill's scripts** (`skills/orthogonality/scripts/`): `arch_index.py`,
  `find_duplicates.py`, `check_boundaries.py`, `check_mechanisms.py`, `run_community_tools.py` and
  `arch_scan.py`, thin wrappers over the shared engine.
  - **Output:** JSON follows `sdh.orthogonality/v1`, and the formats are json, markdown, brief and
    sarif-lite.
  - **Exit codes:** 0 clean, 1 a finding at or above `--fail-on`, 2 usage or configuration error, 3
    internal error.
  - **CI from a fresh cache:** `--changed-since REF --new-only --fail-on warn` judges newness against
    the base ref.
- **Orthogonality · the architecture index**, cached under
  `${CLAUDE_PLUGIN_DATA}/orthogonality/<project key>/`. The key includes the parser generation
  (`-v<SCHEMA_VERSION>`), so two plugin versions never rewrite each other's index.
  - **Fallbacks:** a temp directory when `CLAUDE_PLUGIN_DATA` is unset, and an
    `SDH_ORTHOGONALITY_DIR` override.
  - **Freshness:** it refreshes incrementally, and keeps a separate key per worktree, seeded from the
    main checkout.
  - **Storage:** without `sqlite3`, it falls back to a JSON store.
  - **Failures stay readable:** a watcher or SessionStart failure recorded before the first refresh
    still reaches the checker's once-per-session note, and a successful full refresh or `--rebuild`
    clears it.
  - **One writer:** a lock whose holder process has exited, or whose pid was reused, is broken at
    once; a live holder refreshes the lock at every batch; a killed pass resumes from the files it
    committed. During a build, `arch_index.py` reports that a refresh is in progress and exits 0 (1
    with `--require-complete`).
  - **Scope:** no index for a session outside a project; a walk without git skips `site-packages`,
    `AppData`, `Library` and dot directories.
  - **Lifetime:** a rebuildable cache, removed with the plugin.
- **Orthogonality · what it writes, runs and installs.**
  - **Writes:** nothing into a project, except `.claude/orthogonality/last-scan.json` (in a
    directory that gitignores itself), and only when a scan runs with `--write-report`.
  - **Installs:** no community tool, ever.
  - **Runs:** database-connected tools only with `--with-db`, and installed tools in the watcher only
    with `SDH_ORTHOGONALITY_TOOLS=1`. `SDH_ORTHOGONALITY_CLONES=0` skips DK6 clone detection.
  - **Permission floor:** unchanged.
- **Orthogonality · an architectural fitness-function CI job** in
  `skills/orthogonality/references/scans-and-tools.md`.
  - **How it gates:** it stamps the baseline on the base commit, then fails only on new warnings in
    changed files (`--changed-since origin/<base> --new-only --fail-on warn`).
  - **Adoption:** a staged path moves it from report-only to failing to strict.
  - **Community tools** (packwerk or pks, import-linter, tach, dependency-cruiser, jscpd, squawk)
    run only when already installed, and are never installed.
  - **Database-connected tools** (`database_consistency`, Django checks, `alembic check`) run only
    with `--with-db`, and only when the user asks.
- **`hooks/_hooktools.py`** — project-local tool resolution (`node_modules/.bin`, `.venv`,
  `bundle exec`, `bin/` binstubs) with the cmd-shim argument safety check. It never launches `npx`,
  `pnpm dlx`, `yarn dlx`, `bunx`, `uvx`, `uv run` or `pipx run`.
- **Hook tests for orthogonality** (`hooks/tests/run-all.py`):
  - **81 trigger-matrix rows** through the real registrations:
    - `orthogonality-checker`: 24 fire / 25 quiet, across Rails, packwerk, Django, FastAPI, Vite,
      Next.js, React Native and Terraform;
    - `orthogonality-watch`: 3 fire / 12 quiet, judged on exit 2 plus stderr;
    - `orthogonality-index`: 2 fire / 4 quiet;
    - the dispatcher: 1 row;
    - 10 `hooks.json` selection rows.
  - **12 test functions:**
    - parsers, normalization and graph;
    - the mechanism registry against the standards;
    - the six scripts' exit codes and reports;
    - the JSON, flag and detector contract against the skill's docs;
    - never-installs PATH shims;
    - store concurrency and the no-`sqlite3` JSON fallback;
    - performance guards for index build and per-edit lookup;
    - thin scripts, and references that cite their owners;
    - the Python 3.6 grammar with standard-library-only imports.
  - **`test_fail_open_is_not_silent`** now covers all three orthogonality hooks.
- **CI · `hook-fixtures-windows`** (windows-latest, Python 3.12, LF checkout) runs
  `bash hooks/run-python.sh hooks/tests/run-all.py --only orthogonality`. The harness gains
  `--only <prefix>` to run tagged tests and matrix rows.

### Changed

- **Permission floor (ACTION REQUIRED) · two new Bash denies, and a PowerShell mirror for every
  shell deny.** `.claude/settings.json` now holds 48 reference denies, and
  `.claude/managed-settings.template.json` holds 43.
  - **`apply -destroy`.** The floor adds `Bash(terraform apply -destroy:*)` and
    `Bash(tofu apply -destroy:*)` beside the existing destroy rules. `terraform apply -destroy` is
    Terraform's own spelling of a full destroy, and the floor did not deny it.
    `terraform-command-gate` denies it too, including the `-chdir=…` and `-target=… -destroy` forms
    a prefix rule cannot catch (*Hook decisions*).
  - **PowerShell mirrors.** A `Bash(...)` rule never matches the PowerShell tool, which is on by
    default on Windows. Both floors now carry `PowerShell(...)` forms of the `sudo`, `chmod 777`,
    Terraform and OpenTofu `destroy`, `apply -destroy`, `state rm|mv|push` and `force-unlock` rules.
    The `rm -rf /` rules become five `Remove-Item` rules on the `/` and `C:/` roots, with no
    backslash in any rule. The `curl … | bash` and `wget … | bash` rules become
    `PowerShell(Invoke-Expression:*)`: Claude Code checks each stage of a PowerShell pipeline on its
    own, so the rule denies `iex` itself. The managed template also mirrors `nc` and `ncat`. The rule
    shape follows the permissions docs: `:*` equals a trailing ` *`, and a cmdlet rule also matches
    its aliases, case-insensitively. Monitor needs no mirror, because it runs its commands under the
    Bash rules.
  - **CI.** `managed-floor-sync` takes its required list from `session-start-check`'s
    `managed_tier()`, the definition the sentinel uses, and fails when a Bash deny in either file
    lacks its PowerShell mirror.

  Copy them by hand (*Upgrade steps* 1); until you do, the SessionStart sentinel reports the floor as
  STALE.
- **UI agents and skills place every screen in the drill-down model:**
  - `/nextjs-dev` gains steps and checklist items that place each route in the drill-down model
    (the `nextjs-developer` agent is under *Added*).
  - `phlex-developer` is now a 10-Step Protocol. New step 2 places every view (area, level, route,
    location cues, `advance`, an areas-only sidebar, a command palette that is never the only route,
    existing screens included), with chart guidance, new reference rows, and checklist items.
    `std-phlex-conventions` and `/phlex-dev` cover drill-down navigation and Chart.js charts, and a
    Phlex page receives its location (visible areas, breadcrumb items) from the controller, never
    from `request.path` or history.
  - `react-native-dev` asks which area (tab) and drill level a screen belongs to and what its
    linking path is, keys queries per drill level, and routes navigation work to
    `std-react-native/references/navigation.md`. `react-native-best-practices` points navigation
    structure there too.
- **Phlex `NavLink` takes `current:`** (`"page"` / `"true"` / nil) instead of a boolean `active:`. The
  `/phlex-dev` Header, DashboardLayout, and Articles examples replace hardcoded nav link arrays and
  the history-style "Back" link with controller-built `areas:` and `crumbs:`, and the Header now
  requires `search_action:`.
- **`std-reactjs/references/animation.md` keys page transitions inside the area,** so the section nav
  does not re-mount (house choice).
- **Vite SPA vendor chunks move to Vite 8's `build.rolldownOptions.output.codeSplitting.groups`**
  in `std-reactjs/references/routing-and-code-split.md`, which showed a `manualChunks` object form
  that fails a Vite 8 build. `vendor-query` is narrowed to `@tanstack/react-query` and
  `@tanstack/query-core`, so table or virtual libraries don't join a preloaded chunk, and a Vite 7
  note keeps `manualChunks` (*Upgrade steps* 3).
- **`std-nextjs` documents Next.js 16 beside 15.** A server action whose user must see their own
  write calls `updateTag`. A Route Handler, such as the Rails revalidation webhook, calls
  `revalidateTag(tag, { expire: 0 })`, and `revalidateTag(tag, 'max')` is for data that may be
  served stale while it refreshes. The webhook handler no longer passes `revalidateTag` by
  reference, which on 16 would hand it the array index as its profile. On 16, `middleware.ts` is
  renamed `proxy.ts` and runs on Node.js only; the examples keep 15's names, with a note per major.
- **`std-nextjs` [Skill + `paths:`]** also loads on `**/proxy.ts`.
- **`std-phlex-conventions` [Skill + `paths:`]** also loads for
  `**/app/javascript/controllers/chart_controller.js`,
  `**/app/javascript/controllers/disclosure_controller.js` and `**/app/javascript/charts/**`, so
  editing the house chart or disclosure controller delivers its CSP, teardown, token and
  reduced-motion rules. Other Stimulus controllers are unaffected.
- **Drill-down-ready APIs · shallow nesting replaces "maximum 3 levels of nesting".** In
  `std-api-design`, collection routes nest one level under one canonical parent, member routes are
  flat by ID, and a record outside the caller's scope answers 404, not 403. `api-designer` gains a
  drill-down levels step, a level table, and a level-map output.
- **Drill-down and tree-storage pointers:**
  - `std-rails-conventions`: shallow routes, parent scope-then-find, detail serializers carrying
    `ancestors`, list-cache keys that include the viewer's scope, conditional GET, and
    `permissions_version` in the ETag.
  - `std-fastapi`: one router per level. `std-django`: nested routers, a parent-authorizing
    `get_queryset`, and trees.
  - `std-python-performance`: per-level N+1, scoped grouped counts, and unique cursor ordering.
    `performance-profiler`: drill-down level profiling.
  - `rails-architect`, `python-dev`, `db-migration`, and `std-database`'s relationships reference (a
    counter cache is valid only at `org` scope) and design-and-query-plan reference (scoped counts,
    tree walks).
- **Theming contrast tables** gain rows for `border-border`, for `border-input` on background and card,
  and for fields on tinted panels (2.92 / 2.40:1, below 3:1: give the field its own `bg-background`
  fill and a visible label), plus a per-preset boundary row in `theme-presets.md`.
- **`subagent-context` · the stack every subagent receives** names the chart library per stack
  (Next.js: Recharts through the shadcn/ui chart component; Vite SPA: Chart.js through
  `react-chartjs-2`; Rails Phlex views: Chart.js through a house Stimulus controller). It also
  describes drill-down navigation (an areas-only global sidebar or tab bar, section nav in area
  layouts, breadcrumbs from `ancestors`, list state in the URL, an optional command palette that is
  never the only way in) and drill-down-ready APIs.
- **The three-state rule replaces "disable unavailable actions".** `ui-ux-patterns` (heuristic 5
  and the Disabled interaction state) and `heuristic-evaluation.md` gave one outcome, a disabled
  control with a tooltip, for three different reasons. The rule is now:

  | The action is… | It is shown… |
  |---|---|
  | Not permitted | **Not rendered** |
  | Permitted, but blocked by the record's state | **Disabled, with a visible reason** (never tooltip-only) |
  | Available on another plan | **Visible and locked**, only for roles that could act on it |

  It resolves permission → entitlement → record state, and the UI checks permission keys, never
  role names. In a multi-role product, heuristic evaluation runs once per role and is never
  averaged across roles.
- **`rails-patterns.md`'s Pundit example checks permission keys.** `OrderPolicy` was
  `owner? || admin?` over `user.admin?`, with an `if user.admin?` scope. It is now
  `permitted?("orders.read" | "orders.update" | "orders.cancel")`, with record state (`pending?`,
  `shipped?`) checked alongside, and `Scope#resolve` is `scope_for("orders.read")`.
  `std-security`'s TypeScript example also drops `currentUser.isAdmin` for a permission check that
  returns 404, matching the same file's "prefer 404 over 403". It gains a "check permissions, never
  role names" rule.
- **ARIA for gated controls** — `std-accessibility` gains a *Not permitted, blocked, locked*
  subsection:
  - **Not permitted:** absent from the DOM. Never hidden with `hidden`, `sr-only`, or
    `aria-hidden`.
  - **Blocked by record state:** `aria-disabled="true"`, with `aria-describedby` pointing at a
    visible reason. Not native `disabled`, which drops the control from the tab order.
  - **Locked:** stays focusable and announces what unlocks it.
  - **The rule behind them:** APG focusability for `aria-disabled`, a handler guard that covers
    Enter-to-submit, no tooltip on a natively disabled control, WCAG 1.4.13, and WCAG 1.4.3's
    contrast exemption not covering the reason text.
- **Six agents learned the model:**
  - `security-auditor`: a role check is not a permission check; `permit(:role)` is CRITICAL; the
    grant action's guards; `/me` returns only the caller's rules.
  - `code-reviewer`: permission keys in policies and gates, and `/me` in TanStack Query. It also
    flags `has_and_belongs_to_many`, an unindexed foreign key, and a new table with no query plan.
  - `architecture-advisor`: CASL is pinned, so it never proposes a spike for it; the role-model
    choice is ADR-worthy.
  - `requirements-consultant`: authorization sub-questions, the role lens, and a
    *Permission Matrix (draft)* output block. It still has seven phases. Its stack table covers
    every house layer (Rails, Python, the Vite SPA, Next.js, shadcn/ui, CASL, and the chart library
    per stack), and Phase 5 sketches Python and web pieces too.
  - `phlex-developer`: gated items arrive as `can_*:` props; blocked controls use `aria-disabled`
    with a visible reason; its reference table lists `role-based-ux.md` and
    `role-based-ux-states.md`.
  - `design-critique`: a new step 8, Role Lens, in both the agent and the skill, pointing at
    `role-based-ux-states.md` and `role-management-ux.md`.
- **`std-database` description and `paths:`.** The description now covers ANY schema, model,
  association, migration, index, or query change, across Rails, Django, SQLAlchemy + Alembic, raw
  SQL, PostGIS, and pgvector. `paths:` changes:
  - dropped: `**/schemas/**` (Pydantic schemas are not the database)
  - widened: `**/db/**/*.rb` → `**/db/**`
  - added: `**/models.py`, `**/alembic/**`, `**/*.sql`

  This is the [Skill + `paths:`] tier, so expect the skill to be eligible on more files (FastAPI
  `app/db/`, Rails `db/schema.rb`).
- **`std-api-design` and `std-monitoring` now apply to the files their hooks warn on.**
  `std-api-design`'s `paths:` add Next.js route handlers (`**/app/**/route.ts|js`) and FastAPI
  `app/routers`/`app/api`. `std-monitoring`'s add the Python files `monitoring-checker` scans:
  `services/`, `tasks/` and `views/` packages, FastAPI `app/routers`/`app/api`, and Django
  `views.py`, `viewsets.py`, `services.py`, `tasks.py`.
- **Contradictions resolved in `std-database`:**
  - **Composite index order:** equality columns first, range and sort columns last. The old rule
    was "most selective first", which the query shape overrides.
  - **Index names:** the Rails default, `index_<table>_on_<columns>`. The old `idx_table_column`
    is a name `add_index` never generates. `chk_` stays for check constraints.
  - **Backfills:** the in-migration example is small-table only (`unscoped.in_batches`). A
    large-table backfill is a Sidekiq or Celery job, owned by `db-migration`.

  Ownership is now stated outright: `std-database` owns the design-time query and index plan,
  `db-migration` owns operation safety and rollout, and `performance-profiler` owns slow
  production queries.
- **Orthogonality pointers in existing skills and agents.** Each keeps its own concern and links to
  the `orthogonality` skill.
  - **`clean-architecture` skill:** injects the orthogonality boundary scan (BC1, BC2, BC3, MF1)
    through a `!` line, with a matching `allowed-tools` Bash rule. Its read-only agent reports those
    findings under a separate "Context coupling (orthogonality)" heading, falling back to
    `.claude/orthogonality/last-scan.json`, and still owns the layers inside a context.
  - **`code-reviewer` agent:** checks for duplicate concepts (DK findings), a second mechanism for a
    covered concern (CM1–CM4), and cross-context imports, writes and cycles (BC1–BC3), from scan
    output a caller passes in or `.claude/orthogonality/last-scan.json`. A PR adding a
    table must show the `arch_index.py --name` lookup, or the ADR plus its
    `.claude/orthogonality.json` declaration.
  - **`architecture-advisor` agent:** starts from orthogonality scan output when a caller passes it
    in or `.claude/orthogonality/last-scan.json` exists, and recommends a scan when it is absent. A second library for a covered concern is a competing
    mechanism, whose ADR names which library leaves and by when. Intentional duplicates are recorded
    as ADRs referenced from `.claude/orthogonality.json`.
  - **`refactor-specialist` agent and `refactor` skill:** measure duplication and coupling with the
    orthogonality scripts, and require a before/after scan of the touched paths that reports
    observed counts. Merging two tables routes to `db-migration`; a duplicate kept on purpose routes
    to an ADR.
  - **`std-database`, `std-clean-architecture` and `monorepo-architect` (skill and agent):** point to
    the `orthogonality` skill for duplicate tables and copied facts, context boundaries, and
    competing mechanisms. Layers, package boundaries, the one-version policy and relationship design
    stay with their current owners.
  - **`sdh-engineering-standards` and `CLAUDE.md`:**
    - An Orthogonality rule: one owner per concept, one mechanism per concern per deployable, an ADR
      for every kept exception.
    - A pointer to the skill.
    - The standards' Library preferences now name the registry's house packages by package name:
      `sidekiq`, `panko_serializer`, `phlex-rails`, `database_consistency`, `zustand`,
      `@tanstack/react-query`, `pyjwt`, `argon2-cffi` and `djangorestframework-simplejwt`.
- **README counts match disk:** 73 skills (46 workflow + 26 `std-*` + `sdh-engineering-standards`),
  14 agents, and 35 hook scripts, plus `run-python.sh`, `_mechanisms.json`, and 46 shared `_*.py`
  modules (32 of them the orthogonality engine).
  - Several count sites had drifted, to `58 skills: 37 workflow + 20 std-*`, `69 skills`, and
    `12 agents`.
  - The skills tree now lists all 46 workflow skills, and the install section names v4.0.0.
  - `hooks/README.md` and `docs/hook-development.md` now count 15 advisory checkers.
    `database-design-checker.py` and `orthogonality-checker.py` join the dispatcher in this release.
    The docs said 12 while the dispatcher ran 13.
- **Registration docs follow this release.**
  - **`CLAUDE.md`:**
    - Its Architecture section gains the Drill-down navigation, Drill-down-ready APIs and
      Orthogonality rules, with their canonical references.
    - Its stack, rule, agent and skill lines name the chart library per stack and React Router 8.
    - Its Skills list gains `/orthogonality`.
    - Its Hooks section names `orthogonality-index.py` under SessionStart and
      `orthogonality-watch.py` under PostToolUse, and describes `orthogonality-checker.py` with the
      dispatched checkers.
  - **`README.md`:**
    - The copyable deny block lists `Bash(rm -rf /)` and all 8 terraform/tofu denies, including both
      `apply -destroy` rules.
    - The Technology Stack chart row is split per stack.
    - The configuration table adds `SDH_ORTHOGONALITY`, `SDH_ORTHOGONALITY_TOOLS` and
      `SDH_ORTHOGONALITY_DIR`.
    - The hook tables and trees list the orthogonality hooks and modules.
  - **Hook docs:**
    - `CLAUDE.md`, `hooks/README.md` and `docs/hook-development.md` show the anchored MCP matchers
      exactly as `hooks.json` registers them, and document
      `_hooklib.MCP_FILE_WRITE_MATCHER` / `is_mcp_file_write(name)`.
    - `hooks/README.md` adds output-contract, fail-stance and exit-code rows for the `async`
      SessionStart and `asyncRewake` PostToolUse hooks. It also adds an *Orthogonality engine*
      section: modules, index location and fallback, budgets, fail-open behaviour, switches, and how
      to run the scans.
    - `docs/hook-development.md` adds *Background hooks*, which quotes the hooks reference on
      `async` and `asyncRewake`, and *The orthogonality engine*.
    - The launcher docs give exit 2's effect per event, say that an `ask` reason reaches only the
      user, and state that a gate past its timeout lets the tool run. The shell gates are documented
      on `Bash|PowerShell|Monitor`, beside the floor's PowerShell mirrors.
- **Hook tests:**
  - **Timeouts by handler kind:** `hooks.json` timeouts are checked by kind, synchronous 1–30 s and
    `async`/`asyncRewake` 1–180 s. The background set is pinned to `orthogonality-index.py` (async,
    `startup|resume|fork`) and `orthogonality-watch.py` (asyncRewake, on PostToolUse and
    PostToolUseFailure), and none of them may be fail-closed.
  - **asyncRewake rows:** the trigger matrix treats exit 2 from an `asyncRewake` hook as a fire.
  - **Hermetic environment:** it clears `SDH_ORTHOGONALITY`, `SDH_ORTHOGONALITY_DIR`,
    `SDH_ORTHOGONALITY_TOOLS` and `SDH_ORTHOGONALITY_CLONES`.
  - **Skill pointers:** hook messages are checked for every "the `x` skill" pointer, not only `std-*`
    names. Every `owner_skill` in `hooks/_mechanisms.json` and in the orthogonality finding catalog
    must be a real skill.
- **House standard · Charts, one library per stack. ApexCharts leaves the house over its licence.**
  Every chart ships a text alternative (a visible summary, or a data table outside the chart), and
  color is never the only signal.
  - **Next.js → the shadcn/ui `chart` component (Recharts),** per
    `std-shadcn-ui/references/charts.md`. `ChartContainer` has a height, `min-h-*`, or `aspect-*`;
    `ChartConfig` colors are `var(--chart-N)`, never `hsl(var(--chart-N))`; `ChartTooltip` and
    `ChartLegend` keep `accessibilityLayer` on. A Server Component renders the states, caption,
    summary and data table, and a `'use client'` leaf draws, with `isAnimationActive={!reduceMotion}`
    on every series. Tests assert the data mapping and the text alternative, never the SVG.
  - **Vite SPA → Chart.js 4.5.1 through `react-chartjs-2` 5.3.1** (both MIT).
    `std-reactjs/references/charts.md` is rewritten: one registration module (never
    `chart.js/auto`), chart modules lazy-loaded by file path, memoised `data`/`options` with labelled
    datasets, `updateMode="none"` for streams, colours read from the CSS tokens through
    `useChartTokens`, `animation: false` under reduced motion, a text alternative outside the canvas,
    React 19 StrictMode notes, and tests with `vitest-canvas-mock` plus a `ResizeObserver` stub.
  - **Rails Phlex views → Chart.js 4.5.1 through a house Stimulus controller,** per
    `std-phlex-conventions/references/charts.md`. Chartkick is rejected: its inline scripts and
    styles break a strict CSP, and it tears down only on `turbo:before-render`.

  **What changed in the plugin:**
  - `std-reactjs` and `/reactjs-dev` name Chart.js via `react-chartjs-2`. The order-status example is
    a Chart.js doughnut, the vendor chunk is `['chart.js', 'react-chartjs-2']`, and
    `std-reactjs/references/animation.md` switches Chart.js off under reduced motion with
    `animation: false`.
  - Every chart pointer in `std-shadcn-ui`, `std-nextjs`, `/nextjs-dev`, and `nextjs-developer`
    targets `std-shadcn-ui/references/charts.md`, and those surfaces state that the Vite SPA and
    Rails views chart with Chart.js. `nextjs-dev`'s `client-patterns.md` no longer duplicates the
    chart organism; it points at the standard and lists what a page adds.
  - Chart testing guidance in `std-testing`, `test-generator` (skill and agent), the
    `clean-architecture` agent, and `std-clean-architecture/references/reactjs-vite-mapping.md`
    covers Chart.js on a canvas: a canvas mock, `Chart.getChart`, and never draw calls or pixels.
    The SVG-and-Recharts rule applies to Next.js only.
  - `ui-ux-patterns/references/screen-patterns.md`, `CLAUDE.md`, `README.md`,
    `sdh-engineering-standards`, the web, Next.js and backend `docs/templates`, and the
    `subagent-context` stack text name the library per stack. `code-reviewer` reports any chart
    library outside the split.

  **What consumers do:** follow *Upgrade steps* 3. Entries for earlier versions below still name
  ApexCharts, because that is what they shipped.
- **House standard · shadcn/ui is the component standard for Next.js and the Vite SPA** (it was
  Next.js only):
  - **Base:** Base UI primitives for new packages (shadcn's default since 2026-07-02). Existing Radix
    packages (`style` `new-york`, `default`, or `radix-*`) stay on Radix, with no migration. Never two
    bases in one package.
  - **`cn`:** shadcn packages import it from `@/lib/utils`, which re-exports the `cn` package.
    Non-shadcn packages may keep `clsx` + `tailwind-merge`.
  - **Motion:** `tw-animate-css` for primitives only, under a mandatory global
    `prefers-reduced-motion` backstop. `framer-motion` stays for house page and list transitions.
  - **Forms:** `Field` + react-hook-form + zod, never `shadcn add form` (legacy). Next.js re-checks
    the same schema with `safeParse` in the server action, through `useActionState`.
  - **Toasts:** follow the base (Base UI → shadcn `Toast`, Radix → `sonner`), behind a house
    `notify()` that takes translation keys. Never used for field validation.
  - **Dark mode:**
    - **Next.js:** `next-themes` (`attribute="class"`, `defaultTheme="system"`, `enableSystem`,
      `disableTransitionOnChange`), with `suppressHydrationWarning` on `<html>`.
    - **Vite SPA:** the house theming provider, on the same `.dark` class.
  - **i18n:** label props (`closeLabel`, `toggleLabel`, …) filled from `t()`. RTL through
    `rtl: true` and `DirectionProvider`, set before the first `add`.

  These are **skill rules, not gates**: no hook stops `shadcn init`, `apply`, `add --overwrite`, or
  `eject`, and `mcp init` draws only `mcp-install-gate`'s ask. React Native keeps the house RN
  approach, because shadcn is web-only.
  Updated: `CLAUDE.md`, `README.md`, `sdh-engineering-standards`, `std-reactjs` (and its forms,
  animation, routing, and testing references), `reactjs-dev`, `nextjs-dev`, `std-nextjs`,
  `std-design-system`, `theming`, `brand-identity`, and the web and Next.js `docs/templates`.
- **Vendored shadcn/ui primitives in `std-i18n` and `std-accessibility`:** both skills now point at
  `std-shadcn-ui/references/accessibility-and-i18n.md`. That reference says the i18n hook skips
  files under `aliases.ui` and the accessibility hook keeps only two checks there, so label props,
  ring contrast and target size there rely on review.
- **`std-design-system` documents what `design-token-checker.py` enforces.** A role-rooted utility
  the registry lacks compiles to no CSS and warns; the 15 shadcn/ui aliases and tokens defined in
  the same file are accepted. It also lists the reduced-motion forms the checker accepts (`.tsx`,
  `.jsx`, `.css`, `.scss`) and describes the focus check on styled host controls (`.tsx`, `.jsx`),
  where bare `focus:` does not count.
- **`std-code-standards` states the shadcn/ui exemption and how destructured props count.**
  CLI-owned primitives in the `components.json` `aliases.ui` directory are exempt from the
  file-length, function-length, parameter and nesting checks and are never split. A destructured
  props object counts as one parameter. The limits are unchanged.
- **`std-testing` lists where tests may live.** Vendored shadcn/ui primitives need no test file;
  test what is built on them. The section also lists the pytest layouts `test-coverage-checker`
  accepts: `tests/<mirror>/`, `tests/unit/<mirror>/`, a mirror that keeps the package directory, a
  flat `tests/test_<name>.py`, and co-located tests. These are found from the nearest
  `pyproject.toml` (or `manage.py`, `setup.py`, `setup.cfg`), for `src/<pkg>` and FastAPI `app/`.
- **`nextjs-dev` examples:** server actions return `ActionResult` with translation keys, and
  `error.tsx` logs the digest instead of showing `error.message`.
- **Design tokens (consumers update their CSS) · shadcn's token names become aliases, and the
  Tailwind v4 wiring changes.**
  - **Aliases:**
    - `destructive` / `destructive-foreground` → the error role
    - `sidebar` / `sidebar-foreground` → card
    - `sidebar-primary` (+ `-foreground`) → primary
    - `sidebar-accent` (+ `-foreground`) → accent
    - `sidebar-border` → border, and `sidebar-ring` → ring
  - **Chart palette:** `chart-1`…`chart-5`, each measured at ≥ 4.5:1 on card in both modes and in
    every preset, and checked for color-vision deficiency. Only the first three stay distinct under
    deuteranopia, so scatter, bubble, and small-multiple charts cap at three series.
  - **Wiring:**
    - CSS variables hold complete `hsl()` values, registered with
      `@theme inline { --color-X: var(--X) }`, and dark mode is `@custom-variant dark (&:is(.dark *))`.
    - Arbitrary CSS uses `var(--X)`, never `hsl(var(--X))`.
    - The alias block sits on `:root, .dark`, so a nested `.dark` section re-resolves.
    - Focus rings drop the `/50` opacity unless it measures ≥ 3:1.
  - **Naming:** house code names the role (`bg-error`); vendored primitives keep their alias classes.

  **What consumers do:**
  - Replace the stylesheet with the canonical one in `theming/references/platform-integration.md`.
    Theme presets are HSL triples; `theme-presets.md` has the one-liner that wraps them in `hsl()`.
  - Change any `hsl(var(--X))` to `var(--X)`.

  The Tailwind v3 `tailwind.config.ts` is now a legacy note. Phlex and non-shadcn packages have no
  alias block, so `bg-destructive` still compiles to nothing there.
- **The Modern preset's dark `--ring` is lighter:** `263.4 70% 50.4%` → `263.4 70% 56%`, taking it
  from 2.80:1 to 3.47:1 against its background, which clears the 3:1 focus rule. It no longer equals
  Modern's dark primary.
- **`std-reactjs` forms and tests map API errors through `std-api-design`'s envelope.**
  `VALIDATION_ERROR` goes to `setError`; anything else goes to a root error carrying `requestId`. The
  old example mapped a Rails `{errors: {field: [...]}}` hash that the envelope's owner never
  returns.
- **Gate change · hook registration (`hooks/hooks.json`).**
  - **security-scan:** now also runs on `MultiEdit`, `NotebookEdit`, and MCP file writers, matched
    as whole tool names:
    `^mcp__[^_].*__(write_file|edit_file|create_directory|move_file|create_or_update_file|push_files)$`.
    That string is `_hooklib.MCP_FILE_WRITE_MATCHER`, and the script tests tool names against it.
  - **The five shell gates** (`dangerous-command-blocker`, `pre-commit-check`, `deployment-gate`,
    `terraform-command-gate`, `mcp-install-gate`) match `Bash|PowerShell|Monitor`; in 3.2.0 they
    matched `Bash` only. Each reads `tool_input.command`; a Monitor WebSocket watch carries none.
  - **mcp-install-gate:** also matches `Edit|Write|MultiEdit` and the same MCP file writers, which it
    tests with `hooklib.is_mcp_file_write`.
  - **migration-validator:** matches `Edit|Write|MultiEdit`.
  - **auto-format and post-edit-dispatch:** match `Edit|Write|MultiEdit` and
    `^mcp__[^_].*__(write_file|edit_file)$`. The dispatcher's timeout goes from 20 to 30 seconds.
  - **Why the MCP matchers are anchored:** a matcher holding a regex character is an unanchored
    JavaScript regular expression. Without `^…$`, a verb pattern would also route Gmail
    `create_draft`, Calendar `create_event`, Linear `create_attachment`, and memory
    `create_entities` into a gate that denies whenever Python is missing, and any longer tool name
    containing `write_file` would start the formatter.
  - **audit-logger:** runs on every tool (`*`) for PostToolUse, PostToolUseFailure, and
    PermissionDenied, and records PowerShell and Monitor commands like Bash.
  - **TaskCreated (newly registered):** `task-completed-checker.py` snapshots each task's baseline
    and always exits 0.
  - **Orthogonality (newly registered):**
    - `orthogonality-index.py` on SessionStart `startup|resume|fork`, with `async: true` (timeout
      30). Forked sessions have reported source `fork` since Claude Code v2.1.214.
    - `orthogonality-watch.py` on PostToolUse `Edit|Write|MultiEdit|Bash|PowerShell` and
      `^mcp__[^_].*__(write_file|edit_file)$`, and on PostToolUseFailure `Bash|PowerShell`, so an
      install or generator whose chained command fails still refreshes the index. All three entries
      use `asyncRewake: true` (timeout 150).
  - **Timeouts:** every synchronous handler has an explicit timeout of 1–30 seconds, and the two
    background handlers above stay within 180. All hooks remain command hooks in shell form.
- **Gate change · the three security gates fail closed, even before they start.**
  `run-python.sh --fail-closed` is used by security-scan, dangerous-command-blocker, and
  terraform-command-gate.
  - **When Python or the gate breaks:** exit 2 and **block** when no Python 3 is found, or when the
    gate exits with anything other than 0 or 2 (for example, a broken import). Before, the tool ran.
  - **When the event is bad:** these three also **deny** a non-empty event they cannot parse, a
    non-object event, a non-object `tool_input`, or a failed `_hooklib` import. Empty stdin is still
    allowed.
  - **Every other hook:** exits 1 when it cannot start, a visible error that never blocks.
  - **When a gate stalls:** a gate that runs past its `timeout` (10 s; 30 s for `security-scan`) is
    cancelled, and the tool runs. The hooks reference: "A timed-out `command`, `http`, or
    `mcp_tool` hook doesn't block the tool call." No launcher can turn that into a block; the
    permission floor, its Bash rules and their PowerShell mirrors, is what still holds. The realistic
    stall is a cold Windows start probing `python`, `py -3` and `python3`, which the interpreter
    cache in `$CLAUDE_PLUGIN_DATA` limits to the first run.
- **Shell lexer moved to `hooks/_shell.py` and push parser to `hooks/_gitpush.py`**, imported
  normally instead of loaded by path from `pre-commit-check.py`.
  - **Two dialects, one segment shape.** `_shellcore.py` reads POSIX shells for Bash and Monitor:
    subshells, brace groups, `if`/`for`/`while`/`until` and `function` bodies, `!`, `$(...)` and
    backticks (bare or double-quoted), `bash <<<` here-strings, `bash -c -- '…'` and `$'…'`, while
    single-quoted prose stays prose. `_shellpwsh.py` reads PowerShell for the PowerShell tool:
    backtick escapes, `''`, here-strings, `(...)`/`$(...)`/`{...}` groups and comments.
  - **Handed-on scripts** (`bash -c`, `eval`, `ssh host "…"`, `| sh`, `pwsh -Command`,
    `Invoke-Expression`, `cmd /c`, `wsl`) are read in their own dialect. Program names match without
    regard to case or a `.exe` suffix.
  - **When a module breaks:** a broken or missing `_shell.py`, `_shellcore.py` or `_shellpwsh.py`
    denies at `dangerous-command-blocker` and `terraform-command-gate` (a broken `_dangerpwsh.py` or
    `_protected.py` at the blocker). At `deployment-gate`, `mcp-install-gate` and `pre-commit-check`
    it is a visible hook error (exit 1), not a silent allow; a missing `_teamgate.py` is the same
    exit 1 at the two push gates.
- **`post-edit-dispatch.py` runs 15 advisory checkers**, with `orthogonality-checker.py` appended
  last. Its budget and per-checker line cap are unchanged.
- **`clean-architecture-checker.py` reads its import pattern (`IMPORT_OF`) from the shared
  `_archgraph` module.** Its behaviour is unchanged.
- **Launcher.** Windows tries `python`, then `py -3`, then `python3`; macOS and Linux try `python3`,
  then `python`. The interpreter that works is cached in `$CLAUDE_PLUGIN_DATA/sdh-python-interpreter`,
  so a hook starts one interpreter instead of two.
- **Hook output follows the per-event contract** (`hooks/README.md`):
  - **PreToolUse:** a deny's `permissionDecisionReason` reaches Claude; an ask's reason is shown
    only to the user.
  - **PostToolUse:** advisory lines reach the model as `additionalContext`, capped at 20 lines /
    4,000 characters (`HOOK ERROR` lines are always kept) and 5 lines per checker.
  - **SessionStart:** one JSON object; the GOVERNANCE GAP goes to the user as `systemMessage`.
  - **Stop:** a `systemMessage`.
  - **SubagentStart and UserPromptSubmit:** `additionalContext`.
  - **TeammateIdle and TaskCompleted:** exit 2, with the reason on stderr.
- **Hook contracts re-verified against the live hooks reference.** TeammateIdle receives only
  `teammate_name` and `team_name`, and `teammate-idle-checker.py` no longer reads `agent_name` /
  `task_description`, which no event carries. TaskCreated and TaskCompleted receive `task_id`,
  `task_subject` and optional `task_description`. SubagentStart injects
  `hookSpecificOutput.additionalContext`. `subagent-context.py` matches team members by `agentId`
  only.
- **Path matching is project-relative.**
  - **Canonical dirs:** `under()`, `under_any()`, and `replace_first_segment()` match an absolute
    path relative to the nearest package root (`Gemfile`, `package.json`, `pyproject.toml`, or
    `manage.py`, stopping at `.git`). A checkout under `/app`, or under a folder named `private`, no
    longer matches canonical dirs above the project.
  - **Framework detection:** in a folder that also holds a bundler marker, `detect_framework()` gives
    `.rb` and `.py` files the backend label, and a React Native root with a CocoaPods `Gemfile` stays
    `react-native`.
- **Vendored shadcn/ui primitives are CLI-owned in the hooks.** For files under `components.json`
  `aliases.ui`:
  - code-quality, test-coverage, i18n, and atomic-design skip the file;
  - accessibility keeps only the clickable-`div` and hidden-interactive checks;
  - design-token keeps only the unregistered-token check;
  - auto-format does not reformat the file;
  - teammate-idle-checker does not ask for a test.

  One Write of a stock sidebar drew 10 warnings; it now draws none. Blocks installed outside
  `aliases.ui` are fully checked. Label props, ring contrast, and the reduced-motion backstop for
  vendored files are now enforced only by the `std-shadcn-ui` skill.

**Hook decisions — what now passes, asks, or denies differently.** Every line below changes what a
session in a consuming repo is allowed to do.

- **Gate change · `pre-commit-check.py`:**
  - **Now passes:** commit bodies and trailers (`Co-Authored-By`). Only the subject line is
    validated, from `-m`, `-am`, `--message`, a `$(cat <<'EOF')` heredoc, `-F -`, or `-F <file>`.
    `--follow-tags`, `--fill`, and `-fix` are no longer read as `-f`.
  - **Now denies:** deleting a protected branch (`--delete main`, `:main`), and a force push that
    names no destination when the event cwd's repository resolves it to a protected branch.
  - **Now asks:** on a direct push that names no destination (`git push`, `git push origin HEAD`,
    `git push origin "$(git branch --show-current)"`) when it resolves to a protected branch
    (`@{push}`, else the current branch), and on a force push that names no destination and does not
    resolve to one. Nothing is resolved without the event cwd, when git fails, or after a `cd`,
    `ssh`, `wsl` or `git checkout`/`switch`/`worktree` earlier in the command.
  - **Now judges** PowerShell and Monitor commands too, reading a PowerShell here-string commit
    subject.
  - **Unchanged decision, new parsing:** a force push is judged per refspec destination (`HEAD:main`,
    `refs/heads/main`, and globs in `SDH_PROTECTED_BRANCHES`).
- **Gate change · `deployment-gate.py`:**
  - **No longer asks:** on feature branches whose names contain a protected word
    (`feature/TICKET-42-main-nav`), or on a `gh pr create --base main` chained after a push.
  - **Now asks:** on fastlane release lanes and upload actions, `eas submit` / `eas update`, and
    `gcloud run|app|functions deploy`; on a push that names no destination when it resolves to a
    protected branch; and on the same commands from PowerShell and Monitor. It shares
    pre-commit-check's push parser, `_gitpush.py`, and gives one protected-branch warning per
    command.
- **Gate change · `dangerous-command-blocker.py`:**
  - **Now passes:**
    - quoted mentions, such as a commit message naming `DROP TABLE` or a PR title naming `chmod 777`
    - `rsync -lrt`, and heredocs written to files
    - `rm -rf` of non-root absolute or home sub-paths (`~/proj/old`, `/tmp/x`, a build dir), and
      `: > /tmp/log`
    - DROP / TRUNCATE against `*_test` / `*_development` databases, SQLite test files, or
      `-h localhost`
  - **Now denies:**
    - `rm -fr /`, `rm -r -f ~`, `rm -rf $VAR/`
    - a `>` redirect onto `/etc`, `/usr`, `/bin`, `/boot`, or `/lib`
    - `curl -d` / `--data` / `-F` / `-T` to a non-local URL
    - an unfiltered `DELETE` through a database client
    - destructive commands inside `bash -c`, `eval`, `ssh host "…"`, or `… | sh`
    - any shell word followed by `-c` in a segment (`echo sh -c "rm -rf /"`, erring on the safe
      side)
    - `rm -r ~` and `rm -r /` without `-f`, and program names in any case or with `.exe`
    - a shell write that meets `security-scan`'s file decision (`_protected.shell_write_verdict`): a
      provider key written through a redirect or `tee` (a here-document, a here-string, `echo` or
      `printf` arguments) into any file, and a write to an environment file or key material unless
      it is seeded from a committed template (`cp .env.example .env` passes). A data file inside a
      project's `secrets/`, `credentials/` or `private/` asks, and a command that only uses a key
      (`gh secret set X --body …`) writes no file and passes
    - from the PowerShell tool: `Remove-Item -Recurse` (or `rm`, `ri`, `del`, `rd`, `rmdir`,
      `erase`, any parameter prefix, `-Name:value`) on a drive root, the home directory or a system
      directory, and on a wildcard, `.` or bare-variable target with `-Force` and no filter;
      `rd /s` and `del /s` through `cmd /c`; `Format-Volume`, `Clear-Disk` and `Remove-Partition`;
      a download run through `Invoke-Expression` or piped to `pwsh -`; and
      `Invoke-WebRequest`/`Invoke-RestMethod` with `-Method Post`, `-Body`, `-Form` or `-InFile` to
      an external URL
    - the same commands inside `pwsh -Command`, `Invoke-Expression`, `cmd /c` or `wsl`, and from the
      Monitor tool
  - **Still passes:** `-WhatIf`, filtered deletes, `-OutFile` downloads, and a POST to localhost.
- **Gate change · `terraform-command-gate.py`:**
  - **Now denies:** `apply -destroy` / `--destroy` under terraform and tofu, which used to go to the
    apply checklist, including through `sudo`, `bash -c`, and `docker run hashicorp/terraform`.
  - **Now passes:** commit messages and greps that mention terraform subcommands.
  - **Now denies:** `TERRAFORM destroy`, `terraform.exe destroy`, and the same commands from the
    PowerShell and Monitor tools.
- **Gate change · `migration-validator.py`:**
  - **Now asks** on:
    - Alembic `alembic/versions` and Django `migrations/`: destructive forward operations, an empty
      `downgrade()`, RunPython / RunSQL with no reverse, interpolated SQL
    - Rails multi-database `db/<name>_migrate`
    - MultiEdit
  - **Judged after the edit:** the gate checks the file as it will be, so an edit to a migration
    that already holds a flagged construct asks again.
  - **No longer asks:** about `drop_table`, `TRUNCATE` or `DROP INDEX` inside a Rails `def down`
    (or `def self.down`) or a `reversible` block's `dir.down`, where they undo the migration. A drop
    in the forward direction still asks.
- **Gate change · `mcp-install-gate.py`:**
  - **Now asks** on:
    - writes to `.mcp.json` or `.claude.json` through Bash redirects, `tee`, copy/move, or MCP file
      tools
    - `.claude.json` writes that add servers
    - `.MCP.json`, because names are now compared case-insensitively
  - **Correct scope:** the prompt now reports `-s project`, `-sproject`, and `--scope=project`
    correctly.
  - **Now asks** on a write that approves a project's servers wholesale:
    `enableAllProjectMcpServers: true`, or a new `enabledMcpjsonServers` name, in
    `.claude/settings.json` or `.claude/settings.local.json`, through Write/Edit/MultiEdit, MCP file
    writers, Bash or PowerShell. `disabledMcpjsonServers` never asks. The `.mcp.json` ask no longer
    promises teammates a `Pending approval` step unconditionally, since those keys skip it.
  - **Now asks** on the same MCP commands and writes from PowerShell (`Set-Content`, `Out-File`)
    and Monitor, and on a GitHub `push_files` whose entries include `.mcp.json`, `.claude.json` or
    such a settings file.
- **mcp-install-gate:** asks on `shadcn mcp init` through any runner (`npx`, `pnpm dlx`, `bunx`,
  `yarn dlx`), which writes MCP configuration from inside the CLI. It also asks when an MCP move
  puts a file onto `.mcp.json`.
- **Gate change · `security-scan.py`:**
  - **Now denies:**
    - provider-format keys (Anthropic, OpenAI, Stripe, GitHub classic and fine-grained, GitLab,
      Slack, AWS, Google OAuth, npm, private key blocks) under any variable name and in any file,
      `.md` and test fixtures included. AWS documentation keys containing `EXAMPLE` are excepted.
    - `.ENV` / `Secrets/db.yml` case variants, on every OS
    - the same checks on NotebookEdit, MultiEdit, and MCP writes
  - **Now asks instead of denying:**
    - credential-shaped literals: quoted, letters and digits, entropy ≥ 3.0, assigned to a password
      / secret / token / api_key name. Skipped in locale catalogs, docs, tests, fixtures, factories,
      and seeds.
    - Google `AIza` keys
    - `.github/workflows/` edits, with a checklist (SHA pins, `permissions`, `pull_request_target`,
      secrets)
  - **Now passes:**
    - `.env.example` and other templates, and `id_*.pub`
    - `const token = useAuthStore.getState().token`, `password: "Password"` in a locale file, and
      `POSTGRES_PASSWORD: "postgres"` in Compose
    - code files inside `secrets/`, `credentials/`, or `private/` (their content is still scanned)
    - every write in a repo checked out under a folder named `private`
  - **Unchanged:** `.envrc` stays denied.
  - **Now judges each `push_files` entry** as a write of its own: its path against the protected
    files, its content for keys.
  - **Deny text:** a protected-file deny now tells Claude that a person edits the file outside Claude
    Code, not by another route such as a shell redirect.
- **Gate change · MCP file writes (`security-scan`, `mcp-install-gate`):** an MCP tool reaches these
  gates only when its whole name ends in the filesystem server's `write_file`, `edit_file`,
  `create_directory`, or `move_file`, or GitHub's `create_or_update_file` or `push_files`, on any
  server (plugin-bundled servers included).
  - **Now judged:** those writes get the same deny and ask checks as Write and Edit, and a move's
    `destination` is read. GitHub `create_or_update_file` and `push_files` go through the
    fail-closed `security-scan`, so without Python that remote write is denied, like a local Write.
    Both gates judge each `push_files` entry as a write of its own, path and content.
  - **Stay quiet:** Gmail `create_draft`, Calendar `create_event`, Linear `create_attachment`,
    memory `create_entities`, Notion page updates, and the claude.ai Google Drive `create_file` (a
    title, no path).
  - **Not scanned:** third-party file tools with other names (a `create_file` that takes a path,
    `append_file`, `edit_block`). Only `audit-logger` records them.
- **Gate change · `teammate-idle-checker.py`:**
  - **Role:** the teammate's role now comes from this session's team config, then from `agent_type`.
    An agent whose `tools:` line holds no edit tool skips every gate, so `security-auditor` and
    `incident-responder` are now exempt.
  - **Coverage gate:** runs only in the teammate's own linked worktree. A shared checkout is never
    judged.
  - **Rejections:** the reason goes to stderr, and the gate stops after 3 identical rejections.
- **Gate change · `task-completed-checker.py`:**
  - **Tests gate:** only write-intent wording triggers it. "Run the test suite" and "Fix failing
    tests" no longer reject; "Update the README with test instructions" still does. Committed tests
    now count.
  - **Uncommitted-source gate:** applies only to a teammate in its own worktree.
  - **Rejections:** the reason goes to stderr, and the gate stops after 3 identical rejections.
- **Gate change · `team-task-validator.py`:**
  - **Scope:** judges only files the task touched (a linked worktree, or changes since a
    baseline taken on `TaskCreated`), and stays quiet otherwise, including about changes made before
    the task was created.
  - **Debug statements:** matched as statements, and never inside comments, JSDoc, docstrings,
    strings, tests, scripts, `bin/`, or `*.config.*`.
  - **New:** it also flags trailing whitespace, and untracked files now count.
- **Advisory checkers** (these never block):
  - **design-token:** a new warning on color utilities that name no registered token
    (`bg-primary-600`, `bg-danger`, `fill-chart-6`). Tokens defined in the same file are accepted.
  - **i18n:** judges each JSX text node, so literal text in a file that also calls `t(` now warns.
    Package-root `components/` is in scope.
  - **accessibility-checker:** judges a removed focus outline per element (its opening tag, class
    string or declaration block) instead of a ±3-line window. A customised Radix or Base UI overlay
    container (`DialogPrimitive.Content`, `Popover.Popup`) no longer warns, and a neighbouring
    element's ring no longer excuses a bare `outline-none`.
  - **test-coverage:** now warns on untested Python modules under a FastAPI `app/` rooted at
    `pyproject.toml`.
  - **test-coverage-checker:** shares test-runner's candidates (`hooks/_testpaths.py`). Python roots
    at `pyproject.toml`, `manage.py`, `setup.py` or `setup.cfg`; a Rails model's Minitest `test/`
    mirror counts; the warning appears once per file per session.
  - **clean-architecture:** now warns on HTTP concerns (`HTTPException`, `JSONResponse`,
    `status.HTTP_*`) in Python services, and exempts App Router Server Components.
  - **api-design:** now covers Next.js route handlers (`app/**/route.ts|js`).
  - **monitoring:** now covers `services/`, `tasks/`, and `views/` packages; Django `views.py`,
    `viewsets.py`, `services.py`, and `tasks.py`; and Ruby hash keys (`password:`).
  - **terraform:** the tags rule is AWS-only, and it reads sibling `.tf` files and a calling root
    module's `default_tags`.
  - **test-runner:** now reminds you about Rails `spec/` / `test/` and pytest mirrors.
  - **rails-routes:** session and cookie middleware, and `Sidekiq::Web.app_url`, no longer count as
    authentication; inline `constraints:` does.
- **Lifecycle hooks:**
  - **session-start-check:** looks for the floor in project, local, user, and file-based managed
    settings, so a floor held only in user or managed settings no longer reports a GOVERNANCE GAP.
    Only missing secrets, privilege, remote-exec, or infrastructure rules count as a gap, and each
    `PowerShell(...)` mirror counts like its Bash rule. Missing build-artifact `Read` rules become a
    note to the model. A file-based managed floor that carries the whole catastrophic tier counts as
    complete: a missing `Read(**/*secret*)` is then a note too, and with no managed floor it is still
    a gap. The fallback sample adds `PowerShell(Invoke-Expression:*)`.
  - **session-stop-summary:** speaks only when the tree summary changed.
  - **subagent-context:** gives team context only to members of this session's team.
  - **vague-request-detector:** no longer fires on prompts that carry a concrete signal (a path,
    backticks, a digit, an identifier, a stack name, or 12+ words), and its advice is conditional.

### Removed

- **ApexCharts and `react-apexcharts` are no longer house libraries**, over their licence. They are
  gone from `CLAUDE.md`, `README.md`, `sdh-engineering-standards`, the web template, and every skill
  and agent that recommended them. See *Changed → Charts*.
- **The Tailwind v3 `tailwind.config.ts` token block** in `theming/references/platform-integration.md`
  is now a short legacy note beside the v4 stylesheet.

### Fixed

- **Permission floor (ACTION REQUIRED) · `Bash(rm -rf /)*` was malformed, so Claude Code skipped
  it.** The `*` sat outside the closing parenthesis; Claude Code reports *"Malformed Tool(content)
  rule"* and drops the rule entirely rather than guessing. It is now `Bash(rm -rf /)` — an exact
  match on the bare command — in both `.claude/settings.json` and
  `.claude/managed-settings.template.json`. The adjacent `Bash(rm -rf /*)` was always valid, and
  `dangerous-command-blocker.py` blocked the command throughout, so the hole was in the
  permission layer only. **If you copied the floor, replace the malformed line:** the SessionStart
  sentinel compares rules by exact string, so it will report your floor as stale and name
  `Bash(rm -rf /)` as missing until you do.
- **Accessibility tokens · `--border` and `--input` gave text fields no visible edge.** They measured
  1.23–1.37:1 against `--background` and `--card` in every token block, under WCAG 2.2 SC 1.4.11's
  3:1. Both are darkened, keeping hue and saturation, in `design-tokens.md`, all three presets, the
  Tailwind v4 stylesheet, the React Native tokens, and the shared token package example:
  - Default and Corporate: `214.3 31.8% 59%` / `217.2 32.6% 42%` (3.20 / 3.29:1)
  - Modern: `240 5.9% 58%` / `240 3.7% 39%` (3.24 / 3.19:1)
  - Minimal: `0 0% 56%` / `0 0% 38%` (3.23 / 3.20:1)

  `--sidebar-border` follows as an alias. A field on a tinted panel still measures 2.92 / 2.40:1;
  *Changed → Theming contrast tables* gives the remedy.
- **`brand-identity`'s palette recipe reproduced failing values.** Its Borders row (85–92% / 15–25%)
  gave borders under 3:1, and its Muted text row reached 50% (3.95:1 on white). Both rows now name
  the surface and the ratio they must clear, with the measured house range.
- **Touch targets were labelled as WCAG numbers.** `std-design-system`, `design-critique`,
  `design-system-architect`, and `design-to-code` called the 44×44 mobile and 32×32 web targets WCAG
  2.5.8 requirements. They are house minimums above 2.5.8's 24×24 CSS px. The arbitrary
  `min-h-[44px] min-w-[44px]` is now `min-h-11 min-w-11` in `design-to-code`, `std-accessibility`,
  and `figma-handoff`.
- **Drift from the drill-down navigation standard:**
  - `heuristic-evaluation.md`: breadcrumbs start at level 3, and a navigation severity table was
    added.
  - `screen-patterns.md`: filters live in the list page, and Settings categories in the Settings
    area's own layout.
  - `atomic-design`: `AppSidebar` (areas only), `SectionNav`, and `FilterPanel` replace `Sidebar`;
    page examples no longer hardcode nav items or breadcrumbs.
  - `std-react-native` said "max 3 levels of nesting" without saying whether it counted navigators
    or screens. It now caps navigator nesting at three (root stack → area tabs → a stack per tab)
    and leaves screen depth to the drill-down levels, and deep linking is no longer described as
    only for push notifications.
- **`std-reactjs`'s route tree put `errorElement` on the root layout route,** so a route error (a
  record not found, a failed loader) replaced the whole layout, sidebar included. The page-level
  `errorElement` now sits on a pathless route inside `AppLayout`, so not found and the no-access
  page render inside the shell.
- **TanStack Query's deprecated `ensureQueryData`** is replaced by `queryClient.query` in
  `std-reactjs`'s loader examples, with an explicit `staleTime`.
  TanStack Query 5 deprecates it for removal in its next major; a project on a release that predates
  `queryClient.query` keeps `ensureQueryData` until it upgrades.
- **`std-reactjs` named "React Router v6+" and imported from `react-router-dom`.** Examples now use
  React Router 8: `react-router`, with `RouterProvider` from `react-router/dom`, since v8 removed
  `react-router-dom`.
- **The `/reactjs-dev` router example** wrapped every route in its own `<Suspense>` and always landed
  on `/dashboard`. Pages now sit under layout-level Suspense inside area layouts, and the landing page
  is derived per role.
- **Second error envelopes removed:**
  - `rails-architect` defined its own `{ error, code: Integer, details }`. Its patterns library now
    scopes `set_order` through `policy_scope` (404, not 403), authorizes `create`, renders errors
    through the shared concern, and returns the house `pagination` envelope.
  - `api-designer/references/api-conventions.md` uses the one flat envelope in its 429 example and
    OpenAPI `ErrorResponse`, and the OpenAPI template's `page`/`pageSize` became `cursor`/`limit`,
    citing the pagination owner.
  - A GREEN controller example in `code-reviewer`'s PR review guide rendered a partial envelope
    (`{ error:, code: 422 }`). It now renders through the single `render_api_error` helper.
- **`std-api-design`'s `CursorPaginable` hardcoded the `orders` table.** The pagination and
  versioning examples now use the real Panko API
  (`Panko::ArraySerializer.new(records, each_serializer:)`, `Serializer.new.serialize`).
- **`/phlex-dev` step 3 searched a hardcoded `backend/` wrapper directory,** and Phlex layout and
  dropdown examples used arbitrary Tailwind values (`grid-cols-[240px_1fr]`, `min-w-[12rem]`). Both
  are gone.
- **Three SKILL.md bodies pointed at another skill's reference as if it were their own.**
  `security-auditor` and `toolchain` named `std-infrastructure/references/ci-pipeline.md` without
  `../`, and `api-designer` named `references/errors-rails.md` and `references/errors-typescript.md`,
  which live in `std-api-design`. A SKILL.md body resolves a bare pointer inside its own skill, so
  each named a file that does not exist and CI's reference-resolution lint failed (all four
  failures were already present at v3.2.0). They are now
  `../std-infrastructure/references/ci-pipeline.md`,
  `@skills/std-api-design/references/errors-rails.md`, and
  `@skills/std-api-design/references/errors-typescript.md`.
- **`nextjs-dev`'s `error.tsx` example used raw palette classes** (`text-red-600`, `text-blue-600`)
  in a stack that styles only with tokens. It now uses `text-error` / `text-primary` and
  `role="alert"`.
- **Hook defects found by this release's hook audit**, grouped by hook, each with the symptom a user
  saw:
  - **`run-python.sh`**
    - On Windows it tried `python3` first. That is the slow WindowsApps alias, or a Store stub that
      runs nothing. Where a python.org install put only `py` on PATH, no hook ran.
    - A fail-closed gate with no Python, or with a broken import, failed open, and the tool ran.
  - **`hooks.json`**
    - NotebookEdit and MCP file writes skipped security-scan. MultiEdit skipped migration-validator
      and mcp-install-gate. MCP writes also skipped mcp-install-gate, auto-format, and every checker.
    - The audit trail held no failed calls, no auto-mode denials, and no tool except Bash, Edit, and
      Write.
    - PowerShell and Monitor commands reached no shell gate, so on Windows, where the PowerShell tool
      is on by default, most commands went unjudged.
  - **`_hooklib.py`**
    - A truncated or non-object event was allowed by the fail-closed gates.
    - Notebook cells, MultiEdit `edits[]`, and MCP `path` / `newText` writes were never scanned.
    - `.ENV` matched no protected pattern on case-insensitive filesystems.
    - A checkout under `/app`, or under a folder named `private`, matched canonical dirs above the
      project.
    - One legacy file put 402 warning lines (32K characters) into context on every edit.
    - A cp932 console crashed a hook on an em dash.
    - A checker that read a file mid-format saw `""` and passed every rule.
  - **`post-edit-dispatch.py`**
    - An empty or unparseable event ran every checker on `{}` and printed nothing, exactly like a
      clean edit.
    - Checkers raced auto-format and judged the half-written file.
    - A slow checker on a 1 MB file pushed the reply past the hook timeout, which discards every
      warning.
  - **`auto-format.py`**
    - On Windows, every `prettier` / `rubocop` launch raised FileNotFoundError, because a `.cmd` shim
      is not an `.exe`. Nothing was formatted, and nothing said so.
    - It ran the PATH binary instead of the project's (`bundle exec`, `node_modules/.bin`, `.venv`).
    - A formatter timeout or failure was silent.
    - It reformatted vendored shadcn primitives, turning every `shadcn add --diff` into noise.
  - **`audit-logger.py`**
    - Bash commands were logged in plaintext (see *Security*).
    - The log followed the handler's cwd, so a worktree teammate's log was deleted with its worktree.
    - A write failure went to the debug log, so gaps in the trail were invisible.
  - **`capture-event.py`**
    - Two captures in the same second overwrote each other.
    - Stdin was re-encoded through the console codepage.
  - **`pre-commit-check.py`**
    - It validated the **last** `-m`, which is the `Co-Authored-By` trailer, instead of the subject.
      Conventional commits with trailers were denied.
    - A heredoc commit was judged as the literal subject `$(cat <<`.
    - `--follow-tags` and a chained `gh pr create --fill` were read as `-f`. The house
      push-then-open-a-PR chain was denied as a force push to main.
    - A push that named no destination (`git push`, `git push origin HEAD`) went through on a
      protected branch without a question.
  - **`deployment-gate.py`**
    - It asked on feature branches named with a protected word, and on a chained
      `gh pr create --base main`.
    - It never saw a fastlane, EAS, or gcloud release.
  - **`dangerous-command-blocker.py`**
    - **Denied by mistake:** a commit message mentioning DROP TABLE, `rsync -lrt` (read as a netcat
      listener), a local `_test` database reset, and `rm -rf` of any absolute build path.
    - **Allowed by mistake:** `rm -fr /`, `rm -r ~` and `rm -r /` without `-f`, a quoted unfiltered
      DELETE, `curl -d @.env https://…`, and `printf 'KEY=sk_live_…' >> .env`.
  - **`terraform-command-gate.py`**
    - `terraform apply -destroy` got the ordinary apply checklist instead of a deny.
    - A commit message mentioning `terraform state rm` was denied.
    - `TERRAFORM destroy` and `terraform.exe destroy` passed.
  - **`migration-validator.py`**
    - It asked "no down method" of edits to migrations that had one.
    - It missed a `remove_column` added inside an existing `def change`.
    - It checked no Alembic or Django migration.
    - It asked about `drop_table` and `TRUNCATE` inside a Rails `def down`, where they undo the
      migration.
  - **`mcp-install-gate.py`**
    - `-s project` and `--scope=project` were reported as "local (default)".
    - A write to `.MCP.json`, or a shell redirect into `.mcp.json`, went unasked.
  - **`security-scan.py`**
    - **Denied by mistake:**
      - `const token = useAuthStore.getState().token`
      - `password: "Password"` in a locale file
      - `web/.env.example` and `modules/secrets/main.tf`
      - every `.github/workflows/` edit
      - every write in a repo under a folder named `private`
    - **Missed:** provider keys assigned to variable names outside its list.
  - **`code-quality-checker.py`**
    - `Map<string, number>` and destructured props counted as several parameters.
    - JS function length stopped at the destructuring `{`, so long React components passed.
    - In Python, trailing blank lines, `elif`, and continuation lines counted as length or nesting.
    - Quadratic line counting timed the dispatcher out on large files.
  - **`design-token-checker.py`**
    - "Missing focus-visible" fired on controls that inherit an atom's ring, and on tests, stories,
      and React Native.
    - "Missing reduced-motion" fired on `transition-colors`, on `useReducedMotion` / `MotionConfig`
      code, and on `@import "tw-animate-css"`.
    - Its remedy suggested `hsl(var(--primary))`, a double wrap under the new wiring.
    - A private tool gate kept it silent on MultiEdit and MCP writes.
  - **`accessibility-checker.py`**
    - An `alt` or `aria-label` written after an inline arrow handler was not seen.
    - Pass-through primitives, shadcn `FormControl` inputs, and hidden or submit inputs were flagged
      as unlabelled.
  - **`i18n-checker.py`**
    - `{page > 1 && page < pageCount}` and `&hellip;` were read as copy.
    - One `t(` call exempted a whole file.
  - **`atomic-design-checker.py`**
    - Every named import went unflagged, including the skill's own violation examples.
    - Co-located `./Card.css` and `import type` were flagged.
  - **`test-coverage-checker.py`**
    - Every edit of a tested Python module warned, because it looked only for `billing.test.py`.
    - FastAPI `app/` was never checked.
  - **`clean-architecture-checker.py`**
    - `update!(status: :paid)` and a comment containing "render" warned, while `head :not_found` and
      `import axios from 'axios'` passed.
    - A file starting with blank lines backtracked a regex exponentially.
  - **`terraform-checker.py`**
    - Every resource file of a correctly configured root module warned about tags and backend,
      because `default_tags` lives in `providers.tf` and the backend in `backend.tf`. Child modules
      and GCP IAM files warned too.
    - `required_version` hid unpinned providers.
    - `"${var.x}"` was called a hardcoded secret.
  - **`test-runner.py`**
    - The reminder never fired for Rails or Python.
  - **`error-handling-checker.py`**
    - `catch {` with no binding, and comment-only catch bodies, passed.
  - **`api-design-checker.py`**
    - A complete envelope with `details: [{...}]` was reported as missing `requestId`, in Rails and
      FastAPI.
    - `status.HTTP_200_OK` on a POST passed.
  - **`monitoring-checker.py`**
    - Ruff-wrapped multi-line log calls and Ruby `password:` keys passed.
    - LLM usage counts (`{usage.output_tokens}`) were flagged as secret tokens.
  - **`rails-routes-checker.py`**
    - A real unauthenticated `Sidekiq::Web` mount was silenced by a guard block that closed above
      the mount, or by session middleware on an API-only app.
  - **`database-design-checker.py`**
    - pytest modules under `models/` got the plan notice and the model checks.
    - A directory of 3,000 fresh migrations took 22 s cold, past the dispatcher's budget.
  - **`session-start-check.py`**
    - The GOVERNANCE GAP was plain text the developer never saw.
    - A floor in user or managed settings was ignored.
    - Missing build-artifact rules raised the security banner.
  - **`session-stop-summary.py`**
    - Its summary was plain stdout that nobody saw.
    - A first-line ` M` (modified, not staged) counted as "1 staged".
  - **`subagent-context.py`**
    - Its output went to the debug log, so subagents never got the stack, and the stack text was out
      of date.
  - **`vague-request-detector.py`**
    - It fired on fully specified prompts ("Create a Terraform module for the RDS instance with
      multi-AZ, 7-day backups").
    - It told the model it MUST call AskUserQuestion, which `-p` runs lack and dontAsk mode denies.
  - **`teammate-idle-checker.py`**
    - It blocked with the reason on stdout, so the teammate got no explanation.
    - It read `agent_name` / `task_description`, which the event does not carry. The read-only
      exemption never applied, and the coverage gate judged the whole shared tree.
  - **`task-completed-checker.py`**
    - It blocked with no explanation (stdout on exit 2).
    - It rejected tasks whose tests were already committed.
    - It ran git in the hook's cwd instead of the event's.
  - **`team-task-validator.py`**
    - It flagged `console.log` in comments, JSDoc, strings, tests, and scripts, and flagged
      `config.debugger_enabled`.
    - It missed untracked files.
    - From a monorepo package it checked nothing, because git paths are repo-root-relative.
- **Hook documentation described hooks that do not exist.**
  - **`CLAUDE.md`:**
    - It called the SessionStart, Stop, and SubagentStart hooks "prompt hooks"; every hook is a
      command hook.
    - It said Stop "validates task completion"; it summarizes the working tree.
    - It said teammate-idle-checker checks uncommitted changes.
    - It credited deployment-gate with `terraform apply`.
    - It omitted terraform-command-gate.
  - **`hooks/README.md`:**
    - It documented PostToolUse output as plain stdout lines, which the model never sees.
    - It listed `black` and `rubocop --autocorrect-all`.
    - It left every lifecycle hook out of its inventory and its stance table.
- **Token documentation drifted from the measured values:**
  - `design-tokens.md`'s description table disagreed with its value blocks (error light 60.2% →
    47%, info dark 46% → 35%, muted-foreground 46.9% → 44%).
  - A duplicate `.dark` block in `platform-integration.md` carried a stale info value.
  - The React Native registry had stale `mutedForeground`, `success`, `error`, and dark `info`
    values.
  - `defining-tokens.md` claimed ratios it never measured: brand "7.1" is 7.47, and warning "8.4"
    is 6.87.
- **The `next-themes` toggle read `theme`**, so on a dark-OS machine the first click did nothing. It
  now reads `resolvedTheme`.
- **`std-nextjs/references/rendering.md`'s example `components/ui/Accordion`** was the same file as
  shadcn's `accordion.tsx` on a case-insensitive disk. It is now `molecules/Disclosure`.
- **`figma-handoff`:** `destructive` is a registered alias in shadcn/ui packages, but a Figma
  "Destructive" layer still maps to the role, `bg-error`. Hex now converts to a complete
  `hsl(H S% L%)` value instead of bare channels.
- **`phlex-developer` and `atomic-design`'s `atom-theming-tokens` rule:** `bg-destructive` compiles
  to no CSS only in packages without the shadcn/ui alias block (Phlex and non-shadcn packages).
- **`atomic-design`'s `atom-standalone-primitives` rule:** the Button examples (Phlex, Vite,
  Next.js, React Native) used `hover:bg-primary-dark` and `hover:bg-secondary-dark`, which no
  registry defines and so compile to no CSS. They now use `hover:bg-primary/90` and
  `hover:bg-secondary/80`. `text-white` and `text-gray-900` on those backgrounds are now
  `text-primary-foreground` and `text-secondary-foreground`, so the text keeps its contrast in
  dark mode.
- **`web-design-guidelines`** now gives `std-design-system`'s full scope: `**/components/ui/**`,
  `**/src/theme/**` and `**/app/components/**/*.rb`, as well as styles, `tailwind.config.*` and
  `globals.css`.
- **`std-i18n`'s web i18n setup snippet** now ends with `export default i18n;`, so
  `import i18n from '@/i18n'` in `std-reactjs`'s test setup resolves as written.
- **`std-nextjs` · server actions return translation keys:** every `createOrder` schema message is a
  key, type errors included, and a caught failure returns `orders.errors.createFailed`.
  `NewOrderForm` renders errors, labels and options through `t()`. The `ActionResult` type is
  unchanged.
- **`std-nextjs` · the revalidate route handler returns the house error envelope:** the 401 carries
  `error`, `code`, `status` and `requestId`, and a bad payload returns `validationErrorBody` (422).
  api-design-checker, which now covers route handlers, flagged the old bodies as missing `code` and
  `requestId`.
- **`reactjs-dev` · the router's Suspense fallback is shadcn's `Spinner` with a translated
  `label`,** replacing a house `LoadingSpinner` that lived in `components/ui`, the CLI-owned
  primitive tier.
- **Vite SPA and access-control examples sit on the atomic ladder:** `AppLayout` is under
  `components/templates/` in `std-reactjs`'s routing and animation references, and `FadeIn` is under
  `components/molecules/`.
- **Error-envelope drift removed from four more docs.** `std-error-handling` (an integer
  `code: 404`, no `requestId`), `std-monitoring`'s request-tracing guide (a nested snake_case
  `{ error: { code, request_id } }`), `std-testing`'s route-handler test (a nested `error.code`), and
  `std-clean-architecture`'s Next.js GOOD route handler (`{ errors }`) now use, or point to,
  `std-api-design`'s one envelope: `error`, string `code`, `status`, `details`, `requestId`.
- **Server-action examples return `std-nextjs`'s `ActionResult`.** `std-api-design`'s
  `errors-typescript.md`, `std-clean-architecture`'s App Router mapping, `std-testing`'s
  server-action tests, and `clean-architecture`'s layer examples dropped their own result types
  (`{ ok: false; code; error; details }`, `{ errors: string[] }`, `{ errors }`, `{ success: true }`).
  They now return `{ ok: true, data }` or `{ ok: false, formErrors, fieldErrors }` with translation
  keys. Route handlers and the axios client keep the HTTP envelope.
- **`std-agent-teams` Quality Gates now describe what the hooks actually do.** A gate rejects with
  exit 2 and gives its reason on stderr. TeammateIdle judges only a teammate's own linked worktree
  and skips read-only agents. TaskCreated snapshots a baseline. TaskCompleted rejects uncommitted
  worktree changes and missing promised tests (commits count), and `team-task-validator` flags debug
  statements and whitespace faults in files the task touched. Every gate gives up after 3 identical
  rejections. The old text described checks that no longer exist.
- **Managed settings went to a path Claude Code never reads.** `docs/org-policy.md` and
  `.claude/managed-settings.template.json` said to deploy to `C:\ProgramData\ClaudeCode` on Windows
  and `/etc/claude-code` on macOS. The paths are `C:\Program Files\ClaudeCode\managed-settings.json`
  (Windows), `/Library/Application Support/ClaudeCode/managed-settings.json` (macOS) and
  `/etc/claude-code/managed-settings.json` (Linux and WSL). A policy left at the legacy
  `C:\ProgramData` path enforces nothing, so move it. The template's `GOVERNANCE GAP` announcement
  now says the deny floor is missing or incomplete across every settings source the plugin reads
  (project, local, user, file-based managed), not that the project's floor was never copied.

### Security

- **The audit trail redacts common credential formats before writing.** In 3.2.0 it logged Bash
  commands in plaintext.
  - **Redaction:** these are redacted before the 500-character truncation, in linear time, so a
    long base64url or dash run cannot push the logger past its timeout:
    - any `Authorization` scheme, and `Cookie` headers
    - `NAME=value` secrets, and `--password`, `--token` or `--api-key` values
    - passwords inside URLs, `curl -u user:pass`, and `curl -b` cookies
    - `mysql -p<password>`, `sshpass -p`, `docker login -p` and `redis-cli -a`
    - `aws configure set` keys, `gh secret|variable set --body`, and openssl `pass:`
    - PEM keys
    - AKIA / `ghp_` / `xox` / `sk-` / `AIza` / JWT formats
  - **Shell tools:** Bash, PowerShell and Monitor commands are recorded and redacted alike.
  - **Storage:** `.claude/audit/` creates its own ignore-everything `.gitignore`, and the log is
    owner-only on POSIX.
  - **Denials:** gate denies and asks are now recorded. A denied call never reaches PostToolUse, so
    the trail used to hold no denial at all.
- **PowerShell and Monitor commands reach the shell gates, and the floor mirrors every shell deny
  for PowerShell.** In 3.2.0 the gates matched `Bash` only, and a `Bash(...)` rule never matches the
  PowerShell tool, which is on by default on Windows: a `Remove-Item -Recurse -Force C:\` or an
  `irm <url> | iex` from that tool met no gate and no rule. PowerShell commands are now read by a
  PowerShell lexer (*Changed → Permission floor*, *Hook decisions*; *Upgrade steps* 1).
- **Shell writes meet the file gate's decision.** In 3.2.0 `security-scan` judged only Edit and
  Write, so `printf 'STRIPE_SECRET_KEY=sk_live_…' >> .env`, a here-document carrying a live key, or
  `echo … | tee config/master.key` reached no gate. `dangerous-command-blocker` now applies the same
  protected-file and provider-key tables (`hooks/_protected.py`) to redirects, `tee` and
  here-documents (*Hook decisions*).
- **`mcp-install-gate` asks before a settings write approves project MCP servers.**
  `enableAllProjectMcpServers: true`, or a new `enabledMcpjsonServers` name, in
  `.claude/settings.json` or `.claude/settings.local.json` approves a project's `.mcp.json` servers
  without a prompt, so the write itself now asks.
- **GitHub `push_files` reaches the file gates.** It commits many files to a branch in one call;
  each entry is now judged as a write of its own, its path for protected files and MCP
  configuration, its content for keys.
- **Subagents no longer receive another project's team.** `subagent-context.py` used to read the
  most recently modified team config on the machine and inject its members and absolute paths into
  every subagent. It now reads only this session's team, only for that team's members, and injects
  no paths.
- **Captured fixtures can hold credentials.** `capture-event.py` writes them owner-only on POSIX,
  never overwrites one, and says so in its docstring. `hooks/tests/fixtures/` stays gitignored.

## [3.2.0] - 2026-08-28

**Python joins the stack as a secondary backend** — FastAPI (default for new Python APIs) and
Django + DRF (admin-heavy CRUD), positioned for AI/ML serving, data pipelines, and
client-mandated stacks. Rails remains the primary backend; nothing about the Rails, frontend,
or infra conventions changed.

### Added

- **Five new `std-*` convention skills** (the [Skill + `paths:`] delivery tier — no new hooks,
  so nothing to copy by hand and no new denials or gates):
  - `std-python` — src/ layout, typing, `uv`/`ruff`/`mypy`, pydantic v2, and the
    models/services/controllers layering shared by both frameworks. Claims `**/*.py`,
    `**/pyproject.toml`, `**/requirements*.txt`.
  - `std-fastapi` — routers, Pydantic schemas, SQLAlchemy 2.0 + Alembic, `Depends` injection,
    Celery (Redis broker), the house error envelope by reference. Scoped to `app/`-package
    structure and `alembic/` — **not** to any universal Python file.
  - `std-django` — models with DB constraints, DRF viewsets/serializers, service functions,
    QuerySet managers, GeoDjango on the house PostGIS, migrations. Scoped to Django-idiomatic
    filenames (`manage.py`, `models.py`, `views.py`, `migrations/`).
  - `std-python-ai-ml` — notebooks vs modules, MLflow tracking + registry, reproducibility,
    FastAPI model serving, `pgvector` before any dedicated vector DB, LLM (Anthropic SDK)
    integration with pinned evals. Scoped to `ml/`, `training/`, `inference/`, `pipelines/`,
    `*.ipynb`.
  - `std-python-performance` — N+1 prevention (Django ORM + SQLAlchemy 2.0), bulk operations,
    keyset pagination, indexing pointers, connection pooling, Redis caching. Deliberately
    overlaps the framework skills on data-access paths, mirroring how `std-clean-architecture`
    rides alongside `std-rails-conventions`.
- **Path-exclusivity by design**: the five `paths:` sets were dictated centrally so no Python
  skill claims another framework's files — `models.py`/`views.py`/`manage.py` are Django's,
  the `app/` package shape and `alembic/` are FastAPI's, and only the *general* `std-python`
  claims universal Python files, per the invariant
  `test_framework_skills_load_for_their_own_framework` pins for the JS/TS skills.
- Tech-stack and library-preference registrations for Python across `CLAUDE.md`, `README.md`,
  and the `sdh-engineering-standards` skill: `uv`, `ruff`, `mypy`, pydantic v2, `httpx`,
  Celery + Redis, `pyjwt` + `argon2-cffi` (explicitly not `python-jose`/`passlib`), pytest,
  MLflow, pandera, onnxruntime, `pgvector`, `anthropic`.
- **`/python-dev` workflow skill** — the `/rails-architect` analog for the Python stack:
  scaffold → model + Alembic migration → schemas → service → router → Celery → tests →
  query-performance pass → the `uv run ruff format && ruff check && mypy && pytest` ladder,
  with a Django + DRF variant. It sequences the `std-*` skills and owns no rules itself.
- **`docs/templates/python.CLAUDE.md`** — the per-package `CLAUDE.md` starter for Python
  service packages in a monorepo (registered in `docs/monorepo-setup.md` alongside the
  backend/mobile/web/next/shared templates).

### Fixed

- **The SessionStart area line no longer says skills "auto-load"** — v3.1.0 corrected 59 doc
  sites from *auto-loaded* to *scoped* (`paths:` limits when a skill may load; Claude still
  chooses to read it), but the one user-facing message survived. It now says "the scoped
  convention skills for it", so the first line of every session stops overpromising the
  delivery mechanism.

### Changed

- **`.py` auto-format switched from `black` to `ruff format`** — one tool for lint and format,
  matching the `std-python` toolchain. Same layout-only contract: the hook runs `ruff format`,
  never `ruff check --fix` (lint rewrites remain a deliberate human act), and
  `test_autoformat_never_changes_semantics` now also rejects `--fix`/`--unsafe-fixes`. A repo
  without ruff gets the once-per-session notice naming the install; nothing is blocked.

### Added — hook delivery for Python (the tier that arrives whether or not a skill is read)

The code-quality and error-handling checkers **already parsed `.py`** (function length,
parameter counts, indentation nesting, `except: pass`) — that enforcement was in place before
Python was even on the stack. What was missing, and ships now:

- **`_hooklib.detect_framework()` knows `django` and `fastapi`** — markers: `manage.py`,
  a **dependency-anchored** `pyproject.toml` grep (a quoted PEP 621 requirement or a Poetry
  table key — prose and comments do not count, so "# not a django project" cannot
  misclassify), `alembic.ini` + `app/main.py`; plus a path-structure fallback (`migrations/`
  dirs are Django's — alembic defaults to `alembic/versions`; the `app/routers|api|schemas`
  package shape is FastAPI's, and the `.py` branch runs before the extension-blind `src/app`
  Next.js rule so a src-layout `app` package cannot be shadowed). On a mixed root, **Rails
  markers win the tie** — Rails is the primary backend, and the ordering is test-pinned.
- **`session-start-check.py` announces Python areas** — `AREA_RULES` gains `django` and
  `fastapi` entries naming the relevant `std-*` skills; a test verifies every named skill
  exists.
- **Bare `except:` / `except BaseException` warning** (error-handling checker) — the Python
  analog of the `rescue Exception` rule: both catch `SystemExit`/`KeyboardInterrupt`, so
  shutdown and Ctrl-C die silently. Covers the tuple form (`except (BaseException, ...)`) and
  3.11 `except*` groups. `except Exception:` stays a judgement call owned by `std-python`
  (whose text now states the BaseException rule the warning cites); the hook flags only the
  unambiguous width.
- **Django's `models.py` gets the 200-line model limit** (code-quality checker) — Django keeps
  an app's models in one *file*, so the existing `app/models` *directory* rule never reached it.
- **Sensitive-data-in-logs now covers Python** (monitoring checker) — `.py` under the house
  FastAPI boundary dirs (`app/routers`, `app/api`, `app/services`, `app/tasks`), matching
  f-string interpolation, keyword arguments **including compound names**
  (`access_token=` — the dominant real spelling), and stdlib `%`-style positional args
  (`logger.info("pw %s", password)`); counters like `token_count=` stay silent, and a
  word-boundary guard keeps `catalog.update(...)` from being read as a log call. Plain string
  concatenation is the one idiom not matched.
- **45 new test assertions** (`test_python_skills_load_for_their_own_framework`,
  `test_python_stack_enforcement`) pin the Python path-exclusivity matrix, the new checker
  rules with their regression counterparts (including the adversarial-review catches above:
  compound kwargs, the tuple except form, the dependency-anchored grep, the fallback
  ordering), the FastAPI api-design checks with their Next.js scope guard, detection markers
  and the Rails-first tie-break, and the `AREA_RULES` entries. Suite: 302 passing.
- **api-design checks reach FastAPI routers** — `.py` under `app/routers`/`app/api`
  (extension-gated, so Next.js `app/api/route.ts` handlers stay out of scope — that would be
  a silent scope change for every Next repo, and it is pinned as such): the verb-in-URL check
  now applies; `response_model=list[...]` is flagged as an unwrapped collection (the house
  envelope is `{ data: [...] }`); hand-built `JSONResponse({"error": ...})` bodies are
  checked for the envelope keys with the same key patterns as the Rails check (the ONE
  app-level exception handler remains the prescribed path); and `.post()` routes without
  `status_code=` (or with an explicit 200) are told creation returns 201.

## [3.1.1] - 2026-07-16

### Fixed

- **`std-reactjs` no longer scopes to `tsconfig.json`.** `paths:` autoload is a pure glob — it
  cannot read a marker file — and `tsconfig.json` exists in *every* TypeScript project. Claiming
  it meant editing a **Next.js** or **React Native** repo's `tsconfig.json` surfaced Vite-SPA
  conventions (React Router, Zustand, ApexCharts): confident, on-topic, and wrong. `vite.config.*`
  already identifies a Vite project uniquely, so nothing Vite-specific is lost. A new assertion in
  `test_framework_skills_load_for_their_own_framework` pins the invariant — **no framework skill
  may claim a universal file** (`tsconfig.json`, `package.json`, `jsconfig.json`) — so a future
  path edit cannot reintroduce it. This affects which skill Claude auto-loads on file match; it is
  the [Skill + `paths:`] delivery tier, not a hook, so nothing you must copy by hand.

## [3.1.0] - 2026-07-16

**The advisory hooks were talking to nobody. Now they reach Claude.** If you install this, you
will start seeing warnings you have never seen before — they were always being computed, just
discarded.

### Fixed

- **14 advisory checkers wrote their warnings to the debug log and nowhere else.** `_hooklib.emit()`
  was a bare `print()`, and the hook contract is explicit: *"For most events, stdout is written to
  the debug log but not shown in the transcript. The exceptions are `UserPromptSubmit`,
  `UserPromptExpansion`, and `SessionStart`."* **PostToolUse is not an exception.** So
  `code-quality`, `error-handling`, `accessibility`, `api-design`, `monitoring`, `i18n`,
  `test-coverage`, `clean-architecture`, `atomic-design`, `terraform`, `design-token` and
  `rails-routes` all detected real violations correctly and threw the result away — reaching
  neither Claude nor you. They now use `hookSpecificOutput.additionalContext`, the supported
  channel, which the harness delivers as a system reminder beside the tool result.
  **This is the single change that makes the plugin's conventions arrive automatically** — and,
  since a plugin cannot ship `.claude/rules/`, hooks are the only component that can do it.
- **`notice_once()` was silent** — the helper whose docstring argues *"silent failure is invisible
  failure"* used the same bare `print()`, so `auto-format`'s "rubocop is not installed" notice
  reached nobody. Routed through `emit()`.
- **`hook_error()` was silent** — the helper that exists so *"a dead gate cannot masquerade as a
  green one"* announced a crashed checker into the void. It now returns its line for the caller to
  emit (the dispatcher emits once, so emitting inside its loop would have put a second JSON object
  on stdout and broken the hook).

### Changed

- **Docs: `std-*` skills are described as *scoped*, not *auto-loaded* — 59 corrections across 29
  files.** `paths:` **limits** eligibility; it does not inject. Verified by test, not read off the
  docs: in a fresh session with the plugin live, writing *and* reading a `.rb` matching four
  skills' globs loaded none of them. The old wording — *"auto-load by file path"* — was accurate
  for the `.claude/rules/*.md` these skills were converted from, and that conversion was **forced**
  (a plugin cannot ship `rules/`). The sentence outlived the mechanism.
  **What this means for you:** nothing changes about what the skills contain; what changes is the
  promise. Rules that must hold whether or not a skill is read are the hooks' job — which is why
  the fix above matters.
- `test_file_scoped_hooks_name_a_loadable_skill` asserted a hook-named skill must declare `paths:`,
  on reasoning that inverted the mechanism (no `paths:` = eligible **everywhere**, the most
  reachable state). It now checks the real invariant: **if** a skill declares `paths:`, they must
  cover the files the hook fires on.



## [3.0.0] - 2026-07-15

**MAJOR because this release changes what gets denied and removes a gate.** Read the *Breaking*
section before upgrading — per the preamble above, that is this file's job.

### Breaking

- **New denial: `redis-cli` FLUSHALL/FLUSHDB against a remote host.** On this stack Redis is *both*
  the Rails cache backend *and* the Sidekiq queue store, so flushing production does not clear a
  cache — it **destroys every enqueued job**, irreversibly and with no error. `incident-responder`
  holds Bash and its own protocol said *"clear stuck queues only as last resort (loses jobs)"*;
  that parenthetical was the only thing in the way, and prose is not enforcement.
  **Scoped deliberately:** the block requires a remote target (`-h`/`-u`, no localhost in the
  segment). `redis-cli FLUSHALL` on a dev box is untouched, and read-only production commands
  (`GET`, `INFO`, `LLEN`) still work — an incident responder must be able to diagnose.
  **If a script of yours runs a remote FLUSH, it will now be denied** with a message naming the
  remedy (run it manually, outside Claude Code).
- **Removed: `monitoring-checker.py`'s `request_id` warning.** It warned when a log line did not
  literally contain `request_id` — but that id is attached by Rails via `config.log_tags`, so it is
  **not in the source line at all**. Every correctly-configured app tripped it on every
  parenthesised `Rails.logger.info(...)`, and no per-call edit could ever fix a misconfigured one:
  the remedy is one line of config. It was also dead for the dominant idiom (its pattern required
  whitespace after the method name). **If you relied on this warning, you were relying on a false
  positive** — the mechanism now lives in `std-monitoring/references/request-tracing.md`.
  `monitoring-checker.py` still checks for sensitive data in logs, which *is* a property of the call
  site.
- **`std-error-handling` now auto-loads.** It shipped with no `paths:`, so it loaded on **nothing,
  ever** — while `error-handling-checker.py` named it as the remedy five times. It now auto-loads on
  `**/*.{rb,py,ts,tsx,js,jsx}` (mirroring that hook's own scope). **Expect more context per task on
  those files.**
- **`compliance-auditor`'s output format changed.** It signed Claude as **"Auditor"** on a
  "Compliance Audit Report" with a *Compliant* count. It is now a **readiness self-assessment**:
  *prepared by* (unverified), a **required** named human reviewer, and evidence-based statuses
  (*Evidence found* / *No evidence in scope*) rather than compliance determinations. **If you parse
  or template its output, it has changed shape.** A SOC 2 attestation comes from a licensed CPA
  firm; a repo-reading agent cannot make that determination and no longer implies it can.

### Added

- **`rails-routes-checker.py`** — warns when `Sidekiq::Web` is mounted with no authentication. An
  unwrapped mount publishes every job's *arguments* (user ids, emails, tokens ride along routinely)
  and lets any visitor retry or kill jobs. It reads `config/initializers/` before warning, because
  the idiomatic protection for an **API-only** app is `Sidekiq::Web.use Rack::Auth::Basic` there,
  not in `routes.rb` — a routes-only check would have flagged correctly-secured apps.
- **`refactor-specialist` gained `Bash`.** It held Write/Edit and no Bash while its protocol
  demanded *"Run the test suite"* and a *"pass/fail count"* — full power to mutate, none to verify,
  and the only way to comply was to invent the number. It was the only agent in the plugin that
  could write but not verify. It must now never report a test result it did not observe.
- **All 13 agents are wired to their references** (was: 9 of 13 pointed at nothing, against 116
  reference files). Plus new gates: the token registry, the error envelope's single shape, agent
  capability/pointer resolution, the palette recipe's contrast caps, required-tag parity, and the
  Centrifuge API. **246 tests, up from 214.**

### Fixed

- **13 preset contrast pairs shipped below WCAG AA** — worst `--success` at **2.54:1** against a
  4.5:1 requirement. An earlier fix corrected `design-tokens.md` and gated it, but the gate **read
  one file**: `theme-presets.md` carried the same defaults, copied, and kept them. Presets exist to
  be pasted wholesale. **If you copied a preset, re-copy it.** Traced upstream to the generator:
  `brand-identity`'s recipe prescribed lightness ranges with **no foreground named**, and the entire
  Success and Info ranges fail against near-white — the recipe was the bug and the palettes
  inherited it. Now foreground-aware caps, gated.
- **Design tokens that compiled to nothing.** `bg-destructive` is not a token on this stack —
  `error` is registered, `destructive` is not — so it emitted **no CSS at all**, silently: a Delete
  button rendered transparent with inherited text. Same for `bg-neutral` (`muted` is the registered
  one), in the rule literally titled *"Atoms Must Use Design Tokens"*. `destructive`/`neutral` remain
  valid variant **keys**; only the token names changed. Gated.
- **The API error envelope had three incompatible shapes** across four files — `error` as string vs
  object, `code` as HTTP status vs machine-readable string, `details` as object vs array,
  `request_id` vs `requestId`. `std-error-handling` said *"do not duplicate"* thirty lines after
  duplicating it. One shape now: `error`, `code`, `status`, `details`, `requestId`, owned by
  `std-api-design`. Gated.
- **`api-design-checker.py` flagged correct code.** It grepped for the substring `request_id` and
  told you to add it — to an API whose stated convention is **camelCase**. It passed canonical code
  only by luck (`requestId: request.request_id` carries the substring on the *value* side). It now
  matches key positions and distinguishes absent from present-but-snake_case.
- **`api-designer` taught a default page size of 20**; `std-api-design` owns it at **25** and said so
  three times. The odd family out was the one a designer actually opens. It also taught offset
  pagination as the simple default when the owner's rule is *cursor by default*.
- **Two design agents globbed hardcoded wrapper directories** (`web/`, `mobile/`, `backend/`) in a
  plugin whose central monorepo claim is wrapper-agnosticism — so in any repo not using those names
  they found nothing and **reported clean**. Fabricated coverage is worse than an error.
- **`react-native-dev` taught a Centrifugo hook that could not run** — `centrifuge.subscribe(channel)`
  is not this client's API (`getSubscription() ?? newSubscription()` is), and the shape it taught
  had the exact handler-stacking leak its own reference exists to prevent.
- **`web-design-guidelines` shipped none of its advertised "100+ rules"** — it fetches them from an
  unpinned third-party URL. It now **fails closed** to the pinned local skills rather than reviewing
  from training data, and names each finding's source.
- Plus: `deploy` 357→232 (its frontend half was a drifted copy whose HSTS had lost
  `includeSubDomains; preload`), `doc-generator` 334→50, `test-generator` 316→215, and CLAUDE.md's
  own description of three hooks (two claimed to be **Haiku agents**; both are deterministic command
  hooks that spawn no model).

## [2.0.0] — 2026-07-15

**MAJOR — this release denies work that previously succeeded.** The version is what you pin, and
`1.0.0` had gone stale: it was declared once at the plugin conversion and never moved while the
deny floor, the gates, and the skills all changed underneath it. Per the plugin's resolution
rules, that meant installed users received **none** of it. This release is the first that can
actually be delivered.

**Two things to do when you take it:**

1. **Copy the 6 new Terraform denies** into your project's `.claude/settings.json` (see
   *Permission floor* below). A plugin cannot ship `permissions`. The SessionStart sentinel will
   name the missing rules on every session until you do.
2. **Expect `terraform apply` to ask, and `terraform destroy` / `state rm|mv|push` /
   `force-unlock` / `apply -auto-approve` to be **denied**. If that breaks a workflow, that is
   the intended change, not a bug — read the reason, which names the remedy.

**Pin it** (the `/plugin marketplace add` form floats on `main`):

```json
{ "name": "sdh",
  "source": { "source": "github", "repo": "Kaakati/sdh-claude-skills", "ref": "v2.0.0" } }
```

### Fixed
- **The commit gate blocked on a list you couldn't read in full.** `pre-commit-check.py` accepts
  **11** conventional-commit types and denies everything else, pointing you at
  `std-git-workflow` — which documented **10** (and CLAUDE.md, 9). `revert:` worked but was named
  nowhere, so the only way to discover it was to be denied first. Both are now complete, the
  skill states that its table **is** the accepted set, and a test parses the hook's regex against
  that table and fails on drift **in either direction** — including the worse one, a documented
  type the hook would reject. (Verified: nothing documented was ever blocked.)
- **The auto-format hook silently applied *unsafe* RuboCop corrections (BEHAVIOURAL).** It ran
  `rubocop --autocorrect-all`, which RuboCop's own CLI documents as *"Autocorrect offenses (safe
  and unsafe)"* — against a default config marking **53 cops `SafeAutoCorrect: false`**, i.e.
  corrections its maintainers flag as able to change behaviour. The hook runs unattended on every
  `.rb` write with its output discarded, so those rewrites landed on code nobody re-read. It now
  runs `--autocorrect` (**safe only**); `-A` stays a deliberate human action where you read the
  diff. **If you relied on unsafe autocorrections happening automatically, they no longer do** —
  run `bundle exec rubocop -A` yourself. A new test fails the build if any unattended formatter
  regains an unsafe flag.
- **7 hooks warned you without saying where the rule lives.** `security-scan`, `pre-commit-check`,
  `terraform-checker`, `terraform-command-gate`, `atomic-design-checker`, `design-token-checker`
  and `dangerous-command-blocker` all named a remedy but no skill — so a developer hit by the
  design-token checker had nowhere to learn *why*. Eleven other hooks pointed at a skill; these
  seven pointed at nothing, which reads as arbitrariness. All 7 now name the skill that carries
  the rule, and the test that guaranteed *"a named skill must exist"* now also guarantees *"a skill
  must be named"* (with `auto-format` exempt — it names an install command, which is the real
  remedy).
- **The code-quality hook warned at a number its own skill never stated.** It warns at **200
  lines** for Rails models and UI components (300 elsewhere) and points you at
  `std-code-standards` — which said only *"Target maximum 300 lines"*. Write a 250-line model,
  read the skill you were sent to, get warned anyway, conclude the hook is noise. The number was
  documented in `CLAUDE.md` and the always-on skill, but **a plugin's `CLAUDE.md` is not shipped
  to consumers**, and the skill the hook *names* is the one that must carry it. `std-code-standards`
  now states both limits, the wrapper-agnostic paths they apply to, why models/components get the
  tighter one, and that all four limits are **advisory, never blocking**. A new test imports the
  hook's constants and fails CI if any of them stops appearing in the skills that document them.
- **`code-reviewer` could not catch a single bug this release fixed.** Its stack checks were one
  line each and predated every verified defect. It now greps for the five that fail *silently* —
  a policy that exists but is never called (`policy_scope` filters, `authorize` does not), a
  migration with no `lock_timeout`, a `remove_column` with no prior `ignored_columns` deploy, a
  non-bang `create` inside a transaction (commits half), and a money job with no explicit
  `sidekiq_options retry:`. Also fixed a contradiction in its own guide: the model *"idempotent
  job"* taught `return if order.charged?` as the answer (a race-prone guard, not the correctness)
  and carried no retry policy — so the repo's exemplar job silently inherited 25 retries over ~20
  days on a payment.
- **14 reference files (2,298 lines) that nothing could ever load.** `api-designer`,
  `code-reviewer`, `incident-response`, `nextjs-dev`, `onboarding`, `performance-profiler`,
  `reactjs-dev`, `security-auditor` and `test-generator` all shipped `references/*.md` that their
  SKILL.md never named — and no agent named them either. Tier 1 is the catalog: if the body does
  not name the file, the model never learns it exists, so it is never loaded however good it is.
  `code-reviewer`'s `pr-review-guide.md` held exactly the N+1, migration-safety and Sidekiq checks
  the reviewer needed, unreachable the whole time. All 14 are now indexed with descriptions drawn
  from their real contents, and **`skills-lint` now fails when a reference is not named by its
  body** — the mirror of the existing check that a named reference must exist. Both directions
  now hold: 0 pointers without a file, 0 files without a pointer.
- **An AAA accessibility criterion was sold as AA.** `std-accessibility` said *"WCAG 2.2 adds 7
  success criteria … All are required for AA compliance"* and listed **2.4.13 Focus Appearance**
  as AA. WCAG 2.2 adds **nine** (and removes 4.1.1 Parsing), and W3C states 2.4.13 is
  **Level AAA**. Holding a team to a stricter bar than the standard, while telling them it *is*
  the standard, is how governance gets disabled. The requirement stays — the design system already
  ships the focus ring — relabelled honestly as a **house rule** above AA, in all 4 places across
  `std-accessibility` and `accessibility-auditor`.
- **A payment job that retried for ~20 days.** The repo advised *"configure `retry_on` for
  transient errors"* — an ActiveJob API — and its canonical Rails pattern used
  `retry_on ..., attempts: 5` on a **payment** job. Per Sidekiq's own wiki, `retry_on` caps
  nothing: ActiveJob retries first, then *"kick[s] the job back to Sidekiq, where Sidekiq's
  retries with exponential backoff will take over"* — the default being *"25 retries over
  approximately 20 days."* That job charged 30 times across three weeks. Both are fixed to a
  single `sidekiq_options retry: 5` (which works on ActiveJob classes and does not stack), plus
  `sidekiq_retries_exhausted` so a dead job is not silent.
- **`db-migration` taught a table rewrite that does not happen — and the migration hook flagged
  correct code.** The guide was raw SQL with MySQL branches (`pt-online-schema-change`, `gh-ost`)
  in a Rails/PostgreSQL-only stack, and it labelled `ADD COLUMN ... NOT NULL DEFAULT 'x'` as
  *"rewrites entire table"*, prescribing a batched-backfill dance for it. Postgres is explicit
  that a **non-volatile default requires no rewrite** and is *"very fast even on large tables"* —
  so the guidance cost teams a multi-step migration for free work, while never mentioning what
  does rewrite (**volatile** defaults, stored generated columns, identity columns) or that
  `SET NOT NULL` *"requires scanning the table"* under an exclusive lock. Both files are now
  ActiveRecord against PostgreSQL, led by a what-actually-locks table sourced from the docs, and
  carry the Rails traps the SQL version could not (`ignored_columns` before a drop,
  `add_foreign_key validate: false` → `validate_foreign_key`, `unscoped` backfills).
  **`migration-validator.py` is corrected too:** it called `remove_column` in `change`
  irreversible — but `remove_column :orders, :status, :string` **is** reversible and is the
  recommended form, and `rename_column` is reversible as well. It now flags only the genuinely
  irreversible forms, warns about `rename_column` for the real reason (it breaks running
  instances mid-deploy), and drops a hard-coded `backend/` path that contradicted
  wrapper-agnostic detection.
- **37 hook messages sent you to files that do not exist.** Converting `.claude/rules/*.md` into
  `std-*` skills left every hook still saying *"per `accessibility.md`"*, *"per `security.md`"*,
  *"per `database.md`"* — 37 pointers across 10 hooks, none of which resolved. The hooks fired
  correctly and then sent the reader nowhere, which is the one thing a deny reason must never do:
  it is *"your plugin's user interface, and the only part most users will ever read."* Every
  message now names the skill that actually carries the rule (e.g. *"per the `std-accessibility`
  skill"*), and a new test fails the build if any hook names a `.md` file or a `std-*` skill that
  does not exist.
- **`std-database` was written for a stack this repo does not use.** Every example was `knex` /
  TypeScript — a Node query builder absent from the stack — in a Rails + PostgreSQL repo, with
  **zero** ActiveRecord content. Restacked to ActiveRecord, and the rewrite adds what the Rails
  idiom actually gets wrong: `create!` vs `create` inside a transaction (the non-bang form returns
  `false`, so the block completes and commits half the operation), `after_commit` vs `after_save`
  for Sidekiq/Centrifugo, `includes`/`preload`/`eager_load` + `references`, and Panko serializers
  as where N+1 hides. *(`db-migration` has the same defect — raw SQL with MySQL branches — and is
  recorded as a P2 backlog item rather than rushed into the same pass.)*
- **The README's agent table advertised a "Plan" mode that does not exist.** `permissionMode` is
  silently ignored for plugin-shipped agents and was removed from the agents themselves, but the
  table still listed 4 agents as "Plan". The column is now **Capability**, generated from each
  agent's actual `tools` list — and it counts `Bash` as write access (Ch. 8, the Bash hole), so
  `security-auditor` and `incident-responder` read **Read-write**, not the reassuring label their
  "audit" framing invites. `plugin.json` also under-counted the plugin's own contents.
- **A missing formatter is no longer silent.** `auto-format.py` already exited 0 when `rubocop` /
  `prettier` / `black` / `terraform` was absent — correct, but silent, so you watched formatting
  never happen with no way to learn why. It now prints one line naming the binary and its install
  command, **once per session**, then stays quiet. A formatter that fails to *run* is reported the
  same way instead of being swallowed. Nothing is blocked either way.
- **`react-native-best-practices` was advertising the wrong priorities.** Its body had collapsed
  the skill's 14 canonical sections (`rules/_sections.md`) into 8 invented ones: **Core Rendering
  — CRITICAL, "violations cause runtime crashes or broken UI" — was missing entirely**, List
  Performance was promoted HIGH→CRITICAL in its place, and Monorepo was relabelled LOW→MEDIUM.
  The body is what the model reads, so guidance drawn from this skill was mis-prioritised. All 14
  sections are now restored with their canonical impacts, each carrying its rationale and rule
  prefix. `react-best-practices`, `composition-patterns`, `atomic-design` and `terraform` were
  checked and were already correct — no change.

### Added
- **`/toolchain` skill** — linters, formatters, type-checkers and compilers: the four tiers
  (format / lint / typecheck / build) and why most toolchain arguments compare tools from
  different ones; **safe vs unsafe autocorrect**; **checking a tool is installed without
  installing it** (a global install is a machine-level change that often makes CI parity *worse*
  by shadowing the pinned version); `bundle exec` / `pnpm exec` because a bare `rubocop` is a
  different program; and `tsc --noEmit` as the check most CI omits — **Vite and Next do not
  typecheck**, so a type error can pass dev, build, and a green CI. 2 references: a doctor script
  that reports rather than fixes, and per-stack lint/typecheck/build with the prettier-vs-eslint
  boundary.
- **`/mcp-advisor` skill + `mcp-install-gate.py` hook (ACTION: expect a new prompt).** Adding an
  MCP server now **asks first** — on `claude mcp add`, `add-json`, `add-from-claude-desktop`, and
  any write to `.mcp.json`. It stays silent on `list`/`get`/`remove`. The reason: an MCP server is
  not a library. A library is text you *run*; an MCP server is text the model *obeys* — its tool
  descriptions are prompts, and the docs warn that *"servers that fetch external content can
  expose you to prompt injection risk."* The skill covers discovery (start with the reviewed
  Anthropic Directory), the vetting bar (named publisher, **pinned** not `@latest`, least
  credential, scope matching blast radius), and why `--scope project` is a decision about your
  teammates — it writes a committed `.mcp.json` they see as `Pending approval`. Also flags that
  `headersHelper` executes arbitrary shell commands, so a `.mcp.json` in a PR is code, not config.
  Its honest counsel: **prefer the CLI you already have** — `gh` runs under the gates that exist.
- **`std-nextjs` now states its version target: Next.js 15+ / React 19**, with a 14-vs-15 table of
  what changed (`fetch` and `GET` Route Handlers no longer cached by default; the Client Router
  Cache no longer reuses page segments on `<Link>` navigation; `cookies`/`headers`/`params`/
  `searchParams` are now **async**). The skill's code was already 15-correct — this pins the
  contract, per the repo's own *pin every version* rule, and explains why `references/caching.md`
  always states `next: { revalidate, tags }` explicitly rather than relying on a default that
  reversed between majors.
- **`std-error-handling/references/background-jobs.md`** — Sidekiq's real semantics, previously at
  zero coverage: the **25 retries over ~20 days you never configured**, `retry: 0` (to the Dead
  set, kept and retryable) vs `retry: false` (**discarded**, no record), the Dead set as silent
  failure (10k jobs / 6 months), ActiveJob vs `include Sidekiq::Job` (*"about 30% overhead"*), why
  rescuing inside a job **disables the retry** while reporting success, and why timeouts are what
  make retries meaningful at all.
- **`std-monitoring/references/request-tracing.md`** — `request_id` was referenced by **11 files**
  (two hooks *warn* when it is missing; `log-search` builds its whole trace workflow on it) and the
  mechanism was documented in **none**. Now: Rails already generates it
  (`ActionDispatch::RequestId` adopts the load balancer's `X-Request-Id` or makes a uuid, and
  returns it to the client), `config.log_tags = [:request_id]` tags every line — and the part
  everyone misses, **the trace breaks at the async boundary**: a Sidekiq job has no request, so the
  id is `nil` exactly where you need it. Includes the client/server middleware, the `ensure` reset
  (Sidekiq reuses threads — a leaked id mislabels the *next* job), and a one-`curl` end-to-end
  proof. Note the id is **outside input** (Rails sanitizes it because clients can send it) — never
  interpolate it into SQL.
- **`std-database/references/locking-and-timeouts.md`** + `lock_timeout` in the body — the
  mechanism behind most migration outages, previously at **zero coverage**: `ALTER TABLE` needs
  `ACCESS EXCLUSIVE` (which *"conflicts with locks of all modes"*, and *"only an ACCESS EXCLUSIVE
  lock blocks a SELECT"*), a transaction *"will wait indefinitely for conflicting locks"*, and
  queries arriving after it queue behind it — so a millisecond-fast migration becomes a full table
  outage for as long as an unrelated slow query runs. **`lock_timeout` defaults to 0: wait
  forever.** Covers the retry loop, `disable_ddl_transaction!` and its invalid index,
  `pg_blocking_pids()`, and advisory locks — plus the Postgres subtlety that `lock_timeout` must
  be *smaller* than `statement_timeout` or it never fires.
- **`/log-search` skill** — reading production logs, which the repo could emit but never query:
  `Logs Insights`, `aws logs tail`, `gcloud logging read` and `Cloud Logging` were all at **zero
  coverage** while `std-monitoring` covered structured logging and alarms. Both clouds bill by
  **data scanned**, so the skill leads with narrowing (AWS's own guidance: *"Always specify the
  narrowest possible time range"*), then the four questions that answer most incidents. 2
  references: CloudWatch Insights QL (discovered `@`-fields, `bin()` histograms, `parse` as a
  workaround not a destination, the async `start-query` → `get-query-results` dance, retention as
  an explicit decision) and GCP Cloud Logging (LQL is a **boolean filter, not SQL** — there is no
  `stats`, aggregation is a log-based metric; `:` means *contains* and `=` means *equals*; and the
  sink whose writer identity was never granted permission, which looks configured and exports
  nothing).
- **`std-infrastructure/references/github-actions.md`** — workflows as supply chain. A
  third-party action is code you run with your `GITHUB_TOKEN`, and **`@v4` is a mutable tag, not
  a version** (the mechanism behind the `tj-actions/changed-files` compromise) — pin to a full
  SHA and let Dependabot bump it. Also `permissions` least privilege, `concurrency` (with
  `cancel-in-progress: false` for deploys — cancelling a half-applied migration is worse than
  queueing), reusable workflows vs composite actions, environments as the human gate, and the
  `pull_request_target` hole.
- **`std-infrastructure/references/gcp-secondary-cloud.md` rewritten** (39 → 156 lines) around
  **Workload Identity Federation**. The repo was internally inconsistent: keyless OIDC for AWS,
  but a downloaded service-account key for GCP. Google: *"Workload Identity Federation is
  recommended over Service Account Keys as it obviates the need to export a long-lived
  credential."* Includes the `attribute_condition` that scopes the provider to your repo —
  without it, **every GitHub Actions run on the internet** can assume your service account. The
  AWS-primary stance and the "unavoidable key → AWS Secrets Manager" rule remain, as the
  documented fallback rather than the default.
- **`/mobile-signing` skill** — iOS/Android signing identity management, ordered by blast radius
  rather than workflow, because one failure here is permanent: losing an Android **app signing
  key** while not enrolled in Play App Signing means *"you will not be able to release new
  versions of your app to users as updates"* and *"you cannot regenerate a previously generated
  key."* 3 references: Apple certificates/App IDs/profiles/`.p8` keys/fastlane match (including
  why **revoking a certificate to troubleshoot** invalidates every profile built on it), Android
  upload key vs app signing key + Play App Signing enrolment and upload-key reset, and holding
  these secrets in CI (base64 → `RUNNER_TEMP`, ephemeral keychains, `match(readonly: true)`, and
  the `pull_request_target` hole).
- **`/mobile-beta-release` skill** — shipping betas to testers. Leads with the asymmetry that
  breaks release plans: TestFlight **external** requires Beta App Review (*"have your first build
  already approved by App Review for TestFlight"*) while Play **internal testing** has no review
  gate, so the two platforms do not land together. Also covers the **90-day TestFlight build
  expiry**, internal (≤100 role-holders) vs external (≤10,000), Play track API names
  (`alpha` = closed, `beta` = open), promoting the *same artifact* rather than rebuilding, staged
  rollout and how to halt one — and that there is no rollback, only a higher `versionCode`.
  3 references incl. ready-to-use fastlane lanes.
- **`std-react-native` gains two references** for pillars it previously asserted without a
  mechanism. `references/offline-and-mutations.md`: queuing offline mutations is free, but
  surviving an app kill is not — only mutation *state* is persisted, so a resumed mutation dies
  with `No mutationFn found` unless `queryClient.setMutationDefaults` is registered at module
  scope before hydration; plus NetInfo → `onlineManager` and idempotency keys generated once at
  the call site. `references/realtime-centrifugo.md`: `newSubscription()` **throws** if the
  channel is already registered (what every remounting screen does — use
  `getSubscription() ?? newSubscription()`), `unsubscribe()` does not remove listeners, the
  socket does not backfill on reconnect, and `getToken` beats a static `token`.
- **`std-rails-conventions/references/authorization.md`** + access-control rules in
  `std-security` — the repo documented Pundit *policies* in 10 files but never how to guarantee
  one is **called**. A controller action that forgets `authorize` raises nothing and returns
  `200 OK` with another user's data (OWASP #1, Broken Access Control). Both skills now carry
  Pundit's own enforcement (`after_action :verify_authorized` / `verify_policy_scoped`, off by
  default), `policy_scope` vs `authorize` for collections, 404-not-403 for non-owners, and
  `devise-jwt` revocation (`JTIMatcher` + unique `jti`) — without a strategy, sign-out leaves the
  token valid until it expires.
- **`release-hygiene` CI job + [`docs/releasing.md`](docs/releasing.md)** — the plugin's `version`
  is the delivery handle, and the plugin docs are blunt about it: *"pushing new commits without
  changing that string does nothing for existing users."* CI now fails when plugin content has
  changed since the newest release tag without a version bump, and verifies on a tag push that the
  tag, `plugin.json`, and the CHANGELOG agree and `[Unreleased]` was drained. The doc covers
  pinning (`ref`/`sha`), release channels, and the required branch-protection posture.
  **How to pin:** point a marketplace entry at a tag —
  `{"source":"github","repo":"Kaakati/sdh-claude-skills","ref":"vX.Y.Z"}`. The README's
  `/plugin marketplace add` form floats on `main`.
- **`/monorepo-architect` skill + `monorepo-architect` agent** (Opus, read-only) — monorepo
  architecture and management: workspace layout by deployable unit (`apps/`/`packages/`/`tooling/`),
  dependency boundary enforcement (ESLint `no-restricted-imports`, Nx tags, packwerk), task
  orchestration and caching (Turborepo/Nx/Bazel selection, with Bazel called out as rarely worth
  its cost below ~50 engineers), affected-only CI with remote cache and merge queue, one-version
  policy (and the deliberate React Native pin exception), per-app release tagging with Changesets,
  and generating a shared `api-client`/`types` package from the Rails schema so web and mobile
  cannot drift. 6 references, loaded on demand.
  **This is distinct from [`docs/monorepo-setup.md`](docs/monorepo-setup.md)**, which covers Claude
  Code *configuration* for a large repo (CLAUDE.md layering, excludes, worktrees). The `apps/`
  layout keeps `std-*` auto-loading intact — detection is wrapper-agnostic — though shared
  `packages/` match no framework structure and need a per-package `CLAUDE.md`.
- **`SDH_PROTECTED_BRANCHES`** — the branch names the direct-push and force-push gates protect are
  now configurable (default `main,master,develop`, unchanged). Previously hard-coded, so a repo
  whose trunk is named anything else was **silently ungated**. Set it in your environment:
  `export SDH_PROTECTED_BRANCHES="trunk,staging"`. A blank value falls back to the defaults rather
  than unprotecting everything; branch names are regex-escaped, so `release/v1.0` is safe.
- **`.github/scripts/check_rule_taxonomy.py`** + a `skills-lint` CI step — fails the build when a
  skill body drifts from its `rules/_sections.md`, when a section's prefix matches no rule file,
  or when a rule file on disk is claimed by no section. Run it locally with
  `python3 .github/scripts/check_rule_taxonomy.py`. Contributor-facing: **edit `_sections.md`, not
  the body's table.** Heading numbering is not enforced — both `### 1. Atoms (HIGH)` and
  `### Atoms (HIGH)` are accepted.
- **Layer 4 · Permission floor (ACTION REQUIRED)** — 6 new deny rules for irreversible Terraform.
  Copy these into your project's `.claude/settings.json` `permissions.deny`:
  ```
  Bash(terraform destroy:*)      Bash(terraform state mv:*)
  Bash(tofu destroy:*)           Bash(terraform state push:*)
  Bash(terraform state rm:*)     Bash(terraform force-unlock:*)
  ```
  Floor size: **24 → 30**. Previously `terraform destroy`, `state rm` and `force-unlock` were
  **completely ungated**.
- **Layer 3 · `terraform-command-gate.py`** — new PreToolUse three-tier gate (Ch. 10 Pattern 3).
  **Behavioural change:** `terraform destroy`, `state rm/mv/push`, `force-unlock` and
  `apply -auto-approve` are now **denied**; `terraform apply` now **asks** with a review checklist;
  the read-only surface (`plan`, `validate`, `fmt`, `output`, `state list|show`) is unaffected.
  `terraform plan -destroy` is explicitly **allowed** — it only previews. Fail-closed.
- **Layer 4 · Sentinel staleness detection** — the SessionStart sentinel now diffs your floor
  against the plugin's own reference floor, so it reports a **stale** floor (copied from an older
  version) and names the exact missing rules — not just an absent one.
- **Layer 7 · CI** (`.github/workflows/ci.yml`) — the plugin now runs its own gates: hook fixture
  suite, manifest/structure validation, skill+agent frontmatter lint, tier discipline (every rule
  indexed, no monolith pointers, all references resolve), and a sentinel-presence guard.
- **Layer 1 · Progressive disclosure** — 7 dense `std-*` skills split into a tight body + 28
  decision-shaped, example-paired references (~9.3k lines of tier-3 that cost nothing until needed).
- **Storytelling UI framework** — `skills/ui-ux-patterns/references/storytelling-ui.md`, applied
  across the UI/UX skills.

### Changed
- **Layer 3 · `deployment-gate.py` no longer decides Terraform** — `terraform-command-gate.py` owns
  that surface. Previously both fired: two prompts for one `terraform apply` (approval fatigue), and
  contradictory decisions on `-auto-approve` (ask vs deny).
- **Layer 3 · Hook dispatch consolidated** — 12 advisory checkers now run in one process via
  `post-edit-dispatch.py` (13 PostToolUse entries → 2). Same warnings, ~12 fewer Python cold-starts
  per edit.
- **Layer 1 · Rule-per-file granularity restored** — 5 skills pointed at compiled `full-guide.md`
  monoliths (up to 2934 lines); their bodies now index `rules/<id>.md`, so a task loads one ~60-line
  rule instead of skimming a monolith.
- **Layer 1 · Wrapper-agnostic detection** — conventions load by canonical structure + marker files
  (`Gemfile`, `next.config.*`, `vite.config.*`, `metro.config.js`), **not** by a forced directory
  name. Rails works under `backend/`, `api/`, or the repo root. Directory names are no longer a
  contract.

### Fixed
- **Layer 3 · Silent failure eliminated (important)** — advisory hooks failed **open and silently**,
  so a crashed checker was indistinguishable from a passing one and could enforce nothing, forever,
  with every signal green. All fail-open paths now emit `HOOK ERROR: <checker> failed …`.
  `audit-logger` was the sharpest case: a failed write left **invisible holes in the audit trail**
  plus false confidence it was complete.
- **Layer 2 · The Bash hole** — `clean-architecture` carried `Bash` (write access via `sed -i`) but
  never used it → removed; it is now read-only by capability. `security-auditor` keeps Bash (it
  needs `git diff`/`npm audit`) but no longer implies read-only.
- **Layer 1 · terraform index drift** — the body named **26 rules that had no file** while **26 real
  rule files were invisible**. Regenerated from the real files; CI now guards it.
- **Cross-platform** — hooks emit valid UTF-8 on Windows (`PYTHONUTF8=1`); `.gitattributes` pins
  `*.sh` to LF so `run-python.sh` works under Git Bash/MSYS2.

### Removed
- **The last 3 compiled `full-guide.md` monoliths (6,777 lines)** — `react-best-practices` (2934),
  `react-native-best-practices` (2897), `composition-patterns` (946). **No content lost and no
  behaviour change:** all three were already unreferenced by their bodies (nothing loaded them),
  and their section preambles were copies of `rules/_sections.md`, which remains. Every rule keeps
  its own `rules/<rule-id>.md` with its bad/good pair. This removes a drift source — the same one
  that had already rotted `react-native-best-practices`' section table.
- **`permissionMode` from all 10 agents that carried it** — the field is silently ignored for
  plugin-shipped agents, so advertising it was theater. **No capability change:** the 4 former
  "plan mode" agents carry `tools: Read, Grep, Glob` and are read-only by capability, which is the
  real control. Docs corrected (`plan mode` → `read-only`); CI now rejects `permissionMode`,
  `hooks`, and `mcpServers` on agents, and any agent without a `tools` list.

### Known gaps
- 13 `std-*` skills are still single-file; several references exceed the ~300-line budget.

---

## [1.0.0] — 2026-07-15

### Added
- Initial release as a Claude Code plugin: 58 skills (37 workflow + 20 `std-*` convention +
  `sdh-engineering-standards`), 12 agents, and quality-gate hooks.
- SessionStart **sentinel check** — detects the "plugin trap" (a plugin cannot ship `permissions`,
  so an uncopied deny floor is invisible while every other signal says "protected").
- Fail-closed security gates: `security-scan`, `dangerous-command-blocker`.
