"""``ImportWriter``: writing an export's entities as an import (IMP-01 to IMP-08, WRS-07).

``createOrUpdateForImport`` writes one exported entity with what it owns. The discovery, mapping and commit
steps are the ones every write runs (``WritePipeline``), shared with ``EntityWriter`` through the same
transaction object rather than by subclassing the writer (DD-780); what lives here is only what an import does
differently: the import flag, the deferred deletions, the classification replace, and the task hold that spans
an import's many writes (DD-778).
"""

from aurelius_atlas_model.instance import AtlasEntityWithExtInfo, EntityMutationResponse, EntityOperation

from aurelius_atlas_core.delete_type import DeleteType
from aurelius_atlas_core.entity_classifications import EntityClassifications
from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_writer import (
    WritePipeline,
    WriteTransaction,
    entity_stream,
    imported_classification,
)
from aurelius_atlas_core.task_hold import TaskHold


class ImportWriter(WritePipeline):
    """Writes an export's entities into ``store`` as an import, as ``user`` (IMP-01).

    Holds no mutable field of one write: the flag, the deferred deletions and the GUID map ride the
    ``WriteTransaction`` the shared steps build (WRS-05, WRS-07). Its only own state is the task hold, which
    spans the many writes of one import (IMT-01).
    """

    _hold: TaskHold | None = None
    """The import's hold, set by ``hold_tasks`` around a whole import (IMT-01); each write builds it into its
    ``WriteTransaction``, and no write's state otherwise survives on this writer."""

    async def create_or_update_for_import(self, found: AtlasEntityWithExtInfo) -> EntityMutationResponse:
        """``createOrUpdateForImport``: one exported entity with what it owns, written as an import (IMP-01 to IMP-08).

        Its GUIDs, system attributes and status are kept; its classifications and business attributes replace the
        stored ones; it is not checked against the user's privileges, and its changes are audited as an import's.

        Raises:
            AtlasError: as ``create_or_update``.
        """
        response, txn = await self._run(entity_stream(found), partial=False, importing=True, hold=self._hold)
        await self._replace_classifications(found, response, txn)
        deleted = txn.deletions
        if deleted:
            removed = await self._delete(lambda: self._stored(deleted), txn, DeleteType.DEFAULT)  # unchecked (IMP-07)
            for header in removed.get_entities_by_operation(EntityOperation.DELETE) or []:
                response.add_entity(EntityOperation.DELETE, header)
        return response

    @property
    def defers_tasks(self) -> bool:
        """Whether propagation is deferred to tasks (TSK-02, TSK-08)."""
        return self._tasks

    def hold_tasks(self, hold: TaskHold | None) -> None:
        """Record the tasks of the writes that follow with ``hold``, an import's; None stops holding (IMT-01)."""
        self._hold = hold

    async def _replace_classifications(
        self, found: AtlasEntityWithExtInfo, response: EntityMutationResponse, txn: WriteTransaction
    ) -> None:
        """``deleteClassifications`` then ``addClassifications`` of each entity an import updated (IMP-06, DD-305)."""
        updated = {str(header.guid) for header in response.get_entities_by_operation(EntityOperation.UPDATE) or []}
        entities = [found.entity, *(found.referred_entities or {}).values()]
        classifications = EntityClassifications(
            self._store, user=self._user, tasks=self._tasks, notifier=self._notifier, hold=txn.hold
        )
        for entity in entities:
            guid = None if entity is None else txn.guids.get(str(entity.guid), str(entity.guid))
            if entity is None or guid not in updated:
                continue
            for name in list(dict.fromkeys(await self._own_classifications(guid))):
                await classifications.delete_classification(guid, name)
            given = [
                imported_classification(classification)
                for classification in entity.classifications or []
                if classification.entity_guid in {None, entity.guid, guid}
            ]
            if given:
                await classifications.add_classifications(guid, given)

    async def _own_classifications(self, guid: str) -> list[str]:
        """``getTraitNames``: the names of the classifications attached to the entity itself."""
        return [
            str(found.type_name)
            for found in await EntityRetriever(self._store).classifications(guid)
            if not found.entity_guid or found.entity_guid == guid
        ]
