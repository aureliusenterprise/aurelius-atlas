"""``AtlasObjectId``: a reference to an entity, by GUID or by type and unique attributes (ENT-11)."""

from typing import Any

from aurelius_atlas_model.base import AtlasModel


class AtlasObjectId(AtlasModel):
    """An entity reference: its GUID, or its type name and the unique attribute values that identify it."""

    guid: str | None = None
    type_name: str | None = None
    unique_attributes: dict[str, Any] | None = None

    def __eq__(self, other: object) -> bool:
        """``AtlasObjectId.equals``: by GUID when either has a non-empty one, else by type and unique attributes."""
        if self is other:
            return True
        if type(other) is not type(self):
            return False
        assert isinstance(other, AtlasObjectId)  # noqa: S101 - narrowed by the type check above
        if not self.guid and not other.guid:
            return self.type_name == other.type_name and self.unique_attributes == other.unique_attributes
        return self.guid == other.guid

    __hash__ = None  # mutable, as the Java class
