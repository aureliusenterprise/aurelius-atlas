"""The Atlas JSON codec (VAL-01).

Read from ``AtlasJsonProvider`` and ``AtlasJson`` of Atlas 2.4.0 and Jackson's defaults:
``USE_BIG_DECIMAL_FOR_FLOATS``, dates as timestamps, NaN as a string.
"""

import math
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from aurelius_atlas_model import codec
from aurelius_atlas_model.instance import AtlasEntity, AtlasStruct


@pytest.mark.covers("aurelius_atlas_model.codec.loads", rules=["VAL-01"])
def test__floats_are_read_as_decimals_with_their_digits() -> None:
    """Integers stay exact, every fraction or exponent is a ``Decimal``; objects keep their order."""
    read = codec.loads(b'{"b": 1.10, "a": 1e3, "big": 123456789012345678901234567890, "list": [true, null, "x"]}')

    assert read == {
        "b": Decimal("1.10"),
        "a": Decimal("1E+3"),
        "big": 123456789012345678901234567890,
        "list": [True, None, "x"],
    }
    assert list(read) == ["b", "a", "big", "list"]
    with pytest.raises(ValueError, match="Expecting"):
        codec.loads("{")


@pytest.mark.covers("aurelius_atlas_model.codec.dumps", rules=["VAL-01"])
def test__decimals_dates_and_floats_are_written_as_jackson_writes_them() -> None:
    """``BigDecimal.toString``, epoch milliseconds, the shortest double, ``"NaN"``; keys as Java's text."""
    value = {
        "decimal": Decimal("1.10"),
        "exponent": Decimal("1E+3"),
        "nan": Decimal("NaN"),
        "date": datetime(1970, 1, 1, 0, 0, 1, tzinfo=UTC),
        "float": 0.1,
        "inf": [math.nan, math.inf, -math.inf],
        "text": 'é"',
        2: True,
        Decimal("1.5"): None,
        "set": (1,),
    }

    assert (
        codec.dumps(value)
        == (
            '{"decimal":1.10,"exponent":1E+3,"nan":"NaN","date":1000,"float":0.1,'
            '"inf":["NaN","Infinity","-Infinity"],"text":"é\\"","2":true,"1.5":null,"set":[1]}'
        ).encode()
    )


@pytest.mark.covers("aurelius_atlas_model.codec.dumps", "aurelius_atlas_model.codec.loads", rules=["VAL-01"])
def test__models_are_written_through_to_json_and_read_back_exactly() -> None:
    """A model's untyped values keep their Python types for the codec; anything else is no JSON."""
    entity = AtlasEntity(guid="g", attributes={"size": Decimal("1.10"), "seen": datetime(1970, 1, 1, tzinfo=UTC)})

    written = codec.dumps(entity)

    assert b'"attributes":{"size":1.10,"seen":0}' in written
    assert codec.loads(written)["attributes"]["size"] == Decimal("1.10")
    assert codec.dumps(AtlasStruct(type_name="t")) == b'{"typeName":"t"}'
    with pytest.raises(TypeError, match="object is not a JSON value"):
        codec.dumps(object())
