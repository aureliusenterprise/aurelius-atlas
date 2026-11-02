# 5.2c Term assignment

- **Status:** in progress
- **Pull request:** to follow
- **Records:** DD-248, DV-101 to DV-103; relies on DD-246, DV-95, DV-99

The third part of increment 5.2: glossary terms assigned to entities. A term is assigned by an
`AtlasGlossarySemanticAssignment` relationship from the term to the entity (DD-246), which the term lists as
its `assignedEntities` and the entity's header as its `meanings`. Basic search's `termName` and the DSL's
`hasTerm` find the entities a term is assigned to. Glossary import is 5.2d.

## Scope

| Endpoint                                                                  | Answers                  |
| ------------------------------------------------------------------------- | ------------------------ |
| `GET /api/atlas/v2/glossary/terms/{guid}/assignedEntities`                | `AtlasRelatedObjectId[]` |
| `POST /api/atlas/v2/glossary/terms/{guid}/assignedEntities`               | nothing (204)            |
| `PUT`, `DELETE /api/atlas/v2/glossary/terms/{guid}/assignedEntities`      | nothing (204)            |
| `POST /api/atlas/v2/search/basic`, `GET .../search/basic` with `termName` | `AtlasSearchResult`      |
| `GET /api/atlas/v2/search/dsl` with `hasTerm`                             | `AtlasSearchResult`      |

In `aurelius-atlas-core`, `GlossaryService`'s assignment methods, `GlossaryTermUtils`' `process_term_assignments`
and `process_term_dissociation`, the term methods of `EntityChangeNotifier` and `EntityAuditListener`, the
entity header's meanings in `EntityRetriever`, and `term_search_processor` (`TermSearchProcessor`, the term of
`SearchContext`, `GremlinClause.TERM`); in `aurelius-atlas-model`, the error codes.

## Semantics

| Id     | Rule                                                                                                                                                                                                                                                                                                                      |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GTA-01 | A term's assigned entities are its active assignments' entities, each as a related object id with the assignment's GUID, status and attributes, listed by display text and paged as GLS-05 (DV-101)                                                                                                                       |
| GTA-02 | Assigning a term creates an `AtlasGlossarySemanticAssignment` from the term to each entity it does not list as assigned yet, with the related object id's relationship attributes; a relationship of the type between the two already there is kept. As the type says, the term's classifications propagate to the entity |
| GTA-03 | Removing a term's assignment needs the assignment's GUID (`TERM_DISSOCIATION_MISSING_RELATION_GUID`), which must be the term's assignment to that entity (`INVALID_TERM_DISSOCIATION`, DV-102); it is removed for good. `PUT` and `DELETE` do the same                                                                    |
| GTA-04 | Each entity there is records `TERM_ADD` on an assignment and `TERM_DELETE` on a removal, the details `Added term:` or `Deleted term:`, a space and the JSON of the term's GUID, qualified name and name (`toAuditString`), whether or not anything changed                                                                |
| GTA-05 | An entity's header lists as `meanings` the terms assigned to it by assignments in any state: the term's GUID, name as display text and qualified name, the assignment's GUID, `description`, `expression`, `status`, `confidence`, `createdBy`, `steward` and `source` (DV-103); `meaningNames` are the display texts     |
| GTA-06 | A basic search's `termName` is the qualified name of an active term (`UNKNOWN_GLOSSARY_TERM`); the search finds the entities the term is assigned to, by assignments in any state, that meet its other parameters. A search of a term alone is valid                                                                      |
| GTA-07 | The DSL's `<type> hasTerm <name>` finds the entities of the type assigned a term, in any state, whose qualified name is the name when it holds `@`, else whose name it is; quotes are removed. `hasTerm` of an expression stays declared (DV-95)                                                                          |

## Java origin

Apache Atlas `release-2.4.0`:

- `webapp/.../web/rest/GlossaryREST.java`: the `assignedEntities` endpoints
- `repository/.../glossary/GlossaryService.java`: `getAssignedEntities`, `assignTermToEntities`,
  `removeTermFromEntities`
- `repository/.../glossary/GlossaryTermUtils.java`: `processTermAssignments`, `processTermDissociation`,
  `defineTermAssignment`
- `repository/.../store/graph/v2/AtlasEntityChangeNotifier.java`: `onTermAddedToEntities`,
  `onTermDeletedFromEntities`
- `repository/.../audit/EntityAuditListenerV2.java`: `onTermAdded`, `onTermDeleted`
- `intg/.../model/glossary/AtlasGlossaryTerm.java`: `toAuditString`
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `mapVertexToAtlasEntityHeader`, `mapAssignedTerms`
- `repository/.../discovery/SearchContext.java`, `TermSearchProcessor.java`
- `repository/.../query/GremlinQueryComposer.java`: `addHasTerm`; `GremlinClause.TERM`
- Tests: `repository/.../glossary/GlossaryServiceTest.java` (`testTermAssignmentAndDissociation`)

## Deviations

- **DV-101:** assigned entities are paged in display-text order. Atlas sorts a copy, then pages the unsorted
  set.
- **DV-102:** removing an assignment the term does not have answers `INVALID_TERM_DISSOCIATION`, and
  assigning to an entity there is not answers `RELATIONSHIP_END_IS_NULL`. Atlas fails on a null in both.
- **DV-103:** an assignment status that is no `AtlasTermAssignmentStatus` (`DRAFT`, `ACTIVE`) is left out of the
  meaning. Atlas fails every read of the entity's header.

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — GTA-01 to GTA-07 on the in-memory documents.
- `apps/aurelius-atlas-server/tests/`, `apps/aurelius-atlas-server/scenarios/glossary/` — the endpoints over HTTP.
- `uv run aurelius-atlas-trace check`.
