"""``AtlasEntity.AtlasEntityWithExtInfo``: one entity and the entities it refers to (ENT-10)."""

from aurelius_atlas_model.instance.entity import AtlasEntity
from aurelius_atlas_model.instance.entity_ext_info import AtlasEntityExtInfo


class AtlasEntityWithExtInfo(AtlasEntityExtInfo):
    """The body of a single-entity read or write: ``entity`` and ``referredEntities``."""

    entity: AtlasEntity | None = None

    def get_entity(self, guid: str | None) -> AtlasEntity | None:
        """The referred entity with ``guid``, else the main entity when it has that GUID."""
        found = super().get_entity(guid)
        if found is None and self.entity is not None and self.entity.guid == guid:
            return self.entity
        return found

    def compact(self) -> None:
        """Remove the main entity from the referred entities."""
        if self.entity is not None:
            self.remove_entity(self.entity.guid)
