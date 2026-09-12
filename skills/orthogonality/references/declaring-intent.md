# Declaring intent — when the second representation stays

Real systems are only partly orthogonal. Every detector therefore has a declared-exception path. A
declaration makes a deliberate duplicate visible in review, gives it an owner and a reason, and can
expire.

**Try the orthogonal option first:** extend the existing model, read through the foreign key, use a
generated column, reuse the existing client. Declare only what remains.

## Two routes, both visible in review

| Route | Use it for | Needs an ADR |
|---|---|---|
| an entry in `.claude/orthogonality.json` | anything cross-cutting: read models, denormalized columns, a second library, a sanctioned cross-context write, context ownership | yes, where the key has an `adr` field |
| an inline `sdh:orthogonal-ok <ID> <reason>` comment | one local, obvious case (an HMAC helper beside `devise-jwt`) | no; the reason is the record |

A second model in another **declared** context needs neither: the context map is the record.

## The file: `.claude/orthogonality.json`

Optional and committed, so CI and teammates share it. It is JSON because every supported Python
parses it with the standard library. It declares only what no existing tool can; boundaries already
declared in packwerk, import-linter or tach stay there
(`@skills/orthogonality/references/context-maps.md`).

```json
{
  "version": 1,
  "contexts": {
    "accounts": {"paths": ["apps/api/app/models/accounts/**", "apps/api/app/services/accounts/**"],
                 "tables": ["users", "organizations", "memberships", "customers"]},
    "billing":  {"paths": ["apps/api/app/**/billing/**"], "tables": ["invoices", "payments"],
                 "may_depend_on": ["accounts"],
                 "relationships": {"accounts": "customer-supplier"},
                 "writes": [{"target": "accounts.customers", "columns": ["billing_status"],
                             "adr": "docs/adr/ADR-021-billing-status-on-customers.md"}]}
  },
  "shared_kernel": ["apps/api/app/values/**", "packages/types/**"],
  "concepts": {"synonyms": [["customer", "client", "patron"], ["shipment", "consignment"]]},
  "intentional_duplicates": [
    {"id": "DK1", "subject": "order_search_rows", "counterpart": "orders", "kind": "read-model",
     "source_of_truth": "orders", "refreshed_by": "OrderSearch::RefreshJob", "writes": "refresh job only",
     "adr": "docs/adr/ADR-014-order-search-read-model.md"},
    {"id": "DK3", "subject": "tasks.organization_id", "counterpart": "projects.organization_id",
     "kind": "denormalized-key", "enforced_by": "composite FK (project_id, organization_id)",
     "adr": "docs/adr/ADR-009-tenant-key-on-tasks.md"}
  ],
  "mechanisms": {
    "house_overrides": [{"deployable": "apps/web", "concern": "http_client", "package": "ky",
                         "adr": "docs/adr/ADR-030-client-mandated-ky.md"}],
    "migrations": [{"deployable": "apps/api", "concern": "background_jobs", "from": "solid_queue",
                    "to": "sidekiq", "until": "2026-12-31", "adr": "docs/adr/ADR-031-sidekiq.md"}]
  },
  "backfills": ["apps/api/app/jobs/backfills/**", "apps/api/lib/tasks/backfill_*.rake"],
  "ignore": ["legacy/**"],
  "clones": {"min_tokens": 70, "ignore": ["**/serializers/**"]},
  "enforce": "advisory"
}
```

### Keys

| Key | Meaning |
|---|---|
| `version` | must be `1` |
| `contexts.<name>.paths` | globs belonging to the context |
| `contexts.<name>.tables` | tables the context owns; a write from elsewhere is BC3 |
| `contexts.<name>.may_depend_on` | contexts it may reference (BC1) |
| `contexts.<name>.relationships` | other context → a context-map pattern name |
| `contexts.<name>.writes` | sanctioned writes into another context: `target` (`context.table`), `columns`, `adr` |
| `shared_kernel` | globs every context may reference |
| `concepts.synonyms` | extra synonym groups; they extend the house list |
| `intentional_duplicates` | kept duplicates: `id` (detector), `subject`, `counterpart`, `kind`, an `adr`, and the fields the kind needs; optional `until` |
| `mechanisms.house_overrides` | a different house choice for one deployable: `deployable`, `concern`, `package`, `adr` |
| `mechanisms.migrations` | two mechanisms during a planned move: `deployable`, `concern`, `from`, `to`, `until`, `adr` |
| `backfills` | data-migration jobs allowed to write across contexts |
| `ignore` | globs never indexed |
| `clones` | DK6 tuning: `min_tokens`, `ignore` globs |
| `enforce` | `"advisory"`, the only accepted value in this release |

## Validation

**Structural errors** make the file invalid: `version` other than `1`, a glob list that is not a
list, a relationship name outside the vocabulary, an unknown `enforce` value. A script exits `2`,
and a hook reports a once-per-session `note`; both name the JSON path and the key.

**Content that misses the bar** is reported as a `warn` finding:

- **CFG-ADR** — an `adr` that names no existing file under the project root.
- **CFG-READMODEL** — an `intentional_duplicates` entry of kind `read-model` without
  `source_of_truth`, `refreshed_by` and a `writes` statement. These are the three criteria of a
  legitimate read copy: derived, never written directly by the application, rebuildable from a named
  source (`@skills/orthogonality/references/database-duplication.md`).
- **Expiry.** `until` is an ISO date. Once it passes, the entry stops suppressing and the finding
  returns with `"expired": "<date>"`. That is the burn-down lever a todo file lacks.

## Inline markers

```ruby
# sdh:orthogonal-ok BC3 refund flow owned by billing (ADR-021)
Order.where(id: ids).update_all(status: "refunded")
```

- The comment sits **on the declaring line or the line above it**, after `#`, `//` or `--`.
- One marker suppresses **one detector on one subject**.
- **A reason is required.** `# sdh:orthogonal-ok BC3` alone is a `CFG-MARKER` warning.
- Formats without comments (`package.json`, other JSON manifests) cannot carry a marker; use
  `mechanisms` in the config file.
- **Scans list every active marker**, so a suppression is never invisible.

## The ADR for a kept exception

Write one whenever a finding is **kept** rather than fixed:

- a read model or cache table;
- a denormalized column;
- a second model for a concept in a context that is **not** declared;
- a second library, during a migration or under a client mandate;
- a sanctioned cross-context write;
- a cycle kept deliberately.

Use the house ADR template in `@skills/doc-generator/references/design-docs.md`, the same template
the `architecture-advisor` agent emits, stored in `docs/adr/`. Do not invent headings. Whatever
section a point lands in, the record must answer these questions:

1. **Why is one representation not enough?** Name the concept or fact, both representations with
   paths and tables, and the reason: performance, bounded-context language, a client mandate, a
   migration in progress.
2. **Which representation is the source of truth?**
3. **How does the copy stay in sync?** A generated column, a view, a materialized view with its
   refresh trigger or schedule, a database trigger, a composite foreign key, or a domain event.
4. **Who may write the copy?** For a read model, nothing but its refresh path.
5. **For a second library:** which one leaves, and by what date. That date is the declaration's `until`.
6. **What staleness is tolerated?** None for money or inventory; a materialized view accepts
   staleness those domains cannot.
7. **How is it rebuilt, how is drift detected, and which test proves the copy matches its source?**
8. **What was the orthogonal option,** and why was it rejected? Assumptions about tools stay
   labelled as assumptions.

The declaration references the ADR by path. The `architecture-advisor` skill writes the ADR; the
`orthogonality` skill only checks that the file exists (CFG-ADR) and that `until` has not passed.

## Sources

- Eric S. Raymond — The Art of Unix Programming, ch. 4, "Orthogonality" (Linuxtopia mirror) — https://www.linuxtopia.org/online_books/programming_books/art_of_unix_programming/ch04s02_1.html
- Eric S. Raymond — The Art of Unix Programming, ch. 4, "The SPOT Rule" (Linuxtopia mirror) — https://www.linuxtopia.org/online_books/programming_books/art_of_unix_programming/ch04s02_2.html
- martinfowler.com — Bounded Context — https://martinfowler.com/bliki/BoundedContext.html
- DDD Crew — ddd-crew/context-mapping (pattern names only) — https://github.com/ddd-crew/context-mapping
- Microsoft Learn (Azure Architecture Center) — Materialized View pattern — https://learn.microsoft.com/en-us/azure/architecture/patterns/materialized-view
- Microsoft Learn — Database normalization description — https://learn.microsoft.com/en-us/troubleshoot/microsoft-365-apps/access/database-normalization-description
- Shopify Engineering — A Packwerk Retrospective — https://shopify.engineering/a-packwerk-retrospective
- PMD — Copy/Paste Detector (`CPD-OFF` / `CPD-ON` suppression comments) — https://docs.pmd-code.org/latest/pmd_userdocs_cpd.html
- GitHub sbdchd/squawk (`squawk-ignore` comments) — https://github.com/sbdchd/squawk
