"""``AuditReductionEntityRetrievalTask`` with ``AuditReductionTask``: an aging's entities found, then their audits
aged out in batches (AGE-04, DD-309).
"""  # noqa: D205 - one sentence

from collections.abc import Sequence

from aurelius_atlas_model.audit import EntityAuditActionV2
from aurelius_atlas_model.audit_reduction import (
    AUDIT_AGING_ACTION_TYPES_KEY,
    AUDIT_AGING_COUNT_KEY,
    AUDIT_AGING_ENTITY_TYPES_KEY,
    AUDIT_AGING_SUBTYPES_INCLUDED_KEY,
    AUDIT_AGING_TTL_KEY,
    AUDIT_AGING_TYPE_KEY,
    CREATE_EVENTS_AGEOUT_ALLOWED_KEY,
    AtlasAuditAgingType,
)
from aurelius_atlas_model.typedef import TypeCategory
from aurelius_atlas_typesystem.types import entity_types_and_all_sub_types

from aurelius_atlas_core.entity_audit_repository import EntityAuditRepository, delete_events_v2
from aurelius_atlas_core.entity_store import EntityStore, TaskChange
from aurelius_atlas_core.stored_task import StoredTask
from aurelius_atlas_core.typedef_document import DocumentVersion

AUDIT_REDUCTION_ENTITY_RETRIEVAL = "AUDIT_REDUCTION_ENTITY_RETRIEVAL"
"""``AuditReductionTaskFactory.ATLAS_AUDIT_REDUCTION_ENTITY_RETRIEVAL``: the task that ages out audits (DD-309)."""
GUID_BATCH_SIZE = 100
"""``GUID_BATCH_SIZE_PER_AGE_OUT_TASK``."""
NO_PARAMETERS = "Unable to process task: Parameters is not readable!"
NO_USER = "Unable to process task as user name is empty!"


class AuditReductionTask:
    """Runs an ``AUDIT_REDUCTION_ENTITY_RETRIEVAL`` task over ``store`` and its entities' ``audits``."""

    def __init__(self, store: EntityStore, audits: EntityAuditRepository) -> None:
        self._store = store
        self._audits = audits

    async def run(self, task: StoredTask, version: DocumentVersion) -> int:
        """Age out the audits of the entities the task's aging names, then remove the task; the number removed.

        Raises:
            ValueError: The task has no parameters or no creator.
        """
        parameters = task.parameters or {}
        if not parameters:
            raise ValueError(NO_PARAMETERS)
        if not task.created_by:
            raise ValueError(NO_USER)
        aging_type = AtlasAuditAgingType(str(parameters[AUDIT_AGING_TYPE_KEY]))
        guids = await self.eligible_guids(
            aging_type,
            list(parameters.get(AUDIT_AGING_ENTITY_TYPES_KEY) or []),
            subtypes_included=bool(parameters.get(AUDIT_AGING_SUBTYPES_INCLUDED_KEY, True)),
        )
        actions = [EntityAuditActionV2.from_string(name) for name in parameters.get(AUDIT_AGING_ACTION_TYPES_KEY) or []]
        removed = 0
        for start in range(0, len(guids), GUID_BATCH_SIZE):
            now = self._store.now()
            for guid in guids[start : start + GUID_BATCH_SIZE]:
                removed += len(
                    await delete_events_v2(
                        self._audits,
                        guid,
                        actions,
                        int(parameters.get(AUDIT_AGING_COUNT_KEY) or 0),
                        int(parameters.get(AUDIT_AGING_TTL_KEY) or 0),
                        create_events_ageout_allowed=bool(parameters.get(CREATE_EVENTS_AGEOUT_ALLOWED_KEY)),
                        aging_type=aging_type,
                        now=now,
                    )
                )
        await self._store.write([], [], [], [TaskChange(task, version, remove=True)])
        return removed

    async def eligible_guids(
        self, aging_type: AtlasAuditAgingType, entity_types: Sequence[str], *, subtypes_included: bool
    ) -> list[str]:
        """``createAgingTaskWithEligibleGUIDs``: the entities, in any state, of the types named (``<prefix>*`` all
        that start so, with their sub types if asked), or for the default aging of every other type; a custom
        aging or sweep none of whose types exists has none (AGE-04, DV-132).
        """  # noqa: D205 - one sentence
        registry = self._store.registry
        every = [str(typedef.name) for typedef in registry.typedefs(TypeCategory.ENTITY)]
        named: set[str] = set()
        for name in entity_types:
            if name.endswith("*"):
                named |= {found for found in every if found.startswith(name.replace("*", ""))}
            elif name in every:
                named.add(name)
        if entity_types and not named and aging_type is not AtlasAuditAgingType.DEFAULT:
            return []
        if subtypes_included:
            named = set(entity_types_and_all_sub_types(sorted(named), registry))
        if aging_type is AtlasAuditAgingType.DEFAULT:
            types = [name for name in every if name not in named]
        else:
            types = sorted(named) if entity_types else every
        return [entity.guid for entity in await self._store.of_types(types)]
