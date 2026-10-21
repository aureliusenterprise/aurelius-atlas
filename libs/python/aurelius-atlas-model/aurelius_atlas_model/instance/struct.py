"""``AtlasStruct``: a type name and attribute values, the base of entities, classifications and headers."""

from collections.abc import Mapping
from typing import Any, Self

from aurelius_atlas_model.base import AtlasModel
from aurelius_atlas_model.errors import java_string


class AtlasStruct(AtlasModel):
    """An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).

    Attribute values are JSON values as read, null included, until their types normalise them (DD-038).
    """

    type_name: str | None = None
    attributes: dict[str, Any] | None = None

    @classmethod
    def from_map(cls, values: Mapping[str, Any]) -> Self:
        """``AtlasStruct(Map)``: ``typeName``, and ``attributes`` or, without an ``attributes`` map, the whole map.

        Not how a body is read, which is Jackson's (ENT-02); Atlas's code makes structs from maps (VAL-14).
        """
        type_name = values.get("typeName")
        attributes = values.get("attributes")
        return cls(
            type_name=None if type_name is None else java_string(type_name),
            attributes=dict(attributes if isinstance(attributes, Mapping) else values),
        )

    def has_attribute(self, name: str) -> bool:
        """Whether attribute ``name`` is present, even with a null value."""
        return self.attributes is not None and name in self.attributes

    def get_attribute(self, name: str) -> Any:  # noqa: ANN401 - attribute values are untyped JSON
        """The value of attribute ``name``, or None."""
        return None if self.attributes is None else self.attributes.get(name)

    def set_attribute(self, name: str, value: Any) -> None:  # noqa: ANN401 - attribute values are untyped JSON
        """Set attribute ``name``, creating the attributes when there are none."""
        if self.attributes is None:
            self.attributes = {}
        self.attributes[name] = value

    def remove_attribute(self, name: str) -> Any:  # noqa: ANN401 - attribute values are untyped JSON
        """Remove attribute ``name`` and return its value, or None."""
        return None if self.attributes is None else self.attributes.pop(name, None)
