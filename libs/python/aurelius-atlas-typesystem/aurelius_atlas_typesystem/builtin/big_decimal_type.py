"""``AtlasBuiltInTypes.AtlasBigDecimalType`` (VAL-07)."""

import math
from decimal import Decimal

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_BIGDECIMAL

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.java import big_decimal_value_of, double_value, is_long, is_number, parse_big_decimal


class BigDecimalType(BuiltInType):
    """``bigdecimal``: any number, or a string Java's ``BigDecimal`` parses, with its digits kept."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_BIGDECIMAL)

    def create_default_value(self) -> Decimal:
        """0."""
        return Decimal(0)

    def is_valid_value(self, value: object) -> bool:
        """Null or any number; otherwise a value that normalises."""
        return value is None or is_number(value) or self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> Decimal | None:
        """A decimal as it is; a ``BigInteger`` exactly; 0 as ``0``; another number by ``BigDecimal.valueOf``.

        Raises:
            ValueError: A NaN or infinite double, which ``BigDecimal.valueOf`` rejects.
        """
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, int) and not is_long(value):
            return Decimal(value)
        if is_number(value):
            if value == 0 and isinstance(value, int):
                return Decimal(0)
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(java_string(value))
            return big_decimal_value_of(double_value(value))
        return parse_big_decimal(java_string(value))
