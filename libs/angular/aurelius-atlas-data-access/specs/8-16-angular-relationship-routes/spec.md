# 8.16 Angular relationship twin — the four RelationshipREST routes

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.11 (CLR-01..CLR-04, the Python twin), and the
  server's rules REL-03..REL-08 and EDL-04.

The lib has no relationship client: `routes/relationship.py` answers four
routes and none has a method here, while 8.11 gave the Python twin
(`AtlasClient.relationship`) all four. This increment lands the same four
routes on the Angular side in a new `RelationshipService` and closes the pair.

## Scope

In scope: `POST ""`, `PUT ""`, `GET /guid/{guid}`, and `DELETE /guid/{guid}`
of `routes/relationship.py` in a new `RelationshipService`, the relationship
DTOs in `atlas-relationship.ts` and `DeleteType` in `atlas-mutation.ts`, and
their Vitest specs.

Out of scope: the entity and glossary Angular clients (increments 8.17 and
8.18); the relationship ends' validation (the server answers, REL-04..REL-07 —
the client checks nothing); any screen that calls the new methods.

## Semantics

Each rule's id is named in its Vitest `it()` title, the APC family's
convention (the trace check reads pytest files only; the APC rules are already
in its gap list). The twin's methods are `create`, `update`, `get`, and
`delete` on a `relationship` resource object; a flat service cannot keep those
bare names, so the methods compose the resource name (`createRelationship`,
…), as 8.15 did for lineage.

| Id      | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AREL-01 | `createRelationship(relationship)` and `updateRelationship(relationship)` `POST` and `PUT` `/atlas/v2/relationship` with the `AtlasRelationship` as the bare JSON body and answer the server's bare `AtlasRelationship` (REL-04..REL-07, CLR-03). Neither pre-checks the ends or the type; no body is the empty relationship the server builds (the twin sends `relationship.to_json()` of whatever it was given).                                                                                                                                                            |
| AREL-02 | `getRelationship(guid, extendedInfo = false)` answers `GET /atlas/v2/relationship/guid/{guid}` and answers an `AtlasRelationshipWithExtInfo` (REL-03, REL-06, CLR-02). `extendedInfo` travels as the `extendedInfo` query parameter only when true — the `_present` rule, the lib's `searchParams()` habit (an absent flag is Java's `false`). The answer is always the wrapper: the server wraps even the no-`extendedInfo` answer in `{"relationship": ...}`; `referredEntities` appears only when the flag was sent. The guid rides the path percent-encoded (APC-01).     |
| AREL-03 | `deleteRelationship(guid, deleteType?)` answers `DELETE /atlas/v2/relationship/guid/{guid}` and answers `void` (the 204) (REL-08, EDL-04, CLR-04). An absent `deleteType` sends no parameter — the server applies its own configured strategy; a given one travels as `deleteType` with the values `DEFAULT`, `SOFT`, `HARD` (the client-side `DeleteType` of DD-311, read in any case by the server).                                                                                                                                                                        |
| AREL-04 | The DTO cluster mirrors `aurelius_atlas_model/instance/relationship.py`, `relationship_with_ext_info.py`, `relationship_status.py`, and the client's own `DeleteType` (`models.py`, DD-311) — `AtlasRelationship` (its `AtlasStruct` base inlined: `typeName`, `attributes`), `AtlasRelationshipWithExtInfo`, `RelationshipStatus`, `DeleteType` (APC-03). `end1`/`end2` reuse `AtlasObjectId`, `propagateTags` reuses `PropagateTags`, the classification lists reuse `AtlasClassification`, `referredEntities` reuses `AtlasEntityHeader` — all unchanged from their files. |

### The coverage matrix (`routes/relationship.py`, 4 routes)

Open means no client method yet. All 4 are covered as of this increment.

| Method and path       | Server function | Client method                  | Rule    |
| --------------------- | --------------- | ------------------------------ | ------- |
| `POST ""`             | `create`        | `createRelationship` (covered) | AREL-01 |
| `PUT ""`              | `update`        | `updateRelationship` (covered) | AREL-01 |
| `GET /guid/{guid}`    | `get_by_id`     | `getRelationship` (covered)    | AREL-02 |
| `DELETE /guid/{guid}` | `delete_by_id`  | `deleteRelationship` (covered) | AREL-03 |

After this increment, `routes/relationship.py` is fully covered on both sides
of the wire.

## Aurelius origin

- Apache Atlas 2.4.0 `RelationshipREST` (the four routes).
- This workspace: `routes/relationship.py` (the always-wrapped `getById`
  answer, the `extendedInfo` flag, the `deleteType` override) and the server's
  rules REL-03..REL-08, cited, not restated. `AtlasClient.relationship`
  (CLR-01..CLR-04, in
  `libs/python/aurelius-atlas-server-client/specs/8-11-client-relationship-admin-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decision: DD-217 (both-sides landing). No
new decision: the always-wrapped `getRelationship` answer is a server fact both
twins keep (REL-06), and `DeleteType` joins `atlas-mutation.ts`, the delete
vocabulary's file, so the entity increment (8.17) reuses it without a second
definition.

## Acceptance

- Unit: `src/lib/atlas/relationship.service.spec.ts` names every method in an
  `it()` title with its URL, its body or parameters, and the rule ids
  (APC-10's pattern; Vitest `HttpTestingController`).
- Unit: AREL-02's always-wrapped answer without `referredEntities`, and its
  `extendedInfo=true` parameter only-when-set, each get their own `it()` —
  the two facts a caller can get wrong silently. AREL-03's absent-parameter
  case gets one too.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
