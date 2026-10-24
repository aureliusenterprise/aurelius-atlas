"""What ``AtlasByteType``, ``AtlasShortType``, ``AtlasIntType`` and ``AtlasLongType`` share (VAL-04)."""

from aurelius_atlas_model.errors import java_string

from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.java import is_number, long_value, parse_long, to_big_integer


class IntegralType(BuiltInType):
    """A Java integer type of ``bits`` bits: a number whose integer part is in range, or a string of digits.

    ``byte``, ``short`` and ``int`` check a ``float`` or ``double`` by its saturated ``longValue``; ``long`` checks
    it exactly (``toBigInteger``), as their ``isValidRange`` do. A number in range narrows to its integer part.
    """

    def __init__(self, type_name: str, bits: int) -> None:
        super().__init__(type_name)
        self.min_value = -(2 ** (bits - 1))
        self.max_value = 2 ** (bits - 1) - 1
        self._doubles_exactly = bits == 64  # noqa: PLR2004 - Java's long

    def create_default_value(self) -> int:
        """0."""
        return 0

    def is_valid_value(self, value: object) -> bool:
        """Null, or a value that normalises."""
        return value is None or self.get_normalized_value(value) is not None

    def get_normalized_value(self, value: object) -> int | None:
        """The integer of a number in range, or of a string Java's ``valueOf`` parses; else None.

        Raises:
            ValueError: A NaN or infinite double for ``long``, as Java's ``toBigInteger`` fails on it.
        """
        if value is None or isinstance(value, bool):
            return None
        if is_number(value):
            whole = (
                long_value(value) if isinstance(value, float) and not self._doubles_exactly else to_big_integer(value)
            )
        else:
            whole = parse_long(java_string(value))
        return whole if whole is not None and self.min_value <= whole <= self.max_value else None
