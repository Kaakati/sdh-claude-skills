# Competing mechanisms — one concern, one mechanism, per deployable

"One and only one way to change each property" is Raymond's definition of orthogonality. For a
codebase it means one HTTP client, one client-state store, one job system, one error-envelope
builder and one pagination style **per deployable**. Two of them means two sets of retries,
timeouts, auth headers and test doubles, and a reader who cannot tell which is canonical.

A **deployable** is the package root resolved from its manifest (`Gemfile`, `package.json`,
`pyproject.toml`), labelled by the plugin's framework detection: rails, django, fastapi, vite,
nextjs, react-native, or none. A Next.js app and a Vite SPA in one monorepo are two deployables and
may legitimately differ.

## The registry decides what competes

`hooks/_mechanisms.json` is the one machine-readable list. Each row is concern × ecosystem ×
framework labels, with:

- `house` — the chosen packages, possibly several that work together (`react-hook-form` + `zod`);
- `companions` — plugins or adapters of the chosen library that never compete (`faraday-retry`,
  `axios-retry`, `respx`, `@hookform/resolvers`);
- `competitors` — known alternatives;
- `owner_skill` — the skill that owns the concern's convention.

**It covers only concerns where the house states a choice.** The source is "Library preferences"
in `sdh-engineering-standards`, and a harness test fails when the registry and the standards
disagree. A concern the standards do not name has no row, so nothing is detected for it. Rows record
only which package **names** compete, and only direct dependencies count; the convention itself
stays with the owner skill.

**Rows are per framework label**, because the house answer can differ by stack. Charts are the
example: the shadcn/ui chart component (Recharts) in Next.js; Chart.js with react-chartjs-2 in the
Vite SPA; Chart.js through a house Stimulus controller in Rails Phlex views. ApexCharts,
`react-apexcharts` and Chartkick are competitors.

## How CM1 (second-library) decides

| Situation in one deployable's direct dependencies | Result |
|---|---|
| the house choice plus a competitor (`faraday` + `httparty`, `httpx` + `requests`, `axios` + `ky`) | `warn` |
| two competitors, no house choice | `warn` |
| a companion of the chosen library | quiet |
| **one** off-house library and nothing else for the concern (a client-mandated `ky`, no `axios`) | quiet at edit time, `info` in scans: one mechanism is orthogonal, even an off-house one |
| a competitor only in a test or tooling group | `info` |
| a monorepo root `package.json` holding tooling only | counts for tooling concerns, never app concerns |
| a declared migration (`mechanisms.migrations`) before its `until` date | quiet; after the date the finding returns, marked expired |
| a declared house override (`mechanisms.house_overrides`) naming an ADR | the override is the choice for that deployable |
| Rails 8 defaults (`solid_queue`, `solid_cache`, `solid_cable`) beside `sidekiq` or Redis | `warn`: remove the default, or declare the migration |
| a transitive dependency | never counted |

**Manifests read:** `Gemfile` (checked against `Gemfile.lock` DEPENDENCIES); `package.json`
`dependencies`, `devDependencies`, `peerDependencies`; `pyproject.toml` PEP 621 `dependencies`,
`[dependency-groups]`, `[project.optional-dependencies]` and Poetry tables; `requirements*.txt`.

**`package.json` cannot carry a comment**, so an inline `sdh:orthogonal-ok` marker is impossible
there. Declare overrides and migrations in `.claude/orthogonality.json`
(`@skills/orthogonality/references/declaring-intent.md`).

**Installs through Bash** (`npm i ky`, `bundle add httparty`, `uv add requests`) never pass through
the edit-time checker. The background watcher catches them, refreshes the index, and reports a new
CM1 in at most 5 lines, including an install made while the first index build is still running.

## CM2 — a second client wrapper for the same upstream

- **Signals.** TS/JS `axios.create(`, `ky.create(`, `new ApolloClient(`; Ruby `Faraday.new(`; Python
  `httpx.Client(` and `httpx.AsyncClient(`.
- **Same upstream** means the same environment variable name or the same literal host. The finding
  names the existing factory: reuse it.
- **Quiet.** A different upstream (Stripe, a maps API, another internal service); tests, MSW
  handlers, SDK wrappers. Two factories with no base URL in different directories are `info`.

## CM3 — a second error-envelope builder or global handler

It counts **definitions**, never keys; the envelope's shape and keys belong to `std-api-design`
(its "Error Format" section), and `api-design-checker.py` checks the keys.

- **Rails:** `rescue_from StandardError` or `rescue_from ActiveRecord::RecordNotFound` in more than
  one base controller; a second module defining an `error_body` or `render_error`-style builder.
- **FastAPI:** more than one `@app.exception_handler(Exception)` or `add_exception_handler(Exception, …)`.
- **DRF:** `REST_FRAMEWORK["EXCEPTION_HANDLER"]` plus a view overriding `handle_exception`.
- **Next.js:** more than one exported function building the envelope object.
- **Quiet:** handlers for distinct domain exceptions registered in the one handler module.

## CM4 — a second pagination style

The edited file introduces a style unlike the one covering at least 80% of at least 5 existing uses
in the deployable: `pagy(` vs kaminari `.page(`/`.per(` vs will_paginate `.paginate(` vs a hand-rolled
`.offset(params…)`; limit/offset vs cursor query parameters; DRF `pagination_class` variants;
`page=`/`offset=` vs `cursor=` in TS clients. Fewer than 5 uses is quiet: there is no dominant style
yet. A deliberate move of deep lists to cursors carries an inline marker. The pagination contract
belongs to `std-api-design`.

## CM5 — hand-rolled token code beside the house auth library (`info`)

`JWT.encode`/`JWT.decode` outside `config/initializers` and the auth module in Ruby, or `jwt.encode`
outside the auth module in Python, while `devise-jwt`, `simplejwt` or the house `pyjwt` module
exists. Webhook signature checks (HMAC) and third-party token verification (JWKS) are quiet by file
name (`webhook`, `jwks`) or marker.

## MF2 — a first-of-kind pattern (`info`)

A structural variant with no precedent in the deployable, while the dominant variant counts at
least 5: a second service entry-point name, a second result style, a second serializer, job or view
component base. The catalog → `@skills/orthogonality/references/detectors.md`.

## Out of scope here

- **Version divergence of the same package** across workspaces: the one-version policy, owned by
  `monorepo-architect`.
- **Server data held in a client-state store:** a layer rule for `std-clean-architecture`.
- **Two shadcn/ui bases in one package:** `std-shadcn-ui` reads `components.json` `style`.

## Enforcing the choice in code, with the project's own linters

A hook sees competitors only in manifests and wrapper factories. For imports, generate a ban for
the project's linter from the registry. The script **prints** the block and never writes a file:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/check_mechanisms.py --paths package.json --emit-lint-config eslint
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/check_mechanisms.py --paths pyproject.toml --emit-lint-config ruff
```

The ESLint output is a `no-restricted-imports` block; each entry names the approved package in its
message:

```js
"no-restricted-imports": ["error", {
  paths: [{ name: "ky", message: "http_client uses axios in this deployable (the orthogonality skill)." }],
}]
```

The Ruff output is a `banned-api` table:

```toml
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"requests".msg = "http_client uses httpx in this deployable (the orthogonality skill)."
```

Both **complement** CM1–CM4; neither replaces them:

- ESLint's rule applies to static imports only, not dynamic ones.
- Ruff's banned-api is meant to flag accidental uses, and can be bypassed.
- Neither sees a package merely added to a manifest, or a hand-rolled second pagination or envelope
  helper that imports nothing banned.

Scans report whether a `banned-api` entry already names the competitor. For ESLint they report only
whether `no-restricted-imports` appears, because JavaScript config files are never evaluated.

## Meta-concerns: one tool per job

The same rule applies to the checking tools themselves. Running two tools that overlap on one job
means two baselines, two ignore lists, and results that disagree.

| Job | Overlapping tools | House position |
|---|---|---|
| schema-vs-model consistency (Rails) | `database_consistency`, `active_record_doctor` | **`database_consistency`**; the two overlap almost entirely, and CM1 reports the pair |
| migration safety | `strong_migrations`, `squawk`, `django-migration-linter`, SQLFluff's PostgreSQL rules | pick one per stack; the house names none, so nothing is detected |
| import boundaries (Ruby) | packwerk, `pks` | pick one; they read the same config but can disagree, so the tool runner never runs both |
| import boundaries (Python) | import-linter, tach | pick one; the house names none |

## Sources

- Eric S. Raymond — The Art of Unix Programming, ch. 4, "Orthogonality" (Linuxtopia mirror) — https://www.linuxtopia.org/online_books/programming_books/art_of_unix_programming/ch04s02_1.html
- ESLint — no-restricted-imports — https://eslint.org/docs/latest/rules/no-restricted-imports
- Astral — banned-api (TID251) | Ruff — https://docs.astral.sh/ruff/rules/banned-api/ (the "accidental uses" limit is stated on the Ruff settings page linked from that rule)
- GitHub ankane/strong_migrations — README — https://github.com/ankane/strong_migrations
- Squawk — Rules — https://squawkhq.com/docs/rules
- GitHub 3YOURMIND/django-migration-linter — https://github.com/3YOURMIND/django-migration-linter
- SQLFluff — Rules Reference — https://docs.sqlfluff.com/en/stable/reference/rules.html
- GitHub gregnavis/active_record_doctor — README — https://raw.githubusercontent.com/gregnavis/active_record_doctor/master/README.md
- GitHub djezzzl/database_consistency — README — https://raw.githubusercontent.com/djezzzl/database_consistency/master/README.md
- RubyGems.org — database_consistency — https://rubygems.org/gems/database_consistency
- RubyGems.org — active_record_doctor — https://rubygems.org/gems/active_record_doctor
- Shopify — Shopify/packwerk (including the note on `pks`) — https://github.com/Shopify/packwerk
- David Seddon — Import Linter documentation — https://import-linter.readthedocs.io/en/stable/
- tach-org — tach-org/tach — https://github.com/tach-org/tach
