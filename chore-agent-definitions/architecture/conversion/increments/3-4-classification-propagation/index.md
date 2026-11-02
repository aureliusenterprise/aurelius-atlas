# 3.4a Classification propagation

- **Status:** in progress
- **Pull request:** [\#122](<https://github.com/aureliusenterprise/aurelius-atlas/pull/122>)
- **Records:** DD-075 to DD-078, DV-37; ends DV-34; relies on DD-061, DD-062, DD-066, DD-068, DD-070, DD-071

The first part of increment 3.4 (DD-078; 3.4b defers propagation to tasks, as Atlas does by default): classifications reaching the entities related to their entity, computed and written within the request that causes them, as Atlas does with `atlas.tasks.enabled=false`.

## Scope

No new endpoint. Classification adds, updates and deletes (3.3a), relationship creates, updates and deletes (3.1a), entity writes that create or remove relationships (3.1b, 3.2) and entity deletes (2.5) propagate; entities read propagated classifications among their own (CLS-02), relationships their `propagatedClassifications` and `blockedPropagatedClassifications`.

In `aurelius-atlas-core`, `tag_propagation` (`TagPropagation`: the propagation of `DeleteHandlerV1`, `EntityGraphRetriever` and `GraphHelper`), and changes to `entity_classifications`, `relationship_store`, `entity_writer`, `delete_handler`, `relationship_mapper` and `entity_retriever`. Entities are found by the classification instances they list through an indexed field (DD-076).

Not in scope:

| Not delivered here | Delivered by |
| --- | --- |
| Deferred propagation tasks (`atlas.tasks.enabled`), `pendingTasks`, `admin/tasks`, `DELETE_TAG_PROPAGATION_NOT_ALLOWED` | 3.4b |
| Classification text (`__classificationsText`) and notifications | 4.1, – |

## Semantics

An entity's *propagation-enabled classifications* are those it lists, attached or propagated, whose `propagate` is true. A relationship *propagates from* end 1 for `ONE_TO_TWO`, from end 2 for `TWO_TO_ONE`, from both for `BOTH`.

| Id | Rule |
| --- | --- |
| PRO-01 | The entities a classification reaches from an entity are found breadth first (`traverseImpactedVertices`): from each entity reached, over its `ACTIVE` relationships whose label is one of its type's tag propagation edges (THY-11) and that propagate away from it, skipping a relationship the step excludes and, for a given classification, those that block it; each entity once, the starting one not among them unless the step includes it |
| PRO-02 | Propagating a classification to entities (`addTagPropagation`) skips its own entity, one that lists it already, and one whose type it may not classify; each other entity lists it, after its own (DD-075). Nothing else of the entity changes |
| PRO-03 | Adding a classification with `propagate` true propagates it to the entities it reaches from its entity (PRO-01, no classification given). Updating `propagate` from false to true propagates it to those it reaches, its blocks counted; from true to false removes it from every entity it was propagated to. Deleting a classification attached directly first removes it so when its `propagate` is true |
| PRO-04 | A created relationship (CLS-05 order: blocked classifications first) propagates, for each end it propagates from, that end's propagation-enabled classifications to the other end and the entities they reach from it, the new relationship excluded |
| PRO-05 | Updating a relationship's `propagateTags` to another value recomputes, for the propagation-enabled classifications of its ends before and after, the entities each reaches from its entity, and adds or removes the differences. Otherwise, `blockedPropagatedClassifications` when given replace its blocks: each one matching one of its ends' propagation-enabled classifications by type name and entity GUID blocks it, others are ignored; each classification whose block changed gains the entities it now reaches and loses those it no longer does (`evaluateClassificationPropagation`) |
| PRO-06 | A relationship removed (a hard delete over REST, a hard REL-15 delete, an end removed by a hard delete or purge) removes, of its propagatable classifications whose `removePropagationsOnEntityDelete` is true, each from the entities it no longer reaches without it; a soft delete removes none. Propagated classifications to a deleted relationship's ends stay otherwise |
| PRO-07 | Deleting an entity removes every propagation of its directly attached classifications whose `removePropagationsOnEntityDelete` is true. Its attached ones are then `DELETED` (soft) as CLS-11 says, or removed (hard, purge) unless other entities still list them, which keep them, `entityStatus` `PURGED`; the propagated ones it lists go with it, or stay listed after a soft delete |
| PRO-08 | `DELETE guid/{guid}/classification/{name}?associatedEntityGuid=` naming another entity removes the classification of that name propagated from it: `PROPAGATED_CLASSIFICATION_NOT_ASSOCIATED_WITH_ENTITY` when the entity has none, `PROPAGATED_CLASSIFICATION_REMOVAL_NOT_SUPPORTED` (name, that entity) while its `entityStatus` is `ACTIVE`; else the entity stops listing it, and the instance is removed when no entity lists it any more |
| PRO-09 | A relationship reads, from its ends' propagation-enabled classifications (none while it is `DELETED`), those it blocks in `blockedPropagatedClassifications` and the others in `propagatedClassifications` (`readClassificationsFromEdge`); with `extendedInfo`, each one's entity header is among `referredEntities` |
| PRO-10 | Propagation is written with the request that causes it, all or nothing (DD-071, DD-077) |

## Java origin

Apache Atlas `release-2.4.0`:

- `repository/.../store/graph/v1/DeleteHandlerV1.java`: `addTagPropagation`, `removeTagPropagation`, `updateTagPropagations`, `handleBlockedClassifications`, `deletePropagatedClassification`, `deleteAllClassifications`, `deleteEdge`; `HardDeleteHandlerV1#deleteEdge`
- `repository/.../store/graph/v2/EntityGraphRetriever.java`: `traverseImpactedVertices`, `getImpactedVerticesV2`, `getIncludedImpactedVerticesV2`, `getClassificationPropagatedEntitiesMapping`, `evaluateClassificationPropagation`, `readClassificationsFromEdge`
- `repository/.../store/graph/v2/EntityGraphMapper.java`: `addClassifications`, `updateClassifications`, `deleteClassification`, `propagateClassification`
- `repository/.../graph/GraphHelper.java`: `getPropagatableClassifications`, `getPropagationEnabledClassificationVertices`, `getPropagatedEdges`, `getPropagatedClassificationEdge`
- `repository/.../store/graph/v2/AtlasRelationshipStoreV2.java`: `createRelationship`, `updateTagPropagations`

## Deviations

DV-34 ends. DV-37: Atlas's default defers propagation to tasks; until 3.4b Aurelius Atlas propagates within the request, as Atlas does with `atlas.tasks.enabled=false` (DD-077).

## Acceptance

- `libs/python/aurelius-atlas-core/tests/` — PRO-01 to PRO-10 on the in-memory documents.
- `libs/python/aurelius-atlas-core/e2e/` — a classification propagated and removed on the dev store.
- `apps/aurelius-atlas-server/scenarios/` — PRO-03, PRO-04, PRO-09 over HTTP.
- `uv run aurelius-atlas-trace check`.
