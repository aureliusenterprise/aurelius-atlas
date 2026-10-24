"""``AtlasRelatedObjectId``: a related entity as a relationship attribute shows it (ENT-12)."""

from collections.abc import Mapping
from typing import Any

from pydantic import model_validator

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance.entity_status import EntityStatus
from aurelius_atlas_model.instance.object_id import AtlasObjectId
from aurelius_atlas_model.instance.relationship_status import RelationshipStatus
from aurelius_atlas_model.instance.struct import AtlasStruct

_RELATIONSHIP_TYPE = ("relationshipType", "relationship_type")
_RELATIONSHIP_ATTRIBUTES = ("relationshipAttributes", "relationship_attributes")


class AtlasRelatedObjectId(AtlasObjectId):
    """The other end of a relationship: the entity, its status and display text, and the relationship."""

    entity_status: EntityStatus | None = None
    display_text: str | None = None
    relationship_type: str | None = None
    relationship_guid: str | None = None
    relationship_status: RelationshipStatus | None = None
    relationship_attributes: AtlasStruct | None = None
    qualified_name: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _relationship_type_in_order(cls, data: Any) -> Any:  # noqa: ANN401 - any input Pydantic accepts
        """Jackson calls the setters in the body's order, and ``setRelationshipAttributes`` sets the type."""
        if not isinstance(data, dict):
            return data
        relationship_type: Any = None
        decided = False
        for key, value in data.items():
            if key in _RELATIONSHIP_TYPE:
                relationship_type, decided = value, True
            elif key in _RELATIONSHIP_ATTRIBUTES:
                struct_type = value.get("typeName", value.get("type_name")) if isinstance(value, dict) else None
                if isinstance(value, AtlasStruct):
                    struct_type = value.type_name
                if struct_type is not None:
                    relationship_type, decided = struct_type, True
        if not decided:
            return data
        kept = {key: value for key, value in data.items() if key not in _RELATIONSHIP_TYPE}
        return kept | {"relationship_type": relationship_type}  # by name: assignment validates by name too

    def read_map(self, values: Mapping[str, Any]) -> None:
        """``AtlasRelatedObjectId(Map)``: the object id's fields, then the relationship's (VAL-14).

        In Java's order: the GUID, the attributes as a struct (which set the type), the type and the status.

        Raises:
            ValueError: ``relationshipStatus`` is not a relationship status, as Java's ``valueOf`` fails.
        """
        super().read_map(values)
        guid, attributes = values.get("relationshipGuid"), values.get("relationshipAttributes")
        type_, status = values.get("relationshipType"), values.get("relationshipStatus")
        if guid is not None:
            self.relationship_guid = java_string(guid)
        if isinstance(attributes, Mapping):
            self.set_relationship_attributes(AtlasStruct.from_map(attributes))
        elif isinstance(attributes, AtlasStruct):
            self.set_relationship_attributes(attributes.model_copy(deep=True))
        if type_ is not None:
            self.relationship_type = java_string(type_)
        if status is not None:
            self.relationship_status = RelationshipStatus(java_string(status))

    def set_relationship_attributes(self, relationship_attributes: AtlasStruct | None) -> None:
        """Set the relationship's attributes; their type name, when set, becomes the relationship type."""
        self.relationship_attributes = relationship_attributes
        if relationship_attributes is not None and relationship_attributes.type_name is not None:
            self.relationship_type = relationship_attributes.type_name

    def __eq__(self, other: object) -> bool:
        """``AtlasRelatedObjectId.equals``: the object id's equality, then the relationship's fields."""
        if not super().__eq__(other) or not isinstance(other, AtlasRelatedObjectId):
            return False
        return (
            self.entity_status == other.entity_status
            and self.display_text == other.display_text
            and self.relationship_type == other.relationship_type
            and self.relationship_guid == other.relationship_guid
            and self.relationship_status == other.relationship_status
            and self.relationship_attributes == other.relationship_attributes
        )

    __hash__ = None  # mutable, as the Java class
