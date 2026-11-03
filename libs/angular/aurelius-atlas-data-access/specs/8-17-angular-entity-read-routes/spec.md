# 8.17 Angular entity twin (1/3) — the reads and the audits

- **Status:** in progress
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), DET-03 (the existing by-guid read), 8.9
  (CLE-01..CLE-12, the Python twin), and the server's rules ERD-01..ERD-09,
  AUD-06..AUD-09, CAU-07, DV-19.

`AtlasEntitiesService` answers one of the thirty-seven routes of
`routes/entity.py` (DET-03, 2.3/7.6), while 8.9 gave the Python twin
(`AtlasClient.entity`) all thirty-seven. Thirty-seven methods do not fit one
pull request (the ~1,500-line split rule), so the entity family lands in
three: this increment takes the eight read and audit routes, 8.18 takes the
seven writes and deletes, and 8.19 takes the remaining twenty-two
classifications, business metadata, and labels routes.

## Scope

In scope: `GET /guid/{guid}`, `GET /guid/{guid}/header`,
`GET /uniqueAttribute/type/{type_name}` with its `/header` sibling,
`GET /bulk`, `GET /bulk/uniqueAttribute/type/{type_name}`,
`GET /{guid}/audit`, and `GET /bulk/headers` — on `AtlasEntitiesService` —
plus the audit, bulk, and headers DTOs and their Vitest specs.

Out of scope: the entity writes, deletes, classifications, business metadata,
and labels routes (8.18 and 8.19); the glossary Angular client; any screen
that calls the new methods.

## Semantics

Each rule's id is named in its Vitest `it()` title, the APC family's
convention (the trace check reads pytest files only; the APC rules are already
in its gap list). DET-03's existing `getEntityByGuid` sets the naming style:
`get…`, the Java `EntityREST` client names — not 8.15's compose-the-resource
shape, because this service already exists and its first method's name is a
settled rule id. The existing method keeps its name and its no-parameter
default behaviour (its DET-03 test stays green).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AEN-01 | `getEntityByGuid(guid, minExtInfo = false, ignoreRelationships = false)` answers `GET /guid/{guid}` with an `AtlasEntityWithExtInfo` (ERD-02, CLE-02). Each flag travels as its query parameter only when true — the Java-default-absence rule of APC-11 — so the default call sends no parameter, exactly as DET-03's existing test asserts. 8.17 extends the method; DET-03 is not edited.                                                                                                                                                                               |
| AEN-02 | `getEntityHeaderByGuid(guid)` and `getEntityHeaderByUniqueAttributes(typeName, attributes)` answer the two `…/header` routes and answer an `AtlasEntityHeader` (ERD-07). The header read carries no flags: the route reads none (CLE-02's shape).                                                                                                                                                                                                                                                                                                                          |
| AEN-03 | `getEntityByUniqueAttributes(typeName, attributes, minExtInfo = false, ignoreRelationships = false)` answers `GET /uniqueAttribute/type/{typeName}` and answers an `AtlasEntityWithExtInfo` (ERD-08, CLE-02, CLE-03). Each entry of `attributes` travels as an `attr:<name>` query parameter (the route's `getAttributes` shape, ERD-08); the flags follow AEN-01. Type names and guids ride the path percent-encoded (APC-01).                                                                                                                                            |
| AEN-04 | `getEntitiesByGuids(guids, minExtInfo = false, ignoreRelationships = false)` and `getEntitiesByUniqueAttributes(typeName, attributeSets, minExtInfo = false, ignoreRelationships = false)` answer `GET /bulk` and `GET /bulk/uniqueAttribute/type/{typeName}` and answer an `AtlasEntitiesWithExtInfo` (ERD-01, ERD-08, CLE-02). Every guid travels as a repeated `guid` parameter in the given order; each attribute set renders as `attr_<n>:<name>` parameters, 1-based, in order (DV-19) — the bulk twin's numbering, distinct from AEN-03's single-set `attr:<name>`. |
| AEN-05 | `getAuditEvents(guid, query)` answers `GET /{guid}/audit` and answers an `EntityAuditEventV2[]` (AUD-06..AUD-09, CLE-10). The query object's six fields (`auditAction`, `startKey`, `count`, `offset`, `sortBy`, `sortOrder`) each travel only when given — and a given `count` of 0 or `offset` of -1 travels too: unlike AEN-01's flags, those are choices, not defaults (the twin drops only what is left unset). No field given sends no parameter.                                                                                                                    |
| AEN-06 | `getChangedClassifications(since)` answers `GET /bulk/headers` with `tagUpdateStartTime` set to the epoch-milliseconds value and answers an `AtlasEntityHeaders` (CAU-07, CLE-11). The client sends no end time — the server uses its own clock.                                                                                                                                                                                                                                                                                                                           |
| AEN-07 | The DTO cluster mirrors the Python models (APC-03): `AtlasEntitiesWithExtInfo` and `AtlasEntityHeaders` join `atlas-entity.ts` / `atlas-search.ts`, and `atlas-audit.ts` carries `EntityAuditEventV2`, `EntityAuditActionV2`, and `EntityAuditType` from `aurelius_atlas_model/audit.py`. The audit event's `entity` reuses `AtlasEntity` unchanged; the header map values reuse `AtlasEntityHeader` unchanged. Java writes the audit event with every key, nulls included — the DTO's fields are all optional.                                                            |

### The coverage matrix (`routes/entity.py`, first eight of 37 routes)

Open means no client method yet; the other 29 routes close in 8.18 and 8.19.

| Method and path                                | Server function                          | Client method                                 | Rule   |
| ---------------------------------------------- | ---------------------------------------- | --------------------------------------------- | ------ |
| `GET /guid/{guid}`                             | `get_by_id`                              | `getEntityByGuid` (extended)                  | AEN-01 |
| `GET /guid/{guid}/header`                      | `get_header_by_id`                       | `getEntityHeaderByGuid` (covered)             | AEN-02 |
| `GET /uniqueAttribute/type/{type_name}`        | `get_by_unique_attributes`               | `getEntityByUniqueAttributes` (covered)       | AEN-03 |
| `GET /uniqueAttribute/type/{type_name}/header` | `get_entity_header_by_unique_attributes` | `getEntityHeaderByUniqueAttributes` (covered) | AEN-02 |
| `GET /bulk`                                    | `get_by_guids`                           | `getEntitiesByGuids` (covered)                | AEN-04 |
| `GET /bulk/uniqueAttribute/type/{type_name}`   | `get_entities_by_unique_attributes`      | `getEntitiesByUniqueAttributes` (covered)     | AEN-04 |
| `GET /{guid}/audit`                            | `get_audit_events`                       | `getAuditEvents` (covered)                    | AEN-05 |
| `GET /bulk/headers`                            | `get_entity_headers`                     | `getChangedClassifications` (covered)         | AEN-06 |

## Aurelius origin

- Apache Atlas 2.4.0 `EntityREST` (the eight read routes) and the
  `EntityREST`-shaped client names DET-03's method already follows.
- This workspace: `routes/entity.py` (the `attr:` / `attr_<n>:` parameter
  shapes, the repeated `guid`, the audit paging defaults `count` 100 / `offset`
  -1) and the server's rules ERD, AUD, CAU, cited, not restated.
  `AtlasClient.entity` (CLE-01..CLE-12, in
  `libs/python/aurelius-atlas-server-client/specs/8-9-client-entity-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing),
DD-187 (DET-03's method stays as it is). No new decision. The audit-query
drop-only-what-is-unset rule (AEN-05) is the twin's own deviation from its
`_present` helper (CLE-10), mirrored here, not a new one. Against the twin,
the one shape that differs: the twin's `audit_events` takes six keyword
parameters while AEN-05 takes one query object — six optional positional
parameters in TypeScript invite argument-order mistakes; the object is the
lib's `BasicSearchQuery` habit (7.3).

## Acceptance

- Unit: `atlas-entities.service.spec.ts` grows one `it()` per new method
  naming its URL, its parameters or body, and the rule ids (APC-10's
  pattern); DET-03's two existing tests keep passing unchanged.
- Unit: AEN-05's "a 0 count travels" gets its own `it()` — the one case the
  lib's default-absence habit would silently drop. AEN-04's 1-based
  `attr_<n>:` numbering gets one too.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
