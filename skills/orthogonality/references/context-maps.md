# Context maps — dependencies follow the declared map

Large codebases split into domain-oriented modules at the top, each layered inside. Checks
therefore run on two axes:

| Axis | Question | Owner |
|---|---|---|
| **context** (top level) | may billing depend on orders? who writes `orders`? is there a cycle? | this skill |
| **layer** (inside a context) | may a model import a controller? may a screen call the API client? | `std-clean-architecture` |
| **package** (between deployables and shared packages) | may `apps/web` deep-import `packages/ui/src`? one version of React? | `monorepo-architect` |

A bounded context may hold its own model of a concept another context also models; that is not
duplication. What erodes a context map is **undeclared coupling**: a reference the map does not
allow, a write to data another context owns, a cycle, code that lives in the wrong context. Each type
of data has one owning context that drives its updates. Transactions do not cross aggregate boundaries.

## Where contexts come from

Per subtree, the nearest declaration wins, in this order:

1. **packwerk** (Ruby). `packwerk.yml` `package_paths`; each `package.yml`'s `enforce_dependencies`
   and `dependencies`.
2. **import-linter** (Python). `independence` contracts are contexts that may not import each other;
   `forbidden` contracts are explicit denies. `layers` contracts are read and **ignored**: layers are
   `std-clean-architecture`'s axis.
3. **tach** (Python). `[[modules]] path` and `depends_on`.
4. **`.claude/orthogonality.json` `contexts`**. Use it for TypeScript, whose tool configs are
   JavaScript and never evaluated, for any stack without a tool, and for what **no tool declares**:
   table ownership (`tables`), write exceptions (`writes`), relationship types (`relationships`),
   shared kernel paths.
5. **Nx** `project.json` `tags` supply context **names** only (`scope:billing` → `billing`); the
   constraints stay in the project's ESLint rule.
6. **Inferred**, when nothing is declared (below).

Tool declarations and the config file combine. The config adds ownership, writes and relationships
on top of tool-declared packages, keyed by the same names. A config context name that matches no
tool package is reported by scans as `contexts.unmatched`.

### What is read from each config

| Config | Keys read | Used for |
|---|---|---|
| `packwerk.yml` | `package_paths`, `include`, `exclude` | context roots, index scope |
| `package.yml` | `enforce_dependencies`, `dependencies` | allowed edges (BC1) |
| `package_todo.yml` | presence and entry count | baseline counts in reports; never parsed for rules |
| `.importlinter`, `setup.cfg`, `pyproject.toml [tool.importlinter]` | `root_package(s)`; `independence` and `forbidden` contracts (`modules`, `source_modules`, `forbidden_modules`, `ignore_imports`) | contexts, BC1 |
| `tach.toml` | `[[modules]] path`, `depends_on` | contexts, BC1 |
| `project.json`, `package.json#nx` | `tags` | context names |
| `package.json` `workspaces`, `pnpm-workspace.yaml` `packages` | globs | **deployables**, not contexts |
| `tsconfig*.json` `paths` | aliases | import resolution |
| ESLint configs | **not evaluated** | scans report only whether `no-restricted-imports`, `import/no-cycle` or `@nx/enforce-module-boundaries` appear |

YAML and TOML are read by restricted parsers that understand only these keys. Anything else is
reported under `coverage.config_unparsed`, never guessed.

### Examples

packwerk — billing may depend on accounts, nothing else:

```yaml
# packs/billing/package.yml
enforce_dependencies: true
dependencies:
  - packs/accounts
```

import-linter — billing and orders never import each other:

```ini
[importlinter]
root_package = app

[importlinter:contract:billing-orders-independent]
name = Billing and orders are independent
type = independence
modules =
    app.billing
    app.orders
```

The config file — what the tools cannot say (full schema →
`@skills/orthogonality/references/declaring-intent.md`):

```json
{
  "version": 1,
  "contexts": {
    "orders":  {"paths": ["app/**/orders/**"], "tables": ["orders", "order_items"]},
    "billing": {"paths": ["app/**/billing/**"], "tables": ["invoices", "payments"],
                "may_depend_on": ["orders"],
                "relationships": {"orders": "customer-supplier"}}
  },
  "shared_kernel": ["app/values/**"]
}
```

### Draw packages along how code runs

Shopify's own lesson from years of packwerk is that packages named after domains can mislead about
how the code actually executes, and that constant-based analysis misses runtime dependencies. Before
declaring a context, look at what calls what (`check_boundaries.py --graph dot`), not only at folder
names.

## Inferred contexts

When nothing is declared, contexts are inferred:

| Stack | Inferred context |
|---|---|
| Rails | `app/models/<namespace>/`, `packs/*`, `app/packages/*`, `components/*`. A file under another layer's `app/<layer>/<namespace>/` joins that context only when `app/models/<namespace>/` exists; `api`, `admin`, `concerns` and version folders (`v1`) never become contexts |
| Django | every app directory holding `apps.py` |
| FastAPI and Python packages | first-level subpackages under `app/` or `src/<pkg>/`, excluding layer names: `api`, `routers`, `schemas`, `models`, `services`, `core`, `db`, `tasks`, `utils`, `common`, `lib`, `config`, `settings`, `domain`, `infrastructure`, `infra`, `application`, `adapters`, `repositories`, `repository`, `crud`, `dependencies`, `deps`, `middleware`, `entities`, `use_cases`, `interfaces`, `presentation`, `exceptions`, `helpers` (and `tests`, `migrations`, `alembic`, `static`, `templates`) |
| TypeScript | `src/features/*`, `src/modules/*`, `src/domains/*` |

An inferred context is a guess, so it speaks less:

- **BC1 and BC3** on inferred contexts are `info` in scans only.
- **BC2 cycles** between inferred contexts produce an edit-time `warn` **only for sibling folders
  under one parent**: `src/features/cart` ↔ `src/features/checkout`, `app/billing` ↔ `app/orders`.
  Every other cycle between inferred contexts is scan-only.
- **Declared contexts** warn normally.

## The relationship vocabulary

`relationships` maps another context to one of the context-map pattern names, in kebab-case:
`shared-kernel`, `customer-supplier`, `conformist`, `anticorruption-layer`, `open-host-service`,
`published-language`, `separate-ways`, `partnership`. Any other value makes the file invalid. Only
the pattern names are taken from the DDD Crew context-mapping catalog; read it for their meaning.

A relationship documents the coupling for reviewers and scans. What **allows** an edge is the
dependency declaration: packwerk `dependencies`, an import-linter contract, tach `depends_on`, or
`may_depend_on`. Paths under `shared_kernel` are shared by every context and are never a
cross-context reference.

## BC1 — cross-context dependency

- **Fires** when a new reference from context A into context B is not allowed by the declaration.
  The finding names the importing `path:line`, the referenced symbol or module, both contexts, the
  file and key that forbid it, and the alternative: B's public entry, or the declared published language.
- **Resolution per stack.** Ruby constant references resolve against the index's constant-to-file
  map, the approach packwerk takes through Zeitwerk. Python uses `ast` imports. TS/JS uses import
  specifiers resolved through relative paths, tsconfig `paths` and workspace package names.
- **Quiet.** Tests; type-only imports (`import type`, `if TYPE_CHECKING:`); `shared_kernel` paths.
- **Blind spots.** `constantize`, `importlib`, string imports, method calls on objects passed in.
  packwerk accepts the same false negatives by design.

## BC2 — new cycle

- **Fires** when an edit adds an edge that creates a strongly connected component of at least two
  context nodes, or grows one, compared with the baseline. Evidence: the cycle members in order, one
  example edge `path:line` each, and whether the component is new or grew.
- **Quiet.** Type-only edges; cycles already in the baseline (frozen); the inferred-context cases above.
- **File-level cycles inside one context** are `info` in scans only (`check_boundaries.py --cycles
  file`). Cycle detection is expensive, and ESLint's `import/no-cycle` documents the same trade of
  recall for speed.
- **Resolve** by inverting one edge: move the shared piece into the context both depend on, publish
  an event, or depend on an interface the other context implements. `std-clean-architecture` covers
  dependency inversion inside a context.

## BC3 — cross-context write

- **Fires** when code in context A writes a model or table owned by B.
  - Rails: `B::Model.create`/`create!`/`insert_all`/`upsert_all`/`update_all`/`delete_all`/
    `destroy_all`, `find(...).update!`/`destroy`, raw `INSERT INTO`/`UPDATE`/`DELETE FROM` in `execute`.
  - Django: `objects.create`/`bulk_create`/`update`/`delete`/`get_or_create`/`update_or_create`,
    `Model(...).save()`.
  - SQLAlchemy: `session.add(Model(...))`, `insert(Model)`, `update(Model)`, `delete(Model)`, `text()` SQL.
- **Evidence** names B's existing writer service as the entry point to call instead.
- **Quiet.** Tests, factories, seeds, fixtures; migrations and data-migration jobs under config
  `backfills`; Django `admin.py`; declared `writes` exceptions; instance writes whose type cannot be
  resolved (`order.update!` on a local variable).

## BC4 — multi-context transaction (`info`)

One `transaction do`, `transaction.atomic()` or `session.begin()` block persisting models from two or
more contexts. Transactions should not cross aggregate boundaries, but CRUD-heavy Rails and Django
code relaxes that rule, so this never rises above `info`. When it is deliberate, say so in the ADR
that records the context boundary.

## MF1 — wrong-context file (`info`)

A **new** file in context A where at least 70% of at least 6 resolved references point into B, and
at most 1 into A. Evidence: counts per context, the top 3 referenced symbols in B, and B's matching
directory for the same layer. Quiet: composition roots (`config/`, `app/main.py`, `urls.py`, router
registries), tests, index and barrel files.

## Seeing the map

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_index.py --show contexts --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/check_boundaries.py --contexts-source auto --graph dot --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

`--contexts-source packwerk|importlinter|tach|config|inferred` forces one source, which helps when
two disagree.

## Hard enforcement lives in the project's CI

Hooks warn; they never block. A boundary becomes a gate in the project's CI, with **one** boundary
tool per language (`@skills/orthogonality/references/competing-mechanisms.md`): `bin/packwerk check`,
`lint-imports`, `tach check` or `depcruise`, beside `arch_scan.py --new-only --fail-on warn`
(`@skills/orthogonality/references/scans-and-tools.md`). Cross-package enforcement through ESLint,
Nx tags or dependency-cruiser is configured through `@skills/monorepo-architect/references/boundaries.md`.
Nx Conformance, the language-agnostic check, needs an Nx Enterprise licence and is not integrated.

## Sources

- martinfowler.com — Bounded Context — https://martinfowler.com/bliki/BoundedContext.html
- martinfowler.com — PresentationDomainDataLayering — https://martinfowler.com/bliki/PresentationDomainDataLayering.html
- martinfowler.com — DDD_Aggregate — https://martinfowler.com/bliki/DDD_Aggregate.html
- Microsoft Learn — Identifying domain-model boundaries for each microservice — https://learn.microsoft.com/en-us/dotnet/architecture/microservices/architect-microservice-container-applications/identify-microservice-domain-model-boundaries
- DDD Crew — ddd-crew/context-mapping (pattern names only) — https://github.com/ddd-crew/context-mapping
- arXiv / ICSA 2022 (Li, Soliman, Liang, Avgeriou) — Symptoms of Architecture Erosion in Code Reviews — https://arxiv.org/abs/2201.01184
- Shopify — Shopify/packwerk — https://github.com/Shopify/packwerk
- Shopify Engineering — A Packwerk Retrospective — https://shopify.engineering/a-packwerk-retrospective
- David Seddon — Import Linter documentation — https://import-linter.readthedocs.io/en/stable/
- tach-org — tach-org/tach — https://github.com/tach-org/tach
- Nx — Enforce Module Boundaries — https://nx.dev/docs/features/enforce-module-boundaries
- Sander Verweij — dependency-cruiser command line interface — https://github.com/sverweij/dependency-cruiser/blob/main/doc/cli.md
- import-js — import/no-cycle — https://github.com/import-js/eslint-plugin-import/blob/main/docs/rules/no-cycle.md
