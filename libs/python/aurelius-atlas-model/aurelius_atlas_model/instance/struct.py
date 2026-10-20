"""``AtlasStruct``: a type name and attribute values, the base of entities, classifications and headers."""

from typing import Any

from aurelius_atlas_model.base import AtlasModel


class AtlasStruct(AtlasModel):
    """An instance of a struct type: its name and its attribute values (ENT-02, ENT-03).

    Attribute values are JSON values as read, null included, until their types normalise them (DD-038).
    """

    type_name: str | None = None
    attributes: dict[str, Any] | None = None

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
