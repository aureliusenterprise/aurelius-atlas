"""``AtlasEnumType``: an enum's elements, by value and ordinal, and its values (TRG-14, VAL-11)."""

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import AtlasEnumDef, AtlasEnumElementDef

from aurelius_atlas_typesystem.atlas_type import AtlasType


class EnumType(AtlasType):
    """An enum type: its elements by value and ordinal, and its default (``AtlasEnumType``, TRG-14)."""

    def __init__(self, enum_def: AtlasEnumDef) -> None:
        super().__init__(enum_def.name, enum_def.category, enum_def.service_type)
        self.enum_def = enum_def
        self._elements = {str(element.value).lower(): element for element in enum_def.element_defs}
        first = enum_def.element_defs[0].value if enum_def.element_defs else None
        self.default_value = enum_def.default_value if enum_def.default_value is not None else first

    def element(self, value: str | None) -> AtlasEnumElementDef | None:
        """The element with ``value``, compared without case, or None (TRG-14)."""
        return None if value is None else self._elements.get(value.lower())

    def element_by_ordinal(self, ordinal: int | None) -> AtlasEnumElementDef | None:
        """The element with ``ordinal``, or None (TRG-14)."""
        if ordinal is None:
            return None
        return next((element for element in self._elements.values() if element.ordinal == ordinal), None)

    def create_default_value(self) -> str | None:
        """The enum's default value: its ``defaultValue``, else its first element's (TRG-14)."""
        return self.default_value

    def is_valid_value(self, value: object) -> bool:
        """Null, or a value whose Java text is an element's value, ignoring case (VAL-11)."""
        return value is None or java_string(value).lower() in self._elements

    def get_normalized_value(self, value: object) -> str | None:
        """The value of the element whose value is the Java text of ``value``, ignoring case; else None."""
        element = None if value is None else self._elements.get(java_string(value).lower())
        return None if element is None else element.value
