# 8.20 Angular glossary twin (1/3) — the glossaries

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.14 (DD-315's bytes pair), 8.16 (the flat
  method names for a resource-object twin), 8.17–8.19 (the naming and test
  pattern), and the server's rules GLS-01..GLS-06, GIM-01..GIM-06, DV-104.

`routes/glossary.py` serves thirty-two routes. This increment takes the
thirteen about glossaries themselves and starts a new service,
`GlossaryService` — the Angular twin of `AtlasClient.glossary`
(CLG-01..CLG-09, 8.10). Terms (8.21) and categories (8.22) finish the family.

## Scope

In scope: `GET`/`POST ""`, `GET /import/template`, `POST /import`,
`GET /{glossary_guid}`, `GET /{glossary_guid}/detailed`, the four paged
category and term reads (`/categories`, `/categories/headers`, `/terms`,
`/terms/headers`), `PUT /{glossary_guid}`, `PUT /{glossary_guid}/partial`,
and `DELETE /{glossary_guid}` — plus the glossary DTO cluster
(`atlas-glossary.ts`), the extended `AtlasRelatedTermHeader`, and their
Vitest specs.

Out of scope: the twenty-one term and category routes (8.21, 8.22); any
screen that calls the new methods.

## Semantics

A new service, not a growth of `AtlasEntitiesService`: the glossary family is
its own resource. As 8.15 and 8.16 did for lineage and relationships, the
twin's resource-object methods (`client.glossary.glossaries()`, …) become
flat verb-first names here. Every URL composes from `API_BASE_URL` (APC-01)
with `encodeURIComponent` on each GUID. A 204 answer is a `void` answer.

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AGL-01 | `getGlossary(glossaryGuid)` answers `GET /{glossary_guid}` with an `AtlasGlossary` and `getDetailedGlossary(glossaryGuid)` answers `/detailed` with an `AtlasGlossaryExtInfo` — the glossary plus `termInfo`/`categoryInfo` keyed by GUID (GLS-01, GLS-06). Neither route reads a query parameter.                                                                                                                                                                                                                                                                                                                                                      |
| AGL-02 | The five paged reads — `getGlossaries(page?)`, `getGlossaryCategories`/`getGlossaryCategoriesHeaders`, `getGlossaryTerms`/`getGlossaryTermsHeaders` — take a `GlossaryPage` (`limit`, `offset`, `sort`) and send the server's defaults as absence (CLG-02, GLS-05): an unset `limit`, `offset` or `sort` sends no parameter (the server reads them as -1, 0, `ASC`), and a value that is given always travels — an explicit `limit: -1` travels, `sort` is `"ASC" \| "DESC"`. The category/term reads answer `AtlasGlossaryCategory[]`/`AtlasGlossaryTerm[]`; the `/headers` siblings answer `AtlasRelatedCategoryHeader[]`/`AtlasRelatedTermHeader[]`. |
| AGL-03 | `createGlossary(glossary)` (POST) and `updateGlossary(glossaryGuid, glossary)` (PUT) send the bare `AtlasGlossary`; each answers it back (GLS-02, GLS-03). The update's body guid is not rewritten here — the server grafts the path GUID onto the body it stores, as in the twin (CLG-08). Nothing is validated locally.                                                                                                                                                                                                                                                                                                                               |
| AGL-04 | `partialUpdateGlossary(glossaryGuid, fields)` answers `PUT /{glossary_guid}/partial` with the bare attribute map (name, descriptions, language, usage — GLS-03) and answers the whole updated `AtlasGlossary`. An empty map is a caller bug the client refuses before any request, mirroring the twin's `_no_fields` raise (CLG-03); an unknown field stays the server's answer (`INVALID_PARTIAL_UPDATE_ATTR`).                                                                                                                                                                                                                                        |
| AGL-05 | `deleteGlossary(glossaryGuid)` answers `DELETE /{glossary_guid}`; the route answers 204, so the method is `Observable<void>` (GLS-04, CLG-09). No `deleteType` parameter exists on this route.                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| AGL-06 | `glossaryImportTemplate()` answers the template download as the `{ body, contentType }` pair of DD-315's shape (`AtlasExportAnswer`, `responseType: "arraybuffer"`, GIM-06, CLG-06); `importGlossaryData(fileName, content)` posts a `multipart/form-data` body whose `file` part carries the bytes and answers a `BulkImportResponse` (GIM-01..GIM-05, DV-104). The bytes are what the caller holds — the client never reads a path.                                                                                                                                                                                                                   |
| AGL-07 | `atlas-glossary.ts` mirrors the Python glossary models (APC-03): `AtlasGlossary`, `AtlasGlossaryCategory`, `AtlasGlossaryTerm`, `AtlasGlossaryExtInfo`, `AtlasRelatedObjectId`, `AtlasGlossaryHeader`, `AtlasRelatedCategoryHeader`, `AtlasTermCategorizationHeader`, and `GlossarySort`. Since TypeScript has no inheritance, `AtlasGlossaryBaseObject`'s six fields are written into each of the three model types. `AtlasRelatedTermHeader` is one wire type, not two: it is extended in place in `atlas-entity.ts` (the entity's meanings use it too) to the model's ten fields, and gains `AtlasTermRelationshipStatus`.                           |

### The coverage matrix (`routes/glossary.py`, routes 1–13 of 32)

| Method and path               | Server function                   | Client method                            | Rule   |
| ----------------------------- | --------------------------------- | ---------------------------------------- | ------ |
| `GET ""`                      | `get_glossaries`                  | `getGlossaries` (covered)                | AGL-02 |
| `POST ""`                     | `create_glossary`                 | `createGlossary` (covered)               | AGL-03 |
| `GET /import/template`        | `produce_template`                | `glossaryImportTemplate` (covered)       | AGL-06 |
| `POST /import`                | `import_glossary_data`            | `importGlossaryData` (covered)           | AGL-06 |
| `GET /{g}`                    | `get_glossary`                    | `getGlossary` (covered)                  | AGL-01 |
| `GET /{g}/detailed`           | `get_detailed_glossary`           | `getDetailedGlossary` (covered)          | AGL-01 |
| `GET /{g}/categories`         | `get_glossary_categories`         | `getGlossaryCategories` (covered)        | AGL-02 |
| `GET /{g}/categories/headers` | `get_glossary_categories_headers` | `getGlossaryCategoriesHeaders` (covered) | AGL-02 |
| `GET /{g}/terms`              | `get_glossary_terms`              | `getGlossaryTerms` (covered)             | AGL-02 |
| `GET /{g}/terms/headers`      | `get_glossary_term_headers`       | `getGlossaryTermsHeaders` (covered)      | AGL-02 |
| `PUT /{g}`                    | `update_glossary`                 | `updateGlossary` (covered)               | AGL-03 |
| `PUT /{g}/partial`            | `partial_update_glossary`         | `partialUpdateGlossary` (covered)        | AGL-04 |
| `DELETE /{g}`                 | `delete_glossary`                 | `deleteGlossary` (covered)               | AGL-05 |

The nineteen term and category routes (`/term…`, `/terms…`, `/category…`,
`/categories…`, `/terms/{g}/assignedEntities`) stay open for 8.21 and 8.22.

## Aurelius origin

- Apache Atlas 2.4.0 `GlossaryREST` (the thirteen glossary routes).
- This workspace: `routes/glossary.py` (the paging parameters, the
  `file` form part, the partial-update bodies) and the server's rules GLS and
  GIM, cited, not restated. `AtlasClient.glossary` (CLG-01..CLG-09, in
  `libs/python/aurelius-atlas-server-client/specs/8-10-client-glossary-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing) and
DD-315 (the template's `{ body, contentType }` pair, reused shape — the twin
returns the `(bytes, content-type)` tuple). No new decision. One shape
differs from the twin by platform: the empty-partial-update refusal raises
synchronously out of the method call rather than out of an `await`, since
Angular methods return an `Observable` and no request is made at all.

## Acceptance

- Unit: `glossary.service.spec.ts` — one `it()` per method naming its URL,
  its parameters or body, and the rule ids (APC-10's pattern).
- Unit: AGL-02's paging gets its own `it()`s: no page sends no parameters;
  an explicit `limit: -1` travels; `offset: 0` and `limit: 0` stay absent;
  a given `sort` travels. AGL-04's empty map is asserted to raise with no
  request made.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
