"""What ``AtlasFloatType`` and ``AtlasDoubleType`` share (VAL-05)."""

import math

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.java import JavaNumber, is_number

EPSILON = 0.00000001
"""``FLOAT_EPSILON`` and ``DOUBLE_EPSILON``: how close two equal values are."""


class FloatingType(BuiltInType):
    """A Java floating-point type: a finite number in range, or a string Java's ``valueOf`` parses."""

    def create_default_value(self) -> float:
        """0.0."""
        return 0.0

    def is_valid_value(self, value: object) -> bool:
        """Null, or a value that normalises."""
        return value is None or self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> float | None:
        """A number in range, or a parsed string, that is not infinite; else None."""
        if value is None or isinstance(value, bool):
            return None
        if is_number(value):
            return self._normalized_number(value)
        return self._parsed(value)

    def are_equal_values(
        self,
        left: object,
        right: object,
        guid_assignments: dict[str, str] | None,  # noqa: ARG002 - Java's signature; object ids use it
    ) -> bool:
        """Both null, or both normalise and differ by less than 1e-8 (VAL-05)."""
        if left is None or right is None:
            return left is None and right is None
        normalized_left, normalized_right = self.get_normalized_value(left), self.get_normalized_value(right)
        if normalized_left is None or normalized_right is None:
            return False
        return math.fabs(normalized_left - normalized_right) < EPSILON

    def _normalized_number(self, value: JavaNumber) -> float | None:
        raise NotImplementedError  # pragma: no cover - each floating type has its own

    def _parsed(self, value: object) -> float | None:
        raise NotImplementedError  # pragma: no cover - each floating type has its own
