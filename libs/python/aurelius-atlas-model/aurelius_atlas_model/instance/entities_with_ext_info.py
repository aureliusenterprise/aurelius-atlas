"""``AtlasEntity.AtlasEntitiesWithExtInfo``: several entities and the entities they refer to (ENT-10)."""

from typing import overload

from aurelius_atlas_model.instance.entity import AtlasEntity
from aurelius_atlas_model.instance.entity_ext_info import AtlasEntityExtInfo


class AtlasEntitiesWithExtInfo(AtlasEntityExtInfo):
    """The body of a bulk read or write: ``entities`` and ``referredEntities``."""

    entities: list[AtlasEntity] | None = None

    def get_entity(self, guid: str | None) -> AtlasEntity | None:
        """The referred entity with ``guid``, else the first main entity with that GUID."""
        found = super().get_entity(guid)
        if found is None:
            return next((entity for entity in self.entities or [] if entity.guid == guid), None)
        return found

    def add_entity(self, entity: AtlasEntity) -> None:
        """Append a main entity, creating the list."""
        if self.entities is None:
            self.entities = []
        self.entities.append(entity)

    @overload
    def remove_entity(self, guid: str | None) -> AtlasEntity | None: ...

    @overload
    def remove_entity(self, guid: AtlasEntity) -> None: ...

    def remove_entity(self, guid: str | AtlasEntity | None) -> AtlasEntity | None:
        """Remove a referred entity by GUID, or the first main entity equal to an entity (Java's two overloads)."""
        if not isinstance(guid, AtlasEntity):
            return super().remove_entity(guid)
        if self.entities is not None and guid in self.entities:
            self.entities.remove(guid)
        return None

    def compact(self) -> None:
        """Remove the main entities from the referred entities."""
        for entity in self.entities or []:
            self.remove_referred_entity(entity.guid)
