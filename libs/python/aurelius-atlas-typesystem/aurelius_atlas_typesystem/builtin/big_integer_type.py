"""``AtlasBuiltInTypes.AtlasBigIntegerType`` (VAL-06)."""

from decimal import Decimal

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_BIGINTEGER

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.java import is_number, long_value, parse_big_decimal, to_big_integer


class BigIntegerType(BuiltInType):
    """``biginteger``: any number or numeric string, truncated toward zero."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_BIGINTEGER)

    def create_default_value(self) -> int:
        """0."""
        return 0

    def is_valid_value(self, value: object) -> bool:
        """Null, or a value that normalises."""
        return value is None or self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> int | None:
        """An integer as it is; a decimal truncated; a double's ``longValue``; a string ``BigDecimal`` parses."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int | Decimal):
            return to_big_integer(value)
        if is_number(value):
            return long_value(value)
        parsed = parse_big_decimal(java_string(value))
        return None if parsed is None else to_big_integer(parsed)
