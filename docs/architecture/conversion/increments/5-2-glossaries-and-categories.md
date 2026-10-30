# 5.2a Glossaries and categories

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-246, DV-99, DV-100; relies on DD-043, DD-061, DD-064, DV-39

The first part of increment 5.2 (split by the user on 2026-10-30): glossaries and their categories, as
`GlossaryREST` and `GlossaryService` with `GlossaryCategoryUtils` answer them. Atlas keeps them as entities of
`AtlasGlossary` and `AtlasGlossaryCategory` (`0011-glossary_model`) through `DataAccess` and the glossary
DTOs; Aurelius Atlas does the same through its entity and relationship stores (DD-246). Terms are 5.2b, their
assignment to entities 5.2c; glossary import is a later increment.

## Scope

| Endpoint                                                      | Answers                                       |
| ------------------------------------------------------------- | --------------------------------------------- |
| `GET /api/atlas/v2/glossary`                                  | `AtlasGlossary[]` (`limit`, `offset`, `sort`) |
| `POST /api/atlas/v2/glossary`                                 | `AtlasGlossary`                               |
| `GET`, `PUT`, `DELETE /api/atlas/v2/glossary/{guid}`          | `AtlasGlossary`, nothing (204)                |
| `PUT /api/atlas/v2/glossary/{guid}/partial`                   | `AtlasGlossary`                               |
| `GET /api/atlas/v2/glossary/{guid}/detailed`                  | `AtlasGlossaryExtInfo`                        |
| `GET /api/atlas/v2/glossary/{guid}/categories`                | `AtlasGlossaryCategory[]`                     |
| `GET /api/atlas/v2/glossary/{guid}/categories/headers`        | `AtlasRelatedCategoryHeader[]`                |
| `POST /api/atlas/v2/glossary/category`, `categories`          | `AtlasGlossaryCategory`, `[]`                 |
| `GET`, `PUT`, `DELETE /api/atlas/v2/glossary/category/{guid}` | `AtlasGlossaryCategory`, nothing (204)        |
| `PUT /api/atlas/v2/glossary/category/{guid}/partial`          | `AtlasGlossaryCategory`                       |
| `GET /api/atlas/v2/glossary/category/{guid}/related`          | `{parent, children}` of category headers      |

`aurelius_atlas_model.glossary` (the glossary, category and header models), `aurelius_atlas_core.glossary_dto`
(`AtlasGlossaryDTO`, `AtlasGlossaryCategoryDTO` with `DataAccess`), `aurelius_atlas_core.glossary_service`
(`GlossaryService`, the glossary and category part) and `aurelius_atlas_core.glossary_category_utils`
(`GlossaryCategoryUtils`), and the server's `routes/glossary`.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                 |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| GLS-01 | A glossary is an `AtlasGlossary` entity: `qualifiedName`, `name`, `shortDescription`, `longDescription`, `language`, `usage`, `additionalAttributes`; its `terms` and `categories` are the headers of its anchored terms and categories, each with the relationship's GUID, display text (the name) and attributes                                                                   |
| GLS-02 | Creating a glossary takes its `qualifiedName`, else its `name` (`GLOSSARY_QUALIFIED_NAME_CANT_BE_DERIVED` without, `INVALID_DISPLAY_NAME` for a name with `@`, `.`, `<` or `>`); one of the same qualified name fails with `GLOSSARY_ALREADY_EXISTS`                                                                                                                                 |
| GLS-03 | Updating a glossary needs a name (`BAD_REQUEST` `DisplayName can't be null/empty`, `INVALID_DISPLAY_NAME`); it keeps the stored GUID and qualified name and is written only when it differs. A partial update sets `name`, `shortDescription`, `longDescription`, `language` or `usage` (`INVALID_PARTIAL_UPDATE_ATTR` for another; `BAD_REQUEST` `PartialUpdates missing or empty`) |
| GLS-04 | Deleting a glossary deletes its categories (GCT-06), then the glossary                                                                                                                                                                                                                                                                                                               |
| GLS-05 | Every glossary is listed, deleted ones too, by qualified name (DV-100; `sort` `DESC` reverses it, anything else is `ASC`), a glossary's categories by display text; `limit` -1 (default) is all, `offset` 0 (default) the first; an offset past the end answers none. A `limit` or `offset` that is no number fails with `BAD_REQUEST` (DV-99)                                       |
| GLS-06 | A read of a GUID that is no glossary fails with `UNEXPECTED_TYPE`, of a deleted one with `INSTANCE_GUID_DELETED`, of none with `INSTANCE_GUID_NOT_FOUND`; the detailed glossary adds `categoryInfo` (and from 5.2b `termInfo`), each by GUID                                                                                                                                         |
| GCT-01 | A category is an `AtlasGlossaryCategory` entity anchored to its glossary: `anchor` (the glossary's GUID and the relationship's), `parentCategory`, `childrenCategories` (active ones), `terms`; related headers carry the category's name as display text and its parent's GUID                                                                                                      |
| GCT-02 | Creating a category needs an anchor (`MISSING_MANDATORY_ANCHOR`) with a glossary GUID (`INVALID_NEW_ANCHOR_GUID`) and a valid name; its qualified name is `<name>@<glossary qualified name>`, or `<name>.<parent's qualified name>` with a parent, and must be new (`GLOSSARY_CATEGORY_ALREADY_EXISTS`)                                                                              |
| GCT-03 | A parent, and children, link by `AtlasGlossaryCategoryHierarchyLink` with the header's `description`; a child of another glossary fails with `INVALID_CHILD_CATEGORY_DIFFERENT_GLOSSARY`. Each child's qualified name becomes `<name>.<parent's qualified name>`, down the hierarchy, and a child moves to its parent's glossary                                                     |
| GCT-04 | Updating a category keeps its GUID and qualified name and writes it when it differs: a new anchor moves it (and its children) to that glossary; a new, changed or removed parent relinks it, the qualified name following (removed: `<name>@<glossary>`); children are added, updated and removed as listed, a removed child's qualified name becoming `<name>.<glossary>`           |
| GCT-05 | A partial category update sets `name`, `shortDescription` or `longDescription` (`INVALID_PARTIAL_UPDATE_ATTR` for another)                                                                                                                                                                                                                                                           |
| GCT-06 | Deleting a category deletes its anchor, parent, children and term relationships, then the category                                                                                                                                                                                                                                                                                   |
| GCT-07 | A category's related categories are `{"parent": [...], "children": [...]}`, each key only when there is one                                                                                                                                                                                                                                                                          |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/GlossaryREST.java`: the glossary and category endpoints, `toSortOrder`
- `repository/.../glossary/GlossaryService.java`: `getGlossaries`, `createGlossary`, `getGlossary`,
  `getDetailedGlossary`, `updateGlossary`, `deleteGlossary`, `getCategory`, `createCategory(ies)`,
  `updateCategory`, `deleteCategory`, `getGlossaryCategories(Headers)`, `getRelatedCategories`,
  `isNameInvalid`, `setInfoForRelations`, `PaginationHelper`
- `repository/.../glossary/GlossaryCategoryUtils.java`, `GlossaryUtils.java`
- `repository/.../repository/ogm/DataAccess.java`, `ogm/glossary/AbstractGlossaryDTO.java`,
  `AtlasGlossaryDTO.java`, `AtlasGlossaryCategoryDTO.java`
- `intg/.../model/glossary/AtlasGlossary.java`, `AtlasGlossaryBaseObject.java`, `AtlasGlossaryCategory.java`,
  `relations/AtlasGlossaryHeader.java`, `relations/AtlasRelatedCategoryHeader.java`,
  `relations/AtlasRelatedTermHeader.java`
- Tests: `repository/.../glossary/GlossaryServiceTest.java`

## Deviations

DV-99: Atlas reads a glossary list's `limit` and `offset` with `Integer.parseInt` and lets a
`NumberFormatException` escape as an internal error; Aurelius Atlas answers `BAD_REQUEST`, as DV-39 does for
other parameters. DV-100: Atlas orders the glossaries by `Referenceable.qualifiedName`, which a glossary does
not have: in no order; Aurelius Atlas orders them by their qualified name. Atlas's sets of headers are in no
order; Aurelius Atlas answers them in the order the relationships are listed.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — the models' JSON and partial update attributes.
- `libs/python/aurelius-atlas-core/tests/` — GLS-01 to GCT-07 on the in-memory documents, with the glossaries
  and categories of `GlossaryServiceTest`.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/glossary/` — the endpoints over
  HTTP.
- `uv run aurelius-atlas-trace check`.
