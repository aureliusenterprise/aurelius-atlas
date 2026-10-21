"""What arrays and maps do with the values they hold: parse a string, compare as Java does (VAL-12, VAL-13)."""

from collections.abc import Mapping
from datetime import datetime
from decimal import Decimal

from aurelius_atlas_model import codec
from aurelius_atlas_model.errors import java_string
from aurelius_atlas_model.instance import AtlasRelatedObjectId

from aurelius_atlas_typesystem.java import INT_MAX, INT_MIN, LONG_MAX, LONG_MIN


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


def relationship_type_of(value: object) -> str | None:
    """``AtlasEntityUtil.getRelationshipType``: the relationship type a value names, or None (EVL-08).

    That of a related object id or a map's ``relationshipType``; else of the first element or map value naming one.
    """
    if isinstance(value, AtlasRelatedObjectId):
        return value.relationship_type
    if isinstance(value, list | tuple | set | frozenset):
        return next((found for item in value if (found := relationship_type_of(item)) is not None), None)
    if isinstance(value, Mapping):
        if "relationshipType" in value:
            named = value["relationshipType"]
            return None if named is None else java_string(named)
        return next((found for item in value.values() if (found := relationship_type_of(item)) is not None), None)
    return None


def java_class_name(value: object) -> str:
    """``obj.getClass().getName()`` of a Java value held as DD-040 says: what Jackson would have made of it."""
    match value:
        case bool():
            return "java.lang.Boolean"
        case int() if INT_MIN <= value <= INT_MAX:
            return "java.lang.Integer"
        case int() if LONG_MIN <= value <= LONG_MAX:
            return "java.lang.Long"
        case int():
            return "java.math.BigInteger"
        case _:
            return _CLASS_NAMES.get(type(value), _model_class_name(value))


def _model_class_name(value: object) -> str:
    name = type(value).__name__
    return f"org.apache.atlas.model.instance.{name}" if name.startswith("Atlas") else name


_CLASS_NAMES: dict[type, str] = {
    str: "java.lang.String",
    float: "java.lang.Double",
    Decimal: "java.math.BigDecimal",
    datetime: "java.util.Date",
    list: "java.util.ArrayList",
    tuple: "[Ljava.lang.Object;",
    set: "java.util.HashSet",
    frozenset: "java.util.HashSet",
    dict: "java.util.LinkedHashMap",
}
"""The classes Jackson reads a body's values as (DD-040)."""
