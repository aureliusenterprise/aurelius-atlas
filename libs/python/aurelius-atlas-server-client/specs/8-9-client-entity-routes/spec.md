# 8.9 Client route coverage — entity

- **Status:** planned
- **Pull request:** —
- **Records:** DD-307 (the per-module live-check spec), DD-309 (bodies reused from
  `aurelius-atlas-model`), DD-310 (file routes carry raw bytes); cites 8.4
  (CL-01..CL-08, CL-10, DD-203/DD-205), 8.8 (CL-60..CL-65), and the server's own
  rules ERD, EWR, EDL, CLS, CLA, BMI, LBL, AUD, CAU.

`AtlasClient` has no entity surface at all, while the server's `routes/entity.py`
answers 37 routes. This increment adds `AtlasClient.entity`: reads by GUID and by
unique attributes, creates and updates, deletes, classifications, business
metadata, labels, audit events, and the changed-classifications bulk header. The
shape follows 8.8: one spec per module, and a coverage matrix a reviewer updates
when `routes/entity.py` changes.

## Scope

In scope:

- `AtlasClient.entity` — the 37 routes of `routes/entity.py`, in the matrix below.
- The read flags the server's retriever reads (`minExtInfo`,
  `ignoreRelationships`) and the `deleteType` override, as method parameters.
- The two file routes of the module (the business-metadata template and import)
  as bytes (DD-310).

Out of scope, with the increment that delivers it:

- The relationship routes — [8.11](../8-11-client-relationship-admin-routes/spec.md).
- The search and saved-search routes — 8.4 shipped seven;
  [8.12](../8-12-client-saved-search-dsl-routes/spec.md) ships the rest.
- Server behaviour: the rules of the routes themselves (ERD, EWR, EDL, CLS, CLA,
  BMI, LBL, AUD, CAU) stay specified by the server's own increments. This spec
  states only what the **client** must do on the way to them.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                  |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLE-01 | `AtlasClient.entity` exists as a resource API, built like `AdminApi`/`TypesApi`/`SearchApi` (8.4, DD-203), and every method of it is named in a `covers` marker. Its paths start at `ENTITY_ROOT = "api/atlas/v2/entity"` (CL-60).                                                                                                                                                    |
| CLE-02 | A read that the server serves through its retriever takes `min_ext_info` and `ignore_relationships` flags, both default `False`, and sends them as the query parameters `minExtInfo` and `ignoreRelationships` only when set (CL-13's default-absence rule). This covers the four ext-info reads: `by_guid`, `by_guids`, `by_unique_attributes`, and `entities_by_unique_attributes`. |
| CLE-03 | A read by unique attributes takes a `type_name` and a mapping of attributes, and renders each entry as an `attr:<name>=<value>` query parameter, as `routes/entity.py` reads them (ERD-08). The bulk variant takes a sequence of mappings and renders them as `attr_<n>:<name>`, 1-based, in the order given (DV-19).                                                                 |
| CLE-04 | A delete takes an optional `delete_type` (a `DeleteType`) and sends it as the `deleteType` query parameter only when given. The client has no default of its own: an absent parameter lets the server apply its own setting (EDL-04, DD-059).                                                                                                                                         |
| CLE-05 | A classification or label write answers 204; the client returns `None` and raises nothing (CL-04's success path). A body the server reads as a list of names goes as a JSON array.                                                                                                                                                                                                    |
| CLE-06 | The label verbs follow the server's mapping, not intuition: `POST .../labels` **sets** the labels, `PUT .../labels` **adds** them, and `DELETE .../labels` **removes** them (LBL-01..LBL-04). The same three verbs exist for the unique-attribute form of each.                                                                                                                       |
| CLE-07 | The two business-metadata routes that take a `bm_name` send the body as a plain JSON object of attribute values, and the pair without a name sends `{<bm_name>: {...}}` — as `routes/entity.py` builds them (BMD-01, BMD-03, BMD-05). The `isOverwrite` flag travels as a query parameter only when set.                                                                              |
| CLE-08 | `set_classifications` answers a JSON array of per-guid summaries rather than a model (the server's DV-36 text), so the client returns the parsed JSON value, not a model, and never reorders it.                                                                                                                                                                                      |
| CLE-09 | The business-metadata template and import cross as bytes (DD-310): the template returns `(bytes, content_type)` and the import sends `files={"file": (name, content)}` as `multipart/form-data`.                                                                                                                                                                                      |
| CLE-10 | `audit_events` takes `action` (an `EntityAuditActionV2`), `start_key`, `count` (default `None`, which the server reads as 100), `offset` (default `None`, which the server reads as -1), `sort_by`, and `sort_order`, and sends each only when set. It returns a list of `EntityAuditEventV2`.                                                                                        |
| CLE-11 | `changed_classifications(since)` renders the single `tagUpdateStartTime` parameter and returns the parsed `AtlasEntityHeaders`. The client sends no end time: the server uses its own clock (CAU-07).                                                                                                                                                                                 |
| CLE-12 | Every method raises `AtlasClientError` on a non-2xx answer (CL-04) and propagates `httpx` errors unchanged (CL-05). The client validates no request body the server validates: it sends the model's `to_json()` and lets the server answer (the 8.4 split — a client is not a second validator).                                                                                      |

### The coverage matrix (`routes/entity.py`, 37 routes)

Open means no client method yet. Each series PR marks its own rows covered.

| Method and path                                       | Server function                          | Client method                                 | Rule           |
| ----------------------------------------------------- | ---------------------------------------- | --------------------------------------------- | -------------- |
| `GET /guid/{guid}`                                    | `getById`                                | `by_guid`                                     | CLE-01, CLE-02 |
| `GET /guid/{guid}/header`                             | `getHeaderById`                          | `header_by_guid`                              | CLE-01         |
| `GET /uniqueAttribute/type/{t}`                       | `getByUniqueAttributes`                  | `by_unique_attributes`                        | CLE-02, CLE-03 |
| `GET /uniqueAttribute/type/{t}/header`                | `getEntityHeaderByUniqueAttributes`      | `header_by_unique_attributes`                 | CLE-03         |
| `GET /bulk/uniqueAttribute/type/{t}`                  | `getEntitiesByUniqueAttributes`          | `entities_by_unique_attributes`               | CLE-02, CLE-03 |
| `GET /bulk`                                           | `getByGuids`                             | `by_guids`                                    | CLE-02         |
| `GET /{guid}/audit`                                   | `getAuditEvents`                         | `audit_events`                                | CLE-10         |
| `GET /bulk/headers`                                   | `getEntityHeaders`                       | `changed_classifications`                     | CLE-11         |
| `POST ""`                                             | `createOrUpdate`                         | `create_or_update`                            | CLE-01         |
| `POST /bulk`                                          | `createOrUpdate` (bulk)                  | `create_or_update_bulk`                       | CLE-01         |
| `PUT /guid/{guid}`                                    | `partialUpdateEntityAttrByGuid`          | `partial_update_attribute`                    | CLE-01         |
| `PUT /uniqueAttribute/type/{t}`                       | `partialUpdateEntityByUniqueAttrs`       | `partial_update_by_unique_attributes`         | CLE-03         |
| `DELETE /guid/{guid}`                                 | `deleteByGuid`                           | `delete_by_guid`                              | CLE-04         |
| `DELETE /bulk`                                        | `deleteByGuids`                          | `delete_by_guids`                             | CLE-04         |
| `DELETE /uniqueAttribute/type/{t}`                    | `deleteByUniqueAttribute`                | `delete_by_unique_attributes`                 | CLE-03, CLE-04 |
| `GET /guid/{g}/classification/{c}`                    | `getClassification`                      | `get_classification`                          | CLE-01         |
| `GET /guid/{g}/classifications`                       | `getClassifications`                     | `get_classifications`                         | CLE-01         |
| `POST /guid/{g}/classifications`                      | `addClassifications`                     | `add_classifications`                         | CLE-05         |
| `POST /uniqueAttribute/type/{t}/classifications`      | `addClassificationsByUniqueAttribute`    | `add_classifications_by_unique_attributes`    | CLE-03, CLE-05 |
| `PUT /guid/{g}/classifications`                       | `updateClassifications`                  | `update_classifications`                      | CLE-05         |
| `PUT /uniqueAttribute/type/{t}/classifications`       | `updateClassificationsByUniqueAttribute` | `update_classifications_by_unique_attributes` | CLE-03, CLE-05 |
| `DELETE /guid/{g}/classification/{c}`                 | `deleteClassification`                   | `delete_classification`                       | CLE-05         |
| `DELETE /uniqueAttribute/type/{t}/classification/{c}` | `deleteClassificationByUniqueAttribute`  | `delete_classification_by_unique_attributes`  | CLE-03, CLE-05 |
| `POST /bulk/classification`                           | `addClassification`                      | `associate_classification`                    | CLE-01         |
| `POST /bulk/setClassifications`                       | `setClassifications`                     | `set_classifications`                         | CLE-08         |
| `POST /guid/{g}/businessmetadata`                     | `addOrUpdateBusinessAttributes`          | `add_or_update_business_metadata`             | CLE-07         |
| `DELETE /guid/{g}/businessmetadata`                   | `removeBusinessAttributes`               | `remove_business_metadata`                    | CLE-07         |
| `POST /guid/{g}/businessmetadata/{bm}`                | `addOrUpdateBusinessAttributes` (one)    | `add_or_update_business_metadata_of`          | CLE-07         |
| `DELETE /guid/{g}/businessmetadata/{bm}`              | `removeBusinessAttributes` (one)         | `remove_business_metadata_of`                 | CLE-07         |
| `GET /businessmetadata/import/template`               | `produceTemplate`                        | `business_metadata_template`                  | CLE-09         |
| `POST /businessmetadata/import`                       | `importBMAttributes`                     | `import_business_metadata`                    | CLE-09         |
| `POST /guid/{g}/labels`                               | `setLabels`                              | `set_labels`                                  | CLE-06         |
| `PUT /guid/{g}/labels`                                | `addLabels`                              | `add_labels`                                  | CLE-06         |
| `DELETE /guid/{g}/labels`                             | `removeLabels`                           | `remove_labels`                               | CLE-06         |
| `POST /uniqueAttribute/type/{t}/labels`               | `setLabels` (unique)                     | `set_labels_by_unique_attributes`             | CLE-03, CLE-06 |
| `PUT /uniqueAttribute/type/{t}/labels`                | `addLabels` (unique)                     | `add_labels_by_unique_attributes`             | CLE-03, CLE-06 |
| `DELETE /uniqueAttribute/type/{t}/labels`             | `removeLabels` (unique)                  | `remove_labels_by_unique_attributes`          | CLE-03, CLE-06 |

Bodies, reused whole (DD-309): `AtlasEntityWithExtInfo`,
`AtlasEntitiesWithExtInfo`, `AtlasEntityHeader`, `AtlasEntityHeaders`,
`AtlasClassifications`, `AtlasClassification`, `ClassificationAssociateRequest`,
`EntityMutationResponse` (the create/update/delete/purge answers),
`EntityAuditEventV2`, `EntityAuditActionV2`. The client imports them from
`aurelius-atlas-model` and defines none.

## Aurelius origin

- Apache Atlas 2.4.0 `EntityREST` (the 37 routes) and its client-side twin
  `AtlasEntityClient` / `EntityDiscoveryClient` in `libs/atlas/api` — the method
  names above match its vocabulary where one exists.
- This workspace: `apps/aurelius-atlas-server/aurelius_atlas_server/routes/entity.py`
  (the paths, the `attr:`/`attr_<n>:` parameter shapes, the flags, the 204s) and
  its specs `2-3-entity-read-rest`, `2-4-entity-write-rest`, `2-5-delete-semantics`
  (ERD/EWR/EDL/CLS/CLA/LBL/AUD/CAU rules, cited not restated).
- `aurelius-atlas-model`'s `instance/` package — every body (DD-309).

## Deviations

None of Atlas (ADR 052). The client adds no wire behaviour; the server's parity
scenarios already guard the routes. Workspace decisions: DD-307 (the spec shape),
DD-309 (reused bodies), DD-310 (bytes for file routes) in [8.8's
`design.md`](../8-8-client-route-coverage/design.md).

## Acceptance

- Unit: `tests/test__aurelius_atlas_server_client_entity.py` (new). One test per
  matrix row at minimum, each naming its method in `covers` and its rule ids; the
  `MockTransport` recorder of the 8.4 tests asserts method, path, query, and body
  for each. The CLE-06 label-verb test pins all three verbs in one test so a
  future swap fails loudly.
- Unit: the 8.8 conventions re-pinned here — a `delete_type=None` call sends no
  `deleteType` (CLE-04), and a set flag renders `true` (CL-13).
- e2e: the first real consumer lands with this PR or its follower — a
  container test that drives `AtlasClient.entity` against the running server and
  compares against the same fixtures the server's own e2e uses (8.4's pattern;
  the 8.2 suite shows the wiring). Where the SOPS key is absent, the unit suite
  is the gate and the e2e lands with the 5.x lineage e2e set.
- Trace: `uv run aurelius-atlas-trace check` names CLE-01..CLE-12 and does not
  grow the gap count.
- Gates: `nx test aurelius-atlas-server-client -c ci`, `ruff check`, `zensical
build --strict`.
