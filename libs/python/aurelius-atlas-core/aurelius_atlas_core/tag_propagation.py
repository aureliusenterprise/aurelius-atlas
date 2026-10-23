"""``TagPropagation``: classifications reaching the entities related to their entity (PRO-01 to PRO-07, DD-075).

The propagation of ``DeleteHandlerV1`` (``addTagPropagation``, ``removeTagPropagation``, ``updateTagPropagations``,
``handleBlockedClassifications``), ``EntityGraphRetriever`` (``traverseImpactedVertices``,
``evaluateClassificationPropagation``) and ``GraphHelper``, computed in memory for one request over the store and
the request's own changes; the caller writes what it changed with the request (DD-077).
"""

from collections.abc import Callable, Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from aurelius_atlas_model.instance import AtlasClassification, RelationshipStatus
from aurelius_atlas_model.typedef import PropagateTags

from aurelius_atlas_core.entity_store import EntityChange
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_entity import StoredEntity
from aurelius_atlas_core.stored_relationship import StoredRelationship
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.transaction_view import EntityView
from aurelius_atlas_core.typedef_document import DocumentVersion

ADD = "CLASSIFICATION_PROPAGATION_ADD"
DELETE = "CLASSIFICATION_PROPAGATION_DELETE"
RELATIONSHIP_UPDATE = "CLASSIFICATION_PROPAGATION_RELATIONSHIP_UPDATE"
"""``ClassificationPropagateTaskFactory``'s task types (TSK-02)."""

_FROM_END1 = {PropagateTags.ONE_TO_TWO, PropagateTags.BOTH}
_FROM_END2 = {PropagateTags.TWO_TO_ONE, PropagateTags.BOTH}


@dataclass(frozen=True)
class Deferral:
    """Propagation deferred to tasks (TSK-02, DD-081): recorded by ``user`` at ``now``, new GUIDs from ``new_id``."""

    user: str | None
    now: int
    new_id: Callable[[], str]


@dataclass
class _Entity:
    """An entity as this request sees it: its document, the version it was read in, whether propagation changed it."""

    entity: StoredEntity
    version: DocumentVersion | None
    changed: bool = False


class TagPropagation:
    """Propagation over ``store`` and a request's changes.

    ``entities`` are the request's pending documents with the versions they were read in (None for new ones),
    ``relationships`` its pending relationships, ``removed`` the relationships it removes, ``classifications`` its
    new or changed classification instances.
    """

    def __init__(  # noqa: PLR0913 - the request's pending changes, as ``EntityMutationContext``
        self,
        store: EntityView,
        *,
        entities: Mapping[str, tuple[StoredEntity, DocumentVersion | None]] | None = None,
        relationships: Mapping[str, StoredRelationship] | None = None,
        removed: Collection[str] = (),
        classifications: Mapping[str, StoredClassification] | None = None,
        deferral: Deferral | None = None,
    ) -> None:
        self._store = store
        self._entities = {guid: _Entity(entity, version) for guid, (entity, version) in (entities or {}).items()}
        self._relationships = dict(relationships or {})
        self._removed = set(removed)
        self._classifications = dict(classifications or {})
        self._leaving: dict[str, StoredRelationship] = {}
        self._deferral = deferral
        self._tasks: list[StoredTask] = []
        self.added: dict[str, list[StoredClassification]] = {}
        """``RequestContext.addedPropagations``: per entity, the instances newly propagated to it (DD-086)."""
        self.removed: dict[str, list[StoredClassification]] = {}
        """``RequestContext.removedPropagations``: per entity, the propagated instances it lost (DD-086)."""

    @property
    def deferred(self) -> bool:
        """Whether propagation is deferred to tasks (TSK-02)."""
        return self._deferral is not None

    def tasks(self) -> list[StoredTask]:
        """The tasks recorded, to write with the request (DD-079)."""
        return list(self._tasks)

    async def queue(
        self,
        task_type: str,
        guid: str,
        classification: StoredClassification | None = None,
        relationship_guid: str | None = None,
    ) -> StoredTask | None:
        """``createAndQueueTask``: a task on entity ``guid``, which lists it in ``pendingTasks`` (TSK-02)."""
        found = await self._found(guid)
        if self._deferral is None or found is None:
            return None
        task = self._task(
            task_type,
            {
                "entityGuid": guid,
                "classificationVertexId": None if classification is None else classification.guid,
                "classificationName": None if classification is None else classification.type_name,
                "relationshipGuid": relationship_guid,
            },
        )
        found.entity = found.entity.model_copy(
            update={"pending_tasks": [*(found.entity.pending_tasks or []), task.guid]}
        )
        found.changed = True
        return task

    async def unqueue(self, task_guid: str, guid: str) -> None:
        """``removePendingTaskFromEntity``: entity ``guid`` stops listing the task in ``pendingTasks`` (TSK-05)."""
        found = await self._found(guid)
        if found is not None and task_guid in (found.entity.pending_tasks or []):
            listed = [listed for listed in found.entity.pending_tasks or [] if listed != task_guid]
            found.entity = found.entity.model_copy(update={"pending_tasks": listed or None})
            found.changed = True

    def _task(self, task_type: str, parameters: dict[str, Any]) -> StoredTask:
        deferral = self._deferral
        if deferral is None:  # pragma: no cover - only queued when deferred
            raise RuntimeError(task_type)
        task = StoredTask(
            guid=deferral.new_id(),
            type=task_type,
            created_by=deferral.user,
            created_time=deferral.now,
            updated_time=deferral.now,
            parameters=parameters,
        )
        self._tasks.append(task)
        return task

    async def propagate(self, classification: StoredClassification, guid: str, *, blocks: bool = False) -> list[str]:
        """Propagate a classification of entity ``guid`` to what it reaches, or record an ``ADD`` task (PRO-03).

        ``blocks`` counts the relationships' blocks, as ``propagate`` turned on does. Answers the entities it now
        lists, none when deferred (CAU-02).
        """
        if self.deferred:
            await self.queue(ADD, guid, classification)
            return []
        reached = await self.impacted(guid, classification=classification.guid if blocks else None)
        return await self.add(classification, reached)

    async def withdraw(self, classification: StoredClassification, guid: str) -> list[str]:
        """Remove every propagation of a classification of entity ``guid``, or record a ``DELETE`` task (PRO-03).

        Answers the entities that stopped listing it, none when deferred (CAU-03, CAU-04).
        """
        if self.deferred:
            await self.queue(DELETE, guid, classification)
            return []
        return await self.remove_all(classification)

    def changed_entities(self) -> list[EntityChange]:
        """The documents of entities whose classification lists propagation changed, to write."""
        return [EntityChange(found.entity, found.version) for found in self._entities.values() if found.changed]

    def entity_changes(self, own: Iterable[str]) -> list[EntityChange]:
        """The request's own entities as propagation left them, then the others it changed (PRO-10)."""
        names = list(dict.fromkeys(own))
        changes = [EntityChange(found.entity, found.version) for guid in names if (found := self._entities.get(guid))]
        return changes + [change for change in self.changed_entities() if change.entity.guid not in names]

    def entity(self, guid: str) -> StoredEntity | None:
        """The document of entity ``guid`` as this request has it now, when it was read or given."""
        found = self._entities.get(guid)
        return None if found is None else found.entity

    def put_entity(self, entity: StoredEntity, version: DocumentVersion | None = None) -> None:
        """Take the request's document of an entity; a version given replaces the one read, else it is kept."""
        found = self._entities.get(entity.guid)
        if found is None:
            self._entities[entity.guid] = _Entity(entity, version)
        else:
            found.entity = entity
            found.version = version if version is not None else found.version

    def add_instances(self, instances: Iterable[StoredClassification]) -> None:
        """Take classification instances as the request has them, new or changed."""
        self._classifications.update({instance.guid: instance for instance in instances})

    def put_relationship(self, relationship: StoredRelationship) -> None:
        """Take a relationship as the request now has it."""
        self._relationships[relationship.guid] = relationship
        self._removed.discard(relationship.guid)

    def remove_relationship(self, guid: str) -> None:
        """Take a relationship as removed by the request."""
        self._removed.add(guid)

    async def impacted(
        self,
        guid: str,
        *,
        exclude: str | None = None,
        classification: str | None = None,
        include: bool = False,
    ) -> list[str]:
        """``getImpactedVerticesV2``: the entities a classification reaches from entity ``guid`` (PRO-01).

        Breadth first, over ``ACTIVE`` relationships with a tag propagation label of the entity's type that
        propagate away from it, ``exclude`` skipped and those blocking ``classification``; with ``include``, the
        starting entity first (``getIncludedImpactedVerticesV2``).
        """
        visited: set[str] = set()
        reached: dict[str, None] = {guid: None} if include else {}
        queue = [guid]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            entity = await self._entity(current)
            entity_type = None if entity is None else self._store.registry.entity_type(entity.type_name)
            if entity_type is None:
                continue
            labels = set(entity_type.tag_propagation_edges)
            for relationship in await self._relationships_of(current):
                if relationship.label not in labels or not _propagates_away(relationship, current):
                    continue
                if exclude is not None and relationship.guid == exclude:
                    continue
                if classification is not None and classification in (relationship.blocked_classification_guids or []):
                    continue
                other = relationship.end1_guid if relationship.end2_guid == current else relationship.end2_guid
                if other not in visited and other not in reached:
                    reached[other] = None
                    queue.append(other)
        return list(reached)

    async def add(self, classification: StoredClassification, guids: Iterable[str]) -> list[str]:
        """``addTagPropagation``: the entities that list the classification now; others are skipped (PRO-02)."""
        classification_type = self._store.registry.classification_type(classification.type_name)
        added = []
        for guid in guids:
            found = await self._found(guid)
            if found is None or classification.guid in (found.entity.classification_guids or []):
                continue
            entity_type = self._store.registry.entity_type(found.entity.type_name)
            if classification_type is None or entity_type is None:
                continue
            if not classification_type.can_apply_to_entity_type(entity_type):
                continue
            listed = [*(found.entity.classification_guids or []), classification.guid]
            self._list(found, listed)
            self.added.setdefault(guid, []).append(classification)
            added.append(guid)
        return added

    async def remove(self, classification: StoredClassification, guids: Iterable[str]) -> list[str]:
        """``removeTagPropagation(vertex, entities)``: these entities stop listing a propagated classification.

        Answers those that did.
        """
        removed = []
        for guid in guids:
            found = await self._found(guid)
            if found is not None and guid != classification.entity_guid:
                listed = found.entity.classification_guids or []
                if classification.guid in listed:
                    self._list(found, [listed_guid for listed_guid in listed if listed_guid != classification.guid])
                    self.removed.setdefault(guid, []).append(classification)
                    removed.append(guid)
        return removed

    async def remove_all(self, classification: StoredClassification) -> list[str]:
        """``removeTagPropagation(vertex)``: every entity the classification was propagated to stops listing it."""
        return await self.remove(classification, await self.propagated_to(classification))

    async def propagated_to(self, classification: StoredClassification) -> list[str]:
        """``getAllPropagatedEntityVertices``: the entities listing it other than its own (DD-076)."""
        return [guid for guid in await self.listed_by(classification) if guid != classification.entity_guid]

    async def listed_by(self, classification: StoredClassification) -> list[str]:
        """``hasEntityReferences``: the entities listing it, its own included, as the request has them (DD-076)."""
        candidates = [found.entity.guid for found in await self._store.classified([classification.guid])]
        candidates += [guid for guid in self._entities if guid not in candidates]
        listing = []
        for guid in candidates:
            found = await self._found(guid)
            if found is not None and classification.guid in (found.entity.classification_guids or []):
                listing.append(guid)
        return listing

    async def propagation_enabled(self, guid: str) -> list[StoredClassification]:
        """``getPropagationEnabledClassificationVertices``: the entity's classifications, attached or propagated,
        whose ``propagate`` is true.
        """  # noqa: D205 - Java's name, then its meaning
        entity = await self._entity(guid)
        listed = [] if entity is None else entity.classification_guids or []
        found = await self._instances(listed)
        return [found[g] for g in listed if g in found and found[g].propagate is not False]

    async def propagatable(self, relationship: StoredRelationship) -> list[StoredClassification]:
        """``getPropagatableClassifications``: those of the ends it propagates from; none while it is ``DELETED``."""
        if relationship.state is RelationshipStatus.DELETED:
            return []
        found: list[StoredClassification] = []
        propagation = relationship.propagate_tags or PropagateTags.NONE
        if propagation in _FROM_END1:
            found += await self.propagation_enabled(relationship.end1_guid)
        if propagation in _FROM_END2:
            found += await self.propagation_enabled(relationship.end2_guid)
        return found

    async def relationship_created(self, relationship: StoredRelationship) -> None:
        """``addTagPropagation(edge, propagateTags)``: each end's classifications to the other's reach (PRO-04)."""
        self.put_relationship(relationship)
        propagation = relationship.propagate_tags or PropagateTags.NONE
        if propagation in _FROM_END1:
            await self._across(relationship, relationship.end1_guid, relationship.end2_guid)
        if propagation in _FROM_END2:
            await self._across(relationship, relationship.end2_guid, relationship.end1_guid)

    def defer_update(self, before: StoredRelationship, after: StoredRelationship, given: str) -> StoredRelationship:
        """A ``RELATIONSHIP_UPDATE`` task for an update; its tag propagation and blocks stay until it runs (TSK-02).

        ``given`` is the update's JSON. Answers the relationship to write, listing the task.
        """
        task = self._task(RELATIONSHIP_UPDATE, {"relationshipEdgeId": after.guid, "relationshipObject": given})
        return after.model_copy(
            update={
                "propagate_tags": before.propagate_tags,
                "blocked_classification_guids": before.blocked_classification_guids,
                "pending_tasks": [*(after.pending_tasks or []), task.guid],
            }
        )

    async def relationship_removed(self, relationship: StoredRelationship) -> None:
        """``removeTagPropagation(edge)``: classifications that remove propagations lose what it carried (PRO-06).

        The relationship counts as there while its effect is computed, also when its ends no longer list it; it is
        removed from the view after.
        """
        self._leaving[relationship.guid] = relationship
        self._removed.discard(relationship.guid)
        current = await self.propagatable(relationship)
        before = await self._mapping(current)
        after = await self._mapping(current, exclude=relationship.guid)
        del self._leaving[relationship.guid]
        self.remove_relationship(relationship.guid)
        for classification in current:
            lost = [
                guid for guid in before.get(classification.guid, []) if guid not in after.get(classification.guid, [])
            ]
            if lost and classification.remove_propagations_on_entity_delete is not False:
                await self.remove(classification, lost)

    async def relationship_updated(
        self, before: StoredRelationship, after: StoredRelationship, blocked: Sequence[AtlasClassification] | None
    ) -> StoredRelationship:
        """``updateTagPropagations``: a changed ``propagateTags`` moves propagation, else the blocks (PRO-05).

        Answers the relationship as it is to be written.
        """
        if (after.propagate_tags or None) != (before.propagate_tags or None):
            current = await self.propagatable(before)
            current_mapping = await self._mapping(current)
            self.put_relationship(after)
            union = {c.guid: c for c in [*current, *await self.propagatable(after)]}
            updated_mapping = await self._mapping(list(union.values()))
            for guid, classification in union.items():
                was, now = current_mapping.get(guid, []), updated_mapping.get(guid, [])
                await self.add(classification, [entity for entity in now if entity not in was])
                await self.remove(classification, [entity for entity in was if entity not in now])
            return after
        return await self.handle_blocked(after, blocked)

    async def handle_blocked(
        self, relationship: StoredRelationship, blocked: Sequence[AtlasClassification] | None
    ) -> StoredRelationship:
        """``handleBlockedClassifications``: the blocks the given classifications name, and their effect (PRO-05)."""
        if blocked is None:
            self.put_relationship(relationship)
            return relationship
        propagatable = await self.propagatable(relationship)
        current = [c for c in propagatable if c.guid in (relationship.blocked_classification_guids or [])]
        to_block: list[StoredClassification] = []
        for classification in blocked:
            match = next(
                (
                    c
                    for c in propagatable
                    if c.type_name == classification.type_name and c.entity_guid == classification.entity_guid
                ),
                None,
            )
            if match is not None:
                to_block.append(match)
        updated = relationship.model_copy(update={"blocked_classification_guids": [c.guid for c in to_block] or None})
        self.put_relationship(updated)
        blocked_now = {c.guid for c in to_block}
        blocked_before = {c.guid for c in current}
        for classification in {c.guid: c for c in [*to_block, *current]}.values():
            if (classification.guid in blocked_now) != (classification.guid in blocked_before):
                await self.evaluate(classification)
        return updated

    async def evaluate(self, classification: StoredClassification) -> None:
        """``evaluateClassificationPropagation``: gain the entities it reaches now, lose those it no longer does."""
        propagated = await self.propagated_to(classification)
        source = classification.entity_guid
        impacted = [] if source is None else await self.impacted(source, classification=classification.guid)
        await self.remove(classification, [guid for guid in propagated if guid not in impacted])
        await self.add(classification, [guid for guid in impacted if guid not in propagated])

    async def _across(self, relationship: StoredRelationship, source: str, target: str) -> None:
        """``addTagPropagation(from, to, edge)``: the source end's classifications to the target and its reach.

        One the request attaches propagates on its own, as Atlas attaches classifications after mapping the
        relationships (CAU-02).
        """
        classifications = [c for c in await self.propagation_enabled(source) if c.guid not in self._classifications]
        if not classifications:
            return
        if self.deferred:
            for classification in classifications:
                await self.queue(ADD, target, classification, relationship.guid)
            return
        reached = await self.impacted(target, exclude=relationship.guid, include=True)
        for classification in classifications:
            await self.add(classification, reached)

    async def _mapping(
        self, classifications: Sequence[StoredClassification], exclude: str | None = None
    ) -> dict[str, list[str]]:
        """``getClassificationPropagatedEntitiesMapping``: the entities each reaches from its own entity."""
        mapping: dict[str, list[str]] = {}
        for classification in classifications:
            source = classification.entity_guid
            mapping[classification.guid] = (
                []
                if source is None
                else await self.impacted(source, exclude=exclude, classification=classification.guid)
            )
        return mapping

    def _list(self, found: _Entity, listed: list[str]) -> None:
        found.entity = found.entity.model_copy(update={"classification_guids": listed or None})
        found.changed = True

    async def _found(self, guid: str) -> _Entity | None:
        if guid not in self._entities:
            stored = (await self._store.get_many([guid])).get(guid)
            if stored is None:
                return None
            self._entities[guid] = _Entity(stored.entity, stored.version)
        return self._entities[guid]

    async def _entity(self, guid: str) -> StoredEntity | None:
        found = await self._found(guid)
        return None if found is None else found.entity

    async def _relationships_of(self, guid: str) -> list[StoredRelationship]:
        entity = await self._entity(guid)
        listed = [] if entity is None else list(entity.relationship_guids or [])
        listed += [g for g, r in self._leaving.items() if guid in r.ends() and g not in listed]
        wanted = [g for g in listed if g not in self._removed]
        stored = await self._store.get_relationships([g for g in wanted if g not in self._relationships])
        found = []
        for relationship_guid in wanted:
            if relationship_guid in self._leaving:
                found.append(self._leaving[relationship_guid])
            elif relationship_guid in self._relationships:
                found.append(self._relationships[relationship_guid])
            elif relationship_guid in stored:
                found.append(stored[relationship_guid].relationship)
        return found

    async def _instances(self, guids: Sequence[str]) -> dict[str, StoredClassification]:
        stored = await self._store.get_classifications([g for g in guids if g not in self._classifications])
        found = {guid: instance.classification for guid, instance in stored.items()}
        found.update({guid: self._classifications[guid] for guid in guids if guid in self._classifications})
        return found


def _propagates_away(relationship: StoredRelationship, guid: str) -> bool:
    """Whether the relationship carries classifications away from entity ``guid`` (``traverseImpactedVertices``)."""
    if relationship.state is not RelationshipStatus.ACTIVE:
        return False
    propagation = relationship.propagate_tags or PropagateTags.NONE
    if propagation is PropagateTags.NONE:
        return False
    if propagation is PropagateTags.TWO_TO_ONE:
        return relationship.end1_guid != guid
    if propagation is PropagateTags.ONE_TO_TWO:
        return relationship.end1_guid == guid
    return True
