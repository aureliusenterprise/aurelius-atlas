"""``StoredRelationship``: a relationship instance as stored, what Atlas keeps on its edge (REL-05, DD-061)."""

from datetime import UTC, datetime, timedelta
from typing import Any

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.instance import AtlasObjectId, AtlasRelationship, RelationshipStatus
from aurelius_atlas_model.typedef import PropagateTags
from pydantic import Field

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MILLISECOND = timedelta(milliseconds=1)


class StoredRelationship(AtlasModel):
    """One document of the relationship index: its ends' GUIDs, label, state, times, users and attribute values.

    Attribute values are stored by attribute name (DD-049); ``index`` is the position the last write of an array
    gave it (DD-065); ``write_id`` names the write that last wrote it (DD-046).
    """

    guid: str
    type_name: str
    label: str | None = None
    end1_guid: str
    end2_guid: str
    state: RelationshipStatus = RelationshipStatus.ACTIVE
    propagate_tags: PropagateTags | None = None
    create_time: int = 0
    update_time: int = 0
    created_by: str | None = None
    updated_by: str | None = None
    version: int = 0
    provenance_type: int | None = None
    home_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    index: int | None = None
    write_id: str | None = None

    def ends(self) -> tuple[str, str]:
        """The GUIDs of end 1 and end 2."""
        return self.end1_guid, self.end2_guid

    def to_relationship(
        self, end1: AtlasObjectId, end2: AtlasObjectId, attribute_names: list[str]
    ) -> AtlasRelationship:
        """``mapEdgeToAtlasRelationship``: system fields, the ends as given, every attribute by name (REL-06).

        Propagated and blocked classifications are empty until 3.4.
        """
        relationship = AtlasRelationship(
            type_name=self.type_name,
            guid=self.guid,
            created_by=self.created_by,
            updated_by=self.updated_by,
            create_time=_EPOCH + self.create_time * _MILLISECOND,
            update_time=_EPOCH + self.update_time * _MILLISECOND,
            version=self.version,
            provenance_type=self.provenance_type or 0,
            home_id=self.home_id,
            status=self.state,
            end1=end1,
            end2=end2,
            label=self.label,
            propagate_tags=self.propagate_tags,
            propagated_classifications=[],
            blocked_propagated_classifications=[],
        )
        for name in attribute_names:
            relationship.set_attribute(name, self.attributes.get(name))
        return relationship
