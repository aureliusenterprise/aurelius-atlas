"""``AtlasEntity.AtlasEntityExtInfo``: the entities a request or response refers to, by GUID (ENT-10)."""

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.entity import AtlasEntity


class AtlasEntityExtInfo(AtlasModel):
    """``referredEntities``: the entities that the main entity or entities refer to, by their GUIDs."""

    referred_entities: dict[str, AtlasEntity] | None = None

    def add_referred_entity(self, entity: AtlasEntity) -> None:
        """Refer to ``entity`` under its own GUID (``addReferredEntity(AtlasEntity)``)."""
        self.add_referred_entity_as(entity.guid, entity)

    def add_referred_entity_as(self, guid: str | None, entity: AtlasEntity) -> None:
        """Refer to ``entity`` under ``guid``; without a GUID nothing is added, but the map is still created."""
        if self.referred_entities is None:
            self.referred_entities = {}
        if guid is not None:
            self.referred_entities[guid] = entity

    def get_referred_entity(self, guid: str | None) -> AtlasEntity | None:
        """The referred entity with ``guid``, or None."""
        return None if self.referred_entities is None or guid is None else self.referred_entities.get(guid)

    def remove_referred_entity(self, guid: str | None) -> AtlasEntity | None:
        """Remove and return the referred entity with ``guid``, or None."""
        return None if self.referred_entities is None or guid is None else self.referred_entities.pop(guid, None)

    def get_entity(self, guid: str | None) -> AtlasEntity | None:
        """The entity with ``guid`` among those this holds; here, the referred ones."""
        return self.get_referred_entity(guid)

    def remove_entity(self, guid: str | None) -> AtlasEntity | None:
        """Remove and return the referred entity with ``guid``, or None."""
        return self.remove_referred_entity(guid)

    def has_entity(self, guid: str | None) -> bool:
        """Whether this holds an entity with ``guid``."""
        return self.get_entity(guid) is not None

    def update_entity_guid(self, old_guid: str, new_guid: str) -> None:
        """Give the entity with ``old_guid`` the GUID ``new_guid``; a referred one is moved to it in the map."""
        entity = self.get_entity(old_guid)
        if entity is not None:
            entity.guid = new_guid
            if self.remove_entity(old_guid) is not None:
                self.add_referred_entity_as(new_guid, entity)

    def compact(self) -> None:
        """Remove referred entities that are also main entities; there are none here."""
