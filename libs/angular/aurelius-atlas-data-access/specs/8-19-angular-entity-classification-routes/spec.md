# 8.19 Angular entity twin (3/3) — classifications, business metadata, labels

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.14 (DD-315's bytes pair), 8.17/8.18
  (AEN/AEW, the naming; `attr:` parameters; `AtlasEntityHeaders`), 8.9
  (CLE-01..CLE-12, the Python twin), and the server's rules CLS-03..CLS-09,
  CLA-04, BMD-01..BMD-05, BMI-01..BMI-05, LBL-01..LBL-04, DV-36, DV-19.

8.17 took the eight read and audit routes of `routes/entity.py` and 8.18 the
seven write and delete routes; this increment takes the last twenty-two —
the ten classification routes, the six business-metadata routes, and the six
label routes — and closes the `EntityREST` pair DD-217 opened.

## Scope

In scope: `GET/POST/PUT /guid/{guid}/classification[s]`, the two
`/uniqueAttribute/…/classification[s]` write siblings, the two
`DELETE …/classification/{name}` routes, `POST /bulk/classification`,
`POST /bulk/setClassifications`, the six `…/businessmetadata…` routes
(including the template download and the file import), and the six label
routes (`/guid/{guid}/labels` and its unique-attribute form) — on
`AtlasEntitiesService` — plus the PList, associate-request, and bulk-import
DTOs and their Vitest specs.

Out of scope: the glossary Angular client (8.20+); any screen that calls the
new methods.

## Semantics

The naming mirrors the twin's camelCased — no name of 8.17/8.18 collides, so
no `Entity`-qualified variants are needed here either. A 204 answer is a
`void` answer (the relationship delete's idiom, AREL-03). A body on a DELETE
crosses through `HttpClient.request("DELETE", …)`: the typed
`HttpClient.delete` takes none.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ACL-01 | `getClassification(guid, classificationName)` and `getClassifications(guid)` answer the two classification reads with an `AtlasClassification` and an `AtlasClassifications` `PList` (CLS-03, CLE-01). The routes read no query parameters (the PList's paging fields carry the server's whole-list answer).                                                                                                                                                              |
| ACL-02 | `addClassifications`/`updateClassifications` (POST/PUT `/guid/{guid}/classifications`) and their unique-attribute siblings take an `AtlasClassification[]` and send it as a bare JSON array; each answers 204 → `void` (CLS-04..CLS-06, CLS-08, CLE-05). The unique-attribute form sends the `attr:<name>` parameters of AEN-03.                                                                                                                                          |
| ACL-03 | `deleteClassification(guid, classificationName, associatedEntityGuid?)` and `deleteClassificationByUniqueAttributes(typeName, attributes, classificationName)` answer the two delete routes with 204 → `void` (CLS-09, CLE-05). The optional `associatedEntityGuid` travels only when given; the unique-attribute form carries `attr:<name>` and takes no association parameter — the route reads none.                                                                   |
| ACL-04 | `associateClassification(request)` answers `POST /bulk/classification` with the bare `ClassificationAssociateRequest` and 204 → `void` (CLS-07, CLE-01). The client checks nothing: without a classification or targets the server answers `INVALID_PARAMETERS` (CLE-12).                                                                                                                                                                                                 |
| ACL-05 | `setClassifications(headers)` answers `POST /bulk/setClassifications` with the bare `AtlasEntityHeaders` and answers a JSON array of per-guid summaries — `unknown[]`, never a model, never reordered (CLA-04, DV-36, CLE-08).                                                                                                                                                                                                                                            |
| ACL-06 | Business-metadata writes: `addOrUpdateBusinessMetadata(guid, attributes, isOverwrite?)` (body = the `{<bm>: <attrs\|null>}` map; `isOverwrite` travels only when true — BMD-01), `removeBusinessMetadata(guid, attributes)` (BMD-05, a DELETE with that body), and the `…Of(guid, bmName, attributes)` pair whose bodies are the bare attribute map — the server files it under the name in the path (BMD-03, BMD-05). All four answer 204 → `void` (CLE-07).             |
| ACL-07 | `businessMetadataTemplate()` answers the template download as the `{ body, contentType }` pair of DD-315's shape (`AtlasExportAnswer`, `responseType: "arraybuffer"`, BMI-01); `importBusinessMetadata(fileName, content)` posts a `multipart/form-data` body whose `file` part carries the bytes and answers a `BulkImportResponse` (BMI-02..BMI-05, CLE-09). The bytes are what the caller holds — the client never reads a path.                                       |
| ACL-08 | The six label routes follow the server's verb mapping, not intuition: `setLabels` (POST) makes the entity's labels exactly these, `addLabels` (PUT) adds them, `removeLabels` (DELETE, the body through `request`) takes them away — LBL-01..LBL-04, CLE-06 — and each has a unique-attribute sibling with the `attr:<name>` parameters. Every body is a bare JSON array of names; every answer is 204 → `void`.                                                          |
| ACL-09 | The DTO cluster mirrors the Python models (APC-03): `atlas-entity.ts` gains `AtlasClassifications` (the `PList` shape: `list`, `startIndex`, `pageSize`, `totalCount`, `sortBy`, `sortType`) and `ClassificationAssociateRequest`; `atlas-impexp.ts` gains `BulkImportResponse` and `ImportInfo` (the two lists Java writes only when non-empty; `rowNumber` is never written, so the DTO omits it). `AtlasClassification` and `AtlasEntityHeaders` are reused unchanged. |

### The coverage matrix (`routes/entity.py`, routes 16–37 of 37)

With this increment all thirty-seven routes are covered; 8.17's fifteen stay closed.

| Method and path                                       | Server function                              | Client method                                       | Rule   |
| ----------------------------------------------------- | -------------------------------------------- | --------------------------------------------------- | ------ |
| `GET /guid/{g}/classification/{c}`                    | `get_classification`                         | `getClassification` (covered)                       | ACL-01 |
| `GET /guid/{g}/classifications`                       | `get_classifications`                        | `getClassifications` (covered)                      | ACL-01 |
| `POST /guid/{g}/classifications`                      | `add_classifications`                        | `addClassifications` (covered)                      | ACL-02 |
| `POST /uniqueAttribute/type/{t}/classifications`      | `add_classifications_by_unique_attribute`    | `addClassificationsByUniqueAttributes` (covered)    | ACL-02 |
| `PUT /guid/{g}/classifications`                       | `update_classifications`                     | `updateClassifications` (covered)                   | ACL-02 |
| `PUT /uniqueAttribute/type/{t}/classifications`       | `update_classifications_by_unique_attribute` | `updateClassificationsByUniqueAttributes` (covered) | ACL-02 |
| `DELETE /guid/{g}/classification/{c}`                 | `delete_classification`                      | `deleteClassification` (covered)                    | ACL-03 |
| `DELETE /uniqueAttribute/type/{t}/classification/{c}` | `delete_classification_by_unique_attribute`  | `deleteClassificationByUniqueAttributes` (covered)  | ACL-03 |
| `POST /bulk/classification`                           | `add_classification`                         | `associateClassification` (covered)                 | ACL-04 |
| `POST /bulk/setClassifications`                       | `set_classifications`                        | `setClassifications` (covered)                      | ACL-05 |
| `POST /guid/{g}/businessmetadata`                     | `add_or_update_business_attributes`          | `addOrUpdateBusinessMetadata` (covered)             | ACL-06 |
| `DELETE /guid/{g}/businessmetadata`                   | `remove_business_attributes`                 | `removeBusinessMetadata` (covered)                  | ACL-06 |
| `POST /guid/{g}/businessmetadata/{bm}`                | `add_or_update_business_attributes` (one)    | `addOrUpdateBusinessMetadataOf` (covered)           | ACL-06 |
| `DELETE /guid/{g}/businessmetadata/{bm}`              | `remove_business_attributes` (one)           | `removeBusinessMetadataOf` (covered)                | ACL-06 |
| `GET /businessmetadata/import/template`               | `produce_template`                           | `businessMetadataTemplate` (covered)                | ACL-07 |
| `POST /businessmetadata/import`                       | `import_bm_attributes`                       | `importBusinessMetadata` (covered)                  | ACL-07 |
| `POST /guid/{g}/labels`                               | `set_labels`                                 | `setLabels` (covered)                               | ACL-08 |
| `PUT /guid/{g}/labels`                                | `add_labels`                                 | `addLabels` (covered)                               | ACL-08 |
| `DELETE /guid/{g}/labels`                             | `remove_labels`                              | `removeLabels` (covered)                            | ACL-08 |
| `POST /uniqueAttribute/type/{t}/labels`               | `set_labels_by_unique_attribute`             | `setLabelsByUniqueAttributes` (covered)             | ACL-08 |
| `PUT /uniqueAttribute/type/{t}/labels`                | `add_labels_by_unique_attribute`             | `addLabelsByUniqueAttributes` (covered)             | ACL-08 |
| `DELETE /uniqueAttribute/type/{t}/labels`             | `remove_labels_by_unique_attribute`          | `removeLabelsByUniqueAttributes` (covered)          | ACL-08 |

## Aurelius origin

- Apache Atlas 2.4.0 `EntityREST` (the twenty-two routes).
- This workspace: `routes/entity.py` (the `associatedEntityGuid` parameter,
  the `isOverwrite` flag, the `{<bm>: …}` body shapes, the `file` form part)
  and the server's rules CLS, CLA, BMD, BMI, LBL, cited, not restated.
  `AtlasClient.entity` (CLE-01..CLE-12, in
  `libs/python/aurelius-atlas-server-client/specs/8-9-client-entity-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing),
DD-315 (the template's `{ body, contentType }` pair, reused shape — the twin
returns the `(bytes, content-type)` tuple). No new decision. Two shapes
differ from the twin by platform, not by choice: a DELETE with a body rides
`HttpClient.request` (the typed `delete` takes none), and the template
answer is the typed pair rather than a tuple.

## Acceptance

- Unit: `atlas-entities.service.spec.ts` grows one `it()` per method naming
  its URL, its parameters or body, and the rule ids (APC-10's pattern); the
  8.17/8.18 tests keep passing unchanged.
- Unit: ACL-08's verb mapping (POST set / PUT add / DELETE remove) gets its
  own `it()` pinning all three verbs, as the twin's CLE-06 test does.
  ACL-03's "no `associatedEntityGuid`, no parameter" and ACL-06's
  "`isOverwrite` only when true" assert inside their methods' `it()`s.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
