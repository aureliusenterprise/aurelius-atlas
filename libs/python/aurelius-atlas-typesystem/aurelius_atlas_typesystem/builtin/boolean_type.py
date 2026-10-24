"""``AtlasBuiltInTypes.AtlasBooleanType`` (VAL-03)."""

from aurelius_atlas_model.typedef import ATLAS_TYPE_BOOLEAN

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType


class BooleanType(BuiltInType):
    """``boolean``: a boolean, or ``true`` or ``false`` in any case."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_BOOLEAN)

    def create_default_value(self) -> bool:
        """``false``."""
        return False

    def is_valid_value(self, value: object) -> bool:
        """Null, or a value that normalises."""
        return value is None or self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> bool | None:
        """A boolean as it is; the string ``true`` or ``false``, ignoring case; else None."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        return None
