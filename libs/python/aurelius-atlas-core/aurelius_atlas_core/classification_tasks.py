"""``ClassificationTasks``: the propagation a task records, run after its request (TSK-04, TSK-05).

Atlas's ``ClassificationPropagationTasks`` (``Add``, ``Delete``, ``UpdateRelationship``) and ``ClassificationTask``
over ``EntityGraphMapper``'s ``propagateClassification``, ``deleteClassificationPropagation`` and
``updateTagPropagations``: 3.4a's propagation, written with the task's removal in one write (DD-079).
"""

from collections.abc import Mapping
from typing import Any

from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasRelationship

from aurelius_atlas_core.entity_change_notifier import EntityChangeNotifier
from aurelius_atlas_core.entity_store import (
    ClassificationChange,
    EntityStore,
    EntityVersionConflictError,
    RelationshipChange,
    TaskChange,
)
from aurelius_atlas_core.stored_classification import StoredClassification
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.tag_propagation import ADD, DELETE, RELATIONSHIP_UPDATE, TagPropagation
from aurelius_atlas_core.typedef_document import DocumentVersion

ATTEMPTS = 2
"""A task that loses a race is run once more (DD-052)."""

UNKNOWN_TASK_TYPE = "unknown task type: {type}"


class ClassificationTasks:
    """Runs propagation tasks over the entities of ``store``; ``notifier`` is told what each did (CAU-06)."""

    def __init__(self, store: EntityStore, *, notifier: EntityChangeNotifier | None = None) -> None:
        self._store = store
        self._notifier = notifier

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
                told = await self._attempt(task, version)
            except EntityVersionConflictError:
                if number == ATTEMPTS:
                    raise
            else:
                await self._tell(task, *told)
                return

    async def _attempt(
        self, task: StoredTask, version: DocumentVersion
    ) -> tuple[TagPropagation, list[str], StoredClassification | None]:
        """Run and write the task; answers its propagation, the entities it changed and the classification."""
        parameters = task.parameters or {}
        propagation = TagPropagation(self._store)
        relationships: list[RelationshipChange] = []
        instances: list[ClassificationChange] = []
        changed: list[str] = []
        classification = None
        if task.type == ADD:
            changed, classification = await self._add(propagation, parameters)
        elif task.type == DELETE:
            instances, changed, classification = await self._delete(propagation, parameters)
        else:
            relationships = await self._update(propagation, task, parameters)
        entity_guid = parameters.get("entityGuid")
        if isinstance(entity_guid, str):
            await propagation.unqueue(task.guid, entity_guid)
        await self._store.write(
            propagation.entity_changes([]), relationships, instances, [TaskChange(task, version, remove=True)]
        )
        return propagation, changed, classification

    async def _tell(
        self,
        task: StoredTask,
        propagation: TagPropagation,
        changed: list[str],
        classification: StoredClassification | None,
    ) -> None:
        """What the task did, told as Atlas's task tells it (CAU-06)."""
        notifier = self._notifier
        if notifier is None:
            return
        if task.type == RELATIONSHIP_UPDATE:
            await notifier.notify_propagated_entities(propagation.added, propagation.removed, user=task.created_by)
        elif changed and classification is not None:
            tell = notifier.on_classifications_added if task.type == ADD else notifier.on_classifications_deleted
            await tell(changed, [classification], user=task.created_by)

    async def _add(
        self, propagation: TagPropagation, parameters: Mapping[str, Any]
    ) -> tuple[list[str], StoredClassification | None]:
        """``propagateClassification``: to the entity and what it reaches, but over the relationship (TSK-04).

        Answers the entities that list it now, and it.
        """
        guid, instance_guid = parameters.get("entityGuid"), parameters.get("classificationVertexId")
        if not guid or not instance_guid or await self._store.get(guid) is None:
            return [], None
        found = (await self._store.get_classifications([instance_guid])).get(instance_guid)
        if found is None:
            return [], None
        reached = await propagation.impacted(
            guid, exclude=parameters.get("relationshipGuid"), classification=instance_guid, include=True
        )
        return await propagation.add(found.classification, reached), found.classification

    async def _delete(
        self, propagation: TagPropagation, parameters: Mapping[str, Any]
    ) -> tuple[list[ClassificationChange], list[str], StoredClassification | None]:
        """``deleteClassificationPropagation``: every propagation goes, the instance too when none lists it.

        Answers the instance's removal, the entities that stopped listing it, and it.
        """
        instance_guid = parameters.get("classificationVertexId")
        found = (
            None if not instance_guid else (await self._store.get_classifications([instance_guid])).get(instance_guid)
        )
        if found is None:
            return [], [], None
        removed = await propagation.remove_all(found.classification)
        if await propagation.listed_by(found.classification):
            return [], removed, found.classification
        return [ClassificationChange(found.classification, found.version, remove=True)], removed, found.classification

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
