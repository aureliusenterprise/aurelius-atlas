# 3.3b Bulk classifications

- **Status:** in progress
- **Pull request:** –
- **Records:** DD-074, DV-36; relies on DD-070 to DD-073

The second part of increment 3.3 (DD-073): `bulk/setClassifications`, Atlas's `ClassificationAssociator.Updater`, which sets the classifications of entities found by their unique attributes to those their headers give. `bulk/headers` moves to 3.5, since it lists the entities whose classifications changed from the audit (DD-074).

## Scope

| Endpoint | Takes | Answers |
| --- | --- | --- |
| `POST /api/atlas/v2/entity/bulk/setClassifications` | `AtlasEntityHeaders` | a JSON array of one summary per operation |

In `aurelius-atlas-core`, `classification_associator` (`ClassificationAssociator`, its `Updater`), built on 3.3a's `EntityClassifications`. The server's `routes/entity` answers the endpoint.

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| `GET bulk/headers?tagUpdateStartTime` (`ClassificationAssociator.Retriever`, DD-074) | 3.5 |
| Propagated classifications among an entity's (DV-34) | 3.4 |

## Semantics

| Id | Rule |
| --- | --- |
| CLA-01 | Each header of `guidHeaderMap`, in the request's order, is handled on its own. One of a type that is no entity type adds `<type>: (Skipped)`. The entity is the `ACTIVE` one of the type, or a sub type, holding the unique values among the header's `attributes` (ENS-06); none adds `Entity:<type>:<name>:[Not found]:(Skipped)`, where `<name>` is the attribute name `qualifiedName` when the header's attributes have it, else the type's first unique attribute's name |
| CLA-02 | The header's classifications are those its `entityGuid` names the header's `guid`, or none, or the header has no `guid`; the entity's, as CLS-02 reads them, likewise for the entity's GUID. Matched by type name: the entity's without an incoming one are deleted, the incoming ones the entity has are updated (in the entity's order), the others added; nothing when both are empty |
| CLA-03 | Deletes run first, one by one (CLS-09), then the updates as one request (CLS-08), then the adds as one request (CLS-04, CLS-05); each changes the store at once. Each step adds `<Delete\\|Update\\|Add>:<guid>:<type>:<name> -> <classification names, comma separated>:<status>`, the status `(Done)`, or `(Partial)` when a request of the step failed |
| CLA-04 | The answer is a JSON array of the summaries, in the order they were added; `[]` for none |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/EntityREST.java#setClassifications`
- `repository/.../store/graph/v2/ClassificationAssociator.java`: `Updater` and `ListOps`
- `repository/.../store/graph/v2/AtlasGraphUtilsV2.java#findByUniqueAttributes`

## Deviations

DV-36: a header without `attributes`, a type without unique attributes, and a request without a body fail in Atlas with a `NullPointerException` or `NoSuchElementException`; Aurelius Atlas skips the header as one whose entity is not found, names `<no unique name>`, and answers `[]` for no body.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — CLA-01 to CLA-04 on the in-memory documents.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/entity/` — CLA-01 to CLA-04 over HTTP.
- `uv run aurelius-atlas-trace check`.
