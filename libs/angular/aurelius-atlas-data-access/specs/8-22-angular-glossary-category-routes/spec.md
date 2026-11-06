# 8.22 Angular glossary twin (3/3) — the categories

- **Status:** done
- **Pull request:** to follow
- **Records:** none new; cites DD-217 (the client lands on both sides of the
  wire), 7.3 (APC-01..APC-04), 8.20 (AGL, the service and `GlossaryPage`),
  8.21 (AGT, the keyed-map and partial-update idioms), and the server's rules
  GCT-01..GCT-07, GTM-06.

8.20 took the thirteen glossary routes of `routes/glossary.py` and 8.21 the
eleven term routes; this increment takes the last eight — the category
routes — and closes the `GlossaryREST` pair DD-217 opened.

## Scope

In scope: `GET /category/{category_guid}/terms`, `GET /category/{category_guid}`,
`GET /category/{category_guid}/related`, `POST /category`, `POST /categories`,
`PUT /category/{category_guid}`, `PUT /category/{category_guid}/partial`, and
`DELETE /category/{category_guid}` — on `GlossaryService` — plus their Vitest
specs.

Out of scope: none — all thirty-two routes of `routes/glossary.py` are
covered once this lands. No screen calls the new methods yet.

## Semantics

The methods land on the same `GlossaryService`, named after the twin's
(`client.glossary.category()` → `getCategory`, …). None collides with AGL's
or AGT's names. The idioms carry over unchanged: a 204 answer is `void`, an
empty partial-update map is refused client-side (CLG-03), the update sends
its body as given (CLG-08), the anchor is the server's check (CLG-05), and
the paging is 8.20's `GlossaryPage` (CLG-02).

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AGC-01 | `getCategory(categoryGuid)` answers `GET /category/{guid}` with an `AtlasGlossaryCategory` (GCT-01). `getCategoryTerms(categoryGuid, page?)` answers `GET /category/{guid}/terms` with an `AtlasRelatedTermHeader[]` (GTM-06); the paging follows `GlossaryPage` (CLG-02). `getRelatedCategories(categoryGuid)` answers `GET /category/{guid}/related` with a `Record<string, AtlasRelatedCategoryHeader[]>` keyed `parent`/`children` — a missing relation is absent (GCT-07, CLG-07).                    |
| AGC-02 | `createCategory(category)` and `createCategories(categories)` answer `POST /category` and `POST /categories` with the bare category or array of categories and answer it back (GCT-02). The anchor is not checked here — a category without one is the server's `MISSING_MANDATORY_ANCHOR` answer, as in the twin (CLG-05).                                                                                                                                                                                |
| AGC-03 | `updateCategory(categoryGuid, category)` answers `PUT /category/{guid}` with the bare `AtlasGlossaryCategory`; the body guid is not rewritten — the server grafts the path GUID (GCT-04, CLG-08). `partialUpdateCategory(categoryGuid, fields)` answers `PUT /category/{guid}/partial` with the bare attribute map (GCT-05) and answers the whole updated category; an empty map is refused client-side, mirroring the twin's `_no_fields` raise (CLG-03), and an unknown field stays the server's answer. |
| AGC-04 | `deleteCategory(categoryGuid)` answers `DELETE /category/{guid}`; the route answers 204, so the method is `Observable<void>` (GCT-06, CLG-09).                                                                                                                                                                                                                                                                                                                                                             |

### The coverage matrix (`routes/glossary.py`, the category routes)

With this increment all thirty-two routes are covered; 8.20's thirteen and
8.21's eleven stay closed.

| Method and path             | Server function                    | Client method                     | Rule   |
| --------------------------- | ---------------------------------- | --------------------------------- | ------ |
| `GET /category/{c}/terms`   | `get_category_terms`               | `getCategoryTerms` (covered)      | AGC-01 |
| `GET /category/{c}`         | `get_glossary_category`            | `getCategory` (covered)           | AGC-01 |
| `GET /category/{c}/related` | `get_related_categories`           | `getRelatedCategories` (covered)  | AGC-01 |
| `POST /category`            | `create_glossary_category`         | `createCategory` (covered)        | AGC-02 |
| `POST /categories`          | `create_glossary_categories`       | `createCategories` (covered)      | AGC-02 |
| `PUT /category/{c}`         | `update_glossary_category`         | `updateCategory` (covered)        | AGC-03 |
| `PUT /category/{c}/partial` | `partial_update_glossary_category` | `partialUpdateCategory` (covered) | AGC-03 |
| `DELETE /category/{c}`      | `delete_glossary_category`         | `deleteCategory` (covered)        | AGC-04 |

## Aurelius origin

- Apache Atlas 2.4.0 `GlossaryREST` (the eight category routes).
- This workspace: `routes/glossary.py` (the anchor check, the keyed related
  map, the partial-update bodies) and the server's rules GCT, cited, not
  restated. `AtlasClient.glossary` (CLG-01..CLG-09, in
  `libs/python/aurelius-atlas-server-client/specs/8-10-client-glossary-routes/spec.md`)
  is the twin this mirrors.

## Deviations

None of Atlas (ADR 052). Workspace decisions: DD-217 (both-sides landing). No
new decision. As in 8.20 and 8.21, the empty-partial-update refusal raises
synchronously out of the method call rather than out of an `await`.

## Acceptance

- Unit: `glossary.service.spec.ts` grows one `it()` per method naming its
  URL, its parameters or body, and the rule ids (APC-10's pattern).
- Unit: AGC-01's paging reuses the `GlossaryPage` pin (a default travels as
  absence); AGC-01's related map asserts the `parent`/`children` keys;
  AGC-03's empty map raises with no request.
- Gates: `nx test aurelius-atlas-data-access -c ci`,
  `nx lint aurelius-atlas-data-access`, `nx build aurelius-atlas-data-access`,
  `nx test aurelius-atlas-webapp -c ci` (the consumer).
