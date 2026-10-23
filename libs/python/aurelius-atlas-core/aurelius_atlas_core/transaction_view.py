"""``TransactionView``: the entity store as one write request has changed it so far (OWN-02, DD-068).

Atlas deletes the owned entities an update drops inside the update's graph transaction, after the update's own
changes. The delete handlers read through this view: the entities and relationships the request changed read as
changed, the relationships it removed are gone, and the entities referring to one are checked against their changed
references.
"""

from collections.abc import Collection, Mapping, Sequence
from typing import Protocol

from aurelius_atlas_typesystem.registry import TypeRegistry

from aurelius_atlas_core.entity_documents import VersionedClassification, VersionedEntity, VersionedRelationship
from aurelius_atlas_core.entity_store import EntityStore


class EntityView(Protocol):
    """What the delete handlers read: ``EntityStore``, or a ``TransactionView`` of it (DD-068)."""

    registry: TypeRegistry

    async def get_many(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The entities with these GUIDs that exist."""
        ...

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, VersionedRelationship]:
        """The relationships with these GUIDs that exist."""
        ...

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose references name any of these GUIDs."""
        ...

    async def get_classifications(self, guids: Sequence[str]) -> dict[str, VersionedClassification]:
        """The classification instances with these GUIDs that exist."""
        ...


class TransactionView:
    """``store`` with a request's changed ``entities`` and ``relationships``, without its ``removed`` ones."""

    def __init__(
        self,
        store: EntityStore,
        *,
        entities: Mapping[str, VersionedEntity],
        relationships: Mapping[str, VersionedRelationship],
        removed: Collection[str],
    ) -> None:
        self.registry = store.registry
        self._store = store
        self._entities = entities
        self._relationships = relationships
        self._removed = removed

    async def get_many(self, guids: Sequence[str]) -> dict[str, VersionedEntity]:
        """The entities with these GUIDs, as the request changed them."""
        found = await self._store.get_many([guid for guid in guids if guid not in self._entities])
        return {
            guid: self._entities[guid] if guid in self._entities else found[guid]
            for guid in guids
            if guid in self._entities or guid in found
        }

    async def get_relationships(self, guids: Sequence[str]) -> dict[str, VersionedRelationship]:
        """The relationships with these GUIDs, as the request changed them; none it removed."""
        wanted = [guid for guid in guids if guid not in self._removed]
        found = await self._store.get_relationships([guid for guid in wanted if guid not in self._relationships])
        return {
            guid: self._relationships[guid] if guid in self._relationships else found[guid]
            for guid in wanted
            if guid in self._relationships or guid in found
        }

    async def get_classifications(self, guids: Sequence[str]) -> dict[str, VersionedClassification]:
        """The classification instances with these GUIDs: a write that drops owned entities changes none (CLS-11)."""
        return await self._store.get_classifications(guids)

    async def referring(self, guids: Sequence[str]) -> list[VersionedEntity]:
        """The entities whose references, as the request changed them, name any of these GUIDs (DD-057)."""
        wanted = set(guids)
        candidates = {found.entity.guid: found for found in await self._store.referring(guids)}
        candidates.update(self._entities)
        referring = []
        for found in candidates.values():
            entity_type = self.registry.entity_type(found.entity.type_name)
            if entity_type is not None and wanted & set(found.entity.reference_guids(entity_type)):
                referring.append(found)
        return referring
