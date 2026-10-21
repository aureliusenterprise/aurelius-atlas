"""``AtlasBuiltInTypes.AtlasStringType`` (VAL-09)."""

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_STRING

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType


class StringType(BuiltInType):
    """``string``: every value, as Java's text of it."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_STRING)

    def create_default_value(self) -> str:
        """The empty string."""
        return ""

    def create_optional_default_value(self) -> None:
        """Null: an optional string attribute has no default."""
        return

    def is_valid_value(self, value: object) -> bool:  # noqa: ARG002 - every value is a string value
        """Always."""
        return True

    def get_normalized_value(self, value: object) -> str | None:
        """``obj.toString()``: Java's text of the value, or None for null."""
        return None if value is None else java_string(value)
