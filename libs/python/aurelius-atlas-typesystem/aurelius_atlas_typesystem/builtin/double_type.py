"""``AtlasBuiltInTypes.AtlasDoubleType`` (VAL-05)."""

import math
from decimal import Decimal

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_DOUBLE

from aurelius_atlas_typesystem.builtin.floating_type import FloatingType
from aurelius_atlas_typesystem.java import DOUBLE_MAX, JavaNumber, is_long, parse_double


class DoubleType(FloatingType):
    """``double``: a number within ±``Double.MAX_VALUE``, held as a Python ``float``."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_DOUBLE)

    def _normalized_number(self, value: JavaNumber) -> float | None:
        """``isValidRange``, then ``doubleValue``: a ``BigInteger`` or ``BigDecimal`` is checked exactly."""
        if isinstance(value, float):
            return None if math.isinf(value) else value
        if is_long(value):
            return float(value)
        exact = Decimal(value)
        if not -Decimal(DOUBLE_MAX) <= exact <= Decimal(DOUBLE_MAX):
            return None
        return float(value)

    def _parsed(self, value: object) -> float | None:
        parsed = parse_double(java_string(value))
        return None if parsed is None or math.isinf(parsed) else parsed
