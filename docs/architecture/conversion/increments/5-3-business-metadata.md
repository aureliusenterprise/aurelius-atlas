# 5.3b Business metadata

- **Status:** done
- **Pull request:** to follow
- **Records:** DD-302, DV-117, DV-118; relies on DD-052, DD-084, DD-300, DD-301

Business metadata types (1.x) declare attributes that apply to chosen entity types. This part stores their values
on entities. An entity can be given them when it is created and reads them back. They are added, updated,
overwritten and removed by their own endpoints, validated against their definitions, audited, and checked
with the privilege 6.2b left for 5.3. Their CSV import follows in 5.3c. Searching on them is not part of 5.3.

## Scope

| Endpoint                                                                     | Atlas method                      |
| ---------------------------------------------------------------------------- | --------------------------------- |
| `POST /api/atlas/v2/entity/guid/{guid}/businessmetadata?isOverwrite=`        | `addOrUpdateBusinessAttributes`   |
| `DELETE /api/atlas/v2/entity/guid/{guid}/businessmetadata`                   | `removeBusinessAttributes`        |
| `POST /api/atlas/v2/entity/guid/{guid}/businessmetadata/{bmName}`            | `addOrUpdateBusinessAttributes`   |
| `DELETE /api/atlas/v2/entity/guid/{guid}/businessmetadata/{bmName}`          | `removeBusinessAttributes`        |
| `POST /api/atlas/v2/entity`, `/bulk`; `GET /api/atlas/v2/entity/guid/{guid}` | `businessAttributes` of an entity |

In `aurelius-atlas-core`, `entity_business_metadata` (`EntityBusinessMetadata` and the mapping functions), the
business attributes of a read in `entity_retriever`, of a created entity in `entity_writer`, their notification
and audit event. In `aurelius-atlas-server`, the four routes in `routes/entity`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BMD-01 | The endpoints by GUID take a JSON object of attribute values by business metadata; those by name take the attribute values of that business metadata. No body is none; any other body is `BAD_REQUEST` (DV-10). `isOverwrite` is true only for `true` in any case. Each answers 204 without a body                                                                                                                                                                                                                                            |
| BMD-02 | An entity's business attributes are those of its type's business metadata with a value, by business metadata and attribute name, in a full read's `businessAttributes`, absent when there is none (DV-117). A created entity takes those it is given of its type's business metadata, each mapped as an attribute value is; a business metadata, attribute or null value its type does not have or need is left out. An update leaves them as they are                                                                                        |
| BMD-03 | Adding or updating needs a GUID and a non-empty object (`INVALID_PARAMETERS`) and the entity (`INSTANCE_GUID_NOT_FOUND`). Every problem is then reported at once (`INSTANCE_CRUD_INVALID_PARAMS`): a business metadata its type does not have, a value invalid for its attribute, a string longer than the attribute's `maxStrLength`, and a mandatory attribute without a value given or stored. Each attribute given is set; a null sets the attribute's optional default, removing a string. A value that stays is not counted as a change |
| BMD-04 | With `isOverwrite`, every business attribute of the entity's type becomes the value given, and one given none is removed; a mandatory attribute must be given. The entity is written at the request's time and user even when nothing changes                                                                                                                                                                                                                                                                                                 |
| BMD-05 | Removing needs a GUID, a non-empty object and the entity. Each attribute named is removed, or every attribute of a business metadata given no values. Each counts as a change, with or without a value                                                                                                                                                                                                                                                                                                                                        |
| BMD-06 | A change that is written tells the audit a `BUSINESS_ATTRIBUTE_UPDATE` for each business metadata it changed, `Updated business attributes:` then a struct's JSON of the business metadata's name and the values given its changed attributes, null for one removed. A created entity's come after the classifications it is given, before the next entity's and before the creates                                                                                                                                                           |
| AUZ-17 | Adding or updating needs `ENTITY_UPDATE_BUSINESS_METADATA` for each business metadata of the entity's type whose values change, `add/update business-metadata: guid=<guid>, business-metadata-name=<name>`, before validation: one given null counts only when overwriting, and one whose given and stored values are both empty, or equal, does not count. Removing needs it for each business metadata named, `remove business-metadata: guid=<guid>, business-metadata=<name>`                                                             |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `addOrUpdateBusinessAttributes`, `removeBusinessAttributes` (both
  forms)
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `addOrUpdateBusinessAttributes`,
  `removeBusinessAttributes`, `validateBusinessAttributes`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `mapAttributesAndClassifications` (created entities),
  `setBusinessAttributes`, `addOrUpdateBusinessAttributes`, `removeBusinessAttributes`, `mapAttribute`
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `getBusinessMetadata`, `mapBusinessAttributes`
- `repository/.../store/graph/v2/AtlasEntityChangeNotifier.java`: `onBusinessAttributesUpdated`
- `repository/.../audit/EntityAuditListenerV2.java`: `onBusinessAttributesUpdated`
- `intg/.../type/AtlasBusinessMetadataType.java`: `AtlasBusinessAttribute#isValidLength`

## Deviations

- **DV-117:** business metadata and their attributes come in the entity type's order, where Atlas's maps give
  hash order.
- **DV-118:** a business metadata given as `null` to add or update, or a `businessmetadata/{bmName}` post
  without a body, is taken as one given no values; Atlas fails on the null.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_business_metadata.py` — BMD-02 to BMD-06 and AUZ-17 on the
  in-memory documents, with the audit events in order.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_business_metadata.py` — BMD-01 to BMD-06 and
  AUZ-17 through the routes.
- `apps/aurelius-atlas-server/scenarios/entity/entity-business-metadata.scenario.yaml` — the parity scenario.
- `uv run aurelius-atlas-trace check`.
