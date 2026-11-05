# 8.8 Client route coverage — foundation and lineage

- **Status:** done
- **Pull request:** —
- **Records:** DD-307 (one live-check spec per server route module), DD-308 (the
  `LINEAGE_ROOT` fix), DD-309 (client methods reuse `aurelius-atlas-model` bodies),
  DD-310 (raw bytes for file routes); cites 8.4 (CL-01..CL-13, DD-203/DD-205),
  8.7 (CL-08)

This increment closes the drift between the server's routes and `AtlasClient`. At
the 2026-11-02 review the client answered 33 of the server's 124 endpoints:
`types` in full, five of twelve `admin` routes, seven of fifteen `discovery`
routes, and nothing for `entity`, `glossary`, or `relationship`. Increment 8.4
put those routes out of scope and said each later increment adds its client
methods (its Scope). This increment and its siblings 8.9 to 8.12 make that
promise true.

The series keeps one spec per server route module, so a change to
`routes/<module>.py` has one spec to update. 8.4 and 8.7 stay as they are.

## Scope

In scope, in this increment:

- `AtlasClient.lineage` — the three routes of `routes/lineage.py`
  (`GET /{guid}`, `POST /{guid}`, `GET /uniqueAttribute/type/{type_name}`), and
  the **fix** of `LINEAGE_ROOT` from `v2/lineage` to `api/atlas/v2/lineage`
  (DD-308).
- The **coverage matrix**: a table of every server route of every module in the
  spec of that module, marked covered or open, with the client method name.
  Each sibling spec carries its own table; 8.8 carries the whole view.
- The client-wide conventions the siblings share (CL-60..CL-65 below): path
  constants, parameter rendering, binary and multipart routes, and the two
  `login.py` routes that stay out.

Out of scope, with the increment that delivers it:

- `entity` routes (37) — [8.9](../8-9-client-entity-routes/spec.md).
- `glossary` routes (32) — [8.10](../8-10-client-glossary-routes/spec.md).
- `relationship` routes (4) and the `admin` writes and tasks (7) —
  [8.11](../8-11-client-relationship-admin-routes/spec.md).
- The saved searches and `GET /dsl` of `discovery` (8) —
  [8.12](../8-12-client-saved-search-dsl-routes/spec.md).
- The Angular data-access lib and any code generator (8.4's own out-of-scope
  list stands).

## Semantics

Rules of this increment, with ids tests name in
`@pytest.mark.covers(..., rules=["..."])`. The 8.4 rules (CL-01..CL-08, CL-10..
CL-13) apply to every new method and are not restated.

| Id    | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CL-60 | The path constants of the client carry the `api/atlas` prefix: `ADMIN_ROOT`, `TYPES_ROOT`, `DISCOVERY_ROOT`, and the new `LINEAGE_ROOT = "api/atlas/v2/lineage"`, `ENTITY_ROOT = "api/atlas/v2/entity"`, `GLOSSARY_ROOT = "api/atlas/v2/glossary"`, `RELATIONSHIP_ROOT = "api/atlas/v2/relationship"`. `LINEAGE_ROOT` changes from `v2/lineage`, which matched the legacy host this workspace had before the server's feed landed (DD-308).                                        |
| CL-61 | `AtlasClient.lineage.get(guid, depth=3, direction="BOTH")` answers `GET api/atlas/v2/lineage/{guid}` with `direction` and `depth` as query parameters, and returns the client library's own `LineageInfo` (the CL-12 model — the lenient, UUID-keyed body 8.2 consumes; not `aurelius-atlas-model`'s strict `AtlasLineageInfo`). `get_lineage` on the client stays as a thin alias for one release-cycle, so the 8.2 app keeps working, and its docstring points to `lineage.get`. |
| CL-62 | `AtlasClient.lineage.get_on_demand(guid, constraints=None)` answers `POST api/atlas/v2/lineage/{guid}`; each value of the `guid -> LineageOnDemandConstraints` mapping is reused from `aurelius-atlas-model` (DD-309). The answer is the client library's `LineageInfo` (CL-12); a server that answers the disabled feature raises `AtlasClientError` (CL-04), and the client has no setting of its own.                                                                           |
| CL-63 | `AtlasClient.lineage.get_by_unique_attributes(type_name, attributes, depth=3, direction="BOTH")` answers `GET api/atlas/v2/lineage/uniqueAttribute/type/{type_name}`. Each attribute renders as an `attr:<name>=<value>` query parameter, as `routes/lineage.py` reads it.                                                                                                                                                                                                         |
| CL-64 | A client method that answers a file route sends the bytes itself: an export returns `(bytes, content_type)`, and an import takes a filename and bytes and sends a `multipart/form-data` body (`files=` in httpx terms). The client never reads a path from disk, and never opens a file. A download route answers 204 for an empty result; the client returns empty bytes for that answer (DD-310).                                                                                |
| CL-65 | The client covers no browser route: `login.py`'s sign-in and logout stay outside it. They are the Keycloak redirect flow of a browser, not an API a service calls (6.1a).                                                                                                                                                                                                                                                                                                          |

The `_present` rule of `SearchApi` (8.4, CL-13: Java defaults false and 0 travel
as absence) applies to every GET route of the siblings that reads its parameters
through `first_value`/`flag`/`java_number`.

### The coverage matrix (whole client, after the series)

| Server module            | Endpoints | Client surface                                                                                                                 | Spec       |
| ------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| `routes/admin.py`        | 12        | `AdminApi`: 5 today (version, status, session, liveness, readiness) + patches, purge, export, import, importfile, tasks (8.11) | 8.11       |
| `routes/types.py`        | 20        | `TypesApi`: 20 today                                                                                                           | 8.4 (done) |
| `routes/entity.py`       | 37        | `EntityApi` (new)                                                                                                              | 8.9        |
| `routes/relationship.py` | 4         | `RelationshipApi` (new)                                                                                                        | 8.11       |
| `routes/discovery.py`    | 15        | `SearchApi`: 7 today + dsl + saved (8.12)                                                                                      | 8.12       |
| `routes/lineage.py`      | 3         | `LineageApi` (new, this increment)                                                                                             | 8.8        |
| `routes/glossary.py`     | 32        | `GlossaryApi` (new)                                                                                                            | 8.10       |
| `routes/login.py`        | 2         | none, by rule CL-65                                                                                                            | 8.8        |

After the series every module is covered in full. Each spec repeats this shape
for its own module, route by route.

## Aurelius origin

The reference is Apache Atlas 2.4.0 and the server's own routes:

- `LineageREST` (`GET/POST {guid}`, `GET uniqueAttribute/type/{typeName}`) —
  the three lineage routes; the server ports them in 5.1
  (`routes/lineage.py`, LIN-01..LIN-07).
- `AdminResource` — the lineage feed's legacy path on the Java host had no
  `/api/atlas` prefix on some Aurelius deployments; this workspace's server
  mounts everything under `/api/atlas`, and the client now mirrors that
  (DD-308).
- This workspace: `apps/aurelius-atlas-server/aurelius_atlas_server/`
  `routes/lineage.py` and `app.py` (the mounted prefixes), and
  `aurelius-atlas-model`'s `lineage.py` (`LineageInfo`, `LineageDirection`,
  `LineageOnDemandConstraints` — the bodies the client reuses).
- `libs/angular/aurelius-atlas-data-access` — the Angular twin the client
  matches in shape (8.4's origin list).

## Deviations

None of Atlas (ADR 052 — the client speaks the server's wire, the server's
parity already guards it). Workspace decisions: DD-307 (the per-module spec
shape), DD-308 (the `LINEAGE_ROOT` fix), DD-309 (bodies reused from
`aurelius-atlas-model`), DD-310 (file routes carry raw bytes) in
[`design.md`](./design.md).

## Acceptance

Unit (naming rules per ADR 056; run `uv run pytest
libs/python/aurelius-atlas-server-client/tests`):

- `tests/test__aurelius_atlas_server_client_lineage.py` (new): every method of
  `LineageApi` named in `covers`, each rule id above named on a test, each on a
  `MockTransport` recorder (the 8.4 pattern). The `get_lineage` alias test pins
  the new prefix (CL-60).
- Updated: the `covers` list in
  `tests/test__aurelius_atlas_server_client_client.py` gains the `lineage`
  methods; the 8.2 app's tests keep passing unmodified (the alias).
- Trace: `uv run aurelius-atlas-trace check` reports CL-60..CL-63 as named.
  CL-64 names its first test with the first file route (8.11's export/import, or
  8.9's business-metadata pair if it lands first); CL-65 is a scope rule and is
  named by the absence of a login method — no test of its own.
- e2e: the 8.2 app's e2e keeps its `fixture-atlas` (it answers the legacy
  path); the lineage client's paths prove against the server container when the
  5.1 lineage e2e runs in the same PR set, or a named `AtlasClient`-against-
  server test lands in 8.9's e2e with the entity routes (the first consumer).
- Gates: `nx test aurelius-atlas-server-client -c ci`, `ruff check`, and
  `zensical build --strict` clean.
