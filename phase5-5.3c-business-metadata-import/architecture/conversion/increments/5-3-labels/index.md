# 5.3a Labels

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DV-116; relies on DD-021, DD-052, DD-084, DD-300, DD-301

An entity's labels are free words a steward attaches to it. They are stored with the entity since 2.4 (EWR-09), can be searched (`__labels`), and are returned on every read. This first part of 5.3 serves the endpoints that set, add and remove labels, records what each change did in the entity's audit, and checks the label privileges that 6.2b left for this increment. Business metadata follows in 5.3b, and its CSV import in 5.3c.

## Scope

| Endpoint | Atlas method |
| --- | --- |
| `POST /api/atlas/v2/entity/guid/{guid}/labels`, `.../uniqueAttribute/type/{typeName}/labels` | `setLabels` |
| `PUT /api/atlas/v2/entity/guid/{guid}/labels`, `.../uniqueAttribute/type/{typeName}/labels` | `addLabels` |
| `DELETE /api/atlas/v2/entity/guid/{guid}/labels`, `.../uniqueAttribute/type/{typeName}/labels` | `removeLabels` |

In `aurelius-atlas-core`, `entity_labels` (`EntityLabels`), the label notifications of `entity_change_notifier` and their audit events in `entity_audit_listener`, and the labels of a created entity told by `entity_writer`. In `aurelius-atlas-server`, the six routes in `routes/entity`.

## Semantics

| Id | Rule |
| --- | --- |
| LBL-01 | Each endpoint takes a JSON array of labels, or no body for none; any other body is `BAD_REQUEST` (DV-10). A label given twice counts once. Each answers 204 without a body. By unique attributes, the `typeName` is checked for length and must be an entity type (`TYPE_NAME_INVALID`), and an entity must hold the `attr:` values (`INSTANCE_BY_UNIQUE_ATTRIBUTE_NOT_FOUND`) |
| LBL-02 | Setting labels needs the entity (`INSTANCE_GUID_NOT_FOUND`) and valid labels: at most 50 characters (`INVALID_LABEL_LENGTH`) of letters, digits, `_`, `-` or CJK characters (`INVALID_LABEL_CHARACTERS`, its quotes taken as escapes by `MessageFormat`). The entity's labels become those given, none for no body or an empty array. The entity is written with the request's time and user even when its labels stay |
| LBL-03 | Adding labels needs at least one (`INVALID_PARAMETERS`, `labels is null/empty`), the entity and valid labels. The labels the entity does not have are appended; when it has them all, nothing is written |
| LBL-04 | Removing labels needs at least one, the entity and valid labels. The labels the entity has among them are removed; when it has none of them, nothing is written. An entity left without labels has none (`null` stored, `[]` read) |
| LBL-05 | A change that is written tells the entity's audit what it removed, `LABEL_DELETE` with the details `Deleted labels:` and the labels, each after a space, then what it added, `LABEL_ADD` with `Added labels:` and the labels, each only when there is one. Creating an entity with labels records its `LABEL_ADD` before the classifications it is given and its `ENTITY_CREATE` |
| AUZ-16 | Setting labels needs `ENTITY_ADD_LABEL` for each label added, `add label: guid=<guid>, label=<label>`, and `ENTITY_REMOVE_LABEL` for each removed, `remove label: ...`, checked once the labels are validated. Adding needs `ENTITY_ADD_LABEL` for each label given, `add/update label: ...`, and removing `ENTITY_REMOVE_LABEL` for each given, `remove label: ...`, both checked before the labels are validated. Nothing is written when a check refuses |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java`: `setLabels`, `addLabels`, `removeLabels` (by GUID and by unique attributes)
- `repository/.../store/graph/v2/AtlasEntityStoreV2.java`: `setLabels`, `addLabels`, `removeLabels`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `setLabels`, `addLabels`, `removeLabels`, `updateLabels`, `validateLabels`, `createVertexWithGuid` (the labels of a created entity)
- `repository/.../store/graph/v2/AtlasEntityChangeNotifier.java`: `onLabelsUpdatedFromEntity`
- `repository/.../audit/EntityAuditListenerV2.java`: `onLabelsAdded`, `onLabelsDeleted`

## Deviations

- **DV-116:** Atlas keeps labels in a `HashSet`, so an entity's labels, and those an audit event lists, come in the set's hash order. Aurelius keeps them in the order first given (DD-021): a set's labels after those the entity had, an add's new labels after the entity's own.

Atlas writes each audit event under a key of the entity, the millisecond and the event's place in its batch; two events of one label change in the same millisecond share a key, and HBase keeps the second. Aurelius keeps both. Their order between themselves is then not defined, so the scenario reads them by action.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/test__entity_labels.py` — LBL-02 to LBL-05 and AUZ-16 on the in-memory documents, with the audit events in order.
- `apps/aurelius-atlas-server/tests/test__aurelius_atlas_server_labels.py` — LBL-01 to LBL-05 and AUZ-16 through the routes.
- `apps/aurelius-atlas-server/scenarios/entity/entity-labels.scenario.yaml` — the parity scenario.
- `uv run aurelius-atlas-trace check`.
