# 8.18 Angular entity twin (2/3) — the writes and the deletes

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.14 (`EntityMutationResponse`, `DeleteType`),
  8.17 (AEN-01..AEN-07, the reads and audits; the naming style), 8.9
  (CLE-01..CLE-12, the Python twin), and the server's rules EWR-02, EWR-14,
  EWR-15, EDL-01..EDL-04, DV-19.

8.17 took the eight read and audit routes of `routes/entity.py`; this
increment takes the seven write and delete routes. The remaining twenty-two
classification, business metadata, and labels routes are 8.19.

## Scope

In scope: `POST ""`, `POST /bulk`, `PUT /guid/{guid}`,
`PUT /uniqueAttribute/type/{type_name}`, `DELETE /guid/{guid}`,
`DELETE /bulk`, and `DELETE /uniqueAttribute/type/{type_name}` — on
`AtlasEntitiesService` — and their Vitest specs.

Out of scope: the classifications, business metadata, and labels routes
(8.19); the glossary Angular client; any screen that calls the new methods.

## Semantics

The naming follows 8.17: the `…ByGuid` / `…Entities…` /
`…ByUniqueAttributes` forms the read methods set, the write verbs plain.
Every write answers an `EntityMutationResponse` — the DTO 8.14 brought and
`AdminService.patches()`'s sibling, reused whole; `DeleteType` comes from the
same file (8.16 added it there). No DTO is new in this increment.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AEW-01 | `createOrUpdateEntity(entity)` answers `POST /atlas/v2/entity` with the bare `AtlasEntityWithExtInfo` as the request body and answers an `EntityMutationResponse` (EWR-02, CLE-01). The client validates nothing the server validates (CLE-12).                                                                                                                                                                                        |
| AEW-02 | `createOrUpdateEntities(entities)` answers `POST /bulk` with the bare `AtlasEntitiesWithExtInfo` and answers an `EntityMutationResponse` (EWR-02, CLE-01).                                                                                                                                                                                                                                                                             |
| AEW-03 | `partialUpdateAttribute(guid, value, name?)` answers `PUT /guid/{guid}` (EWR-15, CLE-01). The body is the bare JSON value — whatever it is, the server reads it as the attribute's new value. The optional `name` travels as a query parameter only when given. The answer is an `EntityMutationResponse` (CLE-01).                                                                                                                    |
| AEW-04 | `partialUpdateByUniqueAttributes(typeName, attributes, entity)` answers `PUT /uniqueAttribute/type/{typeName}` with the `attr:<name>` parameters of AEN-03 and the bare `AtlasEntityWithExtInfo` body, and answers an `EntityMutationResponse` (EWR-14, CLE-03).                                                                                                                                                                       |
| AEW-05 | `deleteEntityByGuid(guid, deleteType?)`, `deleteEntitiesByGuids(guids, deleteType?)` (the repeated `guid` of AEN-04), and `deleteEntityByUniqueAttributes(typeName, attributes, deleteType?)` (the `attr:<name>` of AEN-03) answer the three delete routes (EDL-01, EDL-02, CLE-04). The `deleteType` travels only when given — absent, the server applies its own setting (EDL-04). Every delete answers an `EntityMutationResponse`. |
| AEW-06 | The DTOs are all reused, none new: `EntityMutationResponse` and `DeleteType` from `atlas-mutation.ts` (8.14, 8.16), `AtlasEntityWithExtInfo` and `AtlasEntitiesWithExtInfo` from `atlas-entity.ts` (2.3, 8.17). Type names and guids ride the path percent-encoded (APC-01).                                                                                                                                                           |

### The coverage matrix (`routes/entity.py`, routes 9–15 of 37)

The eight reads of 8.17 stay closed; the remaining twenty-two close in 8.19.

| Method and path                            | Server function                         | Client method                               | Rule   |
| ------------------------------------------ | --------------------------------------- | ------------------------------------------- | ------ |
| `POST ""`                                  | `create_or_update`                      | `createOrUpdateEntity` (covered)            | AEW-01 |
| `POST /bulk`                               | `create_or_update_bulk`                 | `createOrUpdateEntities` (covered)          | AEW-02 |
| `PUT /guid/{guid}`                         | `partial_update_entity_attr_by_guid`    | `partialUpdateAttribute` (covered)          | AEW-03 |
| `PUT /uniqueAttribute/type/{type_name}`    | `partial_update_entity_by_unique_attrs` | `partialUpdateByUniqueAttributes` (covered) | AEW-04 |
| `DELETE /guid/{guid}`                      | `delete_by_guid`                        | `deleteEntityByGuid` (covered)              | AEW-05 |
| `DELETE /bulk`                             | `delete_by_guids`                       | `deleteEntitiesByGuids` (covered)           | AEW-05 |
| `DELETE /uniqueAttribute/type/{type_name}` | `delete_by_unique_attribute`            | `deleteEntityByUniqueAttributes` (covered)  | AEW-05 |

## Aurelius origin

- Apache Atlas 2.4.0 `EntityREST` (the seven write and delete routes).
- This workspace: `routes/entity.py` (the bare-value partial update, the
  `deleteType` override rule EDL-04, the repeated `guid`) and the server's
  rules EWR, EDL, cited, not restated. `AtlasClient.entity`
  (CLE-01..CLE-12, in
  `libs/python/aurelius-atlas-server-client/specs/8-9-client-entity-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing),
DD-311 (`DeleteType`'s client-side vocabulary, already recorded). No new
decision. Against the twin, one shape that differs: the twin's
`partial_update_attribute` takes `(guid, name, value)` with `name` possibly
`None`; AEW-03 puts the optional `name` last — an optional middle parameter
forces every caller to pass `undefined` explicitly.

## Acceptance

- Unit: `atlas-entities.service.spec.ts` grows one `it()` per method naming
  its URL, its parameters or body, and the rule ids (APC-10's pattern); the
  8.17 tests keep passing unchanged.
- Unit: AEW-03's "no `name`, no parameter" and AEW-05's "`deleteType` only
  when given" get their own asserts inside their method's `it()`.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
