"""The client's JSON serializer (DD-039, DD-043)."""

from decimal import Decimal

import pytest
from aurelius_atlas_store_es.serializer import JSON_MIMETYPES, serializers


@pytest.mark.covers(
    "aurelius_atlas_store_es.serializer.serializers",
    "aurelius_atlas_store_es.serializer.DecimalJsonSerializer.loads",
    rules=["VAL-01"],
)
def test__floats_are_read_as_decimals_and_bytes_pass_through() -> None:
    """Every JSON media type Elasticsearch answers with is read with ``Decimal`` floats."""
    by_type = serializers()

    assert set(by_type) == set(JSON_MIMETYPES)
    assert by_type["application/json"].loads(b'{"a": 1.10, "b": 2}') == {"a": Decimal("1.10"), "b": 2}
    assert by_type["application/json"].dumps(b'{"a":1.10}') == b'{"a":1.10}'
