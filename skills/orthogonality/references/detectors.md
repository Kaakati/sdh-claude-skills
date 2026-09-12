# Detector catalog

Every detector the `orthogonality` skill ships: what makes it fire, what keeps it quiet, where it
runs in this release, and what it cannot see. Thresholds are starting values. A reported false
positive first becomes a quiet test case in the plugin's trigger-precision matrix; only then does a
threshold move, because a gate that fires on correct work is a gate people learn to ignore.

Resolution guides per family: `@skills/orthogonality/references/database-duplication.md`,
`@skills/orthogonality/references/competing-mechanisms.md`,
`@skills/orthogonality/references/context-maps.md`.

## The finding contract

- **Severity.** `warn` is shown by the edit-time hook and listed by scans. `info` is listed by scans
  only. `note` is a once-per-session operational line (a cold index, an invalid configuration, a
  detector skipped for time). There is no `ask` or `deny` severity.
- **Confidence** is `high`, `medium` or `low`. The hook shows a `warn` only at `high` or `medium`.
- **Evidence.** One line of at most 320 characters: the detector ID and slug; the subject as
  `path:line` and its symbol; the counterpart as `path:line` and its symbol or table; the measured
  signal; the suppression route; the owner skill. The route reads `Keep: sdh:orthogonal-ok <ID>
  <reason>, or <config key> with an ADR.`; on a long line it keeps the marker only, and for a
  `package.json` subject, which cannot carry a comment, it names the config key alone.
- **Fingerprint.** `sha1(detector id + normalized subject + normalized counterpart)`. The hook shows
  a fingerprint at most once per session. Scans list everything.
- **New or frozen.** Findings present in the baseline taken at the first complete index build are
  `new: false`. The hook shows only `new: true`; scans show both, and always print the frozen count.
- **Suppression.** Two routes, both visible in review: an entry in `.claude/orthogonality.json` that
  names an ADR, or an inline `sdh:orthogonal-ok <ID> <reason>` comment. Both →
  `@skills/orthogonality/references/declaring-intent.md`.

## Message shapes

Every hook line starts `ORTHOGONALITY`. Examples:

```text
ORTHOGONALITY [DK1 duplicate-concept] db/migrate/20260911_create_clients.rb:3 declares clients; customers (db/schema.rb:88) is the same concept in context accounts: synonym customer~client, 4 shared columns (J=0.71). Keep: sdh:orthogonal-ok DK1 <reason>. Fix: the `std-database` skill; policy: the `orthogonality` skill.
ORTHOGONALITY [CM1 second-library] package.json:14 adds ky; axios (package.json:11) already covers http_client for this vite deployable (house choice: axios). Remove one, or declare a migration with an until date. Keep: mechanisms.migrations with an ADR. Fix: the `std-reactjs` skill; policy: the `orthogonality` skill.
ORTHOGONALITY [BC3 cross-context-write] billing/services.py:40 updates orders.Order (owned by context orders, declared in .claude/orthogonality.json); orders/services.py:18 is the existing writer. Keep: sdh:orthogonal-ok BC3 <reason>, or contexts.<name>.writes with an ADR. Per the `orthogonality` skill.
ORTHOGONALITY note: the index for this project is not built yet, so duplicate and boundary checks ran on the edited file only. It builds at the next session start, or with the `orthogonality` skill's arch_index.py.
```

The background watcher wakes Claude with a header, the new finding lines and a footer:

```text
ORTHOGONALITY (background): 1 new finding(s) after `npm install ky`:
ORTHOGONALITY [CM1 second-library] package.json:14 adds ky; axios (package.json:11) already covers http_client for this vite deployable (house choice: axios). Remove one, or declare a migration with an until date. Keep: mechanisms.migrations with an ADR. Fix: the `std-reactjs` skill; policy: the `orthogonality` skill.
Full list: the `orthogonality` skill's arch_scan.py.
```

It wakes Claude only when a Bash install, generator or branch switch produced something new,
deduplicated, at most 5 lines per batch. Runner prefixes count: `bundle exec rails g model`,
`uv run alembic revision`, `python -m pip install`, `docker compose run web bin/rails g model`. When
another refresh holds the index lock (the session-start build), it waits up to 15 s, then checks
against the index as it stands, and keeps those files out of the first baseline, so an install made
during the first build is still reported.

## Where each detector runs in this release

"Edit time" is the advisory checker the post-edit dispatcher runs; it parses only the edited file and
looks everything else up in the index. "Scan" is `arch_scan.py` or the per-family script.

| ID | Detector | Edit time | Scan |
|---|---|---|---|
| DK1 | duplicate-concept | `warn`: same context, a name match plus column overlap | `warn`; `info` for name-only, or different inferred contexts |
| DK2 | overlapping-columns | `warn`: same context | `warn` / `info` by Jaccard band |
| DK3 | fact-reachable-through-fk | `warn` | `warn`; `info` for snapshot columns and exact same-name copies |
| DK4 | repeating-group | `warn` at 5+ numbered siblings | `info` at 3–4, `warn` at 5+ |
| DK5 | rule-in-two-places | — | `warn` (Rails) |
| DK6 | copy-paste block | — (no clone data at edit time) | `warn` in business-logic directories, `info` elsewhere |
| CM1 | second-library | `warn`; a single off-house library is quiet | `warn`; `info` for a single off-house or dev-only competitor |
| CM2 | second-client-wrapper | `warn` | `warn` / `info` |
| CM3 | second-error-envelope | `warn` | `warn` |
| CM4 | second-pagination-style | `warn` | `warn` |
| CM5 | second-auth-mechanism | — | `info` |
| BC1 | cross-context-dependency | `warn`, declared contexts only | `warn` declared, `info` inferred |
| BC2 | new-cycle | `warn`: declared contexts, or two inferred sibling folders under one parent | `warn` / `info`; file-level cycles `info` |
| BC3 | cross-context-write | `warn`, declared ownership only | `warn` declared, `info` inferred |
| BC4 | multi-context-transaction | — | `info` |
| MF1 | wrong-context file | — | `info` |
| MF2 | first-of-kind pattern | — | `info` |
| MF3 | EAV table | `warn` | `warn` |
| MF4 | STI bloat | — | `info` |
| MF5 | JSONB key used as a column | `warn` | `warn` |
| TF1–TF3 | Terraform duplication | — | `info` |
| CFG-ADR, CFG-READMODEL, CFG-MARKER | declaration below the bar | `warn` | `warn` |

**When the index is missing** (a new project, a new machine), the edit-time checker says so once
per session and runs only what one file can prove: DK4, MF3, MF5, and CM1 within the edited manifest.
While the first build is still running, its note says so instead; outside a project (no `.git` or
package manifest at the root) no index is ever built. **A file over the 1 MB per-file cap** is not
re-parsed at edit time: a schema, migration, model or manifest is checked from its stored index rows,
any other file is skipped with one note, as the index skips it.
**Past its 1.5 s budget** it returns what it has, plus one `note` naming the detectors that did not run.
**A cycle closed by two files created in the same session** can pass the checker on the closing edit:
the first file's import of a file that did not exist yet stays unresolved until the background
watcher refreshes the index. The BC2 then appears on the next edit to either file, and in every scan.

## Class (a): duplicated knowledge

Normalization, thresholds and remedies for DK1–DK5 → `@skills/orthogonality/references/database-duplication.md`.

| ID | Fires | Quiet |
|---|---|---|
| DK1 | `create_table :clients` (email, phone, first_name, last_name, notes) beside `customers` with the same four columns, one context | the same columns in `customer_imports` (staging table); `clients` and `customers` in two **declared** contexts; `class Client < ApplicationRecord` with no columns yet (name-only is `info`) |
| DK1 (Django) | `class Client(models.Model)` appended beside `Customer` with the same fields in one app | `class CustomerSearch` with `managed = False` on a view (a declared read model); abstract and proxy models |
| DK2 | `contacts` sharing ≥ 4 normalized columns and J ≥ 0.6 with `customers` | address or money groups repeated across unrelated tables (one key each) |
| DK3 | `add_column :orders, :customer_email` while `orders.customer_id` → `customers.email` | `add_column :orders, :shipping_city` (the prefix is not the parent); `unit_price` on `*_items`; `tasks.organization_id` behind a composite FK |
| DK4 | `phone_1` … `phone_5` in one table | `address_line1`, `address_line2`; `sha256`, `utf8`, `oauth2_token`, `v1_payload`; percentiles `latency_p50` … `latency_p99`; a gapped set `slot_2`, `slot_5`, `slot_9` |
| DK5 | `validates :email, uniqueness: true` with no unique index leading with `email` | `uniqueness: { case_sensitive: false }` covered by a `lower(email)` unique index |

### DK6 — copy-paste block (scans and CI only)

- **Trigger.** A clone of at least 70 normalized tokens and 8 lines between two **different** files.
  Tune with `find_duplicates.py --min-tokens` or config `clones.min_tokens`.
- **Mechanism.** Language-aware tokens: Python through the stdlib `tokenize`; Ruby and TS/JS through a
  small lexer for strings, comments, identifiers, numbers and punctuation. Identifiers and literals
  are normalized, so renamed (Type-2) clones match. 25-token k-grams are winnowed into fingerprints.
  This is the technique family of jscpd's Rabin-Karp over tokens and PMD CPD's Karp-Rabin.
- **`warn` only in business-logic directories:** Ruby under `app/services`, `app/models`, `app/jobs`,
  `lib/`; Python `services.py`, `services/`, `models.py`, `tasks.py`, `app/services`, `app/models`,
  `app/tasks`, `src/`; TS/JS under `src/hooks`, `src/api`, `src/domain`, `src/actions`, `src/lib`.
  Elsewhere it is `info`; test files are listed only with `--include-tests`.
- **Quiet.** Migrations, `db/schema.rb`, `structure.sql`, Alembic and Django migration directories;
  generated files and build output; shadcn/ui primitives in the `components.json` `aliases.ui`
  directory; serializers and Pydantic schemas whose only overlap is a field list; config `clones.ignore`.
  A clone **inside one file** is `std-code-standards` territory and appears in scans only.
- **Blind spot.** Token similarity is not the same knowledge. The same rule written two different
  ways is invisible, and two identical blocks can encode different rules. Read both before merging them.

## Class (b): competing mechanisms

Registry, companions, overrides and lint bans → `@skills/orthogonality/references/competing-mechanisms.md`.

| ID | Fires | Quiet |
|---|---|---|
| CM1 | `gem "httparty"` beside `gem "faraday"`; `"requests"` beside `"httpx"`; `"ky"` beside `"axios"`; `"recharts"` in a Vite SPA using `chart.js` + `react-chartjs-2`; `"@reduxjs/toolkit"` beside `zustand`; `sidekiq` beside `solid_queue` | `faraday-retry`, `axios-retry`, `respx` (companions); `recharts` in a Next.js app (its house chart library); a declared migration before its `until` date |
| CM2 | a second `axios.create({ baseURL: import.meta.env.VITE_API_URL })` in a feature folder while `src/api/client.ts` already has one | `axios.create({ baseURL: 'https://api.stripe.com' })` (a different upstream); tests, MSW handlers, SDK wrappers |
| CM3 | a second `@app.exception_handler(Exception)` in a FastAPI deployable | handlers for distinct domain exceptions registered in the one handler module |
| CM4 | `.page(params[:page])` (kaminari) where `pagy(` covers ≥ 80% of ≥ 5 existing uses | fewer than 5 existing uses; a deliberate move to cursors carrying a marker |
| CM5 | `JWT.encode` outside `config/initializers` and the auth module while `devise-jwt` is present | webhook HMAC and JWKS verification (file name contains `webhook` or `jwks`, or a marker) |

### MF2 — first-of-kind pattern (`info`)

The edited file introduces a structural variant whose count in the deployable is 0, while the
dominant variant of the same kind counts at least 5. Kinds: Rails service entry points (`#call` vs
`#perform`/`#execute`/`#run`), result style (house `Result` vs `dry-monads`), serializer base (Panko
vs `ActiveModel::Serializer`), job base, view component base (Phlex vs `ViewComponent::Base`); Python
services as module functions vs classes; class components in a hooks codebase. Quiet where a
framework has two legitimate idioms: Server Components fetch, Client Components use hooks.

## Class (c): boundaries and cycles

Declaring contexts and resolving these → `@skills/orthogonality/references/context-maps.md`.

| ID | Fires | Quiet |
|---|---|---|
| BC1 | `packs/billing/.../charge_order.rb` references `Shipping::RateCalculator`; `packs/billing/package.yml` enforces dependencies and lists none on shipping | the dependency is declared; tests; `import type` and `if TYPE_CHECKING:` imports; `shared_kernel` paths |
| BC2 | `app/billing/service.py` imports `app.orders.service` while orders already imports billing | the new import sits under `if TYPE_CHECKING:`; the cycle was already in the baseline; two inferred contexts that are not siblings (scan `info`) |
| BC2 (TS) | `src/features/cart/useCart.ts` imports `../checkout/useCheckout` while checkout imports cart | `import type { Checkout } from '../checkout/types'` |
| BC3 | `Order.where(id: ids).update_all(status: "refunded")` in a billing service, `orders` owned by the orders context | the same line in a spec; a line marked `# sdh:orthogonal-ok BC3 <reason>`; a declared `writes` exception; config `backfills` paths |
| BC4 | one `transaction do` block persisting models from two contexts | never above `info`: CRUD-heavy Rails and Django code relaxes this rule |
| MF1 | a **new** file in context A with ≥ 70% of ≥ 6 resolved references pointing into B, and at most 1 into A | composition roots (`config/`, `app/main.py`, `urls.py`, router registries), tests, index and barrel files |

## Class (d): schema misfits

| ID | Fires | Quiet | Remedy owner |
|---|---|---|---|
| MF3 | `Attribute(content_type, object_id, key, value)` | `SiteSetting(key unique, value)` with no entity column; feature-flag library tables; `*_translations` | `std-database` ("JSONB sparingly") |
| MF4 | an STI table whose ≥ 4 nullable columns are used by one subclass only (scan) | — | `std-database` (`delegated_type`) |
| MF5 | `Order.objects.filter(data__status="paid")`; `.where("data->>'status' = ?")`; `Model.data["x"].astext == …` | GIN containment (`@>`) over schemaless tags; pgvector and PostGIS operators; a Django lookup through a relation the index knows (`attributes__name` on a ManyToManyField, `details__product` through a `related_name`) | `std-database` |

## Terraform (scans only, `info`)

A stdlib parser cannot compute a plan, so no Terraform detector speaks at edit time.

- **TF1 reimplemented-module.** A local module declares a resource family (`aws_vpc`,
  `aws_ecs_cluster`, `aws_db_instance`) that a registry module used elsewhere in the repo provides.
- **TF2 module-version-divergence.** One registry module `source` pinned to different versions across
  root modules: the one-version policy applied to modules, routed to `monorepo-architect`.
- **TF3 duplicate-singleton.** Two account-singleton resources (an organization `aws_cloudtrail`, an
  `aws_guardduty_detector`) in roots sharing a backend key prefix and environment. `low` confidence.

Module conventions live in `std-terraform-conventions`; secrets, naming, tags, backend and provider
constraints stay with `terraform-checker.py`.

## Declaration findings

- **CFG-ADR** — a declaration names an ADR file that does not exist.
- **CFG-READMODEL** — an `intentional_duplicates` entry of kind `read-model` lacks `source_of_truth`,
  `refreshed_by` or its `writes` statement.
- **CFG-MARKER** — an `sdh:orthogonal-ok` marker with no reason.
- **An invalid file** (wrong `version`, a non-list glob, an unknown relationship name) is a `note`
  naming the JSON path in hooks and exit `2` in scripts.

## What the index can and cannot see

| Stack | Parsed from | Known blind spots (reported in the index `coverage` block) |
|---|---|---|
| Rails schema | `db/schema.rb`; `db/structure.sql` (tables, FKs, indexes, views) | view column lists are not expanded; triggers are listed, not interpreted; with migrations only, a replay (additive, renames and removals in order) |
| Rails code | `app/`, `lib/`, `packs/` Ruby | `constantize`, `send`, metaprogrammed associations; custom Zeitwerk inflections outside `config/initializers/inflections.rb` |
| Django | `models.py`, `models/`, `apps.py`, settings (`ast`) | dynamic `INSTALLED_APPS`; fields added through `add_to_class` |
| SQLAlchemy / Alembic | model modules; `alembic/versions` only when no model maps the table | imperative mappings (`registry.map_imperatively`); renames and unnamed constraints |
| TS/JS | `src/`, `app/`, workspace packages; tsconfig `paths`; `package.json` `exports`/`imports` | `require` with computed strings; bundler aliases not in tsconfig; JS config files, which are never evaluated |
| Manifests | `Gemfile` (+ lock DEPENDENCIES), `package.json`, `pnpm-workspace.yaml` `packages:`, `pyproject.toml`, `requirements*.txt` | `eval_gemfile` and conditional `gem` blocks count as present |
| Terraform | `*.tf` module, resource, provider and backend blocks | `for_each` fan-out; dynamic modules |

The index honours `.gitignore`, skips build output, `node_modules`, `.venv` and config `ignore`, and
caps at 50,000 in-scope files and 1 MB per file. Past a cap it keeps schema, manifests, models and
contexts, and marks `coverage.truncated`.

## Checks this skill never emits

| Check | Owner |
|---|---|
| a model importing a controller or serializer; a service returning HTTP; a domain type importing a framework; a screen or page importing the API client | `clean-architecture-checker.py`, `std-clean-architecture` |
| HABTM; an FK column without an index; `index: false` | `database-design-checker.py`, `std-database` |
| migration reversibility, destructive operations, interpolated SQL | `migration-validator.py`, `db-migration` |
| URL verbs, the `data` wrapper, the error-envelope **keys**, POST status | `api-design-checker.py`, `std-api-design` |
| Terraform secrets, naming, tags, backend, provider constraints | `terraform-checker.py` |
| deep cross-package imports; one-version drift of the same package | `monorepo-architect` |
| file length, function length, parameters, nesting | `code-quality-checker.py`, `std-code-standards` |

## Sources

- Eric S. Raymond — The Art of Unix Programming, ch. 4, "Orthogonality" (Linuxtopia mirror) — https://www.linuxtopia.org/online_books/programming_books/art_of_unix_programming/ch04s02_1.html
- Artima (Bill Venners) — Orthogonality and the DRY Principle: A Conversation with Andy Hunt and Dave Thomas, Part II — https://www.artima.com/intv/dry.html
- arXiv / ICSA 2022 (Li, Soliman, Liang, Avgeriou) — Symptoms of Architecture Erosion in Code Reviews: A Study of Two OpenStack Projects — https://arxiv.org/abs/2201.01184
- Shopify Engineering — Enforcing Modularity in Rails Apps with Packwerk — https://shopify.engineering/enforcing-modularity-rails-apps-packwerk
- TNG Technology Consulting — ArchUnit User Guide (`FreezingArchRule`) — https://www.archunit.org/userguide/html/000_Index.html
- Andrey Kucherenko — kucherenko/jscpd — https://github.com/kucherenko/jscpd
- PMD Open Source Project — Copy/Paste Detector (CPD) — https://docs.pmd-code.org/latest/pmd_userdocs_cpd.html
- pylint-dev — pylint/checkers/symilar.py (duplicate-code R0801) — https://raw.githubusercontent.com/pylint-dev/pylint/main/pylint/checkers/symilar.py
- import-js — import/no-cycle — https://github.com/import-js/eslint-plugin-import/blob/main/docs/rules/no-cycle.md
- Shopify — Shopify/packwerk — https://github.com/Shopify/packwerk
- Django Software Foundation — System check framework reference — https://docs.djangoproject.com/en/stable/ref/checks/
- SQLAlchemy / Alembic — Auto Generating Migrations — https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- Anthropic — Claude Code docs, Hooks reference: Add context for Claude — https://code.claude.com/docs/en/hooks#add-context-for-claude
- Anthropic — Claude Code docs, Hooks reference: Command hook fields (asyncRewake) — https://code.claude.com/docs/en/hooks#command-hook-fields
