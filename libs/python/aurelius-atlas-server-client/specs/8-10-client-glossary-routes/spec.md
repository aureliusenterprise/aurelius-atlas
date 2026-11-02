# 8.10 Client route coverage — glossary

- **Status:** planned
- **Pull request:** —
- **Records:** DD-307 (the per-module live-check spec), DD-309 (bodies reused from
  `aurelius-atlas-model`), DD-310 (file routes carry raw bytes); cites 8.4
  (CL-01..CL-08, CL-10), 8.8 (CL-60..CL-65), and the server's rules GLS, GCT, GTM,
  GTA, GIM.

The server's `routes/glossary.py` answers 32 routes — glossaries, categories,
terms, the term-to-entity assignments, and the CSV/Excel import. `AtlasClient` has
no glossary surface. This increment adds `AtlasClient.glossary` and its coverage
matrix, in the shape 8.8 sets.

## Scope

In scope: the 32 routes of `routes/glossary.py`, the shared paging parameters, and
the two file routes (the import template, the import) as bytes (DD-310).

Out of scope: server-side behaviour (GLS/GCT/GTM/GTA/GIM rules stay in the
server's specs, cited not restated); the Angular data-access mirror (8.4's
out-of-scope list stands); entity assignment targets beyond `AtlasRelatedObjectId`
(8.9 ships the entity half).

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CLG-01 | `AtlasClient.glossary` exists as a resource API (DD-203) with paths from `GLOSSARY_ROOT = "api/atlas/v2/glossary"` (CL-60), and every method is named in a `covers` marker.                                                                                                                                                                                                                                                                                                                                                                                                        |
| CLG-02 | A paged read sends the server's `_page` parameters `limit` (default -1, meaning every item), `offset` (default 0), and `sort` (default `ASC`), as query parameters, and each default travels as absence (the client sends `limit=-1` only when the caller passes it). This applies to every method whose matrix row says "paged".                                                                                                                                                                                                                                                  |
| CLG-03 | The partial-update verbs send a bare JSON object of attribute values to `PUT .../partial` and raise `ValueError` client-side when the caller passes no fields at all, because the server answers `BAD_REQUEST` for an empty body (NO_PARTIAL_UPDATES; the client's error names the same rule, GTM-04/GCT-05/GLS-03). The set of settable fields is the model's `set_attribute` contract, and the client does not pre-validate it — the server answers `INVALID_PARTIAL_UPDATE_ATTR` (CL-12 of 8.4: a client is not a second validator; this rule only covers the empty-body case). |
| CLG-04 | The term-assignment trio (`POST`, `PUT`, `DELETE /terms/{term_guid}/assignedEntities`) all take a list of `AtlasRelatedObjectId` and all answer 204; the client returns `None`. `PUT` and `DELETE` reach the same server behaviour (GTA-03), and the client keeps both names so a caller states its intent.                                                                                                                                                                                                                                                                        |
| CLG-05 | The term and category create methods do **not** check the anchor locally (GTM-02, GCT-02): the client sends the model as-is and lets the server answer `MISSING_MANDATORY_ANCHOR` (CL-04).                                                                                                                                                                                                                                                                                                                                                                                         |
| CLG-06 | The import template returns `(bytes, content_type)` (the download of the header line); the import sends `files={"file": (name, content)}` as `multipart/form-data` (DD-310, GIM-01..GIM-06).                                                                                                                                                                                                                                                                                                                                                                                       |
| CLG-07 | `get_related_terms` and `get_related_categories` return a mapping of relation name to list of related headers (`AtlasRelatedTermHeader` / `AtlasRelatedCategoryHeader`), parsed from the server's keyed JSON. The page parameters the server reads and ignores on the term variant (GTM-06) the client simply does not send.                                                                                                                                                                                                                                                       |
| CLG-08 | A term/category/glossary update whose body lacks a guid is the **caller's** model, not the client's: the client sends it as given (the server grafts the path guid, GTM-04/GCT-04/GLS-03).                                                                                                                                                                                                                                                                                                                                                                                         |
| CLG-09 | The delete methods answer 204 and return `None`; the create/update/get methods return the model (`AtlasGlossary`, `AtlasGlossaryCategory`, `AtlasGlossaryTerm`) or a list of them; the header variants return lists of `AtlasGlossaryHeader`.                                                                                                                                                                                                                                                                                                                                      |

### The coverage matrix (`routes/glossary.py`, 32 routes)

| Method and path                              | Server function                          | Client method                         | Rule   |
| -------------------------------------------- | ---------------------------------------- | ------------------------------------- | ------ |
| `GET ""`                                     | `getGlossaries`                          | `glossaries` (paged)                  | CLG-02 |
| `POST ""`                                    | `createGlossary`                         | `create_glossary`                     | CLG-01 |
| `GET /import/template`                       | `produceTemplate`                        | `import_template`                     | CLG-06 |
| `POST /import`                               | `importGlossaryData`                     | `import_data`                         | CLG-06 |
| `GET /term/{term_guid}`                      | `getGlossaryTerm`                        | `term`                                | CLG-01 |
| `POST /term`                                 | `createGlossaryTerm`                     | `create_term`                         | CLG-05 |
| `POST /terms`                                | `createGlossaryTerms`                    | `create_terms`                        | CLG-05 |
| `PUT /term/{term_guid}`                      | `updateGlossaryTerm`                     | `update_term`                         | CLG-08 |
| `PUT /term/{term_guid}/partial`              | `partialUpdateGlossaryTerm`              | `partial_update_term`                 | CLG-03 |
| `DELETE /term/{term_guid}`                   | `deleteGlossaryTerm`                     | `delete_term`                         | CLG-09 |
| `GET /terms/{term_guid}/related`             | `getRelatedTerms`                        | `related_terms`                       | CLG-07 |
| `GET /terms/{term_guid}/assignedEntities`    | `getEntitiesAssignedWithTerm`            | `assigned_entities` (paged)           | CLG-02 |
| `POST /terms/{term_guid}/assignedEntities`   | `assignTermToEntities`                   | `assign_term`                         | CLG-04 |
| `DELETE /terms/{term_guid}/assignedEntities` | `removeTermAssignmentFromEntities`       | `remove_term_assignment`              | CLG-04 |
| `PUT /terms/{term_guid}/assignedEntities`    | `disassociateTermAssignmentFromEntities` | `disassociate_term_assignment`        | CLG-04 |
| `GET /category/{category_guid}/terms`        | `getCategoryTerms`                       | `category_terms` (paged)              | CLG-02 |
| `GET /category/{category_guid}`              | `getGlossaryCategory`                    | `category`                            | CLG-01 |
| `GET /category/{category_guid}/related`      | `getRelatedCategories`                   | `related_categories`                  | CLG-07 |
| `POST /category`                             | `createGlossaryCategory`                 | `create_category`                     | CLG-05 |
| `POST /categories`                           | `createGlossaryCategories`               | `create_categories`                   | CLG-05 |
| `PUT /category/{category_guid}`              | `updateGlossaryCategory`                 | `update_category`                     | CLG-08 |
| `PUT /category/{category_guid}/partial`      | `partialUpdateGlossaryCategory`          | `partial_update_category`             | CLG-03 |
| `DELETE /category/{category_guid}`           | `deleteGlossaryCategory`                 | `delete_category`                     | CLG-09 |
| `GET /{glossary_guid}`                       | `getGlossary`                            | `glossary`                            | CLG-01 |
| `GET /{glossary_guid}/detailed`              | `getDetailedGlossary`                    | `detailed_glossary`                   | CLG-01 |
| `GET /{glossary_guid}/categories`            | `getGlossaryCategories`                  | `glossary_categories` (paged)         | CLG-02 |
| `GET /{glossary_guid}/categories/headers`    | `getGlossaryCategoriesHeaders`           | `glossary_categories_headers` (paged) | CLG-02 |
| `GET /{glossary_guid}/terms`                 | `getGlossaryTerms`                       | `glossary_terms` (paged)              | CLG-02 |
| `GET /{glossary_guid}/terms/headers`         | `getGlossaryTermHeaders`                 | `glossary_terms_headers` (paged)      | CLG-02 |
| `PUT /{glossary_guid}`                       | `updateGlossary`                         | `update_glossary`                     | CLG-08 |
| `PUT /{glossary_guid}/partial`               | `partialUpdateGlossary`                  | `partial_update_glossary`             | CLG-03 |
| `DELETE /{glossary_guid}`                    | `deleteGlossary`                         | `delete_glossary`                     | CLG-09 |

Bodies, reused whole (DD-309): `AtlasGlossary`, `AtlasGlossaryCategory`,
`AtlasGlossaryTerm`, `AtlasGlossaryHeader`, `AtlasRelatedCategoryHeader`,
`AtlasRelatedTermHeader`, `AtlasRelatedObjectId`. The client imports them from
`aurelius-atlas-model`'s `glossary` module and defines none.

## Aurelius origin

- Apache Atlas 2.4.0 `GlossaryREST` and the Angular `AtlasGlossaryClient` in
  `libs/atlas/api` — the method names above match its vocabulary.
- This workspace: `routes/glossary.py` (paths, the `_page` defaults, the 204s,
  the NO_PARTIAL_UPDATES body rule) and the glossary increments' specs (GLS,
  GCT, GTM, GTA, GIM — cited, not restated).
- `aurelius-atlas-model`'s `glossary` package — every body (DD-309).

## Deviations

None of Atlas (ADR 052). The CLG-03 client-side empty-body `ValueError` is the
only pre-flight check the series adds; it exists because the empty case is a
caller bug, not a wire race, and the server's own `BAD_REQUEST` stays reachable
for any body the client does send. Workspace decisions: DD-307, DD-309, DD-310 in
[8.8's `design.md`](../8-8-client-route-coverage/design.md).

## Acceptance

- Unit: `tests/test__aurelius_atlas_server_client_glossary.py` (new). One test
  per matrix row naming its method and rules, `MockTransport` recorder asserting
  method, path, query (the paging defaults absent), and body.
- Unit: CLG-03's empty-fields error and CLG-07's keyed-mapping parse each get a
  dedicated test.
- Trace: `uv run aurelius-atlas-trace check` names CLG-01..CLG-09.
- Gates: `nx test aurelius-atlas-server-client -c ci`, `ruff check`, `zensical
build --strict`.
