"""What arrays and maps do with the values they hold: parse a string, compare as Java does (VAL-12, VAL-13)."""

from collections.abc import Mapping
from decimal import Decimal

from aurelius_atlas_model import codec


def parse_json(text: str) -> object:
    """``AtlasType.fromJson``: the JSON value of ``text`` read with Atlas's mapper, or None when it is not JSON."""
    try:
        return codec.loads(text)
    except ValueError:
        return None


def java_equals(left: object, right: object) -> bool:
    """``Object.equals`` of two Java values (DD-040): classes must match, and a ``BigDecimal`` compares its scale."""
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, Decimal) and isinstance(right, Decimal):
        return left == right and left.as_tuple().exponent == right.as_tuple().exponent
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(java_equals(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(java_equals(a, b) for a, b in zip(left, right, strict=True))
    if type(left) is not type(right):
        return False
    return left == right


def java_distinct(values: list[object]) -> list[object]:
    """A ``HashSet`` of ``values``: each value once, by Java's ``equals``."""
    kept: list[object] = []
    for value in values:
        if not any(java_equals(value, other) for other in kept):
            kept.append(value)
    return kept
