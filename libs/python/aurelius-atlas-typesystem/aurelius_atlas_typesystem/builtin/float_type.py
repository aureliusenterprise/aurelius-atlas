"""``AtlasBuiltInTypes.AtlasFloatType`` (VAL-05)."""

import math
from decimal import Decimal

from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.typedef import ATLAS_TYPE_FLOAT

from aurelius_atlas_typesystem.builtin.floating_type import FloatingType
from aurelius_atlas_typesystem.java import FLOAT_MAX, JavaNumber, double_value, is_long, parse_float, to_float32


class FloatType(FloatingType):
    """``float``: a number within ±``Float.MAX_VALUE``, held as the shortest decimal of its 32-bit value."""

    def __init__(self) -> None:
        super().__init__(ATLAS_TYPE_FLOAT)

    def _normalized_number(self, value: JavaNumber) -> float | None:
        """``isValidRange``, then ``floatValue``: an integer within ``long`` is always in range (DV-11)."""
        if isinstance(value, float):
            if not math.isfinite(value):
                return None  # a NaN double fails the range check; only a Java Float may be NaN
            single = to_float32(value)
            return None if math.isinf(single) else single
        if is_long(value):
            return to_float32(float(value))
        as_double = double_value(value)
        if math.isinf(as_double):
            return None  # Java fails with NumberFormatException here (DV-11)
        exact = Decimal(as_double)
        if not -Decimal(FLOAT_MAX) <= exact <= Decimal(FLOAT_MAX):
            return None
        return to_float32(float(value))

    def _parsed(self, value: object) -> float | None:
        parsed = parse_float(java_string(value))
        return None if parsed is None or math.isinf(parsed) else parsed
