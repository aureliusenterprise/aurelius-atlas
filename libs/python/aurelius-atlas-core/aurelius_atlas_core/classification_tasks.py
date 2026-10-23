"""``ClassificationTasks``: the propagation a task records, run after its request (TSK-04, TSK-05).

Atlas's ``ClassificationPropagationTasks`` (``Add``, ``Delete``, ``UpdateRelationship``) and ``ClassificationTask``
over ``EntityGraphMapper``'s ``propagateClassification``, ``deleteClassificationPropagation`` and
``updateTagPropagations``: 3.4a's propagation, written with the task's removal in one write (DD-079).
"""

from collections.abc import Mapping
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasRelationship

from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityStore,
    EntityVersionConflictError,
    RelationshipChange,
    TaskChange,
)
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.tag_propagation import ADD, DELETE, RELATIONSHIP_UPDATE, TagPropagation
from aurelius_atlas_core.typedef_document import DocumentVersion

ATTEMPTS = 2
"""A task that loses a race is run once more (DD-052)."""

UNKNOWN_TASK_TYPE = "unknown task type: {type}"


class ClassificationTasks:
    """Runs propagation tasks over the entities of ``store``."""

    def __init__(self, store: EntityStore) -> None:
        self._store = store

    async def run(self, task: StoredTask, version: DocumentVersion) -> None:
        """Run the task and remove it, and its GUID from ``pendingTasks``, in one write (TSK-04, TSK-05).

        ``version`` is the one the task was claimed in.

        Raises:
            ValueError: The task's type is none of the propagation tasks.
            EntityVersionConflictError: The documents it changes changed again while it ran, twice.
        """
        if task.type not in {ADD, DELETE, RELATIONSHIP_UPDATE}:
            raise ValueError(UNKNOWN_TASK_TYPE.format(type=task.type))
        for number in range(1, ATTEMPTS + 1):
            try:
                await self._attempt(task, version)
            except EntityVersionConflictError:
                if number == ATTEMPTS:
                    raise
            else:
                return

    async def _attempt(self, task: StoredTask, version: DocumentVersion) -> None:
        parameters = task.parameters or {}
        propagation = TagPropagation(self._store)
        relationships: list[RelationshipChange] = []
        instances: list[ClassificationChange] = []
        if task.type == ADD:
            await self._add(propagation, parameters)
        elif task.type == DELETE:
            instances = await self._delete(propagation, parameters)
        else:
            relationships = await self._update(propagation, task, parameters)
        entity_guid = parameters.get("entityGuid")
        if isinstance(entity_guid, str):
            await propagation.unqueue(task.guid, entity_guid)
        await self._store.write(
            propagation.entity_changes([]), relationships, instances, [TaskChange(task, version, remove=True)]
        )

    async def _add(self, propagation: TagPropagation, parameters: Mapping[str, Any]) -> None:
        """``propagateClassification``: to the entity and what it reaches, but over the relationship (TSK-04)."""
        guid, instance_guid = parameters.get("entityGuid"), parameters.get("classificationVertexId")
        if not guid or not instance_guid or await self._store.get(guid) is None:
            return
        found = (await self._store.get_classifications([instance_guid])).get(instance_guid)
        if found is None:
            return
        reached = await propagation.impacted(
            guid, exclude=parameters.get("relationshipGuid"), classification=instance_guid, include=True
        )
        await propagation.add(found.classification, reached)

    async def _delete(self, propagation: TagPropagation, parameters: Mapping[str, Any]) -> list[ClassificationChange]:
        """``deleteClassificationPropagation``: every propagation goes, the instance too when none lists it."""
        instance_guid = parameters.get("classificationVertexId")
        found = (
            None if not instance_guid else (await self._store.get_classifications([instance_guid])).get(instance_guid)
        )
        if found is None:
            return []
        await propagation.remove_all(found.classification)
        if await propagation.listed_by(found.classification):
            return []
        return [ClassificationChange(found.classification, found.version, remove=True)]

    async def _update(
        self, propagation: TagPropagation, task: StoredTask, parameters: Mapping[str, Any]
    ) -> list[RelationshipChange]:
        """``updateTagPropagations`` with the update's relationship, which stops listing the task (PRO-05)."""
        guid = parameters.get("relationshipEdgeId")
        found = None if not guid else (await self._store.get_relationships([guid])).get(guid)
        if found is None:
            return []
        given = AtlasRelationship.model_validate(codec.loads(str(parameters.get("relationshipObject") or "{}")))
        stored = found.relationship
        after = (
            stored
            if given.propagate_tags is None
            else stored.model_copy(update={"propagate_tags": given.propagate_tags})
        )
        changed = await propagation.relationship_updated(stored, after, given.blocked_propagated_classifications)
        listed = [listed for listed in changed.pending_tasks or [] if listed != task.guid]
        return [RelationshipChange(changed.model_copy(update={"pending_tasks": listed or None}), found.version)]
