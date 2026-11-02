# 8.15 Angular lineage twin — the three LineageREST routes

- **Status:** in progress
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.8 (CL-61..CL-63, the Python twin), and the
  server's rules LIN-01..LIN-06 and LM-05.

The lib has no lineage client at all: `routes/lineage.py` answers three routes
and none of them has a method here, while 8.8 gave the Python twin
(`AtlasClient.lineage`) all three. This increment lands the same three routes
on the Angular side in a new `LineageService` and closes the pair.

## Scope

In scope: `GET /{guid}`, `POST /{guid}` (on demand), and
`GET /uniqueAttribute/type/{type_name}` of `routes/lineage.py` in a new
`LineageService`, the lineage DTOs in `atlas-lineage.ts`, and their Vitest
specs.

Out of scope: the lineage-model auxiliary API clients (a different service and
lib); any screen that calls the new methods; the entity, relationship, and
glossary Angular clients (increments 8.16 and after).

## Semantics

Each rule's id is named in its Vitest `it()` title, the APC family's
convention (the trace check reads pytest files only; the APC rules are already
in its gap list). The Python twin's methods are `get`, `get_on_demand`, and
`get_by_unique_attributes` on a `lineage` resource object; a flat service
cannot keep those bare names, so the methods compose the resource name
(`getLineage`, …), as `SearchService` did in 8.13.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ALN-01 | `getLineage(guid, depth = 3, direction = "BOTH")` answers `GET /atlas/v2/lineage/{guid}` and answers an `AtlasLineageInfo` (LIN-01..LIN-05, CL-61). It always sends `depth` and `direction` — the twin's shape (its `get` passes both defaults), not the `searchParams()` absence rule — because the route reads them as JAX-RS converts them with those defaults (DV-39). The guid rides the path percent-encoded (APC-01).                                                                            |
| ALN-02 | `getLineageOnDemand(guid, constraints?)` answers `POST /atlas/v2/lineage/{guid}` with the `{ guid: LineageOnDemandConstraints }` map as the JSON body, or no body when the map is missing or empty — the twin's `body or None` (LIN-06, CL-62). A server with the feature off answers `LINEAGE_ON_DEMAND_NOT_ENABLED` through the error channel (APC-04); the client does not pre-check the setting.                                                                                                    |
| ALN-03 | `getLineageByUniqueAttributes(typeName, attributes, depth = 3, direction = "BOTH")` answers `GET /atlas/v2/lineage/uniqueAttribute/type/{typeName}` (LIN-01, CL-63). Each unique attribute travels as an `attr:<name>` query parameter, as the route reads them (ERD-08's shape); `depth` and `direction` are always sent, per ALN-01. The type name rides the path percent-encoded (APC-01). Answers an `AtlasLineageInfo`.                                                                            |
| ALN-04 | A non-2xx answer of any of the three — including the 404 of a guid with no lineage (LM-05) — reaches the caller as the typed Atlas error (APC-04); the client maps no status itself (the twin raises the same, CL-04). The DTO cluster mirrors `aurelius_atlas_model/lineage.py` (APC-03): `AtlasLineageInfo`, `LineageRelation`, `LineageInfoOnDemand`, `LineageOnDemandConstraints`, `LineageDirection`. The `guidEntityMap` values reuse the `AtlasEntityHeader` DTO of `atlas-search.ts` unchanged. |

### The coverage matrix (`routes/lineage.py`, 3 routes)

Open means no client method yet. All 3 are covered as of this increment.

| Method and path                         | Server function                   | Client method                            | Rule   |
| --------------------------------------- | --------------------------------- | ---------------------------------------- | ------ |
| `GET /{guid}`                           | `get_lineage_graph`               | `getLineage` (covered)                   | ALN-01 |
| `POST /{guid}`                          | `get_lineage_graph_on_demand`     | `getLineageOnDemand` (covered)           | ALN-02 |
| `GET /uniqueAttribute/type/{type_name}` | `get_lineage_by_unique_attribute` | `getLineageByUniqueAttributes` (covered) | ALN-03 |

After this increment, `routes/lineage.py` is fully covered on both sides of
the wire.

Bodies, hand-mirrored (APC-03): `atlas-lineage.ts`, from
`aurelius_atlas_model/lineage.py` (the wire answer is `AtlasLineageInfo`'s
JSON; the Python twin reads it through its own lenient `LineageInfo` view,
CL-12, whose extra-fields-ignored rule means both classes accept the same
bodies). `constraints` reuses `LineageOnDemandConstraints`, whose `direction`
is a `LineageDirection` — the same three texts as the query parameter.

## Aurelius origin

- Apache Atlas 2.4.0 `LineageREST` (the three routes).
- This workspace: `routes/lineage.py` (paths, `direction`/`depth` parsing, the
  constraints map body, the `attr:` parameters) and the server's rules LIN-01
  ..LIN-07, cited, not restated. `AtlasClient.lineage` (CL-61..CL-63, in
  `libs/python/aurelius-atlas-server-client/specs/8-8-client-route-coverage/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decision: DD-217 (both-sides landing). No
new decision: always sending `depth` and `direction` is the twin's shape, not
a new one (ALN-01); against the lib's `searchParams()` habit it is deliberate
— the twin sends its two defaults and the route's JAX-RS parsing accepts
exactly those texts and numbers (DV-39).

## Acceptance

- Unit: `src/lib/atlas/lineage.service.spec.ts` names every method in an
  `it()` title with its URL, its body or parameters, and the rule ids
  (APC-10's pattern; Vitest `HttpTestingController`).
- Unit: ALN-01's always-sent defaults, ALN-02's empty-map-means-no-body, and
  ALN-03's `attr:` parameters each get their own `it()` — the three facts a
  caller or a future edit can get wrong silently.
- Unit: ALN-04's 404 passthrough gets its own `it()` (LM-05).
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
