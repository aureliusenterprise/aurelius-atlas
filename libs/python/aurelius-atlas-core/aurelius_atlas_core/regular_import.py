"""``RegularImport``: an export's entities written one by one, as an import writes them (IMS-04, IMS-05).

Each entity of the export order is written with what it owns (``createOrUpdateForImport``); one that names an
entity not written yet is tried again after the rest. An entity whose GUID another stored entity holds the values
of is written as that entity, the export's GUID standing for it for the rest of the import (DD-306).
"""

from typing import Any

from aurelius_atlas_model.errors import AtlasError, AtlasErrorCode
from aurelius_atlas_model.impexp import AtlasImportResult
from aurelius_atlas_model.instance import AtlasEntityWithExtInfo, EntityMutationResponse, EntityOperation
from aurelius_atlas_typesystem.builtin.object_id_type import is_assigned_guid

from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.entity_writer import EntityWriter
from aurelius_atlas_core.zip_source import ZipSource

NO_ENTITIES = "no entities to create/update."
METRICS = (
    ("entity:{}:created", EntityOperation.CREATE),
    ("entity:{}:updated", EntityOperation.UPDATE),
    ("entity:{}:deleted", EntityOperation.DELETE),
)
"""``updateImportMetrics``: the count of each type created, updated and deleted, each entity once."""


class RegularImport:
    """``RegularImport`` into ``store`` through ``writer``."""

    def __init__(self, store: EntityStore, writer: EntityWriter) -> None:
        self._store = store
        self._writer = writer
        self._guids: dict[str, str] = {}

    async def run(self, source: ZipSource, result: AtlasImportResult) -> None:
        """``run``: each entity written in the export order, then those that named an entity not yet written.

        Raises:
            AtlasError: ``INVALID_PARAMETERS`` for an export of no entity; any other failure of a write.
        """
        if not source.has_next():
            raise AtlasError(AtlasErrorCode.INVALID_PARAMETERS, NO_ENTITIES)
        processed: dict[str, None] = {}
        residual: list[AtlasEntityWithExtInfo] = []
        while source.has_next():
            found = source.next_entity_with_ext_info()
            if found is not None and found.entity is not None and not await self._write(found, result, processed):
                residual.append(found)
        for found in residual:
            await self._write(found, result, processed, last=True)
        result.processed_entities += list(processed)

    async def _write(
        self,
        found: AtlasEntityWithExtInfo,
        result: AtlasImportResult,
        processed: dict[str, None],
        *,
        last: bool = False,
    ) -> bool:
        """One entity written and counted; False when it names an entity not written yet, unless ``last``.

        Raises:
            AtlasError: a failure of the write.
        """
        found = await self._standing_for(found)
        try:
            response = await self._writer.create_or_update_for_import(found)
        except AtlasError as error:
            if error.code is AtlasErrorCode.INVALID_OBJECT_ID and not last:
                return False
            raise
        _count(response, result, processed)
        return True

    async def _standing_for(self, found: AtlasEntityWithExtInfo) -> AtlasEntityWithExtInfo:
        """The entity with each GUID a stored entity of the same values holds named by that entity's (DD-306)."""
        for entity in [found.entity, *(found.referred_entities or {}).values()]:
            guid = None if entity is None else entity.guid
            if entity is None or not guid or not is_assigned_guid(guid) or guid in self._guids:
                continue
            if await self._store.get(guid) is not None:
                continue
            entity_type = self._store.registry.entity_type(entity.type_name)
            stored = None
            if entity_type is not None:
                stored = await self._store.find_by_unique_attributes(entity_type, entity.attributes or {})
            if stored is not None and stored.entity.guid != guid:
                self._guids[guid] = stored.entity.guid
        if not self._guids:
            return found
        return AtlasEntityWithExtInfo.model_validate(_renamed(found.to_json(), self._guids))


def _renamed(value: Any, guids: dict[str, str]) -> Any:  # noqa: ANN401 - a JSON value
    """The JSON with each ``guid`` and referred entity key of ``guids`` named by its stored entity's GUID."""
    if isinstance(value, dict):
        return {
            guids.get(key, key): (
                guids.get(item, item) if key == "guid" and isinstance(item, str) else _renamed(item, guids)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_renamed(item, guids) for item in value]
    return value


def _count(response: EntityMutationResponse, result: AtlasImportResult, processed: dict[str, None]) -> None:
    """``updateImportMetrics``: each entity created, updated or deleted counted by its type, once."""
    for key, operation in METRICS:
        for header in response.get_entities_by_operation(operation) or []:
            guid = str(header.guid)
            if guid in processed:
                continue
            processed[guid] = None
            result.increment_metrics_counter(key.format(header.type_name))
