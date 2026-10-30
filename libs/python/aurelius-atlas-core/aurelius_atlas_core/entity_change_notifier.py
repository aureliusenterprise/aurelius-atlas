"""``EntityChangeNotifier``: the entities and classifications a request changed, told to its listeners.

Atlas's ``AtlasEntityChangeNotifier`` (``onEntitiesMutated``, ``pruneResponse``, ``toAtlasEntities``, the
classification methods, ``notifyPropagatedEntities``, the term methods) for the entity change listeners of version 2,
of which the audit listener is the one Aurelius Atlas has (AUD-02, CAU-01 to CAU-06, GTA-04, DD-084, DD-085).
"""

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from aurelius_atlas_model.errors import AtlasError
from aurelius_atlas_model.glossary import AtlasGlossaryTerm
from aurelius_atlas_model.instance import (
    AtlasClassification,
    AtlasEntity,
    AtlasEntityHeader,
    EntityMutationResponse,
    EntityOperation,
)
from aurelius_atlas_model.instance.entity_status import EntityStatus

from aurelius_atlas_core.entity_retriever import EntityRetriever
from aurelius_atlas_core.entity_store import EntityStore
from aurelius_atlas_core.stored_classification import StoredClassification


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

    async def on_classifications_added(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], *, user: str | None
    ) -> None:
        """``onClassificationsAdded``: the classifications added to each entity, directly or propagated."""
        ...

    async def on_classifications_updated(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], context: Propagations
    ) -> None:
        """``onClassificationsUpdated``: the classifications updated, told to each entity notified."""
        ...

    async def on_classifications_deleted(
        self, guids: Sequence[str], classifications: Sequence[AtlasClassification], *, user: str | None
    ) -> None:
        """``onClassificationsDeleted``: the classifications removed from each entity, directly or propagated."""
        ...

    async def on_term_added(self, term: AtlasGlossaryTerm, guids: Sequence[str], *, user: str | None) -> None:
        """``onTermAdded``: the term assigned to each entity."""
        ...

    async def on_term_deleted(self, term: AtlasGlossaryTerm, guids: Sequence[str], *, user: str | None) -> None:
        """``onTermDeleted``: the term's assignment to each entity removed."""
        ...


@dataclass
class RequestRecord:
    """What a request tells the notifier after its write: classifications added directly (CAU-02), then the
    propagations it added and removed, per entity (DD-086).
    """  # noqa: D205 - one sentence

    added_classifications: list[tuple[list[str], StoredClassification]] = field(default_factory=list)
    added: dict[str, list[StoredClassification]] = field(default_factory=dict)
    removed: dict[str, list[StoredClassification]] = field(default_factory=dict)

    def merge(
        self,
        added: Mapping[str, Sequence[StoredClassification]],
        removed: Mapping[str, Sequence[StoredClassification]],
    ) -> None:
        """Take another part of the request's propagations."""
        for own, more in ((self.added, added), (self.removed, removed)):
            for guid, classifications in more.items():
                own.setdefault(guid, []).extend(classifications)


@dataclass(frozen=True)
class Propagations:
    """A request's user and the propagations it added and removed, per entity, as read (``RequestContext``)."""

    user: str | None
    added: Mapping[str, Sequence[AtlasClassification]] = field(default_factory=dict)
    removed: Mapping[str, Sequence[AtlasClassification]] = field(default_factory=dict)


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

    async def on_classifications_added(
        self, guids: Sequence[str], classifications: Sequence[StoredClassification], *, user: str | None
    ) -> None:
        """``onClassificationsAddedToEntities``: the classifications added to these entities (CAU-02)."""
        read = await self._read(classifications)
        for listener in self._listeners:
            await listener.on_classifications_added(guids, read, user=user)

    async def on_classifications_updated(
        self,
        guids: Sequence[str],
        classifications: Sequence[StoredClassification],
        *,
        user: str | None,
        added: Mapping[str, Sequence[StoredClassification]],
        removed: Mapping[str, Sequence[StoredClassification]],
    ) -> None:
        """``onClassificationUpdatedToEntity`` of each entity: updates, told what the request propagated (CAU-03)."""
        read = await self._read(classifications)
        context = Propagations(user, await self._read_map(added), await self._read_map(removed))
        for guid in guids:
            for listener in self._listeners:
                await listener.on_classifications_updated([guid], read, context)

    async def on_classifications_deleted(
        self, guids: Sequence[str], classifications: Sequence[StoredClassification], *, user: str | None
    ) -> None:
        """``onClassificationsDeletedFromEntities``: the classifications removed from these entities (CAU-04)."""
        read = await self._read(classifications)
        for listener in self._listeners:
            await listener.on_classifications_deleted(guids, read, user=user)

    async def on_term_added_to_entities(
        self, term: AtlasGlossaryTerm, guids: Sequence[str], *, user: str | None
    ) -> None:
        """``onTermAddedToEntities``: the term assigned to the entities of these GUIDs that exist (GTA-04)."""
        found = await self._existing(guids)
        if found:
            for listener in self._listeners:
                await listener.on_term_added(term, found, user=user)

    async def on_term_deleted_from_entities(
        self, term: AtlasGlossaryTerm, guids: Sequence[str], *, user: str | None
    ) -> None:
        """``onTermDeletedFromEntities``: the term's assignment to the entities that exist removed (GTA-04)."""
        found = await self._existing(guids)
        if found:
            for listener in self._listeners:
                await listener.on_term_deleted(term, found, user=user)

    async def _existing(self, guids: Sequence[str]) -> list[str]:
        """``getAndCacheEntity``: the GUIDs of entities there are, in order."""
        found = await self._store.get_many(list(dict.fromkeys(guids)))
        return [guid for guid in guids if guid in found]

    async def notify_propagated_entities(
        self,
        added: Mapping[str, Sequence[StoredClassification]],
        removed: Mapping[str, Sequence[StoredClassification]],
        *,
        user: str | None,
        deleted: Collection[str] = (),
    ) -> None:
        """``notifyPropagatedEntities``: each entity's added, then each one's removed propagations (CAU-05).

        Entities the request deleted, and those that no longer exist, are left out.
        """
        if not self._listeners or not (added or removed):
            return
        existing = await self._store.get_many([*added, *removed])
        for propagations, notify in (
            (added, self.on_classifications_added),
            (removed, self.on_classifications_deleted),
        ):
            for guid, classifications in propagations.items():
                if guid not in deleted and guid in existing:
                    await notify([guid], classifications, user=user)

    async def _read(self, classifications: Sequence[StoredClassification]) -> list[AtlasClassification]:
        """The classifications as a read answers them (DV-42)."""
        retriever = EntityRetriever(self._store)
        return [await retriever.classification_of(classification) for classification in classifications]

    async def _read_map(
        self, propagations: Mapping[str, Sequence[StoredClassification]]
    ) -> dict[str, list[AtlasClassification]]:
        return {guid: await self._read(classifications) for guid, classifications in propagations.items()}

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
