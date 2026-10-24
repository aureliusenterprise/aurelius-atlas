"""Atlas's built-in types, one module per nested class of ``AtlasBuiltInTypes`` (DD-041)."""

from collections.abc import Callable

from aurelius_atlas_typesystem.builtin.big_decimal_type import BigDecimalType
from aurelius_atlas_typesystem.builtin.big_integer_type import BigIntegerType
from aurelius_atlas_typesystem.builtin.boolean_type import BooleanType
from aurelius_atlas_typesystem.builtin.builtin_type import BuiltInType
from aurelius_atlas_typesystem.builtin.byte_type import ByteType
from aurelius_atlas_typesystem.builtin.date_type import DateType
from aurelius_atlas_typesystem.builtin.double_type import DoubleType
from aurelius_atlas_typesystem.builtin.float_type import FloatType
from aurelius_atlas_typesystem.builtin.int_type import IntType
from aurelius_atlas_typesystem.builtin.long_type import LongType
from aurelius_atlas_typesystem.builtin.object_id_type import ObjectIdType
from aurelius_atlas_typesystem.builtin.short_type import ShortType
from aurelius_atlas_typesystem.builtin.string_type import StringType

PRIMITIVE_TYPES: tuple[Callable[[], BuiltInType], ...] = (
    BooleanType,
    ByteType,
    ShortType,
    IntType,
    LongType,
    FloatType,
    DoubleType,
    BigIntegerType,
    BigDecimalType,
    DateType,
    StringType,
)
"""The primitive types, ``string`` and ``date``, in ``AtlasTypeRegistry``'s order; ``objectid`` is apart."""

__all__ = [
    "PRIMITIVE_TYPES",
    "BigDecimalType",
    "BigIntegerType",
    "BooleanType",
    "BuiltInType",
    "ByteType",
    "DateType",
    "DoubleType",
    "FloatType",
    "IntType",
    "LongType",
    "ObjectIdType",
    "ShortType",
    "StringType",
]
