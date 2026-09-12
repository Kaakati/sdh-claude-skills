# Drill-down Resources — every level cheap, safe, and linkable

Load-bearing rules restated (hold even if you read nothing else):

1. **One canonical parent per resource. Nest only collection routes, one level deep; member routes
   are flat by ID.** `GET /v1/sites/{siteId}/assets` lists and creates. `GET /v1/assets/{id}` reads,
   updates, and deletes, wherever the asset lives.
2. **A detail carries its own location**: `parentId` and a permission-filtered `ancestors` chain,
   root first. Never rebuild it from history, from URL segments, or with one request per parent.
3. **Scope, then find, at every level**: the parent of a nested list, the child of a flat member
   route, every include, every ancestor. A record outside the caller's scope returns `404`.
4. **Counts are computed inside the caller's policy scope.** A stored counter is a valid badge only
   for a caller whose scope covers every row it counts (`org`).
5. **Every level answers `If-None-Match` with a validator that varies by viewer and
   `permissions_version`.** Nothing permission-scoped is cached `public`.

Owned elsewhere — do not duplicate:
- List envelope, cursor vs offset, limits → `@skills/std-api-design/references/pagination-rails.md`
  and `@skills/std-api-design/references/pagination-clients.md`
- The one error envelope → `@skills/std-api-design/references/errors-rails.md`
- `policy_scope`, 404-not-403 → `@skills/std-rails-conventions/references/authorization.md`
- Permission keys, scope levels, `permissions_version` →
  `@skills/std-rails-conventions/references/roles-and-permissions.md` and
  `@skills/access-control-designer/references/permission-matrix.md`
- `/me`, and what a client does with a 404 → `@skills/access-control-designer/references/ui-gates.md`
- Tree storage and read models → `@skills/std-database/references/hierarchies.md`
- The UI half (nav chrome, breadcrumb rendering, Back, restored list state, the command palette) →
  `@skills/ui-ux-patterns/references/drill-down-navigation.md`

---

## 1. Each level and the endpoint behind it

| UI level | Endpoint | Body | Serializer |
|---|---|---|---|
| Area overview | the area's root list, plus an optional `GET /v1/<node>/summary` | `{ "data": { …aggregates, "asOf" } }` | `XSummary`: aggregates only |
| Collection list | `GET /v1/<parents>/{parentId}/<children>` | the house list envelope | `XListItem`: the row, nothing more |
| Member detail | `GET /v1/<children>/{id}`, flat | `{ "data": { …, "parentId", "ancestors" }, "links": {…} }` | `XDetail` |
| Sub-collection | `GET /v1/<children>/{id}/<grandchildren>` | the house list envelope | `YListItem` |
| Sub-detail | `GET /v1/<grandchildren>/{id}`, flat | same as member detail | `YDetail` |
| Search (the second way in) | `GET /v1/search?q=&types=`, or `?q=` on one collection | the house list envelope; hits carry `type`, `id`, `name`, `ancestors` | `SearchHit` |

- **Exactly one canonical parent.** "The parent-child relationship also must be acyclic", and an
  instance has "only one canonical parent resource" (Google — AIP-121: Resource-oriented design). One
  parent means one breadcrumb path. Any other association is a filter (`?siteId=`) or a link, never a
  second nested URL.
- **A summary is its own resource, not extra fields on a list.** Azure: "YOU SHOULD NOT return a
  count of all objects in the collection as this may be expensive to compute" (Microsoft — Azure REST
  API Guidelines). Zalando omits totals unless the client sends `Prefer: return=total-count` (Zalando
  SE — RESTful API Guidelines, Pagination chapter). Model the summary as a read-only singleton under
  its parent, extending AIP-156's shape beyond its config example (Google — AIP-156: Singleton
  resources). It then gets its own URL, validator, and authorization check.
- **When an overview gets a summary endpoint:** when first paint would otherwise need three or more
  requests, when it aggregates across descendants, or when its numbers need a different cache
  lifetime from the list's. The summary lives in Rails so every client shares it; a Next.js Route
  Handler is "BFF/webhooks/health only, never a second API" (`std-nextjs`).

## 2. URLs — shallow nesting

**Nest only collection routes (`index`, `create`), one level deep, under the canonical parent. Member
routes (`show`, `update`, `destroy`) are flat and take the ID alone.**

- **Rails.** "The general rule of thumb is to only nest resources 1 level deep"; `shallow: true`
  builds member routes "with the minimal amount of information to uniquely identify the resource"
  (Ruby on Rails Guides — Rails Routing from the Outside In).
- **GitHub.** The comment list nests under the issue, but a single comment is
  `GET /repos/{owner}/{repo}/issues/comments/{comment_id}`, with no issue number (GitHub Docs — REST
  API endpoints for issue comments). `{owner}/{repo}` is a tenant scope, not depth. The house
  equivalent is the organization resolved from the request (`roles-and-permissions.md`).
- **Why flat members:** a deep link needs one ID, survives a move to another parent, and stays short.
  The client rebuilds the location from `ancestors` (§4). A member nested under its parent gives one
  record two URLs, which means two cache entries, two tag sets, and two places to authorize.

## 3. IDs and deep links

- **Every level is reachable by one stable ID.** Store the ID, not a URL built from it. AIP-122 calls
  resource names "what users should store as the canonical names for the resources" (Google — AIP-122:
  Resource names). House IDs are UUID strings (`api-designer`, Field Conventions). OWASP advises
  "random and unpredictable values as GUIDs for records' IDs" (OWASP API Security Project — API1:2023
  BOLA).
- **Links go in the body, beside `data`**, in the HATEOAS shape of
  `@skills/api-designer/references/api-conventions.md`: `self`, `parent`, and one per sub-collection.
  Zalando embeds links in the payload rather than the Link header (Zalando SE — RESTful API
  Guidelines, Hypermedia chapter). A link is "a typed connection between two resources" (IETF — RFC
  8288: Web Linking).
- **A deep link to a record the caller cannot read returns `404`** (§11). The client shows not-found and
  does not treat the response as stale permissions (`ui-gates.md`).

## 4. Breadcrumbs — the `ancestors` payload

```json
{
  "data": {
    "id": "b6f1…",
    "type": "asset",
    "name": "Pump 3",
    "parentId": "5c2e…",
    "ancestors": [
      { "type": "region", "id": "9a07…", "name": "North" },
      { "type": "site", "id": "5c2e…", "name": "Yard B" }
    ]
  },
  "links": { "self": "/v1/assets/b6f1…", "parent": "/v1/sites/5c2e…", "readings": "/v1/assets/b6f1…/readings" }
}
```

- **Order and shape:** root first, down to the immediate parent; camelCase; inside the house `{ data }`
  envelope.
- **Built on the server, filtered by the read policy.** Each ancestor passes the same check as its own
  detail endpoint. One the caller cannot read is **left out entirely**: no name, no ID, no placeholder.
  `links.parent` names the nearest readable ancestor, or is `null`, in which case the client falls
  back to the area root. OWASP asks for authorization that "relies on the user policies and
  hierarchy" (OWASP API Security Project — API1:2023 BOLA) and for exposing only chosen properties
  (OWASP API Security Project — API3:2023 BOPLA). How a shortened chain is *displayed* is a
  per-project question (§15).
- **One query per detail, never one per parent.** A fixed chain eager-loads with
  `includes(site: :region)`. A tree of any depth takes one statement: a recursive query, `ancestry`'s
  `ancestors_of`, or `closure_tree`'s single SELECT (`hierarchies.md`).
- **List rows carry no `ancestors`**, because the list already gives that context. **Search hits do**,
  because a search result has none.

## 5. Counts and badges on overview levels

- **Count inside the caller's scope.** Counting rows the caller cannot see reveals that they exist,
  and how many. That is the same leak a `403` on a detail would be.
- **Serve stored counters only at `org` scope.** A `counter_cache` or materialized-view figure counts
  every row, so serve it only when the caller's level for that key is `org`
  (`roles-and-permissions.md`). For `own` or `team`, run one grouped `COUNT` over the policy scope
  per level, never one per row.
- **`counter_cache`** keeps the count with `increment_counter` / `decrement_counter`.
  `counter_cache: { active: false }` backfills a large table safely. Writes that bypass Active Record
  make it drift, and `reset_counters` repairs it (Ruby on Rails API —
  ActiveRecord::Associations::ClassMethods; ActiveRecord::CounterCache::ClassMethods). Hot-row cost →
  `@skills/std-database/references/relationships.md`.
- **Materialized views for heavy rollups** are "often much faster than accessing the underlying
  tables directly", but "the data is not always current" (PostgreSQL — 39.3 Materialized Views). A
  summary served from one returns `asOf`, and how stale each badge may be is a per-project question
  (§15). Refresh rules → `@skills/std-database/references/hierarchies.md`.
- **Keep totals out of list responses.** A list that needs "N results" or "go to page 7" is the offset
  exception `pagination-rails.md` defines. Every other overview number comes from the summary.

## 6. The list contract

- **Filters, sort, and pagination are query parameters that mirror the UI URL one to one.** A restored
  or shared URL, including the list breadcrumb's href, then replays the same request. Filter and sort
  syntax → `api-designer` Step 6. Cursor, limits, and envelope → `pagination-rails.md`; cite it, and
  never restate its numbers.
- **A cursor is valid only with the parameters that produced it.** Page tokens are opaque and URL-safe,
  and every other request parameter must match the call that issued the token (Google — AIP-158:
  Pagination). The client drops the cursor when a filter changes. The server may reject a mismatch with
  the house `400`.
- **Order by a unique key.** Pagy: "The set must be uniquely ordered. Add the primary key (usually :id)
  as the last order column to be sure" (Pagy — :keyset). DRF's cursor pagination "requires that there
  is a unique, unchanging ordering of items in the result set" (Django REST framework — Pagination).
- **Paginate from the first release.** "Adding pagination to an existing RPC is a
  backwards-incompatible change" (Google — AIP-158), and Azure agrees. Put the parent in the path: a
  List method takes a `parent` unless the resource is top-level (Google — AIP-132: Standard methods:
  List).
- **Pagy 43's `:keyset`** is an alternative to the hand-written `CursorPaginable`. It needs a unique
  order ending in `:id` plus a matching index, and it moves forward only: "no jumping to arbitrary
  pages" (Pagy — :keyset). Check it against the installed version; adopting it is an engineering call.

## 7. Includes, over-fetching, and N+1 per level

- **Lean rows, full detail.** Where a view enum exists, "For List RPCs, the effective default value
  should be BASIC" (Google — AIP-157: Partial responses). The house form is separate list and detail
  serializers (`std-rails-conventions`, Serialization).
- **`?include=` accepts a closed, per-endpoint allow-list, one level deep**: a detail's immediate
  children, or its summary. Anything else is a `400` in the house envelope. JSON:API requires `400`
  when an endpoint doesn't support the parameter (JSON:API — Specification v1.1). Stripe allows four
  levels but warns to "limit many nested expansions on list requests" (Stripe — Expanding responses).
  Zalando's `embed` exists to cut round trips (Zalando SE — RESTful API Guidelines, Performance
  chapter). The house stops at one level because every include is both an authorization surface and an
  N+1: "cherry-pick specific object properties you specifically want to return" (OWASP API Security
  Project — API3:2023 BOPLA).
- **Every include is authorized and eager-loaded within the controller's scope.** Panko does not
  eager-load (`std-database`, N+1). Pin the query count per level
  (`@skills/std-database/references/design-and-query-plan.md` §10; `std-python-performance`).

## 8. Conditional GET and ETags, per level

- **Every level sends a validator and honours `If-None-Match`**, so going back up a level costs a
  `304`. "If-None-Match is primarily used in conditional GET requests to enable efficient updates of
  cached information with a minimum amount of transaction overhead" (IETF — RFC 9110: HTTP Semantics).
- **Rails:** `fresh_when` and `stale?` set ETag and Last-Modified and render the `304`. Responses are
  private unless you pass `public: true` (Ruby on Rails API — ActionController::ConditionalGet). ETags
  are weak by default (Ruby on Rails Guides — Caching with Rails).
- **Include the viewer and their permissions version.** Rails documents `etag { current_user&.id }`
  "to prevent unauthorized displaying of cached pages" (Ruby on Rails API —
  ActionController::ConditionalGet::ClassMethods). A user ID doesn't change when the role does, so add
  `permissions_version` too (inference from that caveat).
- **Include every record the payload names**: the detail and each ancestor. Otherwise a renamed parent
  keeps serving its old crumb with a `304` (inference: `touch` runs from child to parent, never down).
  Add a serializer version token, since records alone miss a serializer change (inference). Each
  `include` combination is its own representation and gets its own ETag (IETF — RFC 9110).
- **A child change moves the parent's validator** via `touch: true` (Ruby on Rails API —
  ActiveRecord::Associations::ClassMethods), at the hot-row cost recorded in `relationships.md`. Never
  mark a scoped level `public`, or a shared cache serves one user's view to another (inference). On
  Python stacks no helper was verified: a small dependency or mixin hashes the same inputs, compares
  them with `If-None-Match`, and returns `304`.

## 9. Realtime invalidation

- **Publish after commit** (`after_commit`, `std-database` Transactions), as `permissions_changed`
  does in `roles-and-permissions.md`.
- **Publish IDs, never data**: `{ "event": "changed", "type": "asset", "id", "parentId",
  "ancestorIds": [...] }`. Names never go out on a shared channel; channel topology is
  `rails-architect`'s.
- **Clients invalidate, never patch** permission-scoped data from a broadcast. This is the "carries only
  an id" row of `@skills/std-react-native/references/realtime-centrifugo.md`, which also invalidates on
  reconnect. `parentId` refreshes the parent's lists, and `ancestorIds` refresh every summary that
  counted the node. Prefix invalidation refetches every active match, so a broad key on a deep tree is a
  request burst; narrow it with `exact: true` or a predicate (TanStack — Query Invalidation).
- **Next.js:** Rails calls the revalidation Route Handler (`@skills/std-nextjs/references/caching.md`)
  with the entity's tag and its ancestors' tags (`asset:<id>`, `site:<parentId>`, `region:<ancestorId>`).
  Each cached level carries its own tag and its ancestors' tags; that pattern is an inference built on
  documented multi-tag support. One `cacheTag()` call takes up to 128 tags of at most 256 characters,
  and extras are dropped with only a console warning (Vercel — cacheTag). On Next.js 16 that Route
  Handler calls `revalidateTag(tag, { expire: 0 })`, and a server action whose user must see their own
  write calls `updateTag(tag)`; `revalidateTag(tag, 'max')` serves stale content while it revalidates,
  and the one-argument form, the only one on 15, is deprecated on 16 (Vercel — revalidateTag, updateTag).

## 10. Search — the second way in

- **One permission-scoped endpoint.** Hits carry `type`, `id`, `name`, and `ancestors` (filtered as in
  §4), so "Pump 3 — North › Yard B" can be told apart from other results and opens by ID. The header
  search field and the web command palette call it (`drill-down-navigation.md`). Whether the default
  scope is global or the current area is a per-project question (§15).
- **Rails: `pg_search`** (house pin). `pg_search_scope` searches one model; multisearch builds one
  global index. A precomputed `tsvector` column "speeds up searching dramatically", but with
  `associated_against` "it will be impossible to speed up searches with database indexes" (Casecommons
  — pg_search README). Merge the search scope with the level's policy scope.
- **Relevance rank is not a unique key.** Break ties on `id` before keyset pagination (inference).

## 11. Authorization on every level

- **Scope, then find.** For a nested collection, load the parent through its own scope
  (`policy_scope(Site).find(params[:site_id])`) on every action, `create` included, then scope the
  children and build new ones on that parent. For a flat member, call
  `policy_scope(Asset).find(params[:id])`, then `authorize`. Every include and every ancestor passes
  its own read policy. Shallow routes take the parent out of the URL, so the child's lookup is the only
  check left. This is the house form of "check if the logged-in user has access to perform the
  requested action on the record in every function that uses an input from the client" (OWASP API
  Security Project — API1:2023 BOLA). Mechanics → `authorization.md`.
- **`404`, not `403`**, for a node the caller cannot see. This is already the house rule
  (`authorization.md`, `std-security`), and Microsoft Graph's: "SHOULD return a 404 Not Found error if
  a 403 error would result in information disclosure" (Microsoft — Microsoft Graph REST API
  Guidelines). AIP-193 instead checks permission before existence and always returns `403` (Google —
  AIP-193: Errors). That leaks nothing either, but the house does not use it. A real `403` remains for
  "you can see this, but you can't do that".
- **Authorization tests cover every level**, including rows from another tenant and another team, and
  every write to a nested collection: a POST to another tenant's parent returns `404` and creates
  nothing (the DRF test in §13). A failure blocks the deploy (OWASP API1; the matrix-driven specs in
  `roles-and-permissions.md`).

## 12. Caching, per level

| Layer | Caches | Key must include | Invalidation |
|---|---|---|---|
| HTTP conditional GET | every level | records named + serializer version + include + user + `permissions_version` | automatic; `touch` for parents |
| Rails cache / Russian doll | JSON or Phlex fragments; a nested one needs `touch`, or the outer one never expires (Ruby on Rails Guides — Caching with Rails) | record versions + viewer scope + `permissions_version` when scoped | versioned keys + explicit TTL; cache IDs, not records |
| Phlex `cache` | organism fragments; the key gets boot time, class, method, and line (Phlex — Fragment caching in Phlex Components) | viewer and permission context, absent by default (inference) | cold after every deploy |
| TanStack Query | each level, under hierarchical keys (`@skills/std-reactjs/references/data-fetching.md`) | level path + filters + organization | prefix `invalidateQueries` (§9) |
| Next.js server cache | shared, non-personalized data only | entity tag **and ancestor tags** | `revalidateTag` / `revalidatePath`; per-user data uses `'use cache: private'` or dynamic rendering (Vercel — Caching) |

A list cached on request params alone serves one user's rows to another. That is why
`std-rails-conventions`' list-caching line names viewer scope and `permissions_version`.

## 13. Sketches per stack

These build on house pieces defined in the cited files: `CursorPaginable`, `UserContext`,
`require_permission`, `scope_for` / `visible_to`, and the one error handler.

### Rails

```ruby
# config/routes.rb — shallow: index/create nest one level; show/update/destroy stay flat
scope path: "v1", module: "api/v1", as: "api_v1" do
  resources :regions, only: %i[index show], shallow: true do
    resources :sites, only: %i[index show create update destroy] do
      resources :assets, only: %i[index show create update destroy]
    end
  end
  get "regions/:region_id/summary", to: "region_summaries#show", as: :region_summary # own controller
end
# => GET /v1/regions/:region_id/sites · GET /v1/sites/:id · GET /v1/sites/:site_id/assets · GET /v1/assets/:id
```

```ruby
# app/controllers/api/v1/assets_controller.rb (excerpt)
def index
  site = policy_scope(Site).find(params[:site_id]) # another tenant's site => RecordNotFound => 404
  scope = policy_scope(Asset).where(site:).order(created_at: :desc, id: :desc)
  assets, pagination = paginate_by_cursor(scope)   # CursorPaginable owns limits and the envelope
  render json: { data: Panko::ArraySerializer.new(assets, each_serializer: AssetListItemSerializer).to_a,
                 pagination: }
end

def show
  asset = policy_scope(Asset).includes(site: :region).find(params[:id]) # flat route: scope it HERE
  authorize asset
  return unless stale?(etag: [asset, asset.site, asset.site.region, AssetDetailSerializer::VERSION])

  nodes = Hierarchy::Ancestors.new(pundit_user).for(asset) # readable ancestors, root first
  render json: {
    data: AssetDetailSerializer.new(context: { ancestors: nodes }).serialize(asset),
    links: { self: api_v1_asset_path(asset), parent: nodes.last && polymorphic_path([:api_v1, nodes.last]) }
  }
end

# app/controllers/application_controller.rb (excerpt) — every validator varies by viewer and grants
etag { current_user&.id }
etag { pundit_user.membership&.permissions_version }
```

```ruby
# app/queries/hierarchy/ancestors.rb — the one ancestors contract, for the API detail and the Phlex
# breadcrumb alike: the records the read policy allows, root first. Resource-agnostic: each model
# names its chain over associations the caller eager-loaded, so filtering costs zero extra queries.
# A tree of any depth swaps the chain for one query (hierarchies.md) and filters the same way.
module Hierarchy
  class Ancestors
    def initialize(context) = @context = context
    def for(record) = record.ancestor_chain.select { |node| Pundit.policy!(@context, node).show? }
  end
end

class Asset < ApplicationRecord # excerpt
  def ancestor_chain = [site.region, site] # root first; every node answers `name`. Shipment: [order]
end

class AssetDetailSerializer < Panko::Serializer
  VERSION = 3 # bump when the output changes — it is part of the ETag
  attributes :id, :type, :name, :status, :ancestors
  aliases site_id: :parentId

  def type = "asset"
  def ancestors = context.fetch(:ancestors).map { |n| { type: n.model_name.element, id: n.id, name: n.name } }
end

# app/controllers/api/v1/region_summaries_controller.rb — counts inside the caller's scope, one query
def show
  region = policy_scope(Region).find(params[:region_id])
  authorize region, :show?
  counts = policy_scope(Asset).joins(:site).where(sites: { region_id: region.id }).group(:status).count
  return unless stale?(etag: [region, counts]) # the counts ARE the payload: saves bytes, not the query
  render json: { data: { regionId: region.id, assetsByStatus: counts, asOf: Time.current.iso8601 } }
end
```

### FastAPI

```python
# app/api/routers/assets.py — the collection router nests once; a flat `assets` router holds members
site_assets = APIRouter(prefix="/sites/{site_id}/assets", tags=["assets"])


async def site_in_scope(
    site_id: UUID,
    scope: str = Depends(require_permission("sites.read")),
    membership: Membership = Depends(get_current_membership),
    session: AsyncSession = Depends(get_session),
) -> Site:
    # A prefix authorizes nothing. This does: SiteNotFound -> the one handler -> the house 404.
    return await SiteService(session).get_visible(site_id, membership, scope)


@site_assets.get("", response_model=AssetListPage)  # the house list envelope
async def list_site_assets(
    params: AssetListParams = Depends(),  # filters + sort + cursor, mirroring the UI URL
    site: Site = Depends(site_in_scope),
    scope: str = Depends(require_permission("assets.read")),
    membership: Membership = Depends(get_current_membership),
    session: AsyncSession = Depends(get_session),
) -> AssetListPage:
    return await AssetService(session).list_for_site(site, params, membership, scope)
```

- **Including a router joins paths and dependencies.** "You don't have to worry about performance when
  including routers" (FastAPI — Bigger Applications - Multiple Files). It checks nothing about the
  parent (inference), so the parent check has to be a dependency.
- **The flat `GET /assets/{asset_id}`** scopes the find in its service, eager-loads the chain
  (`joinedload(Asset.site).joinedload(Site.region)`), and filters `ancestors` by the read policy. Each
  level gets its own response model (`AssetListItem`; `AssetDetail` adds `parentId` and `ancestors`).
  Relationships use `lazy="raise"` (`std-fastapi`); deep trees use `Select.cte(recursive=True)`
  (`hierarchies.md`).

### Django / DRF

```python
# config/urls.py: router.register(r"assets", AssetViewSet) — members, flat; then
# site_router = NestedSimpleRouter(router, r"sites", lookup="site")          -> kwarg site_pk
# site_router.register(r"assets", SiteAssetViewSet, basename="site-assets")  -> /sites/{site_pk}/assets/
from rest_framework.generics import get_object_or_404  # also a 404 for a malformed ID, not a 500


class SiteAssetViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """The collection half of a shallow pair; retrieve/update/destroy live on AssetViewSet."""
    permission_classes = [IsAuthenticated, AssetPermission]  # list -> assets.read, create -> assets.create
    pagination_class = AssetCursorPagination  # ordering = ("-created_at", "-id"): unique

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)  # authentication and permission checks run first
        self.get_parent()  # EVERY action: create() never calls get_queryset() or get_object()

    def get_parent(self) -> Site:
        if not hasattr(self, "_parent"):  # memoized: one parent query per request
            m = self.request.membership
            self._parent = get_object_or_404(Site.objects.visible_to(m, scope_for(m, "sites.read")),
                                             pk=self.kwargs["site_pk"])  # another tenant's: Http404 -> the house 404
        return self._parent

    def get_serializer_class(self) -> type[BaseSerializer]:
        return AssetCreateSerializer if self.action == "create" else AssetListItemSerializer

    def get_queryset(self) -> QuerySet[Asset]:
        m = self.request.membership
        return (Asset.objects.visible_to(m, scope_for(m, "assets.read"))
                .filter(site=self.get_parent()).only("id", "name", "status", "site_id", "created_at"))

    def perform_create(self, serializer: AssetCreateSerializer) -> None:
        serializer.save(site=self.get_parent())  # AssetCreateSerializer has no writable `site` field


class AssetViewSet(mixins.RetrieveModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):
    serializer_class = AssetDetailSerializer
    permission_classes = [IsAuthenticated, AssetPermission]

    def get_queryset(self) -> QuerySet[Asset]:
        m = self.request.membership
        return Asset.objects.visible_to(m, scope_for(m, "assets.read")).select_related("site__region")
```

- **Authorize the parent for every action, not inside `get_queryset`.** `create()` validates and
  saves without calling `get_queryset()` or `get_object()`, so a parent check there never runs on a
  POST, and "object level permissions from the `has_object_permission()` method **are not applied**
  when creating objects" (Django REST framework — Permissions). `initial()` runs before every handler,
  after authentication and permission checks (Django REST framework — Views); the `Http404` it raises
  goes through the house `EXCEPTION_HANDLER`. `perform_create` takes the site from that lookup, never
  from the URL kwarg or the request body.
- **Scope `get_queryset` everywhere.** `has_object_permission` never runs on `list` (`std-django`). Map
  `CursorPagination` to the house envelope in `get_paginated_response`. Per level, use `only()` for
  rows, `select_related` for foreign-key chains, and `prefetch_related(Prefetch(...))` for an allowed
  include, and pin the count with `assertNumQueries` (`std-python-performance`).

```python
# apps/assets/tests/test_site_assets_api.py — the write path gets the same parent check as the list
@pytest.mark.django_db
def test_should_return_404_and_create_nothing_when_posting_to_another_tenants_site(sign_in):
    # Arrange: a caller who may create assets in their own organization, and a site in another one
    stranger = MembershipFactory(role="owner")
    foreign_site = SiteFactory()  # the factory builds a fresh organization
    client = sign_in(stranger)  # the project's fixture: through the house authentication class

    # Act
    response = client.post(reverse("site-assets-list", kwargs={"site_pk": foreign_site.pk}),
                           {"name": "Pump 9"}, format="json")

    # Assert
    assert response.status_code == 404
    assert not Asset.objects.filter(site=foreign_site).exists()
```

- **Sign in through the authentication class, not `force_authenticate`.** A forced user replaces the
  request's authenticators with DRF's `ForcedAuthentication` (Django REST framework — `request.py`),
  so the class that sets `request.membership` never runs and the test exercises nothing real.
- **drf-nested-routers** is "a work in progress", and its author "cannot warranty that it fully 'works
  everywhere' yet". It lists Django 4.2–5.2 and DRF 3.14–3.16 (alanjds — drf-nested-routers README).
  That fits `std-django`'s Django 5.x; recheck it before moving to Django 6, the current stable line
  (Django — Model field reference). Its README example filters by the kwarg with no parent check, so add
  one as shown above. Without the library, use a flat ViewSet with a django-filter `site` filter, and
  still scope-check the parent. A create there takes the parent from the body, so the writable `site`
  field is a `PrimaryKeyRelatedField` whose `get_queryset()` returns the caller's scoped sites
  (Django REST framework — Serializer relations), or `perform_create` checks it. A
  `queryset=Site.objects.all()` lets the body name any tenant's site.

## 14. Anti-patterns

| Anti-pattern | What you see | Fix |
|---|---|---|
| Deep nesting, or a member nested under its parent | long URLs; two URLs for one record; links break on a move | shallow routes (§2); `ancestors` in the detail |
| A request per level to draw a breadcrumb, or a trail built from history | slow deep links; an empty or wrong trail on refresh; revoked names linger | the server's filtered `ancestors` (§4); a summary endpoint |
| Unscoped counts | a `team` user sees "Assets 1,204" above a list of 12 | a scoped grouped count; stored counters at `org` only (§5) |
| `403` on a deep link, or a parent kwarg filtered but never authorized | probing IDs reveals which ones exist; `/sites/<other tenant>/assets` lists that tenant's rows | scope-then-find → `404`, parent first (§11) |
| N+1, offset, or an unrestricted `include` on a list level | query count grows with the page; deep pages slow; sensitive relations pulled | lean serializer + eager load + pinned count; cursor with a unique order; closed allow-list (§7) |
| ETag without viewer and `permissions_version`, or `public` caching | a demoted user gets a `304`; one user's rows reach another | §8; private caching, `'use cache: private'` |
| Full records broadcast on an organization channel | restricted names reach every subscriber | IDs + `ancestorIds`, then invalidate (§9) |

## 15. Per-project questions — not house rules

`requirements-consultant` asks these during discovery; `architecture-advisor` records the answers in an
ADR.

1. **Fixed levels or user-defined depth?** Can records move between parents? The answer picks the
   storage (`hierarchies.md`) and decides whether links must survive a move.
2. **How fresh is each badge?** Live, as a scoped count per request, or "as of N minutes ago", from a
   read model that returns `asOf`?
3. **Which lists need totals or page jumping?** Those use the offset exception.
4. **What does a partly restricted chain show?** Start at the first readable level (reveals nothing),
   or show a "Restricted" step (reveals that a level exists)?
5. **What does a link to something no longer accessible show?** Not-found, or "request access"? Offering
   access confirms the record exists.
6. **Search scope?** Global, or the current area? Do hits show their path?
7. **Which levels update live**, and where is fresh-on-revisit enough?
8. **Are opaque IDs acceptable in shared links, or do they need readable names?** Names need uniqueness
   rules and redirects on rename.

## Sources

- Ruby on Rails Guides — Rails Routing from the Outside In — https://guides.rubyonrails.org/routing.html
- GitHub Docs — REST API endpoints for issue comments — https://docs.github.com/en/rest/issues/comments
- Google (API Improvement Proposals) — AIP-121: Resource-oriented design — https://google.aip.dev/121
- Google (API Improvement Proposals) — AIP-122: Resource names — https://google.aip.dev/122
- Google (API Improvement Proposals) — AIP-132: Standard methods: List — https://google.aip.dev/132
- Google (API Improvement Proposals) — AIP-156: Singleton resources — https://google.aip.dev/156
- Google (API Improvement Proposals) — AIP-157: Partial responses — https://google.aip.dev/157
- Google (API Improvement Proposals) — AIP-158: Pagination — https://google.aip.dev/158
- Google (API Improvement Proposals) — AIP-193: Errors — https://google.aip.dev/193
- Microsoft — Azure REST API Guidelines — https://github.com/microsoft/api-guidelines/blob/vNext/azure/Guidelines.md
- Microsoft — Microsoft Graph REST API Guidelines — https://github.com/microsoft/api-guidelines/blob/vNext/graph/GuidelinesGraph.md
- Zalando SE — RESTful API Guidelines, Pagination chapter — https://github.com/zalando/restful-api-guidelines/blob/main/chapters/pagination.adoc
- Zalando SE — RESTful API Guidelines, Hypermedia chapter — https://github.com/zalando/restful-api-guidelines/blob/main/chapters/hyper-media.adoc
- Zalando SE — RESTful API Guidelines, Performance chapter — https://github.com/zalando/restful-api-guidelines/blob/main/chapters/performance.adoc
- IETF — RFC 8288: Web Linking — https://www.rfc-editor.org/rfc/rfc8288
- IETF — RFC 9110: HTTP Semantics — https://www.rfc-editor.org/rfc/rfc9110
- JSON:API — Specification v1.1 — https://jsonapi.org/format/1.1/
- Stripe — Expanding responses — https://docs.stripe.com/expand
- OWASP API Security Project — API1:2023 Broken Object Level Authorization — https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa1-broken-object-level-authorization.md
- OWASP API Security Project — API3:2023 Broken Object Property Level Authorization — https://github.com/OWASP/API-Security/blob/master/editions/2023/en/0xa3-broken-object-property-level-authorization.md
- PostgreSQL Global Development Group — 39.3. Materialized Views — https://www.postgresql.org/docs/current/rules-materializedviews.html
- Ruby on Rails API — ActiveRecord::Associations::ClassMethods — https://api.rubyonrails.org/classes/ActiveRecord/Associations/ClassMethods.html
- Ruby on Rails API — ActiveRecord::CounterCache::ClassMethods — https://api.rubyonrails.org/classes/ActiveRecord/CounterCache/ClassMethods.html
- Ruby on Rails API — ActionController::ConditionalGet — https://api.rubyonrails.org/classes/ActionController/ConditionalGet.html
- Ruby on Rails API — ActionController::ConditionalGet::ClassMethods — https://api.rubyonrails.org/classes/ActionController/ConditionalGet/ClassMethods.html
- Ruby on Rails Guides — Caching with Rails: An Overview — https://guides.rubyonrails.org/caching_with_rails.html
- Phlex — Fragment caching in Phlex Components — https://www.phlex.fun/components/caching
- Pagy (ddnexus) — :keyset — https://ddnexus.github.io/pagy/toolbox/paginators/keyset/
- Django REST framework — Pagination — https://www.django-rest-framework.org/api-guide/pagination/
- Django REST framework — Permissions — https://www.django-rest-framework.org/api-guide/permissions/
- Django REST framework — Views — https://www.django-rest-framework.org/api-guide/views/
- Django REST framework — Serializer relations — https://www.django-rest-framework.org/api-guide/relations/
- Django REST framework — `request.py` (forced authentication) — https://github.com/encode/django-rest-framework/blob/main/rest_framework/request.py
- Django Software Foundation — Model field reference — https://docs.djangoproject.com/en/stable/ref/models/fields/
- Casecommons — pg_search README — https://github.com/Casecommons/pg_search
- alanjds — drf-nested-routers README — https://github.com/alanjds/drf-nested-routers
- FastAPI — Bigger Applications - Multiple Files — https://fastapi.tiangolo.com/tutorial/bigger-applications/
- TanStack — Query Invalidation — https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation
- Vercel (Next.js documentation) — revalidateTag — https://nextjs.org/docs/app/api-reference/functions/revalidateTag
- Vercel (Next.js documentation) — updateTag — https://nextjs.org/docs/app/api-reference/functions/updateTag
- Vercel (Next.js documentation) — cacheTag — https://nextjs.org/docs/app/api-reference/functions/cacheTag
- Vercel (Next.js documentation) — Caching — https://nextjs.org/docs/app/getting-started/caching
