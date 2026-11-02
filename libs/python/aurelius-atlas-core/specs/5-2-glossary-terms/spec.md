# 5.2b Glossary terms

- **Status:** in progress
- **Pull request:** to follow
- **Records:** relies on DD-246, DV-99

The second part of increment 5.2: glossary terms, as `GlossaryREST`, `GlossaryService` and
`GlossaryTermUtils` answer them. A term is an `AtlasGlossaryTerm` entity anchored to its glossary (DD-246),
related to other terms by the glossary model's term relationships and to categories by
`AtlasGlossaryTermCategorization`. Assigning terms to entities is 5.2c; glossary import is 5.2d.

## Scope

| Endpoint                                                   | Answers                                           |
| ---------------------------------------------------------- | ------------------------------------------------- |
| `POST /api/atlas/v2/glossary/term`, `terms`                | `AtlasGlossaryTerm`, `[]`                         |
| `GET`, `PUT`, `DELETE /api/atlas/v2/glossary/term/{guid}`  | `AtlasGlossaryTerm`, nothing (204)                |
| `PUT /api/atlas/v2/glossary/term/{guid}/partial`           | `AtlasGlossaryTerm`                               |
| `GET /api/atlas/v2/glossary/{guid}/terms`, `terms/headers` | `AtlasGlossaryTerm[]`, `AtlasRelatedTermHeader[]` |
| `GET /api/atlas/v2/glossary/category/{guid}/terms`         | `AtlasRelatedTermHeader[]`                        |
| `GET /api/atlas/v2/glossary/terms/{guid}/related`          | the related terms by relation                     |

In `aurelius-atlas-model`, `AtlasGlossaryTerm`, its `Relation` and `AtlasTermCategorizationHeader`; in
`aurelius-atlas-core`, `glossary_term_utils` (`GlossaryTermUtils`, the term relations), the term DTO in
`glossary_dto`, and `GlossaryService`'s term methods; deleting a glossary now deletes its terms as `deleteTerm`
does; the detailed glossary holds `termInfo`. What the category and term utilities share moves to `glossary_utils`
(`GlossaryUtils`), and the relationship mapper removes the relationships an update of an internal-type entity
replaces.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| GTM-01 | A term is an `AtlasGlossaryTerm` entity: `qualifiedName`, `name`, `shortDescription`, `longDescription`, `examples`, `abbreviation`, `usage`, `additionalAttributes`, its classifications, its `anchor`, its `categories` (each with the categorization's GUID, `description`, `status` and the category's name), and per relation of `Relation` the related terms' headers (each with the relationship's GUID and attributes, the term's name and qualified name)                                           |
| GTM-02 | Creating a term needs an anchor (`MISSING_MANDATORY_ANCHOR`), a name (`GLOSSARY_TERM_QUALIFIED_NAME_CANT_BE_DERIVED`) without `@ . < >` (`INVALID_DISPLAY_NAME`) and a glossary with a qualified name; its qualified name is `<name>@<glossary qualified name>`, which no term of that glossary may have already (`GLOSSARY_TERM_ALREADY_EXISTS`)                                                                                                                                                            |
| GTM-03 | A term's relations to other terms are relationships of the relation's type, going out of the term (or into it for `preferredToTerms`, `replacementTerms`, `translationTerms`, `isA`, `validValues`) with the header's `expression`, `description`, `steward`, `source` and `status`; a relation to itself fails with `INVALID_TERM_RELATION_TO_SELF`. Its categories are `AtlasGlossaryTermCategorization` relationships from the category, with `description` and `status`                                  |
| GTM-04 | Updating a term needs a valid name and no term listed twice in one relation (`GLOSSARY_TERM_ALREADY_EXISTS` naming that term); it keeps its GUID and qualified name and is written when it differs: a new anchor moves it (`<name>@<glossary>`), and relations and categories are added, updated and removed as listed. A partial update sets `name`, `shortDescription`, `longDescription`, `abbreviation` or `usage` (`INVALID_PARTIAL_UPDATE_ATTR` with Atlas's swapped arguments, `Glossary Term` first) |
| GTM-05 | Deleting a term assigned to entities fails with `TERM_HAS_ENTITY_ASSOCIATION`; otherwise its anchor, relations and categorizations are deleted, then the term. Deleting a glossary deletes its terms so                                                                                                                                                                                                                                                                                                      |
| GTM-06 | A glossary's terms and a category's terms are listed by display text, paged as GLS-05; the related terms are, by relation name, the term's related terms, `{}` when it has none                                                                                                                                                                                                                                                                                                                              |
| GTM-07 | The detailed glossary's `termInfo` holds its terms by GUID                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| GTM-08 | A relationship that an update of an entity of an internal type replaces is removed, not marked `DELETED` (`DeleteHandlerV1.deleteEdgeReference`): a term or category moved to another glossary leaves the old one                                                                                                                                                                                                                                                                                            |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/GlossaryREST.java`: the term endpoints
- `repository/.../glossary/GlossaryService.java`: `getTerm`, `createTerm(s)`, `updateTerm`, `deleteTerm`,
  `getGlossaryTerms(Headers)`, `getCategoryTerms`, `getRelatedTerms`, `getDetailedGlossary`, `termExists2`,
  `getDuplicateGlossaryRelatedTerm`, `setInfoForRelations`
- `repository/.../glossary/GlossaryTermUtils.java`: `processTermRelations` and its helpers
- `repository/.../repository/ogm/glossary/AtlasGlossaryTermDTO.java`
- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `deleteEdgeReference` of an internal type
- `intg/.../model/glossary/AtlasGlossaryTerm.java`, `relations/AtlasTermCategorizationHeader.java`
- Tests: `repository/.../glossary/GlossaryServiceTest.java`

## Deviations

None of its own; DV-99 applies to the term lists' `limit` and `offset` too.

## Acceptance

- `libs/python/aurelius-atlas-model/tests/` — the term model.
- `libs/python/aurelius-atlas-core/tests/` — GTM-01 to GTM-07 on the in-memory documents.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/glossary/` — the endpoints over HTTP.
- `uv run aurelius-atlas-trace check`.
