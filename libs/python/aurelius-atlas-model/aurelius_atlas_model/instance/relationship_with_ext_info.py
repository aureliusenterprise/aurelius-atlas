"""``AtlasRelationship.AtlasRelationshipWithExtInfo``: a relationship and the headers of its ends (REL-01)."""

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance.entity_header import AtlasEntityHeader
from aurelius_atlas_model.instance.relationship import AtlasRelationship


class AtlasRelationshipWithExtInfo(AtlasModel):
    """``relationship`` and ``referredEntities``: the headers of the entities it relates, by GUID."""

    relationship: AtlasRelationship | None = None
    referred_entities: dict[str, AtlasEntityHeader] | None = None

    def referred_entities_contains(self, guid: str | None) -> bool:
        """Whether an entity with ``guid`` is referred to."""
        return self.referred_entities is not None and guid in self.referred_entities

    def add_referred_entity(self, guid: str, header: AtlasEntityHeader) -> None:
        """Refer to ``header`` under ``guid``, creating the map when there is none."""
        if self.referred_entities is None:
            self.referred_entities = {}
        self.referred_entities[guid] = header

    def remove_referred_entity(self, guid: str | None) -> AtlasEntityHeader | None:
        """Remove and return the referred header with ``guid``, or None."""
        return None if self.referred_entities is None or guid is None else self.referred_entities.pop(guid, None)
