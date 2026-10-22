"""``AtlasObjectId``: a reference to an entity, by GUID or by type and unique attributes (ENT-11)."""

from collections.abc import Mapping
from typing import Any, Self

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import java_string


class AtlasObjectId(AtlasModel):
    """An entity reference: its GUID, or its type name and the unique attribute values that identify it."""

    guid: str | None = None
    type_name: str | None = None
    unique_attributes: dict[str, Any] | None = None

    @classmethod
    def from_map(cls, values: Mapping[str, Any]) -> Self:
        """``AtlasObjectId(Map)``: ``guid`` and ``typeName`` as text, ``uniqueAttributes`` when it is a map (VAL-14)."""
        found = cls(guid=None)
        found.read_map(values)
        return found

    def read_map(self, values: Mapping[str, Any]) -> None:
        """Set the fields Java's map constructor reads from ``values``."""
        guid, type_name, unique = values.get("guid"), values.get("typeName"), values.get("uniqueAttributes")
        if guid is not None:
            self.guid = java_string(guid)
        if type_name is not None:
            self.type_name = java_string(type_name)
        if isinstance(unique, Mapping):
            self.unique_attributes = dict(unique)

    def __eq__(self, other: object) -> bool:
        """``AtlasObjectId.equals``: by GUID when either has a non-empty one, else by type and unique attributes."""
        if not isinstance(other, AtlasObjectId) or type(other) is not type(self):
            return False
        if not self.guid and not other.guid:
            return self.type_name == other.type_name and self.unique_attributes == other.unique_attributes
        return self.guid == other.guid

    __hash__ = None  # mutable, as the Java class

    def java_string(self) -> str:
        """``AtlasObjectId.toString``, as errors name an object id: ``AtlasObjectId{guid='…', …}`` (EWR-05)."""
        unique = ", ".join(
            f"{java_string(key)}:{java_string(value)}" for key, value in (self.unique_attributes or {}).items()
        )
        guid, type_name = java_string(self.guid), java_string(self.type_name)
        return f"AtlasObjectId{{guid='{guid}', typeName='{type_name}', uniqueAttributes={{{unique}}}}}"
