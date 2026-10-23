"""``EntityChangeNotifier``: the entities a mutation changed, told to its listeners (AUD-02, DD-084).

Atlas's ``AtlasEntityChangeNotifier`` (``onEntitiesMutated``, ``pruneResponse``, ``toAtlasEntities``) for the
entity change listeners of version 2, of which the audit listener is the one Aurelius Atlas has.
"""

from collections.abc import Callable, Sequence
from typing import Protocol, runtime_checkable

from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.instance import AtlasEntity, AtlasEntityHeader, EntityMutationResponse, EntityOperation
from aurelius_atlas_model.instance.entity_status import EntityStatus

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore


@runtime_checkable
class EntityChangeListener(Protocol):
    """``EntityChangeListenerV2``'s entity methods: entities as they are after the change, or their headers'."""

    async def on_entities_added(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesAdded``."""
        ...

    async def on_entities_updated(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesUpdated``."""
        ...

    async def on_entities_deleted(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesDeleted``."""
        ...

    async def on_entities_purged(self, entities: Sequence[AtlasEntity], *, user: str | None) -> None:
        """``onEntitiesPurged``."""
        ...


class EntityChangeNotifier:
    """Tells ``listeners`` the entities of ``store`` each mutation changed."""

    def __init__(self, store: EntityStore, listeners: Sequence[EntityChangeListener]) -> None:
        self._store = store
        self._listeners = list(listeners)

    async def on_entities_mutated(self, response: EntityMutationResponse, *, user: str | None) -> None:
        """``onEntitiesMutated``: created, updated, partially updated, deleted, then purged entities (AUD-02).

        The response is to be pruned already (``prune_response``).
        """
        if not self._listeners:
            return
        for operation in (
            EntityOperation.CREATE,
            EntityOperation.UPDATE,
            EntityOperation.PARTIAL_UPDATE,
            EntityOperation.DELETE,
            EntityOperation.PURGE,
        ):
            entities = await self._entities(response.get_entities_by_operation(operation) or [], operation)
            if entities:
                for listener in self._listeners:
                    await _notify(listener, operation, entities, user)

    async def _entities(self, headers: Sequence[AtlasEntityHeader], operation: EntityOperation) -> list[AtlasEntity]:
        """``toAtlasEntities``: deleted and purged ones from their headers, others as read now; internal types left out.

        Entities are read without relationship attributes, as the full text mapper reads them.
        """
        retriever = EntityRetriever(self._store, ignore_relationships=True)
        found: list[AtlasEntity] = []
        for header in headers:
            entity_type = self._store.registry.entity_type(header.type_name)
            if entity_type is None or entity_type.is_internal:
                continue
            if operation in {EntityOperation.DELETE, EntityOperation.PURGE}:
                found.append(entity_of_header(header))
                continue
            try:
                entity = (await retriever.entity_with_ext_info(str(header.guid))).entity
            except AtlasError:
                continue
            if entity is not None:
                found.append(entity)
        return found


async def _notify(
    listener: EntityChangeListener, operation: EntityOperation, entities: list[AtlasEntity], user: str | None
) -> None:
    if operation is EntityOperation.CREATE:
        await listener.on_entities_added(entities, user=user)
    elif operation is EntityOperation.DELETE:
        await listener.on_entities_deleted(entities, user=user)
    elif operation is EntityOperation.PURGE:
        await listener.on_entities_purged(entities, user=user)
    else:
        await listener.on_entities_updated(entities, user=user)


def entity_of_header(header: AtlasEntityHeader) -> AtlasEntity:
    """``new AtlasEntity(AtlasEntityHeader)``: type name, attributes, GUID, status, classifications, meanings."""
    return AtlasEntity(
        type_name=header.type_name,
        attributes=header.attributes,
        guid=header.guid,
        status=header.status,
        classifications=header.classifications,
        meanings=header.meanings,
    )


def prune_response(response: EntityMutationResponse) -> None:
    """``pruneResponse``: each entity listed under the one kind that counts, as Atlas answers and records it (AUD-02).

    ``DELETED`` ones leave the created, updated and partially updated lists; purged ones leave every other list,
    deleted ones the created and updated lists, created ones the updated lists, updated ones the partial ones.
    """
    lists = response.mutated_entities or {}
    changed = [EntityOperation.CREATE, EntityOperation.UPDATE, EntityOperation.PARTIAL_UPDATE]
    for operation in changed:
        _drop(lists, operation, lambda header: header.status is EntityStatus.DELETED)
    for later, earlier in (
        (EntityOperation.PURGE, [EntityOperation.DELETE, *changed]),
        (EntityOperation.DELETE, changed),
        (EntityOperation.CREATE, changed[1:]),
        (EntityOperation.UPDATE, changed[2:]),
    ):
        guids = {header.guid for header in lists.get(later) or []}
        for operation in earlier:
            _drop(lists, operation, lambda header, names=guids: header.guid in names)


def _drop(
    lists: dict[EntityOperation, list[AtlasEntityHeader]],
    operation: EntityOperation,
    drop: Callable[[AtlasEntityHeader], bool],
) -> None:
    """Take the headers ``drop`` names from the list of ``operation``; an emptied list stays, as in Java."""
    if operation in lists:
        lists[operation] = [header for header in lists[operation] if not drop(header)]
